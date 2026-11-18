"""Independent V14-B CPU verification: no model launch and no density scoring."""
from pathlib import Path
import json,hashlib,sys,datetime,math,time,subprocess,re,resource
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R)]
import numpy as np,cdflib
from netCDF4 import Dataset
F=R/'experiments/tiegcm_2022_mar25_preparation_v1'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def load(n):return json.loads((F/n).read_text())
def main():
 start=time.perf_counter();cpu=time.process_time();a=load('observation_acquisition_audit.json');assert a['PASS'] and a['ZIP']['CRC_test_PASS']
 for e in [a['ZIP'],a['CDF'],a['HDR']]:assert sha(R/e['path'])==e['SHA256']
 with cdflib.CDF(R/a['CDF']['path']) as c:
  t=cdflib.cdfepoch.to_datetime(c.varget('time'));d=c.varget('density');fl=c.varget('validity_flag');lat=c.varget('latitude');lon=c.varget('longitude');alt=c.varget('altitude')
  assert len(t)==2880 and t[0]==np.datetime64('2022-03-25T00') and t[-1]==np.datetime64('2022-03-25T23:59:30') and np.all(np.diff(t)==np.timedelta64(30,'s'));assert np.all(fl==0) and np.all(np.isfinite(d)&(d>0)) and np.all(np.isfinite(lat)&(abs(lat)<=90)) and np.all(np.isfinite(lon)&(abs(lon)<=180)) and np.all(np.isfinite(alt)&(alt>0));assert c.varattsget('density')['UNITS']=='kg/m3'
 raw=load('driver_source_audit.json');maps={'Fobs':{},'Kp':{}}
 for e in raw['sources']:
  p=R/e['path'];assert sha(p)==e['SHA256'];x=json.loads(p.read_text());key=e['key'];ts=x['datetime'];assert len(set(ts))==len(ts)
  if key=='Kp':assert x['status']==['def']*len(ts)
  for t,v in zip(ts,x[key]):
   tt=datetime.datetime.fromisoformat(t.replace('Z','+00:00'));assert tt.utcoffset()==datetime.timedelta(0) and tt not in maps[key];maps[key][tt]=float(v)
 with Dataset(F/'gpi_2022_extended.nc') as n,Dataset(R/'data/processed/tiegcm_2022_spinup_14day_v1/gpi_2022_14day.nc') as old:
  days=np.asarray(n['year_day'][:]);assert len(days)==22 and n['kp'].shape==(22,8) and n.data_model=='NETCDF3_CLASSIC';meanerr=0
  for i,day in enumerate(days):
   t=datetime.datetime.strptime(str(int(day)),'%Y%j').replace(tzinfo=datetime.timezone.utc);assert float(n['f107d'][i])==maps['Fobs'][t];mean=math.fsum(maps['Fobs'][t+datetime.timedelta(days=j)] for j in range(-40,41))/81;meanerr=max(meanerr,abs(mean-float(n['f107a'][i])));assert meanerr<1e-12
   for k in range(8):assert float(n['kp'][i,k])==maps['Kp'][t+datetime.timedelta(hours=3*k)]
  for j,day in enumerate(old['year_day'][:]):
   i=list(days).index(day)
   for k in ['f107d','f107a','kp']:np.testing.assert_array_equal(n[k][i],old[k][j])
 m=load('model_configuration_manifest.json')
 for p,h in m['verified_assets'].items():assert sha(R/p)==h,p
 for k in ['old_input','new_input','old_run_status','old_data_audit']:e=m[k];assert sha(R/e['path'])==e['SHA256']
 old=(R/m['old_input']['path']).read_text();new=(R/m['new_input']['path']).read_text();entries=lambda txt:dict((x.strip().split('=')[0].strip(),x.strip().split('=',1)[1].strip()) for x in txt.splitlines() if '=' in x)
 oldc,newc=entries(old),entries(new);changes={k for k in oldc if oldc[k]!=newc[k]};assert changes=={'STOP','SECSTOP','OUTPUT','SECOUT','GPI_NCFILE'};assert newc['STOP']=='85 0 0' and newc['START']=='68 0 0' and newc['SOURCE_START']=='80 0 0';assert len(re.findall(r'primary_\d{3}\.nc',newc['OUTPUT']))==18 and len(re.findall(r'secondary_\d{3}\.nc',newc['SECOUT']))==17
 # Independently read SOURCE record and compare current/previous masks with recorded source audit.
 source=next(p for p in m['verified_assets'] if p.endswith('mareqx_smax_prim.nc'));sa=load('initial_state_audit.json');assert len(sa['required_native_fields'])==34
 with Dataset(R/source) as n:
  np.testing.assert_array_equal(n['mtime'][:],[[80,0,0]]);np.testing.assert_array_equal(n['year'][:],[2002])
  for name,e in sa['required_native_fields'].items():v=n[name][:];assert np.isfinite(v.compressed()).all() and v.count()>0 and int(np.ma.getmaskarray(v).sum())==e['native_masked']
 e=load('environment_audit.json');assert e['PASS'] and e['MPI_python_probe']['returncode']==0 and e['termination_helper']['cleanup_verified'];assert not list((F/'run').glob('*.nc')) and not (F/'run/launch_once.json').exists()
 guard=subprocess.run([sys.executable,str(R/'scripts/execute_tiegcm_2022_mar25_v1.py')],capture_output=True,text=True);assert guard.returncode==2 and 'authorization' in guard.stderr and not (F/'run/launch_once.json').exists()
 p=load('frozen_evaluation_protocol.json');assert p['no_evaluation_or_fitting_this_task'] and p['min_history_and_future_region_N']==30 and p['history_hours']==3 and p['future_hours']==[1,3,6] and p['future_poison_factor']==1e20
 protected=load('protected_assets_local.json')
 for p,h in protected.items():assert sha(R/p)==h,p
 # Model files were rehashed against their original full audit before readiness, no write.
 for item in json.loads((R/'experiments/tiegcm_2022_b14_exploratory_pair_v2/B14/data_audit.json').read_text())['files']:assert sha(R/'experiments/tiegcm_2022_b14_exploratory_pair_v2/B14'/item['file'])==item['SHA256']
 result=dict(PASS=True,raw_observation_independent=True,raw_drivers_independent=True,mean_max_abs=meanerr,Kp_independent_buckets=176,common_raw_arrays_exact=True,configuration_changed_keys=sorted(changes),source_34_fields=True,old_protected_files=len(protected),old_NetCDF_original_SHA_verified=True,future_launcher_unauthorized_refusal=True,new_model_launches=0,actual_target_queries='NOT_RUN_MODEL_OUTPUT_NOT_YET_CREATED',fitting=0,metrics=0,wall_s=time.perf_counter()-start,CPU_s=time.process_time()-cpu,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
 with (F/'independent_verification.json').open('x') as s:json.dump(result,s,indent=2);s.write('\n')
 print('Independent V14-B verification PASS; no model launch, fits or metrics.')
if __name__=='__main__':main()
