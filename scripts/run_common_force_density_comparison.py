"""H6 conditional drag matrix. C0 is immutable historical H6, never propagated."""
import sys,json,time,hashlib,resource,shutil,gzip,csv,traceback,argparse
from pathlib import Path
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from astropy.time import Time
from orbit.frames import configure_time_data
from orbit.common_force_model import CommonForceModel
from orbit.common_density_research import DensityResearchForce,LABELS
from orbit.rk45_propagator import propagate
from orbit.two_body import make_state_derivative
F=ROOT/'experiments/common_density_h6_v1';D=ROOT/'data/processed/common_density_h6_v1'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for x in iter(lambda:f.read(4*1024*1024),b''):h.update(x)
 return h.hexdigest()
def dump(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False)
def load(p):
 with np.load(p) as z:return z['states'].copy(),z['seconds'].copy()
def preflight():
 for p in [F,D]:p.resolve().relative_to(ROOT)
 F.mkdir(exist_ok=False)
 freeze=ROOT/'configs/provisional_common_force_model.json';frozen=json.loads(freeze.read_text());audit=json.loads((ROOT/'experiments/common_force_validation_v1/delivery_audit_final.json').read_text());assert audit['passed']
 for e in audit['artifacts']:assert sha(ROOT/e['file'])==e['sha256'],e['file']
 protected=json.loads((ROOT/'experiments/common_force_validation_v1/protected.json').read_text())
 # Progress documents will be updated only after execution; immutable scientific files remain protected.
 for e in audit['artifacts']:
  if e['file'].startswith(('data/','src/','configs/','experiments/')):protected[e['file']]=e['sha256']
 for p,h in {**frozen['implementation_sha256'],**frozen['legacy_code_sha256'],**frozen['code_sha256']}.items():assert sha(ROOT/p)==h,p
 assert sha(ROOT/frozen['evidence'])==frozen['evidence_sha256']
 for folder in ['experiments/msis_drag_orbit_v1','experiments/provisional_drag_orbit_v1','data/processed/msis_drag_orbit_v1','data/processed/provisional_drag_orbit_v1']:
  for p in (ROOT/folder).glob('*'):
   if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 for e in json.loads((ROOT/'logs/nrlmsis_drivers_audit.json').read_text())['sources']:
  assert sha(ROOT/e['path'])==e['sha256'];protected[e['path']]=e['sha256']
 protected['configs/nrlmsis2023_gfz_frozen.json']=sha(ROOT/'configs/nrlmsis2023_gfz_frozen.json')
 for e in json.loads((ROOT/'experiments/tiegcm2023_s7_continuous_v1/data_audit.json').read_text())['files']:
  p=ROOT/'experiments/tiegcm2023_s7_continuous_v1'/e['file'];assert sha(p)==e['sha256'];protected[str(p.relative_to(ROOT))]=e['sha256']
 for name in ['msis_density_provider','msis_drag_provider','tiegcm_density_provider','provisional_drag_provider','provisional_coordinate_adapter','density_interface']:
  p=ROOT/f'src/atmosphere/{name}.py';protected[str(p.relative_to(ROOT))]=sha(p)
 for p,h in protected.items():assert sha(ROOT/p)==h,p
 _,tm=configure_time_data()
 for name in ['iers_b','leap_seconds']:assert tm[name]['sha256']==frozen['time_data'][name]['sha256']
 base,seconds=load(ROOT/'data/processed/common_force_validation_v1/H6_states.npz');tight,st=load(ROOT/'data/processed/common_force_validation_v1/H6_tight_states.npz');np.testing.assert_array_equal(seconds,np.arange(0,21601,60));np.testing.assert_array_equal(seconds,st)
 y=np.array(frozen['initial_state_GCRS_SI']);assert hashlib.sha256(y.astype('<f8').tobytes()).hexdigest()==frozen['initial_sha256'];np.testing.assert_array_equal(base[0],y);np.testing.assert_array_equal(tight[0],y)
 assert 'Ran 187 tests' in (ROOT/'logs/common_density_tests.log').read_text() and (ROOT/'logs/common_density_tests.log').read_text().rstrip().endswith('OK')
 assert shutil.disk_usage(ROOT).free>20*2**30
 c=dict(labels=LABELS,common_freeze_file=str(freeze.relative_to(ROOT)),common_freeze_sha256=sha(freeze),initial_sha256=frozen['initial_sha256'],initial_state=y.tolist(),t0_utc=frozen['t0_utc'],base=frozen['numerics_base'],tight=frozen['numerics_tight'],time_data=tm,mass_kg=400.,Cd=2.2,area_m2=1.,wind='zero ITRS neutral wind; corotation through full state transform',B_sphere_radius_m=6371000.,NRLMSIS_version='2.1',pymsis_version='0.13.0',MSIS_driver_sha256=sha(ROOT/'configs/nrlmsis2023_gfz_frozen.json'),wall_limit_s=3600,RSS_limit_GiB=2,state_precheck_limit_m=.02,precheck_drag_pair_relative=.01,state_full_limit_m=.5,pair_full_limit_m=.1,forecast_safety_factor=1.1,current_authorization='Current user explicitly authorizes C1-C3; prior frozen no_density_runs_authorized field is a historical scope record and is preserved',new_code_sha256={p:sha(ROOT/p) for p in ['src/orbit/common_density_research.py','scripts/run_common_force_density_comparison.py','docs/COMMON_FORCE_DENSITY_PREREGISTRATION.md']})
 dump(F/'configuration.json',c);dump(F/'protected.json',protected);dump(F/'preflight.json',dict(passed=True,protected_files=len(protected),C0_reused=True,common_SHA_verified=True,free_disk_GiB=shutil.disk_usage(ROOT).free/2**30,tests=187));print('PREFLIGHT PASS',len(protected),'immutable files',flush=True)
