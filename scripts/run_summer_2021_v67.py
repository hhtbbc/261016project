"""Authorized A-fill 2021 summer two-seed HINDCAST. One attempt per arm."""
import os
import re
import sys
from datetime import timedelta,timezone
from pathlib import Path
from uuid import uuid4

from netCDF4 import Dataset
import numpy as np

from run_training_events_v65 import (
    ROOT,V37,V62,ELF,ELF_SHA,annual,available,at,env,pin,execution_lock,engineering,
    inspect,seal,load,now,sha,require,write_once,model_argv,supervise,Limits,G,builder,forcing,
)
from run_native_density_baselines_v59 import table

OUT=ROOT/'experiments/thermosphere_summer_2021_research_fill_v67'
PRIVATE=OUT/'data_local'
V51=ROOT/'experiments/thermosphere_summer_spinup_add7_v50'
GFZ=ROOT/'experiments/thermosphere_gfz_gap_fill_v66'
CANDIDATE=GFZ/'data_local/A_reference_same_day_HINDCAST_RESEARCH_FILL.nc'
SOURCE_SHA='c1006bfb4443a01a979bce6203d58abb47941e504a3d31e9197cd3323b8e3d46'
GPI_SHA='efbc645f53a2d89f7c2c1555d8373eff141ebc13617c2f1456f849d587121a40'
ARMS={
    'A1':('run_A_mareqx_add7.namelist','a.nc',(80,0,0),'a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7'),
    'A2':('run_B_junsol_add7.namelist','b.nc',(172,0,0),'baed93b59dee7f8e6355c8d0224bd2335cf355bd0d632c9d2327aa7d0227475e'),
}
PLAN=dict(start='2021-05-31T00:00:00Z',end='2021-06-23T00:00:00Z',days=23,steps_60s=33120,
          primary_volumes=24,secondary_volumes=23,hourly_DEN_frames=552)
FILLS={'2021-05-09T00:00:00Z':76.,'2021-06-16T00:00:00Z':77.}


def adapt(template,role):
    require("START_YEAR = 2022" in template and "START_DAY = 151" in template
            and "STOP = 174 0 0" in template and "STEP  = 60" in template,'V51 historical calendar')
    fields={'LABEL':"'V67 SUMMER 2021 A-FILL HINDCAST'",'START_YEAR':'2021',
            'SOURCE':"'seed.nc'",'GPI_NCFILE':"'gpi.nc'"}
    for k,v in fields.items():
        template,n=re.subn(rf'(?m)^ {k}\s*=.*$',lambda _:f' {k} = {v}',template)
        require(n==1,'Input key '+k)
    require('SOURCE_START = '+' '.join(map(str,ARMS[role][2])) in template,'Frozen source clock')
    return template.encode()


