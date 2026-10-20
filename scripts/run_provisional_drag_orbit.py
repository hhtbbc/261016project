"""Bounded research-only RK45 matrix; never starts TIE-GCM or fits SP3."""
import argparse,csv,gzip,hashlib,json,resource,sys,time,traceback
from pathlib import Path
from dataclasses import asdict
import numpy as np
from astropy.time import Time,TimeDelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data,transform_state,check_eop
from orbit.drag import EarthFixedFrame,DragProperties
from orbit.two_body import central_gravity,make_state_derivative
from orbit.j2 import EarthFigureAxis
from orbit.rk45_propagator import propagate
from evaluation.orbit_data import load_sp3_reference
from atmosphere.tiegcm_density_provider import TiegcmDensityProvider
from atmosphere.provisional_coordinate_adapter import ProvisionalCoordinateAdapter,A_WGS84,B_SPHERE
from atmosphere.provisional_drag_provider import ProvisionalDragForce,LABELS

MODELS={'D0':(None,None),'D1':('S3',A_WGS84),'D2':('S7',A_WGS84),'D3':('S3',B_SPHERE),'D4':('S7',B_SPHERE)}
BASE={'rtol':1e-10,'atol':[1e-3]*3+[1e-6]*3,'max_step':30.}
TIGHT={'rtol':1e-12,'atol':[1e-5]*3+[1e-8]*3,'max_step':15.}
THRESHOLDS={'precheck_state_max_m':.02,'precheck_drag_difference_relative':.01,'six_hour_state_max_m':.5,'pair_convergence_relative':.01,'pair_convergence_floor_m':.005}

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
def dump(path,data):path.write_text(json.dumps(data,indent=2,allow_nan=False))
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--run-tag',default='provisional_drag_orbit_v1');parser.add_argument('--phase',choices=['precheck','matrix'],default='precheck');parser.add_argument('--execute',action='store_true');parser.add_argument('--duration-hours',type=int,choices=[1,3,6],default=6);a=parser.parse_args()
 if not a.run_tag.replace('_','').isalnum():raise ValueError('Invalid tag')
 if not a.execute:print(json.dumps({'labels':LABELS,'models':MODELS,'base':BASE,'tight':TIGHT,'thresholds':THRESHOLDS,'requires':'--execute and precheck before matrix'},indent=2));return
 folder=ROOT/'experiments'/a.run_tag;local=ROOT/'data/processed'/a.run_tag
 for path in [folder,local,ROOT/'results/metrics']:path.resolve().relative_to(ROOT)
 process_start=time.monotonic()
 if a.phase=='precheck':
  folder.mkdir(exist_ok=False);local.mkdir(exist_ok=False)
  config={'labels':LABELS,'t0_utc':'2023-03-21T00:00:02','max_duration_hours':6,'models':MODELS,'base':BASE,'tight':TIGHT,'thresholds':THRESHOLDS,'mass_kg':400.,'Cd':2.2,'area_m2':1.,'ballistic_coefficient_kg_m2':400/2.2,'ballistic_coefficient_definition':'m/(Cd*A)','wind':'zero neutral wind in ITRS, corotating atmosphere','B_sphere_radius_m':6371000.,'budget_start_monotonic':process_start,'budget_wall_s':1800,'RSS_limit_GiB':2,'runner_sha256':sha(Path(__file__)),'force_sha256':sha(ROOT/'src/atmosphere/provisional_drag_provider.py')}
  dump(folder/'configuration.json',config)
  protected={}
  for source in ['S3','S7']:
   directory=ROOT/f'experiments/tiegcm2023_{source.lower()}_continuous_v1'
   for item in json.loads((directory/'data_audit.json').read_text())['files']:
    path=directory/item['file'];assert sha(path)==item['sha256'];protected[str(path.relative_to(ROOT))]=item['sha256']
  for name in ['src/orbit/rk45_propagator.py','src/orbit/j2.py','src/orbit/drag.py','src/orbit/frames.py','src/atmosphere/tiegcm_density_provider.py','src/atmosphere/density_interface.py','src/atmosphere/provisional_coordinate_adapter.py','experiments/rk45_j2_v1/states.npz','experiments/rk45_j2_v1/summary.json']:
   protected[name]=sha(ROOT/name)
  dump(folder/'protected.json',protected)
 else:
  config=json.loads((folder/'configuration.json').read_text());pre=json.loads((folder/'precheck.json').read_text())
  if not pre['passed']:raise RuntimeError('Precheck failed; matrix blocked')
  if sha(Path(__file__))!=config['runner_sha256'] or sha(ROOT/'src/atmosphere/provisional_drag_provider.py')!=config['force_sha256']:raise RuntimeError('Frozen research code changed')
  with (folder/'matrix_launch_once.json').open('x') as f:json.dump({'labels':LABELS,'duration_hours':a.duration_hours},f)
  protected=json.loads((folder/'protected.json').read_text())
  for name,digest in protected.items():assert sha(ROOT/name)==digest
 table,time_meta=configure_time_data();t0=Time(config['t0_utc'],scale='utc')
 ref=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3')))
 initial=ref.take_exact(Time([t0]));r0,v0=transform_state(initial.positions_m,initial.velocities_m_s,Time([t0]),'ITRS','GCRS');r0=r0[0];v0=v0[0]
 old=json.loads((ROOT/'experiments/rk45_j2_v1/summary.json').read_text());np.testing.assert_array_equal(r0,old['initial_gcrs_position_m']);np.testing.assert_array_equal(v0,old['initial_gcrs_velocity_m_s'])
 axis=EarthFigureAxis(t0,21600.,cadence_s=60.)
 properties=DragProperties(config['mass_kg'],config['area_m2'],config['Cd'],'SYNTHETIC_AERODYNAMIC_PARAMETERS: explicit 400kg, 1m2, Cd2.2; not actual Swarm parameters')
 last_guard=[0.]
 def guard():
  now=time.monotonic()
  if now-last_guard[0]>.25:
   last_guard[0]=now
   if now-config['budget_start_monotonic']>config['budget_wall_s']-40:raise RuntimeError('Experiment wall budget reached; reserve 40s for audit')
   if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>2*1024**2:raise RuntimeError('2 GiB RSS cap reached')
 def run(name,model,duration,tight=False):
  guard();start=time.perf_counter();source,mapping=MODELS[model];times=np.arange(0,duration+1,60.);utc=t0+TimeDelta(times,format='sec')
  provider=None;force=None;trace_file=None;observations=[]
  try:
   if source:
    provider=TiegcmDensityProvider((ROOT/f'experiments/tiegcm2023_{source.lower()}_continuous_v1').glob('secondary_*.nc'),source,cache_columns=4096)
    adapter=ProvisionalCoordinateAdapter(assumption=mapping,sphere_radius_m=6371000. if mapping==B_SPHERE else None)
    trace_path=local/f'{name}_all_queries.jsonl.gz';trace_file=gzip.open(trace_path,'xt',compresslevel=1)
    def sink(record):trace_file.write(json.dumps(record,separators=(',',':'),allow_nan=False)+'\n')
    force=ProvisionalDragForce(frame=EarthFixedFrame(t0),provider=provider,adapter=adapter,properties=properties,acknowledge_provisional=True,audit_sink=sink)
   rhs=make_state_derivative([central_gravity,axis.acceleration]+([force] if force else []))
   def guarded_rhs(t,y):guard();return rhs(t,y)
   settings=TIGHT if tight else BASE
   print('START',name,model,'duration',duration,'tight',tight,flush=True)
   result=propagate(guarded_rhs,r0,v0,(0,duration),times,**settings)
   np.testing.assert_array_equal(result.states[0],np.r_[r0,v0])
   if force:assert force.phase_calls['rhs']==result.statistics['nfev']
   rows=[];density=[];accel=[];relative=[]
   for seconds,state,epoch in zip(times,result.states,utc):
    guard()
    if force:
     diagnostic=force.evaluate(seconds,state[:3],state[3:],phase='output');rho=diagnostic['density_kg_m3'];ar=diagnostic['acceleration_gcrs_m_s2'];vr=diagnostic['relative_velocity_itrs_m_s'];coordinates=diagnostic['provisional_query'].coordinates
     mapped_lat=coordinates.model_latitude_deg;mapped_height=coordinates.model_zg_m
    else:
     _,_,vr,_=EarthFixedFrame(t0).state_to_itrs(seconds,state[:3],state[3:]);rho=None;ar=np.zeros(3);mapped_lat=None;mapped_height=None
    density.append(np.nan if rho is None else rho);accel.append(ar);relative.append(vr)
    rows.append([*LABELS,model,source or 'NONE',mapping or 'NONE',epoch.utc.isot,seconds,*state,rho,*vr,*ar,np.linalg.norm(ar),mapped_lat,mapped_height])
   path=ROOT/f'results/metrics/{a.run_tag}_{name}_states.csv'
   with path.open('x') as f:
    w=csv.writer(f,lineterminator='\n');w.writerow(['status','parameter_status','driver_status','model','density_source','coordinate_mapping','utc','elapsed_s','gcrs_x_m','gcrs_y_m','gcrs_z_m','gcrs_vx_m_s','gcrs_vy_m_s','gcrs_vz_m_s','rho_kg_m3','relative_itrs_vx_m_s','relative_itrs_vy_m_s','relative_itrs_vz_m_s','drag_gcrs_ax_m_s2','drag_gcrs_ay_m_s2','drag_gcrs_az_m_s2','drag_norm_m_s2','model_lat_deg','model_zg_m']);w.writerows(rows)
   np.savez_compressed(local/f'{name}_states.npz',seconds=times,states=result.states,density=density,drag_gcrs=accel,relative_itrs=relative,internal_times=result.internal_times_s)
   stats={'labels':LABELS,'model':model,'source':source,'mapping':mapping,'integration':result.statistics,'initial_state':result.states[0].tolist(),'wall_with_output_diagnostics_s':time.perf_counter()-start,'peak_RSS_MiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'force':force.statistics() if force else None,'density_valid_fraction':1. if force else None}
   if force:
    assert force.bridge.failures==0
    assert len(density)==len(times) and np.isfinite(density).all() and np.min(density)>0
    assert np.max(np.linalg.norm(accel,axis=1))<1e-4
    stats['output_density_range_kg_m3']=[float(min(density)),float(max(density))]
    stats['output_acceleration_range_m_s2']=[float(np.min(np.linalg.norm(accel,axis=1))),float(np.max(np.linalg.norm(accel,axis=1)))]
    stats['relative_velocity_range_m_s']=[float(np.min(np.linalg.norm(relative,axis=1))),float(np.max(np.linalg.norm(relative,axis=1)))]
   dump(folder/f'{name}.json',stats);print('END',name,json.dumps(stats['integration']),flush=True)
   return result.states,stats
  finally:
   if trace_file:trace_file.close()
   if provider:provider.close()
 try:
  if a.phase=='precheck':
   d0,s0=run('pre_D0','D0',3600);d2,s2=run('pre_D2','D2',3600)
   z0,t0stats=run('pre_D0_tight','D0',3600,True);z2,t2stats=run('pre_D2_tight','D2',3600,True)
   effect=np.linalg.norm(d2[:,:3]-d0[:,:3],axis=1)
   err0=np.linalg.norm(d0[:,:3]-z0[:,:3],axis=1);err2=np.linalg.norm(d2[:,:3]-z2[:,:3],axis=1)
   err_pair=np.linalg.norm((d2[:,:3]-d0[:,:3])-(z2[:,:3]-z0[:,:3]),axis=1)
   gate=bool(max(err0.max(),err2.max())<THRESHOLDS['precheck_state_max_m'] and err_pair.max()<THRESHOLDS['precheck_drag_difference_relative']*effect.max())
   pre={'labels':LABELS,'passed':gate,'max_state_difference_D0_m':float(err0.max()),'max_state_difference_D2_m':float(err2.max()),'max_drag_effect_m':float(effect.max()),'terminal_drag_effect_m':float(effect[-1]),'max_pair_convergence_difference_m':float(err_pair.max()),'actual_integrations':4,'time_data':time_meta,'eop':check_eop(Time([Time(config['t0_utc']),Time(config['t0_utc'])+TimeDelta(21600,format='sec')]),table),'initialization':'single native SP3 P/V, no calibration','SP3_metadata':ref.metadata}
   # Planning estimate only, not an extra propagation.
   pre['estimated_6h_matrix_seconds']=6*(4*s2['wall_with_output_diagnostics_s']+3*t2stats['wall_with_output_diagnostics_s']+2*s0['wall_with_output_diagnostics_s'])*1.15+60
   pre['budget_used_wall_s']=time.monotonic()-config['budget_start_monotonic'];pre['remaining_wall_s']=1800-pre['budget_used_wall_s']
   dump(folder/'precheck.json',pre)
   print(json.dumps(pre,indent=2),flush=True)
   if not gate:raise RuntimeError('Precheck convergence failed; no matrix authorized by gate')
  else:
   duration=a.duration_hours*3600
   if pre['estimated_6h_matrix_seconds']*(duration/21600)>1800-(time.monotonic()-config['budget_start_monotonic'])-40:raise RuntimeError('Matrix forecast exceeds remaining budget; select a shorter permitted window before starting')
   summary={'labels':LABELS,'duration_s':duration,'runs':{},'convergence':{},'actual_integrations':0}
   states={}
   for model in MODELS:
    states[model],summary['runs'][model]=run(model,model,duration);summary['actual_integrations']+=1;dump(folder/'matrix_progress.json',summary)
   tight_states={}
   for model in ['D0','D1','D2','D4']:
    tight_states[model],summary['runs'][model+'_tight']=run(model+'_tight',model,duration,True);summary['actual_integrations']+=1;dump(folder/'matrix_progress.json',summary)
   for model in tight_states:
    difference=np.linalg.norm(states[model][:,:3]-tight_states[model][:,:3],axis=1)
    summary['convergence'][model]={'max_position_difference_m':float(difference.max()),'terminal_difference_m':float(difference[-1]),'passed':bool(difference.max()<THRESHOLDS['six_hour_state_max_m'])}
   for lhs,rhs in [('D1','D2'),('D2','D4'),('D2','D0')]:
    difference=np.linalg.norm((states[lhs][:,:3]-states[rhs][:,:3])-(tight_states[lhs][:,:3]-tight_states[rhs][:,:3]),axis=1);amplitude=np.linalg.norm(states[lhs][:,:3]-states[rhs][:,:3],axis=1)
    threshold=max(THRESHOLDS['pair_convergence_floor_m'],THRESHOLDS['pair_convergence_relative']*float(amplitude.max()))
    summary['convergence'][lhs+'_'+rhs]={'max_difference_m':float(difference.max()),'threshold_m':threshold,'passed':bool(difference.max()<threshold)}
   summary['numerical_gate_passed']=all(x['passed'] for x in summary['convergence'].values())
   summary['budget_used_wall_s']=time.monotonic()-config['budget_start_monotonic'];summary['peak_RSS_MiB']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
   for name,digest in protected.items():assert sha(ROOT/name)==digest
   summary['protected_unchanged']=True;dump(folder/'matrix_summary.json',summary)
   print(json.dumps(summary,indent=2),flush=True)
   if not summary['numerical_gate_passed']:raise RuntimeError('Convergence gate failed; do not interpret sensitivity quantitatively')
 except Exception as e:
  dump(folder/f'{a.phase}_failure.json',{'labels':LABELS,'reason':str(e),'traceback':traceback.format_exc(),'budget_wall_s':time.monotonic()-config['budget_start_monotonic']})
  raise
if __name__=='__main__':main()
