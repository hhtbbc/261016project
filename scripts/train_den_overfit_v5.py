"""One100-update fixed-real-pair AFNONet task. No work occurs on import."""
from pathlib import Path
import sys,os,json,time,gc,resource
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from train_den_gpu_smoke_v4 import sha,dump
F=ROOT/'experiments/fourcastden_den_overfit_v5';O=ROOT/'results/fourcastden_den_overfit_v5'

def main():
 from runtime.gpu_environment import configure_determinism,require_cuda,assert_visibility
 visibility=configure_determinism()  # before torch import, never alter device allocation
 import torch,numpy as np
 from training.den_engineering import pairs,DenTrainer,DEN_INDICES,LABEL,load_statistics,den_objective,evaluate_fields,restore_den
 from training.pipeline import build_direct,seed_all
 from training.den_overfit import validate_overfit_plan,array_sha,state_digest
 from persistence_den_engineering_v3 import csvout,aggregate
 assert_visibility(visibility);start=time.perf_counter();plan=json.loads((F/'plan.json').read_text());validate_overfit_plan(plan);pre=json.loads((F/'preflight.json').read_text());assert pre['PASS'] and pre['visibility']==visibility
 for n,h in pre['frozen_SHA256'].items():assert sha(ROOT/n)==h,n
 dump(F/'worker_launch_once.json',dict(training_tasks=1,max_updates=100,visibility=visibility))
 hardware=require_cuda(torch,visibility);torch.set_num_threads(4);torch.cuda.set_per_process_memory_fraction(20*2**30/hardware['total_bytes'],device=0)
 cfg=plan['training_config'];t=time.perf_counter();dataset=pairs(2021);cpu_pair=dataset[0]
 assert {k:array_sha(a) for k,a in zip(['X','D','Y'],cpu_pair)}==plan['cache_array_SHA256']
 fixed=tuple(a[None].cuda() for a in cpu_pair);torch.cuda.synchronize();cache_s=time.perf_counter()-t
 norm=load_statistics();lat=np.asarray(cfg['latitude_deg']);records=plan['source_frame_records']
 with np.load(ROOT/records[1]['path']) as n:truth=n['DEN'].astype(float)*1000;zg=n['ZG'].astype(float)*.01
 # Seed immediately before random initialization; never restore any v4 weight.
 seed_all(cfg['seed']);t=time.perf_counter();architecture=dict(cfg['architecture'],img_size=tuple(cfg['architecture']['img_size']));model=build_direct(architecture).cuda();trainer=DenTrainer(model,cfg);torch.cuda.synchronize();construction_s=time.perf_counter()-t
 assert sum(p.numel() for p in model.parameters())==64695744
 initial_hash=state_digest(model.state_dict());assert initial_hash==plan['expected_initial_model_SHA256'],'Initial model differs from frozen seed baseline'
 phase=['fixed_evaluation'];forward_counts={k:0 for k in ['training','fixed_evaluation','checkpoint_restore','validation']};updates=[0];events=[];fixed_input_identity_checks=[0]
 def before(module,args):
  forward_counts[phase[0]]+=1
  if phase[0]=='training':
   assert args[0] is fixed[0] and args[1] is fixed[1];fixed_input_identity_checks[0]+=1
  event=[torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True),phase[0]];event[0].record();events.append(event)
 def after(*_):events[-1][1].record()
 def before_step(*_):assert updates[0]<100 and phase[0]=='training'
 def after_step(*_):updates[0]+=1
 def attach():
  trainer.model.register_forward_pre_hook(before);trainer.model.register_forward_hook(after);trainer.optimizer.register_step_pre_hook(before_step);trainer.optimizer.register_step_post_hook(after_step)
 attach();metrics=[];snapshots={};snapshot_summary=[];snapshot_s=0.
 def evaluate_fixed(step):
  nonlocal snapshot_s
  t=time.perf_counter();phase[0]='fixed_evaluation';mode=trainer.model.training;mh=state_digest(trainer.model.state_dict());oh=state_digest(trainer.optimizer.state_dict());count=updates[0]
  trainer.model.eval()
  with torch.no_grad():
   p=trainer.model(fixed[0],fixed[1]);assert p.shape==(1,171,36,72) and torch.isfinite(p).all();loss=den_objective(p,fixed[2],lat).item();saved=p.detach().cpu()
  physical=(saved[0,DEN_INDICES.tolist()].numpy().astype(float)*norm.stds[DEN_INDICES]+norm.means[DEN_INDICES])*1000
  rr=evaluate_fields(physical,truth,lat,zg);metrics.extend(dict(step=step,normalized_loss=loss,**r) for r in rr);snapshots[step]=physical
  summary=dict(step=step,normalized_loss=loss,nonpositive_count=int((physical<=0).sum()),positive_fraction=float((physical>0).mean()),finite_fraction=float(np.isfinite(physical).mean()),global_metrics=[r for r in rr if r['region']=='global' and r['group'] in ['all','upper20_28','top28']])
  snapshot_summary.append(summary);dump(F/f'fixed_step{step}.json',summary)
  assert state_digest(trainer.model.state_dict())==mh and state_digest(trainer.optimizer.state_dict())==oh and updates[0]==count
  trainer.model.train(mode);snapshot_s+=time.perf_counter()-t;return saved
 initial_output=evaluate_fixed(0);del initial_output;rows=[];train_start=time.perf_counter()
 for i in range(100):
  phase[0]='training';old=trainer.model.head.weight.detach().clone();lr=trainer.optimizer.param_groups[0]['lr'];torch.cuda.synchronize();t=time.perf_counter();row=trainer.train_step(fixed);torch.cuda.synchronize();step_wall=time.perf_counter()-t
  head=trainer.model.head.weight;grad=head.grad.reshape(16,171,-1);assert float(grad[:,:142].abs().max())==0 and torch.equal(old.reshape(16,171,-1)[:,:142],head.detach().reshape(16,171,-1)[:,:142]);delta=float((head.detach()-old).norm());assert delta>0
  gradients=[p.grad for p in trainer.model.parameters() if p.grad is not None]
  row.update(train_pair_index=0,source_input_SHA256=plan['cache_array_SHA256']['X'],target_UTC=plan['train_target_UTC'],learning_rate=lr,head_parameter_delta_l2=delta,nonDEN_head_gradient_absmax=0.,nonDEN_head_parameters_exact=True,gradient_tensors=len(gradients),nonzero_finite_gradient_tensors=sum(bool(torch.isfinite(g).all() and g.count_nonzero()) for g in gradients),wall_s=step_wall,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())
  assert row['peak_allocated_bytes']<=20*2**30 and time.perf_counter()-start<295
  rows.append(row)
  with (F/'updates.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
  print(json.dumps(dict(event='actual_optimizer_update',**row)),flush=True)
  if trainer.step in plan['evaluation_steps']:
   output=evaluate_fixed(trainer.step)
   if trainer.step==100:output100=output
   else:del output
 training_and_snapshots_s=time.perf_counter()-train_start
 assert trainer.step==updates[0]==100 and fixed_input_identity_checks[0]==100
 assert {k:array_sha(a[0]) for k,a in zip(['X','D','Y'],fixed)}==plan['cache_array_SHA256']
 # Save only final full AdamW checkpoint; no intermediate model selected using validation.
 trainer.optimizer.zero_grad(set_to_none=True);mh=state_digest(trainer.model.state_dict());oh=state_digest(trainer.optimizer.state_dict());sched=trainer.scheduler.state_dict();t=time.perf_counter();checkpoint=F/'step100.pt'
 trainer.save(checkpoint,dict(label=LABEL,tag=plan['tag'],statistics_SHA256=plan['statistics_SHA256'],manifest_SHA256=plan['manifest_SHA256'],code_SHA256=pre['frozen_SHA256'],train_pair_index=0));checkpoint_hash=sha(checkpoint)
 del model,trainer,old,head,grad,gradients;gc.collect();torch.cuda.empty_cache()
 trainer=DenTrainer(build_direct(architecture).cuda(),cfg);attach();restore_den(trainer,checkpoint,checkpoint_hash,trusted_root=F);assert trainer.step==100 and state_digest(trainer.model.state_dict())==mh and state_digest(trainer.optimizer.state_dict())==oh and trainer.scheduler.state_dict()==sched
 phase[0]='checkpoint_restore';trainer.model.eval()
 with torch.no_grad():restored=trainer.model(fixed[0],fixed[1]).detach().cpu()
 torch.testing.assert_close(output100,restored,rtol=0,atol=0);restore_s=time.perf_counter()-t
 dump(F/'checkpoint_restore.json',dict(PASS=True,step=100,checkpoint_SHA256=checkpoint_hash,model_exact=True,optimizer_exact=True,scheduler_exact=True,output_exact=True,save_restore_s=restore_s));del restored,output100
 # FIRST AND ONLY validation pass: instantiated only after100 updates and restoration.
 phase[0]='validation';trainer.model.eval();trainer.optimizer.zero_grad(set_to_none=True);mh=state_digest(trainer.model.state_dict());oh=state_digest(trainer.optimizer.state_dict());count=updates[0];t=time.perf_counter();validation=pairs(2022);assert len(validation)==48
 manifest=json.loads((ROOT/'experiments/fourcastden_den_engineering_v3/dataset_manifest.json').read_text())['frames']['2022'];valrows=[];valpred=[];losses=[];nonpositive=0;nonfinite=0
 with torch.no_grad():
  for i in plan['validation_indices']:
   x,d,y=tuple(a[None].cuda() for a in validation[i]);p=trainer.model(x,d);assert p.shape==(1,171,36,72) and torch.isfinite(p).all();losses.append(den_objective(p,y,lat).item())
   physical=(p[0,DEN_INDICES.tolist()].cpu().numpy().astype(float)*norm.stds[DEN_INDICES]+norm.means[DEN_INDICES])*1000;valpred.append(physical);nonpositive+=int((physical<=0).sum());nonfinite+=int((~np.isfinite(physical)).sum())
   with np.load(ROOT/manifest[i+1]['path']) as n:ref=n['DEN'].astype(float)*1000;zz=n['ZG'].astype(float)*.01
   for r in evaluate_fields(physical,ref,lat,zz):valrows.append(dict(year=2022,pair=i,target_UTC=manifest[i+1]['UTC'],method='AFNONet_fixed_pair100',**r))
 assert state_digest(trainer.model.state_dict())==mh and state_digest(trainer.optimizer.state_dict())==oh and updates[0]==count==100 and all(p.grad is None for p in trainer.model.parameters());val_s=time.perf_counter()-t
 assert sum(forward_counts.values())==153 and forward_counts==plan['forward_budget'];assert_visibility(visibility)
 t=time.perf_counter();csvout(O/'fixed_sample_metrics.csv',metrics);csvout(O/'training_updates.csv',rows);csvout(O/'validation_hourly.csv',valrows);csvout(O/'validation_summary.csv',aggregate(valrows));np.savez_compressed(O/'fixed_predictions_local.npz',steps=np.asarray(list(snapshots)),prediction_kg_m3=np.stack(list(snapshots.values())));np.savez_compressed(O/'validation_predictions_local.npz',prediction_kg_m3=np.stack(valpred),target_UTC=[r['UTC'] for r in manifest[1:]]);save_s=time.perf_counter()-t
 torch.cuda.synchronize();forward_ms={phase:sum(e[0].elapsed_time(e[1]) for e in events if e[2]==phase) for phase in forward_counts};size=sum(p.stat().st_size for base in [F,O] for p in base.rglob('*') if p.is_file());assert size<2*2**30 and time.perf_counter()-start<295
 result=dict(PASS=True,tag=plan['tag'],training_tasks=1,actual_updates=100,train_pair_index=0,fixed_input_identity_checks=100,cache_unmodified=True,initial_model_SHA256=initial_hash,final_model_SHA256=mh,random_initialization=True,official_or_v4_weights_loaded=False,forward_counts=forward_counts,actual_forwards=sum(forward_counts.values()),fixed_snapshots=snapshot_summary,validation_passes=1,validation_after_step=100,validation_pairs=48,validation_no_grad=True,validation_model_optimizer_unchanged=True,validation_normalized_loss=float(np.mean(losses)),validation_nonpositive=nonpositive,validation_nonfinite=nonfinite,checkpoint_SHA256=checkpoint_hash,checkpoint_recovery_PASS=True,hardware=hardware,wall_s=time.perf_counter()-start,cache_s=cache_s,construction_s=construction_s,training_and_snapshots_s=training_and_snapshots_s,fixed_evaluation_s=snapshot_s,pure_update_wall_s=sum(r['wall_s'] for r in rows),save_restore_s=restore_s,validation_s=val_s,save_metrics_s=save_s,forward_GPU_ms=forward_ms,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),CPU_peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,output_bytes=size,science_training_ready=False)
 dump(F/'GPU_result.json',result);print('FIXED PAIR100 GPU COMPLETE',json.dumps({k:v for k,v in result.items() if k!='fixed_snapshots'}),flush=True)
if __name__=='__main__':main()
