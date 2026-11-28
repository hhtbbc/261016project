"""Post-score diagnostics using only the authorized cache and locked forecasts."""
import json
import math
import os
from datetime import timedelta

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from score_independent_events_v64 import B, METHODS, OUT, ROOT, RUNS, SHAPE, V62, V63
from run_independent_predictions_v64 import need, read_csv, save, sha, table, utc

P='Persistence'
LT='LocalTimePersistence'
DAY='DailyPersistence'
CNN='TinyDirectCNN'
SHORT=['P','Linear','Log','OLS','Damped','LT','Daily','CNN']
LEADS=(1,3,6)
V60=ROOT/'experiments/thermosphere_tiny_direct_cpu_v60'


def read(name):
    return json.loads(name.read_text())


def producer_plan():
    previous=read(V62/'event_dataset_production_plan.json')
    roles=previous['B']['roles']
    roles['LOCKED_INDEPENDENT_TEST']=previous['C']['roles']['LOCKED_INDEPENDENT_TEST'][2:]
    candidates={r['event_id']:r for r in read_csv(V62/'geomagnetic_event_candidates.csv')
                if r['full_metadata_candidate']=='True'}
    costs={r['event_id']:r for r in read_csv(V62/'simulation_cost_estimates.csv')}
    actual=read(V63/'resource_usage.json')
    seconds_per_day=sum(r['elapsed_s'] for r in actual.values())/35
    cpu_per_day=sum(r['CPU_user_s']+r['CPU_system_s'] for r in actual.values())/35
    bytes_per_day=sum(r['native_bytes'] for r in actual.values())/35
    plan={}
    timeline=[]
    for role,ids in roles.items():
        plan[role]=[]
        for event in ids:
            c,v=candidates[event],costs[event]
            days=int(v['days'])
            a,b=utc(c['buffer_start']),utc(c['buffer_end_exclusive'])
            timeline.append((a,b,event))
            plan[role].append(dict(event=event,subclass=c['design_subclass'],season=c['season'],
                peak_kp=float(c['peak_Kp']),core_start=c['core_start'],core_end_exclusive=c['core_end_exclusive'],
                start=v['start'],end=v['end'],cutoffs=c['prediction_cutoffs'].split(';'),steps=int(v['steps_60s']),
                wall_hours=days*seconds_per_day/3600,cpu_hours=days*cpu_per_day/3600,
                native_GiB=days*bytes_per_day/2**30))
    timeline.sort()
    need(all(l[1]+timedelta(hours=72)<=r[0] for l,r in zip(timeline,timeline[1:])),
         'Candidate event buffers not independent')
    entries=[x for group in plan.values() for x in group]
    need(len({x['event'] for x in entries})==8 and not set(RUNS)&{x['event'] for x in entries},'Role collision')
    return dict(roles=plan,estimate_4_rank_basis='V63 measured 35 integration days, extrapolated linearly',
                totals={k:sum(e[k] for e in entries) for k in ('wall_hours','cpu_hours','native_GiB')},
                training_first={k:sum(e[k] for e in plan['TRAIN']) for k in ('wall_hours','cpu_hours','native_GiB')},
                constraints=['new authorization','verify forcing and model calendar','validate season seed and convergence',
                             'use separate role families','seal locked test labels',
                             'V65 scope is new training events first'])


def plot_save(fig,name):
    fig.savefig(B/'figures'/f'{name}.png',dpi=135,bbox_inches='tight')
    plt.close(fig)


def plot_lines(events,metric,axes,lookup):
    for e,ax in zip(events,axes):
        for name,short in zip(METHODS,SHORT):
            ax.plot(LEADS,[lookup[e,h,'global',name][metric] for h in LEADS],'.-',label=short)
        if metric=='rmse':
            ax.set_yscale('log')
        ax.set(title=e,xlabel='Forecast lead (h)',ylabel='kg m$^{-3}$' if metric=='rmse' else 'log RMSE',
               xticks=LEADS)
        ax.grid(alpha=.25)
    axes[0].legend(ncol=4,fontsize=8)


