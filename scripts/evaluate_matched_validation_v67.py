"""Exact V66 validation slices, isolated forecasts, conditional one-shot scoring."""
import hashlib
import json
import os
import resource
import subprocess
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from evaluate_locked_events_v64 import score,self_test
from run_independent_predictions_v64 import extract,key,stage,sync,utc,save,sha
from run_native_density_baselines_v59 import SHAPE,need,read_csv,readonly,seal,table,worker
from score_independent_events_v64 import read_target
from check_external_evidence_v55 import check

ROOT=Path(__file__).resolve().parents[1]
V66=ROOT/'experiments/thermosphere_matched_residual_training_v66'
V65=ROOT/'experiments/thermosphere_multi_event_training_dataset_v65'
OUT=ROOT/'experiments/thermosphere_matched_validation_v67'
LOCAL=OUT/'data_local'
BASE='4634e3b9fda672758bd85cbaa73942f7837cd67f'
METHODS=('Persistence','LogLinear','LocalTimePersistence','DailyPersistence','P-Residual-CNN','LT-Residual-CNN')
SHA={'P':('7386c0282ebebd3f9dac7d0be2d58d92566fe3fdf9e35081d66d64f773b96876',
          '270f31f5ee5690d27e158e628f3ffef2cd0ffd19c75ac5e58ac8af713506f909'),
     'LT':('d8a8c97e564eaf1b4a2442e40620031ad97f2459807b7cf28dbb0b16ba5ff2d6',
           '8cf5123dc39d836520e874a6818220c48a4515a39db10032a4088a3d24d40fd8')}
RUNS={'quiet_20220301T21':'50d3c9fbdb6f43b785eaa544c637e269',
      'disturbed_20211103T21':'1d45eae9a8694415899797844ad13c70'}
LEADS=(1,3,6)
INDEX={'history':'validation_history_record_index.csv','periodic':'validation_periodic_history_index.csv',
       'target':'validation_target_record_index.csv'}


def pinned(path):
    raw=subprocess.check_output(['git','show',f'{BASE}:{path.relative_to(ROOT)}'],cwd=ROOT)
    need(path.resolve()==path and path.read_bytes()==raw,'Frozen scope mismatch: '+path.name)
    return path


def scope():
    seal_info=json.loads(pinned(V66/'validation_sealing_manifest.json').read_text())
    anchors={}
    groups=defaultdict(dict)
    inventory={(r['run_id'],r['file']):r for r in read_csv(pinned(V66/'validation_native_output_inventory.csv'))}
    verified={}
    for kind,name in INDEX.items():
        path=pinned(V66/name)
        need(len(read_csv(path))==12 and sha(path)==seal_info['SHA256'][name],'Sealed index mismatch')
        for r in read_csv(path):
            h=int(r['lead_hours'])
            offset=h-24 if kind=='periodic' else h
            a,b=utc(r['UTC']),utc(r['cutoff_UTC'])
            need(r['run_id']==RUNS[r['event_id']] and r['stage']==kind and r['DEN_access']=='SEALED'
                 and r['role']=='MODEL_SELECTION_VALIDATION' and (a-b).total_seconds()==offset*3600 and
                 h in ((-3,-2,-1) if kind=='history' else LEADS),'Wrong record type/offset')
            cid=(r['run_id'],r['cutoff_UTC'])
            bucket=groups[cid].setdefault(kind,{})
            need(h not in bucket,'Duplicate lead')
            bucket[h]=r
            vol=inventory[r['run_id'],r['file']]
            p=ROOT/r['relative_directory']/r['file']
            need(p.resolve()==p and p.stat().st_uid==0 and p.stat().st_mode&0o777==0o400 and
                 p.parent.stat().st_mode&0o777==0o500 and p.parent.parent.stat().st_mode&0o777==0o700
                 and r['volume_SHA256']==vol['sha256'] and vol['kind']=='secondary'
                 and vol['directory']==r['relative_directory'] and 0<=int(r['record'])<int(vol['records']),
                 'Source/run/record custody identity')
            if p not in verified:
                verified[p]=sha(p)
            need(verified[p]==r['volume_SHA256'],'Volume SHA mismatch')
            if kind=='target':
                need(key(r) not in anchors,'Duplicate target')
                anchors[key(r)]=r
    expected=['2021-11-04T06:00:00Z','2022-03-02T06:00:00Z','2022-03-02T18:00:00Z','2022-03-03T06:00:00Z']
    need(sorted(c[1] for c in groups)==expected and all(len(v)==3 and
         all(len(r)==3 for r in v.values()) for v in groups.values()),'Bad registered cutoff matrix')
    return groups,anchors


