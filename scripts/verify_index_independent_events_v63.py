"""Independent scalar/header-only audit, archived metadata indexing and denied-open probe."""
from collections import defaultdict
from datetime import timedelta,timezone
import errno
import hashlib
import math
import os
import subprocess
import sys

from netCDF4 import Dataset,num2date
import numpy as np

from atmosphere.autumn_gpi_validation import independent_at
from check_external_evidence_v55 import check
from run_independent_events_v63 import (ROOT,V37,V62,OUT,PRIVATE,EVENTS,G,H,at,utc,load,sha,
    require,write_once,pin,annual,frozen)
from runtime.tiegcm_rank_exit import digest


def csvwrite(name,rows):
    import csv
    with (OUT/name).open('x',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]),lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def blocked_open(path):
    body="""import os,sys
try:
 fd=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW)
except PermissionError:
 sys.exit(13)
else:
 os.close(fd)
 sys.exit(1)
"""
    child=subprocess.run([sys.executable,'-I','-B','-c',body,str(path)],cwd=ROOT,
        user=65534,group=65534,extra_groups=[],stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,close_fds=True,timeout=10)
    require(child.returncode==errno.EACCES,'Real different-UID open probe did not get EACCES')


def inspect(receipt,plan,solar,kp, *, private=PRIVATE):
    run=ROOT/receipt['directory']
    require(run.resolve()==run and private.stat().st_uid==run.stat().st_uid==0
      and private.stat().st_mode&0o777==0o700 and run.stat().st_mode&0o777==0o500,'Custody modes')
    status=load(run/'status.json')
    require(digest(run/'status.json')==receipt['status_sha256'] and status['returncode']==0
         and status['wait_source']=='direct subprocess.Popen.wait' and status['cleanup_verified'],'Parent identity')
    event=plan['event_id']
    rid=receipt['run_id']
    days=[at(plan['start']).replace(tzinfo=timezone.utc)+timedelta(days=d) for d in range(-2,plan['days']+3)]
    means={t:math.fsum(solar[t+timedelta(days=d)] for d in range(-40,41))/81 for t in days}
    inventory={v['file']:v for v in receipt['files']}
    closed=defaultdict(list)
    anchors={}
    worst={}
    for name,e in sorted(inventory.items()):
        path=run/name
        require(path.stat().st_size==e['bytes'] and digest(path)==e['sha256'] and
                 path.stat().st_uid==0 and path.stat().st_mode&0o777==0o400,'Frozen output byte or access drift')
        with Dataset(path) as nc:
            v=nc['time']
            time_axis=num2date(v[:],v.units)
            kind=e['kind']
            for idx,t in enumerate(time_axis):
                time=t.isoformat()+'Z'
                closed[kind].append(time)
                if kind=='secondary':
                    require(nc['DEN'].dimensions==('time','ilev','lat','lon') and nc['DEN'].units=='g/cm3'
                            and nc['DEN'].shape[1:]==(29,36,72),'DEN metadata drift')
                    # Allowed scalar drivers and calendar variables only. No DEN/other field slices.
                    expected=independent_at(at(time).replace(tzinfo=timezone.utc),solar,means,kp)
                    for k,val in expected.items():
                        diff=abs(float(nc[k][idx])-val)
                        require(np.isfinite(diff) and diff<1e-10,'Actual scalar driver mismatch '+k)
                        worst[k]=max(diff,worst.get(k,0.))
                    key=(event,time)
                    require(key not in anchors,'Duplicate hourly UTC')
                    anchors[key]=dict(event_id=event,run_id=rid,UTC=time,file=name,record=idx,volume_SHA256=e['sha256'])
    start=at(plan['start'])
    for kind,step,n,offset in [('primary',timedelta(days=1),plan['primary_volumes'],0),
                               ('secondary',H,plan['hourly_DEN_frames'],1)]:
        expected=[utc(start+(i+offset)*step) for i in range(n)]
        require(closed[kind]==expected,'Independent timeline differs')
    for rank in range(4):
        r=load(run/f'rank_{rank:03d}_exit.json')
        require(r['rank']==rank and r['run_id']==rid and r['returncode']==0 and r['size']==4 and
                r['child_sid']==status['identity']['sid'] and r['input_SHA256']==receipt['input_SHA256']['input.inp'],
                'Independent rank validation')
    require(load(run/'launch_once.json')['launch_count']==1 and
            len([r for r in (run/'events.jsonl').read_text().splitlines() if json_event(r)=='launched'])==1,
            'One actual launcher event')
    blocked_open(run/'secondary_001.nc')
    return anchors,worst


def json_event(line):
    import json
    return json.loads(line)['event']


def identifier(*parts):
    return hashlib.sha256('|'.join(parts).encode()).hexdigest()


