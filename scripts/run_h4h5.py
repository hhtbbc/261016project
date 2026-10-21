"""Four bounded short numerical checks; H4/H5 full six-hour base each ONCE."""
import sys,json,hashlib,time,resource,argparse,shutil
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from astropy.time import Time
from orbit.frames import configure_time_data
from orbit.rk45_propagator import propagate
from orbit.two_body import make_state_derivative
from orbit.spherical_harmonics_gravity import GcrsSphericalHarmonicsForce
from orbit.gravity_truncation import ExtendedEarthGravity
from orbit.gravity_degree40 import Degree40EarthGravity
from orbit.third_body_gravity import ThirdBodyGravity
F=ROOT/'experiments/gravity_third_body_v1';D=ROOT/'data/processed/gravity_third_body_v1'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def dump(p,j):
 with p.open('x') as f:json.dump(j,f,indent=2,allow_nan=False)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');args=ap.parse_args()
 for p in [F,D]:p.resolve().relative_to(ROOT)
 if not args.execute:
  validation=json.loads((F/'validation.json').read_text());assert validation['passed'];tests=(ROOT/'logs/h4h5_all_tests.log').read_text();assert 'Ran 176 tests' in tests and tests.rstrip().endswith('OK')
  c=json.loads((ROOT/'experiments/gravity_truncation_v1/configuration.json').read_text());protected=json.loads((ROOT/'experiments/gravity_truncation_v1/protected.json').read_text())
  for folder,glob in [('experiments/gravity_truncation_v1','*.json'),('data/processed/gravity_truncation_v1','*.npz')]:
   for p in (ROOT/folder).glob(glob):protected[str(p.relative_to(ROOT))]=sha(p)
  for p in ['src/orbit/gravity_truncation.py','src/orbit/force_budget_estimates.py']:protected[p]=sha(ROOT/p)
  for p,h in protected.items():assert sha(ROOT/p)==h,p
  with np.load(ROOT/'data/processed/gravity_truncation_v1/H3_states.npz') as z:assert hashlib.sha256(z['states'][0].astype('<f8').tobytes()).hexdigest()==c['initial_sha256']
  c.update(new_allowed_runs=['H4_short','H4_short_tight','H5_short','H5_short_tight','H4','H5'],new_H3_runs=0,H6_runs=0,wall_limit_s=1800,RSS_limit_GiB=2,short_convergence_limit_m=.02,full_6h_convergence_status='PENDING: no H4/H5 full tight authorized by this runner',source40=json.loads((ROOT/'configs/egm2008_degree40_source.json').read_text()),third_body=validation['third_body'],code_sha256={p:sha(ROOT/p) for p in ['src/orbit/gravity_degree40.py','src/orbit/third_body_gravity.py','scripts/run_h4h5.py','src/orbit/gravity_truncation.py','src/orbit/spherical_harmonics_gravity.py']},validation_sha256=sha(F/'validation.json'))
  configure_time_data();dump(F/'configuration.json',c);dump(F/'protected.json',protected);dump(F/'preflight.json',{'passed':True,'protected_files':len(protected),'all_tests':176,'free_disk_GiB':shutil.disk_usage(ROOT).free/2**30});print('H4/H5 preflight passed');return
 c=json.loads((F/'configuration.json').read_text());protected=json.loads((F/'protected.json').read_text())
 for p,h in {**protected,**c['code_sha256']}.items():assert sha(ROOT/p)==h,p
 assert sha(F/'validation.json')==c['validation_sha256'];dump(F/'launch_once.json',{'started_utc':Time.now().utc.isot,'allowed':c['new_allowed_runs']});D.mkdir(exist_ok=False);configure_time_data();epoch=Time(c['t0_utc'],scale='utc');y=np.array(c['initial_state']);out={'runs':{},'new_H3_runs':0,'H6_runs':0,'full_6h_convergence_status':c['full_6h_convergence_status'],'labels':'PROVISIONAL / HINDCAST / NO_DRAG; H5 PROVISIONAL_EPHEMERIS'};states={};start=time.perf_counter()
 def guard():
  if time.perf_counter()-start>1800 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>2*1024**2 or shutil.disk_usage(ROOT).free<20*2**30:raise RuntimeError('Resource budget limit')
 def run(name,dur,tight=False):
  guard();dump(F/(name+'_launch_once.json'),{'duration_s':dur,'tight':tight});is5=name.startswith('H5');earth=GcrsSphericalHarmonicsForce(epoch,ExtendedEarthGravity(20) if is5 else Degree40EarthGravity(40));forces=[earth]
  if is5:forces.append(ThirdBodyGravity(epoch,21600))
  rhs=make_state_derivative(forces)
  def guarded(t,y):guard();return rhs(t,y)
  print('START',name,flush=True);z=propagate(guarded,y[:3],y[3:],(0,dur),np.arange(0,dur+1,60),**c['tight' if tight else 'base']);np.testing.assert_array_equal(y,z.states[0]);assert np.isfinite(z.states).all();radius=np.linalg.norm(z.states[:,:3],axis=1);assert radius.min()>6.3e6 and radius.max()<8e6
  states[name]=z.states;out['runs'][name]=z.statistics;dump(F/(name+'.json'),z.statistics);np.savez_compressed(D/(name+'_states.npz'),states=z.states,seconds=z.times_s,internal_times=z.internal_times_s);print('END',name,z.statistics,flush=True)
 try:
  for name in ['H4','H5']:
   run(name+'_short',600);run(name+'_short_tight',600,True);diff=np.linalg.norm(states[name+'_short'][:,:3]-states[name+'_short_tight'][:,:3],axis=1);gate={'model':name,'state_max_m':float(diff.max()),'threshold_m':.02,'passed':bool(diff.max()<.02)};dump(F/(name+'_short_gate.json'),gate)
   if not gate['passed']:raise RuntimeError('Short convergence gate failed; no main propagation')
  estimate=sum(out['runs'][n+'_short']['elapsed_s']/out['runs'][n+'_short']['nfev']*4346 for n in ['H4','H5'])*1.5
  budget={'predicted_remaining_s':estimate,'remaining_budget_s':1800-(time.perf_counter()-start),'passed':estimate<1800-(time.perf_counter()-start),'safety_factor':1.5};dump(F/'runtime_budget_gate.json',budget)
  if not budget['passed']:raise RuntimeError('Predicted runtime too high; stop before full runs')
  for name in ['H4','H5']:run(name,21600)
  for p,h in protected.items():assert sha(ROOT/p)==h,p
  out.update(protected_unchanged=True,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,actual_new_propagations=6,no_new_drag_or_TIE_runs=True)
  dump(F/'run_summary.json',out);print(json.dumps(out),flush=True)
 except Exception as e:dump(F/'failure.json',{'reason':str(e),'completed':list(out['runs']),'wall_s':time.perf_counter()-start});raise
if __name__=='__main__':main()
