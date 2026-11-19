"""V23 autumn-only cold-start gates; old spring executor and identities unchanged."""
from pathlib import Path
import os,json,re,shutil,subprocess,sys,time,uuid,fcntl
from .tiegcm_rank_exit import digest,write_once
from .supervisor import supervise,Limits
ROOT=Path(__file__).resolve().parents[2]
PACKAGE=ROOT/'experiments/thermosphere_autumn_mareqx_config_v23'
SEED='data/raw/tiegcm_2021_spinup_initial_condition_v1/tiegcm_res5.0_mareqx_smax_prim.nc'
SEED_SHA='a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7'
GPI_SHAS={2021:'d401d0ae525babb343faaa6d1dd9a8d3c4fb1c2ea85beb26d2b0025cdf001b9a',2022:'7d43db220fe7fbaded6b2182db8db32ee09cedf99dc5760815824ccf8298ebb2'}
class GateError(RuntimeError):pass
def require(ok,message):
    if not ok:raise GateError(message)
def inside(p):
    p=Path(p);require(p.resolve().is_relative_to(ROOT),'Path outside project');return p

def namelist(text):
    matches=list(re.finditer(r'(?mi)^\s*([A-Z][A-Z0-9_]*)\s*=',text));result={}
    for i,m in enumerate(matches):
        require(m[1] not in result,'Duplicate input field');result[m[1]]=text[m.end():matches[i+1].start() if i+1<len(matches) else text.rfind('/')].strip()
    return result

def expected_input(year):
    require(year in GPI_SHAS,'Unsupported year')
    text=(ROOT/'experiments/tiegcm_2022_mar25_preparation_v1/run/input.inp').read_text()
    edits={'LABEL':f"'AUTUMN MAREQX RESTRICTED; {year}; ADAPTATION/SPINUP UNVERIFIED'",'START_YEAR':str(year),'START_DAY':'252','START':'252 0 0','STOP':'268 0 0','SECSTART':'252 1 0','SECSTOP':'268 0 0','OUTPUT':', '.join(f"'primary_{i:03d}.nc'" for i in range(1,18)),'SECOUT':', '.join(f"'secondary_{i:03d}.nc'" for i in range(1,17)),'GPI_NCFILE':f"'$PROJECTROOT/experiments/thermosphere_autumn_gpi_seed_policy_v22/gpi_{year}_autumn.nc'"}
    for k,v in edits.items():
        text,n=re.subn(rf'(?m)^\s*{k}\s*=.*$',f' {k} = {v}',text);require(n==1,'Spring schema changed '+k)
    return text.replace(str(ROOT),'$PROJECTROOT')

def validate_input(text,year):
    require(text==expected_input(year),'Unexpected physical fields/path/year/output change')
    a=namelist(text)
    require(a['SOURCE_START']=='80 0 0' and a['START']=='252 0 0','Illegal native source record/target clock')
    require(a['STEP']=='60' and a['CALENDAR_ADVANCE']=='1','Step/calendar changed')
    require(not set(a)&{'KP','POWER','CTPOTEN','F107','F107A','IMF_NCFILE'},'Driver override')
    return a

def validate_native_source(path):
    import numpy as np
    from netCDF4 import Dataset
    from atmosphere.restart_validation import inspect_restart
    with Dataset(path) as n:
        require(n.data_model=='NETCDF3_CLASSIC' and n.history_type=='primary','Wrong native primary format')
        require(np.array_equal(n['year'][:],[2002]) and np.array_equal(n['mtime'][:],[[80,0,0]]),'Source native identity changed')
        for k,size in [('lat',36),('lon',72),('lev',29),('ilev',29)]:
            require(len(n.dimensions[k])==size and np.array_equal(n[k][:],np.load(ROOT/f'data/processed/static/{k}.npy')),'Source/model grid mismatch '+k)
    a=inspect_restart(path,[80,0,0]);require(a['structure_complete'] and a['record_available'],'Incomplete native34-state source')
    return True

