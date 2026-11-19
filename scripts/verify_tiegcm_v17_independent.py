"""V17 independent read-only verification of actual outputs, no density-error metric."""
from pathlib import Path
import sys,json,re,hashlib,time,resource,datetime,collections
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R)]
import numpy as np,cdflib
from netCDF4 import Dataset,num2date
from astropy.coordinates import EarthLocation
import astropy.units as u
F=R/'experiments/tiegcm_2022_mar25_postrun_acceptance_v17';REVIEW=R/'experiments/tiegcm_2022_mar25_execution_review_v1';RUN=REVIEW/'actual_run';PREP=R/'experiments/tiegcm_2022_mar25_preparation_v1'
def load(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as s:
  for b in iter(lambda:s.read(2**20),b''):h.update(b)
 return h.hexdigest()
def require(ok,reason):
 if not ok:raise ValueError(reason)
def native(v,i):
 v.set_auto_mask(False);a=np.asarray(v[i]);mask=np.zeros(a.shape,bool)
 for key in ['missing_value','_FillValue']:
  if key in v.ncattrs():
   for x in np.asarray(v.getncattr(key)).reshape(-1):mask|=a==np.asarray(x,dtype=a.dtype)
 require(np.isfinite(a).all() and not mask.any() and not (abs(a)>1e30).any(),'Invalid target native field '+v.name)
 return a.astype(float)
def main():
 start=time.perf_counter();cpu=time.process_time();status=load(RUN/'status.json');mainpath=F/'audit_once_local/acceptance.json';main=load(mainpath) if mainpath.exists() else None;audit_status={'returncode':None,'stop_reason':'BATCH_STILL_RUNNING; parent direct-wait status required after completion'};claim=load(REVIEW/'execution_claim_local.json');notes={}
 require(status['returncode']==0 and status['qualification']=='PASS' and status['cleanup_verified'] and not status['gaps'],'Actual supervisor failed')
 require(status['wait_source']=='direct subprocess.Popen.wait','Not actual direct wait')
 events=[json.loads(x) for x in (RUN/'events.jsonl').read_text().splitlines()];wait=[x for x in events if x['event']=='child_wait_final'];require(len(wait)==1 and wait[0]['returncode']==0 and wait[0]['cleanup_verified'],'Wait journal disagrees')
 launched=next(x for x in events if x['event']=='launched');require(launched['identity']==status['identity'],'Launch identity disagrees')
 protocol=load(PREP/'launch_protocol.json');ranks=[]
 for rank in range(4):
  a=load(RUN/f'rank_{rank:03d}_started.json');b=load(RUN/f'rank_{rank:03d}_exit.json');require(b['rank']==rank and b['size']==4 and b['run_id']==claim['run_id'] and all(b[k]==v for k,v in a.items()),'Wrong rank/run identity')
  require(b['returncode']==0 and b['error'] is None and not b['received_signals'] and b['wrapper_sid']==b['child_sid']==status['identity']['sid'],'Rank exit/session failure')
  require(b['model_SHA256']==protocol['executable']['SHA256'] and b['input_SHA256']==protocol['input']['SHA256'],'Rank model/input SHA mismatch')
  text=(RUN/f'rank_{rank:03d}.log').read_text();matches=re.findall(r'^Step\s+(\d+) of\s+(\d+) mtime=\s*(\d+)\s+(\d+)\s+(\d+)',text,re.M);require([int(x[0]) for x in matches]==list(range(10,24481,10)) and all(int(x[1])==24480 for x in matches),'Missing or duplicate progress')
  require(list(map(int,matches[-1][2:]))==[85,0,0] and len(re.findall(r'^NORMAL EXIT\s*$',text,re.M))==1,'Wrong final time or exit log')
  ranks.append(dict(rank=rank,returncode=0,model_pid=b['child_pid'],started_unix=b['started_unix'],ended_unix=b['ended_unix'],receipt_SHA256=sha(RUN/f'rank_{rank:03d}_exit.json')))
 notes['identity']=dict(run_id=claim['run_id'],ranks=ranks,parent_returncode=0,wait_journal_confirmed=True)
 inventory=main['checks']['output_files']['evidence']['files'] if main else [];byname={e['file']:e for e in inventory};primary=[];secondary=[];outputs=[];arrays={};physical=[];native_records=0;driver_max=0.
 with Dataset(PREP/'gpi_2022_extended.nc') as gn:gd=list(gn['year_day'][:]);gf=np.array(gn['f107d'][:]);ga=np.array(gn['f107a'][:]);gk=np.array(gn['kp'][:])
 for kind,count in [('primary',18),('secondary',17)]:
  paths=sorted(RUN.glob(kind+'_*.nc'));require(len(paths)==count,'Wrong volume count')
  for path in paths:
   digest=sha(path)
   if main:require(digest==byname[path.name]['SHA256'],'Independent output SHA differs')
   outputs.append(dict(file=path.name,SHA256=digest,bytes=path.stat().st_size))
   with Dataset(path) as n:
    require(n.history_type==kind and len(n.dimensions['time'])==(1 if kind=='primary' else 24),'Bad volume schema')
    tt=[datetime.datetime(x.year,x.month,x.day,x.hour,x.minute,x.second) for x in num2date(n['time'][:],n['time'].units)];(primary if kind=='primary' else secondary).extend(tt)
    for i,t in enumerate(tt):
     require(int(n['year'][i])==2022 and list(n['mtime'][i])==[int(t.strftime('%j')),t.hour,t.minute],'Independent calendar mismatch')
     if t!=datetime.datetime(2022,3,9):require(int(n['iter'][i])==68*1440+int((t-datetime.datetime(2022,3,9)).total_seconds()/60),'Warm iter mismatch')
     if kind=='secondary':
      require(n['DEN'].dimensions==n['ZG'].dimensions==('time','ilev','lat','lon') and n['DEN'].units=='g/cm3' and n['ZG'].units=='cm','Density native schema mismatch')
      den=native(n['DEN'],i)*1000.;z=native(n['ZG'],i)*.01;require((den>0).all() and (np.diff(z,axis=0)>0).all(),'Nonphysical target fields');native_records+=1
      di=gd.index(int(t.strftime('%Y%j')));seconds=t.hour*3600+t.minute*60;left=di-2 if seconds<43200 else di-1;x=np.array([(left+k-di)*86400+43200 for k in range(4)],float);w=np.array([np.prod([(seconds-x[b])/(x[a]-x[b]) for b in range(4) if b!=a]) for a in range(4)]);kp=float(np.interp(seconds,np.arange(-1,9)*10800+5400,np.r_[gk[di-1,7],gk[di],gk[di+1,0]]));expected=dict(f107d=float(w@gf[left:left+4]),f107a=float(w@ga[left:left+4]),Kp=kp,hpower=16.82*np.exp(.32*kp)-4.86 if kp<=7 else 153.13+(kp-7)/2*(300-153.13),ctpoten=15+15*kp+.8*kp**2)
      for key,value in expected.items():driver_max=max(driver_max,abs(float(native(n[key],i))-value))
      require(driver_max<1e-10,'Independent actual driver mismatch')
      if t>=datetime.datetime(2022,3,25):arrays[t]=(z,den)
      lat=np.asarray(n['lat'][:],float);lon=np.asarray(n['lon'][:],float)
      if t in [datetime.datetime(2022,3,25),datetime.datetime(2022,3,25,1),datetime.datetime(2022,3,25,12),datetime.datetime(2022,3,26)]:physical.append(dict(UTC=t.isoformat()+'Z',DEN_min_kg_m3=float(den.min()),DEN_max_kg_m3=float(den.max()),ZG_min_m=float(z.min()),ZG_max_m=float(z.max()),values=len(den.ravel()),all_finite_positive_DEN=True,ZG_monotonic=True))
 require(primary==[datetime.datetime(2022,3,9)+datetime.timedelta(days=i) for i in range(18)],'Independent primary time series incomplete')
 require(secondary==[datetime.datetime(2022,3,9)+datetime.timedelta(hours=i) for i in range(1,409)],'Independent secondary time series incomplete');require(len(arrays)==25,'Target day boundary absent')
 require(native_records==408,'Full warm native scan incomplete')
 notes['all_warm_native_checks']=dict(records=408,DEN_ZG_fills_nonfinite_nonpositive=0,ZG_nonmonotonic=0,actual_GPI_max_abs_difference=driver_max,tolerance=1e-10,source='independent raw arrays, not main PASS field')
 notes['outputs']=dict(primary_records=len(primary),secondary_records=len(secondary),volumes=len(outputs),final_UTC=secondary[-1].isoformat()+'Z',all_SHA256=outputs,physical_fixed_samples=physical)
 obs=load(PREP/'observation_acquisition_audit.json')
 for key in ['ZIP','CDF','HDR','hapi']:
  e=obs[key];require(sha(R/e['path'])==e['SHA256'],'Original observation asset SHA changed')
 with cdflib.CDF(R/obs['CDF']['path']) as c:
  utc=cdflib.cdfepoch.to_datetime(c.varget('time'));rho=np.asarray(c.varget('density'));flags=np.asarray(c.varget('validity_flag'));olat=np.asarray(c.varget('latitude'));olon=np.asarray(c.varget('longitude'));alt=np.asarray(c.varget('altitude'));require(c.varattsget('density')['UNITS']=='kg/m3','Observation density units changed')
 quality=(flags==0)&np.isfinite(rho)&(rho>0)&(rho<1e30)&np.isfinite(olat)&(abs(olat)<=90)&np.isfinite(olon)&(abs(olon)<=180)&np.isfinite(alt)&(alt>0)
 require(len(utc)==2880 and quality.sum()==2880 and np.all(np.diff(utc)==np.timedelta64(30,'s')),'Observation records/quality changed')
 # Independently reconstruct provisional Map-A via explicit GRS80->same XYZ->WGS84.
 location=EarthLocation.from_geodetic(olon*u.deg,olat*u.deg,alt*u.m,ellipsoid='GRS80');geo=location.to_geodetic(ellipsoid='WGS84');mlat=geo.lat.to_value(u.deg);mlon=geo.lon.to_value(u.deg);height=geo.height.to_value(u.m)
 stackz=np.stack([arrays[datetime.datetime(2022,3,25)+datetime.timedelta(hours=i)][0] for i in range(25)]);stackr=np.stack([arrays[datetime.datetime(2022,3,25)+datetime.timedelta(hours=i)][1] for i in range(25)]);success=0;reasons=collections.Counter();nr=0
 for index in np.flatnonzero(quality):
  h=float((utc[index]-np.datetime64('2022-03-25T00'))/np.timedelta64(1,'h'))
  if not 0<=h<24:reasons['TIME_OUTSIDE']+=1;continue
  if not lat[0]<=mlat[index]<=lat[-1]:reasons['LAT_OUTSIDE_NATIVE_CENTER']+=1;continue
  k=int(np.floor(h));j=min(max(int(np.searchsorted(lat,mlat[index],side='right'))-1,0),len(lat)-2);x=(mlon[index]-lon[0])%360+lon[0];i=int(np.searchsorted(lon,x,side='right'))-1;i2=(i+1)%len(lon);right=lon[i2] if i2 else lon[0]+360
  weights_t=[1-(h-k),h-k];wy=(mlat[index]-lat[j])/(lat[j+1]-lat[j]);wx=(x-lon[i])/(right-lon[i]);value=0.;valid=True
  for a in [0,1]:
   for b in [0,1]:
    for cc,ii in enumerate([i,i2]):
     zz=stackz[k+a,:,j+b,ii];rr=stackr[k+a,:,j+b,ii];nr+=1
     if not (np.isfinite(zz).all() and np.isfinite(rr).all() and (rr>0).all() and (np.diff(zz)>0).all() and zz[0]<=height[index]<=zz[-1]):valid=False;continue
     value+=weights_t[a]*[1-wy,wy][b]*[1-wx,wx][cc]*np.exp(np.interp(height[index],zz,np.log(rr)))
  if valid and np.isfinite(value) and value>0:success+=1
  else:reasons['INVALID_COLUMN_OR_VERTICAL_OUTSIDE']+=1
 require(success==int(quality.sum()),'Independent target-day coverage incomplete: '+json.dumps(dict(reasons)))
 qmain=main['checks']['target_observation_queries']['evidence'] if main else None
 if qmain:require(qmain['eligible']==int(quality.sum()) and qmain['success']==success and qmain['failed']==0,'Main/independent query counts disagree')
 notes['independent_queries']=dict(method='Independent neighbor/time/vertical eight-column reconstruction; unchanged explicit Map-A assumption, no density-error calculation',N_total=len(utc),N_eligible=int(quality.sum()),N_success=success,N_failure=int(quality.sum())-success,reason_counts=dict(reasons),column_checks=nr,zero_weight_columns_not_skipped=True,no_extrapolation=True,comparison_to_main_counts='MATCH' if qmain else 'NOT_AVAILABLE_MAIN_AUDIT_INTERRUPTED',identity='PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED')
 # Original frozen inputs and all pre-existing public scientific assets are unchanged.
 for item in [protocol['input'],protocol['GPI'],protocol['executable']]:require(sha(R/item['path'])==item['SHA256'],'Frozen input changed')
 mm=load(PREP/'model_configuration_manifest.json')
 for name,digest in mm['verified_assets'].items():require(sha(R/name)==digest,'Original model/support source changed')
 protected=load(F/'protected_assets_local.json')
 for name,digest in protected.items():require(sha(R/name)==digest,'Historical tracked asset changed')
 notes['historical_assets_unchanged']=len(protected);notes['main_engineering_acceptance']=main['overall'] if main else 'INCOMPLETE_CONTROLLED_STOP';notes['main_audit_returncode']=audit_status['returncode'];notes['main_audit_stop_reason']=audit_status['stop_reason'];notes['V16_ORIGINAL_ENGINEERING_STATUS']='FAIL';notes['model_launches_this_task']=0;notes['independent_check_not_second_main_audit']=True
 require(len({x['model_pid'] for x in ranks})==4,'Model child PID identity not unique')
 notes.update(PASS=True,overall='ENGINEERING_PASS' if main and main['overall']=='PASS' else 'ENGINEERING_FAIL',independent_physical_data_checks='PASS',complete_engineering_acceptance=False if main is None else main['overall']=='PASS',ACTUAL_MODEL_RUN='COMPLETED',model_launches=1,automatic_retry=0,density_error_metrics=0,correction_fits=0,wall_s=time.perf_counter()-start,CPU_s=time.process_time()-cpu,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
 with (F/'independent_verification.json').open('x') as s:json.dump(notes,s,indent=2,allow_nan=False);s.write('\n')
 print(json.dumps({k:notes[k] for k in ['PASS','overall','ACTUAL_MODEL_RUN','wall_s','CPU_s','peak_RSS_MiB']}))
if __name__=='__main__':main()
