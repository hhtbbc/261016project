"""Final TRAIN_DIAGNOSTIC scores and matched-arm independent verification."""
import hashlib
import os

import numpy as np

from train_matched_residual_v66 import OUT,LOCAL,TRAIN,ARRAYS,LEADS,ARMS,SHAPE,BASE,ROOT
from run_training_events_v65 import sha,require,load,write_once
from run_native_density_baselines_v59 import read_csv,table

METHODS=('Persistence','LogLinear','LocalTimePersistence','P-Residual-CNN','LT-Residual-CNN')


def metrics(target,forecast,w,mask):
    mask=mask&np.isfinite(forecast)&np.isfinite(target)
    e=forecast[mask]-target[mask]
    weights=np.broadcast_to(w,target.shape)[mask]
    a=np.exp(forecast[mask])-np.exp(target[mask])
    if not len(e):
        return dict(n=0,log_rmse=None,relative_rmse=None,rmse=None,log_mae=None,log_bias=None)
    avg=lambda x:float(np.average(x,weights=weights))
    return dict(n=len(e),log_rmse=avg(e**2)**.5,relative_rmse=avg(np.expm1(e)**2)**.5,
                rmse=avg(a**2)**.5,log_mae=avg(abs(e)),log_bias=avg(e))


def main():
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    require(OUT.resolve()==OUT,'Unsafe output path')
    cfg=load(OUT/'training_protocol.json')
    receipt=load(OUT/'checkpoint_manifest.json')
    init=load(OUT/'model_initialization_receipt.json')
    seq=read_csv(OUT/'shared_sampling_sequence.csv')
    require(len(seq)==200 and sha(OUT/'shared_sampling_sequence.csv')==cfg['sampling_SHA256']
            and sha(LOCAL/'initial.pt')==init['initial_checkpoint_SHA256'],'Sequence or initialization drift')
    logs=read_csv(OUT/'training_log.csv')
    for arm in ARMS:
        r=receipt[arm]
        actual=[(x['step'],x['sample_id']) for x in logs if x['arm']==arm]
        require(len(actual)==200 and actual==[(a['step'],a['sample_id']) for a in seq]
                and r['initial_vector_SHA256']==init['initial_vector_SHA256']
                and r['sequence_SHA256']==cfg['sampling_SHA256'] and r['updates']==200 and r['parameters']==1027
                and r['step0_exact_background'] and r['checkpoint_recovered']
                and sha(LOCAL/arm/'checkpoint.pt')==r['checkpoint_SHA256']
                and sha(LOCAL/arm/'parameter_packet.bin')==r['packet_SHA256']
                and sha(LOCAL/arm/'correction.npy')==r['correction_SHA256'],'Matched-arm evidence')
    require(receipt['LT']['exposure']==receipt['P']['exposure'],'Exposure mismatch')
    samples=read_csv(TRAIN/'hourly_training_sample_manifest.csv')
    x=np.load(ARRAYS/'density_kg_m3.npy',mmap_mode='r')
    idx=np.load(ARRAYS/'sample_field_indices.npy',mmap_mode='r')
    field=np.log(x.astype(np.float64))
    z0,z1=field[idx[:,2]],field[idx[:,1]]
    delta={a:np.load(LOCAL/a/'correction.npy',mmap_mode='r') for a in ARMS}
    coords=load(TRAIN/'data_quality_report.json')['coordinates']
    lat=np.asarray(coords['lat'])
    w=np.cos(np.deg2rad(lat))[None,None,:,None]
    p5=np.log(load(TRAIN/'train_normalization.json')['low_density_p5_unique_train_inputs'])[None,:,None,None]
    groups={e:np.array([i for i,s in enumerate(samples) if s['event_id']==e])
            for e in sorted({s['event_id'] for s in samples})}
    groups.update({e:np.array([i for i,s in enumerate(samples) if s['event_id'].startswith(e)])
                   for e in ('quiet','disturbed')})
    groups['ALL']=np.arange(len(samples))
    domains=dict(global_=True,north_polar=lat[None,None,:,None]>=60,south_polar=lat[None,None,:,None]<=-60)
    domains.update({f'ilev_{l:02}':np.arange(29)[None,:,None,None]==l for l in range(29)})
    mrows=[]
    crows=[]
    check_max=0.
    v65={(r['event'],int(r['horizon']),r['method']):float(r['rms'])
         for r in read_csv(TRAIN/'training_baseline_metrics.csv')}
    for j,h in enumerate(LEADS):
        truth=field[idx[:,j+3]]
        p=z0
        lt=np.take(z0,(np.arange(72)+3*(h+1))%72,axis=-1)
        guesses=(p,z0+(h+1)*(z0-z1),lt,p+delta['P'][:,j],lt+delta['LT'][:,j])
        for event,i in groups.items():
            t=truth[i]
            for region,mask in (*domains.items(),('low_density',t<=p5)):
                label='global' if region=='global_' else region
                mask=np.broadcast_to(mask,t.shape)
                rows=[]
                for method,pred in zip(METHODS,guesses):
                    r=metrics(t,pred[i],w,mask)
                    rows.append(dict(event=event,horizon=h,domain=label,method=method,role='TRAIN_DIAGNOSTIC',
                                     windows=len(i),coverage=r['n']/mask.sum() if mask.any() else None,**r))
                    if label=='global' and method in METHODS[:3]:
                        check_max=max(check_max,abs(r['log_rmse']-v65[event,h,method]))
                for r in rows:
                    refs={m['method']:m for m in rows}
                    for other,short in [('Persistence','P'),('LocalTimePersistence','LT'),('P-Residual-CNN','PCNN')]:
                        v,r0=r['log_rmse'],refs[other]['log_rmse']
                        r[f'log_rmse_change_pct_vs_{short}']=100*(v/r0-1) if v is not None and r0 else None
                mrows.extend(rows)
                if not mask.any():
                    continue
                weights=np.broadcast_to(w,t.shape)[mask]
                rms=lambda arr:float(np.sqrt(np.average(arr[mask]**2,weights=weights)))
                for a,b in [('P',p),('LT',lt)]:
                    r=rms(t-b[i])
                    c=rms(delta[a][i,j].astype('f8'))
                    crows.append(dict(event=event,horizon=h,domain=label,arm=a,role='TRAIN_DIAGNOSTIC',
                                      correction_rms=c,true_residual_rms=r,ratio=c/r if r else None))
    require(check_max<3e-7,'Baseline diagnostic reproduction drift')
    for name,rows in [('train_diagnostic_metrics.csv',[r for r in mrows if r['domain']=='global']),
                      ('layer_metrics.csv',[r for r in mrows if r['domain'].startswith('ilev')]),
                      ('regional_metrics.csv',[r for r in mrows if r['domain'] in ('low_density','north_polar','south_polar')]),
                      ('correction_amplitude_analysis.csv',crows)]:
        table(OUT/name,rows)
    write_once(OUT/'independent_verification.json',dict(parameters_each=1027,updates_each=200,
               matched_initial_and_sequence=True,checkpoint_restore_and_zero_correction_at_step0=True,
               V65_baseline_max_abs_log_RMS_diff=check_max,validation_DEN_reads=0,
               validated_train_windows=len(samples),forecast_diagnostic_rows=len(mrows),training_GPU=0))
    val=load(OUT/'validation_run_receipts.json')
    write_once(OUT/'resource_usage.json',dict(training=receipt,validation={k:{a:r[a] for a in
               ('run_id','elapsed_s','peak_RSS_bytes','native_bytes','CPU_user_s','CPU_system_s')} for k,r in val.items()}))
    plots(mrows,logs)
    print('TRAIN_DIAGNOSTICS_COMPLETE',flush=True)


def plots(metrics,logs):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder=OUT/'figures'
    folder.mkdir()
    fig,axs=plt.subplots(1,2,figsize=(10,4))
    for a,ax in zip(ARMS,axs):
        row=[r for r in logs if r['arm']==a]
        ax.plot([int(x['step']) for x in row],[float(x['loss']) for x in row],alpha=.7)
        ax.set(title=a,xlabel='CPU optimizer update',ylabel='Sample log MAE')
    fig.tight_layout()
    fig.savefig(folder/'training_loss.png',dpi=110)
    plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(12,4))
    for e,ax in zip(('ALL','quiet','disturbed'),axs):
        for m in METHODS:
            r=[r for r in metrics if r['event']==e and r['domain']=='global' and r['method']==m]
            ax.plot(LEADS,[v['log_rmse'] for v in r],'.-',label=m)
        ax.set(title=e,xlabel='Forecast lead h',ylabel='Log RMSE',xticks=LEADS)
    axs[0].legend(fontsize=7)
    fig.suptitle('V66 TRAIN_DIAGNOSTIC')
    fig.tight_layout()
    fig.savefig(folder/'train_log_rmse.png',dpi=110)
    plt.close(fig)


if __name__=='__main__':
    main()
