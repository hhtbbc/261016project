"""One-shot S3 continuous integration; prepare and execute are separate gates."""
from pathlib import Path
import argparse, importlib.util, sys, json, re, os, resource, shutil, time
import subprocess, signal, socket, getpass, datetime
import numpy as np
from netCDF4 import Dataset
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from atmosphere.tiegcm_drivers import GpiDriver
from atmosphere.restart_validation import REQUIRED
spec=importlib.util.spec_from_file_location('crossday',ROOT/'scripts/run_tiegcm2023_crossday.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c);s=c.startup


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
    return (series([(77,0,0),(82,0,0)],[(82,0,0),(82,0,10)],[(1,0,0),(0,0,10)],1),
            series([(77,0,0),(80,0,0)],[(80,0,0),(82,0,10)],[(1,0,0),(0,0,10)],24))


def configuration():
    p,q=schedules();text=s.configuration()
    vals={'LABEL':"'S3 continuous 2023 hindcast; 3-day candidate spin-up NOT proven converged'",'START':'77 0 0, 82 0 0','STOP':'82 0 0, 82 0 10','HIST':'1 0 0, 0 0 10','MXHIST_PRIM':'1',
          'OUTPUT':', '.join(f"'primary_{i:03d}.nc'" for i in range(1,len(p)+1)),
          'SECSTART':'77 0 0, 80 0 0','SECSTOP':'80 0 0, 82 0 10','SECHIST':'1 0 0, 0 0 10','MXHIST_SECH':'24',
          'SECOUT':', '.join(f"'secondary_{i:03d}.nc'" for i in range(1,len(q)+1))}
    for k,v in vals.items():
        text,n=re.subn(rf'(?m)^\s*{k}\s*=.*$',f' {k} = {v}',text)
        if n!=1:raise ValueError(k)
    return text


def validate(text):
    if text!=configuration():raise ValueError('Only reviewed fixed S3 configuration accepted')
    if re.search(r'(?im)^\s*(F107|F107A|KP|POWER|CTPOTEN)(?:_TIME)?\s*=',text):raise ValueError('Driver override')
    p,q=schedules();assert len(p)==7 and len(q)==14
    flat=sum(q,[]);assert len(flat)==293 and len(set(flat))==293
    assert sum(t>=80*86400 for t in flat)==290
    assert (82*86400+600-77*86400)//60==7210
    assert 'SOURCE_START = 80 0 0' in text and 'SOURCE =' in text


def field(v):
    v.set_auto_mask(False);a=np.asarray(v[:]);mask=np.zeros(a.shape,bool)
    for name in ['missing_value','_FillValue']:
        if name in v.ncattrs():
            for m in np.asarray(v.getncattr(name)).reshape(-1):mask|=a==np.asarray(m,dtype=a.dtype)
    mask|=abs(a)>1e30
    if not np.isfinite(a).all():raise ValueError('Nonfinite '+v.name)
    return np.ma.array(a,mask=mask)


def basic_file(path):
    with Dataset(path) as n:
        if n.history_type=='primary':
            for name in REQUIRED:
                assert name in n.variables and n[name].dtype==np.dtype('float64')
                field(n[name])
        else:
            # Native cold echo has no addfld diagnostics (output.F302-306).
            cold=(np.asarray(n['mtime'][:])==[77,0,0]).all(axis=1)
            active=~cold
            if not active.any():return
            den=field(n['DEN'])[active];z=field(n['ZG'])[active]
            assert not np.ma.getmaskarray(den).any() and den.min()>0
            assert not np.ma.getmaskarray(z).any() and (np.diff(z,axis=1)>0).all()
            tn=field(n['TN'])[active];assert tn.min()>100 and tn.max()<5000
            for k in ['UN','VN']:assert abs(field(n[k])[active]).max()<2e5
            for k in ['O1','O2','N2','HE']:
                v=field(n[k])[active];assert v.min()>=0 and v.max()<=1.000001
            total=sum(field(n[k])[active] for k in ['O1','O2','N2','HE']);assert abs(total-1).max()<1e-5


def preflight():
    pre=s.preflight();old=json.loads((ROOT/'experiments/tiegcm2023_crossday_24h10_v1/preflight.json').read_text())
    for k in ['executable_sha256','apex_sha256','gpi_sha256','restart_sha256']:assert pre[k]==old[k]
    assert shutil.disk_usage(ROOT).free>24*1024**3
    available=int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1])*1024
    assert available>16*1024**3 and len(os.sched_getaffinity(0))>=4
    hard=resource.getrlimit(resource.RLIMIT_CPU)[1];assert hard==resource.RLIM_INFINITY or hard>=2100
    drv=GpiDriver(s.GPI)
    for minutes in range(7211):
        sec=77*86400+minutes*60;drv.at(2023000+sec//86400,sec%86400)
    with Dataset(s.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc') as n:
        assert all(k in n.variables for k in REQUIRED)
    p,q=schedules()
    return {**pre,'static_pass':True,'cpu_affinity_count':len(os.sched_getaffinity(0)),'mem_available_bytes':available,'expected_steps':7210,'mpi_ranks':4,'primary_volume_seconds':p,'secondary_volume_seconds':q,'primary_records':7,'secondary_records':293,'common_window_records':290,'primary_files':7,'secondary_files':14,'max_secondary_records_per_volume':24,'estimated_max_secondary_bytes':24*8027108+200000,'estimated_total_netcdf_bytes':2470895072,'wall_limit_s':1800,'cpu_per_process_limit_s':2100,'aggregate_rss_limit_bytes':16*1024**3,'generated_limit_bytes':4*1024**3,'volume_target_bytes':256*1024**2,'disk_floor_bytes':20*1024**3,'driver_every_minute_check':True,'continuation_used':False,'numfiles_source':'third_party/TIEGCM2.0/src/numfiles.F:103-152; new volume at series boundary'}


def limits():
    for key,val in [(resource.RLIMIT_CORE,0),(resource.RLIMIT_AS,8*1024**3),(resource.RLIMIT_FSIZE,256*1024**2),(resource.RLIMIT_CPU,2100)]:resource.setrlimit(key,(val,val))


def prepare(out):
    if out.exists():raise FileExistsError(out)
    text=configuration();validate(text);pre=preflight();protected={}
    for base in ['third_party/TIEGCM2.0','data','experiments','results','reports']:
        for f in (ROOT/base).rglob('*'):
            if f.is_file() and not f.is_symlink():protected[str(f.relative_to(ROOT))]=s.sha(f)
    out.mkdir();(out/'input.inp').write_text(text);pre['input_sha256']=s.sha(out/'input.inp')
    (out/'preflight.json').write_text(json.dumps(pre,indent=2)+'\n');(out/'protected_files.json').write_text(json.dumps(protected,indent=2)+'\n');print('STATIC PASS',out)


def execute(out):
    pre=json.loads((out/'preflight.json').read_text());validate((out/'input.inp').read_text());assert s.sha(out/'input.inp')==pre['input_sha256']
    now=preflight()
    for k in ['executable_sha256','apex_sha256','gpi_sha256','restart_sha256']:assert pre[k]==now[k]
    logpath=ROOT/'logs'/f'{out.name}.log'
    if logpath.exists():raise FileExistsError(logpath)
    (out/'launch_once.json').open('x').write(json.dumps({'model_launches':1,'no_retry':True,'expected_steps':7210}))
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
                if size>4*1024**3:reason='total_output_limit'
                elif any(f.stat().st_size>256*1024**2 for f in out.glob('*.nc')):reason='volume_size_limit'
                elif shutil.disk_usage(ROOT).free<20*1024**3:reason='disk_floor'
                elif time.perf_counter()-lastchange>120:reason='log_stalled_120s'
                if not samples or elapsed-samples[-1]['wall_s']>=5:
                    samples.append({'wall_s':elapsed,'rss_bytes':rss,'generated_bytes':size,'completed_volumes_checked':len(checked)})
                    (out/'progress.json').write_text(json.dumps(samples[-1])+'\n')
            if elapsed>1800:reason='wall_timeout'
            elif rss>16*1024**3:reason='aggregate_RSS'
            if reason:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL)
                break
            time.sleep(.1)
        proc.wait()
    usage=resource.getrusage(resource.RUSAGE_CHILDREN)
    status={'model_launches':1,'returncode':proc.returncode,'stop_reason':reason,'elapsed_s':time.perf_counter()-start,'started_utc':started,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'normal_exit_count':logpath.read_text().count('NORMAL EXIT'),'peak_sampled_tree_rss_bytes':peak,'children_user_cpu_s':usage.ru_utime,'children_system_cpu_s':usage.ru_stime,'resource_samples':samples,'completed_volumes_checked_online':len(checked),'netcdf_bytes':sum(f.stat().st_size for f in out.glob('*.nc')),'total_generated_bytes':sum(f.stat().st_size for f in out.rglob('*') if f.is_file())+logpath.stat().st_size,'rss_note':'sampled process group + descendants; shared pages counted repeatedly; transient peak may be missed'}
    (out/'run_status.json').write_text(json.dumps(status,indent=2)+'\n');print(json.dumps({k:v for k,v in status.items() if k!='resource_samples'},indent=2))
    if proc.returncode or reason or status['normal_exit_count']!=4:raise SystemExit(1)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-tag',required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+',a.run_tag):raise ValueError('Bad run tag')
    out=s.inside(ROOT/'experiments'/a.run_tag)
    execute(out) if a.execute else prepare(out)
if __name__=='__main__':main()
