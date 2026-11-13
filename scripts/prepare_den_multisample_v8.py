"""Freeze v8 after read-only v7/data audit. No extraction or statistics fitting."""
from pathlib import Path
import sys,json,time,subprocess,os,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from train_den_gpu_smoke_v4 import sha,dump
F=ROOT/'experiments/fourcastden_den_multisample_continuation_v8';O=ROOT/'results/fourcastden_den_multisample_continuation_v8'
def main():
 start=time.perf_counter();assert not F.exists() and not O.exists();F.resolve().relative_to(ROOT);O.resolve().relative_to(ROOT);F.mkdir();O.mkdir()
 import numpy as np,torch
 from training.den_engineering import pairs,load_statistics,DEN_INDICES,DATA
 from training.den_overfit import array_sha
 from training.den_continuation import checkpoint_summary
 from training.den_multisample_continuation import additional_order,validate_plan,SOURCE_SHA256
 from training.pipeline import EpochPairs,validate_disjoint
 from persistence_den_engineering_v3 import csvout
 old=ROOT/'experiments/fourcastden_den_multisample_v7';oldout=ROOT/'results/fourcastden_den_multisample_v7';p7=json.loads((old/'plan.json').read_text());g7=json.loads((old/'GPU_result.json').read_text());assert g7['PASS'] and g7['optimizer_updates']==200
 protected=json.loads((old/'preflight.json').read_text())['frozen_SHA256']
 for base in [old,oldout]:
  for p in base.rglob('*'):
   if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 for n,h in protected.items():assert sha(ROOT/n)==h,n
 source=old/'step200.pt';assert sha(source)==SOURCE_SHA256==g7['checkpoint_SHA256'];cfg=p7['training_config'];meta=dict(tag=p7['tag'],statistics_SHA256=p7['statistics_SHA256'],manifest_SHA256=p7['manifest_SHA256'],fresh_initial_model_SHA256=p7['initial_model_SHA256']);summary=checkpoint_summary(source,SOURCE_SHA256,old,200,meta,cfg);history=json.loads((old/'checkpoint_restore.json').read_text())['state']
 for k,v in summary.items():assert v==history[k],k
 assert summary['model_training'] is False and summary['optimizer_state_entries']==148 and summary['model_SHA256']==g7['final_model_SHA256']
 manifest=json.loads((ROOT/'experiments/fourcastden_den_engineering_v3/dataset_manifest.json').read_text());stats=json.loads((ROOT/'experiments/fourcastden_den_engineering_v3/statistics.json').read_text());assert sha(DATA/'statistics.npz')==p7['statistics_SHA256']==stats['statistics_SHA256'];assert stats['source_year']==2021 and stats['validation_not_used'] and stats['fit_frame_SHA256']==[r['SHA256'] for r in manifest['frames']['2021']]
 ds1,ds2=pairs(2021),pairs(2022);validate_disjoint(ds1,ds2);assert len(ds1)==72 and len(ds2)==48;poison_checks=0
 for year,ds in [(2021,ds1),(2022,ds2)]:
  for r in manifest['frames'][str(year)]:
   assert sha(ROOT/r['path'])==r['SHA256']
   with np.load(ROOT/r['path']) as z:assert (z['DEN']>0).all() and np.isfinite(z['DEN']).all() and (np.diff(z['ZG'],axis=0)>0).all() and np.isfinite(z['ZG']).all()
  for i in range(len(ds)):
   x,d,y=ds[i];record=p7['pair_tables'][str(year)][i];assert {k:array_sha(a) for k,a in zip(['X_SHA256','D_SHA256','Y_SHA256'],[x,d,y])}=={k:record[k] for k in ['X_SHA256','D_SHA256','Y_SHA256']};assert tuple(x.shape)==(177,36,72) and tuple(d.shape)==(1,4) and tuple(y.shape)==(171,36,72)
   source_reader=ds.source;target=ds.epochs[i+1]
   def poison(t):
    s,a,c=source_reader(t);return (s+1234 if t==target else s),a,c
   xp,dp,yp=EpochPairs(ds.epochs,poison,ds.split)[i];assert torch.equal(x,xp) and torch.equal(d,dp) and not torch.equal(y,yp);poison_checks+=1
 np.testing.assert_array_equal(DEN_INDICES,np.arange(142,171));order=additional_order();counts=np.bincount(p7['train_order']+order,minlength=72).tolist();assert counts==[10]*72
 plan=dict(tag='fourcastden_den_multisample_continuation_v8',label=cfg['label'],training_config=cfg,source_checkpoint=str(source.relative_to(ROOT)),source_checkpoint_SHA256=SOURCE_SHA256,source_summary=summary,source_expected_metadata=meta,source_model_training=False,start_step=200,additional_updates=520,end_step=720,train_order=order,cumulative_exposure_counts=counts,forward_budget=dict(initial_restore=1,training=520,train_evaluation=72,validation=48,checkpoint_restore=1),expected_forwards=642,train_evaluation_indices=list(range(72)),validation_indices=list(range(48)),evaluation_after_step=720,validation_after_step=720,pair_tables=p7['pair_tables'],statistics_SHA256=p7['statistics_SHA256'],manifest_SHA256=p7['manifest_SHA256'],restore_array_rtol=0,restore_array_atol=0,restore_probe_pair=0,source_prediction_path=str((oldout/'AI_2021_predictions_local.npz').relative_to(ROOT)),one_checkpoint='step720.pt',display_validation_pair=0,display_native_ilev=24,max_tasks=1,no_retry=True,loss_analysis='raw losses and same-pair10-visit plus complete72-update epoch descriptions; not uniform checkpoint evaluation',limits=p7['limits'],estimated_pure_update_wall_s=520*g7['pure_update_wall_s']/200,estimated_total_s=140,safety_estimate_s=210,estimates_not_measurements=True,uninterrupted720_bitwise_equivalence='NOT_TESTED; source saved after final evaluations')
 validate_plan(plan,cfg);dump(F/'plan.json',plan);dump(F/'protected_inputs.json',protected);dump(F/'source_checkpoint_audit.json',summary);dump(F/'data_audit.json',dict(PASS=True,frames=[73,49],pairs=[72,48],future_poison_checks=poison_checks,all_pair_SHA_match_v7=True,statistics_2021_only=True,data_reextracted=False,statistics_refitted=False,source_checkpoint_mode=False,protected_assets=len(protected),wall_s=time.perf_counter()-start))
 csvout(O/'frozen_new_training_order.csv',[dict(step=i+201,new_update=i+1,pair_index=j,input_UTC=p7['pair_tables']['2021'][j]['input_UTC'],target_UTC=p7['pair_tables']['2021'][j]['target_UTC']) for i,j in enumerate(order)])
 dump(F/'resources_initial.json',dict(CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),GPU=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.free','--format=csv'],text=True),other_GPU_processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv'],text=True),free_disk_bytes=shutil.disk_usage(ROOT).free));print('V8 SOURCE/DATA/SCHEDULE PASS',len(protected),poison_checks,time.perf_counter()-start)
if __name__=='__main__':main()
