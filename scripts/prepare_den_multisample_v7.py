"""Read-only audit of all120 pairs, freeze200 cyclic exposures; never fit statistics."""
from pathlib import Path
import os,sys,json,time,copy,subprocess,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from train_den_gpu_smoke_v4 import sha,dump
F=ROOT/'experiments/fourcastden_den_multisample_v7';O=ROOT/'results/fourcastden_den_multisample_v7'
def main():
 tick=time.perf_counter();assert not F.exists() and not O.exists();F.resolve().relative_to(ROOT);O.resolve().relative_to(ROOT);F.mkdir();O.mkdir()
 import numpy as np,torch
 from training.den_multisample import cyclic_indices,exposure_counts,validate_multisample_plan,INITIAL_MODEL_SHA256
 from training.den_overfit import array_sha
 from training.den_engineering import pairs,DEN_INDICES,DATA,load_statistics,native_fields
 from training.pipeline import EpochPairs,validate_disjoint
 from persistence_den_engineering_v3 import csvout
 old=ROOT/'experiments/fourcastden_den_overfit_continuation_v6';oldout=ROOT/'results/fourcastden_den_overfit_continuation_v6';protected=json.loads((old/'preflight.json').read_text())['frozen_SHA256']
 for base in [old,oldout]:
  for p in base.rglob('*'):
   if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 for n,h in protected.items():assert sha(ROOT/n)==h,n
 v3=ROOT/'experiments/fourcastden_den_engineering_v3';manifest=json.loads((v3/'dataset_manifest.json').read_text());stats=json.loads((v3/'statistics.json').read_text());assert sha(DATA/'statistics.npz')==manifest['statistics']==stats['statistics_SHA256'];assert stats['source_year']==2021 and stats['fit_frame_SHA256']==[x['SHA256'] for x in manifest['frames']['2021']] and stats['validation_not_used']
 train=pairs(2021);val=pairs(2022);validate_disjoint(train,val);assert len(train)==72 and len(val)==48;np.testing.assert_array_equal(DEN_INDICES,np.arange(142,171));norm=load_statistics();tables={};poison_checks=0;roundtrip=0.
 for year,ds,nf in [(2021,train,73),(2022,val,49)]:
  rows=manifest['frames'][str(year)];assert len(rows)==nf
  for record in rows:
   assert sha(ROOT/record['path'])==record['SHA256']
   with np.load(ROOT/record['path']) as n:assert np.isfinite(n['DEN']).all() and (n['DEN']>0).all() and np.isfinite(n['ZG']).all() and (np.diff(n['ZG'],axis=0)>0).all()
   raw=native_fields(ROOT/record['path']);recovered=norm.decode(norm.encode(raw));roundtrip=max(roundtrip,float(abs((recovered[DEN_INDICES]-raw[DEN_INDICES])/raw[DEN_INDICES]).max()))
  table=[]
  for i in range(len(ds)):
   x,d,y=ds[i];assert (tuple(x.shape),tuple(d.shape),tuple(y.shape))==((177,36,72),(1,4),(171,36,72)) and all(torch.isfinite(z).all() for z in [x,d,y]);source=ds.source;target=ds.epochs[i+1]
   def poison(t):
    s,a,c=source(t);return (s+1234 if t==target else s),a,c
   xp,dp,yp=EpochPairs(ds.epochs,poison,ds.split)[i];torch.testing.assert_close(x,xp,rtol=0,atol=0);torch.testing.assert_close(d,dp,rtol=0,atol=0);assert not torch.equal(y,yp);poison_checks+=1
   table.append(dict(pair_index=i,input_UTC=ds.epochs[i].isoformat(),target_UTC=ds.epochs[i+1].isoformat(),X_SHA256=array_sha(x),D_SHA256=array_sha(d),Y_SHA256=array_sha(y)))
  tables[str(year)]=table
 assert roundtrip<1e-5 and poison_checks==120
 oldcfg=json.loads((ROOT/'experiments/fourcastden_den_overfit_v5/plan.json').read_text())['training_config'];cfg=copy.deepcopy(oldcfg);cfg['max_train_steps']=200;order=cyclic_indices()
 plan=dict(tag='fourcastden_den_multisample_v7',label=cfg['label'],training_config=cfg,initial_model_SHA256=INITIAL_MODEL_SHA256,initialization='fresh seed20261113; no official/v4/v5/v6 checkpoint loaded',train_order=order,exposure_counts=exposure_counts(order),updates=200,train_evaluation_indices=list(range(72)),validation_indices=list(range(48)),validation_after_step=200,evaluation_after_step=200,forward_budget=dict(training=200,train_evaluation=72,validation=48,checkpoint_restore=1),expected_forwards=321,loss_trend=dict(type='trailing_arithmetic_mean',window=24,min_periods=24,descriptive_only=True),pair_visit_loss_comparison='first versus last pre-update loss for same pair; not a full initial-model evaluation',initial_full_train_evaluation=False,train_cache='load72 CPU tuples once and SHA-freeze; GPU copy for each selected pair',pair_tables=tables,statistics_SHA256=stats['statistics_SHA256'],manifest_SHA256=sha(v3/'dataset_manifest.json'),display_validation_pair=0,display_native_ilev=24,one_checkpoint='step200.pt',checkpoint_probe_train_pair=0,max_tasks=1,no_retry=True,limits=dict(supervised_wall_s=300,worker_wall_s=295,GPU_bytes=20*2**30,CPU_RSS_bytes=8*2**30,output_bytes=2*2**30,free_disk_bytes=20*2**30),estimated_pure_training_s=24.49,estimated_total_wall_s=110,estimated_process_GPU_GiB=3,estimated_output_GiB=.85,estimates_not_measurements=True)
 validate_multisample_plan(plan,oldcfg);dump(F/'plan.json',plan);dump(F/'protected_inputs.json',protected);dump(F/'data_audit.json',dict(PASS=True,frames=[73,49],pairs=[72,48],future_poison_checks=120,all_pair_contracts_PASS=True,year_separation_PASS=True,statistics_2021_only=True,statistics_refitted=False,data_reextracted=False,max_DEN_relative_roundtrip_error=roundtrip,protected_assets=len(protected),wall_s=time.perf_counter()-tick))
 csvout(O/'frozen_training_order.csv',[dict(update=i+1,pair_index=j,input_UTC=tables['2021'][j]['input_UTC'],target_UTC=tables['2021'][j]['target_UTC']) for i,j in enumerate(order)])
 dump(F/'resources_initial.json',dict(CUDA_VISIBLE_DEVICES=os.environ.get('CUDA_VISIBLE_DEVICES'),GPU=subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total,memory.free','--format=csv'],text=True),other_GPU_processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv'],text=True),free_disk_bytes=shutil.disk_usage(ROOT).free))
 print('V7 READONLY120 PAIRS AND ORDER PASS',len(protected),poison_checks,time.perf_counter()-tick)
if __name__=='__main__':main()
