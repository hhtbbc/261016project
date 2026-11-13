"""Resume trusted v5 step100; only outer v6 budget authorizes100 more updates."""
from pathlib import Path
import sys,os,json,time,gc,resource
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from train_den_gpu_smoke_v4 import sha,dump
F=ROOT/'experiments/fourcastden_den_overfit_continuation_v6';O=ROOT/'results/fourcastden_den_overfit_continuation_v6'

def main():
 from runtime.gpu_environment import configure_determinism,require_cuda,assert_visibility
 visibility=configure_determinism()
 import torch,numpy as np
 from training.den_engineering import pairs,DenTrainer,DEN_INDICES,LABEL,load_statistics,den_objective,evaluate_fields
 from training.pipeline import build_direct,seed_all
 from training.den_overfit import array_sha,state_digest
 from training.den_continuation import ContinuationBudget,validate_continuation_plan,audited_restore,rng_snapshot,rng_fingerprint
 from persistence_den_engineering_v3 import csvout,aggregate
 assert_visibility(visibility);start=time.perf_counter();plan=json.loads((F/'plan.json').read_text());validate_continuation_plan(plan);pre=json.loads((F/'preflight.json').read_text());assert pre['PASS'] and pre['visibility']==visibility
 for n,h in pre['frozen_SHA256'].items():assert sha(ROOT/n)==h,n
 dump(F/'worker_launch_once.json',dict(GPU_tasks=1,start_step=100,max_additional_updates=100,visibility=visibility))
 hardware=require_cuda(torch,visibility);torch.set_num_threads(4);torch.cuda.set_per_process_memory_fraction(20*2**30/hardware['total_bytes'],device=0)
 cfg=plan['training_config'];t=time.perf_counter();dataset=pairs(2021);cpu_pair=dataset[0];assert {k:array_sha(a) for k,a in zip(['X','D','Y'],cpu_pair)}==plan['cache_array_SHA256'];fixed=tuple(a[None].cuda() for a in cpu_pair);torch.cuda.synchronize();cache_s=time.perf_counter()-t
 norm=load_statistics();lat=np.asarray(cfg['latitude_deg']);source=ROOT/plan['source_checkpoint']
 with np.load(ROOT/plan['source_frame_records'][1]['path']) as n:truth=n['DEN'].astype(float)*1000;zg=n['ZG'].astype(float)*.01
 seed_all(cfg['seed']);t=time.perf_counter();architecture=dict(cfg['architecture'],img_size=tuple(cfg['architecture']['img_size']));model=build_direct(architecture).cuda();trainer=DenTrainer(model,cfg);assert sum(p.numel() for p in model.parameters())==64695744
 restored=audited_restore(trainer,source,plan['source_checkpoint_SHA256'],root=source.parent,expected_step=100,expected_metadata=plan['source_expected_metadata']);assert restored['model_SHA256']==plan['source_summary']['model_SHA256'] and trainer.config['max_train_steps']==100
 restore_initial_s=time.perf_counter()-t;budget=ContinuationBudget(100,100);phase=['fixed_evaluation'];counts={k:0 for k in plan['forward_budget']};events=[];identity_checks=[0]
 def before(module,args):
  counts[phase[0]]+=1
  if phase[0]=='training':assert args[0] is fixed[0] and args[1] is fixed[1];identity_checks[0]+=1
  e=[torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True),phase[0]];e[0].record();events.append(e)
 def after(*_):events[-1][1].record()
 def before_step(*_):
  assert phase[0]=='training';budget.before_step(trainer.step)
 def after_step(*_):budget.after_step(trainer.step+1)
 def attach():
  trainer.model.register_forward_pre_hook(before);trainer.model.register_forward_hook(after);trainer.optimizer.register_step_pre_hook(before_step);trainer.optimizer.register_step_post_hook(after_step)
 attach();metrics=[];snapshots={};summaries=[];fixed_eval_s=0.
 def evaluate_fixed(step):
  nonlocal fixed_eval_s
  t=time.perf_counter();phase[0]='fixed_evaluation';mode=trainer.model.training;mh=state_digest(trainer.model.state_dict());oh=state_digest(trainer.optimizer.state_dict());rng=rng_fingerprint(rng_snapshot());completed=budget.completed
  trainer.model.eval()
  with torch.no_grad():
   prediction=trainer.model(fixed[0],fixed[1]);assert prediction.shape==(1,171,36,72) and torch.isfinite(prediction).all();loss=den_objective(prediction,fixed[2],lat).item();output=prediction.detach().cpu()
  physical=(output[0,DEN_INDICES.tolist()].numpy().astype(float)*norm.stds[DEN_INDICES]+norm.means[DEN_INDICES])*1000;rr=evaluate_fields(physical,truth,lat,zg)
  snapshots[step]=physical;metrics.extend(dict(step=step,normalized_loss=loss,**r) for r in rr);summary=dict(step=step,normalized_loss=loss,nonpositive_count=int((physical<=0).sum()),positive_fraction=float((physical>0).mean()),finite_fraction=float(np.isfinite(physical).mean()),global_metrics=[r for r in rr if r['region']=='global' and r['group'] in ['all','upper20_28','top28']]);summaries.append(summary);dump(F/f'fixed_step{step}.json',summary)
  trainer.model.train(mode)
  assert state_digest(trainer.model.state_dict())==mh and state_digest(trainer.optimizer.state_dict())==oh and budget.completed==completed and rng_fingerprint(rng_snapshot())==rng
  fixed_eval_s+=time.perf_counter()-t;return output
 initial_output=evaluate_fixed(100);del initial_output
 # BEFORE ANY NEW UPDATE: compare exact frozen v5 DEN output plus registered metrics.
 with np.load(ROOT/plan['historical_prediction_path']) as n:
  idx=list(n['steps']).index(100);historical=n['prediction_kg_m3'][idx]
 tol=plan['restore_tolerances'];np.testing.assert_allclose(snapshots[100],historical,rtol=tol['physical_DEN_array_rtol'],atol=tol['physical_DEN_array_atol'])
 old=json.loads((ROOT/plan['historical_metrics_path']).read_text());np.testing.assert_allclose(summaries[0]['normalized_loss'],old['normalized_loss'],rtol=tol['normalized_loss_rtol'],atol=tol['normalized_loss_atol'])
 metric_deltas={}
 for a in summaries[0]['global_metrics']:
  b=next(x for x in old['global_metrics'] if x['group']==a['group'])
  for k in ['relative_RMS','RMSE','bias']:
   np.testing.assert_allclose(a[k],b[k],rtol=tol['metrics_rtol'],atol=tol['metrics_atol']);metric_deltas[a['group']+'_'+k]=a[k]-b[k]
 assert summaries[0]['nonpositive_count']==old['nonpositive_count']==0 and trainer.model.training==plan['source_summary']['model_training']
 dump(F/'initial_restore_gate.json',dict(PASS=True,new_updates_before_gate=0,checkpoint=restored,config_exact=True,RNG_exact=True,training_mode_exact=True,DEN_array_bitwise_exact=bool(np.array_equal(snapshots[100],historical)),DEN_max_abs_difference=float(abs(snapshots[100]-historical).max()),normalized_loss_difference=summaries[0]['normalized_loss']-old['normalized_loss'],metric_differences=metric_deltas,tolerances=tol));del historical
 rows=[];train_start=time.perf_counter()
 for _ in range(plan['additional_updates']):
  phase[0]='training';oldhead=trainer.model.head.weight.detach().clone();lr=trainer.optimizer.param_groups[0]['lr'];torch.cuda.synchronize();t=time.perf_counter();row=trainer.train_step(fixed);torch.cuda.synchronize();elapsed=time.perf_counter()-t
  head=trainer.model.head.weight;grad=head.grad.reshape(16,171,-1);assert float(grad[:,:142].abs().max())==0 and torch.equal(oldhead.reshape(16,171,-1)[:,:142],head.detach().reshape(16,171,-1)[:,:142]);delta=float((head.detach()-oldhead).norm());assert delta>0
  gradients=[p.grad for p in trainer.model.parameters() if p.grad is not None];opt_steps=[float(x['step']) for x in trainer.optimizer.state.values()];assert min(opt_steps)==max(opt_steps)==trainer.step
  row.update(new_update=budget.completed,train_pair_index=0,source_input_SHA256=plan['cache_array_SHA256']['X'],learning_rate=lr,gradient_clipped=row['gradient_l2_before_clip']>cfg['gradient_clip_norm'],head_parameter_delta_l2=delta,nonDEN_head_gradient_absmax=0.,nonDEN_head_parameters_exact=True,finite_nonzero_gradient_tensors=sum(bool(torch.isfinite(g).all() and g.count_nonzero()) for g in gradients),optimizer_internal_step=trainer.step,wall_s=elapsed,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved());rows.append(row)
  assert row['peak_allocated_bytes']<=20*2**30 and time.perf_counter()-start<295
  with (F/'updates.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
  print(json.dumps(dict(event='continuation_update',**row)),flush=True)
  if trainer.step in [150,200]:
   out=evaluate_fixed(trainer.step)
   if trainer.step==200:output200=out
   else:del out
 training_and_snapshots_s=time.perf_counter()-train_start;budget.assert_finished(trainer.step);assert identity_checks[0]==100 and {k:array_sha(a[0]) for k,a in zip(['X','D','Y'],fixed)}==plan['cache_array_SHA256']
 # Original config stays max_train_steps100 even in final cumulative step200 checkpoint.
 trainer.optimizer.zero_grad(set_to_none=True);mode=trainer.model.training;final_model_hash=state_digest(trainer.model.state_dict());t=time.perf_counter();cp=F/'step200.pt';final_metadata=dict(label=LABEL,tag=plan['tag'],statistics_SHA256=plan['statistics_SHA256'],manifest_SHA256=plan['manifest_SHA256'],source_checkpoint_SHA256=plan['source_checkpoint_SHA256'],continuation_budget=dict(start_step=100,additional_updates=100,end_step=200),code_SHA256=pre['frozen_SHA256'],train_pair_index=0)
 trainer.save(cp,final_metadata);cp_sha=sha(cp);del model,trainer,oldhead,head,grad,gradients;gc.collect();torch.cuda.empty_cache();trainer=DenTrainer(build_direct(architecture).cuda(),cfg);attach()
 final_restore=audited_restore(trainer,cp,cp_sha,root=F,expected_step=200,expected_metadata=dict(tag=plan['tag'],source_checkpoint_SHA256=plan['source_checkpoint_SHA256'],statistics_SHA256=plan['statistics_SHA256'],manifest_SHA256=plan['manifest_SHA256'],train_pair_index=0));assert trainer.model.training==mode and state_digest(trainer.model.state_dict())==final_model_hash
 phase[0]='checkpoint_restore';trainer.model.eval()
 with torch.no_grad():after=trainer.model(fixed[0],fixed[1]).detach().cpu()
 torch.testing.assert_close(output200,after,rtol=0,atol=0);save_restore_s=time.perf_counter()-t;dump(F/'final_checkpoint_restore.json',dict(PASS=True,state=final_restore,output200_bitwise_exact=True,save_restore_s=save_restore_s));del output200,after
 # One final2022 pass, only after completing cumulative200.
 phase[0]='validation';trainer.optimizer.zero_grad(set_to_none=True);mh=state_digest(trainer.model.state_dict());oh=state_digest(trainer.optimizer.state_dict());t=time.perf_counter();validation=pairs(2022);assert len(validation)==48;manifest=json.loads((ROOT/'experiments/fourcastden_den_engineering_v3/dataset_manifest.json').read_text())['frames']['2022'];valrows=[];valpred=[];losses=[];nonpositive=nonfinite=0
 with torch.no_grad():
  for i in plan['validation_indices']:
   x,d,y=tuple(a[None].cuda() for a in validation[i]);p=trainer.model(x,d);assert p.shape==(1,171,36,72) and torch.isfinite(p).all();losses.append(den_objective(p,y,lat).item());physical=(p[0,DEN_INDICES.tolist()].cpu().numpy().astype(float)*norm.stds[DEN_INDICES]+norm.means[DEN_INDICES])*1000;valpred.append(physical);nonpositive+=int((physical<=0).sum());nonfinite+=int((~np.isfinite(physical)).sum())
   with np.load(ROOT/manifest[i+1]['path']) as n:ref=n['DEN'].astype(float)*1000;zz=n['ZG'].astype(float)*.01
   for r in evaluate_fields(physical,ref,lat,zz):valrows.append(dict(year=2022,pair=i,target_UTC=manifest[i+1]['UTC'],method='AFNONet_same_pair_cumulative200',**r))
 assert state_digest(trainer.model.state_dict())==mh and state_digest(trainer.optimizer.state_dict())==oh and trainer.step==200 and budget.completed==100 and all(p.grad is None for p in trainer.model.parameters());validation_s=time.perf_counter()-t;assert counts==plan['forward_budget'] and sum(counts.values())==152;assert_visibility(visibility)
 t=time.perf_counter();csvout(O/'fixed_sample_metrics.csv',metrics);csvout(O/'training_updates.csv',rows);csvout(O/'validation_hourly.csv',valrows);csvout(O/'validation_summary.csv',aggregate(valrows));np.savez_compressed(O/'fixed_predictions_local.npz',steps=np.asarray(list(snapshots)),prediction_kg_m3=np.stack(list(snapshots.values())));np.savez_compressed(O/'validation_predictions_local.npz',prediction_kg_m3=np.stack(valpred),target_UTC=[r['UTC'] for r in manifest[1:]]);save_metrics_s=time.perf_counter()-t
 torch.cuda.synchronize();forward_ms={name:sum(e[0].elapsed_time(e[1]) for e in events if e[2]==name) for name in counts};size=sum(p.stat().st_size for base in [F,O] for p in base.rglob('*') if p.is_file());assert size<2*2**30 and time.perf_counter()-start<295
 result=dict(PASS=True,tag=plan['tag'],training_tasks=1,start_step=100,additional_updates=100,end_step=200,config_max_train_steps_unchanged=trainer.config['max_train_steps'],source_checkpoint_SHA256=plan['source_checkpoint_SHA256'],restored_initial_model_SHA256=restored['model_SHA256'],final_model_SHA256=final_model_hash,initial_restore_gate_PASS=True,final_restore_PASS=True,initial_RNG_exact=True,fixed_input_identity_checks=identity_checks[0],cache_unmodified=True,fixed_snapshots=summaries,forward_counts=counts,actual_forwards=sum(counts.values()),validation_passes=1,validation_after_step=200,validation_pairs=48,validation_no_grad=True,validation_model_optimizer_unchanged=True,validation_normalized_loss=float(np.mean(losses)),validation_nonpositive=nonpositive,validation_nonfinite=nonfinite,checkpoint_SHA256=cp_sha,hardware=hardware,wall_s=time.perf_counter()-start,cache_s=cache_s,initial_restore_s=restore_initial_s,training_and_snapshots_s=training_and_snapshots_s,fixed_evaluation_s=fixed_eval_s,pure_update_wall_s=sum(r['wall_s'] for r in rows),save_restore_s=save_restore_s,validation_s=validation_s,save_metrics_s=save_metrics_s,forward_GPU_ms=forward_ms,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),CPU_peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,output_bytes=size,science_training_ready=False)
 dump(F/'GPU_result.json',result);print('CONTINUATION100TO200 COMPLETE',json.dumps({k:v for k,v in result.items() if k!='fixed_snapshots'}),flush=True)
if __name__=='__main__':main()