def protocols():
    cfg=json.loads(pinned(V66/'training_protocol.json').read_text())
    identity=json.loads(pinned(V66/'checkpoint_manifest.json').read_text())
    normalized=pinned(V66/'normalization.json')
    need(cfg['normalization_SHA256']==sha(normalized),'Model normalization packet input')
    norm=json.loads(normalized.read_text())['primary_unique_input_frames']
    packets={}
    for arm,hashes in SHA.items():
        folder=V66/'data_local'/arm
        weight,packet=folder/'checkpoint.pt',folder/'parameter_packet.bin'
        v=identity[arm]
        need(weight.resolve()==weight and packet.resolve()==packet and
             (sha(weight),sha(packet))==hashes==(v['checkpoint_SHA256'],v['packet_SHA256']) and
             v['updates']==200 and v['parameters']==1027,'Frozen model packet or checkpoint')
        packets[arm]=packet.read_bytes()
        a=np.frombuffer(packets[arm],dtype='<f8')
        need(len(a)==1085 and np.isfinite(a).all() and np.array_equal(a[1027:],norm['mean']+norm['std']),
             'Normalization is not V65 training moments')
    # Freeze missing target-based P5 using unique TRAIN target indices only.
    frozen=json.loads(pinned(V65/'training_arrays_SHA256.json').read_text())
    arr=V65/'data_local/training_arrays'
    for n in ('density_kg_m3.npy','sample_field_indices.npy'):
        need(sha(arr/n)==frozen[n]['SHA256'],'TRAIN array drift')
    x=np.load(arr/'density_kg_m3.npy',mmap_mode='r')
    i=np.unique(np.load(arr/'sample_field_indices.npy',mmap_mode='r')[:,3:])
    need(len(i)==152 and norm['frames']==140,'TRAIN-only processing')
    threshold=np.quantile(x[i],.05,axis=(0,2,3))
    return packets,identity,norm,threshold


def compile_worker(name,source,flags=()):
    path=LOCAL/name
    subprocess.run(['/usr/bin/gcc','-static','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror',
                    *flags,str(ROOT/'scripts'/source),'-lm','-o',str(path)],
                   env={'PATH':'/usr/bin:/bin','TMPDIR':str(LOCAL)},timeout=45,check=True)
    return path


