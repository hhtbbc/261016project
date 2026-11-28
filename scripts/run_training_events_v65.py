"""Four serial one-shot V65 cold starts, using the V63 supervisor and checks."""
import os
import re
import subprocess
import sys
import tarfile
from datetime import timedelta, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np
from netCDF4 import Dataset

from run_independent_events_v63 import (
    ROOT, V37, V62, G, H, annual, at, available, builder, engineering, env,
    execution_lock, forcing, load, model_argv, now, pin, require, seal, sha,
    supervise, Limits, utc, write_once,
)
from prepare_independent_events_v62 import ELF, SEED
from run_native_density_baselines_v59 import read_csv
from verify_index_independent_events_v63 import inspect

OUT=ROOT/'experiments/thermosphere_multi_event_training_dataset_v65'
PRIVATE=OUT/'data_local'
START='3a8ae1d551965a6fb5d742449e49ef1d625a5bbe'
V64=ROOT/'experiments/thermosphere_independent_event_prediction_v64/evaluation_v64b'
EVENTS={
    'T1':('quiet_20240329T00','2024-03-15','2024-03-31',16,1.667),
    'T2':('quiet_20211125T06','2021-11-11','2021-11-28',17,1.333),
    'T3':('disturbed_20250915T00','2025-09-01','2025-09-18',17,6.667),
    'T4':('disturbed_20210301T03','2021-02-15','2021-03-05',18,5.667),
}
SEED_SHA='a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7'
ELF_SHA='f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776'
ARCHIVE=ROOT/'data/raw/thermosphere_ncar_junsol_acquisition_v40/tiegcm2.0_res5.0_data.tar'


def pinned(path):
    require(path.resolve()==path and path.read_bytes()==subprocess.check_output(
        ['git','show',f'{START}:{path.relative_to(ROOT)}'],cwd=ROOT),f'Frozen dependency drift {path.name}')
    return path


def seed_policy():
    require(sha(SEED)==SEED_SHA and sha(ELF)==ELF_SHA,'Official run asset SHA')
    alternatives={}
    # Catalog exact members of the previously accepted official archive. An alternate
    # seed would change the established V62 cold-start policy for this event family.
    with tarfile.open(ARCHIVE,'r:') as archive:
        for clock in ('sepeqx','decsol','mareqx'):
            item=f'tiegcm_res5.0_data/tiegcm_res5.0_{clock}_smax_prim.nc'
            member=archive.getmember(item)
            require(member.isfile() and 0<member.size<25*2**20,'Seed member identity')
            with archive.extractfile(member) as stream:
                with Dataset('seed',memory=stream.read()) as n:
                    alternatives[clock]={'mtime':n['mtime'][:].tolist(),
                        'grid':[len(n.dimensions[k]) for k in ('ilev','lat','lon')],
                        'source_member':item}
    with Dataset(SEED) as n:
        require(np.any(np.all(n['mtime'][:]==[80,0,0],axis=1)), 'Verified source clock')
    return dict(seed=str(SEED.relative_to(ROOT)),sha256=SEED_SHA,source_clock=[80,0,0],
                policy='V62 MAM/SON same verified mareqx smax cold-start background',
                rationale='Use existing executed and validated seed policy for all four events. '
                          'No date-specific mature seed; alternative archive members inspected by metadata only '
                          'and not admitted for this frozen family. T2 November and T3 September use spring proxy.',
                archived_alternatives=alternatives,convergence='NOT_ESTABLISHED')


