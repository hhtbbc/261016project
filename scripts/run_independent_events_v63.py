"""One-shot serial TIE-GCM CPU production. No output DEN arrays are decoded."""
from datetime import datetime,timedelta,timezone
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

from netCDF4 import Dataset
import numpy as np

from execute_tiegcm_autumn_2022_v27 import execution_lock, model_argv, resource_review
from runtime import tiegcm_autumn_execution as env
from runtime.supervisor import Limits, supervise
from runtime.tiegcm_rank_exit import write_once
from atmosphere.tiegcm_mar25_acceptance import parse_progress, validate_exits, require, sha
from audit_tiegcm_autumn_v26 import metadata
from prepare_independent_events_v62 import annual
import prepare_tiegcm_training_drivers as builder
from build_non_target_horizon_index_v56 import ROOT, V37, pin

V62=ROOT/'experiments/thermosphere_independent_event_production_v62'
OUT=ROOT/'experiments/thermosphere_independent_event_cpu_execution_v63'
PRIVATE=OUT/'data_local'
BASE='e97111d9cc65bf35640ee1df7a1ded8b4bb1233e'
G=2**30
S=timedelta(seconds=60)
H=60*S
EVENTS={'quiet': ('quiet_20230502T12','q',24480,
    '1f919053cd7912f2cef066c51e9aa40d506f51cfcd4df1b5aece300d55145cd6',
    'e37a8780e9f21068f39591989b8290c2b51c44febe0261616577fac1b0b4f14a'),
  'disturbed': ('disturbed_20230520T00','d',25920,
    '1b413881cf86bcb8c600be98bf22fef481cf669c8fabc4a8713f1fd080f363ae',
    '85de066c0ce65bf6834c9a476d3c5d2e3e43b5b61114aca27121650aaba5cb21')}


def load(path):
    return json.loads(path.read_text())


def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')


def at(text):
    return datetime.fromisoformat(text.rstrip('Z'))


def utc(t):
    return t.isoformat()+'Z'


def frozen(name):
    p=V62/name
    require(p.resolve()==p and p.read_bytes()==subprocess.check_output(
        ['git','show',f'{BASE}:{p.relative_to(ROOT)}'],cwd=ROOT),'V62 identity drift: '+name)
    return load(p)


def protocol(key, proof, plan):
    event,letter,steps,gpi,deck=EVENTS[key]
    source=V62/'data_local'/letter
    run=PRIVATE/letter
    require(source.resolve()==source and run.resolve()==run and not run.exists(),'Run directory already exists or unsafe')
    require({p.name for p in source.iterdir()}=={'input.inp','gpi.nc','seed.nc'},'Unexpected prior artifacts')
    require(plan['event_id']==proof['event_id']==event and plan['steps_60s']==steps,'Event contract')
    expected={'input.inp':deck,'gpi.nc':gpi,'seed.nc':proof['seed_sha256']}
    files={}
    for name,checksum in expected.items():
        p=source/name
        require(p.resolve()==p and p.stat().st_mode&0o222==0 and sha(p)==checksum,'Frozen '+name)
        files[name]=p.read_bytes()
    require(sha(ROOT/proof['seed_original'])==proof['seed_sha256']==
       'a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7','Frozen seed')
    require(len(os.fsencode(run/'seed.nc'))<120 and len(os.fsencode(source/'seed.nc'))==103,'Fortran SOURCE limit')
    body=files['input.inp'].decode()
    require("SOURCE = 'seed.nc'" in body and "GPI_NCFILE = 'gpi.nc'" in body and
      "POTENTIAL_MODEL = 'HEELIS'" in body and "STEP  = 60" in body,'Deck semantics')
    for rel in re.findall(r"'\$PROJECTROOT/([^']+)'",body):
        require((ROOT/rel).resolve()==ROOT/rel and (ROOT/rel).is_file(),'Missing GSWM')
    start,end=at(plan['start']),at(plan['end'])
    require((end-start)==steps*S,'Plan duration')
    p=dict(executable=dict(path='experiments/tiegcm2_apex2023_v1/tiegcm2.0',SHA256=proof['model_ELF_SHA256']),
           mpirun=dict(path='.envs/tiegcm/bin/mpirun'),
           input=dict(SHA256=deck),seed_sha256=proof['seed_sha256'],gpi_sha256=gpi)
    require(sha(ROOT/p['executable']['path'])==p['executable']['SHA256']==
        'f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776','ELF identity')
    return run,files,p


def forcing(source,plan,kp,solar):
    start,end=(at(plan[k]).replace(tzinfo=timezone.utc) for k in ('start','end'))
    days,f,mean,k=builder.arrays(solar,kp,(start-48*H).date(),(end+48*H).date())
    with Dataset(source/'gpi.nc') as n:
        require(n.data_model=='NETCDF3_CLASSIC' and
            [int(x) for x in n['year_day'][:]]==[int(t.strftime('%Y%j')) for t in days] and
            np.array_equal(n['f107d'][:],f) and np.array_equal(n['kp'][:],k) and
            np.max(abs(n['f107a'][:]-mean))<1e-12 and
            int(n.yearday_beg)==int(start.strftime('%Y%j')) and int(n.yearday_end)==int(end.strftime('%Y%j')),
            'GPI driving metadata/centered support')
    return dict(days=len(days),definitive_Kp_bins=int(k.size),observed_F107_center_days=81,adjusted_flux_used=False)


