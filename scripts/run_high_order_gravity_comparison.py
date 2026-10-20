"""At most G1, G2 and G2-tight; G0 is read from the frozen D0 experiment."""
import argparse,csv,hashlib,json,resource,sys,time,traceback
from pathlib import Path
import numpy as np
from astropy.time import Time,TimeDelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data,transform_state
from orbit.two_body import central_gravity,make_state_derivative
from orbit.j2 import EarthFigureAxis,j2_acceleration
from orbit.higher_order_gravity import HigherOrderZonalForce,j3_acceleration,j4_acceleration
from orbit.rk45_propagator import propagate
from evaluation.orbit_data import load_sp3_reference
LABELS=('PROVISIONAL','HINDCAST','NO_DRAG')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-tag',default='high_order_gravity_v1');p.add_argument('--execute',action='store_true');args=p.parse_args()
 if not args.run_tag.replace('_','').isalnum():raise ValueError('Safe tag required')
 F=ROOT/'experiments'/args.run_tag;L=ROOT/'data/processed'/args.run_tag
 for q in [F,L]:q.resolve().relative_to(ROOT)
 if not args.execute:
  F.mkdir(exist_ok=False);protected=json.loads((ROOT/'experiments/msis_drag_orbit_v1/protected.json').read_text())
  for x in json.loads((ROOT/'experiments/msis_drag_orbit_v1/delivery_audit.json').read_text())['artifacts']:
   assert sha(ROOT/x['file'])==x['sha256'];protected[x['file']]=x['sha256']
  for x in (ROOT/'experiments/msis_drag_orbit_v1').glob('*.json'):protected[str(x.relative_to(ROOT))]=sha(x)
  for x in json.loads((ROOT/'logs/swarm_sp3_inspection.json').read_text())['files']:
   assert sha(ROOT/x['file'])==x['sha256'];protected[x['file']]=x['sha256']
  for name,digest in protected.items():assert sha(ROOT/name)==digest,name
  independent=json.loads((ROOT/'logs/high_order_gravity_independent_validation.json').read_text());assert independent['passed']
  assert 'Ran 142 tests' in (ROOT/'logs/high_order_gravity_all_tests.log').read_text()
  _,tm=configure_time_data();old=json.loads((ROOT/'experiments/provisional_drag_orbit_v1/configuration.json').read_text());t0=Time(old['t0_utc'],scale='utc')
  ref=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))).take_exact(Time([t0]))
  r,v=transform_state(ref.positions_m,ref.velocities_m_s,Time([t0]),'ITRS','GCRS');initial=np.r_[r[0],v[0]]
  with np.load(ROOT/'data/processed/provisional_drag_orbit_v1/D0_states.npz') as z:np.testing.assert_array_equal(z['states'][0],initial)
  assert hashlib.sha256(np.asarray(initial,dtype='<f8').tobytes()).hexdigest()==json.loads((ROOT/'experiments/msis_drag_orbit_v1/configuration.json').read_text())['initial_state_sha256_le_float64']
  c={'labels':LABELS,'t0_utc':old['t0_utc'],'duration_s':21600,'output_step_s':60,'base':old['base'],'tight':old['tight'],'thresholds':old['thresholds'],'initial_state_gcrs':initial.tolist(),'initial_sha256_le_float64':hashlib.sha256(np.asarray(initial,dtype='<f8').tobytes()).hexdigest(),'time_data':tm,'higher_order_parameters':json.loads((ROOT/'configs/higher_order_gravity.json').read_text()),'source_code_sha256':{name:sha(ROOT/name) for name in ['scripts/run_high_order_gravity_comparison.py','src/orbit/higher_order_gravity.py','configs/higher_order_gravity.json','tests/test_higher_order_gravity.py']},'validation_sha256':sha(ROOT/'logs/high_order_gravity_independent_validation.json'),'wall_limit_s':300,'RSS_limit_GiB':2,'new_allowed_runs':['G1','G2','G2_tight'],'G0_reference':'data/processed/provisional_drag_orbit_v1/D0_states.npz','no_drag':True}
  dump(F/'configuration.json',c);dump(F/'protected.json',protected);dump(F/'preflight.json',{'passed':True,'protected_count':len(protected),'independent_validation_passed':True,'all_tests':142,'free_disk_GiB':__import__('shutil').disk_usage(ROOT).free/2**30});print('Preflight passed',len(protected),'protected files');return
 c=json.loads((F/'configuration.json').read_text());protected=json.loads((F/'protected.json').read_text())
 for p,h in protected.items():assert sha(ROOT/p)==h
 for p,h in c['source_code_sha256'].items():assert sha(ROOT/p)==h
 assert sha(ROOT/'logs/high_order_gravity_independent_validation.json')==c['validation_sha256']
 with (F/'launch_once.json').open('x') as f:json.dump({'maximum_runs':3,'labels':LABELS},f)
 L.mkdir(exist_ok=False);configure_time_data();t0=Time(c['t0_utc'],scale='utc');seconds=np.arange(0,21601,60.);times=t0+TimeDelta(seconds,format='sec');axis=EarthFigureAxis(t0,21600,cadence_s=60);initial=np.asarray(c['initial_state_gcrs']);start=time.perf_counter();out={'labels':LABELS,'runs':{},'new_G0_runs':0,'new_drag_runs':0,'new_TIE_runs':0}
 def guard():
  if time.perf_counter()-start>c['wall_limit_s']:raise RuntimeError('300s wall limit reached')
  if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>2*1024**2:raise RuntimeError('2GiB RSS limit reached')
 try:
  states={}
  for name,active4,tight in [('G1',False,False),('G2',True,False),('G2_tight',True,True)]:
   with (F/f'{name}_launch_once.json').open('x') as f:json.dump({'labels':LABELS,'J3':True,'J4':active4,'tight':tight},f)
   extra=HigherOrderZonalForce(axis,include_j3=True,include_j4=active4);rhs=make_state_derivative([central_gravity,axis.acceleration,extra]);tick=time.perf_counter()
   def guarded(t,y):guard();return rhs(t,y)
   print('START',name,flush=True);z=propagate(guarded,initial[:3],initial[3:],(0,21600),seconds,**c['tight' if tight else 'base']);states[name]=z.states;np.testing.assert_array_equal(initial,z.states[0])
   np.savez_compressed(L/f'{name}_states.npz',seconds=seconds,states=z.states,internal_times=z.internal_times_s)
   rows=[]
   for t,y,epoch in zip(seconds,z.states,times):
    k=axis(t);a2=j2_acceleration(y[:3],k);a3=j3_acceleration(y[:3],k);a4=j4_acceleration(y[:3],k) if active4 else np.zeros(3)
    rows.append([*LABELS,name,epoch.isot,t,*y,*a2,*a3,*a4,np.linalg.norm(a2),np.linalg.norm(a3),np.linalg.norm(a4)])
   with (ROOT/f'results/metrics/{args.run_tag}_{name}_states.csv').open('x') as f:
    w=csv.writer(f,lineterminator='\n');w.writerow(['status','evaluation_status','force_status','model','utc','elapsed_s','gcrs_x_m','gcrs_y_m','gcrs_z_m','gcrs_vx_m_s','gcrs_vy_m_s','gcrs_vz_m_s',*[f'{n}_a{a}_m_s2' for n in ['J2','J3','J4'] for a in ['x','y','z']],*[f'{n}_norm_m_s2' for n in ['J2','J3','J4']]]);w.writerows(rows)
   stats={'labels':LABELS,'integration':z.statistics,'initial_sha256':hashlib.sha256(np.asarray(z.states[0],dtype='<f8').tobytes()).hexdigest(),'wall_with_output_s':time.perf_counter()-tick,'peak_RSS_MiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'J3':True,'J4':active4}
   dump(F/f'{name}.json',stats);out['runs'][name]=stats;dump(F/'run_summary.json',out);print('END',name,z.statistics['elapsed_s'],flush=True)
  with np.load(ROOT/'data/processed/provisional_drag_orbit_v1/D0_states.npz') as z:g0=z['states']
  with np.load(ROOT/'data/processed/provisional_drag_orbit_v1/D0_tight_states.npz') as z:g0t=z['states']
  err=np.linalg.norm(states['G2'][:,:3]-states['G2_tight'][:,:3],axis=1)
  diff=np.linalg.norm((states['G2'][:,:3]-g0[:,:3])-(states['G2_tight'][:,:3]-g0t[:,:3]),axis=1)
  amplitude=np.linalg.norm(states['G2'][:,:3]-g0[:,:3],axis=1);limit=max(.005,.01*float(amplitude.max()))
  out['convergence']={'G2_state_max_m':float(err.max()),'state_threshold_m':.5,'G2_G0_pair_change_max_m':float(diff.max()),'pair_threshold_m':limit,'passed':bool(err.max()<.5 and diff.max()<limit)}
  for p,h in protected.items():assert sha(ROOT/p)==h
  out.update(protected_unchanged=True,actual_new_real_state_propagations=3,wall_s=time.perf_counter()-start);dump(F/'run_summary.json',out)
  if not out['convergence']['passed']:raise RuntimeError('Convergence gate failed; no interpretation/retry')
  print(json.dumps(out['convergence']),flush=True)
 except Exception as e:dump(F/'failure.json',{'reason':str(e),'traceback':traceback.format_exc()});raise
if __name__=='__main__':main()
