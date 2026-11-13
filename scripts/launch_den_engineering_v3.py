"""One GPU launch after all real CPU gates; no automatic retry."""
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
from pathlib import Path
import sys,json,subprocess,shutil,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from training.den_engineering import F,O,DATA
from run_tiegcm_mar23_2021_longrun import stream_sha
from runtime.supervisor import supervise,Limits,resource_snapshot
def dump(path,obj):
 with path.open('x') as f:json.dump(obj,f,indent=2)
def generated_bytes():
 return sum(p.stat().st_size for base in [F,O] for p in base.rglob('*') if p.is_file())
def sampler(reader,identity,cwd,log,total):
 snap=resource_snapshot(reader,identity,cwd,log,total);snap['output_bytes']=generated_bytes()
 result=subprocess.run(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],cwd=ROOT,capture_output=True,text=True,timeout=3,check=True)
 gpu=0
 for line in result.stdout.splitlines():
  pid,used=line.split(',');pid=int(pid.strip())
  if pid==identity.pid:gpu+=int(used.strip())*2**20
 snap['GPU_process_bytes']=gpu
 if gpu>20*2**30:raise MemoryError('GPU process memory exceeds frozen20GiB; stop after monitored failure')
 return snap
if __name__=='__main__':
 assert not (F/'GPU_task_once.json').exists() and not (F/'gpu_launch_once.json').exists()
 assert json.loads((F/'cpu_data_audit.json').read_text())['PASS']
 assert json.loads((F/'persistence_audit.json').read_text())['PASS']
 tests=['den_engineering_v3_tests_final.log','den_engineering_v3_training_regression.log','den_engineering_v3_interface_regression.log']
 for name in tests:
  text=(ROOT/'logs'/name).read_text();assert text.rstrip().endswith('OK') and 'FAILED' not in text,name
 for name,sha in json.loads((F/'protected_files.json').read_text()).items():assert stream_sha(ROOT/name)==sha,name
 assert shutil.disk_usage(ROOT).free>=22*2**30 and generated_bytes()<200*2**20
 probe="import os;os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8';import torch,json;assert torch.cuda.is_available();print(json.dumps(dict(torch=torch.__version__,CUDA=torch.version.cuda,GPU=torch.cuda.get_device_name(0),total_bytes=torch.cuda.get_device_properties(0).total_memory)))"
 result=subprocess.run([sys.executable,'-c',probe],cwd=ROOT,capture_output=True,text=True,timeout=30,check=True);info=json.loads(result.stdout)
 mem=subprocess.check_output(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],text=True).strip();assert int(mem.splitlines()[0])>22*1024
 procs=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True).strip();assert not procs,'Other GPU process present; no launch'
 dump(F/'GPU_frozen_plan.json',dict(scheme='A, original171 head, DEN29 supervised',updates=10,training_pair_indices=list(range(10)),validation_pair_indices=list(range(48)),display_pair=0,display_native_ilev=24,forward_budget_breakdown=dict(train=10,fixed_train_before_after=2,checkpoint_probe=2,validation=48),total_expected_forward_calls=62,restore_at_update=5,checkpoints=['real_step5.pt','real_step10.pt'],normalization='training2021 only, no log',no_validation_tuning=True,no_future_2023_state=True,estimated_wall_s=120,estimated_allocated_GiB=4,estimated_outputs_GiB=1.5,estimates_not_measurements=True))
 files=[ROOT/'src/training/den_engineering.py',ROOT/'scripts/train_den_engineering_v3.py',ROOT/'scripts/launch_den_engineering_v3.py',ROOT/'scripts/persistence_den_engineering_v3.py',ROOT/'src/training/pipeline.py',F/'training_config.json',F/'protocol.json',F/'GPU_frozen_plan.json',DATA/'statistics.npz',F/'dataset_manifest.json',F/'cpu_data_audit.json']
 frozen={str(p.relative_to(ROOT)):stream_sha(p) for p in files}
 for year in ['2021','2022']:
  for frame in json.loads((F/'dataset_manifest.json').read_text())['frames'][year]:
   assert stream_sha(ROOT/frame['path'])==frame['SHA256'];frozen[frame['path']]=frame['SHA256']
 dump(F/'GPU_preflight.json',dict(PASS=True,hardware=info,free_memory_MiB=int(mem.splitlines()[0]),other_GPU_processes=procs,frozen_SHA256=frozen,probe='capability only; no model or updates',single_training_launch=True))
 folder=F/'gpu_job';folder.mkdir();dump(F/'GPU_task_once.json',dict(launches=1,max_updates=10,no_retry=True,CuBLAS=':4096:8'))
 env=dict(os.environ,CUBLAS_WORKSPACE_CONFIG=':4096:8',OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
 status=supervise([sys.executable,str(ROOT/'scripts/train_den_engineering_v3.py')],folder,Limits(890,16*2**30,20*2**30,2*2**30,2*2**30,1.,3.,1,180.),env=env,sampler=sampler,total_dir=F)
 print('GPU supervised exit',status['returncode'],status['qualification'],status['elapsed_s'],flush=True)
 assert status['qualification']=='PASS' and status['returncode']==0 and status['elapsed_s']<=900 and generated_bytes()<2*2**30
 assert json.loads((F/'GPU_result.json').read_text())['optimizer_updates']==10
 dump(F/'GPU_gate.json',dict(PASS=True,qualification='ENGINEERING_ONLY',actual_returncode=status['returncode'],real_updates=10,real_GPU_training_launches=1,science_training_ready=False))
