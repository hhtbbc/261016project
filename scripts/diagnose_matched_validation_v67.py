"""TRAIN-only predictability and held-out validation diagnostics without model updates."""
from collections import defaultdict
import json
import os

import numpy as np

from evaluate_matched_validation_v67 import METHODS, OUT, LOCAL, V65, RUNS, LEADS, save, sha
from run_native_density_baselines_v59 import read_csv,table,need


def numeric_suite():
    a=np.exp(.2*np.cos(np.arange(72)*2*np.pi/72))
    # At a later time, fixed local time samples the earlier field farther east.
    later=np.exp(.2*np.cos((np.arange(72)+3)*2*np.pi/72))
    need(np.allclose(later,np.roll(a,-3),rtol=2e-15),'Eastward phase/sign')
    need(np.allclose(later,np.take(a,(np.arange(72)+3)%72),rtol=2e-15),'Seam')


def train_diagnostic():
    numeric_suite()
    rows=read_csv(V65/'hourly_training_sample_manifest.csv')
    a=V65/'data_local/training_arrays'
    pins=json.loads((V65/'training_arrays_SHA256.json').read_text())
    for name in ('density_kg_m3.npy','sample_field_indices.npy','log_residuals.npy'):
        need(sha(a/name)==pins[name]['SHA256'],'TRAIN diagnostic identity')
    x=np.load(a/'density_kg_m3.npy',mmap_mode='r')
    ix=np.load(a/'sample_field_indices.npy',mmap_mode='r')
    residual=np.load(a/'log_residuals.npy',mmap_mode='r')
    log=np.log(x.astype(float))
    latest=log[ix[:,2]]
    prev=log[ix[:,1]]
    align=latest-np.roll(prev,-3,axis=-1)
    ordinary=latest-prev
    lat=np.asarray(json.loads((V65/'data_quality_report.json').read_text())['coordinates']['lat'])
    w=np.cos(np.deg2rad(lat))[None,None,:,None]

    def measures(x,y,w):
        w=np.broadcast_to(w,y.shape)
        avg=lambda t:float(np.average(t,weights=w))
        xx,yy=x-avg(x),y-avg(y)
        u,v,r=avg(xx**2),avg(yy**2),avg(xx*yy)
        return r/(u*v)**.5 if u and v else None,avg(x*x)**.5,avg(y*y)**.5

    groups={e:[i for i,r in enumerate(rows) if r['event_id']==e] for e in sorted({r['event_id'] for r in rows})}
    groups.update({c:[i for i,r in enumerate(rows) if r['event_id'].startswith(c)] for c in ('quiet','disturbed')})
    result=[]
    for event,index in groups.items():
        for tag,a0 in [('P',0),('LT',1)]:
            raw=[residual[a0,index,j].astype(float) for j,h in enumerate(LEADS)]
            back=[np.roll(x,3*(h+1),axis=-1) if tag=='LT' else x for h,x in zip(LEADS,raw)]
            delta=align[index] if tag=='LT' else ordinary[index]
            regions={'global':np.ones(36,bool),'polar':abs(lat)>=60,'nonpolar':abs(lat)<60}
            for name,domain in regions.items():
                W=w[:,:,domain]
                d=delta[:,:,domain]
                for j,h in enumerate(LEADS):
                    r=back[j][:,:,domain]
                    corr,dx,rr=measures(d,r,W)
                    w1=raw[j][:,:,domain]
                    east=measures(w1,np.roll(w1,-1,axis=-1),W)[0]
                    le=(slice(None),slice(None),domain,slice(None))
                    adjacent=measures(back[j][:-1][le],back[j][1:][le],W)[0] if event in groups and event not in ('quiet','disturbed') else None
                    cross=measures(back[0][:,:,domain],r,W)[0] if j else 1.
                    zonal=np.fft.rfft(r,axis=-1)[...,1]
                    result.append(dict(event=event,background=tag,domain=name,lead=h,windows=len(index),
                               aligned_history_change_vs_future_residual_r=corr,history_change_rms=dx,
                               remaining_log_residual_rms=rr,within_event_adjacent_cutoff_r=adjacent,
                               lead1_to_leadN_r=cross,zonal_neighbor_r=east,
                               zonal_wavenumber1_mean_amplitude=float(abs(zonal).mean()*2/72),
                               role='TRAIN_DESCRIPTIVE'))
                    if name=='global':
                        for l in range(29):
                            a,b,c=measures(delta[:,l:l+1],back[j][:,l:l+1],w)
                            result.append(dict(event=event,background=tag,domain=f'ilev_{l:02}',lead=h,windows=len(index),
                               aligned_history_change_vs_future_residual_r=a,history_change_rms=b,
                               remaining_log_residual_rms=c,within_event_adjacent_cutoff_r=None,
                               lead1_to_leadN_r=None,zonal_neighbor_r=None,zonal_wavenumber1_mean_amplitude=None,
                               role='TRAIN_DESCRIPTIVE'))
    table(OUT/'train_residual_predictability.csv',result)
    return result