def evaluate(y,p,records,lat,threshold):
    w=np.cos(np.deg2rad(lat))[None,None,:,None]
    rows=[]
    energy=[]
    for kind in ('event_id','cutoff_UTC'):
        for event in sorted({r[kind] for r in records}):
            for h in LEADS:
                use=[j for j,r in enumerate(records) if r[kind]==event and int(r['lead_hours'])==h]
                t,all_p=y[use],p[:,use]
                common=np.all(np.isfinite(all_p)&(all_p>0),axis=0)
                domains={'global':True,'south_polar':lat[None,None,:,None]<=-60,
                         'north_polar':lat[None,None,:,None]>=60,'low_density':t<=threshold[None,:,None,None]}
                domains.update({f'ilev_{i:02}':np.arange(29)[None,:,None,None]==i for i in range(29)})
                for region,domain in domains.items():
                    for label,pp in zip(METHODS,all_p):
                        for mask,valid in [('own',None),('common',common)]:
                            rows.append(dict(group_key=kind,group=event,lead=h,method=label,
                                             domain=region,mask=mask,**score(t,pp,w,domain,valid)))
                    v=np.isfinite(t)&(t>0)&common&domain
                    if not v.any():
                        continue
                    weights=np.broadcast_to(w,t.shape)[v]
                    avg=lambda x:float(np.average(x,weights=weights))
                    for arm,i,j in [('P',0,4),('LT',2,5)]:
                        r=np.log(t[v])-np.log(all_p[i][v])
                        c=np.log(all_p[j][v])-np.log(all_p[i][v])
                        rr,cc,rc=avg(r*r),avg(c*c),avg(r*c)
                        after=avg((r-c)**2)
                        gain=rr-after
                        need(abs(gain-(2*rc-cc))<2e-15,'Energy closure')
                        mr,mc=avg(r),avg(c)
                        sr,sc=avg((r-mr)**2),avg((c-mc)**2)
                        wr=avg((r-mr)*(c-mc))
                        energy.append(dict(group_key=kind,group=event,lead=h,domain=region,arm=arm,n=len(r),
                            residual_rms=rr**.5,correction_rms=cc**.5,ratio=(cc/rr)**.5 if rr else None,
                            weighted_corr=wr/(sr*sc)**.5 if sr and sc else None,
                            residual_mean=mr,correction_mean=mc,remaining_rms=after**.5,
                            remaining_log_bias=mc-mr,improved_fraction=float(np.mean(abs(r-c)<abs(r))),
                            worsened_fraction=float(np.mean(abs(r-c)>abs(r))),
                            twice_cross=2*rc,correction_energy=cc,actual_gain=gain,
                            identity_error=gain-(2*rc-cc),alpha_oracle=rc/cc if cc else None,
                            alpha_role='ORACLE_DIAGNOSTIC_ONLY'))
    # Physically independent reduction, opposite log expression, exact paired support.
    lookup={(r['group'],r['lead'],r['method']):r for r in rows if r['group_key']=='event_id'
            and r['domain']=='global' and r['mask']=='common'}
    for (event,h,m),r in lookup.items():
        i=[j for j,x in enumerate(records) if x['event_id']==event and int(x['lead_hours'])==h]
        t=y[i]
        pp=p[METHODS.index(m),i]
        use=np.isfinite(t)&(t>0)&np.all(np.isfinite(p[:,i])&(p[:,i]>0),axis=0)
        a=np.where(use,w,0)
        error=np.where(use,np.log(pp/t),0)
        need(use.sum()==r['valid_count'] and np.isclose(np.sqrt(np.sum(a*error**2)/a.sum()),r['log_rmse'],
             rtol=1e-12,atol=0),'Independent RMSE or mask')
    refs={(r['group_key'],r['group'],r['lead'],r['domain'],r['mask'],r['method']):r for r in rows}
    for k,r in refs.items():
        for base,label in [(METHODS[0],'P'),(METHODS[2],'LT'),(METHODS[3],'Daily'),(METHODS[4],'PCNN')]:
            u=refs[(*k[:-1],base)]['log_rmse']
            r['log_rmse_delta_pct_vs_'+label]=100*(r['log_rmse']/u-1) if r['log_rmse'] is not None and u else None
    for n,f in [('global',lambda r:r['group_key']=='event_id' and r['domain']=='global'),
                ('cutoff',lambda r:r['group_key']=='cutoff_UTC'),('layer',lambda r:r['domain'].startswith('ilev')),
                ('regional',lambda r:r['domain'] in ('north_polar','south_polar','low_density'))]:
        table(OUT/f'{n}_metrics.csv',[r for r in rows if f(r)])
    table(OUT/'residual_energy_decomposition.csv',energy)
    table(OUT/'oracle_alpha_diagnostics.csv',[{k:r[k] for k in ('group_key','group','lead','domain','arm',
                                                               'alpha_oracle','alpha_role')} for r in energy])
    table(OUT/'correction_amplitude_analysis.csv',[{k:r[k] for k in ('group_key','group','lead','domain','arm',
                                          'residual_rms','correction_rms','ratio','weighted_corr')} for r in energy])
    table(OUT/'two_event_macro_metrics.csv',[dict(method=m,lead=h,**{k:float(np.mean([r[k] for r in lookup.values()
                  if r['method']==m and r['lead']==h])) for k in ('log_rmse','relative_rmse','rmse')})
                  for m in METHODS for h in LEADS])
    return dict(global_recomputations=len(lookup),energy_rows=len(energy),
                max_energy_identity_error=max(abs(r['identity_error']) for r in energy))


