"""Produce only MODEL_SELECTION_VALIDATION cold runs and sealed position indexes."""
import hashlib
import os
import sys
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from run_training_events_v65 import (
    ROOT,V62,V37,V64,SEED,ELF,SEED_SHA,ELF_SHA,annual,available,at,env,pin,
    pinned,prepare,seed_policy,execution_lock,engineering,inspect,seal,load,now,sha,
    require,write_once,model_argv,supervise,Limits,G,utc,read_csv,
)
from run_native_density_baselines_v59 import table
from verify_index_independent_events_v63 import blocked_open

OUT=ROOT/'experiments/thermosphere_matched_residual_training_v66'
PRIVATE=OUT/'validation_local'
ROLE='MODEL_SELECTION_VALIDATION'
EVENTS={
    'VAL1':('quiet_20220301T21','2022-02-16','2022-03-04',16,2.0),
    'VAL2':('disturbed_20211103T21','2021-10-21','2021-11-07',17,7.667),
}
H=timedelta(hours=1)
LEADS=(1,3,6)


def index(receipts,plans,anchors):
    groups={k:[] for k in ('history','target','periodic')}
    for tag,plan in plans.items():
        r=receipts[tag]
        by={a['UTC']:a for a in anchors[tag].values()}
        core=at(plan['core_start'])
        end=at(plan['core_end_exclusive'])
        for c in plan['cutoffs']:
            t=at(c)
            require(core<=t-3*H and t+6*H<end,'Core support')
            for kind,hs in [('history',(-3,-2,-1)),('target',LEADS),('periodic',LEADS)]:
                for h in hs:
                    delta=h-24 if kind=='periodic' else h
                    row=by[utc(t+delta*H)]
                    groups[kind].append(row | {'cutoff_UTC':c,'lead_hours':h,'role':ROLE,'stage':kind,
                         'record_id':hashlib.sha256(f"{r['run_id']}|{c}|{kind}|{h}".encode()).hexdigest(),
                         'relative_directory':r['directory'],'DEN_access':'SEALED'})
    check={(r['run_id'],r['UTC']):r for r in groups['target']}
    overlaps=[{'historical':a,'earlier_target':check[a['run_id'],a['UTC']]}
              for a in groups['periodic'] if (a['run_id'],a['UTC']) in check]
    require(all(len(v)==12 for v in groups.values()) and len(check)==12,'Exact validation index')
    names={'history':'validation_history_record_index.csv','target':'validation_target_record_index.csv',
           'periodic':'validation_periodic_history_index.csv'}
    for k,v in groups.items():
        table(OUT/names[k],v)
    table(OUT/'validation_native_time_index.csv',[a for q in anchors.values() for a in q.values()])
    table(OUT/'validation_native_output_inventory.csv',[f | {'directory':r['directory']}
                                                     for r in receipts.values() for f in r['files']])
    write_once(OUT/'validation_sealing_manifest.json',dict(role=ROLE,cutoffs=4,targets=12,history=12,periodic=12,
               DEN_reads=0,unprivileged_uid=65534,denied_open='EACCES',
               private_mode='0700',run_mode='0500',native_mode='0400',periodic_overlap=overlaps,
               SHA256={n:sha(OUT/n) for n in names.values()},status='SEALED_AWAITING_SEPARATE_AUTHORIZATION'))


