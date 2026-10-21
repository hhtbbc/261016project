"""Streaming audit of actual RHS queries, force law, frozen files and scalar metrics."""
import sys,json,gzip,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from astropy.time import Time,TimeDelta
from orbit.frames import configure_time_data,transform_state
from atmosphere.msis_density_provider import FrozenGfzDrivers
from evaluation.orbit_data import load_sp3_reference
F=ROOT/'experiments/common_density_h6_v1';D=ROOT/'data/processed/common_density_h6_v1'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 c=json.loads((F/'configuration.json').read_text());s=json.loads((F/'run_summary.json').read_text());a=json.loads((F/'analysis.json').read_text());assert s['passed'] and s['new_C0_runs']==0 and s['actual_6h_runs']==6 and s['actual_1h_runs']==6
 assert sha(ROOT/c['common_freeze_file'])==c['common_freeze_sha256']
 for p,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==h,p
 for p,h in c['new_code_sha256'].items():assert sha(ROOT/p)==h,p
 configure_time_data();epoch=Time(c['t0_utc'],scale='utc');drivers=FrozenGfzDrivers(ROOT/'configs/nrlmsis2023_gfz_frozen.json');counts={}
 for name,run in s['runs'].items():
  phases={'rhs':0,'output':0};max_formula_relative=0.
  with gzip.open(D/(name+'_queries.jsonl.gz'),'rt') as f:
   for line in f:
    q=json.loads(line);assert 'failure' not in q;phases[q['phase']]+=1;assert 'FORCE_MODEL_INCOMPLETE' in q['labels'] and 'SYNTHETIC_AERODYNAMIC_PARAMETERS' in q['labels']
    assert q['properties']['mass_kg']==400 and q['properties']['area_m2']==1 and q['properties']['cd']==2.2
    velocity=np.array(q['relative_velocity_itrs_m_s']);ae=np.array(q['acceleration_itrs_m_s2']);ag=np.array(q['acceleration_gcrs_m_s2']);rho=q['rho_kg_m3'] if run['model']=='C1' else q['native_query']['rho_kg_m3'];assert np.isfinite(rho) and rho>0
    expected=-.5*rho*2.2/400*np.linalg.norm(velocity)*velocity;np.testing.assert_allclose(ae,expected,rtol=1e-13,atol=1e-22);np.testing.assert_allclose(np.linalg.norm(ae),np.linalg.norm(ag),rtol=1e-12,atol=1e-22);assert np.dot(ae,velocity)<0
    max_formula_relative=max(max_formula_relative,float(np.linalg.norm(ae-expected)/np.linalg.norm(expected)))
    if run['model']=='C1':
     d=drivers.at(epoch+TimeDelta(q['seconds'],format='sec'));np.testing.assert_array_equal(d.ap,q['drivers']['ap']);assert d.f107_previous_day==q['drivers']['f107_previous_day'] and d.f107a_centered81==q['drivers']['f107a_centered81']
    else:
     assert q['mapping']['status']=='PROVISIONAL' and q['source']=='S7' and q['native_query']['valid'];assert len(q['native_query']['metadata']['columns'])==8
  assert phases['rhs']==run['integration']['nfev'];assert phases=={k:v for k,v in run['force']['phase_calls'].items() if k!='test'};counts[name]=dict(phases=phases,force_formula_max_relative=max_formula_relative)
 times=epoch+TimeDelta(np.arange(361)*60,format='sec');ref=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))).take_exact(times);r,v=transform_state(ref.positions_m,ref.velocities_m_s,times,'ITRS','GCRS');states={};tight={}
 for n in ['C0','C1','C2','C3']:
  folder=ROOT/'data/processed/common_force_validation_v1' if n=='C0' else D;prefix='H6' if n=='C0' else n
  with np.load(folder/(prefix+'_states.npz')) as z:y=z['states'];states[n]=y;np.testing.assert_array_equal(z['seconds'],np.arange(361)*60)
  with np.load(folder/(prefix+'_tight_states.npz')) as z:tight[n]=z['states']
  np.testing.assert_array_equal(y[0],c['initial_state']);assert np.isfinite(y).all();d=y[:,:3]-r;norm=np.sqrt(np.einsum('ij,ij->i',d,d));R=r/np.linalg.norm(r,axis=1)[:,None];C=np.cross(r,v);C/=np.linalg.norm(C,axis=1)[:,None];A=np.cross(C,R);rac=np.column_stack([np.einsum('ij,ij->i',d,b) for b in [R,A,C]])
  np.testing.assert_allclose(norm[-1],a['residuals'][n]['terminal_m'],rtol=0,atol=1e-9);np.testing.assert_allclose(np.sqrt(np.mean(norm**2)),a['residuals'][n]['rmse_3d_m'],rtol=0,atol=1e-9);np.testing.assert_allclose(rac[-1],a['residuals'][n]['terminal_RAC_m'],rtol=0,atol=1e-9)
  assert np.linalg.norm(y[:,:3]-tight[n][:,:3],axis=1).max()<.5
 for x,y in [('C1','C0'),('C2','C0'),('C3','C0'),('C1','C2'),('C1','C3'),('C2','C3')]:
  d=states[x]-states[y];norm=np.linalg.norm(d[:,:3],axis=1);np.testing.assert_allclose(norm[-1],a['pairs'][x+'_'+y]['terminal_m'],rtol=0,atol=1e-9);assert np.linalg.norm((d-(tight[x]-tight[y]))[:,:3],axis=1).max()<.1
 paths=[p for p in F.glob('*') if p.is_file()]+list(D.glob('*'))+list((ROOT/'results/metrics').glob('common_density_h6_v1*'))+list((ROOT/'results/figures').glob('common_density_h6_v1*'))
 result=dict(passed=True,streaming_query_audits=counts,protected_unchanged=True,no_C0_propagation=True,independent_residual_RAC_and_convergence=True,artifacts=[dict(file=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in paths])
 with (F/'independent_audit.json').open('x') as f:json.dump(result,f,indent=2)
 print('Independent audit passed:',len(counts),'runs;',sum(sum(x['phases'].values()) for x in counts.values()),'streamed queries;',len(paths),'artifacts')
if __name__=='__main__':main()
