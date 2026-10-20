"""Offline reference-trajectory densities only; no orbit integration or TIE launch."""
import sys,json,csv,hashlib,time,resource,platform,importlib.metadata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import astropy.units as u
from astropy.time import Time
from orbit.frames import configure_time_data
from evaluation.orbit_data import load_sp3_reference
from atmosphere.density_interface import DensityQuery
from atmosphere.msis_density_provider import FrozenGfzDrivers,MsisDensityProvider
import pymsis
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from unittest.mock import patch

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def savecsv(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
def stats(x):
 x=np.asarray(x);return {'min':float(x.min()),'max':float(x.max()),'median':float(np.median(x)),'mean':float(x.mean()),'p95':float(np.percentile(x,95)),'rmse':float(np.sqrt(np.mean(x*x)))}

def main():
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--run-tag',required=True);parser.add_argument('--output-prefix',default='nrlmsis2023');args=parser.parse_args()
 prefix=args.output_prefix
 if not prefix.replace('_','').isalnum():raise ValueError('Safe output prefix required')
 if not args.run_tag.replace('_','').isalnum():raise ValueError('Safe run-tag required')
 start=time.perf_counter();run=ROOT/'experiments'/args.run_tag;run.mkdir(exist_ok=False)
 if (ROOT/f'results/metrics/{prefix}_60s.csv').exists():raise ValueError('Existing published outputs; do not overwrite')
 _,eop=configure_time_data()
 frozen=FrozenGfzDrivers(ROOT/'configs/nrlmsis2023_gfz_frozen.json');provider=MsisDensityProvider(frozen,version='2.1')
 protected={}
 for src in ['s3','s7']:
  audit=json.loads((ROOT/f'experiments/tiegcm2023_{src}_continuous_v1/data_audit.json').read_text())
  for x in audit['files']:
   p=ROOT/f'experiments/tiegcm2023_{src}_continuous_v1'/x['file'];assert sha(p)==x['sha256'],str(p);protected[str(p.relative_to(ROOT))]=x['sha256']
 old=json.loads((ROOT/'experiments/swarm_provisional_v1/audit.json').read_text())
 table={};read_times={}
 for src in ['S3','S7']:
  p=ROOT/f'data/processed/swarm_provisional_v1/PROVISIONAL_full_{src}.csv'
  entry=next(x for x in old['files'] if x['file']==str(p.relative_to(ROOT)))
  assert sha(p)==entry['sha256'];protected[entry['file']]=entry['sha256']
  t=time.perf_counter()
  with p.open() as f:
   for r in csv.DictReader(f):
    sample=int(r['sample'])
    if sample<=2160 and sample%6==0:
     assert r['valid']=='1' and r['status']=='PROVISIONAL'
     table[(src,r['scenario'],sample)]=r
  read_times[src]=time.perf_counter()-t
 orbit=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3')))
 t0=Time('2023-03-21T00:00:02',scale='utc')
 outputs={};latencies={};summaries={}
 with patch('pymsis.msis.get_f107_ap',side_effect=RuntimeError('Network/default weather forbidden')):
  for step in [300,60]:
   times=t0+np.arange(0,21600+1,step)*u.s;ref=orbit.take_exact(times)
   qs=[DensityQuery.from_itrs(t,r) for t,r in zip(times,ref.positions_m)]
   lat=np.array([q.latitude_deg for q in qs]);lon=np.array([q.longitude_deg for q in qs]);height=np.array([q.height_wgs84_m for q in qs])
   tick=time.perf_counter();results=provider.query_batch(times,lon,lat,height);duration=time.perf_counter()-tick
   rows=[]
   for i,(t,q,result) in enumerate(zip(times,qs,results)):
    sample=i*step//10
    row={'status':'HINDCAST; TIE comparisons PROVISIONAL','utc':t.isot,'elapsed_s':i*step,'wgs84_lat_deg':q.latitude_deg,'wgs84_lon_deg':q.longitude_deg,'height_wgs84_m':q.height_wgs84_m,'nrlmsis21_kg_m3':result.rho_kg_m3,'f107_previous_day':result.drivers.f107_previous_day,'f107a_centered81':result.drivers.f107a_centered81}
    row.update({f'ap_{j}':v for j,v in enumerate(result.drivers.ap)})
    for src in ['S3','S7']:
     for mapping,scenario in [('A','A+0km'),('B','B_R6371km')]:
      r=table[(src,scenario,sample)]
      assert abs((Time(r['utc'])-t).to_value(u.s))<1e-6
      np.testing.assert_allclose([float(r[k]) for k in ['itrs_x_m','itrs_y_m','itrs_z_m']],q.position_itrs_m,rtol=0,atol=1e-6)
      np.testing.assert_allclose([float(r['wgs84_lat_deg']),float(r['wgs84_lon_deg']),float(r['wgs84_height_m'])],[q.latitude_deg,q.longitude_deg,q.height_wgs84_m],rtol=0,atol=1e-6)
      key=f'{src}_{mapping}';rho=float(r['rho_kg_m3']);row[key+'_kg_m3']=rho;row[key+'_ratio_to_msis']=rho/result.rho_kg_m3;row[key+'_ln_ratio']=np.log(rho/result.rho_kg_m3)
    rows.append(row)
   savecsv(ROOT/f'results/metrics/{prefix}_{step}s.csv',rows);outputs[step]=rows
   summaries[str(step)]={'samples':len(rows),'valid_fraction':1.0,'batch_wall_s':duration,'rho_kg_m3':stats([r.rho_kg_m3 for r in results]),'height_m':stats(height),'latitude_deg':stats(lat)}
   if step==300:
    assert len(rows)==73 and all(x.rho_kg_m3>0 for x in results)
  # Distinct scalar latency benchmark, not mixed with batch speed or old TIE timing.
  for q in qs:
   tick=time.perf_counter();provider.density_kg_m3(q);latencies.setdefault('msis_scalar_ms',[]).append(1000*(time.perf_counter()-tick))
 rows=outputs[60];hours=np.array([r['elapsed_s']/3600 for r in rows]);msis=np.array([r['nrlmsis21_kg_m3'] for r in rows]);lat=np.array([r['wgs84_lat_deg'] for r in rows]);h=np.array([r['height_wgs84_m'] for r in rows])
 comparisons=[]
 for key in ['S3_A','S7_A','S3_B','S7_B']:
  rho=np.array([r[key+'_kg_m3'] for r in rows]);diff=rho-msis;ratio=rho/msis;log=np.log(ratio)
  for name,mask in [('global',np.ones(len(rows),bool)),('south_polar',lat<-60),('south_mid',(lat>=-60)&(lat<-30)),('low',abs(lat)<=30),('north_mid',(lat>30)&(lat<=60)),('north_polar',lat>60)]:
   if not mask.any():continue
   comparisons.append({'mapping_source':key,'region':name,'n':int(mask.sum()),'relative_median_percent':float(np.median((ratio[mask]-1)*100)),'absolute_relative_p95_percent':float(np.percentile(abs(ratio[mask]-1)*100,95)),'ratio_min':float(ratio[mask].min()),'ratio_max':float(ratio[mask].max()),'density_difference_RMSE_kg_m3':float(np.sqrt(np.mean(diff[mask]**2))),'density_difference_median_kg_m3':float(np.median(diff[mask])),'log_RMSE':float(np.sqrt(np.mean(log[mask]**2))),'log_height_correlation_descriptive':float(np.corrcoef(log[mask],h[mask])[0,1]),'log_abs_latitude_correlation_descriptive':float(np.corrcoef(log[mask],abs(lat[mask]))[0,1])})
 savecsv(ROOT/f'results/metrics/{prefix}_comparison.csv',comparisons)
 peaks={}
 for key in ['nrlmsis21','S3_A','S7_A','S3_B','S7_B']:
  i=int(np.argmax([r[key+'_kg_m3'] for r in rows]));peaks[key]={k:rows[i][k] for k in ['utc','wgs84_lat_deg','wgs84_lon_deg','height_wgs84_m',key+'_kg_m3']}
 def finish(name):
  plt.suptitle('HINDCAST | TIE-GCM A/B mappings PROVISIONAL',fontsize=10);plt.tight_layout();plt.savefig(ROOT/f'results/figures/{prefix}_{name}.png',dpi=140);plt.close()
 plt.figure(figsize=(10,4));plt.plot(hours,msis*1e12,label='NRLMSIS 2.1 / WGS84')
 for key in ['S3_A','S7_A','S3_B','S7_B']:plt.plot(hours,[r[key+'_kg_m3']*1e12 for r in rows],label=key,alpha=.8)
 plt.xlabel('Hours since 2023-03-21 00:00:02 UTC');plt.ylabel('Density (10^-12 kg/m³)');plt.legend(ncol=3);finish('density')
 fig,ax=plt.subplots(2,1,figsize=(10,6),sharex=True)
 for key in ['S3_A','S7_A','S3_B','S7_B']:
  ax[0].plot(hours,[r[key+'_ratio_to_msis'] for r in rows],label=key);ax[1].plot(hours,[r[key+'_ln_ratio'] for r in rows],label=key)
 ax[0].set_ylabel('TIE / NRLMSIS density');ax[1].set_ylabel('ln(TIE / NRLMSIS)');ax[1].set_xlabel('Elapsed hours');ax[0].legend(ncol=4);finish('ratios')
 plt.figure(figsize=(10,4));names=['south_polar','south_mid','low','north_mid','north_polar']
 for key in ['S3_A','S7_A','S3_B','S7_B']:
  plt.plot(names,[next(r['relative_median_percent'] for r in comparisons if r['mapping_source']==key and r['region']==n) for n in names],marker='o',label=key)
 plt.xlabel('WGS84 latitude region (60°/30° boundaries)');plt.ylabel('Median (TIE/MSIS - 1) (%)');plt.legend();finish('latitude')
 fig,ax=plt.subplots(3,1,figsize=(10,7),sharex=True)
 ax[0].plot(hours,[r['f107_previous_day'] for r in rows],label='Previous day observed F10.7');ax[0].plot(hours,[r['f107a_centered81'] for r in rows],label='Centered 81-day');ax[0].set_ylabel('Solar flux (sfu)');ax[0].legend()
 for j in range(7):ax[1].step(hours,[r[f'ap_{j}'] for r in rows],where='post',label=f'Ap[{j}]')
 ax[1].set_ylabel('Ap input');ax[1].legend(ncol=7,fontsize=7);ax[2].plot(hours,h/1000,label='WGS84 altitude');ax[2].set_ylabel('Height (km)');ax[2].set_xlabel('Elapsed hours');finish('drivers')
 plt.figure(figsize=(9,4));vals=[summaries['60']['batch_wall_s']/361*1000,np.median(latencies['msis_scalar_ms']),read_times['S3']/722*1000,read_times['S7']/722*1000]
 plt.bar(['MSIS batch / point','MSIS scalar median','S3 CSV scan / row','S7 CSV scan / row'],vals);plt.ylabel('Wall time (ms)');plt.xticks(rotation=12);plt.title('Different operations: reuse timings are NOT TIE model runtime');finish('cost')
 # Current raw files unchanged, verification is separate from timed model evaluation.
 assert all(sha(ROOT/p)==v for p,v in protected.items())
 audit={'status':'HINDCAST / TIE COMPARISONS PROVISIONAL','model':'NRLMSIS 2.1','pymsis':pymsis.__version__,'python':platform.python_version(),'versions':{p:importlib.metadata.version(p) for p in ['numpy','scipy','astropy','pymsis']},'driver_sha256':frozen.sha256,'sampling':summaries,'comparison':comparisons,'peaks':peaks,'scalar_latency_ms':stats(latencies['msis_scalar_ms']),'TIE_CSV_reuse_scan_wall_s':read_times,'peak_process_RSS_MiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'total_analysis_wall_s':time.perf_counter()-start,'raw_files_verified':len(protected),'protected_sha256':protected,'eop':eop,'orbit_metadata':orbit.metadata,'new_orbit_integrations':0,'new_TIE_integrations':0,'automatic_weather_retrieval':'patched to fail throughout all model evaluations'}
 (run/'audit.json').write_text(json.dumps(audit,indent=2,default=str)+'\n');print(json.dumps({k:audit[k] for k in ['sampling','comparison','scalar_latency_ms','peak_process_RSS_MiB','total_analysis_wall_s']},indent=2))
if __name__=='__main__':main()
