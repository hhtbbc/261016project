"""One short H1 check, at most one six-hour H1 and tight; never replay old groups."""
import sys,json,hashlib,time,resource,argparse
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from astropy.time import Time
from orbit.frames import configure_time_data
from orbit.two_body import make_state_derivative
from orbit.rk45_propagator import propagate
from orbit.spherical_harmonics_gravity import GcrsSphericalHarmonicsForce,SOURCE,SOURCE_SHA,GM,RADIUS_M

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2,allow_nan=False)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');a=ap.parse_args()
 F=ROOT/'experiments/spherical_harmonics_v1';D=ROOT/'data/processed/spherical_harmonics_v1';F.resolve().relative_to(ROOT);D.resolve().relative_to(ROOT)
 if not a.execute:
  assert not (F/'configuration.json').exists()
  assert json.loads((F/'validation.json').read_text())['passed']
  old=json.loads((ROOT/'experiments/high_order_gravity_v1/configuration.json').read_text())
  protected=json.loads((ROOT/'experiments/high_order_gravity_v1/protected.json').read_text())
  for p in (ROOT/'data/processed/high_order_gravity_v1').glob('*.npz'):protected[str(p.relative_to(ROOT))]=sha(p)
  for p in [ROOT/'data/processed/provisional_drag_orbit_v1/D0_states.npz',ROOT/'data/processed/provisional_drag_orbit_v1/D0_tight_states.npz']:protected[str(p.relative_to(ROOT))]=sha(p)
  for p,h in protected.items():assert sha(ROOT/p)==h,p
  with np.load(ROOT/'data/processed/provisional_drag_orbit_v1/D0_states.npz') as z:y=z['states'][0]
  assert hashlib.sha256(y.astype('<f8').tobytes()).hexdigest()==old['initial_sha256_le_float64']
  configure_time_data();assert sha(SOURCE)==SOURCE_SHA
  config={'t0_utc':old['t0_utc'],'initial_state':y.tolist(),'initial_sha256':old['initial_sha256_le_float64'],'base':old['base'],'tight':old['tight'],'source_sha256':SOURCE_SHA,'GM':GM,'radius_m':RADIUS_M,'degree':8,'order':8,'labels':'PROVISIONAL / HINDCAST / NO_DRAG','state_convergence_limit_m':.5,'time_data':old['time_data'],'validation_sha256':sha(F/'validation.json'),'code_sha256':{p:sha(ROOT/p) for p in ['src/orbit/spherical_harmonics_gravity.py','scripts/run_spherical_harmonics_comparison.py']}}
  dump(F/'configuration.json',config);dump(F/'protected.json',protected);dump(F/'preflight.json',{'passed':True,'protected_files':len(protected),'free_disk_GiB':__import__('shutil').disk_usage(ROOT).free/2**30});print('Preflight passed');return
 c=json.loads((F/'configuration.json').read_text());protected=json.loads((F/'protected.json').read_text())
 for p,h in {**protected,**c['code_sha256']}.items():assert sha(ROOT/p)==h
 assert sha(F/'validation.json')==c['validation_sha256']
 dump(F/'launch_once.json',{'allowed':['H1_short','H1','H1_tight'],'started_utc':Time.now().utc.isot});D.mkdir(exist_ok=False)
 configure_time_data();force=GcrsSphericalHarmonicsForce(Time(c['t0_utc'],scale='utc'));rhs=make_state_derivative([force]);y=np.array(c['initial_state']);start=time.perf_counter();out={'runs':{},'labels':c['labels']}
 def guarded(t,y):
  if time.perf_counter()-start>900 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>2*1024**2:raise RuntimeError('Resource limit')
  return rhs(t,y)
 for name,dur,settings in [('H1_short',600,c['base']),('H1',21600,c['base']),('H1_tight',21600,c['tight'])]:
  dump(F/(name+'_launch_once.json'),{'duration_s':dur})
  print('START',name,flush=True);z=propagate(guarded,y[:3],y[3:],(0,dur),np.arange(0,dur+1,60),**settings)
  np.testing.assert_array_equal(z.states[0],y)
  np.savez_compressed(D/(name+'_states.npz'),states=z.states,seconds=z.times_s,internal_times=z.internal_times_s)
  out['runs'][name]=z.statistics;dump(F/(name+'.json'),z.statistics);print('END',name,z.statistics,flush=True)
 with np.load(D/'H1_states.npz') as z:base=z['states']
 with np.load(D/'H1_tight_states.npz') as z:tight=z['states']
 err=np.linalg.norm(base[:,:3]-tight[:,:3],axis=1)
 out.update(convergence_max_m=float(err.max()),convergence_passed=bool(err.max()<c['state_convergence_limit_m']),wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
 for p,h in protected.items():assert sha(ROOT/p)==h,p
 out['protected_unchanged']=True;dump(F/'run_summary.json',out)
 assert out['convergence_passed'];print(json.dumps(out),flush=True)
if __name__=='__main__':main()
