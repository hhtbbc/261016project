"""Same-import CUDA probe, exclusive supervised single GPU training task."""
from pathlib import Path
import sys,os,json,time,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from train_den_gpu_smoke_v4 import F,O,sha,dump
from runtime.gpu_environment import configure_determinism,require_gpu_assignment
from runtime.supervisor import supervise,Limits,resource_snapshot

def output_bytes():
 return sum(p.stat().st_size for base in [F,O] for p in base.rglob('*') if p.is_file())
def sampler(reader,identity,cwd,log,total):
 snap=resource_snapshot(reader,identity,cwd,log,total);snap['output_bytes']=output_bytes()
 rows=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True,timeout=3);gpu=0
 for row in rows.splitlines():
  a,b=row.split(',')
  if int(a.strip())==identity.pid:gpu+=int(b.strip())*2**20
 snap['GPU_process_bytes']=gpu
 if gpu>20*2**30:raise MemoryError('Process GPU memory exceeded frozen20GiB')
 return snap

def main():
 assert not (F/'training_launch_once.json').exists();assert json.loads((F/'data_audit.json').read_text())['PASS']
 for log in ['environment_tests','DEN_tests','pipeline_tests','interface_tests','import_tests']:
  text=(ROOT/f'logs/den_gpu_smoke_v4_{log}.log').read_text();assert text.rstrip().endswith('OK') and 'FAILED' not in text
 for n,h in json.loads((F/'protected_inputs.json').read_text()).items():assert sha(ROOT/n)==h,n
 assert shutil.disk_usage(ROOT).free>=22*2**30 and output_bytes()<100*2**20
 inherited=require_gpu_assignment();env=dict(os.environ);configure_determinism(env);env.update(OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
 # Capability-only child uses the worker's dependency import order, zero model calls.
 probe="from runtime.gpu_environment import configure_determinism,assert_visibility,require_cuda;v=configure_determinism();import torch,numpy as np;from training.den_engineering import pairs,DenTrainer,DEN_INDICES,LABEL,load_statistics,evaluate_fields,restore_den;from training.pipeline import build_direct,seed_all;from persistence_den_engineering_v3 import csvout,aggregate;assert_visibility(v);import json;h=require_cuda(torch,v);h['free_bytes']=torch.cuda.mem_get_info(0)[0];print(json.dumps(h))"
 env['PYTHONPATH']=str(ROOT/'src')+os.pathsep+str(ROOT/'scripts')
 p=subprocess.run([sys.executable,'-c',probe],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
 if p.returncode:
  dump(F/'preflight_failure.json',dict(PASS=False,phase='same_import_capability_probe',returncode=p.returncode,stderr=p.stderr,training_launches=0));raise RuntimeError('Preflight failed; no training launched')
 info=json.loads(p.stdout);assert info['visibility']==inherited and info['free_bytes']>=22*2**30
 procs=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True).strip();assert not procs,'Other GPU process present; stop before launch'
 code=['src/runtime/gpu_environment.py','src/runtime/supervisor.py','src/training/pipeline.py','src/training/den_engineering.py','scripts/train_den_gpu_smoke_v4.py','scripts/launch_den_gpu_smoke_v4.py','scripts/prepare_den_gpu_smoke_v4.py','scripts/persistence_den_engineering_v3.py']
 frozen=json.loads((F/'protected_inputs.json').read_text())
 for n in code:frozen[n]=sha(ROOT/n)
 for p in (ROOT/'third_party/FourCastDEN_linux').rglob('*.py'):frozen[str(p.relative_to(ROOT))]=sha(p)
 frozen[str((F/'plan.json').relative_to(ROOT))]=sha(F/'plan.json')
 dump(F/'preflight.json',dict(PASS=True,visibility=inherited,hardware=info,other_GPU_processes=procs,probe_model_calls=0,frozen_SHA256=frozen))
 dump(F/'training_launch_once.json',dict(training_tasks=1,max_updates=10,no_retry=True,visibility=inherited))
 job=F/'gpu_job';job.mkdir()
 status=supervise([sys.executable,str(ROOT/'scripts/train_den_gpu_smoke_v4.py')],job,Limits(890,16*2**30,20*2**30,2*2**30,2*2**30,1.,3.,1,180.,2*2**30),env=env,sampler=sampler,total_dir=F)
 print('SUPERVISED_GPU_RESULT',status['qualification'],status['returncode'],status['elapsed_s'],flush=True)
 if status['returncode']!=0 or status['qualification']!='PASS':raise RuntimeError('GPU job failed; no retry permitted')
 result=json.loads((F/'GPU_result.json').read_text());assert result['optimizer_updates']==10 and result['PASS'] and output_bytes()<2*2**30
 dump(F/'engineering_gate.json',dict(PASS=True,training_tasks=1,updates=10,validation_pairs=48,wall_s=status['elapsed_s'],science_training_ready=False))
if __name__=='__main__':main()
