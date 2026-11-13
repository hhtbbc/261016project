"""Explicitly authorized exploratory v2; never uses the legacy B14 launcher."""
from pathlib import Path
import sys,json,os,time,re,shutil,hashlib,argparse,socket,getpass,difflib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from runtime.supervisor import supervise,Limits,ProcReader
from atmosphere.tiegcm_drivers import GpiDriver
from atmosphere.restart_validation import check_source_clock
from run_tiegcm_mar23_2021_longrun import stream_sha
import run_tiegcm_2022_14day as legacy_data
TAG='tiegcm_2022_b14_exploratory_pair_v2';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG
H=ROOT/'experiments/tiegcm_2022_spinup_14day_v1';A=H/'A14';B=F/'B14'

def dump(path,obj):
 path=Path(path);assert path.resolve().is_relative_to(ROOT)
 with path.open('x') as out:json.dump(obj,out,indent=2,allow_nan=False)
def environment():
 return dict(os.environ,OMPI_ALLOW_RUN_AS_ROOT='1',OMPI_ALLOW_RUN_AS_ROOT_CONFIRM='1',OMPI_MCA_pml='ob1',OMPI_MCA_btl='self,tcp',OMPI_MCA_osc='rdma',PMIX_MCA_gds='hash',HOST=socket.gethostname(),LOGNAME=getpass.getuser(),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='')
def active_models():
 out=[]
 for name in os.listdir('/proc'):
  if not name.isdigit():continue
  try:
   if (Path('/proc')/name/'comm').read_text().strip()=='tiegcm2.0':out.append(int(name))
  except OSError:continue
 return out

