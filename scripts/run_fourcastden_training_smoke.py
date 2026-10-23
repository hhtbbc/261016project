"""At most three full AFNONet synthetic SGD steps, independently initialized."""
import sys,json,time,gc,hashlib,resource
from pathlib import Path
import torch,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from training.pipeline import DirectTrainer,build_direct,seed_all,synthetic_batch,LABEL
F=ROOT/'experiments/fourcastden_training_smoke_v1'
def digest(model):
 h=hashlib.sha256()
 for n,p in model.state_dict().items():h.update(n.encode());h.update(p.detach().cpu().contiguous().numpy().tobytes())
 return h.hexdigest()
def main():
 cfg=json.loads((ROOT/'configs/training/direct_synthetic_smoke.json').read_text());pre=json.loads((F/'preflight.json').read_text());assert pre['status']=='PASS'
 for p,h in pre['code_SHA256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
 with (F/'gpu_launch_once.json').open('x') as f:json.dump(dict(max_steps=3,official_checkpoint_loaded=False,synthetic_only=True),f)
 start=time.perf_counter();cfg['architecture']['img_size']=tuple(cfg['architecture']['img_size']);seed_all(cfg['seed']);torch.set_num_threads(4)
 assert torch.cuda.is_available();torch.cuda.set_per_process_memory_fraction((20*2**30)/torch.cuda.get_device_properties(0).total_memory)
 t=time.perf_counter();model=build_direct(cfg['architecture']).cuda();assert sum(p.numel() for p in model.parameters())==64695744;trainer=DirectTrainer(model,cfg);torch.cuda.synchronize();construct=time.perf_counter()-t
 batch=synthetic_batch(cfg['seed'],'cuda');validation=synthetic_batch(cfg['seed']+1,'cuda');records=[];initial_head=model.head.weight.detach().clone();checkpoint=F/'synthetic_step2.pt';restore=None
 for i in range(3):
  torch.cuda.synchronize();t=time.perf_counter();r=trainer.train_step(batch);torch.cuda.synchronize();r.update(wall_s=time.perf_counter()-t,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved());records.append(r)
  assert r['peak_reserved_bytes']<20*2**30 and time.perf_counter()-start<300
  assert not torch.equal(initial_head,trainer.model.head.weight)
  print(json.dumps(r),flush=True)
  if i==1:
   before=digest(trainer.model);old_optimizer=trainer.optimizer.state_dict();old_scheduler=trainer.scheduler.state_dict();trainer.save(checkpoint,dict(label=LABEL,synthetic=True,source='no real NPZ read',config_SHA256=pre['code_SHA256']['configs/training/direct_synthetic_smoke.json']))
   assert checkpoint.stat().st_size<300*2**20
   # Free the first full model; reconstruct separately, then restore without an extra training step.
   del model,trainer;gc.collect();torch.cuda.empty_cache();trainer=DirectTrainer(build_direct(cfg['architecture']).cuda(),cfg);trainer.restore(checkpoint,trusted_local=True)
   assert digest(trainer.model)==before and trainer.step==2;assert trainer.optimizer.state_dict()==old_optimizer and trainer.scheduler.state_dict()==old_scheduler
   restore=dict(status='PASS',step=2,parameter_SHA256=before,optimizer_exact=True,scheduler_exact=True,checkpoint_bytes=checkpoint.stat().st_size)
 assert trainer.step==3;value=trainer.validation_step(validation);assert np.isfinite(value)
 result=dict(status='PASS',label=LABEL,train_steps=trainer.step,records=records,checkpoint_restore=restore,validation_loss=value,parameter_count=sum(p.numel() for p in trainer.model.parameters()),construction_s=construct,wall_s=time.perf_counter()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,device=torch.cuda.get_device_name(),torch=torch.__version__,CUDA=torch.version.cuda,official_weights_loaded=False,real_data_read=False,loss_is_not_scientific_skill=True)
 with (F/'gpu_result.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k!='records'}),flush=True)
if __name__=='__main__':main()
