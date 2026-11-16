"""Independent acquisition/quality/coverage audit. No correction or observed-model errors."""
from pathlib import Path
import sys,json,csv,time,resource,zipfile,zlib,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np,cdflib
from netCDF4 import Dataset
from observations.bounded_swarm_acquisition import sha,posix_cksum
F=ROOT/'experiments/causal_density_latitude_acquisition_v1'
def main():
 start=time.perf_counter();download=json.loads((F/'download_manifest.json').read_text());quality=list(csv.DictReader((F/'quality_audit.csv').open()));counts=list(csv.DictReader((F/'latitude_window_counts.csv').open()));model=list(csv.DictReader((F/'model_coverage.csv').open()));ma=json.loads((F/'model_query_audit.json').read_text());files=[];cdfrecords=0
 assert len(download['products'])==2 and download['actual_network_body_bytes']==279668 and download['verified_extracted_bytes']==388878
 for product in download['products']:
  p=ROOT/product['path'];assert sha(p)==product['SHA256'] and p.stat().st_size==product['bytes'];assert product['HTTP']==200 and product['bytes']==product['Content_Length']
  with zipfile.ZipFile(p) as z:
   assert z.testzip() is None and len(z.infolist())==2
   for entry in product['extracted_members']:
    pp=ROOT/entry['path'];assert sha(pp)==entry['SHA256'];assert z.read(pp.name)==pp.read_bytes();assert f'{zlib.crc32(pp.read_bytes()):08x}'==entry['CRC32'];files.append(dict(path=entry['path'],SHA256=entry['SHA256'],ZIP_CRC32=entry['CRC32']))
  y=str(product['year']);cdf=ROOT/next(x['path'] for x in product['extracted_members'] if x['path'].endswith('.cdf'))
  with cdflib.CDF(cdf) as c:
   t=cdflib.cdfepoch.to_datetime(c.varget('time'));rho=c.varget('density');flag=c.varget('validity_flag');lat=c.varget('latitude');lon=c.varget('longitude');h=c.varget('altitude');assert c.varinq('time').Data_Type==31
  assert len(t)==2880 and np.all(np.diff(t)==np.timedelta64(30,'s')) and t[0]==np.datetime64(y+'-03-23') and t[-1]==np.datetime64(y+'-03-23T23:59:30');mask=(flag==0)&np.isfinite(rho)&(rho>0)&(rho<1e30)&np.isfinite(lat)&np.isfinite(lon)&np.isfinite(h)&(abs(lat)<=90)&(abs(lon)<=180)&(h>0)&(h<2e6)
  row=next(x for x in quality if x['year']==y);assert mask.sum()==int(row['valid_samples']) and (flag==0).sum()==int(row['flag0']);cdfrecords+=len(t)
  hour=(t-np.datetime64(y+'-03-23'))/np.timedelta64(1,'h');windows={'history15_18':(hour>=15)&(hour<18),'future18_19':(hour>=18)&(hour<19),'future18_21':(hour>=18)&(hour<21),'future18_24':(hour>=18)&(hour<24)};regions={'all':np.ones(len(t),bool),'low':abs(lat)<30,'mid':(abs(lat)>=30)&(abs(lat)<60),'high':abs(lat)>=60}
  for r in counts:
   if r['year']==y:assert int(r['valid_N'])==int((mask&windows[r['window']]&regions[r['region']]).sum())
  external=subprocess.check_output(['cksum',str(cdf)],text=True).split();posix,n=posix_cksum(cdf);assert posix==int(external[0]) and n==int(external[1])
 trace_count=0;eight=0;reconstructed=0;lookup={(x['year'],x['case']):x for x in ma['cases']}
 with (F/'model_queries_local.jsonl').open() as stream:
  for line in stream:
   x=json.loads(line);trace_count+=1;assert x['valid'] and x['reason']=='';m=x['metadata'];assert len(m['columns'])==8;eight+=1;assert x['coordinate']['status']=='PROVISIONAL';t=np.datetime64(x['UTC'][:-1]);assert np.datetime64(m['time_utc'][0])<=t<=np.datetime64(m['time_utc'][1]);assert 0<=m['weights']['time']<=1
   if x['index'] not in [1800,2160,2879]:continue
   vals=[];folder=ROOT/lookup[(x['year'],x['case'])]['folder'];height=x['coordinate']['model_zg_m']
   for col in m['columns']:
    with Dataset(folder/col['file']) as n:
     z=np.asarray(n['ZG'][col['record'],:,col['lat_index'],col['lon_index']],float)*.01;r=np.asarray(n['DEN'][col['record'],:,col['lat_index'],col['lon_index']],float)*1000;assert z[0]<=height<=z[-1] and (np.diff(z)>0).all();vals.append(np.exp(np.interp(height,z,np.log(r))))
   w=m['weights'];ww=np.array([1-w['time'],w['time']])[:,None,None]*np.array([1-w['latitude'],w['latitude']])[None,:,None]*np.array([1-w['longitude'],w['longitude']])[None,None,:];direct=float(np.sum(ww*np.array(vals).reshape(2,2,2)));assert np.isclose(direct,x['model_density_kg_m3'],rtol=1e-13,atol=0);reconstructed+=1
 assert trace_count==6480 and eight==6480 and reconstructed==18
 assert len(model)==6 and all(r['status']=='PASS' and r['static_target_frames']=='10' and r['successful']=='1080' and r['failed']=='0' for r in model)
 for n,h in json.loads((F/'input_protection.json').read_text())['protected'].items():assert sha(ROOT/n)==h,n
 for n,h in ma['NetCDF_input_SHA256'].items():assert sha(ROOT/n)==h,n
 assert not (F/'correction_parameters.json').exists() and not (F/'metrics.csv').exists() and not (F/'joint_assessment.csv').exists()
 out=dict(PASS=True,independent_CDF_records=cdfrecords,CRC_and_SHA_member_checks=files,actual_downloads=2,network_bytes=279668,extract_bytes=388878,model_trace_queries=trace_count,eight_column_PASS=eight,native_density_reconstruction_probes=reconstructed,all_model_cases_PASS=6,old_blocked_audit_unchanged=True,correction_fits=0,prediction_errors=0,joint_assessments=0,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
 with (F/('supervised_independent_verification.json' if '--supervised-confirmation' in sys.argv else 'independent_verification.json')).open('x') as f:json.dump(out,f,indent=2)
 print('INDEPENDENT ACQUISITION/COVERAGE PASS',cdfrecords,trace_count,reconstructed,flush=True)
if __name__=='__main__':main()