def prepare(tag,event,dp,c,kp,solar, *, out=OUT, private=PRIVATE, role="TRAIN"):
    event_id,lo_date,hi_date,days,peak=event
    lo,hi=at(dp['start']),at(dp['end'])
    require(lo.isoformat()==lo_date+'T00:00:00' and hi.isoformat()==hi_date+'T00:00:00'
            and hi-lo==timedelta(days=days) and float(c['peak_Kp'])==peak
            and dp['cutoffs']==c['prediction_cutoffs'].split(';') and c['full_metadata_candidate']=='True',
            'Training proposal/calendar mismatch')
    core=(at(c['core_start']),at(c['core_end_exclusive']))
    for cut in map(at,dp['cutoffs']):
        require(max(core[0],lo+timedelta(days=14))<=cut-3*H and cut+6*H<core[1], 'Fixed cutoff scope')
    run=private/tag.lower()
    require(run.resolve()==run and len(os.fsencode(run/'seed.nc'))<120,'SOURCE path bound')
    folder=out/'prepared_configs'/tag
    folder.mkdir()
    template=pinned(V62/'configs/q_input.inp').read_text()
    def volumes(kind,count):
        return ',\n           '.join(', '.join(f"'{kind}_{i:03d}.nc'" for i in range(a,min(a+5,count+1)))
                                     for a in range(1,count+1,5))
    a,b=lo.strftime('%j'),hi.strftime('%j')
    replacements=dict(LABEL=f"'{'V65' if role=='TRAIN' else 'V66'} {role} EVENT HINDCAST'",START_YEAR=str(lo.year),START_DAY=a,
                      START=f'{a} 0 0',STOP=f'{b} 0 0',SECSTART=f'{a} 1 0',SECSTOP=f'{b} 0 0',
                      OUTPUT=volumes('primary',days+1),SECOUT=volumes('secondary',days))
    for name,value in replacements.items():
        pattern=rf'(?m)^ {name}\s*=.*(?:\n           .*\n?)*'
        if name in ('OUTPUT','SECOUT'):
            pattern=rf'(?m)^ {name}\s*=.*(?:\n           .*)*'
        else:
            pattern=rf'(?m)^ {name}\s*=.*$'
        template,n=re.subn(pattern,lambda _:f' {name} = {value}',template)
        require(n==1,'Deck field '+name)
    require("SOURCE = 'seed.nc'" in template and "SOURCE_START = 80 0 0" in template
            and "POTENTIAL_MODEL = 'HEELIS'" in template and "STEP  = 60" in template
            and max(map(len,template.splitlines()))<1024,'Frozen physics and deck syntax')
    for rel in re.findall(r"'\$PROJECTROOT/([^']+)'",template):
        p=ROOT/rel
        require(p.resolve()==p and p.is_file(),'Missing tide file')
    (folder/'input.inp').write_text(template)
    gpi_dir=private/f'forcing_{tag}'
    gpi_dir.mkdir(mode=0o700)
    gpi=gpi_dir/'gpi.nc'
    grid,f,mean,k=builder.arrays(solar,kp,(lo-48*H).date(),(hi+48*H).date())
    builder.write_gpi(gpi,grid,f,mean,k,lo.date(),hi.date())
    a_core,b_core=(t.replace(tzinfo=timezone.utc) for t in core)
    require(np.isclose(max(kp[t] for t in kp if a_core<=t<b_core),peak,atol=.0005),
            'Definitive Kp peak differs')
    for p in (folder/'input.inp',gpi):
        p.chmod(0o444)
    metadata=dict(dp, event_id=event_id,days=days,steps_60s=days*1440,primary_volumes=days+1,
                  secondary_volumes=days,hourly_DEN_frames=days*24,Training_role=role)
    proof=dict(executable=dict(path=str(ELF.relative_to(ROOT)),SHA256=ELF_SHA),
               mpirun=dict(path='.envs/tiegcm/bin/mpirun'),input=dict(SHA256=sha(folder/'input.inp')),
               seed_sha256=SEED_SHA,gpi_sha256=sha(gpi))
    driver=forcing(gpi_dir,metadata,kp,solar)
    write_once(folder/'preflight.json',dict(plan=metadata,proof=proof,driver=driver,
               expected_first_Fobs=c['Fobs_first'],expected_last_Fobs=c['Fobs_last'],
               source_path_bytes=len(os.fsencode(run/'seed.nc'))))
    return run,metadata,proof,folder/'input.inp',gpi,driver


