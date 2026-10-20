"""Offline validation only. No model/trajectory integration or network access."""
import sys,json,hashlib,time,csv,resource,argparse
from pathlib import Path
import numpy as np
from astropy.time import Time
from astropy import units as u
from astropy.coordinates import EarthLocation
from netCDF4 import Dataset
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from atmosphere.tiegcm_density_provider import TiegcmDensityProvider,DATUM
from evaluation.orbit_data import load_sp3_reference
from orbit.frames import configure_time_data
OUT=ROOT/'experiments/tiegcm_density_interface_v1'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
def main():
 global OUT
 parser=argparse.ArgumentParser();parser.add_argument('--run-tag',default='tiegcm_density_interface_v1');args=parser.parse_args()
 if not args.run_tag.replace('_','').isalnum():raise ValueError('Unsafe run tag')
 OUT=ROOT/'experiments'/args.run_tag
 OUT.mkdir(exist_ok=False); report={'model_launches':0,'orbit_integrations':0,'provider_sha256':sha(ROOT/'src/atmosphere/tiegcm_density_provider.py'),'sources':{}}
 rows=[]
 for source in ['S3','S7']:
  directory=ROOT/f'experiments/tiegcm2023_{source.lower()}_continuous_v1';audit=json.loads((directory/'data_audit.json').read_text())
  verified=[]
  for f in audit['files']:
   p=directory/f['file'];h=sha(p)
   if h!=f['sha256']:raise ValueError('Protected hash changed: '+str(p))
   verified.append({'file':str(p.relative_to(ROOT)),'sha256':h})
  init=time.perf_counter()
  with TiegcmDensityProvider(directory.glob('secondary_*.nc'),source) as provider:
   index_s=time.perf_counter()-init
   grid=[]
   for k in [0,100,289]:
    t,path,record=provider.records[k]
    with Dataset(path) as n:
     n.set_auto_mask(False)
     h=float(n['ZG'][record,20,12,20])*.01;expected=float(n['DEN'][record,20,12,20])*1000
    r=provider.query_native(t,float(provider.lat[12]),float(provider.lon[20]),h,datum=DATUM)
    assert r.valid and abs(r.rho_kg_m3/expected-1)<1e-12
    grid.append({'utc':t.utc.isot,'rho_kg_m3':r.rho_kg_m3,'relative_error':r.rho_kg_m3/expected-1})
   elapsed=[]; alternatives=[];examples=[]
   for q in range(1000):
    k=q%289;t=provider.records[k][0]+300*u.s
    lat=-85+(q*17%17000)/100;lon=-180+(q*37%36000)/100
    start=time.perf_counter();r=provider.query_native(t,lat,lon,450000,datum=DATUM);elapsed.append(time.perf_counter()-start)
    assert r.valid,r.reason
    linear=provider.query_native(t,lat,lon,450000,datum=DATUM,vertical='linear')
    alternatives.append([linear.rho_kg_m3/r.rho_kg_m3-1,r.metadata['all_log_alternative_kg_m3']/r.rho_kg_m3-1])
    rows.append([source,q,t.utc.isot,lat,lon,450000,r.rho_kg_m3,elapsed[-1],*alternatives[-1]])
    if q<2:examples.append({'utc':t.utc.isot,'lat':lat,'lon':lon,'height_native_zg_m':450000,'result':r.__dict__})
   perf={'queries':1000,'index_seconds':index_s,'total_query_seconds':sum(elapsed),'mean_ms':float(np.mean(elapsed)*1000),'p95_ms':float(np.percentile(elapsed,95)*1000),'process_peak_RSS_MiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'column_cache_limit':provider.limit,'column_cache_bytes':sum(z.nbytes+rho.nbytes for z,rho in provider.cache.values()),'columns_read':provider.reads,'grid_tests':grid,'examples':examples,'linear_vertical_relative_difference_p95':float(np.percentile(np.abs(np.array(alternatives)[:,0]),95)),'all_log_horizontal_time_relative_difference_p95':float(np.percentile(np.abs(np.array(alternatives)[:,1]),95))}
  assert provider.closed and not provider.cache
  report['sources'][source]={'verified_files':verified,**perf}
 # Reuse the frozen time/EOP and SP3 conversion; no unverified ZG mapping.
 configure_time_data();series=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3')))
 dt=(series.times-Time('2023-03-21T00:00:02',scale='utc')).sec;selection=(dt>=-1e-6)&(dt<=172800+1e-6)
 r=series.positions_m[selection];geo=EarthLocation.from_geocentric(*r.T,unit=u.m).to_geodetic('WGS84')
 assert len(r)==17281
 report['Swarm']={'samples':len(r),'frame':series.frame,'WGS84_height_m':[float(geo.height.to_value(u.m).min()),float(geo.height.to_value(u.m).max())],'latitude_deg':[float(geo.lat.deg.min()),float(geo.lat.deg.max())],'formal_density_valid_fraction':None,'reason':'EXTERNAL_DATUM_UNVERIFIED','density_queries_executed':0}
 # Check protected NetCDF again after all reads.
 for entry in report['sources'].values():
  for f in entry['verified_files']:assert sha(ROOT/f['file'])==f['sha256']
 report['protected_NetCDF_unchanged']=True
 (OUT/'audit.json').write_text(json.dumps(report,indent=2))
 with (ROOT/('results/metrics/'+args.run_tag+'_queries.csv')).open('w') as f:
  writer=csv.writer(f,lineterminator="\n");writer.writerow(['source','query','utc','model_lat_deg','east_lon_deg','native_ZG_m','rho_kg_m3','seconds','linear_vertical_relative_difference','all_log_relative_difference']);writer.writerows(rows)
 print(json.dumps({k:{x:v[x] for x in ['queries','mean_ms','p95_ms','process_peak_RSS_MiB','linear_vertical_relative_difference_p95']} for k,v in report['sources'].items()},indent=2))
if __name__=='__main__':main()
