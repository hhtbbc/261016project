"""V64-A trusted history extractor and one-shot coordinator. No target DEN loader."""
import hashlib
import json
import os
import resource
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from netCDF4 import Dataset, num2date

from evaluate_locked_events_v64 import self_test
from run_native_density_baselines_v59 import (SHAPE, need, read_csv, readonly, seal,
                                             table, worker)

ROOT=Path(__file__).resolve().parents[1]
V63=ROOT/'experiments/thermosphere_independent_event_cpu_execution_v63'
V62=ROOT/'experiments/thermosphere_independent_event_production_v62'
V60=ROOT/'experiments/thermosphere_tiny_direct_cpu_v60'
OUT=ROOT/'experiments/thermosphere_independent_event_prediction_v64'
LOCAL=OUT/'data_local'
LEADS=(1,3,6)
METHODS=('Persistence','TwoFrameLinear','LogLinear','ThreeFrameOLSLog','DampedLogTrend',
         'LocalTimePersistence','DailyPersistence','TinyDirectCNN')
RUNS={'quiet_20230502T12':'9438b5d05e764dcc8cc8c37cb7a89e97',
      'disturbed_20230520T00':'3d4514d73a864f3d9aab5fc1475aed81'}
BASE='2ca02f5b961545015fdd8d9f512f92de0be262c2'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(2**20),b''):
            h.update(chunk)
    return h.hexdigest()


def save(path,obj):
    return readonly(path,(json.dumps(obj,indent=2,allow_nan=False)+'\n').encode())


def frozen(path):
    expected=subprocess.check_output(['git','show',f'{BASE}:{path.relative_to(ROOT)}'],cwd=ROOT)
    need(path.read_bytes()==expected,f'V63 commit mismatch: {path.name}')
    return hashlib.sha256(expected).hexdigest()


def key(r):
    return (r['run_id'],r['file'],int(r['record']))


def utc(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))