def execute():
 c=json.loads((F/'configuration.json').read_text());protected=json.loads((F/'protected.json').read_text())
 for p,h in {**protected,**c['new_code_sha256']}.items():assert sha(ROOT/p)==h,p
 D.mkdir(exist_ok=False);dump(F/'launch_once.json',dict(allowed_1h=6,allowed_6h=6,new_C0_runs=0));configure_time_data();epoch=Time(c['t0_utc'],scale='utc');y=np.array(c['initial_state']);common=CommonForceModel(epoch,21600);start=time.monotonic();out=dict(labels=LABELS,runs={},prechecks={},full_gates={},new_C0_runs=0);states={}
 states['C0'],_=load(ROOT/'data/processed/common_force_validation_v1/H6_states.npz');states['C0_tight'],_=load(ROOT/'data/processed/common_force_validation_v1/H6_tight_states.npz')
 def guard():
  if time.monotonic()-start>3600 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>2*1024**2 or shutil.disk_usage(ROOT).free<20*2**30:raise RuntimeError('Propagation resource limit; no retry')
 def run(name,model,duration,tight):
  guard();dump(F/(name+'_launch_once.json'),dict(model=model,duration_s=duration,tight=tight,initial_sha256=c['initial_sha256'],common_freeze_sha256=c['common_freeze_sha256'],started_utc=Time.now().utc.isot));tick=time.perf_counter();times=np.arange(0,duration+1,60);rows=[];last=[time.monotonic()]
  with gzip.open(D/(name+'_queries.jsonl.gz'),'xt',compresslevel=1) as trace:
   def sink(r):trace.write(json.dumps(r,separators=(',',':'),allow_nan=False)+'\n')
   drag=DensityResearchForce(model,epoch,sink);rhs=make_state_derivative([common,drag])
   def guarded(t,state):
    guard()
    if time.monotonic()-last[0]>45:print('PROGRESS',name,round(t,2),'budget_s',round(time.monotonic()-start,2),flush=True);last[0]=time.monotonic()
    return rhs(t,state)
   print('START',name,flush=True)
   try:
    with patch('pymsis.msis.get_f107_ap',side_effect=RuntimeError('Automatic weather retrieval forbidden')):
     z=propagate(guarded,y[:3],y[3:],(0,duration),times,**c['tight' if tight else 'base']);np.testing.assert_array_equal(z.states[0],y);assert np.isfinite(z.states).all();assert drag.inner.phase_calls['rhs']==z.statistics['nfev']
     for t,state in zip(times,z.states):
      guard();value=drag.evaluate(t,state[:3],state[3:],phase='output');record=drag.last_record
      rows.append(dict(model=model,elapsed_s=int(t),utc=value['query'].utc.isot,**dict(zip(['x_m','y_m','z_m','vx_m_s','vy_m_s','vz_m_s'],state)),itrs_x_m=value['query'].position_itrs_m[0],itrs_y_m=value['query'].position_itrs_m[1],itrs_z_m=value['query'].position_itrs_m[2],wgs84_lat_deg=value['query'].latitude_deg,wgs84_lon_deg=value['query'].longitude_deg,wgs84_height_m=value['query'].height_wgs84_m,rho_kg_m3=value['density_kg_m3'],relative_speed_m_s=np.linalg.norm(value['relative_velocity_itrs_m_s']),**dict(zip(['relative_itrs_vx','relative_itrs_vy','relative_itrs_vz'],value['relative_velocity_itrs_m_s'])),**dict(zip(['drag_gcrs_ax','drag_gcrs_ay','drag_gcrs_az'],value['acceleration_gcrs_m_s2'])),drag_norm_m_s2=np.linalg.norm(value['acceleration_gcrs_m_s2']),density_query_s=record['density_query_seconds'],mapping='WGS84_NATIVE_MSIS' if model=='C1' else record['mapping']['assumption'],driver_or_interpolation_json=json.dumps(record['drivers'] if model=='C1' else record['native_query']['metadata'],separators=(',',':')),labels=' / '.join(LABELS)))
    stats=dict(model=model,integration=z.statistics,force=drag.statistics(),wall_with_output_s=time.perf_counter()-tick,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,labels=LABELS,all_queries_valid=drag.inner.bridge.failures==0)
    assert stats['all_queries_valid'];dump(F/(name+'.json'),stats)
    with (ROOT/f'results/metrics/common_density_h6_v1_{name}_states.csv').open('x') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    np.savez_compressed(D/(name+'_states.npz'),states=z.states,seconds=z.times_s,internal_times=z.internal_times_s);states[name]=z.states;out['runs'][name]=stats;print('END',name,stats['wall_with_output_s'],flush=True)
   finally:drag.close()
 def gate(name,b,t,threshold):
  delta=b-t;norm=np.linalg.norm(delta[:,:3],axis=1);v=dict(max_position_m=float(norm.max()),rms_position_m=float(np.sqrt(np.mean(norm**2))),max_velocity_m_s=float(np.linalg.norm(delta[:,3:],axis=1).max()),threshold_m=threshold,passed=bool(norm.max()<threshold));dump(F/(name+'_gate.json'),v)
  if not v['passed']:raise RuntimeError(name+' convergence gate failed')
  return v
 try:
  for n in ['C1','C2','C3']:
   run('pre_'+n,n,3600,False);run('pre_'+n+'_tight',n,3600,True);b=states['pre_'+n];t=states['pre_'+n+'_tight'];effect=np.linalg.norm(b[:,:3]-states['C0'][:61,:3],axis=1);out['prechecks'][n]=dict(state=gate(n+'_pre',b,t,.02),drag_response=gate(n+'_pre_pair',b-states['C0'][:61],t-states['C0_tight'][:61],.01*float(effect.max())))
  used=time.monotonic()-start;estimate=6*sum(v['wall_with_output_s'] for v in out['runs'].values())*1.1;dump(F/'runtime_budget.json',dict(precheck_wall_s=used,predicted_remaining_s=estimate,remaining_s=3600-used,safety_factor=1.1,passed=estimate<3600-used))
  if estimate>=3600-used:raise RuntimeError('Six-hour forecast exceeds remaining budget; no main propagation')
  for n in ['C1','C2','C3']:
   run(n,n,21600,False);run(n+'_tight',n,21600,True);out['full_gates'][n]=gate(n,states[n],states[n+'_tight'],.5)
  for a,b in [('C1','C0'),('C2','C0'),('C3','C0'),('C1','C2'),('C1','C3'),('C2','C3')]:out['full_gates'][a+'_'+b]=gate(a+'_'+b,states[a]-states[b],states[a+'_tight']-states[b+'_tight'],.1)
  out.update(passed=True,propagation_wall_s=time.monotonic()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,actual_1h_runs=6,actual_6h_runs=6);dump(F/'run_summary.json',out);print('ALL RUNS PASS',out['propagation_wall_s'],flush=True)
 except Exception as e:dump(F/'failure.json',dict(reason=str(e),traceback=traceback.format_exc(),completed=list(out['runs']),wall_s=time.monotonic()-start));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');args=p.parse_args()
 if args.execute:execute()
 else:preflight()
