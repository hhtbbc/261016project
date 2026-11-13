"""Read-only v3 audit and freeze a separate v4 plan; no extraction or statistic fit."""
from pathlib import Path
import sys,os,json,hashlib,time,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from train_den_gpu_smoke_v4 import F,O,sha,dump
from runtime.gpu_environment import visibility_snapshot,require_gpu_assignment

def main():
 start=time.perf_counter();assert not F.exists() and not O.exists();assert F.resolve().is_relative_to(ROOT) and O.resolve().is_relative_to(ROOT);F.mkdir();O.mkdir()
 from training.den_engineering import pairs,DEN_INDICES,load_statistics,native_fields,DATA
 from training.pipeline import EpochPairs
 import numpy as np,torch
 v3=ROOT/'experiments/fourcastden_den_engineering_v3';m=json.loads((v3/'dataset_manifest.json').read_text());stats=json.loads((v3/'statistics.json').read_text());frozen={}
 assert stats['source_year']==2021 and stats['fit_frame_SHA256']==[r['SHA256'] for r in m['frames']['2021']]
 assert sha(DATA/'statistics.npz')==stats['statistics_SHA256']==m['statistics']
 for p in [v3/'dataset_manifest.json',v3/'statistics.json',DATA/'statistics.npz',DATA/'grid.npz']:
  frozen[str(p.relative_to(ROOT))]=sha(p)
 for year,nframes,npairs in [(2021,73,72),(2022,49,48)]:
  rows=m['frames'][str(year)];assert len(rows)==nframes
  for row in rows:
   p=ROOT/row['path'];assert sha(p)==row['SHA256'];frozen[row['path']]=row['SHA256'];frozen[row['source']]=row['source_SHA256']
 for name,h in json.loads((v3/'protected_files.json').read_text()).items():
  assert sha(ROOT/name)==h,name;frozen[name]=h
 for n,h in list(frozen.items()):assert sha(ROOT/n)==h,n
 np.testing.assert_array_equal(DEN_INDICES,np.arange(142,171))
 norm=load_statistics();checks=[];roundtrip=0.
 for year,expected in [(2021,72),(2022,48)]:
  ds=pairs(year);assert len(ds)==expected
  for i in range(len(ds)):
   x,d,y=ds[i];assert tuple(x.shape)==(177,36,72) and tuple(d.shape)==(1,4) and tuple(y.shape)==(171,36,72) and all(torch.isfinite(a).all() for a in [x,d,y])
   source=ds.source;target=ds.epochs[i+1]
   def poison(t):
    s,a,d=source(t);return s+999 if t==target else s,a,d
   xp,dp,yp=EpochPairs(ds.epochs,poison,ds.split)[i];torch.testing.assert_close(x,xp,rtol=0,atol=0);torch.testing.assert_close(d,dp,rtol=0,atol=0);assert not torch.equal(y,yp)
   checks.append(dict(year=year,pair=i,target_UTC=target.isoformat(),future_physics_poison_input_exact=True))
  for row in m['frames'][str(year)]:
   with np.load(ROOT/row['path']) as n:assert (n['DEN']>0).all() and np.isfinite(n['ZG']).all() and (np.diff(n['ZG'],axis=0)>0).all()
   raw=native_fields(ROOT/row['path']);decoded=norm.decode(norm.encode(raw));roundtrip=max(roundtrip,float(abs((decoded[DEN_INDICES]-raw[DEN_INDICES])/raw[DEN_INDICES]).max()))
 assert roundtrip<1e-5
 for p in (v3).rglob('*'):
  if p.is_file():frozen[str(p.relative_to(ROOT))]=sha(p)
 for p in (ROOT/'results/fourcastden_den_engineering_v3').rglob('*'):
  if p.is_file():frozen[str(p.relative_to(ROOT))]=sha(p)
 cfg=json.loads((v3/'training_config.json').read_text())
 plan=dict(tag='fourcastden_den_gpu_smoke_v4',label=cfg['label'],training_config=cfg,configuration_changes='none to model/data/loss/optimizer; inherit CUDA assignment, separate output root',train_pairs=list(range(10)),validation_pairs=list(range(48)),display_pair=0,display_native_ilev=24,manifest_SHA256=sha(v3/'dataset_manifest.json'),statistics_SHA256=sha(DATA/'statistics.npz'),expected_forward_calls=62,updates=10,max_tasks=1,no_retry=True,checkpoints=['real_step5.pt','real_step10.pt'],limits=dict(wall_s=900,supervised_wall_s=890,peak_GPU_sample_bytes=20*2**30,allocator_bytes=20*2**30,CPU_RSS_bytes=16*2**30,new_outputs_bytes=2*2**30,free_disk_bytes=20*2**30),estimated_wall_s=120,estimated_GPU_allocated_GiB=4,estimated_outputs_GiB=1.5,estimates_not_measurements=True)
 dump(F/'plan.json',plan);dump(F/'protected_inputs.json',frozen)
 dump(F/'data_audit.json',dict(PASS=True,frames=[73,49],pairs=[72,48],checked_future_poison_pairs=len(checks),checks=checks,train_statistics_unchanged=True,statistics_fitted=False,extraction_performed=False,DEN_channel_indices=DEN_INDICES.tolist(),max_DEN_relative_roundtrip_error=roundtrip,protected_files=len(frozen),wall_s=time.perf_counter()-start))
 dump(F/'resources_initial.json',dict(CUDA_visibility=visibility_snapshot(),GPU_inventory=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,memory.total,memory.free','--format=csv'],text=True),other_GPU_processes=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv'],text=True),free_disk_bytes=shutil.disk_usage(ROOT).free,available_CPU_affinity=len(os.sched_getaffinity(0))))
 print('V4 READONLY DATA AUDIT PASS',len(checks),len(frozen),time.perf_counter()-start)
if __name__=='__main__':main()
