"""Read-only independent delivery/immutability audit; no model inference."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from fourcastden.validation import channel_metrics
F=ROOT/'experiments/fourcastden_two_step_v1'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4194304),b''):h.update(b)
 return h.hexdigest()
def main():
 protected=json.loads((F/'protected.json').read_text())
 for name,value in protected.items():
  p=(ROOT/name).resolve();assert p.is_relative_to(ROOT) and sha(p)==value,name
 old='experiments/20261019_minimal_direct/result.npz'
 prior=json.loads((ROOT/'experiments/tiegcm2023_s7_continuous_v1/protected_files.json').read_text())
 assert sha(ROOT/old)==prior[old]
 runtime=json.loads((F/'runtime.json').read_text())
 result=ROOT/'data/processed/fourcastden_two_step_v1/result.npz'
 assert sha(result)==runtime['file_sha256']
 with np.load(result) as q:
  real=q['real'][0];pred=q['pred'][0]
  np.testing.assert_array_equal(q['input0'][0,:171],real[0,:171])
  np.testing.assert_array_equal(q['input1'][0,:171],q['out0'][0])
  for k in range(2):
   np.testing.assert_array_equal(q[f'input{k}'][0,171:],real[k+1,171:])
   np.testing.assert_array_equal(q[f'out{k}'][0],pred[k+1])
  mu=q['means'][:171].astype(float);sig=q['stds'][:171].astype(float)
  physical=pred.astype(float)*sig+mu;reference=real[:,:171].astype(float)*sig+mu
  assert np.isfinite(physical).all() and (physical[:,142:]>0).all()
  lat=np.load(ROOT/'data/processed/static/lat.npy')
  for h in (1,2):
   rmse,acc,valid=channel_metrics(physical[h],reference[h],q['climatology'],lat)
   np.testing.assert_allclose(rmse,q['author_rmse'][0,h-1],rtol=2e-5,atol=1e-25)
   np.testing.assert_allclose(acc[valid],q['author_acc'][0,h-1][valid],rtol=2e-5,atol=2e-6)
 assert 'Ran 192 tests' in (ROOT/'logs/fourcastden_two_step_tests.log').read_text()
 assert runtime['GPU_phase_wall_s']<300
 paths=set(F.rglob('*'))|set(result.parent.rglob('*'))
 for folder in ['results/figures','results/metrics','logs']:
  paths.update((ROOT/folder).glob('fourcastden_two_step*'))
 files=[p for p in paths if p.is_file() and p.name!='delivery_audit.json']
 assert all(p.resolve().is_relative_to(ROOT) for p in files)
 total=sum(p.stat().st_size for p in files);assert total<500*1024**2
 audit=dict(status='PASS',protected_files_unchanged=len(protected),historical_single_step_sha256=sha(ROOT/old),feedback_exact=True,independent_metrics_pass=True,tests=192,GPU_phase_wall_s=runtime['GPU_phase_wall_s'],new_experiment_bytes=total,budget_bytes=500*1024**2,scope='Experiment arrays, audit metadata, plots, CSVs and logs; code/docs add less than 1 MiB',sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)})
 (F/'delivery_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 print(json.dumps({k:v for k,v in audit.items() if k!='sha256'},indent=2))
if __name__=='__main__':main()
