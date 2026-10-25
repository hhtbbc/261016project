"""One-shot second-initial-state 2021 controlled integration; prepare and execute are separate gates."""
from pathlib import Path
import argparse, importlib.util, sys, json, re, os, resource, shutil, time
import subprocess, signal, socket, getpass, datetime
import numpy as np
from netCDF4 import Dataset
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from atmosphere.tiegcm_drivers import GpiDriver
from atmosphere.restart_validation import REQUIRED
spec=importlib.util.spec_from_file_location('old_s7',ROOT/'scripts/run_tiegcm2023_s7.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);c=old.c
spec=importlib.util.spec_from_file_location('mar23',ROOT/'scripts/run_tiegcm_mar23_diagnostic.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s);s.YEAR=2021;s.GPI=ROOT/'data/processed/training_window_mar23_v2/gpi_2021_mar23_v2.nc'
def stream_sha(path):
    import hashlib
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
    return h.hexdigest()
s.sha=stream_sha


def series(starts,stops,intervals,capacity):
    """numfiles.F: a new volume at each series, no repeated touching point."""
    volumes=[]
    for i,(a,b,h) in enumerate(zip(starts,stops,intervals)):
        lo=c.seconds(a);hi=c.seconds(b);step=c.seconds(h)
        if i and a==stops[i-1]:lo+=step
        values=list(range(lo,hi+1,step))
        if not values or values[-1]!=hi:raise ValueError('Nonintegral output schedule')
        volumes.extend([values[j:j+capacity] for j in range(0,len(values),capacity)])
    return volumes


def schedules():
    return (series([(68,0,0)],[(85,0,0)],[(1,0,0)],1),
            series([(68,1,0)],[(85,0,0)],[(0,1,0)],24))

GROUP='A14'
CASE=ROOT/'experiments/tiegcm_2021_spinup_14day_v1'
A_DIR=ROOT/'experiments/tiegcm_training_mar23_v2_2021_longrun'
B_SOURCE=ROOT/'data/raw/tiegcm_2021_spinup_initial_condition_v1/tiegcm_res5.0_mareqx_smax_prim.nc'

def configuration():
    text=(A_DIR/'input.inp').read_text()
    assert s.sha(A_DIR/'input.inp')==json.loads((A_DIR/'preflight.json').read_text())['input_sha256']
    for key,value in {'START_DAY':'68','START':'68 0 0','SECSTART':'68 1 0','OUTPUT':', '.join(f"'primary_{i:03d}.nc'" for i in range(1,19)),'SECOUT':', '.join(f"'secondary_{i:03d}.nc'" for i in range(1,18)),'GPI_NCFILE':"'"+str(ROOT/'data/processed/tiegcm_2021_spinup_14day_v1/gpi_2021_14day.nc')+"'"}.items():
        text,count=re.subn(rf'(?m)^\s*{key}\s*=.*$',f' {key} = {value}',text);assert count==1
    if GROUP=='B14':text=text.replace(str(s.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc'),str(B_SOURCE))
    return text

def validate(text):
    if text!=configuration():raise ValueError('Only SOURCE may differ from frozen A namelist')
    assert 'SOURCE_START = 80 0 0' in text and 'START_YEAR = 2021' in text
    if re.search(r'(?im)^\s*(F107|F107A|KP|POWER|CTPOTEN)(?:_TIME)?\s*=',text):raise ValueError('Driver override')
    p,q=schedules();assert len(p)==18 and len(q)==17 and len(sum(q,[]))==408


def field(v):
    v.set_auto_mask(False);a=np.asarray(v[:]);mask=np.zeros(a.shape,bool)
    for name in ['missing_value','_FillValue']:
        if name in v.ncattrs():
            for m in np.asarray(v.getncattr(name)).reshape(-1):mask|=a==np.asarray(m,dtype=a.dtype)
    mask|=abs(a)>1e30
    if not np.isfinite(a).all():raise ValueError('Nonfinite '+v.name)
    return np.ma.array(a,mask=mask)


def basic_file(path):
    """Cold echo exemption applies ONLY to native uncomputed DEN/ZG/N2 diagnostics.

    Cold TN/wind/composition remain checked. Warm diagnostic fills always fail.
    The identity must match the first initial-run record and time attributes.
    """
    with Dataset(path) as n:
        if n.history_type=='primary':
            for name in REQUIRED:
                if name not in n.variables or n[name].dtype!=np.dtype('float64'):raise ValueError('Incomplete primary '+name)
                value=field(n[name])
                if value.count()==0:raise ValueError('Empty primary '+name)
            return
        times=np.asarray(n['mtime'][:],int);years=np.asarray(n['year'][:],int)
        assert np.all(years==2021)
        cold=(times==[68,0,0]).all(axis=1)
        if cold.any():
            assert np.flatnonzero(cold).tolist()==[0] and n.run_type=='initial'
            assert int(n['time'].initial_year)==2021 and int(n['time'].initial_day)==68
            assert np.array_equal(n['time'].initial_mtime,[68,0,0])
        for name in ['DEN','ZG']:
            if name not in n.variables:
                if not cold.all():raise ValueError('Missing warm '+name)
                continue
            v=field(n[name]);mask=np.ma.getmaskarray(v)
            for i in range(len(times)):
                if cold[i] and mask[i].all():continue
                if mask[i].any():raise ValueError('Incomplete diagnostic '+name)
                if name=='DEN' and not (v[i]>0).all():raise ValueError('Nonpositive density')
                if name=='ZG' and not (np.diff(v[i],axis=0)>0).all():raise ValueError('Unordered ZG')
        values={}
        for name in ['TN','UN','VN','O1','O2','N2','HE']:
            if name not in n.variables:raise ValueError('Missing prognostic '+name)
            v=field(n[name]);mask=np.ma.getmaskarray(v)
            if name in ['TN','UN','VN']:
                if mask[:,:-1].any() or not mask[:,-1].all():raise ValueError('Incorrect padding '+name)
                if name=='TN' and not (v.min()>100 and v.max()<5000):raise ValueError('Temperature range')
                if name!='TN' and abs(v).max()>=2e5:raise ValueError('Wind range')
            else:
                if name=='N2' and cold.any():
                    if not mask[cold].all():raise ValueError('Unexpected cold N2: expected uncomputed native fill')
                    v=v[~cold];mask=np.ma.getmaskarray(v)
                    if not v.size:continue
                if mask.any() or v.min()<0 or v.max()>1.000001:raise ValueError('Composition '+name)
                values[name]=v
        if (~cold).any():
            total=sum(values[name] if name=='N2' else values[name][~cold] for name in ['O1','O2','N2','HE'])
            if abs(total-1).max()>=1e-5:raise ValueError('Mass mixing ratios do not sum to one')


def preflight():
    if GROUP=='B14':
        status=json.loads((CASE/'A14/run_status.json').read_text());assert status['returncode']==0 and status['stop_reason'] is None
        assert json.loads((CASE/'A14/data_audit.json').read_text())['engineering_PASS']
    # Audit the original installation before binding the new, separately audited GPI.
    s.GPI=ROOT/'data/processed/training_window_mar23_v2/gpi_2021_mar23_v2.nc';pre=s.preflight()
    s.GPI=ROOT/'data/processed/tiegcm_2021_spinup_14day_v1/gpi_2021_14day.nc'
    audit=json.loads((CASE/'driver_audit.json').read_text());assert audit['status']=='PASS' and s.sha(s.GPI)==audit['SHA256']
    initial=json.loads((CASE/'initial_state_audit.json').read_text());source=B_SOURCE if GROUP=='B14' else s.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc'
    assert s.sha(source)==initial['B_SHA256' if GROUP=='B14' else 'A_SHA256']
    for parent in [A_DIR,ROOT/'experiments/tiegcm_training_mar23_v2_2022_longrun',ROOT/'experiments/tiegcm_2021_spinup_initial_condition_v1/B']:
        for entry in json.loads((parent/'data_audit.json').read_text())['files']:assert s.sha(parent/entry['file'])==entry['SHA256']
    for year in [2021,2022]:
        for entry in json.loads((ROOT/f'experiments/tiegcm_training_mar23_v2_{year}_longrun/candidate_audit.json').read_text())['frames']:assert s.sha(ROOT/entry['file'])==entry['SHA256']
    drv=GpiDriver(s.GPI)
    for minute in range(24481):
        absolute=68*86400+minute*60;drv.at(2021000+absolute//86400,absolute%86400)
    available=int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1])*1024
    free=shutil.disk_usage(ROOT).free;estimate=json.loads((A_DIR/'run_status.json').read_text())['elapsed_s']*1.7
    assert estimate*1.5<4800 and available>16*1024**3 and free>32*1024**3
    assert not any('tiegcm2.0' in p.read_text(errors='ignore') for p in Path('/proc').glob('[0-9]*/comm') if p.exists())
    p,q=schedules();assert len(p)==18 and len(q)==17 and len(sum(q,[]))==408
    return {**pre,'group':GROUP,'expected_steps':24480,'gpi_sha256':s.sha(s.GPI),'restart_sha256':s.sha(source),'frozen_comparison_rules_SHA256':s.sha(CASE/'frozen_comparison_rules.json'),'free_disk_bytes':free,'mem_available_bytes':available,'estimated_wall_s':estimate,'safety_factor':1.5,'estimated_netcdf_bytes':18*17000000+408*8040000,'expected_primary':18,'expected_secondary':408,'primary_volume_seconds':p,'secondary_volume_seconds':q,'wall_limit_s':4800,'total_wall_limit_s':9600,'per_group_generated_limit_bytes':5*1024**3,'total_generated_limit_bytes':12*1024**3,'disk_floor_bytes':20*1024**3,'expected_drivers':{str(v):drv.at(2021068,v) for v in range(0,601,60)},'static_pass':True}

def limits():
    for key,val in [(resource.RLIMIT_CORE,0),(resource.RLIMIT_AS,8*1024**3),(resource.RLIMIT_FSIZE,256*1024**2),(resource.RLIMIT_CPU,4900)]:resource.setrlimit(key,(val,val))


def prepare(out):
    if out.exists():raise FileExistsError(out)
    text=configuration();validate(text);pre=preflight();protected={}
    for base in ['third_party/TIEGCM2.0','data','experiments','results','reports']:
        for f in (ROOT/base).rglob('*'):
            if f.is_file() and not f.is_symlink():protected[str(f.relative_to(ROOT))]=s.sha(f)
    out.mkdir();(out/'input.inp').write_text(text);pre['input_sha256']=s.sha(out/'input.inp');pre['runner_sha256']=s.sha(Path(__file__))
    (out/'preflight.json').write_text(json.dumps(pre,indent=2)+'\n');(out/'protected_files.json').write_text(json.dumps(protected,indent=2)+'\n');print('STATIC PASS',out)


def execute(out):
    pre=json.loads((out/'preflight.json').read_text());validate((out/'input.inp').read_text());assert s.sha(out/'input.inp')==pre['input_sha256']
    assert s.sha(Path(__file__))==pre['runner_sha256'],'Runner changed after preflight'
    assert not (out/'launch_once.json').exists(),'Single authorized launch already consumed'
    now=preflight()
    for k in ['executable_sha256','apex_sha256','gpi_sha256','restart_sha256','frozen_comparison_rules_SHA256']:assert pre[k]==now[k]
    logpath=ROOT/'logs'/f'tiegcm_2021_14day_{GROUP}.log'
    if logpath.exists():raise FileExistsError(logpath)
    (out/'launch_once.json').open('x').write(json.dumps({'model_launches':1,'no_retry':True,'expected_steps':24480}))
    env=dict(os.environ,OMPI_ALLOW_RUN_AS_ROOT='1',OMPI_ALLOW_RUN_AS_ROOT_CONFIRM='1',OMPI_MCA_pml='ob1',OMPI_MCA_btl='self,tcp',OMPI_MCA_osc='rdma',PMIX_MCA_gds='hash',HOST=socket.gethostname(),LOGNAME=getpass.getuser(),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='')
    (out/'runtime_environment.json').write_text(json.dumps({k:env[k] for k in ['TMPDIR','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','CUDA_VISIBLE_DEVICES','OMPI_MCA_pml','OMPI_MCA_btl']},indent=2)+'\n')
    started=datetime.datetime.now(datetime.timezone.utc).isoformat();start=time.perf_counter();peak=0;reason=None;samples=[];checked=set();lastchange=start;lastsize=0;lastscan=0
    with logpath.open('x') as log:
        proc=subprocess.Popen(['mpirun','-np','4',str(s.BUILD/'tiegcm2.0'),'input.inp'],cwd=out,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True,preexec_fn=limits)
        while proc.poll() is None:
            elapsed=time.perf_counter()-start;rss=c.process_tree_rss(proc.pid);peak=max(peak,rss)
            if elapsed-lastscan>=1:
                lastscan=elapsed;size=sum(f.stat().st_size for f in out.rglob('*') if f.is_file())+logpath.stat().st_size
                if logpath.stat().st_size!=lastsize:lastsize=logpath.stat().st_size;lastchange=time.perf_counter()
                contents=logpath.read_text(errors='replace')
                if re.search(r'(?im)^.*(?:\bNaN\b|\bInf\b|ERROR|bad isec_req|MPI_ABORT).*$',contents):reason='fatal_log_pattern'
                for prefix in ['primary','secondary']:
                    files=sorted(out.glob(prefix+'_*.nc'))
                    for f in files[:-1]:
                        if str(f) not in checked:
                            try:basic_file(f);checked.add(str(f))
                            except Exception as e:reason='completed_volume_physical_check: '+repr(e)
                if size>5*1024**3:reason='total_output_limit'
                elif any(f.stat().st_size>256*1024**2 for f in out.glob('*.nc')):reason='volume_size_limit'
                elif shutil.disk_usage(ROOT).free<20*1024**3:reason='disk_floor'
                elif sum(f.stat().st_size for f in CASE.rglob('*') if f.is_file())>12*1024**3:reason='total_12GiB_limit'
                elif time.perf_counter()-lastchange>120:reason='log_stalled_120s'
                if not samples or elapsed-samples[-1]['wall_s']>=5:
                    samples.append({'wall_s':elapsed,'rss_bytes':rss,'generated_bytes':size,'completed_volumes_checked':len(checked)})
                    (out/'progress.json').write_text(json.dumps(samples[-1])+'\n')
            if elapsed>4800:reason='wall_timeout'
            elif GROUP=='B14' and elapsed+json.loads((CASE/'A14/run_status.json').read_text())['elapsed_s']>9600:reason='total_wall_timeout'
            elif rss>16*1024**3:reason='aggregate_RSS'
            if reason:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL)
                break
            time.sleep(.1)
        proc.wait()
    if not reason and proc.returncode==0:
        try:
            for f in sorted(out.glob('*.nc')):basic_file(f)
        except Exception as e:reason='final_volume_check: '+repr(e)
    usage=resource.getrusage(resource.RUSAGE_CHILDREN)
    status={'model_launches':1,'returncode':proc.returncode,'stop_reason':reason,'elapsed_s':time.perf_counter()-start,'started_utc':started,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'normal_exit_count':logpath.read_text().count('NORMAL EXIT'),'peak_sampled_tree_rss_bytes':peak,'children_user_cpu_s':usage.ru_utime,'children_system_cpu_s':usage.ru_stime,'resource_samples':samples,'completed_volumes_checked_online':len(checked),'netcdf_bytes':sum(f.stat().st_size for f in out.glob('*.nc')),'total_generated_bytes':sum(f.stat().st_size for f in out.rglob('*') if f.is_file())+logpath.stat().st_size,'rss_note':'sampled process group + descendants; shared pages counted repeatedly; transient peak may be missed'}
    (out/'run_status.json').write_text(json.dumps(status,indent=2)+'\n');print(json.dumps({k:v for k,v in status.items() if k!='resource_samples'},indent=2))
    if proc.returncode or reason or status['normal_exit_count']!=4:raise SystemExit(1)


def main():
    global GROUP
    p=argparse.ArgumentParser();p.add_argument('--run-tag',required=True);p.add_argument('--execute',action='store_true');p.add_argument('--group',choices=['A14','B14'],required=True);a=p.parse_args();GROUP=a.group
    if a.run_tag!='tiegcm_2021_spinup_14day_v1':raise ValueError('Only authorized controlled experiment')
    out=s.inside(ROOT/'experiments'/a.run_tag/GROUP)
    execute(out) if a.execute else prepare(out)
if __name__=='__main__':main()