def available(p):
    review=resource_review(p)
    require(review['resource_ready'] and review['active_model_count']==0,'CPU/MPI or exclusive process budget')
    return review


def engineering(run,plan,p,run_id,status, *, source_clock=(80,0,0),
                role="LOCKED_INDEPENDENT_TEST_CANDIDATE"):
    require(status['qualification']=='PASS' and status['returncode']==0 and status['cleanup_verified']
         and not status['gaps'] and status['stop_reason'] is None and status['elapsed_s']<=6000
         and 0<status['peak_sampled_tree_rss_bytes']<=4*G,'Execution supervisor failure')
    launch=load(run/'launch_once.json')
    require(launch['launch_count']==1 and launch['argv']==model_argv(p,run_id),'One launch identity')
    ranks=validate_exits(run,run_id,p)['ranks']
    start,end=at(plan['start']),at(plan['end'])
    last=[parse_progress((run/f'rank_{i:03d}.log').read_text(),steps=plan['steps_60s'],start=start) for i in range(4)]
    require('output_hist: copied source history structure sh to' in (run/'rank_000.log').read_text(),'Cold start log missing')
    total=sum(f.stat().st_size for f in run.rglob('*') if f.is_file())
    require(total<=8*G,'Output budget')
    with Dataset(run/'seed.nc') as seed:
        grid={k:np.asarray(seed[k][:]) for k in ('lat','lon','lev','ilev')}
        seed_iter=int(seed['iter'][0])
    require([len(grid[k]) for k in ('ilev','lat','lon')]==[29,36,72],'Seed grid')
    expected={f'{kind}_{i:03d}.nc' for kind in ('primary','secondary')
              for i in range(1,plan[kind+'_volumes']+1)}
    require({f.name for f in run.glob('*.nc')}==expected|{'seed.nc','gpi.nc'},'Output files do not match')
    inventory=[]
    index=[]
    for name in sorted(expected):
        path=run/name
        stat=path.stat()
        require(path.resolve()==path and stat.st_size<=256*2**20,'Native file identity')
        kind,volume=name[:-3].split('_')
        count=1 if kind=='primary' else 24
        with Dataset(path) as n:
            require(n.data_model=='NETCDF3_CLASSIC' and len(n.dimensions['time'])==count and
              int(np.asarray(n['timestep'][:]).item())==60 and np.all(n['calendar_advance'][:]==1),'Native file header')
            for k,v in grid.items():
                require(np.array_equal(n[k][:],v),'Grid drift '+k)
            if kind=='secondary':
                den=n['DEN']  # dimensions and units only
                require(den.dimensions==('time','ilev','lat','lon') and den.units=='g/cm3'
                     and den.shape==(count,29,36,72),'Native DEN metadata')
            times=[]
            for i in range(count):
                hour=24*(int(volume)-1)+(i+1 if kind=='secondary' else 0)
                t=start+hour*H
                m=metadata(n,i)
                doy=t.timetuple().tm_yday
                require(m['utc']==t and m['history_type']==kind and
                   (m['initial_year'],m['initial_day'],m['initial_mtime'])==(start.year,start.timetuple().tm_yday,[start.timetuple().tm_yday,0,0])
                   and (m['year'],m['day'],m['mtime'])==(t.year,doy,[doy,t.hour,0]),'Output clock shift')
                if hour==0:
                    require(m['iter']==seed_iter and tuple(n.source_mtime)==source_clock,'Cold source identity')
                else:
                    require(m['run_type']=='initial' and m['iter']==start.timetuple().tm_yday*1440+hour*60,'Warm iter')
                times.append(utc(t))
                if kind=='secondary':
                    index.append(dict(event_id=plan['event_id'],run_id=run_id,UTC=utc(t),file=name,record=i))
        h=sha(path)
        after=path.stat()
        require((stat.st_size,stat.st_mtime_ns,stat.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino),'Output changed')
        inventory.append(dict(event_id=plan['event_id'],run_id=run_id,file=name,kind=kind,bytes=stat.st_size,
              sha256=h,records=count,first_UTC=times[0],last_UTC=times[-1]))
    require(len(index)==plan['hourly_DEN_frames'] and at(index[-1]['UTC'])==end,'Complete hourly index')
    exact={'input.inp':p['input']['SHA256'],'seed.nc':p['seed_sha256'],'gpi.nc':p['gpi_sha256']}
    require(all(sha(run/f)==h for f,h in exact.items()) and sha(ROOT/p['executable']['path'])==p['executable']['SHA256'],
        'Post-run source identity')
    warning=[]
    for f in sorted(run.glob('rank_*.log')):
        for line in f.read_text(errors='replace').splitlines():
            if re.search(r'\bwarning\b|\bcaution\b',line,re.I):
                warning.append(line.strip())
    return dict(engineering='PASS',independent_science_status=role,run_id=run_id,
          directory=str(run.relative_to(ROOT)),datetime_start=plan['start'],datetime_end=plan['end'],
          final_step=last[0]['final_step'],rank_progress=last,ranks=ranks,parent_exit=0,command=launch['argv'],
          status_sha256=sha(run/'status.json'),peak_RSS_bytes=status['peak_sampled_tree_rss_bytes'],
          CPU_user_s=status['children_cpu_user_s'],CPU_system_s=status['children_cpu_system_s'],
          elapsed_s=status['elapsed_s'],total_workdir_bytes=total,
          native_bytes=sum(f['bytes'] for f in inventory),warnings_unique=sorted(set(warning)),warning_line_count=len(warning),
          model_SHA256=p['executable']['SHA256'],input_SHA256=exact,files=inventory,time_index=index,
          DEN_values_decoded=0,scientific_convergence='NOT_ESTABLISHED')


