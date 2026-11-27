"""Independently check additive identities, fixed archive scope and proposal boundaries."""
import json
from datetime import timedelta
import os
import resource
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from analyze_direct_event_v61 import OUT, R60, H, assets, csvread, require, save
from design_geomagnetic_events_v61 import utc, catalog_events, matches, BIN, RULE
from check_external_evidence_v55 import check


def verify(samples,y,p,history,coords):
    lat=np.array(coords['lat'])
    wl=np.cos(lat*np.pi/180)
    summary=json.loads((OUT/'sse_summary.json').read_text())
    err=0.
    for row in summary:
        ids=[i for i,s in enumerate(samples) if s['date'].startswith(row['year']) and int(s['horizon'])==row['horizon']]
        yy=y[ids]
        pp=p[ids]
        valid=np.all((pp>0)&np.isfinite(pp),axis=1)&(yy>0)&np.isfinite(yy)
        diffs=np.where(valid,(pp[:,0]-yy)**2-(pp[:,3]-yy)**2,0)
        per=np.einsum('tcxy,x->c',diffs,wl)
        total=np.einsum('tcxy,x->',diffs,wl)
        require(np.allclose(per[row['top_layers']],row['top_layer_reductions'],rtol=2e-14,atol=0) and
                np.isclose(total,row['net_sse_reduction'],rtol=2e-14,atol=0),'Independent SSE')
        err=max(err,float(abs(per.sum()/total-1)))
    norm=json.loads((R60/'normalization.json').read_text())
    arr=np.concatenate([np.log(a) for t,a in history.items() if t.startswith('2021')])
    for j in range(29):
        zz=arr[:,j].ravel()
        require(abs(zz.mean()-norm['mean'][j])<2e-12 and abs(zz.std()-norm['std'][j])<2e-12,'Training stats changed')
    split=json.loads((OUT/'data_split_preregistration.json').read_text())
    inventory={r['cutoff_UTC']:r for r in csvread(OUT/'candidate_cutoff_inventory.csv')}
    for mode in ('minimum','expanded'):
        a=split[mode]['TRAIN']
        b=split[mode]['ENGINEERING_VALIDATION_ALREADY_USED']
        require(not split[mode]['LOCKED_INDEPENDENT_TEST'] and not split[mode]['MODEL_SELECTION_VALIDATION'],'Unexpected split promotion')
        for r in a+b:
            cut=utc(r['cutoff_UTC'])
            require(len(r['history_UTC'])==len(r['target_UTC'])==3 and
                    [int((utc(t)-cut).total_seconds()/3600) for t in r['history_UTC']]==[-3,-2,-1] and
                    [int((utc(t)-cut).total_seconds()/3600) for t in r['target_UTC']]==[1,3,6] and
                    inventory[r['cutoff_UTC']]['V37_or_sealed_family']=='False','Scope boundary')
            require(r['role']=='D' if r['run_id']=='UNRESOLVED' else r['role']=='A','Unresolved identity role')
        require(all(r['forcing_family']!=s['forcing_family'] and
              max(r['support_start_UTC'],s['support_start_UTC'])>=min(r['support_end_exclusive_UTC'],s['support_end_exclusive_UTC'])
              and (not r['event_id'] or r['event_id']!=s['event_id']) for r in a for s in b),'Split leakage')
    # Small artificial controls test gap rejection and storm merging. No density access here.
    d=utc('2020-01-01T00:00:00Z')
    q={d+i*BIN:1.0 for i in range(64)}
    quiet=catalog_events(q)
    require(len(quiet)==1 and matches(quiet[0],d,d+16*BIN),'Quiet positive')
    q[d+8*BIN]=5
    q[d+18*BIN]=6
    del q[d+19*BIN]
    storm=[r for r in catalog_events(q) if r['kind']=='disturbed']
    require(len(storm)==1 and not storm[0]['Kp_complete'],'Storm merge or missing buffer')
    require(not matches(storm[0],d+8*BIN,d+9*BIN),'Incomplete Kp accepted')
    save('independent_verification.json',dict(SSE_blocks=6,max_independent_relative_layer_closure=err,
         normalization_layers=29,training_runs=0,split_modes_checked=2,
         synthetic_event_controls=3,event_thresholds=RULE,status='VERIFIED'))


