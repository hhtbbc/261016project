"""One authorized 1450-step 2023 run; native one-record primary files."""
from pathlib import Path
import argparse, importlib.util, json, os, re, resource, shutil, signal
import subprocess, time, socket, getpass, hashlib

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('startup',ROOT/'scripts/run_tiegcm2023_diagnostic.py')
startup=importlib.util.module_from_spec(spec);spec.loader.exec_module(startup)
STARTS=[(77,0,0),(77,23,50),(78,0,0)]
STOPS=[(77,23,50),(78,0,0),(78,0,10)]
HIST=[(0,23,50),(0,0,10),(0,0,10)]

def seconds(t):return t[0]*86400+t[1]*3600+t[2]*60

def schedule():
    writes=[]
    for i,(start,stop,hist) in enumerate(zip(STARTS,STOPS,HIST)):
        assert seconds(stop)>seconds(start)
        assert (seconds(stop)-seconds(start))%seconds(hist)==0
        assert i==0 or start==STOPS[i-1]
        first=seconds(start)+(seconds(hist) if i else 0)
        writes+=list(range(first,seconds(stop)+1,seconds(hist)))
    return writes

def configuration():
    text=(ROOT/'third_party/TIEGCM2.0/scripts/tiegcm_res5.0_default.inp').read_text()
    triple=lambda ts:', '.join(' '.join(map(str,t)) for t in ts)
    values={'LABEL':"'2023 native checkpoint generation; cold initial guess; NOT spun up'",
            'START_YEAR':'2023','START_DAY':'77','START':triple(STARTS),'STOP':triple(STOPS),
            'HIST':triple(HIST),'OUTPUT':', '.join(f"'primary_{i:03d}.nc'" for i in range(1,5)),
            'MXHIST_PRIM':'1','SECSTART':'77 23 50','SECSTOP':'78 0 10',
            'SECHIST':'0 0 10','SECOUT':"'secondary_001.nc'"}
    for key,value in values.items():
        text,n=re.subn(rf'(?m)^\s*{key}\s*=.*$',f' {key} = {value}',text)
        if n!=1:raise ValueError(f'Unexpected template field {key}')
    text=re.sub(r'(?m)^\s*(?:F107|F107A|KP|POWER|CTPOTEN)\s*=.*\n','',text)
    text=text.replace('$TGCMDATA',str(startup.SUPPORT))
    return text.replace('\n/',f"\n GPI_NCFILE = '{startup.GPI}'\n/")

def validate_config(text):
    if text!=configuration():raise ValueError('Only the reviewed fixed 1450-step configuration is accepted')
    assert len(schedule())==4 and len(set(schedule()))==4
    assert (seconds(STOPS[-1])-seconds(STARTS[0]))//60==1450
    assert 'SOURCE_START = 80 0 0' in text
    assert not re.search(r'(?im)^\s*(F107|F107A|KP|POWER|CTPOTEN)(?:_TIME)?\s*=',text)

def limits():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE,(512*1024**2,512*1024**2))
    # Deliberately different from the old ten-minute runner's 60 s CPU cap.
    resource.setrlimit(resource.RLIMIT_CPU,(300,300))

