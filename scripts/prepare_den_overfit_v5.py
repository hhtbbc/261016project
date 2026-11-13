"""Freeze v5 fixed pair and its baseline; all existing v3/v4 assets remain read-only."""
from pathlib import Path
import os,sys,json,time,copy,subprocess,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from train_den_gpu_smoke_v4 import sha,dump
F=ROOT/'experiments/fourcastden_den_overfit_v5';O=ROOT/'results/fourcastden_den_overfit_v5'
def main():
 tick=time.perf_counter();assert not F.exists() and not O.exists();F.resolve().relative_to(ROOT);O.resolve().relative_to(ROOT);F.mkdir();O.mkdir()
 import numpy as np,torch
 from training.den_engineering import pairs,DEN_INDICES,load_statistics,native_fields,evaluate_fields
 from training.pipeline import EpochPairs
 from training.den_overfit import validate_overfit_plan,array_sha
 from persistence_den_engineering_v3 import csvout
 v3=ROOT/'experiments/fourcastden_den_engineering_v3';v4=ROOT/'experiments/fourcastden_den_gpu_smoke_v4';manifest=json.loads((v3/'dataset_manifest.json').read_text());oldplan=json.loads((v4/'plan.json').read_text());oldresult=json.loads((v4/'GPU_result.json').read_text());assert oldresult['PASS'] and oldresult['optimizer_updates']==10
 protected=json.loads((v4/'protected_inputs.json').read_text())
 for base in [v4,ROOT/'results/fourcastden_den_gpu_smoke_v4']:
  for p in base.rglob('*'):
   if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 for name,h in protected.items():assert sha(ROOT/name)==h,name
 frames=manifest['frames']['2021'];stats=json.loads((v3/'statistics.json').read_text());assert stats['fit_frame_SHA256']==[x['SHA256'] for x in frames] and stats['validation_not_used']
 ds=pairs(2021);assert len(ds)==72 and ds.epochs[0].isoformat()=='2021-03-23T00:00:00+00:00' and ds.epochs[1].isoformat()=='2021-03-23T01:00:00+00:00'
 x,d,y=ds[0];assert (tuple(x.shape),tuple(d.shape),tuple(y.shape))==((177,36,72),(1,4),(171,36,72));assert all(torch.isfinite(a).all() for a in [x,d,y]);np.testing.assert_array_equal(DEN_INDICES,np.arange(142,171))
 target=ds.epochs[1];source=ds.source
 def poison(t):
  s,a,d=source(t);return (s+1234 if t==target else s),a,d
 xp,dp,yp=EpochPairs(ds.epochs,poison,'train')[0];torch.testing.assert_close(x,xp,rtol=0,atol=0);torch.testing.assert_close(d,dp,rtol=0,atol=0);assert not torch.equal(y,yp)
 norm=load_statistics();raw=native_fields(ROOT/frames[0]['path']);decoded=norm.decode(norm.encode(raw));roundtrip=float(abs((decoded[DEN_INDICES]-raw[DEN_INDICES])/raw[DEN_INDICES]).max());assert roundtrip<1e-5
 with np.load(ROOT/frames[0]['path']) as n:p=n['DEN'].astype(float)*1000
 with np.load(ROOT/frames[1]['path']) as n:t=n['DEN'].astype(float)*1000;zg=n['ZG'].astype(float)*.01
 assert np.isfinite(t).all() and (t>0).all() and (np.diff(zg,axis=0)>0).all()
 lat=oldplan['training_config']['latitude_deg'];csvout(O/'fixed_Persistence.csv',[dict(method='Persistence',target_UTC=target.isoformat(),**r) for r in evaluate_fields(p,t,np.asarray(lat),zg)])
 cfg=copy.deepcopy(oldplan['training_config']);cfg['max_train_steps']=100
 plan=dict(tag='fourcastden_den_overfit_v5',label=cfg['label'],training_config=cfg,train_pair_index=0,train_input_UTC=ds.epochs[0].isoformat(),train_target_UTC=target.isoformat(),updates=100,evaluation_steps=[0,10,50,100],validation_after_step=100,validation_indices=list(range(48)),display_native_ilev=24,cache_policy='CPU fixed pair once; one GPU copy, identical tuple reused100 times; no augmentation',resume_source='none: seed-identical random initialization',expected_initial_model_SHA256=oldresult['initial_model_SHA256'],cache_array_SHA256=dict(X=array_sha(x),D=array_sha(d),Y=array_sha(y)),source_frame_records=frames[:2],statistics_SHA256=oldplan['statistics_SHA256'],manifest_SHA256=oldplan['manifest_SHA256'],forward_budget=dict(training=100,fixed_evaluation=4,validation=48,checkpoint_restore=1),expected_forwards=153,full_checkpoints=['step100.pt'],save_intermediate_checkpoint=False,max_tasks=1,no_retry=True,limits=dict(supervised_wall_s=300,worker_wall_s=295,GPU_bytes=20*2**30,CPU_RSS_bytes=8*2**30,output_bytes=2*2**30,free_disk_bytes=20*2**30),estimated_training_compute_s=15.633,estimated_total_wall_s=60,estimated_process_GPU_GiB=3,estimated_new_output_GiB=.8,estimates_not_measurements=True)
 validate_overfit_plan(plan);dump(F/'plan.json',plan);dump(F/'protected_inputs.json',protected)
 dump(F/'data_audit.json',dict(PASS=True,train_pair_index=0,training_samples=1,train_year=2021,validation_in_gradient=False,statistics_refitted=False,data_reextracted=False,source_SHA_verified=True,future_poison_PASS=True,max_DEN_relative_roundtrip_error=roundtrip,protected_files=len(protected),wall_s=time.perf_counter()-tick))
 dump(F/'resources_initial.json',dict(GPU=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.free','--format=csv'],text=True),other_GPU_processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv'],text=True),CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),free_disk_bytes=shutil.disk_usage(ROOT).free))
 print('FIXED SAMPLE AND PLAN PASS',len(protected),roundtrip,time.perf_counter()-tick)
if __name__=='__main__':main()
