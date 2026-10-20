"""D5 only: gated 1h + 6h base/tight; never propagates historical D0--D4."""
import argparse,csv,gzip,hashlib,json,resource,sys,time,traceback,platform
from pathlib import Path
from unittest.mock import patch
import numpy as np
from astropy.time import Time,TimeDelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data,transform_state
from orbit.drag import EarthFixedFrame,DragProperties
from orbit.two_body import central_gravity,make_state_derivative,EARTH_MU
from orbit.j2 import EarthFigureAxis,J2_COEFFICIENT,J2_REFERENCE_RADIUS_M
from orbit.rk45_propagator import propagate
from atmosphere.msis_density_provider import FrozenGfzDrivers,MsisDensityProvider
from atmosphere.msis_drag_provider import MsisResearchDrag
from atmosphere.provisional_drag_provider import LABELS
from evaluation.orbit_data import load_sp3_reference

OLD=ROOT/'experiments/provisional_drag_orbit_v1';OLD_LOCAL=ROOT/'data/processed/provisional_drag_orbit_v1'
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
def loadstate(name):
 with np.load(OLD_LOCAL/f'{name}_states.npz') as z:return z['states'].copy()
def initial_sha(y):return hashlib.sha256(np.asarray(y,dtype='<f8').tobytes()).hexdigest()

def prepare(folder):
 folder.mkdir(exist_ok=False)
 old=json.loads((OLD/'configuration.json').read_text());old_audit=json.loads((OLD/'independent_audit.json').read_text())
 protected={}
 for x in old_audit['local_files']:
  assert sha(ROOT/x['file'])==x['sha256'];protected[x['file']]=x['sha256']
 for p in [*OLD.glob('*.json'),*ROOT.glob('results/metrics/provisional_drag_orbit_v1*.csv'),
           *ROOT.glob('reports/PROVISIONAL_DRAG*.md'),ROOT/'configs/nrlmsis2023_gfz_frozen.json',ROOT/'logs/20261020_frozen_time_data.json']:
  protected[str(p.relative_to(ROOT))]=sha(p)
 for name,digest in json.loads((OLD/'protected.json').read_text()).items():
  assert sha(ROOT/name)==digest;protected[name]=digest
 for x in json.loads((ROOT/'logs/nrlmsis_drivers_audit.json').read_text())['sources']:
  assert sha(ROOT/x['path'])==x['sha256'];protected[x['path']]=x['sha256']
 for name in ['src/orbit/two_body.py','src/orbit/j2.py','src/orbit/rk45_propagator.py','src/orbit/drag.py','src/orbit/frames.py','src/atmosphere/density_interface.py','src/atmosphere/tiegcm_density_provider.py']:
  protected[name]=sha(ROOT/name)
 configure_time_data();t0=Time(old['t0_utc'],scale='utc')
 ref=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))).take_exact(Time([t0]))
 r,v=transform_state(ref.positions_m,ref.velocities_m_s,Time([t0]),'ITRS','GCRS');y=np.r_[r[0],v[0]]
 for name in ['D0','D1','D2','D3','D4']:
  d=json.loads((OLD/f'{name}.json').read_text());np.testing.assert_array_equal(y,d['initial_state']);np.testing.assert_array_equal(loadstate(name)[0],y)
  assert d['integration']['rtol']==old['base']['rtol'] and d['integration']['max_step_s']==old['base']['max_step']
  np.testing.assert_array_equal(d['integration']['atol_si'],old['base']['atol'])
 config={'labels':LABELS,'t0_utc':old['t0_utc'],'duration_s':21600,'output_cadence_s':60,
  'base':old['base'],'tight':old['tight'],'thresholds':old['thresholds'],
  'mass_kg':old['mass_kg'],'Cd':old['Cd'],'area_m2':old['area_m2'],'wind':old['wind'],
  'initial_state_gcrs_si':y.tolist(),'initial_state_sha256_le_float64':initial_sha(y),
  'gravity':{'mu':EARTH_MU,'J2':J2_COEFFICIENT,'radius_m':J2_REFERENCE_RADIUS_M,'axis_grid_cadence_s':60,'axis_grid_duration_s':21600},
  'NRLMSIS':'2.1','pymsis':'0.13.0','driver_sha256':sha(ROOT/'configs/nrlmsis2023_gfz_frozen.json'),
  'wall_budget_s':1200,'memory_limit_GiB':2,'allowable_runs':['pre_D5','pre_D5_tight','D5','D5_tight'],
  'code_sha256':{p:sha(ROOT/p) for p in ['scripts/run_msis_drag_orbit.py','src/atmosphere/msis_drag_provider.py','src/atmosphere/msis_density_provider.py']},
  'preflight_disk_free_GiB':__import__('shutil').disk_usage(ROOT).free/2**30,'SP3_metadata':ref.metadata,
  'time_data':json.loads((OLD/'precheck.json').read_text())['time_data'],
  'precision_change':'Astropy datetime64 retains submillisecond times; underlying pymsis Fortran float32 inputs remain as distributed'}
 assert config['preflight_disk_free_GiB']>20
 dump(folder/'configuration.json',config);dump(folder/'protected.json',protected)
 dump(folder/'preflight.json',{'passed':True,'protected_count':len(protected),'historical_local_artifacts_match_previous_audit':len(old_audit['local_files']),'initial_state_sha256':initial_sha(y),'initial_source':'same SP3 single epoch; later SP3 not used inside dynamics','historical_runs_restarted':0,'python':platform.python_version()})
 print('Static preflight passed',len(protected),'protected files',flush=True)