def claim(directory):
    directory=inside(directory);directory.mkdir(exist_ok=False);return directory

def validate_binding(p):
    y=p['year'];require(y in GPI_SHAS,'Year not frozen');folder=PACKAGE/str(y)
    require(p['cwd']==str((folder/'actual_run').relative_to(ROOT)),'Shared/spring/wrong year working directory')
    require(p['input']['path']==str((folder/'input.inp').relative_to(ROOT)),'Wrong input binding')
    require(p['source']==dict(path=SEED,SHA256=SEED_SHA),'Wrong seed binding')
    require(p['GPI']['path']==f'experiments/thermosphere_autumn_gpi_seed_policy_v22/gpi_{y}_autumn.nc' and p['GPI']['SHA256']==GPI_SHAS[y],'Wrong year/GPI SHA')
    require((p['start_UTC'],p['stop_UTC'],p['steps'])==(f'{y}-09-09T00:00:00Z',f'{y}-09-25T00:00:00Z',23040),'Wrong integration calendar')
    require(p['MPI']==4 and p['OMP']==1,'MPI/OMP changed')
    return folder

def verify_package(year):
    require(year in GPI_SHAS,'Unsupported year')
    release=json.loads((PACKAGE/'execution_release.json').read_text());require(release['static_checks_PASS'],'Static release incomplete')
    for n,wanted in release['SHA256'].items():require(digest(inside(ROOT/n))==wanted,'Frozen release changed: '+n)
    policy=json.loads((PACKAGE/'seed_policy_receipt.json').read_text())
    require(policy['SEED_POLICY']=='A_MAREQX_APPROVED' and policy['actual_model_authorized_this_task'] is False,'Missing restricted A policy')
    p=json.loads((PACKAGE/str(year)/'launch_protocol.json').read_text());folder=validate_binding(p)
    validate_input((ROOT/p['input']['path']).read_text(),year)
    for a in [p['source'],p['GPI'],p['input'],p['executable'],p['mpirun'],p['observation'],p['hapi']]:require(digest(inside(ROOT/a['path']))==a['SHA256'],'Frozen asset SHA mismatch: '+a['path'])
    for name,wanted in release['scientific_asset_SHA256'].items():require(digest(inside(ROOT/name))==wanted,'Scientific dependency changed: '+name)
    validate_native_source(ROOT/p['source']['path'])
    return p

def runtime_environment():
    env=dict(os.environ,PROJECTROOT=str(ROOT),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='',OMPI_ALLOW_RUN_AS_ROOT='1',OMPI_ALLOW_RUN_AS_ROOT_CONFIRM='1',OMPI_MCA_pml='ob1',OMPI_MCA_btl='self,tcp',OMPI_MCA_osc='rdma',PMIX_MCA_gds='hash')
    env['HOST']=__import__('socket').gethostname();env['LOGNAME']=__import__('getpass').getuser()
    return env

def environment_review(p):
    env=runtime_environment();binary=ROOT/p['executable']['path'];linked=subprocess.check_output(['ldd',str(binary)],text=True,env=env);require('not found' not in linked,'Missing runtime dependency');actual={}
    for line in linked.splitlines():
        m=re.search(r'=>\s+(\S+)\s+\(',line)
        if m:actual[line.split()[0]]=digest(Path(m[1]).resolve())
    old=json.loads((ROOT/'experiments/tiegcm_2022_mar25_preparation_v1/environment_audit.json').read_text())
    for e in old['dependencies']:require(actual.get(e['name'])==e['SHA256'],'Runtime dependency drift '+e['name'])
    version=subprocess.check_output([str(ROOT/p['mpirun']['path']),'--version'],env=env,text=True).splitlines()[0]
    available=int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1])*1024
    active=[]
    for q in Path('/proc').glob('[0-9]*/comm'):
        try:
            if q.read_text().strip()=='tiegcm2.0':active.append(int(q.parent.name))
        except FileNotFoundError:pass
    free=shutil.disk_usage(ROOT).free
    return dict(library_SHA256=actual,libraries_match_spring=True,MPI_version=version,CPU_affinity_count=len(os.sched_getaffinity(0)),MemAvailable_bytes=available,disk_free_bytes=free,active_model_count=len(active),resource_ready=free>=25*2**30 and available>=16*2**30 and len(os.sched_getaffinity(0))>=4 and not active,monitoring='session sampling/signals; not OS cgroup isolation')

