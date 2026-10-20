"""PROVISIONAL offline trajectory queries; never starts model or orbit integration."""
import argparse,csv,hashlib,json,sys,time,resource
from pathlib import Path
from collections import Counter
from dataclasses import asdict
import numpy as np
from astropy.time import Time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from atmosphere.density_interface import DensityQuery
from atmosphere.provisional_coordinate_adapter import (ProvisionalCoordinateAdapter,A_WGS84,B_SPHERE,diagnose_provisional_interpolation)
from atmosphere.tiegcm_density_provider import TiegcmDensityProvider
from evaluation.orbit_data import load_sp3_reference
from orbit.frames import configure_time_data

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def write_json(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False))
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--run-tag',default='swarm_provisional_v1');parser.add_argument('--full-after-coarse',action='store_true');args=parser.parse_args()
 if not args.run_tag.replace('_','').isalnum():raise ValueError('Unsafe tag')
 tag=args.run_tag;out=ROOT/'experiments'/tag;out.resolve().relative_to(ROOT);out.mkdir(exist_ok=False)
 local=ROOT/'data/processed'/tag;local.resolve().relative_to(ROOT);local.mkdir(exist_ok=False)
 start=time.perf_counter();audit={'status':'PROVISIONAL','model_launches':0,'orbit_integrations':0,'formal_swarm_valid_fraction':None,'files':[],'stages':{},'protected':{}}
 import shutil
 def guard():
  if time.perf_counter()-start>900:raise RuntimeError('Offline 900s budget exceeded')
  if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>1024*1024:raise RuntimeError('1 GiB RSS budget exceeded')
  if shutil.disk_usage(ROOT).free<20*1024**3:raise RuntimeError('Free disk below 20 GiB')
 guard()
 for source in ['S3','S7']:
  directory=ROOT/f'experiments/tiegcm2023_{source.lower()}_continuous_v1'
  for f in json.loads((directory/'data_audit.json').read_text())['files']:
   p=directory/f['file'];actual=sha(p)
   if actual!=f['sha256']:raise ValueError('Original NetCDF hash mismatch')
   audit['protected'][str(p.relative_to(ROOT))]=actual
 for p in [ROOT/'src/atmosphere/tiegcm_density_provider.py',ROOT/'src/atmosphere/density_interface.py']:
  audit['protected'][str(p.relative_to(ROOT))]=sha(p)
 configure_time_data();series=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3')))
 for s in series.metadata['sources']:
  for p in [Path(s['path']),Path(s['path']).with_suffix('.HDR')]:audit['protected'][str(p.relative_to(ROOT))]=sha(p)
 delta=(series.times-Time('2023-03-21T00:00:02',scale='utc')).sec;indices=np.flatnonzero((delta>=-1e-6)&(delta<=172800+1e-6))
 assert len(indices)==17281
 queries=[DensityQuery.from_itrs(series.times[i],series.positions_m[i]) for i in indices]
 scenarios={f'A{offset:+d}km':ProvisionalCoordinateAdapter(assumption=A_WGS84,height_offset_m=offset*1000) for offset in [-10,-5,-2,0,2,5,10]}
 scenarios['B_R6371km']=ProvisionalCoordinateAdapter(assumption=B_SPHERE,sphere_radius_m=6371000.)
 config={'status':'PROVISIONAL','run_tag':tag,'seconds_between_sp3':10,'coarse_stride':30,'full_baseline_scenarios':['A+0km','B_R6371km'],'scenarios':{k:asdict(v) for k,v in scenarios.items()},'budget':{'wall_seconds':900,'RSS_GiB':1,'new_output_MiB':256},'formal_provider_sha256':sha(ROOT/'src/atmosphere/tiegcm_density_provider.py'),'adapter_sha256':sha(ROOT/'src/atmosphere/provisional_coordinate_adapter.py'),'sphere_interpretation':'6371000m is an explicit exploratory reference only, not proven ZG zero','limitations':'PROVISIONAL conditional mappings; offsets are not confidence bounds; no orbit accuracy claim'}
 write_json(out/'configuration.json',config)
 providers={s:TiegcmDensityProvider((ROOT/f'experiments/tiegcm2023_{s.lower()}_continuous_v1').glob('secondary_*.nc'),s,cache_columns=4096) for s in ['S3','S7']}
 edges={};coarse_rows=[];timings={}
 fields=['status','source','sample','scenario','assumption','utc','itrs_x_m','itrs_y_m','itrs_z_m','wgs84_lon_deg','wgs84_lat_deg','wgs84_height_m','geocentric_lat_deg','model_lon_deg','model_lat_deg','model_zg_m','offset_m','sphere_radius_m','valid','reason','rho_kg_m3','top_margin_m','bottom_margin_m','dlnrho_dh_per_m','scale_height_m','vertical_spacing_min_m','vertical_spacing_max_m','vertical_linear_relative','horizontal_log_relative','time_log_relative','horizontal_and_time_log_relative','vertical_coarsened_log_relative','elapsed_ms','limitations']
 def run_stage(stage,sample_indices,names):
  stage_start=time.perf_counter();stats={};latencies=[]
  for source,p in providers.items():
   dest=ROOT/f'results/metrics/{tag}_coarse_{source}.csv' if stage=='coarse' else local/f'PROVISIONAL_full_{source}.csv'
   if dest.exists():raise FileExistsError(dest)
   counters={name:Counter() for name in names}
   with dest.open('x') as f:
    writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader()
    for count,ii in enumerate(sample_indices):
     if count%100==0:guard()
     q=queries[ii]
     for name in names:
      before=time.perf_counter();result=scenarios[name].query_provisional(p,q);c=result.coordinates;n=result.native_result
      d=diagnose_provisional_interpolation(p,result) if n.valid else {}
      milliseconds=(time.perf_counter()-before)*1000;latencies.append(milliseconds)
      if n.valid and (not np.isfinite(n.rho_kg_m3) or n.rho_kg_m3<=0):raise RuntimeError('Invalid valid density')
      counters[name]['valid' if n.valid else n.reason]+=1
      row=dict(zip(fields,[None]*len(fields)))
      row.update(status='PROVISIONAL',source=source,sample=int(ii),scenario=name,assumption=c.assumption,utc=c.utc,itrs_x_m=c.itrs_m[0],itrs_y_m=c.itrs_m[1],itrs_z_m=c.itrs_m[2],wgs84_lon_deg=c.wgs84_longitude_deg,wgs84_lat_deg=c.wgs84_latitude_deg,wgs84_height_m=c.wgs84_height_m,geocentric_lat_deg=c.geocentric_latitude_deg,model_lon_deg=c.model_longitude_deg,model_lat_deg=c.model_latitude_deg,model_zg_m=c.model_zg_m,offset_m=c.height_offset_m,sphere_radius_m=c.sphere_radius_m,valid=int(n.valid),reason=n.reason,rho_kg_m3=n.rho_kg_m3,elapsed_ms=milliseconds,limitations='PROVISIONAL; datum unverified; offsets are not bounds; no operational drag')
      row.update({k:v for k,v in d.items() if k in fields and k not in ('status','reason')});writer.writerow(row)
      if stage=='coarse':coarse_rows.append(row)
      conditions=[]
      if abs(c.wgs84_latitude_deg)>85:conditions.append('high_latitude')
      if abs(c.wgs84_longitude_deg)>175:conditions.append('longitude_seam')
      if abs(c.model_latitude_deg)>87:conditions.append('grid_edge')
      if not n.valid:conditions.append('invalid')
      for condition in conditions:
       key=f'{stage}_{source}_{name}_{condition}'
       if key not in edges:edges[key]=asdict(result)
     if count%1000==0:print(stage,source,count,'/',len(sample_indices),flush=True)
   audit['files'].append({'file':str(dest.relative_to(ROOT)),'bytes':dest.stat().st_size,'sha256':sha(dest)})
   stats[source]={name:{'samples':len(sample_indices),'valid_count':counters[name]['valid'],'valid_fraction':counters[name]['valid']/len(sample_indices),'reasons':dict(counters[name])} for name in names}
  timings[stage]={'seconds':time.perf_counter()-stage_start,'queries':len(latencies),'mean_ms':float(np.mean(latencies)),'p95_ms':float(np.percentile(latencies,95)),'cumulative_peak_RSS_MiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024}
  audit['stages'][stage]=stats;write_json(out/'progress.json',{'status':'PROVISIONAL','timings':timings,'stages':audit['stages']})
 try:
  coarse=np.arange(0,len(queries),30);assert len(coarse)==577
  run_stage('coarse',coarse,list(scenarios))
  passed=all(v['valid_fraction']==1 for source in audit['stages']['coarse'].values() for v in source.values())
  # Conservative measured estimate; full only for the two baseline maps.
  estimate=timings['coarse']['seconds']*(len(queries)*2)/(len(coarse)*8)
  audit['full_decision']={'coarse_gate_passed':passed,'estimated_full_seconds_from_coarse':estimate,'is_estimate':True}
  write_json(out/'coarse_gate.json',audit['full_decision'])
  if args.full_after_coarse and passed and time.perf_counter()-start+estimate*1.5<900:
   run_stage('full',np.arange(len(queries)),['A+0km','B_R6371km'])
  else:audit['full_decision']['not_run_reason']='not requested, gate failed, or conservative wall budget'
 finally:
  for p in providers.values():p.close()
 audit['timings']=timings;audit['elapsed_seconds']=time.perf_counter()-start;audit['peak_RSS_MiB']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
 audit['queries_SP3_samples']=len(queries)
 for name,expected in audit['protected'].items():
  if sha(ROOT/name)!=expected:raise ValueError('Protected data changed: '+name)
 audit['protected_unchanged']=True
 write_json(out/'edge_queries.json',edges)
 write_json(out/'audit.json',audit)
 total=sum(x['bytes'] for x in audit['files']);assert total<256*1024**2
 print(json.dumps({'status':'PROVISIONAL','timings':timings,'output_bytes':total},indent=2),flush=True)
if __name__=='__main__':main()
