"""Offline V50 pair, exact source-path probe, and future one-shot admission predicates."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from netCDF4 import Dataset
import probe_summer_seed_recovery_v47 as probe
import preflight_summer_seed_recovery_v47 as v47
import prepare_summer_gpi_extended_v50 as gpi
from atmosphere.restart_validation import REQUIRED, check_source_clock, inspect_restart

ROOT,OUT=gpi.ROOT,gpi.OUT
RUNS=('run_A_mareqx_add7','run_B_junsol_add7')
SEEDS=('a.nc','b.nc')
CLOCK=(80,172)
SRC=ROOT/'third_party/TIEGCM2.0/src'
PLAN=OUT/'paired_plan.json'
require=gpi.require
LABEL='SUMMER ADD7 2022 OFFLINE CANDIDATE'


def check_gpu(environment):
    require(environment.get('CUDA_VISIBLE_DEVICES','')=='' and environment.get('OMP_NUM_THREADS','1')=='1','GPU or OMP prohibited')


def next_admission(scope,role,receipt,available,prior_A=None):
    """A V51 runner must call this, then take the shared lock and claim exclusively."""
    require(role in ('A','B') and available,'Role or once-only admission failure')
    require(receipt=={'scope':'V51 2022 add7 A then B CPU','plan_sha256':scope,
                     'attempts_each':1,'approved':True,'automatic_retry':False},'New explicit V51 pair authorization required')
    if role=='B':
        require(prior_A is not None and prior_A.get('engineering')=='PASS' and
                prior_A.get('role')=='A' and prior_A.get('plan_sha256')==scope,'Verified A same-plan receipt required')


def safe_source(cwd,value):
    require(value in tuple('../'+s for s in SEEDS) and len(value.encode())<120,
            'SOURCE must select a short parent copy')
    require(cwd.parent==OUT and cwd.resolve()==cwd,'Wrong model working directory')
    expected=OUT/value.split('/')[-1]
    require((cwd/value).resolve()==expected and expected.resolve()==expected and
            expected.is_file() and not expected.is_symlink() and not bool(expected.stat().st_mode&0o222),
            'Unsafe or writable SOURCE')
    return expected


def derive_calendar():
    hours=int((gpi.STOP-gpi.START).total_seconds()/3600)
    secstart=gpi.START+gpi.timedelta(hours=1)
    stride=gpi.timedelta(hours=1)
    count=int((gpi.STOP-secstart)/stride)+1
    primary=(gpi.STOP-gpi.START).days+1
    require(hours==552 and count==552 and primary==24 and count%24==0,'Wrong frozen history layout')
    return {'steps':hours*60,'primary':primary,'secondary':count//24,'warm_hours':count}


def expected_pair(template):
    schedule=derive_calendar()
    common={'LABEL':repr(LABEL),'START_DAY':'151','START':'151 0 0','SECSTART':'151 1 0',
            'OUTPUT':', '.join(repr(f'primary_{i:03d}.nc') for i in range(1,schedule['primary']+1)),
            'SECOUT':', '.join(repr(f'secondary_{i:03d}.nc') for i in range(1,schedule['secondary']+1)),
            'GPI_NCFILE':repr(f'$PROJECTROOT/{gpi.FILE.relative_to(ROOT)}')}
    candidates=[]
    for i in range(2):
        s=template
        items=common|{'SOURCE':repr('../'+SEEDS[i]),'SOURCE_START':f'{CLOCK[i]} 0 0'}
        for key,val in items.items():
            s,count=re.subn(rf'(?m)^( +{key}\s*=).*$',rf'\g<1> {val}',s)
            require(count==1,f'Corrupt template key {key}')
        candidates.append(s)
    return candidates


def validate(texts,expected,steps=33120):
    require(list(texts)==list(expected),'Unexpected physical or schedule drift')
    require(steps==derive_calendar()['steps'],'Expected 33120 steps')
    diff=[dict(A=a,B=b) for a,b in zip(*[x.splitlines() for x in texts],strict=True) if a!=b]
    require([d['A'].split('=')[0].strip() for d in diff]==['SOURCE','SOURCE_START'],'Only source differences allowed')
    for i,t in enumerate(texts):
        fields=dict(re.findall(r'(?m)^ +([A-Z_]+)\s*=\s*(.*)$',t))
        parse=lambda k:list(map(int,fields[k].split()))
        require(fields['START_YEAR']=='2022' and fields['START_DAY']=='151' and
                parse('START')==[151,0,0] and parse('STOP')==[174,0,0] and fields['STEP']=='60','Wrong calendar')
        require(parse('SOURCE_START')==[CLOCK[i],0,0],'Wrong source clock')
        check_source_clock(parse('START'),parse('SOURCE_START'))
        require(len(re.findall("'primary_",fields['OUTPUT']))==24 and
                len(re.findall("'secondary_",fields['SECOUT']))==23,'Wrong output list')
    return diff


def stage_copy(origin,target,sha):
    require(origin.resolve()==origin and not target.exists() and not target.is_symlink(),'Unsafe seed original or destination')
    with tempfile.TemporaryDirectory(dir=OUT,prefix='.copy-') as tmp:
        p=Path(tmp)/target.name
        shutil.copyfile(origin,p)
        p.chmod(0o444)
        require(v47.sha(origin)==v47.sha(p)==sha and p.stat().st_size==origin.stat().st_size,'Seed changed')
        os.link(p,target)


def fortran_probe(files):
    """Compile only frozen acquisition routines plus a small NetCDF reader."""
    tests=OUT/'tests'
    tests.mkdir(exist_ok=False)
    cwd=OUT/'probe_cwd'
    cwd.mkdir(exist_ok=True)
    require(not list(cwd.iterdir()),'Probe CWD occupied')
    for name in ('getfile.F','util.F','nchist.F','rdsource.F'):
        p=SRC/name
        require(v47.sha(p)==v47.load(v47.v45.OUT/'preflight.json')['critical_assets'][str(p.relative_to(ROOT))],'Source drift')
    expand=probe.exact_block(SRC/'util.F','      recursive subroutine expand_path(path)','      end subroutine expand_path')
    opener=probe.exact_block(SRC/'nchist.F','      subroutine nc_open(ncid,flnm,status,rdwr)','      end subroutine nc_open')
    head,body=opener.split('\n',1)
    opener=head+"\n      implicit none\n      include 'netcdf.inc'\n"+body
    rd=probe.exact_block(SRC/'rdsource.F',"      diskfile = ' '","      call nc_open(ncid,diskfile,'OLD','READ')").replace('filepath','source')
    f=tests/'frozen.f'
    f.write_text(expand+opener+"""      subroutine add7_acquire(source,ncid)
      implicit none
      character(len=*),intent(in) :: source
      integer,intent(out) :: ncid
      character(len=120) :: diskfile
