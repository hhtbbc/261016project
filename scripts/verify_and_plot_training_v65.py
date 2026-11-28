"""Independent V65 data audit on generated arrays, with eight diagnostic figures."""
import hashlib
import os
from collections import Counter
from datetime import timedelta

import numpy as np

from build_training_dataset_v65 import LEADS, SHAPE
from run_training_events_v65 import EVENTS, OUT, PRIVATE, V62, annual, at, load, require, sha, write_once
from run_native_density_baselines_v59 import read_csv, table


def verify():
    lock=load(OUT/'training_scope_lock.json')['SHA256']
    require(all(sha(OUT/name)==checksum for name,checksum in lock.items()),'Frozen scope mismatch')
    samples=read_csv(OUT/'hourly_training_sample_manifest.csv')
    field=read_csv(OUT/'training_field_manifest.csv')
    field_at={(f['run_id'],f['UTC']):i for i,f in enumerate(field)}
    require(len(field_at)==len(field),'Duplicate field identity')
    quality=load(OUT/'data_quality_report.json')
    coords=quality['coordinates']
    receipts={event:load(OUT/'run_receipts'/f'{tag}_run_receipt.json') for tag,(event,*_) in EVENTS.items()}
    candidates={r['event_id']:r for r in read_csv(V62/'geomagnetic_event_candidates.csv')}
    work=PRIVATE/'training_arrays'
    hashes=load(OUT/'training_arrays_SHA256.json')
    require(all(sha(work/p)==r['SHA256'] and (work/p).stat().st_size==r['bytes'] for p,r in hashes.items()),
            'Training array SHA mismatch')
    x=np.load(work/'density_kg_m3.npy',mmap_mode='r')
    z=np.load(work/'log_density.npy',mmap_mode='r')
    index=np.load(work/'sample_field_indices.npy',mmap_mode='r')
    residual=np.load(work/'log_residuals.npy',mmap_mode='r')
    require(x.shape==z.shape==(len(field),*SHAPE) and index.shape==(len(samples),6)
            and residual.shape==(2,len(samples),3,*SHAPE),'Array shapes')
    exposure=Counter()
    for i,s in enumerate(samples):
        entry=receipts[s['event_id']]
        require(entry['run_id']==s['run_id'] and s['role']=='TRAIN','Role mismatch')
        t=at(s['cutoff_UTC'])
        c=candidates[s['event_id']]
        for j,(delta,name) in enumerate(zip((-3,-2,-1,1,3,6),('x_m3','x_m2','x_m1','y_p1','y_p3','y_p6'))):
            stamp=at(s[name])
            require(stamp-t==timedelta(hours=delta) and
                    at(c['core_start'])<=stamp<at(c['core_end_exclusive']) and
                    stamp>=at(entry['datetime_start'])+timedelta(days=14)
                    and index[i,j]==field_at[s['run_id'],s[name]],'Window roles, frame index or time support')
        exposure[s['event_id']]+=1
    require(len({s['sample_id'] for s in samples})==len(samples),'Sample identity uniqueness')
    require(len(read_csv(OUT/'train_cutoff_inventory.csv'))==11,'Fixed cutoff count')
    archive=read_csv(OUT/'training_field_receipt.csv')
    for i,r in enumerate(archive):
        require(hashlib.sha256(x[i].tobytes()).hexdigest()==r['float32_SI_SHA256']
                and np.isfinite(x[i]).all() and np.min(x[i])>0,'Slice bytes or positivity')
    verify_max=0.
    for s in range(len(samples)):
        latest=np.log(np.asarray(x[index[s,2]],dtype=np.float64))
        for j,h in enumerate(LEADS):
            y=np.log(np.asarray(x[index[s,j+3]],dtype=np.float64))
            columns=(np.arange(SHAPE[-1])+3*(h+1))%SHAPE[-1]
            expected=np.stack([y-latest,y-latest[:,:,columns]])
            verify_max=max(verify_max,float(np.max(abs(residual[:,s,j]-expected))))
    require(verify_max<5e-7,'Independent float32 residual accuracy')
    hist=np.unique(index[:,:3])
    exact=load(OUT/'train_normalization.json')['primary_unique_input_frames']
    hist_log=np.log(np.asarray(x[hist],dtype=np.float64))
    require(np.allclose(hist_log.mean(axis=(0,2,3)),exact['mean'],rtol=0,atol=6e-8)
            and np.allclose(hist_log.std(axis=(0,2,3)),exact['std'],rtol=0,atol=6e-8),
            'Independent TRAIN normalization')
    w=np.cos(np.deg2rad(coords['lat']))[None,None,:,None]
    summaries={(r['event'],int(r['horizon'])):r for r in read_csv(OUT/'residual_summary.csv')}
    for event in exposure:
        use=[i for i,s in enumerate(samples) if s['event_id']==event]
        for j,h in enumerate(LEADS):
            for k,method in enumerate(('P','LT')):
                a=residual[k,use,j].astype(float)
                rm=float(np.sqrt(np.sum(a*a*w)/(len(use)*29*72*w.sum())))
                require(abs(rm-float(summaries[event,h][method+'_RMS']))<3e-7,'Independent area RMS')
    raw=read_csv(OUT/'native_output_inventory.csv')
    require(sum(r['kind']=='primary' for r in raw)==72 and sum(r['kind']=='secondary' for r in raw)==68
            and len(read_csv(OUT/'native_time_index.csv'))==1632,'Raw count aggregation')
    write_once(OUT/'independent_verification.json',dict(all_four_PASS=True,
                  model_launch_count=4,scanned_volumes=140,hourly_frames=1632,
                  sample_count=len(samples),fields=len(field),residual_checks=6*len(samples),
                  max_residual_float32_delta=verify_max,role='TRAIN',cross_role_DEN_reads=0,
                  GPU=0,Swarm_label_reads=0,training=0))
    return samples,exposure,receipts