def execute(year,authorized=False):
    require(authorized,'No explicit single-year 16-day user authorization: launch refused')
    # flock prevents cross-year concurrent starts; per-year mkdir is permanent no-retry identity.
    lock=inside(PACKAGE/'autumn_execution_lock_local').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:lock.close();raise GateError('Another autumn execution owns the lock')
    try:
        p=verify_package(year);review=environment_review(p);require(review['resource_ready'],'Startup resource/active model gate failed')
        folder=PACKAGE/str(year);run=ROOT/p['cwd'];require(not run.exists() and not (folder/'execution_claim_local.json').exists(),'Run already reserved/attempted; no retry')
        if year==2022:
            prior=json.loads((PACKAGE/'2021/postrun_audit_local/acceptance.json').read_text());require(prior['overall']=='PASS' and prior['ACTUAL_MODEL_RUN']=='ATTEMPTED','2021 engineering acceptance required before separately-authorized 2022 run')
        run=claim(run);run_id=uuid.uuid4().hex
        write_once(folder/'execution_claim_local.json',dict(run_id=run_id,year=year,attempts=1,automatic_retry=False,claimed_unix=time.time()))
        try:
            wrapper=ROOT/'src/runtime/tiegcm_rank_exit.py'
            argv=[str(ROOT/p['mpirun']['path']),'-np','4',sys.executable,str(wrapper),'--model',str(ROOT/p['executable']['path']),'--run-id',run_id,'--model-sha',p['executable']['SHA256'],'--input-sha',p['input']['SHA256']]
            st=supervise(argv,run,Limits(4770,16*2**30,20*2**30,5*2**30,256*2**20,.25,2,3,120,5*2**30),env=runtime_environment(),total_dir=run,input_files={'input.inp':(ROOT/p['input']['path']).read_bytes()})
            write_once(folder/'execution_result_local.json',dict(run_id=run_id,year=year,ACTUAL_MODEL_RUN='ATTEMPTED',supervisor_qualification=st['qualification'],returncode=st['returncode'],engineering='NOT_RUN'))
            require(st['qualification']=='PASS' and st['returncode']==0,'Model wait failed/unknown; preserve reservation, no retry')
            audit=claim(folder/'postrun_audit_local')
            argv=[sys.executable,str(ROOT/'scripts/audit_tiegcm_autumn_v23.py'),'--year',str(year),'--run-id',run_id,'--output',str(audit/'acceptance.json')]
            ast=supervise(argv,audit,Limits(600,4*2**30,20*2**30,150*2**20,20*2**20,.25,1,3,120,150*2**20),env=runtime_environment(),total_dir=audit)
            require(ast['returncode']==0 and ast['qualification']=='PASS','Read-only acceptance incomplete; no retry')
            result=json.loads((audit/'acceptance.json').read_text());require(result['overall']=='PASS','Engineering acceptance failed')
            return result
        except BaseException as e:
            if not (folder/'execution_failure_local.json').exists():write_once(folder/'execution_failure_local.json',dict(run_id=run_id,error=type(e).__name__,message=str(e).replace(str(ROOT),'$PROJECT'),reservation_preserved=True,no_retry=True,actual_state='FAILED_OR_UNKNOWN; inspect direct wait receipts'))
            raise
    finally:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
