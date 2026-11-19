"""Limited autumn acquisition and static admission; no model/GPI/density scoring."""
from pathlib import Path
import sys,os,json,csv,time,datetime,resource,hashlib,zipfile,zlib,subprocess,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R),str(R/'src'),str(R/'scripts')]
import numpy as np,cdflib
from netCDF4 import Dataset
from observations.autumn_acquisition import Meter,bounded_get
from observations.bounded_swarm_acquisition import Budget,archive_plan,extract_members,posix_cksum,sha,inside
from observations.autumn_validation import check_product_stem,check_times,quality_counts,inspect_initial
from observations.density_catalog import read_swarm_pod
from evaluation.independent_date_planning import kp_class
from atmosphere.restart_validation import REQUIRED
from prepare_tiegcm_training_drivers import decode
F=R/'experiments/thermosphere_autumn_data_acquisition_v21';D=R/'data/raw/thermosphere_autumn_data_acquisition_v21';V20=R/'experiments/thermosphere_independent_date_validation_plan_v20'
def load(p):return json.loads(Path(p).read_text())
def plain(v):
 if isinstance(v,np.ndarray):return v.tolist()
 if isinstance(v,np.generic):return v.item()
 if isinstance(v,dict):return {k:plain(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [plain(x) for x in v]
 return v
def put(n,x):
 p=inside(F/n)
 with p.open('x') as f:json.dump(plain(x),f,indent=2,allow_nan=False)
def table(n,rr):
 with inside(F/n).open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rr[0]),lineterminator='\n');w.writeheader();w.writerows(rr)
def entry(p):return dict(path=str(p.relative_to(R)),SHA256=sha(p),bytes=p.stat().st_size)
def same(p,h):
 if sha(p)!=h:raise ValueError('Frozen input SHA mismatch')
def safe_error(e):
 text=str(e)
 for key in ['HTTPS_PROXY','HTTP_PROXY']:
  host=__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(os.environ.get(key,'')).hostname
  if host:text=text.replace(host,'[existing proxy]')
 return dict(error_type=type(e).__name__,reason=text.replace(str(R),'[project]'))