def main():
    tick=time.monotonic()
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    need(OUT.resolve()==OUT and not OUT.exists(),'One-shot validation already reserved')
    self_test()
    groups,targets=scope()
    packets,identity,norm,threshold=protocols()
    OUT.mkdir()
    LOCAL.mkdir(mode=0o700)
    save(OUT/'execution_authorization.json',dict(stage1=['12 regular history','12 daily history'],
         stage2='12 exact model targets after verified locks and isolation; conditional user approval in V67',
         training=0,GPU=0,Swarm_reads=0,V55=check()['candidates']))
    save(OUT/'checkpoint_identity.json',identity)
    save(OUT/'frozen_evaluation_protocol.json',dict(primary='cosine latitude weighted log RMSE',
         kernel_SHA256=sha(ROOT/'scripts/evaluate_locked_events_v64.py'),entry_SHA256=sha(Path(__file__)),
         low_density_p5_unique_152_TRAIN_target_fields_kg_m3=threshold.tolist(),own_and_common=True,
         regions=['global','ilev','abs(lat)>=60 by hemisphere','low_density'],sample_scope='V66 sealed indexes'))
    executables=[compile_worker('base','baseline_worker_v67.c'),
                 compile_worker('P','matched_cnn_worker_v67.c'),
                 compile_worker('LT','matched_cnn_worker_v67.c',('-DLT_BACKGROUND',))]
    save(OUT/'frozen_method_protocol.json',dict(methods=METHODS,lead_hours=LEADS,eastward_offsets=[6,12,21],
         model_output='rho_bg*exp(c)',cnn_parameters=1027,worker_SHA256={p.name:sha(p) for p in executables},
         source_SHA256={n:sha(ROOT/'scripts'/n) for n in ('baseline_worker_v67.c','matched_cnn_worker_v67.c',
                                                        'swarm_history_worker_v57.c')}))
    sentinel=LOCAL/'future.csv'
    sentinel.write_bytes(b'synthetic future')
    probes={}
    actual_path=ROOT/next(iter(targets.values()))['relative_directory']/next(iter(targets.values()))['file']
    pattern=np.broadcast_to(np.exp(.2*np.cos((np.arange(72))[None,None,:]*2*np.pi/72)),(3,*SHAPE)).copy()
    for binary in executables:
        name=binary.name
        jail=LOCAL/f'probe_{name}'
        stage(jail,{'anchors.txt':pattern,'daily.bin':pattern},packets.get(name))
        jail.chmod(0o755)
        (jail/'escape').symlink_to(sentinel)
        jail.chmod(0o555)
        denial=worker(binary,jail,sentinel,actual_path,LOCAL/'cut_00_base/anchors.txt').decode().splitlines()
        a=worker(binary,jail)
        sentinel.write_bytes(b'synthetic future poisoned')
        need(len(denial)==12 and a==worker(binary,jail),'Isolation probe or poison')
        if name=='base':
            a=np.frombuffer(a,dtype='<f8').reshape(4,3,*SHAPE)
            for i,h in enumerate(LEADS):
                need(np.array_equal(a[2,i],np.roll(pattern[2],-3*(h+1),axis=-1)),'Longitude rotation sign')
        elif name=='LT':
            # Run the same LT checkpoint with both backgrounds on the analytic field.
            plain=np.frombuffer(worker(executables[1],jail),dtype='<f8').reshape(3,*SHAPE)
            shifted=np.frombuffer(a,dtype='<f8').reshape(3,*SHAPE)
            for i,h in enumerate(LEADS):
                need(np.allclose(shifted[i]/plain[i],np.roll(pattern[2],-3*(h+1),axis=-1)/pattern[2],
                                 rtol=3e-15),'Wrong frozen CNN background')
        sentinel.write_bytes(b'synthetic future')
        probes[name]=dict(denials=denial,synthetic_poison_invariant=True)
    locks={}
    overlaps=[]
    receipts=[]
    forecast=[]
    coords={}
    shifts=[]
    for i,cid in enumerate(sorted(groups,key=lambda c:c[1])):
        group=groups[cid]
        values={}
        for kind in ('history','periodic'):
            v=[]
            for h,r in sorted(group[kind].items()):
                prior=targets.get(key(r))
                if prior:
                    old=(prior['run_id'],prior['cutoff_UTC'])
                    need(kind=='periodic' and utc(old[1])<utc(cid[1]) and old in locks and
                         sha(locks[old][0])==locks[old][1],'Historical target overlap before lock')
                    overlaps.append(dict(current_cutoff=cid[1],prior_cutoff=old[1],UTC=r['UTC'],
                                         prior_lock_SHA256=locks[old][1],access_sequence=len(receipts)+1))
                array,receipt=extract(r,ROOT/r['relative_directory']/r['file'],coords)
                v.append(array)
                receipts.append(r | receipt | dict(access_sequence=len(receipts)+1,
                               policy='authorized late history only' if prior else 'authorized history'))
            values[kind]=np.stack(v)
        x,daily=values.values()
        streams=[]
        for binary in executables:
            name=binary.name
            jail=LOCAL/f'cut_{i:02}_{name}'
            files={'anchors.txt':x}
            if name=='base':
                files['daily.bin']=daily
            stage(jail,files,packets.get(name))
            if i==1:
                logs=worker(binary,jail,sentinel,actual_path,LOCAL/'cut_00_base/anchors.txt').decode().splitlines()
                need(len(logs)==12,'Existing other cutoff file denial failed')
                probes[name]['existing_sibling_denials']=logs
            streams.append(worker(binary,jail))
        final=np.frombuffer(b''.join(streams),dtype='<f8').reshape(6,3,*SHAPE)
        for j,h in enumerate(LEADS):
            independent=(x[2],np.exp(np.log(x[2])+(h+1)*(np.log(x[2])-np.log(x[1]))),
                         np.take(x[2],(np.arange(72)+3*(h+1))%72,axis=-1),daily[j])
            need(all(np.allclose(final[k,j],v,rtol=6e-14,atol=0) for k,v in enumerate(independent)),'Baseline formula drift')
        rows=[]
        for j,(h,r) in enumerate(sorted(group['target'].items())):
            for m,a in zip(METHODS,final[:,j]):
                payload=a.tobytes()
                fd=seal(payload)
                rel=f'{r["record_id"]}_{m}.bin'
                try:
                    path=LOCAL/rel
                    checksum=readonly(path,os.pread(fd,len(payload),0))
                    with path.open('rb') as f:os.fsync(f.fileno())
                finally:
                    os.close(fd)
                rows.append(dict(record_id=r['record_id'],method=m,lead=h,cutoff_UTC=r['cutoff_UTC'],
                                 target_UTC=r['UTC'],run_id=r['run_id'],file=rel,SHA256=checksum,n=int(a.size),
                                 nonfinite=int((~np.isfinite(a)).sum()),nonpositive=int((np.isfinite(a)&(a<=0)).sum())))
        p=LOCAL/f'cut_{i:02}_lock.json'
        hs=save(p,dict(cutoff_UTC=cid[1],access_through=len(receipts),predictions=rows))
        with p.open('rb') as f:os.fsync(f.fileno())
        sync(LOCAL)
        locks[cid]=(p,hs)
        forecast.extend(rows)
        z=np.log(x)
        for j in range(29):
            tr_mu,tr_sd=norm['mean'][j],norm['std'][j]
            zz=(z[:,j]-tr_mu)/tr_sd
            shifts.append(dict(cutoff_UTC=cid[1],run_id=cid[0],ilev=j,standardized_mean=float(zz.mean()),
                            std_ratio=float(zz.std()),outside_3sigma=float(np.mean(abs(zz)>3)),
                            median_kg_m3=float(np.median(x[:,j]))))
    need(len(receipts)==24 and len(overlaps)==3 and len(locks)==4 and len(forecast)==72,'Scope coverage')
    table(OUT/'prediction_manifest.csv',forecast)
    table(OUT/'input_distribution_shift.csv',shifts)
    save(OUT/'history_extraction_receipts.json',receipts)
    save(OUT/'temporal_overlap_audit.json',dict(overlaps=overlaps,scoring_reads_before_lock=0))
    save(OUT/'isolation_probe_results.json',probes)
    locked=save(OUT/'prediction_lock.json',dict(cutoffs={p.name:h for p,h in locks.values()},
                SHA256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},fields=72))
    rows=read_csv(OUT/'prediction_manifest.csv')
    lookup={(r['record_id'],r['method']):r for r in rows}
    ordered=sorted(targets.values(),key=lambda r:(r['cutoff_UTC'],int(r['lead_hours'])))
    need(sha(OUT/'prediction_lock.json')==locked and set(lookup)=={(t['record_id'],m) for t in ordered for m in METHODS}
         and all(sha(p)==h for p,h in locks.values()),'Prediction scope changed')
    for name,h in json.loads((OUT/'prediction_lock.json').read_text())['SHA256'].items():
        need(sha(OUT/name)==h,'Locked receipt changed')
    checked=[]
    for m in METHODS:
        arrays=[]
        for t in ordered:
            r=lookup[t['record_id'],m]
            p=LOCAL/r['file']
            need(p.resolve()==p and sha(p)==r['SHA256'] and p.stat().st_mode&0o777==0o444 and
                 t['UTC']==r['target_UTC'] and t['run_id']==r['run_id']
                 and int(r['nonfinite'])==0 and int(r['nonpositive'])==0,'Forecast final verification')
            arrays.append(np.fromfile(p,dtype='<f8').reshape(SHAPE))
        checked.append(arrays)
    save(OUT/'evaluation_authorization_receipt.json',dict(verified_prediction_lock_SHA256=locked,
         target_index_SHA256=sha(V66/INDEX['target']),isolation_verified=True,conditional_user_release=True,
         target_fields=12,prelock_current_future_reads=0,historical_overlap_reads=3))
    loaded=[read_target(r,coords) for r in ordered]
    table(OUT/'target_extraction_manifest.csv',[r for _,r in loaded])
    flat_y=np.stack([y for y,_ in loaded])
    flat_p=np.array(checked)
    readonly(LOCAL/'targets.bin',flat_y.tobytes())
    readonly(LOCAL/'forecasts.bin',flat_p.tobytes())
    verification=evaluate(flat_y,flat_p,ordered,coords['lat'],threshold)
    save(OUT/'independent_verification.json',verification | dict(predictions=72,target_reads=12,
         target_valid_cells=int(np.sum(np.isfinite(flat_y)&(flat_y>0))),prediction_nonpositive=0,
         prediction_nonfinite=0,prediction_fields=72,forecast_sha256=sha(LOCAL/'forecasts.bin'),
         target_sha256=sha(LOCAL/'targets.bin'),Swarm_reads=0,timing_s=time.monotonic()-tick,
         max_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
    print('VALIDATION_SCORED',flush=True)


if __name__=='__main__':
    main()
