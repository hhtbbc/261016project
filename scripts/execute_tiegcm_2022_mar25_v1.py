"""Future-only one-attempt continuous run. Not authorized or called by V14-B."""
from pathlib import Path
import sys,os,json,argparse,hashlib,shutil,re,time
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R/'scripts')]
from runtime.supervisor import supervise,Limits
F=R/'experiments/tiegcm_2022_mar25_preparation_v1'
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--authorize-17day-run',action='store_true');a=parser.parse_args()
 if not a.authorize_17day_run:parser.error('Next explicit user authorization is required; this preparation never launches a model')
 p=json.loads((F/'launch_protocol.json').read_text());pre=json.loads((F/'preflight.json').read_text());assert pre['status']=='RUN_READY_NOT_LAUNCHED'
 # Immutable preparation package and all linked scientific inputs.
 frozen=json.loads((F/'sha256_manifest.json').read_text())
 for n,h in frozen.items():assert digest(R/n)==h,n
 m=json.loads((F/'model_configuration_manifest.json').read_text())
 for n,h in m['verified_assets'].items():assert digest(R/n)==h,n
 for e in [p['input'],p['GPI'],p['executable']]:assert digest(R/e['path'])==e['SHA256']
 source=json.loads((F/'source_manifest.json').read_text())
 for e in source['compiled_source_inventory']:assert digest(R/e['path'])==e['SHA256']
 assert digest(R/source['mpirun']['path'])==source['mpirun']['SHA256']
 assert shutil.disk_usage(R).free>25*2**30 and int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1])*1024>16*2**30
 assert len(os.sched_getaffinity(0))>=4
 for comm in Path('/proc').glob('[0-9]*/comm'):
  try:assert comm.read_text().strip()!='tiegcm2.0','Another model is active'
  except FileNotFoundError:pass
 run=R/p['cwd'];assert run.resolve().is_relative_to(R) and not list(run.glob('*.nc')) and not (run/'launch_once.json').exists()
 env=dict(os.environ,OMPI_ALLOW_RUN_AS_ROOT='1',OMPI_ALLOW_RUN_AS_ROOT_CONFIRM='1',OMPI_MCA_pml='ob1',OMPI_MCA_btl='self,tcp',OMPI_MCA_osc='rdma',PMIX_MCA_gds='hash',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='');env['HOST']=__import__('socket').gethostname();env['LOGNAME']=__import__('getpass').getuser()
 import subprocess
 linked=subprocess.check_output(['ldd',str(R/p['executable']['path'])],env=env,text=True);assert 'not found' not in linked
 actual={}
 for line in linked.splitlines():
  hit=re.search(r'=>\s+(\S+)\s+\(',line)
  if hit:actual[line.split()[0]]=digest(Path(hit[1]).resolve())
 for e in json.loads((F/'environment_audit.json').read_text())['dependencies']:assert actual[e['name']]==e['SHA256']
 argv=[str(R/p['argv'][0]),'-np','4',str(R/p['argv'][3]),'input.inp'];start=time.perf_counter()
 st=supervise(argv,run,Limits(4770,16*2**30,20*2**30,5*2**30,256*2**20,.25,2,3,120,5*2**30),env=env,total_dir=run)
 # A successful direct wait is engineering execution evidence, not scientific acceptance.
 summary=dict(qualification=st['qualification'],returncode=st['returncode'],elapsed_s=time.perf_counter()-start,cleanup_verified=st['cleanup_verified'],postrun_full_field_audit='REQUIRED_BEFORE_DENSITY_EVALUATION',new_model_launches=1,retry=0)
 (F/'execution_result_local.json').open('x').write(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary));assert st['qualification']=='PASS' and st['returncode']==0 and st['cleanup_verified']
if __name__=='__main__':main()
