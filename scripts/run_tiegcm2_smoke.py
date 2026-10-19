"""Bounded official default-physics smoke run (2002), never 2023 production."""
from pathlib import Path
import argparse,subprocess,time,resource,json,os,socket,getpass
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--run-tag',default='tiegcm2_smoke_v2');p.add_argument('--build-tag',default='tiegcm2_build_v1');p.add_argument('--minutes',type=int,default=10);p.add_argument('--ranks',type=int,choices=[1,4],default=4);a=p.parse_args()
if not a.run_tag or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in a.run_tag):raise ValueError('Bad tag')
if not a.build_tag or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in a.build_tag):raise ValueError('Bad build tag')
if a.minutes not in [10,30,60,1440]:raise ValueError('Only bounded smoke runs or the official default single day')
wall_limit=300 if a.minutes==1440 else 60
out=ROOT/'experiments'/a.run_tag;assert out.resolve().is_relative_to(ROOT);out.mkdir(exist_ok=False)
hour,minute=divmod(a.minutes,60)
text=(ROOT/'third_party/TIEGCM2.0/scripts/tiegcm_res5.0_default.inp').read_text().replace('$TGCMDATA',str(ROOT/'data/raw/tiegcm2_support'))
if a.minutes!=1440:
 text=text.replace('STOP  = 81 0 0',f'STOP  = 80 {hour} {minute}').replace('HIST = 1 0 0','HIST = 0 0 5').replace('SECSTART = 80 1 0','SECSTART = 80 0 5').replace('SECSTOP  = 81 0 0',f'SECSTOP  = 80 {hour} {minute}').replace('SECHIST  =  0 1 0','SECHIST  =  0 0 5')
(out/'input.inp').write_text(text)
env=dict(os.environ,OMPI_ALLOW_RUN_AS_ROOT='1',OMPI_ALLOW_RUN_AS_ROOT_CONFIRM='1',OMPI_MCA_pml='ob1',OMPI_MCA_btl='self,tcp',OMPI_MCA_osc='rdma',PMIX_MCA_gds='hash',HOST=socket.gethostname(),LOGNAME=getpass.getuser())
started=time.perf_counter()
with (ROOT/'logs'/f'{a.run_tag}.log').open('x') as log:
 process=subprocess.Popen(['mpirun','-np',str(a.ranks),str(ROOT/'experiments'/a.build_tag/'tiegcm2.0'),'input.inp'],cwd=out,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
 try:code=process.wait(timeout=wall_limit);status={'returncode':code}
 except subprocess.TimeoutExpired:
  import signal
  os.killpg(process.pid,signal.SIGKILL);process.wait();status={'timeout_s':wall_limit}
status.update(elapsed_s=time.perf_counter()-started,max_launcher_rss_kb=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,simulated_minutes=a.minutes,mpi_ranks=a.ranks,build_tag=a.build_tag,run_directory=str(out),actual_2023_simulation=False)
(ROOT/'logs'/f'{a.run_tag}_resources.json').write_text(json.dumps(status,indent=2));print(status)
