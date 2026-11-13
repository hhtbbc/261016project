"""Strict v7 resume; separate520-update budget; final-only120 evaluations."""
from pathlib import Path
import sys,os,json,time,gc,resource
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from train_den_gpu_smoke_v4 import sha,dump
F=ROOT/'experiments/fourcastden_den_multisample_continuation_v8';O=ROOT/'results/fourcastden_den_multisample_continuation_v8'

def main():
 from runtime.gpu_environment import configure_determinism,require_cuda,assert_visibility
 visibility=configure_determinism()
 import torch,numpy as np
 from training.den_engineering import pairs,DenTrainer,DEN_INDICES,LABEL,load_statistics,den_objective,evaluate_fields
 from training.pipeline import build_direct,seed_all
 from training.den_overfit import array_sha,state_digest
 from training.den_continuation import ContinuationBudget,audited_restore,rng_snapshot,rng_fingerprint
 from training.den_multisample_continuation import validate_plan
 from training.den_multisample import exposure_counts
 from persistence_den_engineering_v3 import csvout,aggregate
 assert_visibility(visibility);start=time.perf_counter();plan=json.loads((F/'plan.json').read_text());validate_plan(plan);pre=json.loads((F/'preflight.json').read_text());assert pre['PASS'] and pre['visibility']==visibility
 for n,h in pre['frozen_SHA256'].items():assert sha(ROOT/n)==h,n
 dump(F/'worker_launch_once.json',dict(GPU_tasks=1,start_step=200,max_additional_updates=520,source_checkpoint=plan['source_checkpoint'],visibility=visibility))
 hardware=require_cuda(torch,visibility);torch.set_num_threads(4);torch.cuda.set_per_process_memory_fraction(20*2**30/hardware['total_bytes'],device=0)
 cfg=plan['training_config'];t=time.perf_counter();dataset=pairs(2021);assert dataset.split=='train' and len(dataset)==72;cache=[dataset[i] for i in range(72)]
 def check_cache():
  for i,b in enumerate(cache):
   record=plan['pair_tables']['2021'][i]
   for key,a in zip(['X_SHA256','D_SHA256','Y_SHA256'],b):assert array_sha(a)==record[key]
 check_cache();cache_s=time.perf_counter()-t;norm=load_statistics();lat=np.asarray(cfg['latitude_deg']);manifest=json.loads((ROOT/'experiments/fourcastden_den_engineering_v3/dataset_manifest.json').read_text())['frames']
 seed_all(cfg['seed']);t=time.perf_counter();architecture=dict(cfg['architecture'],img_size=tuple(cfg['architecture']['img_size']));model=build_direct(architecture).cuda();trainer=DenTrainer(model,cfg);torch.cuda.synchronize();construction_s=time.perf_counter()-t;assert sum(p.numel() for p in model.parameters())==64695744
 t=time.perf_counter();source=ROOT/plan['source_checkpoint'];source_state=audited_restore(trainer,source,plan['source_checkpoint_SHA256'],root=source.parent,expected_step=200,expected_metadata=plan['source_expected_metadata']);assert source_state==dict(PASS=True,**plan['source_summary']) and trainer.model.training is False and trainer.config['max_train_steps']==200
 initial_hash=state_digest(model.state_dict());initial_restore_s=time.perf_counter()-t
 budget=ContinuationBudget(200,520);phase=['initial_restore'];counts={k:0 for k in plan['forward_budget']};events=[];active_batch=[None];identity_checks=[0]
 def before(module,args):
  counts[phase[0]]+=1
  if phase[0]=='training':assert module.training and args[0] is active_batch[0][0] and args[1] is active_batch[0][1];identity_checks[0]+=1
  e=[torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True),phase[0]];e[0].record();events.append(e)
 def after(*_):events[-1][1].record()
 def before_step(*_):assert phase[0]=='training' and trainer.model.training;budget.before_step(trainer.step)
 def after_step(*_):budget.after_step(trainer.step+1)
 def attach():
  trainer.model.register_forward_pre_hook(before);trainer.model.register_forward_hook(after);trainer.optimizer.register_step_pre_hook(before_step);trainer.optimizer.register_step_post_hook(after_step)
 attach()
 # One source probe, before any new update; original eval mode and RNG verified.
 rng_before=rng_fingerprint(rng_snapshot());optimizer_before=state_digest(trainer.optimizer.state_dict());scheduler_before=state_digest(trainer.scheduler.state_dict());assert trainer.model.training is False
 with torch.no_grad():probe=trainer.model(*tuple(a[None].cuda() for a in cache[0][:2])).detach().cpu()
 physical=(probe[0,DEN_INDICES.tolist()].numpy().astype(float)*norm.stds[DEN_INDICES]+norm.means[DEN_INDICES])*1000
 with np.load(ROOT/plan['source_prediction_path']) as z:old_prediction=z['prediction_kg_m3'][0]
 np.testing.assert_allclose(physical,old_prediction,rtol=plan['restore_array_rtol'],atol=plan['restore_array_atol']);assert np.array_equal(physical,old_prediction)
 assert rng_fingerprint(rng_snapshot())==rng_before and state_digest(trainer.model.state_dict())==initial_hash and state_digest(trainer.optimizer.state_dict())==optimizer_before and state_digest(trainer.scheduler.state_dict())==scheduler_before and trainer.step==200 and budget.completed==0 and trainer.model.training is False
 trainer.model.train();assert trainer.model.training and rng_fingerprint(rng_snapshot())==rng_before and state_digest(trainer.model.state_dict())==initial_hash
 dump(F/'initial_restore_gate.json',dict(PASS=True,source=source_state,config_exact=True,original_eval_mode_verified=True,probe_no_grad=True,DEN_array_bitwise_exact=True,DEN_max_abs_difference=float(abs(physical-old_prediction).max()),RNG_unchanged_by_probe_and_mode_switch=True,training_mode_before201=True,new_updates_before_gate=0,uninterrupted720_equivalence='NOT_TESTED'))
 del probe,physical,old_prediction
 phase[0]='training';rows=[];transfer_s=0.;train_start=time.perf_counter()
 for i,index in enumerate(plan['train_order']):
  assert index==(i+200)%72 and trainer.step==i+200;record=plan['pair_tables']['2021'][index];t=time.perf_counter();b=tuple(a[None].cuda() for a in cache[index]);torch.cuda.synchronize();transfer_s+=time.perf_counter()-t;active_batch[0]=b
  oldhead=trainer.model.head.weight.detach().clone();lr=trainer.optimizer.param_groups[0]['lr'];torch.cuda.synchronize();t=time.perf_counter();row=trainer.train_step(b);torch.cuda.synchronize();elapsed=time.perf_counter()-t
  head=trainer.model.head.weight;grad=head.grad.reshape(16,171,-1);assert float(grad[:,:142].abs().max())==0 and torch.equal(oldhead.reshape(16,171,-1)[:,:142],head.detach().reshape(16,171,-1)[:,:142]);delta=float((head.detach()-oldhead).norm());assert delta>0
  gradients=[p.grad for p in trainer.model.parameters() if p.grad is not None];optsteps=[float(x['step']) for x in trainer.optimizer.state.values()];assert min(optsteps)==max(optsteps)==trainer.step
  row.update(new_update=budget.completed,optimizer_internal_step=trainer.step,model_training=trainer.model.training,pair_index=index,input_UTC=record['input_UTC'],target_UTC=record['target_UTC'],source_input_SHA256=record['X_SHA256'],learning_rate=lr,gradient_clipped=row['gradient_l2_before_clip']>1.,head_parameter_delta_l2=delta,nonDEN_head_gradient_absmax=0.,nonDEN_head_parameters_exact=True,finite_nonzero_gradient_tensors=sum(bool(torch.isfinite(g).all() and g.count_nonzero()) for g in gradients),wall_s=elapsed,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved());rows.append(row)
  assert row['peak_allocated_bytes']<=20*2**30 and time.perf_counter()-start<295
  with (F/'updates.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
  print(json.dumps(dict(event='actual_multisample_continuation_update',**row)),flush=True)
 training_wall_s=time.perf_counter()-train_start;budget.assert_finished(trainer.step);assert identity_checks[0]==520 and exposure_counts([i%72 for i in range(200)]+[r['pair_index'] for r in rows])==plan['cumulative_exposure_counts'];check_cache()
 csvout(O/'training_updates.csv',rows)
 # No final evaluation until cumulative720/additional520 updates finish. These are120 final-only one-step calls.
 trainer.optimizer.zero_grad(set_to_none=True);trainer.model.eval();model_hash=state_digest(trainer.model.state_dict());optimizer_hash=state_digest(trainer.optimizer.state_dict());train_predictions=[];train_rows=[];train_losses=[];validation_predictions=[];validation_rows=[];validation_losses=[];evaluation_times={};invalid={};evaluation_started_at=trainer.step
 for year,indices,name in [(2021,plan['train_evaluation_indices'],'train_evaluation'),(2022,plan['validation_indices'],'validation')]:
  phase[0]=name;t=time.perf_counter();ds=None if year==2021 else pairs(2022)
  if ds is not None:assert ds.split=='validation' and len(ds)==48
  rr=[];preds=[];losses=[];negative=nonfinite=0
  with torch.no_grad():
   for index in indices:
    cpu=cache[index] if year==2021 else ds[index];x,d,y=tuple(a[None].cuda() for a in cpu);p=trainer.model(x,d);assert p.shape==(1,171,36,72) and torch.isfinite(p).all();losses.append(den_objective(p,y,lat).item())
    if year==2021 and index==0:checkpoint_probe_output=p.detach().cpu()
    physical=(p[0,DEN_INDICES.tolist()].cpu().numpy().astype(float)*norm.stds[DEN_INDICES]+norm.means[DEN_INDICES])*1000;preds.append(physical);negative+=int((physical<=0).sum());nonfinite+=int((~np.isfinite(physical)).sum())
    with np.load(ROOT/manifest[str(year)][index+1]['path']) as n:truth=n['DEN'].astype(float)*1000;zg=n['ZG'].astype(float)*.01
    for r in evaluate_fields(physical,truth,lat,zg):rr.append(dict(year=year,pair=index,target_UTC=manifest[str(year)][index+1]['UTC'],method='AFNONet_multisample720',**r))
  assert state_digest(trainer.model.state_dict())==model_hash and state_digest(trainer.optimizer.state_dict())==optimizer_hash and trainer.step==720 and budget.completed==520 and all(p.grad is None for p in trainer.model.parameters())
  evaluation_times[name]=time.perf_counter()-t;invalid[str(year)]=dict(nonpositive=negative,nonfinite=nonfinite,prediction_values=len(indices)*29*36*72)
  if year==2021:train_predictions=preds;train_rows=rr;train_losses=losses
  else:validation_predictions=preds;validation_rows=rr;validation_losses=losses
 # Save one final checkpoint, with actual order, update trace SHA and measured resource snapshot.
 t=time.perf_counter();checkpoint=F/'step720.pt';metadata=dict(label=LABEL,tag=plan['tag'],statistics_SHA256=plan['statistics_SHA256'],manifest_SHA256=plan['manifest_SHA256'],code_SHA256=pre['frozen_SHA256'],training_order=plan['train_order'],cumulative_exposure_counts=plan['cumulative_exposure_counts'],updates_JSONL_SHA256=sha(F/'updates.jsonl'),updates_CSV_SHA256=sha(O/'training_updates.csv'),source_model_SHA256=initial_hash,source_checkpoint_SHA256=plan['source_checkpoint_SHA256'],continuation_budget=dict(start_step=200,additional_updates=520,end_step=720),training_records=rows,resource_snapshot_at_save=dict(elapsed_s=time.perf_counter()-start,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),CPU_peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,pure_update_wall_s=sum(r['wall_s'] for r in rows),training_wall_s=training_wall_s,evaluation_times=evaluation_times))
 trainer.save(checkpoint,metadata);checkpoint_hash=sha(checkpoint);del model,trainer,oldhead,head,grad,gradients,b;active_batch[0]=None;gc.collect();torch.cuda.empty_cache()
 trainer=DenTrainer(build_direct(architecture).cuda(),cfg);attach();recovered=audited_restore(trainer,checkpoint,checkpoint_hash,root=F,expected_step=720,expected_metadata=dict(tag=plan['tag'],statistics_SHA256=plan['statistics_SHA256'],manifest_SHA256=plan['manifest_SHA256'],source_model_SHA256=initial_hash,source_checkpoint_SHA256=plan['source_checkpoint_SHA256'],continuation_budget=dict(start_step=200,additional_updates=520,end_step=720),training_records=rows));assert recovered['model_SHA256']==model_hash and trainer.model.training is False
 phase[0]='checkpoint_restore'
 with torch.no_grad():restored=trainer.model(*tuple(a[None].cuda() for a in cache[0][:2])).detach().cpu()
 torch.testing.assert_close(restored,checkpoint_probe_output,rtol=0,atol=0);save_restore_s=time.perf_counter()-t;dump(F/'checkpoint_restore.json',dict(PASS=True,state=recovered,probe_train_pair=0,full_output_bitwise_exact=True,save_restore_s=save_restore_s));del restored,checkpoint_probe_output
 assert counts==plan['forward_budget'] and sum(counts.values())==642 and budget.completed==520 and trainer.step==720;assert_visibility(visibility)
 t=time.perf_counter()
 for year,preds,rr in [(2021,train_predictions,train_rows),(2022,validation_predictions,validation_rows)]:
  csvout(O/f'AI_{year}_hourly.csv',rr);csvout(O/f'AI_{year}_summary.csv',aggregate(rr));np.savez_compressed(O/f'AI_{year}_predictions_local.npz',prediction_kg_m3=np.stack(preds),target_UTC=[r['UTC'] for r in manifest[str(year)][1:]])
 save_outputs_s=time.perf_counter()-t;torch.cuda.synchronize();forward_ms={name:sum(e[0].elapsed_time(e[1]) for e in events if e[2]==name) for name in counts};size=sum(p.stat().st_size for base in [F,O] for p in base.rglob('*') if p.is_file());assert size<2*2**30 and time.perf_counter()-start<295
 result=dict(PASS=True,tag=plan['tag'],GPU_tasks=1,optimizer_updates=520,cumulative_step=720,start_step=200,additional_updates=520,config_max_train_steps_unchanged=trainer.config['max_train_steps'],source_checkpoint_SHA256=plan['source_checkpoint_SHA256'],restored_source_model_SHA256=initial_hash,final_model_SHA256=model_hash,random_initialization=False,source_restore_gate_PASS=True,initial_restore_s=initial_restore_s,forward_counts=counts,model_forwards=642,train_order_verified=True,cumulative_exposure_counts=plan['cumulative_exposure_counts'],cache_unchanged=True,train_pairs_evaluated=72,validation_pairs_evaluated=48,evaluation_started_at_step=evaluation_started_at,validation_passes=1,train_eval_passes=1,evaluations_no_grad=True,evaluations_model_optimizer_unchanged=True,train_normalized_loss=float(np.mean(train_losses)),validation_normalized_loss=float(np.mean(validation_losses)),invalid_predictions=invalid,checkpoint_SHA256=checkpoint_hash,checkpoint_recovery_PASS=True,hardware=hardware,wall_s=time.perf_counter()-start,cache_setup_s=cache_s,construction_s=construction_s,training_wall_s=training_wall_s,training_GPU_transfer_s=transfer_s,pure_update_wall_s=sum(r['wall_s'] for r in rows),evaluation_times=evaluation_times,save_restore_s=save_restore_s,save_outputs_s=save_outputs_s,forward_GPU_ms=forward_ms,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),CPU_peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,output_bytes=size,science_training_ready=False)
 dump(F/'GPU_result.json',result);print('MULTISAMPLE720 COMPLETE',json.dumps(result),flush=True)
if __name__=='__main__':main()