def main():
    require(OUT.resolve()==OUT and not OUT.exists() and os.geteuid()==0 and
            Path(sys.executable)==ROOT/'.venv310/bin/python','Unsafe or prior attempt')
    pin(V37)
    require(CANDIDATE.resolve()==CANDIDATE and sha(CANDIDATE)==GPI_SHA and sha(ELF)==ELF_SHA,'GPI or ELF identity')
    cfg=load(V51/'configuration.json')
    g=load(V62/'gfz_source_manifest.json')
    q=ROOT/g['stored_path']
    require(sha(q)==g['source_sha256']==SOURCE_SHA,'Original GFZ drift')
    kp,observed,_,_=annual()
    fills={at(t).replace(tzinfo=timezone.utc):v for t,v in FILLS.items()}
    require(not fills.keys()&observed.keys(),'Original observations no longer missing')
    solar=observed|fills
    with execution_lock(env.PACKAGE/'autumn_execution_lock_local'):
        OUT.mkdir()
        PRIVATE.mkdir(mode=0o700)
        (OUT/'run_receipts').mkdir()
        path=PRIVATE/'gpi.nc'
        path.write_bytes(CANDIDATE.read_bytes())
        path.chmod(0o400)
        d=forcing(PRIVATE,PLAN,kp,solar)
        write_once(OUT/'approved_gap_fill_protocol.json',dict(protocol='GFZ_FOBS_GAP_FILL_V1',
                   status='GFZ_RESEARCH_FILL_POLICY_A_APPROVED',validation_role='PHYSICS_SENSITIVITY_ONLY',
                   selection='A only',fills={k:{'sfu':v,'identity':'RESEARCH_ESTIMATED_FILL'}
                                              for k,v in FILLS.items()},original_GFZ_missing_preserved=True,
                   original_GFZ_SHA256=SOURCE_SHA,GPI_SHA256=GPI_SHA,forcing=d,
                   Fadj_used=False,V37_modified=False,Swarm_DEN_access=False))
        pre={}
        for role,(name,seed,clock,expected) in ARMS.items():
            b=V51/name
            q=V51/seed
            require(b.resolve()==b and sha(b)==cfg['config_sha'][name] and q.resolve()==q and sha(q)==expected,
                    'Historical V51 deck/seed mismatch')
            with Dataset(q) as data:
                require(np.any(np.all(data['mtime'][:]==clock,axis=1)),'V51 native source clock')
            run=PRIVATE/role.lower()
            require(run.resolve()==run and len(os.fsencode(run/'seed.nc'))<120,'Fortran length')
            raw=adapt(b.read_text(),role)
            deck=OUT/(role+'_input.inp')
            deck.write_bytes(raw)
            p=dict(executable=dict(path=str(ELF.relative_to(ROOT)),SHA256=ELF_SHA),
                   mpirun=dict(path='.envs/tiegcm/bin/mpirun'),input=dict(SHA256=sha(deck)),
                   seed_sha256=expected,gpi_sha256=GPI_SHA)
            available(p)
            pre[role]=(run,p,deck,q,clock)
        require(adapt((V51/ARMS['A1'][0]).read_text(),'A1').replace(b'80 0 0',b'172 0 0')==
                adapt((V51/ARMS['A2'][0]).read_text(),'A2'),'Unexpected paired setup differences')
        write_once(OUT/'execution_authorization.json',dict(role='RESEARCH_FILL_PHYSICS_SENSITIVITY',
                   plan=PLAN,protected='V37 Swarm targets sealed, 2022 results unchanged',attempts_each=1,
                   auto_retry=False,both_seeds=True,cumulative_wall_s=12000,total_budget_GiB=16,
                   each_wall_s=6000,each_RSS_GiB=4,each_disk_GiB=8,MPI=4,OMP=1,GPU=0,UTC=now()))
        summaries={}
        inventory=[]
        timeline=[]
        spent=0
        occupied=0
        for role,(run,p,deck,seed,clock) in pre.items():
            checks=available(p)
            require(spent+6000<=12000 and occupied+8*G<=16*G,'Cumulative budget')
            require(all(sha(f)==h for f,h in [(deck,p['input']['SHA256']),(seed,p['seed_sha256']),
                        (ELF,ELF_SHA),(CANDIDATE,GPI_SHA)]),'Frozen assets changed')
            rid=uuid4().hex
            write_once(OUT/'run_receipts'/f'{role}_claim.json',dict(run_id=rid,role=role,
                      preflight_resource=checks,created_UTC=now(),retry=False))
            run.mkdir(mode=0o700)
            t0=now()
            print('START',role,rid,t0,flush=True)
            try:
                old=os.umask(0o077)
                try:
                    status=supervise(model_argv(p,rid),run,Limits(5990,4*G,20*G,8*G,256*2**20,
                                sample_s=.2,term_grace_s=1,total_output_bytes=8*G),
                                env=env.runtime_environment(),total_dir=run,
                                input_files={'input.inp':deck.read_bytes(),'gpi.nc':CANDIDATE.read_bytes(),
                                             'seed.nc':seed.read_bytes()})
                finally:
                    os.umask(old)
                t1=now()
                spec=PLAN | dict(event_id='summer2021_Afill_'+role)
                receipt=engineering(run,spec,p,rid,status,source_clock=clock,role='PHYSICS_SENSITIVITY_ONLY')
                seal(run)
                index,diff=inspect(receipt,spec,solar,kp,private=PRIVATE)
                receipt.update(launch_UTC=t0,exit_UTC=t1,runtime_GPI_max_abs=diff,
                               forcing=d,initial_clock=clock)
                f=OUT/'run_receipts'/f'{role}_run_receipt.json'
                write_once(f,receipt)
                summaries[role]={k:v for k,v in receipt.items() if k not in ('files','time_index','command')}
                summaries[role].update(full_receipt_sha256=sha(f),volumes=len(receipt['files']),hourly=len(index))
                spent+=receipt['elapsed_s']
                occupied+=receipt['total_workdir_bytes']
                inventory.extend(x | {'arm':role,'directory':receipt['directory']} for x in receipt['files'])
                timeline.extend(x | {'arm':role,'directory':receipt['directory']} for x in index.values())
                print('ENGINEERING_PASS',role,rid,receipt['elapsed_s'],flush=True)
            except BaseException as e:
                seal(run)
                write_once(OUT/'run_receipts'/f'{role}_failure.json',dict(run_id=rid,error=repr(e),UTC=now(),retry=False))
                raise
        require(len(inventory)==94 and len(timeline)==1104,'Pair output count')
        table(OUT/'native_output_inventory.csv',inventory)
        table(OUT/'native_time_index.csv',timeline)
        write_once(OUT/'native_output_sha256.json',{r['arm']+'/'+r['file']:r['sha256'] for r in inventory})
        write_once(OUT/'summer_run_receipts.json',summaries)
        print('SUMMER_ENGINEERING_COMPLETE',flush=True)


if __name__=='__main__':
    main()
