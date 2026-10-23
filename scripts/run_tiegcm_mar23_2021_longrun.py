"""One-shot 2021 ten-day continuous integration; prepare and execute are separate gates."""
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
    return (series([(75,0,0)],[(85,0,0)],[(1,0,0)],1),
            series([(75,1,0)],[(85,0,0)],[(0,1,0)],24))

def configuration():
    prim,sec=schedules();text=s.configuration()
    vals={'LABEL':"'INDEPENDENT_TIEGCM_DATA_GENERATION; 2021 ten-day; spinup UNVERIFIED'",'START':'75 0 0','START_DAY':'75','STOP':'85 0 0','HIST':'1 0 0','MXHIST_PRIM':'1',
          'OUTPUT':', '.join(f"'primary_{i:03d}.nc'" for i in range(1,len(prim)+1)),
          'SECSTART':'75 1 0','SECSTOP':'85 0 0','SECHIST':'0 1 0','MXHIST_SECH':'24',
          'SECOUT':', '.join(f"'secondary_{i:03d}.nc'" for i in range(1,len(sec)+1))}
    for k,v in vals.items():
        text,n=re.subn(rf'(?m)^\s*{k}\s*=.*$',f' {k} = {v}',text);assert n==1,k
    return text

def validate(text):
    if text!=configuration():raise ValueError('Only reviewed ten-day 2021 configuration accepted')
    if re.search(r'(?im)^\s*(F107|F107A|KP|POWER|CTPOTEN)(?:_TIME)?\s*=',text):raise ValueError('Driver override')
    p,q=schedules();assert len(p)==11 and len(q)==10
    flat=sum(q,[]);assert len(flat)==len(set(flat))==240
    assert sum(t>=82*86400 for t in flat)==73
    assert 'SOURCE_START = 80 0 0' in text and 'START_YEAR = 2021' in text


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
        cold=(times==[75,0,0]).all(axis=1)
        if cold.any():
            assert np.flatnonzero(cold).tolist()==[0] and n.run_type=='initial'
            assert int(n['time'].initial_year)==2021 and int(n['time'].initial_day)==75
            assert np.array_equal(n['time'].initial_mtime,[75,0,0])
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
    pre=s.preflight();drv=GpiDriver(s.GPI)
    for minute in range(14401):
        sec=75*86400+minute*60;drv.at(2021000+sec//86400,sec%86400)
    available=int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1])*1024
    assert available>16*1024**3 and len(os.sched_getaffinity(0))>=4
    with Dataset(s.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc') as n:assert all(k in n.variables for k in REQUIRED)
    history=json.loads((ROOT/'experiments/tiegcm2023_s7_continuous_v1/runtime_summary.json').read_text())
    estimate=history['elapsed_s']*14400/12970;assert estimate*1.5<3600
    # Check for competing TIE-GCM processes; never interrupt another task.
    assert not any('tiegcm2.0' in p.read_text(errors='ignore') for p in Path('/proc').glob('[0-9]*/comm') if p.exists()),'Another TIE-GCM process active'
    p,q=schedules()
    return {**pre,'expected_steps':14400,'mpi_ranks':4,'mem_available_bytes':available,'cpu_affinity_count':len(os.sched_getaffinity(0)),'primary_volume_seconds':p,'secondary_volume_seconds':q,'primary_records':11,'secondary_records':240,'candidate_records':73,'primary_files':11,'secondary_files':10,'estimated_wall_s':estimate,'safety_factor':1.5,'estimated_total_netcdf_bytes':11*17000000+240*8040000,'estimated_with_candidates_bytes':11*17000000+240*8040000+200000000,'wall_limit_s':3600,'cpu_per_process_limit_s':3900,'aggregate_rss_limit_bytes':16*1024**3,'generated_limit_bytes':5*1024**3,'volume_target_bytes':256*1024**2,'disk_floor_bytes':20*1024**3,'driver_every_minute_check':True,'continuation_used':False,'static_pass':True}

def limits():
    for key,val in [(resource.RLIMIT_CORE,0),(resource.RLIMIT_AS,8*1024**3),(resource.RLIMIT_FSIZE,256*1024**2),(resource.RLIMIT_CPU,3900)]:resource.setrlimit(key,(val,val))


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
    for k in ['executable_sha256','apex_sha256','gpi_sha256','restart_sha256']:assert pre[k]==now[k]
    logpath=ROOT/'logs'/f'{out.name}.log'
    if logpath.exists():raise FileExistsError(logpath)
    (out/'launch_once.json').open('x').write(json.dumps({'model_launches':1,'no_retry':True,'expected_steps':14400}))
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
                elif time.perf_counter()-lastchange>120:reason='log_stalled_120s'
                if not samples or elapsed-samples[-1]['wall_s']>=5:
                    samples.append({'wall_s':elapsed,'rss_bytes':rss,'generated_bytes':size,'completed_volumes_checked':len(checked)})
                    (out/'progress.json').write_text(json.dumps(samples[-1])+'\n')
            if elapsed>3600:reason='wall_timeout'
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
    p=argparse.ArgumentParser();p.add_argument('--run-tag',required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if a.run_tag!='tiegcm_training_mar23_v2_2021_longrun':raise ValueError('Only authorized fixed run tag')
    out=s.inside(ROOT/'experiments'/a.run_tag)
    execute(out) if a.execute else prepare(out)
if __name__=='__main__':main()