def plots(samples,y,p,x,coords):
    dest=OUT/'figures'
    require(OUT.resolve()==OUT and not dest.exists(),'Fresh figures directory')
    dest.mkdir()
    rows=csvread(OUT/'layer_error_contribution.csv')
    index=np.arange(29)
    methods=('Persistence','TwoFrameLinear','LogLinear','TinyDirectCNN')
    lut={(r['year'],int(r['horizon']),r['method'],int(r['ilev_index'])):r for r in rows if r['mask']=='common'}
    fig,ax=plt.subplots(2,2,figsize=(10,7),layout='constrained')
    fig.suptitle('V61 | 2022 autumn engineering validation | +6 h | native pressure coordinates')
    tt=[lut['2022',6,'Persistence',j] for j in index]
    for key in ('p5','p50','p95'):
        ax[0,0].semilogy(index,[float(r['target_'+key]) for r in tt],label=key)
    ax[0,0].set(title='Target density by native layer',ylabel='kg/m³')
    ax[0,0].legend()
    for m in methods:
        v=[lut['2022',6,m,j] for j in index]
        ax[0,1].semilogy(index,[float(r['rmse']) for r in v],label=m)
        ax[1,0].plot(index,[float(r['log_rmse']) for r in v],label=m)
    ax[0,1].set(title='Absolute RMSE',ylabel='kg/m³')
    ax[0,1].legend(fontsize=7)
    ax[1,0].set(title='Log RMSE',ylabel='natural log')
    deltas=np.array([float(lut['2022',6,'TinyDirectCNN',j]['delta_sse_vs_persistence']) for j in index])
    ax[1,1].bar(index,deltas,color=np.where(deltas>0,'#d65a40','#3476a6'))
    ax[1,1].set(title='Direct minus Persistence weighted SSE',ylabel='(kg/m³)²',yscale='symlog')
    ax[1,1].set_yscale('symlog',linthresh=1e-16)
    for a in ax.flat:
        a.set_xlabel('Native ilev index')
        a.grid(alpha=.2)
    fig.savefig(dest/'layer_diagnostics.png',dpi=145)
    plt.close(fig)

    ids=[i for i,s in enumerate(samples) if s['date'].startswith('2022') and s['horizon']=='6']
    yy=y[ids]
    d=p[ids,3]
    b=p[ids,0]
    valid=np.all((p[ids]>0)&np.isfinite(p[ids]),axis=1)
    e=np.where(valid,np.log(d/yy)**2-np.log(b/yy)**2,np.nan)
    heat=np.nanmean(e,axis=(0,3))
    i=next(i for i,s in enumerate(samples) if s['cutoff_UTC']=='2022-09-23T06:00:00Z' and s['horizon']=='6')
    diff=np.log(p[i,3,10]/y[i,10])
    spatial=np.abs(diff)-np.abs(np.log(p[i,0,10]/y[i,10]))
    shift=csvread(OUT/'input_distribution_shift.csv')
    fig,ax=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    fig.suptitle('V61 | +6 h log errors and train-normalized historical inputs')
    for a,z,title,xlab,ylab in [(ax[0,0],heat,'2022 pooled log MSE difference','Latitude (°)','ilev index'),
       (ax[0,1],diff,'Direct ln(pred / target), 2022-09-23 12Z, index 10','Longitude (°)','Latitude (°)'),
       (ax[1,0],spatial,'Direct minus Persistence |log error|, same target','Longitude (°)','Latitude (°)')]:
        xs=coords['lat'] if a is ax[0,0] else coords['lon']
        ys=index if a is ax[0,0] else coords['lat']
        lim=float(np.nanmax(abs(z)))
        pic=a.pcolormesh(xs,ys,z,cmap='RdBu_r',vmin=-lim,vmax=lim)
        a.set(xlabel=xlab,ylabel=ylab,title=title)
        fig.colorbar(pic,ax=a)
    for year in ('2021','2022'):
        r=[a for a in shift if a['year']==year]
        ax[1,1].plot(index,[float(a['mean']) for a in r],label=year)
        ax[1,1].fill_between(index,[float(a['p5']) for a in r],[float(a['p95']) for a in r],alpha=.2)
    ax[1,1].set(title='Historical log-density mean and P5–P95',xlabel='Native ilev index',ylabel='2021 training σ')
    ax[1,1].legend()
    fig.savefig(dest/'spatial_and_shift.png',dpi=145)
    plt.close(fig)


def main():
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    t=time.monotonic()
    samples,y,p,x,c,_=assets()
    verify(samples,y,p,x,c)
    plots(samples,y,p,x,c)
    save('handoff.json',check())
    save('resource_usage.json',dict(
       main=json.loads((OUT/'numerical_checks.json').read_text()),
       verification_plot_seconds=time.monotonic()-t,
       verification_plot_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
       GPU=0,new_training=0,new_integrations=0,new_label_decodes=0))


if __name__=='__main__':
    main()