def execute(folder,local,tag):
 config=json.loads((folder/'configuration.json').read_text());protected=json.loads((folder/'protected.json').read_text())
 for p,d in protected.items():assert sha(ROOT/p)==d
 for p,d in config['code_sha256'].items():assert sha(ROOT/p)==d
 assert 'Ran 133 tests' in (ROOT/'logs/msis_drag_all_tests.log').read_text()
 local.mkdir(exist_ok=False)
 with (folder/'launch_once.json').open('x') as f:json.dump({'runs_limit':4,'labels':LABELS},f)
 tick=time.monotonic();last=[0.];y=np.asarray(config['initial_state_gcrs_si']);t0=Time(config['t0_utc'],scale='utc')
 _,tm=configure_time_data();axis=EarthFigureAxis(t0,21600,cadence_s=60)
 assert tm['iers_b']['sha256']==config['time_data']['iers_b']['sha256'] and tm['leap_seconds']['sha256']==config['time_data']['leap_seconds']['sha256']
 provider=MsisDensityProvider(FrozenGfzDrivers(ROOT/'configs/nrlmsis2023_gfz_frozen.json'),version='2.1')
 prop=DragProperties(400,1,2.2,'SYNTHETIC_AERODYNAMIC_PARAMETERS: frozen demonstration, not real Swarm aerodynamic parameters')
 progress={'labels':LABELS,'runs':{},'new_D0_D4_runs':0,'new_TIE_runs':0}
 def guard():
  if time.monotonic()-tick>config['wall_budget_s']-90:raise RuntimeError('1200s task budget; reserving 90s for audit/analysis')
  if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>2*1024**2:raise RuntimeError('RSS exceeds 2GiB')
 def run(name,duration,tight):
  with (folder/f'{name}_launch_once.json').open('x') as f:json.dump({'duration_s':duration,'tight':tight},f)
  start=time.perf_counter();times=np.arange(0,duration+1,60.);utc=t0+TimeDelta(times,format='sec');rows=[]
  with gzip.open(local/f'{name}_queries.jsonl.gz','xt',compresslevel=1) as trace:
   def sink(r):trace.write(json.dumps(r,separators=(',',':'),allow_nan=False)+'\n')
   force=MsisResearchDrag(frame=EarthFixedFrame(t0),provider=provider,properties=prop,acknowledge_provisional=True,audit_sink=sink)
   rhs=make_state_derivative([central_gravity,axis.acceleration,force])
   def guarded(t,state):
    guard()
    if time.monotonic()-last[0]>20:
     last[0]=time.monotonic();dump(folder/'progress.json',{'run':name,'seconds':float(t),'budget_used_s':time.monotonic()-tick});print('PROGRESS',name,round(t,3),flush=True)
    return rhs(t,state)
   print('START',name,flush=True)
   with patch('pymsis.msis.get_f107_ap',side_effect=RuntimeError('Implicit weather access forbidden')):
    result=propagate(guarded,y[:3],y[3:],(0,duration),times,**config['tight' if tight else 'base'])
    assert force.phase_calls['rhs']==result.statistics['nfev'];np.testing.assert_array_equal(y,result.states[0])
    for sec,state,t in zip(times,result.states,utc):
     guard();v=force.evaluate(sec,state[:3],state[3:],phase='output');r=v['msis_record'];r['utc']=t.utc.isot
     rows.append([*LABELS,'D5','NRLMSIS 2.1','WGS84',r['utc'],sec,*state,*r['position_itrs_m'],r['longitude_wgs84_deg'],r['latitude_wgs84_deg'],r['height_wgs84_m'],r['rho_kg_m3'],*r['relative_velocity_itrs_m_s'],*r['acceleration_gcrs_m_s2'],np.linalg.norm(r['acceleration_gcrs_m_s2']),r['drivers']['f107_previous_day'],r['drivers']['f107a_centered81'],*r['drivers']['ap'],r['density_query_seconds'],r['drivers']['provenance']])
  with (ROOT/f'results/metrics/{tag}_{name}_states.csv').open('x') as f:
   w=csv.writer(f,lineterminator='\n');w.writerow(['status','parameter_status','driver_status','model','density_source','coordinate_mapping','utc','elapsed_s','gcrs_x_m','gcrs_y_m','gcrs_z_m','gcrs_vx_m_s','gcrs_vy_m_s','gcrs_vz_m_s','itrs_x_m','itrs_y_m','itrs_z_m','wgs84_lon_deg','wgs84_lat_deg','wgs84_height_m','rho_kg_m3','relative_itrs_vx_m_s','relative_itrs_vy_m_s','relative_itrs_vz_m_s','drag_gcrs_ax_m_s2','drag_gcrs_ay_m_s2','drag_gcrs_az_m_s2','drag_norm_m_s2','f107_previous_day','f107a_centered81',*[f'ap_{j}' for j in range(7)],'density_query_s','driver_provenance']);w.writerows(rows)
  np.savez_compressed(local/f'{name}_states.npz',seconds=times,states=result.states,internal_times=result.internal_times_s)
  stats={'labels':LABELS,'initial_state_sha256':initial_sha(result.states[0]),'integration':result.statistics,'force':force.statistics(),'wall_with_output_diagnostics_s':time.perf_counter()-start,'peak_RSS_MiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'all_queries_valid':force.bridge.failures==0}
  assert stats['all_queries_valid'];dump(folder/f'{name}.json',stats);progress['runs'][name]=stats;dump(folder/'run_summary.json',progress);print('END',name,result.statistics['elapsed_s'],flush=True)
  return result.states
 try:
  pre=run('pre_D5',3600,False);pt=run('pre_D5_tight',3600,True)
  d0=loadstate('pre_D0');d0t=loadstate('pre_D0_tight')
  state=np.linalg.norm(pre[:,:3]-pt[:,:3],axis=1);effect=np.linalg.norm(pre[:,:3]-d0[:,:3],axis=1)
  pair=np.linalg.norm((pre[:,:3]-d0[:,:3])-(pt[:,:3]-d0t[:,:3]),axis=1)
  th=config['thresholds'];precheck={'labels':LABELS,'state_max_m':float(state.max()),'drag_effect_max_m':float(effect.max()),'paired_change_max_m':float(pair.max()),'state_threshold_m':th['precheck_state_max_m'],'paired_threshold_m':float(effect.max())*th['precheck_drag_difference_relative']}
  precheck['passed']=bool(state.max()<precheck['state_threshold_m'] and pair.max()<precheck['paired_threshold_m'])
  estimate=6*sum(progress['runs'][n]['wall_with_output_diagnostics_s'] for n in ['pre_D5','pre_D5_tight'])*1.25+90
  precheck.update(estimated_remaining_s=estimate,used_wall_s=time.monotonic()-tick);dump(folder/'precheck.json',precheck)
  if not precheck['passed']:raise RuntimeError('1h gate failed; 6h blocked, no retry')
  if estimate>1200-(time.monotonic()-tick):raise RuntimeError('6h forecast exceeds remaining budget; stop')
  base=run('D5',21600,False);tight=run('D5_tight',21600,True)
  errors={'D5_state':{'max_m':float(np.linalg.norm(base[:,:3]-tight[:,:3],axis=1).max()),'threshold_m':th['six_hour_state_max_m']}}
  for name in ['D0','D1','D2','D4']:
   b=loadstate(name);t=loadstate(name+'_tight');effect=np.linalg.norm(base[:,:3]-b[:,:3],axis=1)
   delta=np.linalg.norm((base[:,:3]-b[:,:3])-(tight[:,:3]-t[:,:3]),axis=1)
   errors['D5_'+name]={'max_m':float(delta.max()),'threshold_m':max(th['pair_convergence_floor_m'],th['pair_convergence_relative']*float(effect.max()))}
  for v in errors.values():v['passed']=v['max_m']<v['threshold_m']
  progress.update(convergence=errors,numerical_gate_passed=all(x['passed'] for x in errors.values()),run_phase_wall_s=time.monotonic()-tick)
  for p,d in protected.items():assert sha(ROOT/p)==d
  progress['protected_unchanged']=True;dump(folder/'run_summary.json',progress)
  if not progress['numerical_gate_passed']:raise RuntimeError('6h convergence failed; interpretation blocked')
  print('ALL FOUR D5 RUNS COMPLETE',json.dumps(errors),flush=True)
 except Exception as e:
  dump(folder/'failure.json',{'labels':LABELS,'reason':str(e),'traceback':traceback.format_exc(),'wall_s':time.monotonic()-tick});raise

def main():
 p=argparse.ArgumentParser();p.add_argument('--run-tag',default='msis_drag_orbit_v1');p.add_argument('--execute',action='store_true');a=p.parse_args()
 if not a.run_tag.replace('_','').isalnum():raise ValueError('Safe tag required')
 folder=ROOT/'experiments'/a.run_tag;local=ROOT/'data/processed'/a.run_tag
 for q in [folder,local]:q.resolve().relative_to(ROOT)
 if not a.execute:prepare(folder)
 else:execute(folder,local,a.run_tag)
if __name__=='__main__':main()