def seal(run):
    # The parent is mode 0700 from before launch. Its UID is checked independently.
    for dirpath, _, names in os.walk(run,topdown=False):
        for name in names:
            path=Path(dirpath)/name
            require(path.resolve()==path and path.is_file(),'Untrusted output link')
            path.chmod(0o400)
        Path(dirpath).chmod(0o500)


def execute():
    require(OUT.resolve()==OUT and not PRIVATE.exists(),'V63 already started or unsafe')
    require(Path(sys.executable)==ROOT/'.venv310/bin/python','Frozen CPU environment')
    require(os.geteuid()==0,'Expected privileged custody account')
    pin(V37)
    manifest=frozen('prepared_run_config_manifest.json')
    auth=frozen('next_stage_execution_authorization.json')
    pairs=frozen('selected_event_pairs.json')
    frozen('event_selection_protocol.json')
    frozen('new_baseline_protocol.json')
    require(auth['signed_config_manifest_sha256']==sha(V62/'prepared_run_config_manifest.json'),'Manifest binding')
    g=frozen('gfz_source_manifest.json')
    require(sha(ROOT/g['stored_path'])==g['source_sha256'],'Official archive changed')
    kp,solar,_,_=annual()
    with execution_lock(env.PACKAGE/'autumn_execution_lock_local'):
        prepared={}
        pre={}
        for (key,plan,proof,selected) in zip(EVENTS,auth['runs'],manifest['preflight_runs'],pairs['primary']):
            require(selected['event_id']==plan['event_id'] and selected['prediction_cutoffs'].split(';')==plan['cutoff_UTC'],'Event scope')
            prepared[key]=protocol(key,proof,plan)
            pre[key]=dict(resource=available(prepared[key][2]),driver=forcing(V62/'data_local'/EVENTS[key][1],plan,kp,solar),
                          initial=proof,actual_output_dir=str(prepared[key][0].relative_to(ROOT)))
        require(len(prepared)==2,'Missing authorized event')
        PRIVATE.mkdir(mode=0o700)
        write_once(OUT/'execution_authorization.json',dict(user_message='V63 explicit two single-use CPU cold starts',
             events=[k[0] for k in EVENTS.values()],MPI=4,OMP=1,serial=True,retries=False,GPU=0,RSS_limit_bytes=4*G,
             hard_wall_seconds=6000,output_limit_bytes=8*G,model_DEN_label_access=False,UTC=now()))
        write_once(OUT/'preflight_manifest.json',pre)
        for key,plan in zip(EVENTS,auth['runs']):
            run,files,p=prepared[key]
            available(p)
            run_id=uuid.uuid4().hex
            write_once(OUT/f'{key}_claim.json',dict(run_id=run_id,event_id=plan['event_id'],created_UTC=now(),retry=False))
            run.mkdir(mode=0o700)
            try:
                released_at=now()
                print('Starting',key,run_id,released_at,flush=True)
                oldmask=os.umask(0o077)
                try:
                    status=supervise(model_argv(p,run_id),run,Limits(5990,4*G,20*G,8*G,256*2**20,
                        sample_s=.2,term_grace_s=1,total_output_bytes=8*G),
                        env=env.runtime_environment(),total_dir=run,input_files=files)
                finally:
                    os.umask(oldmask)
                finished=now()
                row=engineering(run,plan,p,run_id,status)
                row.update(launch_UTC=released_at,exit_UTC=finished)
                seal(run)
                write_once(OUT/f'{key}_run_receipt.json',row)
                print('ENGINEERING_PASS',key,run_id,flush=True)
            except BaseException as error:
                write_once(OUT/f'{key}_failure.json',dict(run_id=run_id,error=repr(error),UTC=now(),retry=False))
                seal(run)
                raise


if __name__=='__main__':
    execute()
