"""Targeted verification of sealed baselines, preflight forcing and event partitions."""
import json
import os
from datetime import timedelta
from pathlib import Path
import resource
import shutil
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset,num2date

from analyze_direct_event_v61 import assets, checked_array, sha, csvread, require, R59
from prepare_independent_events_v62 import (annual, utc, touches, separated, disjoint_runs, SOURCE, OUT, LOCAL, ROOT)
from run_event_baselines_v62 import save,table,NEW


def verify(kp,fobs):
    data=json.loads((OUT/'selected_event_pairs.json').read_text())
    manifest=json.loads((OUT/'prepared_run_config_manifest.json').read_text())
    plans=json.loads((OUT/'event_dataset_production_plan.json').read_text())
    chosen=data['primary']
    require(len(chosen)==2 and separated(*chosen) and disjoint_runs(*chosen),'Pair independence')
    candidates={r['event_id']:r for r in csvread(OUT/'geomagnetic_event_candidates.csv')}
    for plan in 'ABC':
        flat=[candidates[k] for values in plans[plan]['roles'].values() for k in values]
        require(len(flat)==plans[plan]['events'] and all(separated(r,s) and disjoint_runs(r,s)
            for i,r in enumerate(flat) for s in flat[:i]),'Role or event collision')
    nforcing=0
    for r,c in zip(chosen,manifest['preflight_runs']):
        folder=ROOT/c['directory']
        require(r['event_id']==c['event_id'] and sha(folder/'input.inp')==c['input_sha256'] and
            sha(folder/'seed.nc')==c['seed_sha256'] and sha(folder/'gpi.nc')==c['GPI_sha256'],'Prepared identity')
        require(not list(folder.glob('primary*')) and not list(folder.glob('secondary*')),'Unexpected launch products')
        with Dataset(folder/'gpi.nc') as n:
            for i,v in enumerate(n['year_day'][:]):
                from datetime import datetime,timezone
                d=datetime.strptime(str(int(v)),'%Y%j').replace(tzinfo=timezone.utc)
                require(n['f107d'][i]==fobs[d] and all(n['kp'][i,h]==kp[d+timedelta(hours=3*h)] for h in range(8)),
                    'GPI crosses source')
                nforcing+=1
        for cut in map(utc,r['prediction_cutoffs'].split(';')):
            require(utc(r['core_start'])<=cut-timedelta(hours=3) and cut+timedelta(hours=6)<utc(r['core_end_exclusive'])
                   and cut-timedelta(hours=3)>=utc(r['model_start'])+timedelta(days=14),'Label forecast support')
    samples,y,old,history,coords,_=assets()
    lock=json.loads((OUT/'baseline_prediction_lock.json').read_text())
    require(lock['target_reads_before_lock']==0 and sha(OUT/'new_baseline_protocol.json')==lock['protocol_SHA256'] and
            sha(OUT/'new_baseline_predictions_sha.csv')==lock['manifest_SHA256'],'Prediction lock')
    hashes={r['sample_id']:r['prediction_SHA256'] for r in csvread(OUT/'new_baseline_predictions_sha.csv')}
    x=[]
    max_delta=0.
    for r in samples:
        a=np.log(history[r['cutoff_UTC']])
        h=int(r['horizon'])
        times=np.array([-3.,-2.,-1.])
        fit=np.linalg.pinv(np.column_stack([np.ones(3),times]))@a.reshape(3,-1)
        logols=fit[0]+h*fit[1]
        damped=a[-1].ravel()+fit[1]*sum((np.exp(-j/3)-np.exp(-(j+1)/3))*3 for j in range(h+1))
        rotated=np.take(a[-1],(np.arange(72)+3*(h+1))%72,axis=-1).ravel()
        expected=np.exp(np.stack([logols,damped,rotated]).reshape(3,29,36,72))
        q=checked_array(LOCAL/('baseline_'+r['sample_id']+'.bin'),hashes[r['sample_id']],(3,29,36,72))
        rel=float(np.max(abs(q/expected-1)))
        require(rel<1e-12,'Independent forecast parity')
        max_delta=max(max_delta,rel)
        x.append(q)
    x=np.array(x)
    wgt=np.cos(np.deg2rad(coords['lat']))
    count=0
    for row in csvread(OUT/'baseline_metrics.csv'):
        if row['method'] not in NEW or row['mask']!='common':
            continue
        i=[j for j,r in enumerate(samples) if r['date'].startswith(row['year']) and r['horizon']==row['horizon']]
        actual=x[i,NEW.index(row['method'])]
        valid=np.all(old[i]>0,axis=1)&(y[i]>0)
        error=np.where(valid,(actual-y[i])**2,0)
        metric=np.sqrt(np.einsum('tlxy,x->',error,wgt)/np.einsum('tlxy,x->',valid,wgt))
        require(np.isclose(metric,float(row['rmse']),rtol=3e-13),'Independent RMSE')
        count+=1
    # 24-hour history is located using time coordinates only.
    requested=csvread(OUT/'periodic_history_authorization_request.csv')
    sources={}
    for r in requested:
        rel=r['source_run_id']
        if rel not in sources:
            index=set()
            for file in sorted((ROOT/rel).glob('secondary_*.nc')):
                with Dataset(file) as n:
                    time_var=n['time']
                    index.update(x.isoformat()+'Z' for x in num2date(time_var[:],time_var.units))
            sources[rel]=index
        r['source_time_axis_present']=r['required_history_UTC'] in sources[rel]
        previous={c for t in history for c in (utc(t)-timedelta(hours=k) for k in (1,2,3))}
        require(utc(r['required_history_UTC']) not in previous,'C includes previously authorized history')
    table('periodic_history_metadata_check.csv',requested)
    save('independent_verification.json',dict(configurations=2,GPI_days_checked=nforcing,disjoint_dataset_plans=3,
         native_forecast_matches=len(x),max_relative_forecast_delta=max_delta,weighted_global_checks=count,
         periodic_requested=24,periodic_time_axis_present=sum(r['source_time_axis_present'] for r in requested),
         periodic_DEN_reads=0,unapproved_DEN_reads=0,model_launches=0))


