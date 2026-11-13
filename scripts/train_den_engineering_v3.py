"""One real B14 GPU task: at most10 updates, random original AFNONet171."""
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
from pathlib import Path
import sys,json,time,gc,hashlib,resource
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import torch,numpy as np
from training.den_engineering import *
from training.pipeline import build_direct,seed_all
from run_tiegcm_mar23_2021_longrun import stream_sha
from persistence_den_engineering_v3 import aggregate,csvout
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
def main():
 start=time.perf_counter();pre=json.loads((F/'GPU_preflight.json').read_text());assert pre['PASS'];cfg=json.loads((F/'training_config.json').read_text())
 for name,expected in pre['frozen_SHA256'].items():assert stream_sha(ROOT/name)==expected,name
 (F/'gpu_launch_once.json').open('x').write(json.dumps(dict(max_updates=10,pretrained_loaded=False,real_2021_data=True,seed=cfg['seed'])))
 assert torch.cuda.is_available();torch.cuda.set_per_process_memory_fraction((20*2**30)/torch.cuda.get_device_properties(0).total_memory);seed_all(cfg['seed']);torch.set_num_threads(4)
 train=pairs(2021);validation=pairs(2022);assert train.split=='train' and validation.split=='validation'
 cfg['architecture']['img_size']=tuple(cfg['architecture']['img_size']);created=time.perf_counter();model=build_direct(cfg['architecture']).cuda();assert sum(p.numel() for p in model.parameters())==64695744
 trainer=DenTrainer(model,cfg);construct=time.perf_counter()-created;forward_count=[0];optimizer_calls=[0]
 def forward_hook(*args):forward_count[0]+=1
 def step_hook(*args):optimizer_calls[0]+=1
 model.register_forward_pre_hook(forward_hook);trainer.optimizer.register_step_post_hook(step_hook)
 batch=lambda d,i:tuple(x[None].cuda() for x in d[i])
 fixed=batch(train,0)
 trainer.model.eval()
 with torch.no_grad():initial_fixed_loss=den_objective(trainer.model(fixed[0],fixed[1]),fixed[2],cfg['latitude_deg']).item()
 initial_hash=digest(trainer.model.state_dict());records=[];checkpoint=F/'real_step5.pt';restore_record=None
 for i in range(10):
  torch.cuda.synchronize();t=time.perf_counter();head=trainer.model.head.weight.detach().clone();r=trainer.train_step(batch(train,i));torch.cuda.synchronize()
  grad=trainer.model.head.weight.grad.reshape(16,171,-1);r['unsupervised_head_gradient_absmax']=float(grad[:,:142].abs().max());assert r['unsupervised_head_gradient_absmax']==0
  r.update(pair_index=i,current_UTC=train.epochs[i].isoformat(),target_UTC=train.epochs[i+1].isoformat(),wall_s=time.perf_counter()-t,head_parameter_delta_l2=float((trainer.model.head.weight-head).norm()),peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())
  assert r['head_parameter_delta_l2']>0 and r['peak_allocated_bytes']<=20*2**30 and time.perf_counter()-start<900
  records.append(r);print(json.dumps(r),flush=True)
  if i==4:
   model_hash=digest(trainer.model.state_dict());optim_hash=digest(trainer.optimizer.state_dict());schedule=trainer.scheduler.state_dict();trainer.save(checkpoint,dict(label=LABEL,statistics_SHA256=cfg['statistics_SHA256'],real_data=True))
   checkpoint_hash=stream_sha(checkpoint);trainer.model.eval()
   with torch.no_grad():before=trainer.model(fixed[0],fixed[1]).detach().cpu()
   del model,trainer,grad,head;gc.collect();torch.cuda.empty_cache()
   trainer=DenTrainer(build_direct(cfg['architecture']).cuda(),cfg);trainer.model.register_forward_pre_hook(forward_hook);trainer.optimizer.register_step_post_hook(step_hook)
   restore_den(trainer,checkpoint,checkpoint_hash);assert trainer.step==5 and digest(trainer.model.state_dict())==model_hash and digest(trainer.optimizer.state_dict())==optim_hash and trainer.scheduler.state_dict()==schedule
   trainer.model.eval()
   with torch.no_grad():after=trainer.model(fixed[0],fixed[1]).detach().cpu()
   torch.testing.assert_close(before,after,rtol=0,atol=0)
   restore_record=dict(PASS=True,step=5,checkpoint_SHA256=checkpoint_hash,model_exact=True,optimizer_exact=True,scheduler_exact=True,prediction_exact=True);del before,after
 assert optimizer_calls[0]==trainer.step==10
 trainer.model.eval();trainer.optimizer.zero_grad(set_to_none=True)
 with torch.no_grad():final_fixed_loss=den_objective(trainer.model(fixed[0],fixed[1]),fixed[2],cfg['latitude_deg']).item()
 pre_validation_hash=digest(trainer.model.state_dict());validation_rows=[];validation_loss=[];predictions=[];norm=load_statistics();lat=cfg['latitude_deg'];manifest=json.loads((F/'dataset_manifest.json').read_text())['frames']['2022']
 with torch.no_grad():
  for i in range(len(validation)):
   x,d,y=batch(validation,i);prediction=trainer.model(x,d);assert prediction.shape==y.shape==(1,171,36,72)
   validation_loss.append(den_objective(prediction,y,lat).item())
   native=prediction[0,DEN_INDICES.tolist()].cpu().numpy().astype(float)*norm.stds[DEN_INDICES]+norm.means[DEN_INDICES];physical=native*1000;predictions.append(physical.astype(np.float32))
   with np.load(ROOT/manifest[i+1]['path']) as n:truth=n['DEN'].astype(float)*1000;zg=n['ZG'].astype(float)*.01
   for row in evaluate_fields(physical,truth,np.asarray(lat),zg):validation_rows.append(dict(year=2022,pair=i,target_UTC=manifest[i+1]['UTC'],method='AFNONet_DEN_10updates',**row))
 assert digest(trainer.model.state_dict())==pre_validation_hash and all(p.grad is None for p in trainer.model.parameters()) and optimizer_calls[0]==10
 assert forward_count[0]==62,forward_count
 trainer.save(F/'real_step10.pt',dict(label=LABEL,statistics_SHA256=cfg['statistics_SHA256'],real_data=True))
 csvout(O/'AI_validation_hourly.csv',validation_rows);csvout(O/'AI_validation_summary.csv',aggregate(validation_rows));np.savez_compressed(O/'AI_validation_local.npz',prediction_kg_m3=np.stack(predictions),target_UTC=[x['UTC'] for x in manifest[1:]])
 total=sum(p.stat().st_size for base in [F,O] for p in base.rglob('*') if p.is_file());assert total<2*2**30 and time.perf_counter()-start<900 and torch.cuda.max_memory_allocated()<=20*2**30
 result=dict(PASS=True,label=LABEL,real_data=True,optimizer_updates=10,optimizer_step_hook_calls=optimizer_calls[0],model_forward_calls=forward_count[0],forward_breakdown=dict(train=10,fixed_train_before_after=2,checkpoint_probe_before_after=2,validation=48),records=records,initial_fixed_train_pair_loss=initial_fixed_loss,final_fixed_train_pair_loss=final_fixed_loss,validation_normalized_DEN_loss=float(np.mean(validation_loss)),validation_pairs=48,validation_no_grad=True,validation_parameters_exact=True,checkpoint_restore=restore_record,model_parameter_count=64695744,model_initial_SHA256=initial_hash,model_final_SHA256=pre_validation_hash,construction_s=construct,wall_s=time.perf_counter()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),CPU_peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,device=torch.cuda.get_device_name(),torch=torch.__version__,CUDA=torch.version.cuda,official_weights_loaded=False,full_state_training=False,science_training_ready=False,output_bytes=total)
 (F/'GPU_result.json').open('x').write(json.dumps(result,indent=2));print('REAL DEN ENGINEERING PASS',json.dumps({k:v for k,v in result.items() if k!='records'}),flush=True)
if __name__=='__main__':main()