def sync(directory):
    fd=os.open(directory,os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def extract(row,path,coordinates):
    with Dataset(path) as nc:
        den=nc['DEN']
        need(den.dimensions==('time','ilev','lat','lon') and den.shape[1:]==SHAPE
             and den.units=='g/cm3' and not {'scale_factor','add_offset'}&set(den.ncattrs()),
             'Native DEN identity')
        t=nc['time']
        index=int(row['record'])
        need(0<=index<len(t) and num2date(t[index],t.units).isoformat()+'Z'==row['UTC'],
             'Native record time mismatch')
        for name in ('ilev','lat','lon'):
            axis=np.asarray(nc[name][:],dtype=float)
            need(np.isfinite(axis).all() and (np.diff(axis)>0).all()
                 and (name not in coordinates or np.array_equal(axis,coordinates[name])),name)
            coordinates[name]=axis
        need(np.array_equal(coordinates['lat'],np.arange(-87.5,90,5)) and
             np.array_equal(np.diff(np.r_[coordinates['lon'],coordinates['lon'][0]+360]),np.full(72,5)),
             'Wrong native grid')
        den.set_auto_maskandscale(False)
        raw=np.asarray(den[index,:,:,:])
        fills=np.asarray([getattr(den,n) for n in ('_FillValue','missing_value') if n in den.ncattrs()],
                         dtype=raw.dtype).ravel()
        missing=np.isin(raw,fills)
        invalid=~np.isfinite(raw)|(raw<=0)|missing
        need(not invalid.any(),'Unusable authorized history')
        field=(raw.astype(float)*1000).astype('<f8')
        return field,dict(raw_slice_SHA256=hashlib.sha256(raw.tobytes()).hexdigest(),
                          converted_slice_SHA256=hashlib.sha256(field.tobytes()).hexdigest(),
                          invalid_count=int(invalid.sum()),fill_count=int(missing.sum()))


def reference(x,daily,h):
    a,b,c=x
    dt=h+1
    logs=np.log(x)
    # Independent least-squares normal equations at time -3,-2,-1.
    beta=np.linalg.pinv(np.array([[1.,-3],[1.,-2],[1.,-1]])) @ logs.reshape(3,-1)
    trend=(beta[0]+h*beta[1]).reshape(SHAPE)
    slope=beta[1].reshape(SHAPE)
    return (c,c+dt*(c-b),c**(dt+1)/b**dt,np.exp(trend),
            c*np.exp(3*(1-np.exp(-dt/3))*slope),
            np.take(c,(np.arange(72)+3*dt)%72,axis=-1),daily)


def stage(jail,arrays,packet=None):
    jail.mkdir(mode=0o755)
    for name,payload in arrays.items():
        readonly(jail/name,payload.tobytes())
    if packet is not None:
        readonly(jail/'model.bin',packet)
    jail.chmod(0o555)


def main():
    started=time.monotonic()
    os.umask(0o022)
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    need(Path.cwd().resolve()==ROOT and OUT.resolve()==OUT and not OUT.exists(),'Unexpected output path')
    kinds={'history':'history_record_index.csv','periodic':'optional_periodic_history_index.csv',
           'target':'target_record_index.csv','cutoff':'cutoff_inventory.csv'}
    pins={k:frozen(V63/v) for k,v in kinds.items()}
    for p in (V63/'next_stage_evaluation_authorization.json',V63/'target_sealing_manifest.json',
              V62/'new_baseline_protocol.json',V62/'low_density_thresholds.json',
              V60/'normalization.json',V60/'training_receipt.json'):
        pins[p.name]=frozen(p)
    scope={k:read_csv(V63/v) for k,v in kinds.items()}
    cuts=sorted(scope['cutoff'],key=lambda r:r['cutoff_UTC'])
    need(len(cuts)==7 and len({r['cutoff_id'] for r in cuts})==7,'Cutoff identity')
    expected={'quiet_20230502T12':['05-02T18','05-03T06','05-03T18','05-04T06'],
              'disturbed_20230520T00':['05-20T06','05-20T18','05-21T06']}
    need({e:[r['cutoff_UTC'][5:13] for r in cuts if r['event_id']==e] for e in RUNS}==expected
         and all(r['cutoff_UTC'].startswith('2023-') for r in cuts),'Wrong prescribed cutoffs')
    by=defaultdict(list)
    for kind in ('history','periodic','target'):
        need(len(scope[kind])==21,'Expected 21 records per scope')
        for r in scope[kind]:
            lead=int(r['lead_hours'])
            cid=r['cutoff_id']
            matches=[c for c in cuts if c['cutoff_id']==cid]
            need(len(matches)==1 and all(matches[0][k]==r[k] for k in ('event_id','run_id','cutoff_UTC'))
                 and RUNS[r['event_id']]==r['run_id'] and r['stage']==kind,'Cutoff/record mismatch')
            offset=lead-24 if kind=='periodic' else lead
            need(utc(r['UTC'])==utc(r['cutoff_UTC'])+timedelta(hours=offset),'Wrong relative time')
            by[cid,kind].append(r)
        for c in cuts:
            group=by[c['cutoff_id'],kind]
            group.sort(key=lambda r:int(r['lead_hours']))
            need(tuple(int(r['lead_hours']) for r in group)==((-3,-2,-1) if kind=='history' else LEADS),
                 'Wrong horizon scope')
    targets={key(r):r for r in scope['target']}
    need(len(targets)==21,'Duplicated target')
    verified={}
    for r in scope['history']+scope['periodic']:
        qd='q' if r['event_id'].startswith('quiet') else 'd'
        parent=V63/'data_local'/qd
        path=parent/r['file']
        need(path.name==r['file'] and path.resolve()==path
             and str(parent.relative_to(ROOT))==r['relative_directory']
             and path.is_file() and path.stat().st_uid==0 and path.stat().st_mode&0o777==0o400
             and parent.stat().st_mode&0o777==0o500 and parent.parent.stat().st_mode&0o777==0o700,
             'Custody or native path mismatch')
        if path not in verified:
            verified[path]=sha(path)
        need(verified[path]==r['volume_SHA256'],'Volume mismatch')
    contract=json.loads((V63/'next_stage_evaluation_authorization.json').read_text())
    train=json.loads((V60/'training_receipt.json').read_text())
    packet_path=V60/'data_local/model.bin'
    for path,hash_value in [(packet_path,train['packet_SHA256']),
                            (V60/'data_local/weights.pt',contract['V60_checkpoint_SHA256']),
                            (V60/'normalization.json',contract['V60_normalization_SHA256'])]:
        need(sha(path)==hash_value,f'Model bundle drift: {path.name}')
    packet=packet_path.read_bytes()
    self_test()
    OUT.mkdir()
    LOCAL.mkdir(mode=0o700)
    save(OUT/'phase_1_authorization.json',dict(index_SHA256=pins,regular_history=21,daily_history=21,
         scoring_target_DEN=0,scope='Separate V64-A authorizations, exact indexed records only'))
    save(OUT/'frozen_method_protocol.json',dict(methods=METHODS,leads=LEADS,shape=SHAPE,dtype='<f8',
         unit='kg/m3',worker_source_SHA256={p:sha(ROOT/'scripts'/p) for p in
             ('event_worker_v64.c','tiny_direct_worker_v60.c','swarm_history_worker_v57.c')},
         checkpoint_SHA256=contract['V60_checkpoint_SHA256'],normalization_SHA256=contract['V60_normalization_SHA256'],
         model_packet_SHA256=train['packet_SHA256'],tau_hours=3,eastward_source_cells=[6,12,21]))
    save(OUT/'frozen_evaluation_protocol.json',dict(primary='cos(latitude) weighted log RMSE',
         relative_rmse='sqrt(weighted mean squared pointwise relative error)',p95='weighted empirical CDF',
         masks=['own positive finite','all methods positive finite'],nonpositive='report separately',
         stratification=['event','cutoff','horizon','native ilev','north/south polar >=60','fixed V62 low-density P5'],
         low_density_SHA256=pins['low_density_thresholds.json'],macro='arithmetic mean of two event metrics',
         residual='log(target)-log(prediction); negate log bias and reverse log-error quantiles',
         compare_to=['Persistence','LocalTimePersistence']))
    save(OUT/'evaluation_code_SHA256.json',
         {'scripts/evaluate_locked_events_v64.py':sha(ROOT/'scripts/evaluate_locked_events_v64.py')})
    binaries={}
    for name in ('event_worker_v64','tiny_direct_worker_v60'):
        binary=LOCAL/name
        subprocess.run(['/usr/bin/gcc','-static','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror',
                        str(ROOT/'scripts'/f'{name}.c'),'-lm','-o',str(binary)],
                       env={'PATH':'/usr/bin:/bin','TMPDIR':str(LOCAL)},check=True,timeout=45)
        binaries[name]=binary
    base,cnn=binaries.values()
    # Exercise both real worker executables before giving either real history.
    sentinel=LOCAL/'future.csv'
    sentinel.write_bytes(b'synthetic placeholder')
    probe_jail=LOCAL/'probe'
    synth=np.broadcast_to(np.exp(.2*np.cos(np.arange(72)*2*np.pi/72)),(3,*SHAPE)).copy()
    stage(probe_jail,{'anchors.txt':synth,'daily.bin':synth},packet)
    probe_jail.chmod(0o755)
    (probe_jail/'escape').symlink_to(sentinel)
    probe_jail.chmod(0o555)
    raw_path=next(iter(verified))
    missing_isolated_sibling=LOCAL/'history_01'/'anchors.txt'
    probe_results={}
    for binary in (base,cnn):
        result=worker(binary,probe_jail,sentinel,raw_path,missing_isolated_sibling).decode().splitlines()
        need(len(result)==12,'Isolation probe mismatch')
        earlier=worker(binary,probe_jail)
        sentinel.write_bytes(b'poisoned synthetic future outside jail')
        need(worker(binary,probe_jail)==earlier,'Future poison influenced output')
        if binary==base:
            data=np.frombuffer(earlier,dtype='<f8').reshape(7,3,*SHAPE)
            for i,h in enumerate(LEADS):
                expected_axis=np.exp(.2*np.cos((np.arange(72)+3*(h+1))*2*np.pi/72))
                need(np.allclose(data[5,i,0,0],expected_axis,rtol=1e-14),'Rotation direction or seam')
        sentinel.write_bytes(b'synthetic placeholder')
        probe_results[binary.name]=dict(rejections=result,poison_invariant=True,worker_SHA256=sha(binary))
    save(OUT/'isolation_probe_results.json',probe_results)
    locks={}
    overlap=[]
    access=[]
    forecasts=[]
    coordinates={}
    max_rel=0.
    for seq,c in enumerate(cuts):
        cid=c['cutoff_id']
        arrays={}
        for kind in ('history','periodic'):
            fields=[]
            for r in by[cid,kind]:
                t=targets.get(key(r))
                if t:
                    earlier=locks.get(t['cutoff_id'])
                    need(earlier is not None and utc(t['cutoff_UTC'])<utc(c['cutoff_UTC'])
                         and sha(earlier[0])==earlier[1],'Earlier prediction must be locked before extraction')
                    overlap.append(dict(access_cutoff=cid,stage=kind,record_UTC=r['UTC'],
                                        earlier_cutoff=t['cutoff_id'],earlier_record_id=t['record_id'],
                                        earlier_lock_SHA256=earlier[1],access_sequence=len(access)+1))
                field,receipt=extract(r,ROOT/r['relative_directory']/r['file'],coordinates)
                fields.append(field)
                access.append(r | receipt | dict(sequence=len(access)+1,earlier_target_overlap=bool(t)))
            arrays[kind]=np.stack(fields)
        x,daily=arrays.values()
        shared=LOCAL/f'history_{seq:02}'
        cnn_jail=LOCAL/f'cnn_{seq:02}'
        stage(shared,{'anchors.txt':x,'daily.bin':daily})
        stage(cnn_jail,{'anchors.txt':x},packet)
        if seq==1:
            # Both paths exist here. The worker must fail to traverse to cutoff 0.
            previous=LOCAL/'history_00'/'anchors.txt'
            for binary,jail in [(base,shared),(cnn,cnn_jail)]:
                out=worker(binary,jail,sentinel,raw_path,previous).decode().splitlines()
                need(len(out)==12,'Cross-cutoff access probe failed')
                probe_results[binary.name]['actual_sibling_rejections']=out
        b=worker(base,shared)
        d=worker(cnn,cnn_jail)
        need(len(b)==7*3*np.prod(SHAPE)*8 and len(d)==3*np.prod(SHAPE)*8,'Worker output size')
        predictions=np.frombuffer(b+d,dtype='<f8').reshape(8,3,*SHAPE)
        for i,h in enumerate(LEADS):
            for j,ref in enumerate(reference(x,daily[i],h)):
                arr=predictions[j,i]
                need(np.allclose(arr,ref,rtol=2e-12,atol=1e-28),'Independent forecast formula mismatch')
                max_rel=max(max_rel,float(np.max(abs(arr-ref)/np.maximum(abs(ref),1e-28))))
        rows=[]
        for j,name in enumerate(METHODS):
            for i,r in enumerate(by[cid,'target']):
                arr=predictions[j,i]
                filename=f'{r["record_id"]}_{name}.bin'
                path=LOCAL/filename
                payload=arr.tobytes()
                fd=seal(payload)
                try:
                    checksum=readonly(path,os.pread(fd,len(payload),0))
                    with path.open('rb') as f:
                        os.fsync(f.fileno())
                finally:
                    os.close(fd)
                finite=np.isfinite(arr)
                nonpositive=int((finite&(arr<=0)).sum())
                nonfinite=int((~finite).sum())
                rows.append(dict(event_id=r['event_id'],cutoff_id=cid,cutoff_UTC=r['cutoff_UTC'],
                                 target_UTC=r['UTC'],record_id=r['record_id'],lead_hours=LEADS[i],
                                 method=name,file=f'data_local/{filename}',SHA256=checksum,
                                 nonpositive=nonpositive,nonfinite=nonfinite,n=arr.size,
                                 coverage=1-(nonpositive+nonfinite)/arr.size))
        lock_path=LOCAL/f'cutoff_{seq:02}_lock.json'
        lock_sha=save(lock_path,dict(cutoff=cid,access_through=len(access),predictions=rows))
        with lock_path.open('rb') as f:
            os.fsync(f.fileno())
        sync(LOCAL)
        locks[cid]=(lock_path,lock_sha)
        forecasts.extend(rows)
    need(len(forecasts)==168 and len(access)==42,'Incomplete run')
    table(OUT/'prediction_manifest.csv',forecasts)
    for kind,name in [('history','approved_history_manifest.csv'),('periodic','approved_periodic_history_manifest.csv')]:
        table(OUT/name,[r for r in access if r['stage']==kind])
    save(OUT/'native_coordinates.json',{k:v.tolist() for k,v in coordinates.items()})
    save(OUT/'history_extraction_receipt.json',dict(regular=21,periodic=21,target_scoring_reads=0,
         native_units='g/cm3',output_units='kg/m3',conversion=1000,verified_volumes=len(verified),
         raw_record_identity='run, volume SHA, zero-based record and UTC',invalid_cells=0))
    save(OUT/'temporal_overlap_audit.json',dict(overlaps=overlap,exact_sequence=True,target_scoring_reads=0))
    save(OUT/'cross_cutoff_probe_results.json',probe_results)
    save(OUT/'prediction_sha256.json',{r['file']:r['SHA256'] for r in forecasts})
    save(OUT/'independent_verification.json',dict(baseline_formula_checks=147,maximum_relative_difference=max_rel,
         cnn='V60 worker unchanged and pinned packet, weight and normalization SHA',synthetic_evaluation='PASS',
         synthetic_rotation_and_seam='PASS',target_values_for_evaluation_read=0))
    save(OUT/'next_phase_authorization_request.json',dict(authorization='AWAITING_NEW_EXPLICIT_V64_B',
         target_index=str((V63/kinds['target']).relative_to(ROOT)),target_index_SHA256=pins['target'],
         exact_records=21,model_DEN_only=True))
    save(OUT/'resource_usage.json',dict(elapsed_seconds=time.monotonic()-started,
         coordinator_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
         child_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
         work_bytes=sum(p.stat().st_size for p in LOCAL.rglob('*') if p.is_file()),
         CPU_affinity=len(os.sched_getaffinity(0)),GPU=0))
    save(OUT/'prediction_lock.json',dict(state='V64_A_PREDICTIONS_LOCKED_AWAITING_V64_B',methods=METHODS,
         forecasts=168,cutoffs=7,grid_values=168*int(np.prod(SHAPE)),target_scoring_reads=0,
         cutoff_locks={k:{'file':str(p.relative_to(OUT)),'SHA256':h} for k,(p,h) in locks.items()},
         artifact_SHA256={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file()}))
    print(sha(OUT/'prediction_lock.json'))


if __name__=='__main__':
    main()
