"""Minimal adapter over the existing supervisor; immutable scientific preparation."""
from pathlib import Path
import sys,os,json,re,shutil,subprocess,time,uuid
from .supervisor import supervise,Limits
from .tiegcm_rank_exit import digest,write_once
ROOT=Path(__file__).resolve().parents[2]
PREP=ROOT/'experiments/tiegcm_2022_mar25_preparation_v1'
REVIEW=ROOT/'experiments/tiegcm_2022_mar25_execution_review_v1'
class GateError(RuntimeError):pass
def require(condition,message):
 if not condition:raise GateError(message)
def claim(directory):
 """Atomic mkdir is the single claimant; keep reservation after every failure."""
 directory=Path(directory);directory.resolve().relative_to(ROOT);directory.mkdir(exist_ok=False);return directory

def verify_preparation(prep=PREP,review=REVIEW):
 overlay=json.loads((review/'execution_overlay.json').read_text());require(digest(prep/'sha256_manifest.json')==overlay['preparation_manifest_SHA256'],'Historical preparation manifest changed');manifest=json.loads((prep/'sha256_manifest.json').read_text());require(overlay['effective_run_directory']==str((review/'actual_run').relative_to(ROOT)),'Working directory override differs from reviewed path')
 for name,wanted in manifest.items():
  p=ROOT/name;p.resolve().relative_to(ROOT)
  if name==overlay['superseded_launcher']:
   require(wanted==overlay['old_launcher_SHA256'],'Unrecognized prior launcher identity');wanted=overlay['new_launcher_SHA256']
  require(digest(p)==wanted,'Frozen preparation changed: '+name)
 for name,wanted in overlay['execution_code_SHA256'].items():require(digest(ROOT/name)==wanted,'Execution code changed: '+name)
 # Every scientific input remains pinned by the unchanged preparation and source manifest.
 model=json.loads((prep/'model_configuration_manifest.json').read_text());source=json.loads((prep/'source_manifest.json').read_text());protocol=json.loads((prep/'launch_protocol.json').read_text())
 for name,wanted in model['verified_assets'].items():require(digest(ROOT/name)==wanted,'Scientific asset changed: '+name)
 for e in source['compiled_source_inventory']+[source['mpirun']]:require(digest(ROOT/e['path'])==e['SHA256'],'Source/MPI changed')
 for e in [protocol['input'],protocol['GPI'],protocol['executable']]:require(digest(ROOT/e['path'])==e['SHA256'],'Frozen physical input changed')
 return protocol

def runtime_preflight(protocol):
 require(shutil.disk_usage(ROOT).free>25*2**30,'Need 5GiB output allowance plus20GiB floor')
 available=int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1])*1024
 require(available>16*2**30 and len(os.sched_getaffinity(0))>=4,'Insufficient memory/CPU')
 for p in Path('/proc').glob('[0-9]*/comm'):
  try:require(p.read_text().strip()!='tiegcm2.0','Another TIEGCM process is active')
  except FileNotFoundError:pass
 old=ROOT/protocol['cwd'];require(not list(old.glob('*.nc')) and not (old/'launch_once.json').exists(),'Historical/prepared directory already used')
 env=dict(os.environ,OMPI_ALLOW_RUN_AS_ROOT='1',OMPI_ALLOW_RUN_AS_ROOT_CONFIRM='1',OMPI_MCA_pml='ob1',OMPI_MCA_btl='self,tcp',OMPI_MCA_osc='rdma',PMIX_MCA_gds='hash',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='')
 env['HOST']=__import__('socket').gethostname();env['LOGNAME']=__import__('getpass').getuser()
 linked=subprocess.check_output(['ldd',str(ROOT/protocol['executable']['path'])],text=True,env=env);require('not found' not in linked,'Missing runtime library');actual={}
 for line in linked.splitlines():
  m=re.search(r'=>\s+(\S+)\s+\(',line)
  if m:actual[line.split()[0]]=digest(Path(m[1]).resolve())
 for e in json.loads((PREP/'environment_audit.json').read_text())['dependencies']:require(actual.get(e['name'])==e['SHA256'],'Runtime dependency changed')
 return env

def execute(authorized=False):
 require(authorized,'No explicit17day authorization: model launch refused')
 release=json.loads((REVIEW/'sha256_manifest.json').read_text())
 for n,h in release.items():require(digest(ROOT/n)==h,'Reviewed package changed: '+n)
 protocol=verify_preparation();env=runtime_preflight(protocol)
 # Use a NEW empty child directory. Never remove or overwrite prepared input.
 run=claim(REVIEW/'actual_run');run_id=uuid.uuid4().hex
 write_once(REVIEW/'execution_claim_local.json',dict(run_id=run_id,claimed_unix=time.time(),attempts=1,automatic_retry=False))
 wrapper=ROOT/'src/runtime/tiegcm_rank_exit.py';model=protocol['executable'];inp=protocol['input']
 argv=[str(ROOT/protocol['argv'][0]),'-np','4',sys.executable,str(wrapper),'--model',str(ROOT/model['path']),'--run-id',run_id,'--model-sha',model['SHA256'],'--input-sha',inp['SHA256']]
 started=time.perf_counter()
 try:
  st=supervise(argv,run,Limits(4770,16*2**30,20*2**30,5*2**30,256*2**20,.25,2,3,120,5*2**30),env=env,total_dir=run,input_files={'input.inp':(ROOT/inp['path']).read_bytes()})
  summary=dict(actual_model_run='ATTEMPTED',run_id=run_id,supervisor_returncode=st['returncode'],supervisor_qualification=st['qualification'],elapsed_s=time.perf_counter()-started,run=str(run.relative_to(ROOT)),cleanup_verified=st['cleanup_verified'],engineering_acceptance='NOT_RUN')
  # Exit0 alone NEVER implies the physical run completed.
  audit_dir=claim(REVIEW/'postrun_audit_local')
  audit_argv=[sys.executable,str(ROOT/'scripts/audit_tiegcm_2022_mar25_execution_v1.py'),'--run',str(run),'--run-id',run_id,'--output',str(audit_dir/'acceptance.json')]
  audit_st=supervise(audit_argv,audit_dir,Limits(600,4*2**30,20*2**30,150*2**20,100*2**20,.3,1,3,120,150*2**20),env=env,total_dir=audit_dir)
  audit=json.loads((audit_dir/'acceptance.json').read_text()) if (audit_dir/'acceptance.json').exists() else {'overall':'FAIL'}
  summary['engineering_acceptance']=audit['overall'];summary['postrun_audit_supervision']=dict(qualification=audit_st['qualification'],returncode=audit_st['returncode'],elapsed_s=audit_st['elapsed_s'])
  write_once(REVIEW/'execution_result_local.json',summary)
  require(audit_st['qualification']=='PASS' and audit_st['returncode']==0,'Postrun audit incomplete or resource limit')
  require(audit['overall']=='PASS','Full engineering acceptance failed; no automatic retry or density scoring')
  return summary
 except BaseException as e:
  if not (REVIEW/'execution_failure_local.json').exists():write_once(REVIEW/'execution_failure_local.json',dict(error=type(e).__name__,message=str(e),run_id=run_id,claimed_attempt_preserved=True,no_retry=True))
  raise