def execute():
    require(OUT.resolve()==OUT and not OUT.exists() and os.geteuid()==0
            and Path(sys.executable)==ROOT/'.venv310/bin/python','Execution directory or frozen CPU environment')
    pin(V37)
    roles=load(pinned(V64/'next_dataset_production_plan.json'))['roles']
    require({x['event'] for x in roles['TRAIN']}=={x[0] for x in EVENTS.values()},'Training roles')
    metadata={x['event_id']:x for x in read_csv(pinned(V62/'geomagnetic_event_candidates.csv'))}
    source=load(pinned(V62/'gfz_source_manifest.json'))
    require(sha(ROOT/source['stored_path'])==source['source_sha256'],'GFZ original mismatch')
    seed=seed_policy()
    kp,solar,_,_=annual()
    with execution_lock(env.PACKAGE/'autumn_execution_lock_local'):
        OUT.mkdir()
        PRIVATE.mkdir(mode=0o700)
        (OUT/'prepared_configs').mkdir()
        (OUT/'run_receipts').mkdir()
        write_once(OUT/'execution_authorization.json',dict(start_commit=START,events=EVENTS,role='TRAIN',
                   attempts_each=1,retries=False,serial=True,MPI=4,OMP=1,GPU=0,wall_s=6000,
                   RSS_bytes=4*G,each_output_bytes=8*G,total_wall_s=24000,total_output_bytes=32*G,
                   GFZ_SHA256=source['source_sha256'],V55_staging=sorted(p.name for p in
                   (ROOT/'data/raw/thermosphere_external_handoff_v55/staging').iterdir()),UTC=now()))
        write_once(OUT/'event_role_registry.json',roles)
        write_once(OUT/'seed_policy.json',seed)
        plans={x['event']:x for x in roles['TRAIN']}
        prepared={}
        for tag,event in EVENTS.items():
            try:
                prepared[tag]=prepare(tag,event,plans[event[0]],metadata[event[0]],kp,solar)
            except (KeyError,ValueError) as e:
                write_once(OUT/'run_receipts'/f'{tag}_preflight_failed.json',dict(error=str(e),launch_count=0))
        require(len(prepared)==4,'V65 training configuration not fully admitted')
        total_wall=0
        total_bytes=0
        for tag,(run,plan,p,deck,gpi,driver) in prepared.items():
            checks=available(p)
            require(total_wall+6000<=24000 and total_bytes+8*G<=32*G,'Cumulative reserve')
            write_once(OUT/'run_receipts'/f'{tag}_resources_before.json',checks)
            require(all(sha(path)==checksum for path,checksum in
                         [(deck,p['input']['SHA256']),(gpi,p['gpi_sha256']),(SEED,SEED_SHA),(ELF,ELF_SHA)]),
                     'Input identity before claim')
            run_id=uuid4().hex
            write_once(OUT/'run_receipts'/f'{tag}_claim.json',
                       dict(run_id=run_id,event_id=plan['event_id'],attempts=1,UTC=now()))
            run.mkdir(mode=0o700)
            started=now()
            print('START',tag,run_id,started,flush=True)
            try:
                old=os.umask(0o077)
                try:
                    status=supervise(model_argv(p,run_id),run,Limits(5990,4*G,20*G,8*G,256*2**20,
                                     sample_s=.2,term_grace_s=1,total_output_bytes=8*G),
                                     env=env.runtime_environment(),total_dir=run,
                                     input_files={'input.inp':deck.read_bytes(),'gpi.nc':gpi.read_bytes(),
                                                  'seed.nc':SEED.read_bytes()})
                finally:
                    os.umask(old)
                ended=now()
                receipt=engineering(run,plan,p,run_id,status,role='TRAIN')
                seal(run)
                _,errors=inspect(receipt,plan,solar,kp,private=PRIVATE)
                receipt.update(launch_UTC=started,exit_UTC=ended,runtime_GPI_max_abs=errors,
                               forcing=driver,event_id=plan['event_id'])
                write_once(OUT/'run_receipts'/f'{tag}_run_receipt.json',receipt)
                total_wall+=receipt['elapsed_s']
                total_bytes+=receipt['total_workdir_bytes']
                print('ENGINEERING_PASS',tag,run_id,receipt['elapsed_s'],flush=True)
            except BaseException as exc:
                write_once(OUT/'run_receipts'/f'{tag}_failure.json',
                           dict(run_id=run_id,error=repr(exc),UTC=now(),no_retry=True))
                seal(run)
                raise


if __name__=='__main__':
    execute()