def figures(kp):
    figpath=OUT/'figures'
    require(figpath.resolve()==figpath and not figpath.exists(),'Figure path')
    figpath.mkdir()
    pairs=json.loads((OUT/'selected_event_pairs.json').read_text())['primary']
    plans=json.loads((OUT/'event_dataset_production_plan.json').read_text())
    fig,axes=plt.subplots(3,1,figsize=(10,8),layout='constrained')
    for ax,r in zip(axes,pairs):
        lo,hi=utc(r['buffer_start']),utc(r['buffer_end_exclusive'])
        times=sorted(t for t in kp if lo<=t<hi)
        ax.step(times,[kp[t] for t in times],where='post',color='#237c96')
        ax.axvspan(utc(r['core_start']),utc(r['core_end_exclusive']),color='#92cca8',alpha=.4,label='Event core')
        for c in r['prediction_cutoffs'].split(';'):
            ax.axvline(utc(c),color='#465cac',alpha=.4,ls='--')
        ax.set(title=r['event_id']+' | complete Kp buffers', ylabel='GFZ definitive Kp')
        ax.set_ylim(0,9)
        ax.legend(loc='upper right')
    axes[2].bar(['A · 2 events','B · 8 events','C · 22 events'],[plans[k]['estimated_wall_hours'] for k in 'ABC'],color='#237c96')
    axes[2].set(title='Serial cold-start production estimate',ylabel='Wall-clock hours (4 MPI ranks)')
    fig.savefig(figpath/'events_and_cost.png',dpi=155)
    plt.close(fig)
    base=csvread(OUT/'baseline_metrics.csv')
    layers=csvread(OUT/'baseline_layer_metrics.csv')
    reg=csvread(OUT/'baseline_region_metrics.csv')
    def values(rows,m,metric,region=None):
        return [float(r[metric]) for r in rows if r['year']=='2022' and r['mask']=='common' and r['method']==m
                and (region is None or r['region']==region)]
    fig,ax=plt.subplots(2,2,figsize=(10,7),layout='constrained')
    fig.suptitle('2022 historical engineering data | common valid cells | no independent test')
    methods=list(dict.fromkeys(r['method'] for r in base))
    for m in methods:
        ax[0,0].semilogy([1,3,6],values(base,m,'rmse'),'o-',label=m)
        ax[0,1].semilogy([1,3,6],values(base,m,'log_rmse'),'o-')
        ax[1,0].semilogy(list(range(29)),values([r for r in layers if r['horizon']=='6'],m,'log_rmse'))
        ax[1,1].semilogy([1,3,6],values(reg,m,'log_rmse','south_polar'),'o-')
        ax[1,1].semilogy([1,3,6],values(reg,m,'log_rmse','north_polar'),'o--')
    ax[0,0].set(title='Global absolute RMSE',ylabel='kg/m³',xlabel='Lead (h)')
    ax[0,1].set(title='Global log RMSE',xlabel='Lead (h)')
    ax[1,0].set(title='+6 h log RMSE per interface',xlabel='Native ilev index')
    ax[1,1].set(title='Polar log RMSE (south solid / north dashed)',xlabel='Lead (h)')
    for a in ax.flat:
        a.grid(alpha=.2)
    ax[0,0].legend(fontsize=7)
    fig.savefig(figpath/'forecast_errors.png',dpi=155)
    plt.close(fig)


def main():
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    t=time.monotonic()
    kp,fobs,_,_=annual()
    verify(kp,fobs)
    figures(kp)
    configs=OUT/'configs'
    configs.mkdir()
    for tag in ('q','d'):
        shutil.copyfile(LOCAL/tag/'input.inp',configs/(tag+'_input.inp'))
    from check_external_evidence_v55 import check
    save('handoff.json',check())
    metrics=Path('/proc/meminfo').read_text()
    save('resource_usage.json',dict(affinity_cpu_ids=sorted(os.sched_getaffinity(0)),native_affinity_before_cap=sorted(os.sched_getaffinity(os.getppid())),
          cgroup={k:Path('/sys/fs/cgroup',k).read_text().strip() for k in [
              'cpu/cpu.cfs_quota_us','cpu/cpu.cfs_period_us','memory/memory.limit_in_bytes']},
          host_MemAvailable_KiB=int(next(r.split()[1] for r in metrics.splitlines() if r.startswith('MemAvailable:'))),
          disk_free_bytes=shutil.disk_usage(ROOT).free,verification_seconds=time.monotonic()-t,
          verification_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,GPU=0,training=0,integrations=0))


if __name__=='__main__':
    main()