def main():
    pin(V37)
    kp,solar,_,_=annual()
    plans=frozen('next_stage_execution_authorization.json')['runs']
    receipts=[]
    volume_rows=[]
    all_times=[]
    cutoffs=[]
    stages={k:[] for k in ('history','target','periodic')}
    verification={}
    for key,plan in zip(EVENTS,plans):
        path=OUT/f'{key}_run_receipt.json'
        if not path.is_file():
            verification[key]=dict(engineering='NO_PASS_RECEIPT',sealed=PRIVATE.is_dir())
            continue
        receipt=load(path)
        index,errors=inspect(receipt,plan,solar,kp)
        all_times.extend(index.values())
        receipts.append(receipt)
        eid=plan['event_id']
        volume_rows.extend(dict(**r,relative_directory=receipt['directory']) for r in receipt['files'])
        verification[key]=dict(engineering='PASS',launches=1,run_id=receipt['run_id'],final_step=receipt['final_step'],
                              hourly_frames=len(index),runtime_GPI_max_abs=errors,unprivileged_open_errno=13)
        for c in plan['cutoff_UTC']:
            cid=identifier('V63',eid,receipt['run_id'],c)
            cutoffs.append(dict(event_id=eid,run_id=receipt['run_id'],cutoff_id=cid,cutoff_UTC=c,classification='LOCKED_INDEPENDENT_TEST_CANDIDATE'))
            for gr,offsets in [('history',(-3,-2,-1)),('target',(1,3,6)),('periodic',(1,3,6))]:
                for h in offsets:
                    t=utc(at(c)+H*(h-(24 if gr=='periodic' else 0)))
                    native=index[eid,t]
                    stages[gr].append(dict(**native,cutoff_UTC=c,cutoff_id=cid,lead_hours=h,
                         record_id=identifier(cid,gr,str(h)),relative_directory=receipt['directory'],stage=gr,
                         V63_access='DEN_SEALED'))
    n=len(receipts)
    require(n>0,'No successful engineering receipts for indexed seal')
    csvwrite('native_output_inventory.csv',volume_rows)
    write_once(OUT/'native_output_sha256.json',{r['relative_directory']+'/'+r['file']:r['sha256'] for r in volume_rows})
    csvwrite('native_time_index.csv',all_times)
    csvwrite('cutoff_inventory.csv',cutoffs)
    csvwrite('target_record_index.csv',stages['target'])
    csvwrite('history_record_index.csv',stages['history'])
    csvwrite('optional_periodic_history_index.csv',stages['periodic'])
    require(len(stages['history'])==len(stages['target'])==len(stages['periodic'])==3*len(cutoffs),'Incomplete forecast indexing')
    if n==2:
        require(len(cutoffs)==7 and len(stages['target'])==21 and len(volume_rows)==72 and len(all_times)==840,'Pair coverage')
        require(len({r['run_id'] for r in receipts})==2 and at(receipts[0]['exit_UTC'])<=at(receipts[1]['launch_UTC']),
                'Serial start order')
    write_once(OUT/'target_sealing_manifest.json',dict(DEN_access='SEALED_ALL_NATIVE_RECORDS',
        root_directory_mode='0700',run_directory_mode='0500',native_file_mode='0400',owner_uid=0,
        unprivileged_UID=65534,unprivileged_open_denied_per_run=n,root_trusted_custody=True,
        note='No claim to constrain privileged custodians. V64 needs a true process boundary and a history-only staging directory.',
        history_index_SHA256=sha(OUT/'history_record_index.csv'),target_index_SHA256=sha(OUT/'target_record_index.csv')))
    v60=ROOT/'experiments/thermosphere_tiny_direct_cpu_v60'
    from run_event_baselines_v62 import OUT as O62
    write_once(OUT/'next_stage_evaluation_authorization.json',dict(state='NOT_AUTHORIZED_V64',
        phase_1=dict(authorize='Trusted extractor only exact history records; isolate worker with input bytes only',
           history_index='history_record_index.csv',history_records=len(stages['history']),
           lock='SHA inputs and all seven forecasts, read-only owner custody, test unprivileged open and no source access'),
        phase_2=dict(authorize='Only trusted evaluation after phase 1 lock',target_index='target_record_index.csv',
           target_records=len(stages['target']),scoring='Event descriptive, paired valid cells, latitude weighted, strata V61',
           no_ML_training=True,Swarm_untouched=True),
        optional_24h=dict(records=len(stages['periodic']),index='optional_periodic_history_index.csv',authorization='SEPARATE'),
        methods=['Persistence','TwoFrameLinear','LogLinear','ThreeFrameOLSLog','DampedLogTrend','LocalTimePersistence','TinyDirectCNN V60 frozen'],
        V62_recipe_sha256=sha(O62/'new_baseline_protocol.json'),
        V60_checkpoint_SHA256=load(v60/'training_receipt.json')['weights_SHA256'],
        V60_normalization_SHA256=sha(v60/'normalization.json'),
        eastward_source_cells={'1':6,'3':12,'6':21},speed_degrees_hour=15,
        role='LOCKED_INDEPENDENT_TEST_CANDIDATE',
        exposure_policy='No inference here. Any V64 selection/modification makes the pair exposed pilot events; keep fresh final events.',
        future_design='Compare equal CNN with ordinary persistence against z_LT+f_theta(X) only after LT diagnostic and separately approved training. Historical Kp/F10.7 must be cutoff available; final drivers are hindcast.'))
    write_once(OUT/'event_admission_status.json',dict(engineering_runs=n,scientific_role='LOCKED_INDEPENDENT_TEST_CANDIDATE',
        convergence='NOT_ESTABLISHED',v64_score='NOT_AUTHORIZED',V37_sealed=True,GPU=0,
        train=0,extra_MPI_runs=0,Restart=False,DEN_values_decoded=0))
    write_once(OUT/'independent_verification.json',dict(checks=verification,native_volumes=len(volume_rows),cutoffs=len(cutoffs),
        target_records=len(stages['target']),native_time_rows=len(all_times),DEN_reads=0,Swarm_reads=0,V37_unchanged=True))
    write_once(OUT/'resource_usage.json',{e['run_id']:{k:e[k] for k in ('elapsed_s','peak_RSS_bytes','native_bytes',
             'CPU_user_s','CPU_system_s','total_workdir_bytes')} for e in receipts})
    write_once(OUT/'handoff.json',check())


if __name__=='__main__':
    main()
