"""Independent scalar/RAC recomputation and immutable evidence manifest."""
import json,hashlib,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from astropy.time import Time,TimeDelta
from orbit.frames import configure_time_data,transform_state
from evaluation.orbit_data import load_sp3_reference
F=ROOT/'experiments/common_force_validation_v1';D=ROOT/'data/processed/common_force_validation_v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 c=json.loads((F/'effective_configuration.json').read_text());a=json.loads((F/'analysis.json').read_text());summary=json.loads((F/'run_summary.json').read_text());assert summary['passed'] and summary['actual_six_hour_runs']==4 and summary['actual_short_runs']==2
 for p,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==h,p
 configure_time_data();t=Time(c['t0_utc'],scale='utc')+TimeDelta(np.arange(361)*60,format='sec');ref=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))).take_exact(t);r,v=transform_state(ref.positions_m,ref.velocities_m_s,t,'ITRS','GCRS');checks={};states={};tight={}
 for n,folder in [('H3','gravity_truncation_v1'),('H4','gravity_third_body_v1'),('H5','gravity_third_body_v1'),('H6','common_force_validation_v1')]:
  with np.load(ROOT/f'data/processed/{folder}/{n}_states.npz') as z:
   y=z['states'];np.testing.assert_array_equal(z['seconds'],np.arange(361)*60)
  assert np.isfinite(y).all();rnorm=np.linalg.norm(y[:,:3],axis=1);vnorm=np.linalg.norm(y[:,3:],axis=1);assert np.all((rnorm>6.3e6)&(rnorm<8e6)) and np.all((vnorm>6000)&(vnorm<9000))
  states[n]=y.copy();tf=ROOT/'data/processed/gravity_truncation_v1' if n=='H3' else D
  with np.load(tf/(n+'_tight_states.npz')) as z:tight[n]=z['states'].copy()
  delta=states[n]-tight[n];mx=np.sqrt(np.max(np.einsum('ij,ij->i',delta[:,:3],delta[:,:3])));assert mx<.5
  np.testing.assert_allclose(mx,a['convergence'][n]['max_position_m'],rtol=0,atol=1e-9)
  np.testing.assert_array_equal(y[0],c['initial_state']);d=y[:,:3]-r;norm=np.sqrt(np.einsum('ij,ij->i',d,d));R=r/np.sqrt(np.einsum('ij,ij->i',r,r))[:,None];C=np.cross(r,v);C/=np.sqrt(np.einsum('ij,ij->i',C,C))[:,None];A=np.cross(C,R);rac=np.column_stack([np.einsum('ij,ij->i',d,b) for b in (R,A,C)]);expected=a['residuals'][n]
  np.testing.assert_allclose(norm[-1],expected['terminal_m'],rtol=0,atol=1e-9);np.testing.assert_allclose(np.sqrt(np.mean(norm**2)),expected['rmse_3d_m'],rtol=0,atol=1e-9);np.testing.assert_allclose(rac[-1],expected['terminal_RAC_m'],rtol=0,atol=1e-9);checks[n]=True
 for x,y in [('H4','H3'),('H5','H3'),('H6','H3'),('H6','H4'),('H6','H5')]:
  delta=(states[x]-states[y])-(tight[x]-tight[y]);mx=float(np.sqrt(np.max(np.einsum('ij,ij->i',delta[:,:3],delta[:,:3]))));assert mx<.1
  np.testing.assert_allclose(mx,a['paired_convergence'][x+'_'+y]['max_position_m'],rtol=0,atol=1e-9)
 assert all(g['passed'] for g in summary['gates'].values());assert 'Ran 181 tests' in (ROOT/'logs/common_force_tests_pass.log').read_text()
 for p in D.glob('*.npz'):
  with np.load(p) as z:assert np.isfinite(z['states']).all()
 paths=[p for p in F.glob('*') if p.is_file()]+list(D.glob('*.npz'))+list((ROOT/'results/metrics').glob('common_force_v1*'))+list((ROOT/'results/figures').glob('common_force_v1*'))
 paths += [ROOT/p for p in ['configs/provisional_common_force_model.json','src/orbit/common_force_model.py','tests/test_common_force_model.py','docs/H6_VALIDATION_DESIGN.md','docs/PROVISIONAL_DENSITY_COMPARISON_PLAN.md','reports/H6_FORCE_MODEL_VALIDATION.md','reports/H6_ORBIT_COMPARISON.md','STATUS.md','WORKLOG.md','docs/COMMON_FORCE_MODEL_DECISION.md','logs/common_force_runs.log','logs/common_force_tests_pass.log']]
 paths += list((ROOT/'scripts').glob('*common_force*.py'))
 out=dict(passed=True,independent_norm_and_RAC=checks,protected_unchanged=True,artifacts=[dict(file=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in paths])
 with (F/'delivery_audit.json').open('x') as f:json.dump(out,f,indent=2)
 print('Independent scalar/RAC, finite states, gates and historical SHA audit passed:',len(paths),'artifacts')
if __name__=='__main__':main()
