"""Author converter, train-only streaming statistics and real CPU contract audit."""
import os
from pathlib import Path
import sys,json,time,csv,resource
from datetime import datetime,timedelta,timezone
import numpy as np
from netCDF4 import Dataset,num2date
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts'),str(ROOT/'third_party/FourCastDEN_linux')]
from training.den_engineering import *
from dataset.tiegcm_utils import read_var
from fourcastden.multidate import KEYS,validate_npz,UNITS
from run_tiegcm_mar23_2021_longrun import stream_sha
from training.readonly_interface import array_hash
import torch
def dump(p,j):
 with p.open('x') as out:json.dump(j,out,indent=2,allow_nan=False)
def main():
 start=time.perf_counter();protocol=json.loads((F/'protocol.json').read_text());manifest={}
 for year in [2021,2022]:
  folder=ROOT/protocol['sources'][str(year)];audit=json.loads((folder/'data_audit.json').read_text());assert audit['engineering_PASS']
  directory=DATA/str(year);directory.mkdir(exist_ok=True);first,last=[datetime.fromisoformat(x.replace('Z','+00:00')) for x in protocol['windows'][str(year)]];frames=[]
  for entry in audit['files']:
   if not entry['file'].startswith('secondary'):continue
   path=folder/entry['file'];assert stream_sha(path)==entry['SHA256']
   with Dataset(path) as n:
    times=[datetime(x.year,x.month,x.day,x.hour,x.minute,x.second,tzinfo=timezone.utc) for x in num2date(n['time'][:],n['time'].units)];idx=[i for i,t in enumerate(times) if first<=t<=last]
    if not idx:continue
    for k in KEYS:
     if k in UNITS and k not in ['Kp','f107d','f107a']:assert getattr(n[k],'units',None)==UNITS[k],(k,n[k].units,UNITS[k])
     if k in ['f107d','f107a']:assert n[k].units=='1.e-22 W/m2/Hz'  # exact SFU definition, no numeric rescale
    arrays={k:read_var(n,k,timeIdx=np.asarray(idx)) for k in KEYS}
    for j,i in enumerate(idx):
     values={k:np.asarray(v[j],np.float32).reshape(1) if v.ndim==1 else np.asarray(v[j],np.float32) for k,v in arrays.items()}
     for k in KEYS:
      raw=np.asarray(n[k][i]);raw=raw[:-1] if k in ['TN','UN','VN'] else raw
      if raw.ndim==2:raw=raw[None]
      if raw.ndim==0:raw=raw.reshape(1)
      np.testing.assert_array_equal(values[k],raw.astype(np.float32))
     dest=directory/(times[i].strftime('%Y_%m_%d_%H%M%S')+'.npz')
     if not dest.exists():np.savez_compressed(dest,**values)
     else:
      with np.load(dest,allow_pickle=False) as saved:
       for k in KEYS:np.testing.assert_array_equal(saved[k],values[k])
     validate_npz(dest)
     frames.append(dict(UTC=times[i].isoformat(),path=str(dest.relative_to(ROOT)),SHA256=stream_sha(dest),source=str(path.relative_to(ROOT)),source_SHA256=entry['SHA256'],record=i,bytes=dest.stat().st_size))
  expected=protocol['frames'][str(year)];assert len(frames)==expected and [x['UTC'] for x in frames]==[(first+timedelta(hours=h)).isoformat() for h in range(expected)]
  manifest[str(year)]=frames
  record=dict(label=LABEL,frames=frames,engineering_source='PASS',scientific_training_READY=False)
  if (directory/'manifest.json').exists():assert json.loads((directory/'manifest.json').read_text())==record
  else:dump(directory/'manifest.json',record)
  for p in directory.iterdir():p.chmod(0o444)
 # Only 2021 frame paths can reach statistic fit. Stable parallel Welford batches.
 mean=np.zeros(174);m2=np.zeros(174);maximum=np.zeros(174);count=0
 for frame in manifest['2021']:
  x=native_fields(ROOT/frame['path']).reshape(174,-1);n=x.shape[1];batchmean=x.mean(1);batchm2=((x-batchmean[:,None])**2).sum(1);delta=batchmean-mean
  m2+=batchm2+delta**2*count*n/(count+n);mean+=delta*n/(count+n);count+=n;maximum=np.maximum(maximum,abs(x).max(1))
 std_raw=np.sqrt(m2/count);std,constant=stats_policy(mean,std_raw,maximum)
 # Independent two-pass, different accumulation axis, full training data only.
 stack=np.stack([native_fields(ROOT/x['path']) for x in manifest['2021']]);ind_mean=stack.mean(axis=(0,2,3));ind_std=stack.std(axis=(0,2,3),ddof=0);del stack
 np.testing.assert_allclose(mean,ind_mean,rtol=2e-12,atol=1e-28);np.testing.assert_allclose(std_raw,ind_std,rtol=2e-10,atol=1e-28)
 np.savez(DATA/'statistics.npz',means=mean[:,None,None],stds=std[:,None,None],raw_stds=std_raw,constant=constant)
 dump(F/'statistics.json',dict(source_year=2021,training_frame_count=73,samples_per_channel=count,fit_frame_SHA256=[x['SHA256'] for x in manifest['2021']],mean=mean.tolist(),population_std_raw=std_raw.tolist(),effective_std=std.tolist(),constant_channels=np.flatnonzero(constant).tolist(),statistics_SHA256=stream_sha(DATA/'statistics.npz'),validation_not_used=True,official_static_modified=False))
 norm=load_statistics();max_roundtrip=0.;den_relative=0.
 for frame in manifest['2021']+manifest['2022']:
  raw=native_fields(ROOT/frame['path']);encoded=norm.encode(raw);decoded=norm.decode(encoded);max_roundtrip=max(max_roundtrip,float(abs((decoded-raw)/norm.stds).max()));den_relative=max(den_relative,float(abs((decoded[DEN_INDICES]-raw[DEN_INDICES])/raw[DEN_INDICES]).max()))
 assert max_roundtrip<1e-5 and den_relative<1e-5
 # Exact author frame assembly and future physical-truth poison on all120 pairs.
 checks=[];lat=np.load(ROOT/'data/processed/static/lat.npy')
 for year in [2021,2022]:
  dataset=author_dataset(year);pairset=pairs(year);assert len(pairset)==protocol['pairs'][str(year)]
  for i in range(len(pairset)):
   x,d,y=pairset[i];data,sc,*_=dataset.get_data([i,i+1],inference=True)
   torch.testing.assert_close(x,torch.cat([data[0,:171],data[1,171:]]),rtol=0,atol=0);torch.testing.assert_close(d,sc[1].reshape(1,4),rtol=0,atol=0);torch.testing.assert_close(y,data[1,:171],rtol=0,atol=0)
   source=pairset.source;target=pairset.epochs[i+1]
   def poisoned(t):
    state,aux,scalar=source(t)
    return (state+1234 if t==target else state),aux,scalar
   xp,dp,yp=EpochPairs(pairset.epochs,poisoned,pairset.split)[i]
   torch.testing.assert_close(x,xp,rtol=0,atol=0);torch.testing.assert_close(d,dp,rtol=0,atol=0);assert not torch.equal(y,yp)
   checks.append(dict(year=year,index=i,current_UTC=pairset.epochs[i].isoformat(),target_UTC=target.isoformat(),input_SHA256=array_hash(x),target_SHA256=array_hash(y),future_physics_poison_input_unchanged=True))
 assert len(checks)==120
 architecture=json.loads((ROOT/'configs/training/direct_synthetic_smoke.json').read_text())['architecture']
 cfg=dict(label=LABEL,seed=protocol['seed'],architecture=architecture,optimizer=protocol['optimizer'],scheduler=protocol['scheduler'],gradient_clip_norm=1.,latitude_deg=lat.tolist(),max_train_steps=10,batch_size=1,statistics_SHA256=stream_sha(DATA/'statistics.npz'),supervised_indices=DEN_INDICES.tolist(),validation_pairs=48,display_validation_pair=0,no_official_weights=True,normalization='v3_train2021_native_linear')
 dump(F/'training_config.json',cfg);dump(F/'dataset_manifest.json',dict(label=LABEL,frames=manifest,statistics=stream_sha(DATA/'statistics.npz'),old_122_replaced=False))
 dump(F/'cpu_data_audit.json',dict(PASS=True,frames2021=73,frames2022=49,pairs2021=72,pairs2022=48,real_future_poison_pairs=120,author_assembly_exact_pairs=120,normalization_independent_PASS=True,max_normalized_roundtrip_error=max_roundtrip,max_DEN_relative_roundtrip_error=den_relative,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,checks=checks))
 print('Real v3 extraction/statistics/contracts PASS',len(checks),time.perf_counter()-start)
if __name__=='__main__':main()
