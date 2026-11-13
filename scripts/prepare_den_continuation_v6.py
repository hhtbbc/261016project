"""Read-only source-checkpoint identity/data audit and freeze separate v6 budget."""
from pathlib import Path
import os,sys,json,time,copy,subprocess,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from train_den_gpu_smoke_v4 import sha,dump
F=ROOT/'experiments/fourcastden_den_overfit_continuation_v6';O=ROOT/'results/fourcastden_den_overfit_continuation_v6'
SOURCE_SHA='e5183727e11c487b8f0c964dc5c80220f7e6a8448ecf60f3de5ef28165524eda'
def main():
 tick=time.perf_counter();assert not F.exists() and not O.exists();F.resolve().relative_to(ROOT);O.resolve().relative_to(ROOT);F.mkdir();O.mkdir()
 import numpy as np,torch
 from training.den_continuation import checkpoint_summary,validate_continuation_plan
 from training.den_overfit import array_sha
 from training.den_engineering import pairs,load_statistics,native_fields,DEN_INDICES
 from training.pipeline import EpochPairs
 old=ROOT/'experiments/fourcastden_den_overfit_v5';oldout=ROOT/'results/fourcastden_den_overfit_v5';oldplan=json.loads((old/'plan.json').read_text());oldresult=json.loads((old/'GPU_result.json').read_text());source=old/'step100.pt';assert source.resolve()==source and sha(source)==SOURCE_SHA
 cfg=copy.deepcopy(oldplan['training_config']);assert cfg['max_train_steps']==100
 provenance=dict(tag='fourcastden_den_overfit_v5',statistics_SHA256=oldplan['statistics_SHA256'],manifest_SHA256=oldplan['manifest_SHA256'],train_pair_index=0)
 summary=checkpoint_summary(source,SOURCE_SHA,old,100,provenance,cfg);assert summary['model_SHA256']==oldresult['final_model_SHA256'] and summary['model_training'] is True
 protected=json.loads((old/'preflight.json').read_text())['frozen_SHA256']
 for base in [old,oldout]:
  for p in base.rglob('*'):
   if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 for n,h in protected.items():assert sha(ROOT/n)==h,n
 ds=pairs(2021);x,d,y=ds[0];actual={k:array_sha(a) for k,a in zip(['X','D','Y'],[x,d,y])};assert actual==oldplan['cache_array_SHA256']
 assert tuple(x.shape)==(177,36,72) and tuple(d.shape)==(1,4) and tuple(y.shape)==(171,36,72);np.testing.assert_array_equal(DEN_INDICES,np.arange(142,171))
 source_frames=oldplan['source_frame_records'];target=ds.epochs[1];original=ds.source
 def poison(t):
  s,a,c=original(t);return (s+1234 if t==target else s),a,c
 xp,dp,yp=EpochPairs(ds.epochs,poison,'train')[0];torch.testing.assert_close(x,xp,rtol=0,atol=0);torch.testing.assert_close(d,dp,rtol=0,atol=0);assert not torch.equal(y,yp)
 norm=load_statistics();raw=native_fields(ROOT/source_frames[0]['path']);decoded=norm.decode(norm.encode(raw));rt=float(abs((decoded[DEN_INDICES]-raw[DEN_INDICES])/raw[DEN_INDICES]).max());assert rt<1e-5
 with np.load(ROOT/source_frames[1]['path']) as n:assert (n['DEN']>0).all() and np.isfinite(n['DEN']).all() and (np.diff(n['ZG'],axis=0)>0).all()
 plan=dict(tag='fourcastden_den_overfit_continuation_v6',label=cfg['label'],start_step=100,additional_updates=100,end_step=200,training_config=cfg,config_policy='exact v5 payload config retained, including max_train_steps=100; separate outer continuation budget',source_checkpoint=str(source.relative_to(ROOT)),source_checkpoint_SHA256=SOURCE_SHA,source_expected_metadata=provenance,source_summary=summary,train_pair_index=0,cache_array_SHA256=actual,source_frame_records=source_frames,train_input_UTC=oldplan['train_input_UTC'],train_target_UTC=oldplan['train_target_UTC'],statistics_SHA256=oldplan['statistics_SHA256'],manifest_SHA256=oldplan['manifest_SHA256'],evaluation_steps=[100,150,200],validation_after_step=200,validation_indices=list(range(48)),historical_prediction_path=str((oldout/'fixed_predictions_local.npz').relative_to(ROOT)),historical_metrics_path=str((old/'fixed_step100.json').relative_to(ROOT)),display_native_ilev=24,forward_budget=dict(training=100,fixed_evaluation=3,checkpoint_restore=1,validation=48),expected_forwards=152,restore_tolerances=dict(model_optimizer_scheduler_RNG_mode='exact',physical_DEN_array_rtol=0.,physical_DEN_array_atol=0.,normalized_loss_rtol=1e-7,normalized_loss_atol=1e-9,metrics_rtol=1e-10,metrics_atol=1e-12),max_tasks=1,no_retry=True,save_checkpoints=['step200.pt'],limits=dict(supervised_wall_s=300,worker_wall_s=295,GPU_bytes=20*2**30,CPU_RSS_bytes=8*2**30,output_bytes=2*2**30,free_disk_bytes=20*2**30),estimated_new_training_compute_s=12.365,estimated_total_wall_s=80,estimated_GPU_GiB=3,estimated_output_GiB=.8,estimates_not_measurements=True)
 validate_continuation_plan(plan,oldplan['training_config']);dump(F/'plan.json',plan);dump(F/'source_checkpoint_audit.json',dict(PASS=True,deserialized_CPU_only=True,source=summary));dump(F/'protected_inputs.json',protected)
 dump(F/'data_audit.json',dict(PASS=True,input_target_SHA_matches_v5=True,future_poison_PASS=True,statistics_refitted=False,data_reextracted=False,config_unchanged=True,max_DEN_relative_roundtrip_error=rt,protected_files=len(protected),wall_s=time.perf_counter()-tick))
 with (O/'fixed_Persistence.csv').open('xb') as f:f.write((oldout/'fixed_Persistence.csv').read_bytes())
 dump(F/'resources_initial.json',dict(CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),GPU=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.free','--format=csv'],text=True),other_GPU_processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv'],text=True),free_disk_bytes=shutil.disk_usage(ROOT).free))
 print('V6 SOURCE CONFIG/RNG/DATA AUDIT PASS',len(protected),time.perf_counter()-tick)
if __name__=='__main__':main()