def main():
 started=time.perf_counter();cpu=time.process_time();assert load(F/'tests.json')['PASS'];req=load(V20/'next_acquisition_request_final.json');same(V20/'preregistered_protocol.json',load(V20/'protocol_sha256.json')['SHA256']);protected=load(F/'preflight.json')['protected_SHA256']
 for n,h in protected.items():same(R/n,h)
 if (F/'acquisition_once_local.json').exists():raise FileExistsError('Acquisition already attempted; no automatic retry')
 put('acquisition_once_local.json',dict(started_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),allowed_dates=req['dates'],formal_physical_model_calls=0));inside(D).mkdir(exist_ok=False)
 assert subprocess.run(['git','check-ignore','-q',str(D/'anything.nc')]).returncode==0
 meter=Meter();receipts=[];assets={};failures=[];extract_budget=Budget();zip_charge=0
 def charge_zip(p,passes):
  nonlocal zip_charge
  with zipfile.ZipFile(p) as z:n=sum(x.file_size for x in z.infolist())
  if n<0 or zip_charge+n*passes>2*2**20:raise ValueError('Aggregate real ZIP verification/decompression budget would exceed2MiB')
  zip_charge+=n*passes
 def acquire(key,url,name,group,expected=None,magic=None):
  marker=F/(key+'_attempt_local.json');put(marker.name,dict(URL=url,one_attempt=True));p=D/name
  try:
   value=bounded_get(url,p,meter,group,receipts,expected_bytes=expected,magic=magic,max_body=(20*2**20 if group=='initial' else 2**20));assets[key]=value;print(json.dumps(dict(event='V21_ASSET_RECEIVED',asset=key,body_bytes=value['bytes'])),flush=True);return p
  except Exception as e:
   failures.append(dict(asset=key,stage='download',**safe_error(e)));print(json.dumps(dict(event='V21_ASSET_NOT_ACQUIRED',asset=key,exception_type=type(e).__name__)),flush=True);return None
  finally:
   put(key+'_http_receipt.json',dict(asset=key,requests=[r for r in receipts if r['original_URL']==url],meter_snapshot=meter.summary()))
 obs={};qualityrows=[];windows=[];contracts=[]
 hapi=load(R/'experiments/tiegcm_2022_mar25_preparation_v1/observation_acquisition_audit.json')['hapi'];same(R/hapi['path'],hapi['SHA256'])
 for request in req['Swarm']:
  day=request['date'];year=day[:4];stem=Path(request['product']).stem;p=acquire('Swarm'+year,request['official_download_URL'],request['product'],'small',int(request['cached_bytes']),[b'PK\x03\x04'])
  if p is None:continue
  try:
   check_product_stem(stem,day);charge_zip(p,1);plan=archive_plan(p,stem,2*2**20-extract_budget.extracted_bytes);charge_zip(p,2);members=extract_members(p,stem,extract_budget,D);cp=D/(stem+'.cdf');hp=D/(stem+'.HDR');_,a,con=read_swarm_pod(cp,R/hapi['path'],sha(cp),satellite='A');check_times(a['utc'],day);q,counts=quality_counts(a)
   if not np.array_equal(q,a['quality']):raise ValueError('Existing quality_mask and direct quality differ')
   with cdflib.CDF(cp) as c:
    if c.varinq('time').Data_Type!=31 or con['global_attributes']['TIME SYSTEM']!=['UTC']:raise ValueError('Wrong CDF_EPOCH or UTC')
    for k,u in [('density','kg/m3'),('latitude','deg'),('longitude','deg'),('altitude','m')]:
     if con['variables'][k]['UNITS']!=u:raise ValueError('Observation unit mismatch')
   header=ET.parse(hp).getroot();fix=header.find('Fixed_Header')
   for k,v in [('File_Name',stem),('Mission','Swarm'),('File_Type','DNSAPOD_2_'),('File_Version','0301')]:
    if fix.findtext(k)!=v:raise ValueError('HDR identity mismatch')
   if fix.findtext('Validity_Period/Validity_Start')!='UTC='+day+'T00:00:00' or fix.findtext('Validity_Period/Validity_Stop')!='UTC='+day+'T23:59:30':raise ValueError('HDR UTC mismatch')
   crc,n=posix_cksum(cp)
   if crc!=int(header.findtext('Variable_Header/MPH/CRC')) or n!=int(header.findtext('Variable_Header/MPH/Tot_Size')):raise ValueError('HDR POSIX checksum/length mismatch')
   countrow=dict(date=day,**counts,UTC_first=str(a['utc'][0]),UTC_last=str(a['utc'][-1]),cadence_s=30,source_SHA256=sha(cp),HDR_POSIX_CRC=crc);qualityrows.append(countrow)
   bands=np.where(abs(a['latitude'])<30,0,np.where(abs(a['latitude'])<60,1,2));minsupport=True
   for h in [6,18]:
    cut=np.datetime64(day+f'T{h:02d}');mask={'history':(a['utc']>=cut-np.timedelta64(3,'h'))&(a['utc']<cut)}
    for lead in [1,3,6]:mask[f'future_{lead}h']=(a['utc']>=cut)&(a['utc']<cut+np.timedelta64(lead,'h'))
    for name,m in mask.items():
     for reg,select in [('all',np.ones(len(q),bool)),('low',bands==0),('mid',bands==1),('high',bands==2)]:
      raw=int((m&select).sum());good=int((m&select&q).sum());support=good>=30;minsupport&=support;windows.append(dict(date=day,cutoff=h,window=name,region=reg,records=raw,quality_valid=good,invalid=raw-good,N30_supported=support,common_UTC_SHA256=hashlib.sha256(a['utc'][m&select&q].astype('<i8').tobytes()).hexdigest()))
   obs[year]=dict(PASS=True,CDF=entry(cp),ZIP=entry(p),HDR=entry(hp),archive_members=plan,extraction=members,quality=counts,all_windows_regions_N30=bool(minsupport),all_target_records_quality_valid=bool(q.all()),density_values_only_used_for_quality=True,no_density_distribution_or_residual_calculated=True)
   contracts.append(dict(date=day,satellite='Swarm A via DNSAPOD identifier and HDR',version='0301',title=con['global_attributes']['TITLE'],time_system='UTC',time_type='CDF_EPOCH',units={k:con['variables'][k]['UNITS'] for k in ['density','latitude','longitude','altitude']},coordinate_reference='GRS80 per SHA-verified existing HAPI product contract',hapi=hapi,instantaneous_field='density',density_orbitmean_used=False))
  except Exception as e:failures.append(dict(asset='Swarm'+year,stage='CDF_HDR_quality',**safe_error(e)))
  print(json.dumps(dict(event='V21_OBSERVATION_STATIC_CHECK_FINISHED',year=year,contract_complete=year in obs)),flush=True)
 if qualityrows:table('Swarm_quality.csv',qualityrows)
 if windows:table('Swarm_window_latitude_counts.csv',windows)
 put('Swarm_contracts.json',contracts);put('Swarm_audit.json',obs)
 # The two GFZ responses are the only new driver acquisitions. Existing2021 archive is reused.
 fpath=acquire('GFZ_Fobs',req['GFZ2022']['Fobs_URL'],'GFZ_Fobs_20220729_20221106.json','small')
 kpath=acquire('GFZ_Kp',req['GFZ2022']['Kp_URL'],'GFZ_Kp_def_20220907_20220927.json','small')
 # Report exact raw response gaps even when the strict original decoder refuses the file.
 rawcontracts={}
 for name,path,index,start,count,step_hours in [('Fobs',fpath,'Fobs','2022-07-29T00:00:00',101,24),('Kp',kpath,'Kp','2022-09-07T00:00:00',168,3)]:
  expected=[(datetime.datetime.fromisoformat(start)+datetime.timedelta(hours=i*step_hours)).isoformat()+'Z' for i in range(count)]
  if path is None:rawcontracts[name]=dict(PASS=False,missing_UTC=expected,reason='NOT_ACQUIRED');continue
  try:
   x=load(path);times=x.get('datetime',[]);values=x.get(index,[]);invalid=[]
   for i,t in enumerate(times):
    try:
     v=float(values[i]);ok=np.isfinite(v) and (v>0 if index=='Fobs' else 0<=v<=9 and x.get('status',[])[i]=='def')
    except Exception:ok=False
    if not ok:invalid.append(t)
   missing=sorted(set(expected)-set(times));extra=sorted(set(times)-set(expected));duplicates=len(times)-len(set(times));rawcontracts[name]=dict(PASS=not missing and not extra and not invalid and not duplicates and len(values)==len(times),actual_records=len(times),required_records=count,missing_UTC=missing,extra_UTC=extra,invalid_UTC=invalid,duplicate_count=duplicates,source=entry(path))
  except Exception as e:rawcontracts[name]=dict(PASS=False,**safe_error(e),missing_UTC=expected,reason_scope='No valid authorized response schema')
 put('GFZ2022_raw_contract_audit.json',rawcontracts)
 driver={};means=[];activity=[]
 for year in [2021,2022]:
  try:
   if year==2021:
    src=load(V20/'driver_source_inventory.json')['sources'][0];p=R/src['path'];same(p,src['SHA256']);solar={};kp={}
    for line in p.read_text().splitlines():
     row=line.split()
     if not row or row[0]!='2021':continue
     d=datetime.date(*map(int,row[:3]));solar[d]=float(row[25])
     for j in range(8):kp[datetime.datetime.combine(d,datetime.time(j*3))]=(float(row[7+j]),'def' if row[27]=='2' else 'not_def')
    source_refs=[entry(p)]
   else:
    if fpath is None or kpath is None:raise ValueError('Missing authorized GFZ response')
    sf=decode(load(fpath),'Fobs');kk=decode(load(kpath),'Kp');solar={k.date():v for k,v in sf.items()};kp={k.replace(tzinfo=None):(v,'def') for k,v in kk.items()};source_refs=[entry(fpath),entry(kpath)]
   lo=datetime.date(year,7,29);hi=datetime.date(year,11,6);needsolar=[lo+datetime.timedelta(days=j) for j in range(101)];rawlo=datetime.date(year,9,7);needkp=[datetime.datetime.combine(rawlo+datetime.timedelta(days=j),datetime.time(h)) for j in range(21) for h in range(0,24,3)]
   missing_s=[str(d) for d in needsolar if d not in solar or not np.isfinite(solar[d]) or solar[d]<=0];missing_k=[t.isoformat() for t in needkp if t not in kp or kp[t][1]!='def' or not np.isfinite(kp[t][0]) or not 0<=kp[t][0]<=9]
   if year==2022 and (set(solar)!=set(needsolar) or set(kp)!=set(needkp)):raise ValueError('GFZ actual response date coverage/extra records mismatch')
   if missing_s or missing_k:driver[str(year)]=dict(PASS=False,missing_Fobs=missing_s,missing_Kp=missing_k,sources=source_refs);continue
   for j in range(21):
    d=rawlo+datetime.timedelta(days=j);vv=[solar[d+datetime.timedelta(days=i)] for i in range(-40,41)];avg=float(np.mean(vv));diff=abs(avg-__import__('math').fsum(vv)/81)
    if diff>=1e-12:raise ValueError('Original centered81 independent sum differs')
    means.append(dict(year=year,GPI_support_day=str(d),source_count=81,center81_mean_sfu=avg,fsum_difference=diff,valid=True,formal_GPI_generated=False))
   day=datetime.date(year,9,23);flux=solar[day];avg=float(np.mean([solar[day+datetime.timedelta(days=i)] for i in range(-40,41)]));bins=[kp[datetime.datetime.combine(day,datetime.time(h))][0] for h in range(0,24,3)];label=kp_class(bins,['def']*8);activity.append(dict(date=str(day),Fobs_sfu=flux,Fobs_center81_sfu=avg,Kp_max=max(bins),def_Kp_bins=8,geomagnetic_class=label,between_activity_group_comparison='N/A_INSUFFICIENT_DISTINCT_DATES_PER_CATEGORY',thresholds_unchanged=True))
   driver[str(year)]=dict(PASS=True,Fobs_count=101,Kp_count=168,GPI_support_days=21,missing_Fobs=[],missing_Kp=[],sources=source_refs,center81_complete=True,formal_GPI_generated=False,definition='historical observed Fobs, centered81/+40future, defKp; HINDCAST not available forecast forcing')
  except Exception as e:driver[str(year)]=dict(PASS=False,**safe_error(e));failures.append(dict(asset='driver'+str(year),stage='completeness',**safe_error(e)))
 if means:table('center81_static_check.csv',means)
 if activity:table('activity_conditions.csv',activity)
 put('driver_completeness.json',driver)
 initial_path=acquire('initial',req['initial_candidate']['URL'],req['initial_candidate']['file'],'initial',magic=[b'CDF\x01',b'CDF\x02',b'CDF\x05',b'\x89HDF\r\n\x1a\n']);initial=None
 if initial_path is not None:
  try:
   with Dataset(initial_path) as n:
    n.set_auto_mask(False);pre=dict(**entry(initial_path),format=n.data_model,history_type=getattr(n,'history_type',''),variables=list(n.variables),mtime=np.asarray(n['mtime'][:]).tolist() if 'mtime' in n.variables else None,year=np.asarray(n['year'][:]).tolist() if 'year' in n.variables else None,missing_required=[k for k in REQUIRED if k not in n.variables])
   put('initial_preliminary_metadata.json',pre)
   old=R/'data/raw/tiegcm_2021_spinup_initial_condition_v1/tiegcm_res5.0_mareqx_smax_prim.nc';same(old,'a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7');initial=inspect_initial(initial_path,old);initial['file']=entry(initial_path);put('initial_full_state_audit.json',initial)
  except Exception as e:failures.append(dict(asset='initial',stage='full_primary_static',**safe_error(e)))
 # Independent readers consume originals, not the first validator's PASS flags.
 from verify_autumn_data_v21 import verify
 independent=verify(D,F,assets,zip_charge);zip_charge=independent.pop('ZIP_upper_bound_bytes_charged');put('independent_verification.json',independent)
 admissions=[]
 for year in ['2021','2022']:
  goodobs=year in obs and obs[year]['all_windows_regions_N30'] and obs[year]['all_target_records_quality_valid'];gooddriver=driver.get(year,{}).get('PASS',False);goodinitial=initial is not None and independent.get('initial',{}).get('PASS',False);ind=independent.get('observations',{}).get(year,{}).get('PASS',False) and independent.get('drivers',{}).get(year,{}).get('PASS',False)
  status='DATA_READY_SEED_POLICY_PENDING' if goodobs and gooddriver and goodinitial and ind else 'DATA_PARTIAL'
  if initial_path is not None and initial is None:status='BLOCKED'
  admissions.append(dict(year=int(year),date=year+'-09-23',Swarm_original_acquired=year in obs,Swarm_protocol_support=goodobs,GFZ_complete=gooddriver,seasonal_source_engineering_compatible=goodinitial,independent_original_checks_PASS=ind,seed_policy_approved=False,physical_config_written=False,can_prepare16day_config_after_policy=bool(goodobs and gooddriver and goodinitial and ind),status=status,actual_model_RUN_READY=False,reason='Policy A/B requires user decision; newGPI/config/launch not authorized' if status=='DATA_READY_SEED_POLICY_PENDING' else 'See actual missing/invalid evidence; no substitution or retry'))
 table('admission_by_year.csv',admissions);put('download_manifest.json',assets);put('failures.json',failures);put('network_budget_audit.json',meter.summary());put('ZIP_budget_audit.json',dict(limit_bytes=2*2**20,unique_extracted_member_bytes=extract_budget.extracted_bytes,verification_and_extraction_decompressed_upper_bound_bytes=zip_charge,includes_all_original_archive_testzip_and_member_read_passes=True));
 for n,h in protected.items():same(R/n,h)
 put('asset_protection_after.json',dict(PASS=True,protected_files=len(protected),V20_protocol_SHA256=sha(V20/'preregistered_protocol.json'),old_data_sources_unchanged=True,no_runtime_configuration_modified=True))
 state='DATA_READY_SEED_POLICY_PENDING' if all(r['status']=='DATA_READY_SEED_POLICY_PENDING' for r in admissions) else ('BLOCKED' if any(r['status']=='BLOCKED' for r in admissions) else 'DATA_PARTIAL')
 put('result.json',dict(status=state,admission_rows=admissions,received_transport_bytes=meter.summary()['total_received_bytes'],charged_transport_bytes=meter.summary()['total_charged_bytes'],saved_body_bytes=sum(v['bytes'] for v in assets.values()),downloaded_files=len(assets),network_or_quality_failures=len(failures),new_GPI=0,new_model_runs=0,new_density_scores=0,new_fits=0,GPU=0,DART=0,orbit=0,seed_policy_decided=False,wall_s=time.perf_counter()-started,CPU_s=time.process_time()-cpu,peak_self_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,scientific_gates_unchanged=True))
 print(json.dumps(dict(event='V21_FINISHED',status=state,assets=len(assets),new_model_runs=0)),flush=True)
if __name__=='__main__':main()
