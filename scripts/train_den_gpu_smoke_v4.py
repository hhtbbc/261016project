"""One bounded real DEN GPU job; importing this entry has no CUDA side effects."""
from pathlib import Path
import sys,os,json,time,hashlib,gc,resource
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
F=ROOT/'experiments/fourcastden_den_gpu_smoke_v4'
O=ROOT/'results/fourcastden_den_gpu_smoke_v4'

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def dump(path,obj):
 with path.open('x') as f:json.dump(obj,f,indent=2,allow_nan=False)
def main():
 from runtime.gpu_environment import configure_determinism,require_cuda,assert_visibility
 inherited=configure_determinism()  # before the first torch/dependency import
 import torch,numpy as np
 from training.den_engineering import (pairs,DenTrainer,DEN_INDICES,LABEL,load_statistics,evaluate_fields,restore_den)
 from training.pipeline import build_direct,seed_all
 from persistence_den_engineering_v3 import csvout,aggregate
 assert_visibility(inherited)
 start=time.perf_counter();plan=json.loads((F/'plan.json').read_text());pre=json.loads((F/'preflight.json').read_text());assert pre['PASS'] and inherited==pre['visibility']
 for n,h in pre['frozen_SHA256'].items():assert sha(ROOT/n)==h,n
 dump(F/'worker_launch_once.json',dict(training_tasks=1,max_updates=10,CUDA_visibility=inherited))
 hardware=require_cuda(torch,inherited);torch.set_num_threads(4)
 torch.cuda.set_per_process_memory_fraction(20*2**30/hardware['total_bytes'],device=0);seed_all(plan['training_config']['seed'])
 a=torch.ones(1,device='cuda');assert a.device.type=='cuda';del a
 dump(F/'cuda_initialization.json',dict(PASS=True,**hardware,CuBLAS=os.environ['CUBLAS_WORKSPACE_CONFIG']))
 cfg=plan['training_config'];architecture=dict(cfg['architecture'],img_size=tuple(cfg['architecture']['img_size']))
 t=time.perf_counter();train=pairs(2021);val=pairs(2022);data_setup=time.perf_counter()-t
 assert len(train)==72 and len(val)==48
 def digest(value):
  h=hashlib.sha256()
  def walk(x):
   if torch.is_tensor(x):h.update(str(x.dtype).encode());h.update(x.detach().cpu().contiguous().numpy().tobytes())
   elif isinstance(x,dict):
    for k,v in x.items():h.update(str(k).encode());walk(v)
   elif isinstance(x,(list,tuple)):
    for v in x:walk(v)
   else:h.update(repr(x).encode())
  walk(value);return h.hexdigest()
 t=time.perf_counter();model=build_direct(architecture).cuda();trainer=DenTrainer(model,cfg);torch.cuda.synchronize();construction=time.perf_counter()-t
 assert sum(p.numel() for p in model.parameters())==64695744
 forwards=[0];steps=[0];events=[]
 def before(*_):
  e=[torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)];e[0].record();events.append(e);forwards[0]+=1
 def after(*_):events[-1][1].record()
 def step_hook(*_):steps[0]+=1;assert steps[0]<=10
 def attach():
  trainer.model.register_forward_pre_hook(before);trainer.model.register_forward_hook(after);trainer.optimizer.register_step_post_hook(step_hook)
 attach();initial_hash=digest(trainer.model.state_dict());preprocess=[]
 def batch(ds,i):
  t=time.perf_counter();b=tuple(x[None].cuda() for x in ds[i]);torch.cuda.synchronize();preprocess.append(time.perf_counter()-t);return b
 from training.den_engineering import den_objective
 fixed=batch(train,0);trainer.model.eval()
 with torch.no_grad():initial_fixed=den_objective(trainer.model(fixed[0],fixed[1]),fixed[2],cfg['latitude_deg']).item()
 records=[];restore_record=None
 for i in range(10):
  b=batch(train,i);old=trainer.model.head.weight.detach().clone();lr=trainer.optimizer.param_groups[0]['lr'];torch.cuda.synchronize();t=time.perf_counter();row=trainer.train_step(b);torch.cuda.synchronize();elapsed=time.perf_counter()-t
  head=trainer.model.head.weight;grad=head.grad.reshape(16,171,-1)
  untouched=float(grad[:,:142].abs().max());assert untouched==0
  before_head=old.reshape(16,171,-1);after_head=head.detach().reshape(16,171,-1)
  assert torch.equal(before_head[:,:142],after_head[:,:142])
  delta=float((head.detach()-old).norm());assert delta>0
  gradients=[p.grad for p in trainer.model.parameters() if p.grad is not None]
  row.update(pair_index=i,target_UTC=train.epochs[i+1].isoformat(),learning_rate=lr,wall_s=elapsed,preprocess_s=preprocess[-1],head_parameter_delta_l2=delta,nonDEN_head_gradient_absmax=untouched,nonDEN_head_parameters_exact=True,finite_gradient_tensors=len(gradients),nonzero_gradient_tensors=sum(bool(g.count_nonzero().item()) for g in gradients),peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())
  assert row['peak_allocated_bytes']<=20*2**30 and time.perf_counter()-start<890
  records.append(row);print(json.dumps(dict(event='optimizer_update',**row)),flush=True)
  # Durable actual update records survive a later failure.
  with (F/'updates.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
  if i==4:
   mh=digest(trainer.model.state_dict());oh=digest(trainer.optimizer.state_dict());sh=trainer.scheduler.state_dict();t=time.perf_counter();p=F/'real_step5.pt'
   trainer.save(p,dict(label=LABEL,tag=plan['tag'],statistics_SHA256=cfg['statistics_SHA256'],source_manifest_SHA256=plan['manifest_SHA256'],code_SHA256=pre['frozen_SHA256']))
   ph=sha(p);trainer.model.eval()
   with torch.no_grad():pred_before=trainer.model(fixed[0],fixed[1]).detach().cpu()
   # Explicitly free all parameter/gradient references before constructing replacement.
   del model,trainer,head,grad,old,before_head,after_head,gradients,b;gc.collect();torch.cuda.empty_cache()
   trainer=DenTrainer(build_direct(architecture).cuda(),cfg);attach();restore_den(trainer,p,ph,trusted_root=F)
   assert trainer.step==5 and digest(trainer.model.state_dict())==mh and digest(trainer.optimizer.state_dict())==oh and trainer.scheduler.state_dict()==sh
   trainer.model.eval()
   with torch.no_grad():pred_after=trainer.model(fixed[0],fixed[1]).detach().cpu()
   torch.testing.assert_close(pred_before,pred_after,rtol=0,atol=0)
   restore_record=dict(PASS=True,step=5,checkpoint_SHA256=ph,model_exact=True,optimizer_exact=True,scheduler_exact=True,prediction_exact=True,save_restore_wall_s=time.perf_counter()-t)
   dump(F/'checkpoint_restore.json',restore_record);del pred_before,pred_after
 assert trainer.step==steps[0]==10
 trainer.model.eval();trainer.optimizer.zero_grad(set_to_none=True)
 with torch.no_grad():final_fixed=den_objective(trainer.model(fixed[0],fixed[1]),fixed[2],cfg['latitude_deg']).item()
 validation_hash=digest(trainer.model.state_dict());validation_optim_hash=digest(trainer.optimizer.state_dict());validation_step_count=trainer.step
 manifest=json.loads((ROOT/'experiments/fourcastden_den_engineering_v3/dataset_manifest.json').read_text())['frames']['2022']
 norm=load_statistics();rows=[];predictions=[];losses=[];vstart=time.perf_counter();positive=finite=total=0
 with torch.no_grad():
  for i in range(48):
   x,d,y=batch(val,i);p=trainer.model(x,d);assert p.shape==(1,171,36,72) and torch.isfinite(p).all()
   losses.append(den_objective(p,y,cfg['latitude_deg']).item())
   physical=(p[0,DEN_INDICES.tolist()].cpu().numpy().astype(float)*norm.stds[DEN_INDICES]+norm.means[DEN_INDICES])*1000
   predictions.append(physical.astype(np.float32));positive+=int((physical>0).sum());finite+=int(np.isfinite(physical).sum());total+=physical.size
   with np.load(ROOT/manifest[i+1]['path']) as n:truth=n['DEN'].astype(float)*1000;zg=n['ZG'].astype(float)*.01
   for row in evaluate_fields(physical,truth,np.asarray(cfg['latitude_deg']),zg):rows.append(dict(year=2022,pair=i,target_UTC=manifest[i+1]['UTC'],method='AFNONet_DEN_10updates',**row))
 assert digest(trainer.model.state_dict())==validation_hash and digest(trainer.optimizer.state_dict())==validation_optim_hash and trainer.step==validation_step_count==10 and all(p.grad is None for p in trainer.model.parameters())
 vwall=time.perf_counter()-vstart;assert forwards[0]==62 and steps[0]==10
 t=time.perf_counter();trainer.save(F/'real_step10.pt',dict(label=LABEL,tag=plan['tag'],statistics_SHA256=cfg['statistics_SHA256'],source_manifest_SHA256=plan['manifest_SHA256'],code_SHA256=pre['frozen_SHA256']))
 csvout(O/'AI_validation_hourly.csv',rows);csvout(O/'AI_validation_summary.csv',aggregate(rows));np.savez_compressed(O/'AI_validation_local.npz',prediction_kg_m3=np.stack(predictions),target_UTC=[r['UTC'] for r in manifest[1:]]);savewall=time.perf_counter()-t
 torch.cuda.synchronize();fw=[e[0].elapsed_time(e[1]) for e in events]
 output=sum(p.stat().st_size for base in [F,O] for p in base.rglob('*') if p.is_file());assert output<2*2**30 and time.perf_counter()-start<890
 result=dict(PASS=True,tag=plan['tag'],optimizer_updates=steps[0],model_forwards=forwards[0],forward_breakdown=dict(training=10,fixed_train_pair_before_after=2,checkpoint_probes=2,validation=48),records=records,initial_fixed_train_loss=initial_fixed,final_fixed_train_loss=final_fixed,validation_normalized_loss=float(np.mean(losses)),validation_pairs=48,validation_no_grad=True,validation_model_and_optimizer_exact=True,initial_model_SHA256=initial_hash,final_model_SHA256=validation_hash,model_parameters=64695744,official_weights_loaded=False,checkpoint_restore=restore_record,checkpoints_SHA256={p.name:sha(p) for p in F.glob('*.pt')},physical_prediction_count=total,nonpositive_predictions=total-positive,nonfinite_predictions=total-finite,positive_fraction=positive/total,finite_fraction=finite/total,wall_s=time.perf_counter()-start,construction_s=construction,data_setup_s=data_setup,preprocess_total_s=sum(preprocess),validation_wall_s=vwall,save_final_outputs_s=savewall,forward_GPU_ms=fw,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),CPU_peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,output_bytes=output,hardware=hardware,science_training_ready=False,full_state_training=False)
 dump(F/'GPU_result.json',result);print('DEN GPU ENGINEERING COMPLETE',json.dumps({k:v for k,v in result.items() if k not in ['records','forward_GPU_ms']}),flush=True)
if __name__=='__main__':main()