"""+rd+"      end subroutine\n")
    getfile=tests/'getfile.f'
    getfile.write_bytes((SRC/'getfile.F').read_bytes())
    source=probe.PROGRAM.replace('output(17), secout(16)','output(24), secout(23)')
    source=source.replace('start_day/=158','start_day/=151').replace('[158,0,0]','[151,0,0]')
    source=source.replace('any(source_start/=[172,0,0])','(source_start(1)/=80.and.source_start(1)/=172)')
    source=source.replace('year(1)/=2002.or.day(1)/=172','year(1)/=2002.or.day(1)/=source_start(1)')
    source=source.replace('clock(3), year(1), day(1)','clock(3), year(1), day(1), daydim, kpdim, ndays, nkp')
    source=source.replace('  character(120) :: diskfile','  logical :: probe_gpi_exists\n  character(120) :: diskfile')
    source=source.replace('  print \'(a,i0)\', \'SOURCE_EXPANDED_LENGTH=\',len_trim(source)', '''  if (len_trim(source)>120) stop 72
  call getfile(gpi_ncfile,path)
  call nc_open(ncid,path,'OLD','READ')
  call ck(nf_inq_dimid(ncid,'ndays',daydim))
  call ck(nf_inq_dimid(ncid,'nkp',kpdim))
  call ck(nf_inq_dimlen(ncid,daydim,ndays))
  call ck(nf_inq_dimlen(ncid,kpdim,nkp))
  if (ndays/=28.or.nkp/=8) stop 73
  call ck(nf_close(ncid))
  print '(a)', 'GPI_NATIVE_28X8_PASS'
  print '(a,i0)', 'SOURCE_EXPANDED_LENGTH=',len_trim(source)''')
    first=source.index("  diskfile=' '")
    end=source.index("  if (ncid==0)",first)
    source=source[:first]+"  call add7_acquire(source,ncid)\n"+source[end:]
    fields=', &\n    '.join(','.join(repr(k) for k in REQUIRED[i:i+6]) for i in range(0,34,6))
    prog=tests/'probe.f90'
    prog.write_text(source.replace('@FIELDS@',fields))
    binary=tests/'probe_local'
    env=v47.v46.env.runtime_environment()
    stack=ROOT/'.envs/tiegcm'
    args=[str(stack/'bin/x86_64-conda-linux-gnu-gfortran'),'-ffixed-line-length-132','-I'+str(stack/'include'),
          str(f),str(getfile),str(prog),'-L'+str(stack/'lib'),'-lnetcdff','-lnetcdf','-o',str(binary)]
    subprocess.run(args,cwd=tests,env=env,check=True,timeout=60)
    link=subprocess.check_output(['ldd',str(binary)],env=env,text=True)
    require(str(stack/'lib/libnetcdff.so.7') in link and 'not found' not in link,'Wrong probe runtime')
    require(v47.sha(stack/'lib/libnetcdff.so.7')==v47.load(v47.v45.OUT/'preflight.json')['netcdff_sha256'],'Wrong lib SHA')
    receipts=[]
    for i, path in enumerate(files):
        p=safe_source(cwd,'../'+SEEDS[i])
        r=subprocess.run([str(binary),str(path)],cwd=cwd,env=env,text=True,stderr=subprocess.STDOUT,
                         stdout=subprocess.PIPE,timeout=45)
        (tests/f'{RUNS[i]}_readonly.txt').write_text(r.stdout)
        require(r.returncode==0 and r.stdout.count('FIELD_READ=')==34 and
                'READONLY_SEED_PASS' in r.stdout and 'GPI_NATIVE_28X8_PASS' in r.stdout and
                'SOURCE_EXPANDED_LENGTH=7' in r.stdout,'Fortran cold-source/GPI read failed')
        receipts.append(dict(role='AB'[i],seed_sha256=v47.sha(p),clock=[CLOCK[i],0,0],required_fields=34,
                             probe_exit=0,source_bytes=7,GPI_dimensions=[28,8]))
    return receipts


def main():
    check_gpu(os.environ)
    require(OUT.resolve()==OUT,'Unsafe destination')
    gp=v47.load(OUT/'GPI_verification.json')
    gpi.verify_sha(gpi.FILE,gp['SHA256'])
    require(gp['numeric']=='GPI_NUMERIC_VERIFIED','GPI not verified')
    e=v47.archived_protocol()
    exits=[e[v47.v46.A],e[v47.v46.B]]
    resources=v47.pins(exits[0])
    budget=v47.load(gpi.V49/'future_design.json')['plans'][1]
    require(budget['estimated_minutes_per_run']*60<4770 and
            budget['estimated_NetCDF_bytes_per_run']<5*2**30,'V50 capacity review needed')
    template=v47.INPUT.read_text()
    gpi.verify_sha(v47.INPUT,v47.load(v47.OUT/'preparation.json')['new_input_sha256'])
    texts=expected_pair(template)
    diff=validate(texts,texts)
    files=[]
    seeds=[]
    for i,p in enumerate(exits):
        target=OUT/SEEDS[i]
        origin=ROOT/p['source']['path']
        require(inspect_restart(origin,[CLOCK[i],0,0])['structure_complete'],'Required source fields')
        with Dataset(origin) as n:
            require(int(n['year'][0])==2002 and n['f107d'][0]==200 and n['f107a'][0]==200,'Wrong startup source')
        if target.exists():
            require(v47.sha(target)==p['source']['SHA256'] and target.resolve()==target and
                    not target.stat().st_mode&0o222, 'Staged seed drift')
        else:
            stage_copy(origin,target,p['source']['SHA256'])
        path=OUT/(RUNS[i]+'.namelist')
        if path.exists():
            require(path.resolve()==path and path.read_text()==texts[i], 'Staged config drift')
        else:
            with path.open('x') as f:f.write(texts[i])
        files.append(path)
        seeds.append(dict(source=str(origin.relative_to(ROOT)),readonly_copy=SEEDS[i],
                          SHA256=p['source']['SHA256'],SOURCE_START=[CLOCK[i],0,0],copy_bytes=target.stat().st_size))
    probe_result=fortran_probe(files)
    require(all(v47.absent(OUT/name) for name in RUNS),'Future model output directory occupied')
    gpi.dump('configuration.json',dict(state='ADD7_AB_CONFIG_VERIFIED',runtime='GPI_RUNTIME_NOT_RUN',
        windows={'start':gpi.START.isoformat(),'stop':gpi.STOP.isoformat(),'target':gpi.TARGET.isoformat()},
        schedule=derive_calendar(),A_B_diff=diff,seeds=seeds,Fortran_probe=probe_result,resources=resources,
        GPI=dict(path=str(gpi.FILE.relative_to(ROOT)),SHA256=gp['SHA256']),
        model=exits[0]['executable'],MPI=exits[0]['mpirun'],
        config_sha={p.name:v47.sha(p) for p in files},model_launches=0))
    gpi.dump(PLAN.name,dict(status='ENGINEERING_ONLY_PREPARATION',roles=['A','B'],work_directories=list(RUNS),
        chronology='A then independent engineering PASS before B',MPI=4,OMP=1,GPU=0,STEP=60,steps=33120,
        wall_hard_seconds=4800,cleanup_trigger_seconds=4770,RSS_budget_GiB=16,output_budget_GiB=5,
        per_volume_MiB=256,start_free_GiB=25,running_free_GiB=20,
        restart=False,authenticated_V51_required=True,formal_launch_claims=0,automatic_retry=False,
        configuration_sha256=v47.sha(OUT/'configuration.json'),budget_estimate=budget,
        shared_supervisor_lock='experiments/thermosphere_autumn_mareqx_config_v23/autumn_execution_lock_local',
        same_target_UTC_hours={'V48_target':336,'V50_target':504,'V48_late':[360,384],'V50_late':[528,552]},
        rules_sha256=v47.sha(v47.ROOT/'experiments/tiegcm_2021_spinup_14day_v1/frozen_comparison_rules.json'),
        official_V37_admission=False,Swarm_target_density_reads=0))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true',help=argparse.SUPPRESS)
    arguments=parser.parse_args()
    if arguments.execute:
        parser.error('V50 prepares candidates only; new V51 authorization and integration runner required')
    main()