def process_tree_rss(pid):
    table={}
    for p in Path('/proc').glob('[0-9]*/stat'):
        try:
            f=p.read_text().rsplit(')',1)[1].split()
            table[int(p.parent.name)]=(int(f[1]),int(f[2]),int(f[21])*os.sysconf('SC_PAGE_SIZE'))
        except (OSError,ValueError,IndexError):pass
    descendants={pid}
    while True:
        new={p for p,(parent,group,_) in table.items() if parent in descendants or group==pid}
        if new.issubset(descendants):break
        descendants.update(new)
    return sum(table[p][2] for p in descendants if p in table)

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-tag',required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+',a.run_tag):raise ValueError('Invalid tag')
    out=startup.inside(ROOT/'experiments'/a.run_tag)
    if not a.execute:
        if out.exists():raise FileExistsError(out)
        pre=startup.preflight();text=configuration();validate_config(text)
        assert pre['free_disk_bytes']>20*1024**3
        previous=json.loads((ROOT/'experiments/tiegcm2023_startup_10min_v1/preflight.json').read_text())
        for key in ['executable_sha256','gpi_sha256','restart_sha256','apex_sha256']:assert pre[key]==previous[key]
        # Protect historical source/data/results, including every prior model run.
        protected={}
        for base in ['third_party/TIEGCM2.0','data','experiments','results','reports']:
            for path in (ROOT/base).rglob('*'):
                if path.is_file() and not path.is_symlink():protected[str(path.relative_to(ROOT))]=startup.sha(path)
        out.mkdir();(out/'input.inp').write_text(text)
        pre.update(input_sha256=startup.sha(out/'input.inp'),wall_limit_s=300,cpu_limit_per_process_s=300,
                   expected_steps=1450,mpi_ranks=4,expected_primary_model_seconds=schedule(),
                   output_limit_bytes=512*1024**2,rss_limit_bytes=16*1024**3,disk_floor_bytes=20*1024**3,
                   estimated_model_wall_s=152.248519*1450/1440,estimated_output_bytes=100*1024**2,
                   primary_policy='one original record per native file; checkpoint has no future records',static_pass=True)
        (out/'preflight.json').write_text(json.dumps(pre,indent=2)+'\n')
        (out/'protected_files.json').write_text(json.dumps(protected,indent=2)+'\n')
        print('STATIC PASS',out);return
    pre=json.loads((out/'preflight.json').read_text());validate_config((out/'input.inp').read_text())
    assert startup.sha(out/'input.inp')==pre['input_sha256']
    now=startup.preflight()
    for key in ['executable_sha256','gpi_sha256','restart_sha256','apex_sha256']:assert pre[key]==now[key]
    assert shutil.disk_usage(ROOT).free>20*1024**3
    logpath=ROOT/'logs'/f'{a.run_tag}.log'
    if logpath.exists():raise FileExistsError(logpath)
    with (out/'launch_once.json').open('x') as f:json.dump({'model_launches':1,'expected_steps':1450,'no_retry':True},f)
    env=dict(os.environ,OMPI_ALLOW_RUN_AS_ROOT='1',OMPI_ALLOW_RUN_AS_ROOT_CONFIRM='1',OMPI_MCA_pml='ob1',
             OMPI_MCA_btl='self,tcp',OMPI_MCA_osc='rdma',PMIX_MCA_gds='hash',HOST=socket.gethostname(),
             LOGNAME=getpass.getuser(),OMP_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='')
    selected={k:env[k] for k in ['TMPDIR','OMP_NUM_THREADS','CUDA_VISIBLE_DEVICES','PRTE_MCA_prte_tmpdir_base','PMIX_MCA_pmix_server_tmpdir','OMPI_MCA_pml','OMPI_MCA_btl','OMPI_MCA_osc']}
    (out/'runtime_environment.json').write_text(json.dumps(selected,indent=2)+'\n')
    start=time.perf_counter();peak=0;reason=None;samples=[]
    with logpath.open('x') as log:
        proc=subprocess.Popen(['mpirun','-np','4',str(startup.BUILD/'tiegcm2.0'),'input.inp'],cwd=out,
                              stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True,preexec_fn=limits)
        while proc.poll() is None:
            rss=process_tree_rss(proc.pid);peak=max(peak,rss)
            size=sum(f.stat().st_size for f in out.rglob('*') if f.is_file())+logpath.stat().st_size
            elapsed=time.perf_counter()-start
            if not samples or elapsed-samples[-1]['wall_s']>=5:samples.append({'wall_s':elapsed,'rss_bytes':rss,'output_bytes':size})
            if elapsed>300:reason='wall_timeout'
            elif rss>16*1024**3:reason='rss_limit'
            elif size>512*1024**2:reason='total_output_limit'
            elif shutil.disk_usage(ROOT).free<20*1024**3:reason='disk_floor'
            if reason:
                os.killpg(proc.pid,signal.SIGKILL);break
            time.sleep(.1)
        proc.wait()
    status={'returncode':proc.returncode,'normal_exit_count':logpath.read_text().count('NORMAL EXIT'),
            'stop_reason':reason,'elapsed_s':time.perf_counter()-start,'peak_sampled_tree_rss_bytes':peak,
            'resource_samples':samples,'model_launches':1,'simulated_seconds_requested':87000,
            'rss_note':'sum RSS across process group and descendants; shared pages counted repeatedly; 0.1s sampling',
            'restart_unchanged':startup.sha(startup.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc')==pre['restart_sha256']}
    (out/'run_status.json').write_text(json.dumps(status,indent=2)+'\n');print(json.dumps(status,indent=2))
    if proc.returncode or reason or not status['normal_exit_count']:raise SystemExit(1)
if __name__=='__main__':main()