def main():
    require(OUT.resolve()==OUT and not OUT.exists() and os.geteuid()==0 and
            Path(sys.executable)==ROOT/'.venv310/bin/python','Unsafe or already attempted')
    pin(V37)
    v65=ROOT/'experiments/thermosphere_multi_event_training_dataset_v65'
    roles=load(pinned(V64/'next_dataset_production_plan.json'))['roles']
    require(load(v65/'event_role_registry.json')==roles,'Role registry drift')
    plans={x['event']:x for x in roles[ROLE]}
    require(set(plans)=={v[0] for v in EVENTS.values()},'Validation scope')
    metadata={r['event_id']:r for r in read_csv(pinned(V62/'geomagnetic_event_candidates.csv'))}
    g=load(pinned(V62/'gfz_source_manifest.json'))
    require(sha(ROOT/g['stored_path'])==g['source_sha256'],'Official source changed')
    seed=seed_policy()
    require(seed['sha256']==load(v65/'seed_policy.json')['sha256'],'Different cold seed policy')
    kp,solar,_,_=annual()
    with execution_lock(env.PACKAGE/'autumn_execution_lock_local'):
        OUT.mkdir()
        PRIVATE.mkdir(mode=0o700)
        (OUT/'prepared_configs').mkdir()
        (OUT/'run_receipts').mkdir()
        write_once(OUT/'execution_authorization.json',dict(validation_events=EVENTS,role=ROLE,TRAIN_arms=['P','LT'],
                   updates_each=200,attempts_per_event=1,automatic_retry=False,serial=True,
                   MPI=4,OMP=1,wall_s=6000,RSS_bytes=4*G,output_bytes=8*G,GPU=0,
                   GFZ_SHA256=g['source_sha256'],seed=seed['sha256'],target_DEN_access=False,UTC=now()))
        pre={tag:prepare(tag,e,plans[e[0]],metadata[e[0]],kp,solar,out=OUT,private=PRIVATE,role=ROLE)
             for tag,e in EVENTS.items()}
        receipts={}
        anchors={}
        for tag,(run,plan,proof,deck,gpi,driver) in pre.items():
            available(proof)
            require(all(sha(f)==x for f,x in [(deck,proof['input']['SHA256']),(gpi,proof['gpi_sha256']),
                        (ELF,ELF_SHA),(SEED,SEED_SHA)]),'Changed validation inputs')
            rid=uuid4().hex
            write_once(OUT/'run_receipts'/f'{tag}_claim.json',dict(run_id=rid,event=plan['event_id'],UTC=now()))
            run.mkdir(mode=0o700)
            t0=now()
            print('START',tag,rid,t0,flush=True)
            try:
                old=os.umask(0o077)
                try:
                    status=supervise(model_argv(proof,rid),run,Limits(5990,4*G,20*G,8*G,256*2**20,
                                 sample_s=.2,term_grace_s=1,total_output_bytes=8*G),
                                 env=env.runtime_environment(),total_dir=run,
                                 input_files={'input.inp':deck.read_bytes(),'gpi.nc':gpi.read_bytes(),
                                              'seed.nc':SEED.read_bytes()})
                finally:
                    os.umask(old)
                end=now()
                receipt=engineering(run,plan,proof,rid,status,role=ROLE)
                seal(run)
                found,errors=inspect(receipt,plan,solar,kp,private=PRIVATE)
                blocked_open(run/'secondary_001.nc')
                receipt.update(event_id=plan['event_id'],launch_UTC=t0,exit_UTC=end,
                               runtime_GPI_max_abs=errors,forcing=driver)
                write_once(OUT/'run_receipts'/f'{tag}_run_receipt.json',receipt)
                receipts[tag]=receipt
                anchors[tag]=found
                print('ENGINEERING_PASS',tag,rid,receipt['elapsed_s'],flush=True)
            except BaseException as e:
                seal(run)
                write_once(OUT/'run_receipts'/f'{tag}_failure.json',dict(run_id=rid,error=repr(e),retry=False))
                raise
        require(sum(len(r['files']) for r in receipts.values())==68 and
                sum(len(x) for x in anchors.values())==792,'Output totals')
        index(receipts,{t:p[1] for t,p in pre.items()},anchors)
        write_once(OUT/'validation_run_receipts.json',
                   {tag:{k:v for k,v in r.items() if k not in ('time_index','files','command')}
                    | {'file_count':len(r['files']),'hourly_frames':len(r['time_index']),
                       'full_receipt_SHA256':sha(OUT/'run_receipts'/f'{tag}_run_receipt.json')}
                    for tag,r in receipts.items()})
        print('VALIDATION_INDEXES_SEALED',flush=True)


if __name__=='__main__':
    main()