def prepare():
 assert not F.exists();assert not B.exists();assert not active_models()
 prior=ROOT/'experiments/tiegcm_supervision_repair_v1';old=json.loads((A/'run_status.json').read_text());data=json.loads((A/'data_audit.json').read_text());assert old['returncode'] is None and not data['engineering_PASS'] and data['data_integrity_PASS']
 for name,expected in json.loads((prior/'history_preservation.json').read_text())['SHA256'].items():assert stream_sha(ROOT/name)==expected,name
 sa=legacy_data.initial.source_audit();check_source_clock([68,0,0],[80,0,0]);assert sa['required_count']==34
 static=json.loads((prior/'B14_static_preflight.json').read_text())
 for name,expected in static['input_SHA256'].items():assert stream_sha(ROOT/name)==expected,name
 drv=GpiDriver(legacy_data.GPI)
 for minute in range(23041):
  sec=68*86400+minute*60;assert all(np.isfinite(v) for v in drv.at(2022000+sec//86400,sec%86400).values())
 text=static['namelist'];assert hashlib.sha256(text.encode()).hexdigest()==static['namelist_SHA256'];assert text==legacy_data.configuration('B14')
 aa=(A/'input.inp').read_text();assert text.replace(str(legacy_data.initial.SOURCE),str(legacy_data.m.s.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc'))==aa
 free=shutil.disk_usage(ROOT).free;mem=int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1])*1024;assert free>25*2**30 and mem>16*2**30 and len(os.sched_getaffinity(0))>=4
 existing=sum(p.stat().st_size for p in A.rglob('*') if p.is_file());assert existing<5*2**30
 F.mkdir();O.mkdir();protected=json.loads((H/'protected_files.json').read_text())
 for path in A.rglob('*'):
  if path.is_file():protected[str(path.relative_to(ROOT))]=stream_sha(path)
 for path in [H/'execution_decision.json',H/'driver_audit.json',ROOT/'results/tiegcm_2022_spinup_14day_v1/observation_partial/aligned_local.npz']:
  protected[str(path.relative_to(ROOT))]=stream_sha(path)
 for name,expected in protected.items():assert stream_sha(ROOT/name)==expected,name
 dump(F/'protected_files.json',protected)
 protocol=dict(version=TAG,user_authorization='Current task explicitly selects exploratory protocol B and authorizes exactly one smax B14 continuous run after all gates; no A14 rerun',A14=dict(path=str(A.relative_to(ROOT)),data_integrity='PASS',historical_engineering='PARTIAL',launcher_exit='UNKNOWN',limited_offline_analysis=True),B14=dict(path=str(B.relative_to(ROOT)),new_continuous_run=True,max_launches=1,no_retry=True,direct_parent_wait=True,engineering_independent=True),conclusion_limits=['Not a v1 complete engineering PASS','Never promote A14 engineering','Internal agreement is not observational accuracy','No automatic scientific training qualification'],year=2022,start_UTC='2022-03-09T00:00:00Z',stop_UTC='2022-03-25T00:00:00Z',candidate_UTC=['2022-03-23T00:00:00Z','2022-03-25T00:00:00Z'],steps=23040,step_seconds=60,MPI=4,OMP=1,primary_records=17,secondary_records=384,primary_volumes=17,secondary_volumes=16,wall_limit_s=4800,supervisor_stop_deadline_s=4770,cleanup_and_final_check_reserve_s=30,rss_limit_bytes=16*2**30,B14_output_limit_bytes=5*2**30,combined_output_limit_bytes=12*2**30,existing_A14_bytes=existing,new_protocol_remaining_output_limit_bytes=12*2**30-existing,volume_limit_bytes=256*2**20,disk_floor_bytes=20*2**30,estimated_wall_s=static['estimated_wall_s'],estimated_safety_wall_s=static['safety_wall_s'],estimated_NetCDF_bytes=static['estimated_NetCDF_bytes'],cpu_affinity_count=len(os.sched_getaffinity(0)),free_disk_bytes=free,available_memory_bytes=mem)
 dump(F/'protocol.json',protocol);dump(F/'frozen_comparison_rules.json',json.loads((H/'frozen_comparison_rules.json').read_text()));dump(F/'configuration.json',dict(namelist=text,SHA256=hashlib.sha256(text.encode()).hexdigest(),changes=list(difflib.unified_diff(aa.splitlines(),text.splitlines(),fromfile='A14',tofile='B14v2'))))
 dump(F/'input_manifest.json',dict(files=static['input_SHA256'],source_audit=sa,protocol_SHA256=stream_sha(F/'protocol.json'),rules_SHA256=stream_sha(F/'frozen_comparison_rules.json'),runner_SHA256=stream_sha(Path(__file__)),supervisor_SHA256=stream_sha(ROOT/'src/runtime/supervisor.py'),mpirun=str(Path(shutil.which('mpirun')).resolve()),physical_check_SHA256=stream_sha(ROOT/'scripts/run_tiegcm_2021_14day.py')))
 print('V2 frozen, preflight PASS; no model started',flush=True)

def mpi_test():
 assert F.exists() and not (F/'mpi_test').exists() and not B.exists()
 helper='import os,time,json;print(json.dumps(dict(rank=int(os.environ["OMPI_COMM_WORLD_RANK"]),pid=os.getpid(),sid=os.getsid(0),pgid=os.getpgid(0))),flush=True);time.sleep(.5)'
 folder=F/'mpi_test';folder.mkdir();p=json.loads((F/'input_manifest.json').read_text())
 result=supervise([p['mpirun'],'-np','4',sys.executable,'-c',helper],folder,Limits(55,2**30,20*2**30,10*2**20,2**20,.05,1,3,10),env=environment(),total_dir=F)
 assert result['elapsed_s']<=60 and result['qualification']=='PASS' and result['returncode']==0 and result['cleanup_verified'] and not result['gaps'],result
 ranks=[json.loads(x) for x in (folder/'stdout.log').read_text().splitlines() if x.startswith('{')];assert sorted(x['rank'] for x in ranks)==list(range(4));assert all(x['sid']==result['identity']['sid'] for x in ranks),ranks
 dump(F/'mpi_test_audit.json',dict(PASS=True,real_TIEGCM_steps=0,ranks=ranks,returncode=result['returncode'],wait_source=result['wait_source'],elapsed_s=result['elapsed_s'],cleanup_verified=result['cleanup_verified'],supervisor_SHA256=stream_sha(ROOT/'src/runtime/supervisor.py')))
 print('4-rank non-physics MPI test PASS',result['elapsed_s'],flush=True)

class ClosedVolumes:
 def __init__(self):self.checked={}
 def __call__(self,cwd,final):
  for prefix,count in [('primary',17),('secondary',16)]:
   paths=sorted(cwd.glob(prefix+'_*.nc'))
   if final:assert len(paths)==count
   for path in paths if final else paths[:-1]:
    if path.name not in self.checked:
     legacy_data.basic_file(path);self.checked[path.name]=path.stat().st_size
  if final:
   dump(F/'closed_volume_audit.json',dict(PASS=True,volumes=self.checked,all_volume_physical_check=True))

def execute():
 p=json.loads((F/'protocol.json').read_text());m=json.loads((F/'input_manifest.json').read_text());config=json.loads((F/'configuration.json').read_text());assert json.loads((F/'mpi_test_audit.json').read_text())['PASS'];assert not B.exists();assert not (F/'model_launch_once.json').exists();assert not active_models()
 for path,expected in [(Path(__file__),m['runner_SHA256']),(ROOT/'src/runtime/supervisor.py',m['supervisor_SHA256']),(F/'protocol.json',m['protocol_SHA256']),(F/'frozen_comparison_rules.json',m['rules_SHA256'])]:assert stream_sha(path)==expected,path
 for name,expected in m['files'].items():assert stream_sha(ROOT/name)==expected,name
 for name,expected in json.loads((F/'protected_files.json').read_text()).items():assert stream_sha(ROOT/name)==expected,name
 assert shutil.disk_usage(ROOT).free>25*2**30;assert int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1])*1024>16*2**30
 assert hashlib.sha256(config['namelist'].encode()).hexdigest()==config['SHA256'];B.mkdir();dump(F/'model_launch_once.json',dict(max_launches=1,no_retry=True,protocol_SHA256=m['protocol_SHA256'],start_monotonic=time.monotonic()))
 env=environment();dump(F/'runtime_environment.json',{k:env[k] for k in ['TMPDIR','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','CUDA_VISIBLE_DEVICES','OMPI_MCA_pml','OMPI_MCA_btl','PRTE_MCA_prte_tmpdir_base']})
 limits=Limits(4770,16*2**30,20*2**30,5*2**30,256*2**20,2.,3.,3,120.,p['new_protocol_remaining_output_limit_bytes'])
 result=supervise([m['mpirun'],'-np','4',str(legacy_data.m.s.BUILD/'tiegcm2.0'),'input.inp'],B,limits,env=env,validator=ClosedVolumes(),total_dir=F,input_files={'input.inp':config['namelist'].encode()})
 print('B14 supervisor finished',result['qualification'],result['returncode'],result['elapsed_s'],flush=True)
 assert result['elapsed_s']<=4800 and result['qualification']=='PASS' and result['returncode']==0 and result['cleanup_verified'] and not result['gaps'],'No downstream engineering PASS allowed'
 dump(F/'B14_supervision_gate.json',dict(PASS=True,returncode=0,source='direct subprocess.Popen.wait',wall_s=result['elapsed_s'],A14_engineering='PARTIAL',v1_pair_engineering='NOT_PASS'))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','mpi-test','execute']);args=parser.parse_args();{'prepare':prepare,'mpi-test':mpi_test,'execute':execute}[args.action]()