def plots(train):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    root=OUT/'figures'
    root.mkdir()

    def push(f,n):
        f.tight_layout()
        f.savefig(root/f'{n}.png',dpi=105,bbox_inches='tight')
        plt.close(f)

    g=read_csv(OUT/'global_metrics.csv')
    e=read_csv(OUT/'residual_energy_decomposition.csv')
    l=read_csv(OUT/'layer_metrics.csv')
    r=read_csv(OUT/'regional_metrics.csv')
    d=read_csv(OUT/'input_distribution_shift.csv')
    target=np.fromfile(LOCAL/'targets.bin',dtype='<f8').reshape(12,29,36,72)
    fp=np.fromfile(LOCAL/'forecasts.bin',dtype='<f8').reshape(6,12,29,36,72)
    record=read_csv(OUT/'target_extraction_manifest.csv')
    events=tuple(RUNS)
    fig,ax=plt.subplots(1,2,figsize=(10,4))
    for axis,event in zip(ax,events):
        for m in METHODS:
            rows=[v for v in g if v['group']==event and v['mask']=='common' and v['method']==m]
            axis.plot(LEADS,[float(v['log_rmse']) for v in rows],'.-',label=m)
        axis.set(title=event,xticks=LEADS,xlabel='Lead hours',ylabel='Weighted log RMSE')
    ax[0].legend(fontsize=7)
    push(fig,'validation_log_rmse')
    for name,domain in [('incremental_gain','global'),('polar_low_density','regional'),('layer_error','layer')]:
        fig,ax=plt.subplots(1,2,figsize=(10,4))
        for axis,event in zip(ax,events):
            for arm in ('P','LT'):
                if domain=='global':
                    rows=[v for v in g if v['group']==event and v['mask']=='common' and v['method']==arm+'-Residual-CNN']
                    axis.plot(LEADS,[float(v['log_rmse_delta_pct_vs_'+arm]) for v in rows],'.-',label=arm)
                elif domain=='layer':
                    rows=[v for v in l if v['group_key']=='event_id' and v['group']==event and v['lead']=='6'
                          and v['method']==arm+'-Residual-CNN' and v['mask']=='common']
                    axis.plot(range(29),[float(v['log_rmse_delta_pct_vs_'+arm]) for v in rows],label=arm)
                else:
                    keys=['north_polar','south_polar','low_density']
                    for k in keys:
                        vv=[v for v in r if v['group_key']=='event_id' and v['group']==event and v['domain']==k
                            and v['method']==arm+'-Residual-CNN' and v['mask']=='common']
                        axis.plot(LEADS,[float(v['log_rmse_delta_pct_vs_'+arm]) if v['log_rmse_delta_pct_vs_'+arm] else np.nan
                                         for v in vv],'.-',label=f'{arm}:{k}')
            axis.axhline(0,color='gray')
            axis.set(title=event,ylabel='RMSE change vs own background (%)',xlabel='ilev index' if domain=='layer' else 'Lead hours')
        ax[0].legend(fontsize=7)
        push(fig,name)
    fig,ax=plt.subplots(1,2,figsize=(10,4))
    for axis,event in zip(ax,events):
        i=[j for j,r in enumerate(record) if r['event_id']==event and int(r['lead_hours'])==6]
        for arm,b,m in [('P',0,4),('LT',2,5)]:
            xx=np.log(target[i]/fp[b,i]).ravel()[::32]
            yy=np.log(fp[m,i]/fp[b,i]).ravel()[::32]
            axis.scatter(xx,yy,s=2,alpha=.23,label=arm)
        axis.set(title=event,xlabel='True background log residual',ylabel='Predicted correction')
    ax[0].legend()
    push(fig,'residual_vs_correction')
    fig,ax=plt.subplots(1,2,figsize=(11,4))
    for axis,event in zip(ax,events):
        rows=[x for x in e if x['group_key']=='event_id' and x['group']==event and x['domain']=='global']
        x=np.arange(len(rows))
        for k,n in enumerate(('twice_cross','correction_energy','actual_gain')):
            axis.bar(x+(k-1)*.24,[float(r[n]) for r in rows],.24,label=n)
        axis.set(title=event,xticks=x,xticklabels=[r['lead']+'h/'+r['arm'] for r in rows],ylabel='Log error squared')
    ax[0].legend(fontsize=7)
    push(fig,'energy_identity')
    fig,ax=plt.subplots(1,2,figsize=(10,4))
    for t in sorted({v['cutoff_UTC'] for v in d}):
        q=[v for v in d if v['cutoff_UTC']==t]
        for axis,key in zip(ax,('standardized_mean','outside_3sigma')):
            axis.plot(range(29),[float(v[key]) for v in q],label=t[:13])
            axis.set(xlabel='Native ilev index',ylabel=key)
    ax[0].legend(fontsize=7)
    push(fig,'validation_input_shift')
    fig,ax=plt.subplots(1,2,figsize=(10,4))
    for axis,e in zip(ax,('quiet','disturbed')):
        for arm in ('P','LT'):
            for h in LEADS:
                rows=[r for r in train if r['event']==e and r['background']==arm and r['lead']==h
                      and r['domain'].startswith('ilev')]
                axis.plot(range(29),[r['aligned_history_change_vs_future_residual_r'] for r in rows],
                          label=f'{arm} +{h}h')
        axis.set(title=e,xlabel='Native ilev index',ylabel='Pearson r (TRAIN)')
    ax[0].legend(ncol=2,fontsize=7)
    push(fig,'aligned_history_predictability')


