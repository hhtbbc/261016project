"""Convert only audited 73 warm-window records; CPU input checks, never training."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
import sys,json,importlib.util,types
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
import numpy as np
from netCDF4 import Dataset,num2date
import torch
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R/'scripts'),str(R/'third_party/FourCastDEN_linux')]
from fourcastden.multidate import validate_npz,KEYS
from training.pipeline import OfficialFrameSource
from training.readonly_interface import inspect_pair,array_hash
from audit_fourcastden_real_data_interface import capture_official
from dataset.tiegcm_utils import read_var
from dataset.dataset_tiegcm import TGCMDataset
from utils.YParams import YParams
s=importlib.util.spec_from_file_location('longrun',R/'scripts/run_tiegcm_mar23_2021_longrun.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
F=R/'experiments/tiegcm_training_mar23_v2_2021_longrun';D=R/'data/processed/training_window_mar23_v2/candidates_2021'
LABELS=['INDEPENDENT_TIEGCM_DATA_GENERATION','HINDCAST','SPINUP_SUFFICIENCY_UNVERIFIED','TRAINING_CANDIDATE_ONLY']
def main():
 a=json.loads((F/'data_audit.json').read_text());assert a['engineering_PASS'] and a['candidate_records']==73
 D.mkdir(exist_ok=False);manifest=[];start=datetime(2021,3,23);end=datetime(2021,3,26)
 for entry in a['files']:
  if not entry['file'].startswith('secondary'):continue
  p=F/entry['file'];assert m.s.sha(p)==entry['SHA256']
  with Dataset(p) as n:
   ts=[datetime(t.year,t.month,t.day,t.hour,t.minute,t.second) for t in num2date(n['time'][:],n['time'].units)]
   indices=[i for i,t in enumerate(ts) if start<=t<=end]
   if not indices:continue
   # Exactly the unmodified author converter: native units, lev top removal, surface singleton.
   arrays={k:read_var(n,k,timeIdx=np.asarray(indices)) for k in KEYS}
   for j,i in enumerate(indices):
    t=ts[i];values={k:np.asarray(v[j],dtype=np.float32).reshape(1) if v.ndim==1 else np.asarray(v[j],dtype=np.float32) for k,v in arrays.items()}
    target=D/(t.strftime('%Y_%m_%d_%H%M%S')+'.npz');assert not target.exists()
    np.savez_compressed(target,**values);stats=validate_npz(target)
    # Independent direct NetCDF indexing verifies every preserved element and unit scaling (none).
    for k in KEYS:
     direct=np.asarray(n[k][i]);direct=direct[:-1] if k in ['TN','UN','VN'] else direct
     if direct.ndim==2:direct=direct[None]
     if direct.ndim==0:direct=direct.reshape(1)
     np.testing.assert_array_equal(values[k],direct.astype(np.float32))
    manifest.append({'UTC':t.replace(tzinfo=timezone.utc).isoformat(),'file':str(target.relative_to(R)),'SHA256':m.s.sha(target),'bytes':target.stat().st_size,'source':entry['file'],'source_record':i,'labels':LABELS,'fourteen_keys_PASS':True,'direct_NetCDF_float32_exact':True})
 assert len(manifest)==73
 assert [x['UTC'] for x in manifest]==[(start+timedelta(hours=i)).replace(tzinfo=timezone.utc).isoformat() for i in range(73)]
 # Store coordinates separately to preserve EXACT fourteen-key author NPZ schema.
 with Dataset(F/'secondary_001.nc') as n:
  for k in ['lat','lon','lev','ilev']:np.save(D/f'{k}.npy',np.asarray(n[k][:]));np.testing.assert_array_equal(n[k][:],np.load(R/f'data/processed/static/{k}.npy'))
 cfg=YParams(str(R/'experiments/fourcastden_two_step_v1/config.yaml'),'afno_inference');cfg['device']='cpu';cfg['test_data_path']=str(D);cfg['n_prediction']=1
 ds=TGCMDataset(cfg,str(D),train=False);assert ds.epochs==[start+timedelta(hours=i) for i in range(73)]
 source=OfficialFrameSource(ds);pairs=[];poison=[];scalar_min=np.full(3,np.inf);scalar_max=np.full(3,-np.inf)
 def forbidden(*a,**k):raise AssertionError('Model evaluation or training forbidden')
 with patch('torch.Tensor.backward',forbidden),patch('torch.autograd.backward',forbidden),patch('torch.nn.Module.__call__',forbidden),patch('training.pipeline.DirectTrainer.__init__',forbidden),torch.inference_mode():
  for i in range(72):
   data,sw,*_=ds.get_data([i,i+1],inference=True)
   scalar_min=np.minimum(scalar_min,sw[:,:3].numpy().min(axis=0));scalar_max=np.maximum(scalar_max,sw[:,:3].numpy().max(axis=0))
   # Official inference is intercepted before any network call.
   x,scalar=capture_official(ds,ds.means,ds.stds,i)
   pairs.append(inspect_pair(source,ds.epochs[i].replace(tzinfo=timezone.utc),ds.epochs[i+1].replace(tzinfo=timezone.utc),x,scalar,data[1:2,:171],current_split='2021_candidate_read_only',target_split='2021_candidate_read_only'))
   # Change future physical state ONLY; auxiliary inputs remain unchanged.
   class Poisoned:
    def __call__(self,epoch):
     state,aux,sw0=source(epoch)
     if epoch==ds.epochs[i+1].replace(tzinfo=timezone.utc):state=state+12345
     return state,aux,sw0
   first,_,_=source(ds.epochs[i].replace(tzinfo=timezone.utc));_,aux,sw0=Poisoned()(ds.epochs[i+1].replace(tzinfo=timezone.utc))
   np.testing.assert_array_equal(torch.cat([first,aux])[None].numpy(),x.numpy());poison.append(True)
  assert all(poison)
 stats={str(p.relative_to(R)):m.s.sha(p) for p in (R/'data/processed/static').glob('*') if p.is_file()}
 output=dict(labels=LABELS,frames=manifest,count=73,continuous_pairs=72,first_three_scalar_min=scalar_min.tolist(),first_three_scalar_max=scalar_max.tolist(),pairs=pairs,future_target_poison_checks=72,official_input_exact=True,shapes=dict(input=[1,177,36,72],scalar=[1,1,4],target=[1,171,36,72]),statistic_source='Existing official ordinary static; READ-ONLY compatibility only, not independent training statistics',static_SHA256=stats,training_statistics_fitted=False,model_instantiated=False,model_forwards=0,backward=0,optimizer_steps=0,training_approved=False,grid_sidecars={k:m.s.sha(D/f'{k}.npy') for k in ['lat','lon','lev','ilev']})
 (F/'candidate_audit.json').write_text(json.dumps(output,indent=2,allow_nan=False))
 with (D/'manifest.json').open('x') as f:json.dump({'labels':LABELS,'training_approved':False,'frames':manifest,'source_audit':str((F/'candidate_audit.json').relative_to(R)),'normalization_statistics_fitted':False},f,indent=2)
 for p in D.iterdir():p.chmod(0o444)
 assert sum(p.stat().st_size for p in D.iterdir())+json.loads((F/'run_status.json').read_text())['total_generated_bytes']<5*1024**3
 print('CANDIDATE AND READ-ONLY INTERFACE PASS',len(manifest))
if __name__=='__main__':main()