def plots(samples,counts,runs):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    folder=OUT/'figures'
    folder.mkdir()
    events=list(counts)
    short=list(EVENTS)
    truth=read_csv(OUT/'residual_summary.csv')
    comp={(r['event'],int(r['horizon'])):r for r in truth}
    strata={(r['event'],int(r['horizon']),r['method'],r['domain']):r
            for r in read_csv(OUT/'residual_comparison.csv')}
    fields=read_csv(OUT/'event_layer_density_stats.csv')
    kp,_,_,_=annual()
    candidates={r['event_id']:r for r in read_csv(V62/'geomagnetic_event_candidates.csv')}

    def savefig(fig,name):
        fig.suptitle('V65 TIE-GCM TRAIN | HINDCAST')
        fig.tight_layout()
        fig.savefig(folder/f'{name}.png',dpi=105,bbox_inches='tight')
        plt.close(fig)

    fig,axs=plt.subplots(2,2,figsize=(10,6))
    for e,ax in zip(events,axs.flat):
        c=candidates[e]
        times=[t for t in kp if at(c['core_start'])<=t.replace(tzinfo=None)<at(c['core_end_exclusive'])]
        ax.step(times,[kp[t] for t in times],where='post')
        ax.set(title=e,ylabel='Definitive Kp',ylim=(0,9))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %HZ'))
        ax.tick_params(axis='x',rotation=35,labelsize=7)
    savefig(fig,'event_kp')
    fig,axs=plt.subplots(1,3,figsize=(9,3.3))
    for ax,key,div,unit in zip(axs,('elapsed_s','peak_RSS_bytes','native_bytes'),(60,2**20,2**30),
                              ('Wall (min)','Sampled RSS (MiB)','Native output (GiB)')):
        ax.bar(short,[runs[e][key]/div for e in events])
        ax.set_ylabel(unit)
    savefig(fig,'run_resources')
    fig,ax=plt.subplots(figsize=(9,3.5))
    for i,e in enumerate(events):
        start=at(candidates[e]['core_start'])
        d=[s for s in samples if s['event_id']==e]
        xy=[(at(s['cutoff_UTC'])-start).total_seconds()/3600 for s in d]
        ax.scatter(xy,[i]*len(xy),marker='|',s=75)
    ax.set(yticks=range(4),yticklabels=short,xlabel='Cutoff hours after event core start')
    savefig(fig,'window_timeline')
    fig,ax=plt.subplots(figsize=(7,4))
    for e,id_ in zip(events,short):
        a=[f for f in fields if f['event']==e]
        ax.plot([int(r['level']) for r in a],[float(r['p50']) for r in a],label=id_)
    ax.set(yscale='log',xlabel='Native pressure interface index',ylabel='Median DEN (kg/m³)')
    ax.legend()
    savefig(fig,'native_density')
    fig,axs=plt.subplots(2,2,figsize=(8,6))
    for e,ax in zip(events,axs.flat):
        for b in ('P','LT'):
            ax.plot(LEADS,[float(comp[e,h][b+'_RMS']) for h in LEADS],'.-',label=b)
        ax.set(title=e,xticks=LEADS,xlabel='Lead h',ylabel='log-residual RMS')
        ax.legend()
    savefig(fig,'residual_backgrounds')
    fig,axs=plt.subplots(2,2,figsize=(9,6))
    for e,ax in zip(events,axs.flat):
        for b in ('Persistence','LocalTimePersistence'):
            ax.plot(range(29),[float(strata[e,6,b,f'ilev_{l:02}']['rms']) for l in range(29)],label=b)
        ax.set(title=e,xlabel='Native pressure interface index',ylabel='+6h log-residual RMS')
        ax.legend(fontsize=7)
    savefig(fig,'layer_residuals')
    fig,axs=plt.subplots(1,2,figsize=(8,3.5))
    metrics={(r['event'],int(r['horizon']),r['method']):r for r in read_csv(OUT/'training_baseline_metrics.csv')}
    for cls,ax in zip(('quiet','disturbed'),axs):
        for b in ('Persistence','LocalTimePersistence'):
            q=[float(metrics[cls,6,b][p]) for p in ('p1','p5','p50','p95','p99')]
            ax.plot((1,5,50,95,99),q,'.-',label=b)
        ax.axhline(0,color='gray',linewidth=.8)
        ax.set(title=cls,xlabel='Gridpoint percentile',ylabel='+6h log residual')
        ax.legend(fontsize=7)
    savefig(fig,'residual_distributions')
    fig,ax=plt.subplots(figsize=(7,3.5))
    x=np.arange(4)
    ax.bar(x-.18,[counts[e]/sum(counts.values()) for e in events],.36,label='Window equal')
    ax.bar(x+.18,[.25]*4,.36,label='Event equal')
    ax.set(xticks=x,xticklabels=short,ylabel='Exposure share')
    ax.legend()
    savefig(fig,'exposure_weights')


def main():
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    require(OUT.resolve()==OUT and not (OUT/'figures').exists(),'V65 figure directory')
    samples,counts,runs=verify()
    rows=[]
    resource={}
    for event,r in runs.items():
        rows.append(dict(event_id=event,run_id=r['run_id'],**r['forcing']))
        resource[event]={k:r[k] for k in ('run_id','final_step','elapsed_s','peak_RSS_bytes',
                         'native_bytes','CPU_user_s','CPU_system_s','warning_line_count')}
    table(OUT/'forcing_completeness.csv',rows)
    write_once(OUT/'resource_usage.json',resource)
    plots(samples,counts,runs)
    print('V65 independent training data verification and eight figures complete')


if __name__=='__main__':
    main()
