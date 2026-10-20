"""Streaming independent audit of saved RK45 force queries; no propagation."""
import sys,gzip,json,hashlib,time
from pathlib import Path
from collections import Counter
import numpy as np
from astropy.time import Time,TimeDelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data,transform_state
from orbit.drag import EarthFixedFrame
from atmosphere.tiegcm_density_provider import TiegcmDensityProvider,DATUM
from atmosphere.provisional_drag_provider import LABELS
TAG='provisional_drag_orbit_v1';FOLDER=ROOT/'experiments'/TAG;LOCAL=ROOT/'data/processed'/TAG

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 audit_started=time.perf_counter()
 config=json.loads((FOLDER/'configuration.json').read_text());matrix=json.loads((FOLDER/'matrix_summary.json').read_text());pre=json.loads((FOLDER/'precheck.json').read_text())
 assert pre['passed'] and matrix['numerical_gate_passed']
 configure_time_data();epoch=Time(config['t0_utc'],scale='utc');frame=EarthFixedFrame(epoch)
 report={'labels':LABELS,'model_launches_TIEGCM':0,'precheck_real_state_propagations':pre['actual_integrations'],'matrix_real_state_propagations_including_tight':matrix['actual_integrations'],'formal_interfaces_modified':False,'queries':{}}
 selected=[]
 for path in sorted(LOCAL.glob('*_all_queries.jsonl.gz')):
  name=path.name.removesuffix('_all_queries.jsonl.gz');stats=json.loads((FOLDER/f'{name}.json').read_text());counts=Counter();seam_count=0;high_lat_count=0;max_formula=0.;max_norm=0.;max_dot=-np.inf;sampled=[]
  with gzip.open(path,'rt') as f:
   for i,line in enumerate(f):
    r=json.loads(line);assert tuple(r['labels'])==LABELS;assert 'failure' not in r
    counts[r['phase']]+=1;m=r['mapping'];n=r['native_query'];properties=r['properties']
    assert m['status']=='PROVISIONAL' and n['valid'] and n['rho_kg_m3']>0
    seam_count+=int({c['lon_index'] for c in n['metadata']['columns']}=={0,71})
    high_lat_count+=int(abs(m['model_latitude_deg'])>85)
    assert all(-1e-12<=w<=1+1e-12 for w in n['metadata']['weights'].values())
    assert r['source']==stats['source'] and m['assumption']==stats['mapping']
    assert properties['mass_kg']==400. and properties['area_m2']==1. and properties['cd']==2.2
    vr=np.array(r['relative_velocity_itrs_m_s']);ae=np.array(r['acceleration_itrs_m_s2']);ag=np.array(r['acceleration_gcrs_m_s2'])
    expected=-.5*n['rho_kg_m3']*2.2/400*np.linalg.norm(vr)*vr
    max_formula=max(max_formula,float(np.linalg.norm(ae-expected)));max_norm=max(max_norm,abs(float(np.linalg.norm(ae)-np.linalg.norm(ag))));max_dot=max(max_dot,float(ae@vr))
    assert np.allclose(ae,expected,rtol=1e-13,atol=1e-22) and ae@vr<=0
    if i<2 or i%1000==0:sampled.append(r)
  assert counts['rhs']==stats['integration']['nfev']==stats['force']['phase_calls']['rhs']
  assert sum(counts.values())==stats['force']['density_queries'] and stats['force']['failures']==0
  with TiegcmDensityProvider((ROOT/f'experiments/tiegcm2023_{stats["source"].lower()}_continuous_v1').glob('secondary_*.nc'),stats['source']) as native:
   density_error=0.;rotation_error=0.;position_roundtrip=0.;velocity_roundtrip=0.
   for r in sampled:
    m=r['mapping'];t=epoch+TimeDelta(r['seconds'],format='sec')
    value=native.query_native(t,m['model_latitude_deg'],m['model_longitude_deg'],m['model_zg_m'],datum=DATUM)
    assert value.valid
    density_error=max(density_error,abs(value.rho_kg_m3/r['native_query']['rho_kg_m3']-1))
    Q=frame.state_to_itrs(r['seconds'],r['position_gcrs_m'],r['velocity_gcrs_m_s'])[3]
    rotation_error=max(rotation_error,float(np.linalg.norm(Q.T@np.array(r['acceleration_itrs_m_s2'])-r['acceleration_gcrs_m_s2'])))
    rp,vp=transform_state(np.array([m['itrs_m']]),np.array([r['relative_velocity_itrs_m_s']]),Time([t]),'ITRS','GCRS')
    position_roundtrip=max(position_roundtrip,float(np.linalg.norm(rp[0]-r['position_gcrs_m'])));velocity_roundtrip=max(velocity_roundtrip,float(np.linalg.norm(vp[0]-r['velocity_gcrs_m_s'])))
   assert density_error<1e-12 and rotation_error<1e-20 and position_roundtrip<1e-6 and velocity_roundtrip<1e-7
  report['queries'][name]={'counts':dict(counts),'periodic_seam_stencil_queries':seam_count,'high_latitude_queries_abs_ge85':high_lat_count,'compressed_trace_bytes':path.stat().st_size,'trace_sha256':sha(path),'max_force_formula_difference_m_s2':max_formula,'max_rotation_norm_difference_m_s2':max_norm,'largest_a_dot_vrel_W_kg':max_dot,'recomputed_density_samples':len(sampled),'max_recomputed_density_relative_difference':density_error,'max_rotation_difference_m_s2':rotation_error,'max_full_state_roundtrip_position_m':position_roundtrip,'max_full_state_roundtrip_velocity_m_s':velocity_roundtrip}
 for name,digest in json.loads((FOLDER/'protected.json').read_text()).items():assert sha(ROOT/name)==digest
 old_sp3=json.loads((ROOT/'logs/swarm_sp3_inspection.json').read_text())
 for item in old_sp3['files']:assert sha(ROOT/item['file'])==item['sha256']
 report['protected_unchanged']=True;report['SP3_matches_old_manifest']=True
 report['all_internal_density_queries']=sum(r['counts'].get('rhs',0) for r in report['queries'].values());report['all_output_density_queries']=sum(r['counts'].get('output',0) for r in report['queries'].values())
 report['elapsed_since_initial_start_including_idle_s']=time.monotonic()-config['budget_start_monotonic']
 report['model_phase_budget_wall_s']=matrix['budget_used_wall_s']
 report['elapsed_note']='Audit resumed after user pause; elapsed_since_initial_start includes idle time, not model runtime'
 report['audit_elapsed_s']=time.perf_counter()-audit_started
 report['local_files']=[{'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p),'labels':LABELS} for p in sorted(LOCAL.iterdir()) if p.is_file()]
 with (FOLDER/'independent_audit.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False)
 print(json.dumps({'labels':LABELS,'rhs_density_queries':report['all_internal_density_queries'],'output_density_queries':report['all_output_density_queries'],'protected_unchanged':True,'audit_elapsed_s':report['audit_elapsed_s'],'model_phase_budget_wall_s':report['model_phase_budget_wall_s']},indent=2))
if __name__=='__main__':main()