def main():
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    need(OUT.resolve()==OUT,'Unsafe diagnostic path')
    train=train_diagnostic()
    plots(train)
    save(OUT/'event_exposure_registry.json',{event:dict(run_id=run,role='MODEL_SELECTION_VALIDATION_EXPOSED',
          final_test_eligible=False) for event,run in RUNS.items()})
    save(OUT/'scientific_decision.json',dict(AI_incremental_value='NOT_ESTABLISHED',
         strongest_baselines=['LocalTimePersistence','DailyPersistence'],
         LT_CNN='One held-out +1h gain, five other combinations favor frozen LT; no broad incremental improvement',
         P_CNN='Short lead improvements but +6h deterioration in both events',
         caveat='Two events, one strong disturbance cutoff; no Swarm or causal validation'))
    save(OUT/'next_model_preregistration.json',dict(proposals=[
         dict(name='TRAIN-only amplitude shrinkage',formula='log(rho_LT)+alpha_train(ilev,h)*c',
              parameters=1027,changes='Shrinkage only; fixed range [0,1], nested out-of-event estimates on TRAIN'),
         dict(name='add independent strong TRAIN event',changes='Training event coverage only, same network and hyperparameters',
              caveat='Fresh data authorization and no rerole of VAL2')],guard='Freeze once before fresh validation; '
              'oracle alpha cannot select deployable shrinkage. Original final test events remain sealed.',
         hypothesis='Where correction cross term cannot cover its energy, conservative shrinkage may prevent degradation.',
         secondary_candidate='Eastward align t−3 and t−2 to latest t−1 by +6/+3 cells, keep output LT background. '
                             'Prioritize only if signal survives per-event validation.',
         budget='Same CNN 200 CPU updates; historical V66 whole-arm below 18 s, plan <=600 s per training arm',
         primary='event-by-lead area weighted log RMSE versus untrained LT; flag degradation against LT',
         failure='No consistent improvement at held-out event level or meaningful polar/upper deterioration'))
    print('TRAIN_AND_VALIDATION_DIAGNOSTICS_COMPLETE')


if __name__=='__main__':
    main()