def main():
    need(B.resolve()==B,'Unexpected work path')
    (B/'figures').mkdir()
    rows=read_csv(B/'event_metrics.csv')
    events=list(RUNS)
    lookup={(r['group'],int(r['lead_hours']),r['region'],r['method']):
             {k:float(r[k]) if r[k] else math.nan for k in
              ('log_rmse','rmse','relative_rmse','log_bias','coverage','mae')}
             for r in rows if r['mask']=='common'}
    records=read_csv(B/'target_extraction_manifest.csv')
    targets=np.fromfile(B/'data_local/targets.bin',dtype='<f8').reshape(21,*SHAPE)
    receipt=read(B/'independent_verification.json')
    need(sha(B/'data_local/targets.bin')==receipt['target_cache_SHA256'],'Cache drift')
    manifest={(r['record_id'],r['method']):r for r in read_csv(OUT/'prediction_manifest.csv')}
    coords=read(OUT/'native_coordinates.json')
    lat=np.asarray(coords['lat'])
    lon=np.asarray(coords['lon'])
    w=np.cos(np.deg2rad(lat))[None,:,None]

    def pred(record,method):
        return np.fromfile(OUT/manifest[record['record_id'],method]['file'],dtype='<f8').reshape(SHAPE)

    summary=[]
    for e in events:
        for h in LEADS:
            v={m:lookup[e,h,'global',m] for m in METHODS}
            row=dict(event=e,lead=h,metrics=v,best_log=min(v,key=lambda m:v[m]['log_rmse']),
                     best_abs=min(v,key=lambda m:v[m]['rmse']))
            for name in (P,DAY):
                row[f'LT_vs_{name}_pct']={metric:100*(v[LT][metric]/v[name][metric]-1)
                                          for metric in ('rmse','log_rmse')}
            counts=sum(lookup[e,h,f'ilev_{l:02}',LT]['log_rmse']<
                       lookup[e,h,f'ilev_{l:02}',P]['log_rmse'] for l in range(29))
            row.update(LT_log_layers_better_than_P=counts,regions={g:{m:lookup[e,h,g,m] for m in METHODS}
                       for g in ('north_polar','south_polar','low_density','ilev_28')})
            summary.append(row)

    normal=read(V60/'normalization.json')
    need(sha(V60/'normalization.json')==read(OUT/'frozen_method_protocol.json')['normalization_SHA256'],
         'V60 normalization drift')
    shifted=[]
    cutoffs=sorted({r['cutoff_UTC'] for r in records})
    for e in events:
        indices=[i for i,c in enumerate(cutoffs) if any(r['event_id']==e and r['cutoff_UTC']==c for r in records)]
        x=np.stack([np.fromfile(OUT/f'data_local/history_{i:02}/anchors.txt',dtype='<f8').reshape(3,*SHAPE)
                    for i in indices])
        log=np.log(x)
        mean=log.mean(axis=(0,1,3,4))
        std=log.std(axis=(0,1,3,4))
        for l in range(29):
            a,b=normal['mean'][l],normal['std'][l]
            shifted.append(dict(event=e,level=l,ilev=coords['ilev'][l],train_2021_log_mean=a,
                                train_2021_log_std=b,input_2023_log_mean=mean[l],input_2023_log_std=std[l],
                                shift_sigma=(mean[l]-a)/b,std_ratio=std[l]/b))
    table(B/'input_distribution_shift.csv',shifted)

    source=read(V62/'gfz_source_manifest.json')
    raw=ROOT/source['stored_path']
    need(sha(raw)==source['source_sha256'],'GFZ source drift')
    kp={}
    for line in raw.read_text().splitlines():
        s=line.split()
        if s and s[0]=='2023' and s[1]=='05':
            if int(s[27]) in (1,2):
                for j,v in enumerate(s[7:15]):
                    kp[int(s[2]),3*j]=float(v)

    def at(time):
        d=utc(time)
        value=kp[d.day,3*(d.hour//3)]
        need(0<=value<=9,'Invalid definitive Kp')
        return value

    diag=[]
    for i,r in enumerate(records):
        current=at(r['cutoff_UTC'])
        target_kp=at(r['UTC'])
        y=targets[i]
        p,lt,cnn,daily=[pred(r,m) for m in (P,LT,CNN,DAY)]

        def rms(a):
            valid=np.isfinite(a)
            ww=np.broadcast_to(w,a.shape)[valid]
            return float(np.sqrt(np.average(a[valid]**2,weights=ww)))

        ltr=np.log(y)-np.log(lt)
        pr=np.log(y)-np.log(p)
        cr=np.log(cnn)-np.log(p)
        diag.append(dict(event=r['event_id'],cutoff_UTC=r['cutoff_UTC'],target_UTC=r['UTC'],
                         lead=int(r['lead_hours']),cutoff_Kp=current,target_Kp=target_kp,
                         LT_residual_rms=rms(ltr),P_residual_rms=rms(pr),
                         Daily_residual_rms=rms(np.log(y)-np.log(daily)),
                         CNN_correction_rms=rms(cr),CNN_over_P_true_change_rms=rms(cr)/rms(pr),
                         LT_residual_south_mean=float(np.nanmean(ltr[:,lat<=-60,:])),
                         LT_residual_north_mean=float(np.nanmean(ltr[:,lat>=60,:]))))
    table(B/'kp_and_residual_diagnostics.csv',diag)
    covariation=[]
    for event in events:
        for lead in LEADS:
            group=[r for r in diag if r['event']==event and r['lead']==lead]
            x=np.array([r['target_Kp'] for r in group])
            y=np.array([r['LT_residual_rms'] for r in group])
            corr=float(np.corrcoef(x,y)[0,1]) if np.ptp(x)>0 and np.ptp(y)>0 else None
            covariation.append(dict(event=event,lead=lead,cutoffs=len(group),
                                    target_Kp_vs_LT_RMS_pearson=corr))
    save(B/'kp_covariation.json',dict(descriptive_only=True,causal_inference=False,rows=covariation))

    macro=[dict(method=m,lead=h,**{metric:float(np.mean([lookup[e,h,'global',m][metric] for e in events]))
                                   for metric in ('rmse','log_rmse','relative_rmse','mae')})
           for m in METHODS for h in LEADS]
    table(B/'two_event_macro_metrics.csv',macro)
    save(B/'method_comparison_summary.json',dict(event_leads=summary,pooled_metric_mask='all methods common',
         event_shift_layers={e:{str(k):int(sum(abs(r['shift_sigma'])>=k for r in shifted if r['event']==e))
                               for k in (1,3)} for e in events}))
    save(B/'event_exposure_registry.json',{e:dict(run_id=rid,role='EXPOSED_PILOT_EVALUATION',
         reason='Results used for residual-background design and method selection',
         eligible_for_final_unseen_test=False) for e,rid in RUNS.items()})
    save(B/'next_dataset_production_plan.json',producer_plan())

    for metric in ('rmse','log_rmse'):
        fig,axes=plt.subplots(1,2,figsize=(11,4))
        plot_lines(events,metric,axes,lookup)
        fig.suptitle('TIE-GCM model density HINDCAST | common positive support')
        plot_save(fig,metric)
    fig,axes=plt.subplots(2,3,figsize=(13,7),sharex=True)
    for i,e in enumerate(events):
        for j,h in enumerate(LEADS):
            ax=axes[i,j]
            for m,s in zip(METHODS,SHORT):
                ax.plot(range(29),[lookup[e,h,f'ilev_{l:02}',m]['relative_rmse'] for l in range(29)],label=s)
            ax.set(title=f'{e}, +{h}h',xlabel='Native pressure index',ylabel='Relative RMSE')
    axes[0,0].legend(ncol=2,fontsize=7)
    plot_save(fig,'layer_relative_rmse')

    for label,regions,selected in [('polar_and_low',['south_polar','north_polar','low_density'],METHODS),
                                  ('local_vs_daily',['global'],(P,LT,DAY))]:
        fig,axes=plt.subplots(2,len(regions),figsize=(max(6,4*len(regions)),7),squeeze=False)
        for i,e in enumerate(events):
            for j,g in enumerate(regions):
                ax=axes[i,j]
                for m in selected:
                    ax.plot(LEADS,[lookup[e,h,g,m]['log_rmse'] for h in LEADS],'.-',label=SHORT[METHODS.index(m)])
                ax.set(title=f'{e}, {g}',xlabel='Lead (h)',ylabel='log RMSE',xticks=LEADS)
        axes[0,0].legend(ncol=3,fontsize=7)
        plot_save(fig,label)

    fig,axes=plt.subplots(2,2,figsize=(10,7),layout='constrained')
    fig2,axes2=plt.subplots(2,4,figsize=(15,7),layout='constrained')
    for i,e in enumerate(events):
        j=next(j for j,r in enumerate(records) if r['event_id']==e and int(r['lead_hours'])==6)
        r=records[j]
        y=targets[j,20]
        p,lt,d=[pred(r,m)[20] for m in (P,LT,DAY)]
        errors=[np.log(y)-np.log(v) for v in (p,lt)]
        bound=max(np.nanmax(abs(v)) for v in errors)
        fields=[np.log10(v) for v in (y,p,lt,d)]
        lo,hi=min(np.nanmin(v) for v in fields),max(np.nanmax(v) for v in fields)
        for k,error in enumerate(errors):
            ax=axes[i,k]
            im=ax.pcolormesh(lon,lat,error,cmap='RdBu_r',vmin=-bound,vmax=bound)
            ax.set(title=f'{r["UTC"]}\n{(P,LT)[k]}',xlabel='East lon (°)',ylabel='Lat (°)')
        fig.colorbar(im,ax=axes[i],label='ln(target/prediction), ilev index 20')
        for k,f in enumerate(fields):
            ax=axes2[i,k]
            im=ax.pcolormesh(lon,lat,f,vmin=lo,vmax=hi)
            ax.set(title=f'{r["UTC"]}\n{("Target",P,LT,DAY)[k]}',xlabel='East lon (°)',ylabel='Lat (°)')
        fig2.colorbar(im,ax=axes2[i],label='log10(DEN in kg m$^{-3}$), ilev index 20')
    plot_save(fig,'spatial_log_residuals')
    plot_save(fig2,'model_target_predictions')

    fig,axes=plt.subplots(2,1,figsize=(10,6))
    for e,ax in zip(events,axes):
        d=[r for r in diag if r['event']==e and r['lead']==6]
        x=np.arange(len(d))
        for name in ('P','LT','Daily'):
            ax.plot(x,[r[f'{name}_residual_rms'] for r in d],'.-',label=name)
        ax.set(title=e,ylabel='+6h log RMSE',xticks=x,xticklabels=[r['cutoff_UTC'][5:16] for r in d])
        right=ax.twinx()
        right.plot(x,[r['cutoff_Kp'] for r in d],':k',label='Cutoff Kp')
        right.plot(x,[r['target_Kp'] for r in d],'--k',label='Target Kp')
        right.set_ylabel('Definitive Kp')
        ax.legend(loc='upper left',fontsize=8)
        right.legend(loc='upper right',fontsize=8)
    plot_save(fig,'kp_and_error')

    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for e in events:
        d=[r for r in shifted if r['event']==e]
        for ax,key,label in zip(axes,('shift_sigma','std_ratio'),('Mean shift in 2021 σ','2023 / 2021 σ')):
            ax.plot(range(29),[r[key] for r in d],label=e)
            ax.set(xlabel='Native pressure index',ylabel=label)
    axes[0].axhline(0,color='gray')
    axes[1].axhline(1,color='gray')
    axes[0].legend(fontsize=8)
    plot_save(fig,'input_distribution_shift')


if __name__=='__main__':
    main()
