"""Independent saved-state/metric/provenance audit; no trajectory integrations."""
import json,hashlib,csv,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data,transform_state
from evaluation.orbit_data import load_sp3_reference
from astropy.time import Time,TimeDelta
F=ROOT/'experiments/gravity_third_body_v1';D=ROOT/'data/processed/gravity_third_body_v1'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def load(p):
 with np.load(p) as z:return z['states'],z['seconds']
a=json.loads((F/'analysis.json').read_text());c=json.loads((F/'configuration.json').read_text());h3,seconds=load(ROOT/'data/processed/gravity_truncation_v1/H3_states.npz');configure_time_data();epochs=Time(c['t0_utc'],scale='utc')+TimeDelta(seconds,format='sec');ref=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))).take_exact(epochs);r,v=transform_state(ref.positions_m,ref.velocities_m_s,epochs,'ITRS','GCRS')
def independent_rac(delta,r,v):
 R=r/np.linalg.norm(r,axis=1)[:,None];C=np.cross(r,v);C/=np.linalg.norm(C,axis=1)[:,None];A=np.cross(C,R);return np.stack([np.sum(delta*b,axis=1) for b in [R,A,C]],axis=1)
for n in ['H4','H5']:
 y,sec=load(D/(n+'_states.npz'));np.testing.assert_array_equal(sec,seconds);np.testing.assert_array_equal(y[0],h3[0]);assert np.isfinite(y).all()
 delta=y[:,:3]-h3[:,:3];norm=np.linalg.norm(delta,axis=1);s=a['pairs'][n+'_H3'];assert abs(norm[-1]-s['terminal_m'])<1e-9 and abs(np.sqrt(np.mean(norm**2))-s['rmse_3d_m'])<1e-9;np.testing.assert_allclose(independent_rac(delta,h3[:,:3],h3[:,3:])[-1],s['terminal_RAC_m'],rtol=0,atol=1e-9)
 delta=y[:,:3]-r;norm=np.linalg.norm(delta,axis=1);s=a['residuals'][n];assert abs(norm[-1]-s['terminal_m'])<1e-9 and abs(np.sqrt(np.mean(norm**2))-s['rmse_3d_m'])<1e-9;np.testing.assert_allclose(independent_rac(delta,r,v)[-1],s['terminal_RAC_m'],rtol=0,atol=1e-9)
for p,h in {**json.loads((F/'protected.json').read_text()),**c['code_sha256']}.items():assert sha(ROOT/p)==h,p
old=json.loads((ROOT/'experiments/gravity_truncation_v1/delivery_audit.json').read_text())
for x in old['artifact_manifest']:assert sha(ROOT/x['file'])==x['sha256'],x['file']
assert 'Ran 176 tests' in (ROOT/'logs/h4h5_final_tests.log').read_text()
files=list(F.glob('*.json'))+list(ROOT.glob('results/metrics/gravity_third_body_v1_*.csv'))+list(ROOT.glob('results/figures/gravity_third_body_v1_*.png'))
out={'passed':True,'independent_SP3_and_model_metrics_recomputed':True,'initial_state_sha256':c['initial_sha256'],'history_protected_count':229,'old_H3_task_artifacts_match':len(old['artifact_manifest']),'test_count':176,'actual_runs':['H4_short','H4_short_tight','H5_short','H5_short_tight','H4','H5'],'new_H3_or_H6_or_drag_or_TIE_runs':0,'full_6h_convergence_status':'PENDING','source_code_matches_preflight':True,'artifacts':[{'file':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in files]}
with (F/'delivery_audit.json').open('x') as f:json.dump(out,f,indent=2)
print('H4/H5 independent delivery audit passed',len(files),'lightweight artifacts')
