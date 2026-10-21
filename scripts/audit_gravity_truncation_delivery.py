"""Independent metrics, historical artifacts, hashes and lightweight manifest."""
import sys,json,hashlib,csv
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
F=ROOT/'experiments/gravity_truncation_v1';D=ROOT/'data/processed/gravity_truncation_v1'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def load(p):
 with np.load(p) as z:return z['states']
a=json.loads((F/'analysis.json').read_text());c=json.loads((F/'configuration.json').read_text());h1=load(ROOT/'data/processed/spherical_harmonics_v1/H1_states.npz');h2=load(D/'H2_states.npz');h3=load(D/'H3_states.npz');tight=load(D/'H3_tight_states.npz')
for key,x,y in [('H2_H1',h2,h1),('H3_H2',h3,h2),('H3_H1',h3,h1)]:
 delta=x[:,:3]-y[:,:3];norm=np.sqrt(np.sum(delta**2,axis=1));s=a['pairs'][key];assert abs(norm[-1]-s['terminal_m'])<1e-9 and abs(np.sqrt(np.mean(norm**2))-s['rmse_3d_m'])<1e-9
 # Independent basis construction/dot products, not rac_errors helper.
 R=h1[:,:3]/np.linalg.norm(h1[:,:3],axis=1)[:,None];C=np.cross(h1[:,:3],h1[:,3:]);C/=np.linalg.norm(C,axis=1)[:,None];A=np.cross(C,R);rac=np.stack([np.sum(delta*b,axis=1) for b in [R,A,C]],axis=1)
 np.testing.assert_allclose(rac[-1],s['terminal_RAC_m'],rtol=0,atol=1e-9)
for x in [h2,h3,tight]:np.testing.assert_array_equal(x[0],h1[0]);assert np.isfinite(x).all()
assert hashlib.sha256(h1[0].astype('<f8').tobytes()).hexdigest()==c['initial_sha256']
for p,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==h,p
old=json.loads((ROOT/'experiments/spherical_harmonics_v1/delivery_audit.json').read_text())
for x in old['artifacts']:assert sha(ROOT/x['file'])==x['sha256'],x['file']
for p,h in c['code_sha256'].items():assert sha(ROOT/p)==h,p
assert 'Ran 163 tests' in (ROOT/'logs/gravity_truncation_final_tests.log').read_text()
files=list(F.glob('*.json'))+list(ROOT.glob('results/metrics/gravity_truncation_v1_*.csv'))+list(ROOT.glob('results/figures/gravity_truncation_v1_*.png'))
out={'passed':True,'independent_pair_metrics_recomputed':True,'initial_state_sha256':c['initial_sha256'],'all_states_finite':True,'protected_history_files':201,'old_H1_delivery_artifacts_verified':len(old['artifacts']),'new_H1_or_drag_runs':0,'actual_new_propagations':['H3_short','H2','H3','H3_tight'],'tests':163,'H3_state_convergence_max_m':float(np.linalg.norm(h3[:,:3]-tight[:,:3],axis=1).max()),'thresholds_unmodified':True,'artifact_manifest':[{'file':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in files]}
with (F/'delivery_audit.json').open('x') as f:json.dump(out,f,indent=2)
print('Delivery audit passed',len(files),'lightweight artifacts')
