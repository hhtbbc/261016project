"""One short check, H2/H3 six-hour runs and H3 tight only; guarded once."""
import sys,json,hashlib,time,resource,argparse,shutil
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from astropy.time import Time
from orbit.frames import configure_time_data
from orbit.two_body import make_state_derivative
from orbit.rk45_propagator import propagate
from orbit.spherical_harmonics_gravity import GcrsSphericalHarmonicsForce
from orbit.gravity_truncation import ExtendedEarthGravity
F=ROOT/'experiments/gravity_truncation_v1';D=ROOT/'data/processed/gravity_truncation_v1'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def dump(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2,allow_nan=False)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');args=ap.parse_args()
 for p in [F,D]:p.resolve().relative_to(ROOT)
 if not args.execute:
  v=json.loads((F/'validation.json').read_text());assert v['passed'];test=(ROOT/'logs/gravity_truncation_all_tests.log').read_text();assert 'Ran 159 tests' in test and test.rstrip().endswith('OK')
  c=json.loads((ROOT/'experiments/spherical_harmonics_v1/configuration.json').read_text());protected=json.loads((ROOT/'experiments/spherical_harmonics_v1/protected.json').read_text())
  for folder,glob in [('experiments/spherical_harmonics_v1','*.json'),('data/processed/spherical_harmonics_v1','*.npz')]:
   for p in (ROOT/folder).glob(glob):protected[str(p.relative_to(ROOT))]=sha(p)
  protected['src/orbit/spherical_harmonics_gravity.py']=sha(ROOT/'src/orbit/spherical_harmonics_gravity.py')
  for p,h in protected.items():assert sha(ROOT/p)==h,p
  with np.load(ROOT/'data/processed/spherical_harmonics_v1/H1_states.npz') as z:assert hashlib.sha256(z['states'][0].astype('<f8').tobytes()).hexdigest()==c['initial_sha256']
  c.update(model='EGM2008 static full degree/order truncation',degrees=[8,12,20],new_allowed_runs=['H3_short','H2','H3','H3_tight'],wall_limit_s=1800,RSS_limit_GiB=2,endpoint_truncation_goal_m=5.,whole_path_truncation_goal_m=5.,source20=json.loads((ROOT/'configs/egm2008_degree20_source.json').read_text()),code_sha256={n:sha(ROOT/n) for n in ['src/orbit/gravity_truncation.py','src/orbit/spherical_harmonics_gravity.py','scripts/run_gravity_truncation.py']},validation_sha256=sha(F/'validation.json'))
  configure_time_data();dump(F/'configuration.json',c);dump(F/'protected.json',protected);dump(F/'preflight.json',{'passed':True,'protected_files':len(protected),'free_disk_GiB':shutil.disk_usage(ROOT).free/2**30,'all_tests':159});print('Preflight passed');return
 c=json.loads((F/'configuration.json').read_text());protected=json.loads((F/'protected.json').read_text())
 for n,h in {**protected,**c['code_sha256']}.items():assert sha(ROOT/n)==h,n
 assert sha(F/'validation.json')==c['validation_sha256'];assert shutil.disk_usage(ROOT).free>20*2**30
 dump(F/'launch_once.json',{'started_utc':Time.now().utc.isot,'allowed':c['new_allowed_runs']});D.mkdir(exist_ok=False);configure_time_data();epoch=Time(c['t0_utc'],scale='utc');y=np.asarray(c['initial_state']);out={'labels':c['labels'],'runs':{},'new_H1_runs':0,'new_drag_runs':0};start=time.perf_counter()
 def guard():
  if time.perf_counter()-start>1800 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>2*1024**2 or shutil.disk_usage(ROOT).free<20*2**30:raise RuntimeError('Resource limit')
 try:
  for name,d,dur,setting in [('H3_short',20,600,'base'),('H2',12,21600,'base'),('H3',20,21600,'base'),('H3_tight',20,21600,'tight')]:
   guard();dump(F/(name+'_launch_once.json'),{'degree':d,'duration_s':dur,'settings':setting});force=GcrsSphericalHarmonicsForce(epoch,ExtendedEarthGravity(d));rhs=make_state_derivative([force])
   def guarded(t,y):guard();return rhs(t,y)
   print('START',name,flush=True);z=propagate(guarded,y[:3],y[3:],(0,dur),np.arange(0,dur+1,60),**c[setting]);np.testing.assert_array_equal(z.states[0],y)
   assert np.isfinite(z.states).all();radius=np.linalg.norm(z.states[:,:3],axis=1);assert np.all((radius>6.3e6)&(radius<8e6))
   np.savez_compressed(D/(name+'_states.npz'),states=z.states,seconds=z.times_s,internal_times=z.internal_times_s);out['runs'][name]=z.statistics;dump(F/(name+'.json'),z.statistics);print('END',name,z.statistics,flush=True)
   if name=='H3_short':
    # Tight has twice as many calls; allow 50% overhead beyond measured per-RHS.
    estimate=z.statistics['elapsed_s']/z.statistics['nfev']*(4346+4346+8666)*1.5
    budget={'remaining_estimate_s':estimate,'remaining_budget_s':1800-(time.perf_counter()-start),'passed':estimate<1800-(time.perf_counter()-start),'basis':'20x20 short measured time/RHS, full matrix calls from historical RK45; 1.5 safety factor'};dump(F/'runtime_budget_gate.json',budget)
    if not budget['passed']:raise RuntimeError('Predicted runtime exceeds remaining budget; no six-hour starts')
  with np.load(D/'H3_states.npz') as z:base=z['states']
  with np.load(D/'H3_tight_states.npz') as z:tight=z['states']
  error=np.linalg.norm(base[:,:3]-tight[:,:3],axis=1);out.update(convergence_max_m=float(error.max()),convergence_passed=bool(error.max()<.5),wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
  for n,h in protected.items():assert sha(ROOT/n)==h,n
  out['protected_unchanged']=True;dump(F/'run_summary.json',out);assert out['convergence_passed'];print(json.dumps(out),flush=True)
 except Exception as e:
  dump(F/'failure.json',{'reason':str(e),'completed_runs':out['runs'],'wall_s':time.perf_counter()-start});raise
if __name__=='__main__':main()
