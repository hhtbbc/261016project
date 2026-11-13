"""One bounded direct-child continuation task; fail closed, never retry."""
from pathlib import Path
import os,sys,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from train_den_continuation_v6 import F,O,sha,dump
from runtime.gpu_environment import configure_determinism,require_gpu_assignment
from runtime.supervisor import supervise,Limits,resource_snapshot

def total_bytes():return sum(p.stat().st_size for base in [F,O] for p in base.rglob('*') if p.is_file())
def sampler(reader,identity,cwd,log,total):
 s=resource_snapshot(reader,identity,cwd,log,total);s['output_bytes']=total_bytes();gpu=0
 for row in subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True,timeout=3).splitlines():
  pid,size=row.split(',')
  if int(pid.strip())==identity.pid:gpu+=int(size.strip())*2**20
 s['GPU_process_bytes']=gpu
 if gpu>20*2**30:raise MemoryError('GPU sample exceeded20GiB')
 return s

def main():
 assert not (F/'training_launch_once.json').exists();assert json.loads((F/'data_audit.json').read_text())['PASS'] and json.loads((F/'source_checkpoint_audit.json').read_text())['PASS']
 for name in ['continuation_tests','overfit_tests','environment_tests','DEN_tests','pipeline_tests','interface_tests','import_tests']:
  text=(ROOT/f'logs/den_continuation_v6_{name}.log').read_text();assert text.rstrip().endswith('OK') and 'FAILED' not in text,name
 protected=json.loads((F/'protected_inputs.json').read_text())
 for n,h in protected.items():assert sha(ROOT/n)==h,n
 assert shutil.disk_usage(ROOT).free>=22*2**30 and total_bytes()<100*2**20
 visibility=require_gpu_assignment();env=dict(os.environ);configure_determinism(env);env.update(OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',PYTHONPATH=str(ROOT/'src')+os.pathsep+str(ROOT/'scripts'))
 probe="from runtime.gpu_environment import configure_determinism,require_cuda,assert_visibility;v=configure_determinism();import torch,numpy as np;from training.den_engineering import pairs,DenTrainer,DEN_INDICES,LABEL,load_statistics,den_objective,evaluate_fields;from training.pipeline import build_direct,seed_all;from training.den_overfit import array_sha,state_digest;from training.den_continuation import ContinuationBudget,validate_continuation_plan,audited_restore,rng_snapshot,rng_fingerprint;from persistence_den_engineering_v3 import csvout,aggregate;assert_visibility(v);import json;h=require_cuda(torch,v);h['free_bytes']=torch.cuda.mem_get_info(0)[0];print(json.dumps(h))"
 p=subprocess.run([sys.executable,'-c',probe],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
 if p.returncode:
  dump(F/'preflight_failure.json',dict(PASS=False,phase='CUDA_capability_only',returncode=p.returncode,stderr=p.stderr,training_tasks=0));raise RuntimeError('Preflight blocked; no job started')
 info=json.loads(p.stdout);assert info['visibility']==visibility and info['free_bytes']>=22*2**30
 others=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True).strip();assert not others,'Other GPU jobs present'
 frozen=dict(protected)
 for n in ['scripts/train_den_continuation_v6.py','scripts/prepare_den_continuation_v6.py','scripts/launch_den_continuation_v6.py','scripts/train_den_gpu_smoke_v4.py','scripts/persistence_den_engineering_v3.py','src/training/den_continuation.py','src/training/den_overfit.py','src/training/den_engineering.py','src/training/pipeline.py','src/runtime/gpu_environment.py','src/runtime/supervisor.py']:
  frozen[n]=sha(ROOT/n)
 for p in (ROOT/'third_party/FourCastDEN_linux').rglob('*.py'):frozen[str(p.relative_to(ROOT))]=sha(p)
 frozen[str((F/'plan.json').relative_to(ROOT))]=sha(F/'plan.json')
 dump(F/'preflight.json',dict(PASS=True,visibility=visibility,hardware=info,other_GPU_processes=others,probe_model_calls=0,frozen_SHA256=frozen))
 dump(F/'training_launch_once.json',dict(GPU_tasks=1,start_step=100,max_additional_updates=100,end_step=200,no_retry=True))
 job=F/'gpu_job';job.mkdir();status=supervise([sys.executable,str(ROOT/'scripts/train_den_continuation_v6.py')],job,Limits(300,8*2**30,20*2**30,2*2**30,2*2**30,1.,3.,1,120.,2*2**30),env=env,sampler=sampler,total_dir=F)
 print('CONTINUATION_SUPERVISION',status['qualification'],status['returncode'],status['elapsed_s'],flush=True)
 if status['returncode']!=0 or status['qualification']!='PASS':raise RuntimeError('Only GPU job failed; no retry')
 result=json.loads((F/'GPU_result.json').read_text());assert result['additional_updates']==100 and result['end_step']==200 and result['validation_passes']==1 and total_bytes()<2*2**30
 dump(F/'engineering_gate.json',dict(PASS=True,GPU_tasks=1,start_step=100,additional_updates=100,end_step=200,validation_passes=1,supervised_wall_s=status['elapsed_s'],science_training_ready=False))
if __name__=='__main__':main()
