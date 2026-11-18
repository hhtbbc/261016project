"""V14-A: bounded one-day acquisition, old-method replication and coverage audit."""
from pathlib import Path
import sys,json,csv,hashlib,datetime,time,resource,subprocess,urllib.parse,xml.etree.ElementTree as ET,warnings
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R),str(R/'src'),str(R/'scripts')]
import numpy as np,cdflib
from netCDF4 import Dataset,num2date
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from observations.bounded_swarm_acquisition import Budget,download_zip,extract_members,sha,inside,posix_cksum
from observations.density_catalog import read_swarm_pod
from evaluation.swarm_density_comparison import quality_mask
from evaluation.late_day_correction import RollingOrigin
from evaluation.causal_density_latitude import fit_global_history,fit_history,apply_global,apply_latitude,latitude_band,supported_metric,assess_joint
from evaluation.residual_representativeness import residual,statistics
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from atmosphere.causal_observation_operator import map_a_queries,observe_map_a
F=R/'experiments/causal_density_new_date_validation_v1';D=R/'data/raw/causal_density_new_date_validation_v1';DAY='2021-03-25';CASES=['B14','A7','B7'];FOLDERS={'B14':'experiments/tiegcm_2021_spinup_14day_v1/B14','A7':'experiments/tiegcm_training_mar23_v2_2021_longrun','B7':'experiments/tiegcm_2021_spinup_initial_condition_v1/B'}
def load(p):return json.loads(Path(p).read_text())
def dump(n,x):
 with inside(F/n).open('x') as f:json.dump(x,f,indent=2,allow_nan=False)
def table(n,rows):
 with inside(F/n).open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def calendar(n):
 return [np.datetime64(datetime.datetime(int(y),1,1)+datetime.timedelta(days=int(mt[0])-1,hours=int(mt[1]),minutes=int(mt[2])),'ns') for y,mt in zip(n['year'][:],n['mtime'][:])]
def save(fig,name):
 fig.text(.5,.005,'NEW_DATE_REPLICATION / SAME_CONTINUOUS_TIE_RUN / HINDCAST / PROVISIONAL Map-A / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED',ha='center',fontsize=6);fig.tight_layout(rect=(0,.035,1,.98));fig.savefig(F/'figures'/name,dpi=145);plt.close(fig)
def expansion_audit():
 """Metadata inventory remains independent of the new-date observation gate."""
 started=time.perf_counter();groups={};invalid=[]
 for p in sorted((R/'experiments').rglob('*.nc')):
  if F in p.parents:continue
  try:
   p.resolve().relative_to(R)
   with Dataset(p) as n:
    if getattr(n,'history_type','')!='secondary' or 'year' not in n.variables or 'mtime' not in n.variables:continue
    tt=calendar(n);z=groups.setdefault(str(p.parent.relative_to(R)),dict(times=[],files=[],schema=True));z['times'].extend(tt);z['files'].append(p.name);z['schema']&=('DEN' in n.variables and 'ZG' in n.variables and n['DEN'].dimensions==n['ZG'].dimensions==('time','ilev','lat','lon') and n['DEN'].units=='g/cm3' and n['ZG'].units=='cm')
  except (OSError,ValueError) as e:invalid.append(dict(file=str(p.relative_to(R)),error=type(e).__name__,message=str(e)))
 rows=[]
 for folder,x in groups.items():
  times=sorted(set(x['times']));parent=R/folder;au=load(parent/'data_audit.json') if (parent/'data_audit.json').exists() else {};status=load(parent/'run_status.json') if (parent/'run_status.json').exists() else {};identity='B14_FULL_SMAX' if folder in ['experiments/tiegcm_2021_spinup_14day_v1/B14','experiments/tiegcm_2022_b14_exploratory_pair_v2/B14'] else 'OTHER_IDENTITY_NOT_POOLED';rows.append(dict(folder=folder,secondary_files=len(x['files']),unique_UTC=len(times),first_UTC=str(times[0]),last_UTC=str(times[-1]),DEN_ZG_schema=x['schema'],actual_field_values_checked='TARGET_2021_MAR25_ONLY',engineering_report=au.get('engineering_PASS',au.get('status','NOT_LOCATED')),launcher_returncode=status.get('returncode'),identity=identity,observation_overlap='Only pre-existing metadata; no additional observation download or value access'))
 table('existing_model_inventory.csv',rows);target=groups['experiments/tiegcm_2022_b14_exploratory_pair_v2/B14'];available=set(target['times']);wanted=[np.datetime64('2022-03-25T00','ns')+np.timedelta64(i,'h') for i in range(25)];needed=set(range(3,13))|set(range(15,25));gaprows=[dict(target_date='2022-03-25',UTC=str(t),hour_from_start=i,exists=t in available,needed_by_registered_queries=i in needed) for i,t in enumerate(wanted)];table('2022_target_gap.csv',gaprows);assert sum(not x['exists'] for x in gaprows)==24 and sum(not x['exists'] and x['needed_by_registered_queries'] for x in gaprows)==20
 source=load(R/'experiments/thermosphere_residual_representativeness_v1/source_manifest.json')['models']['2022']['B14']['source_config'];assert sha(R/source['GPI'])==source['GPI_SHA256']
 with Dataset(R/source['GPI']) as n:yd=np.asarray(n['year_day'][:]);gpi=dict(file=source['GPI'],SHA256=source['GPI_SHA256'],first_YYYYDDD=int(yd[0]),last_YYYYDDD=int(yd[-1]),records=len(yd),variables={k:dict(shape=list(v.shape),units=getattr(v,'units','')) for k,v in n.variables.items()})
 timings=[]
 for tag,steps,days in [('tiegcm_2021_spinup_14day_v1/B14',24480,17),('tiegcm_2022_b14_exploratory_pair_v2/B14',23040,16)]:
  p=R/'experiments'/tag/'run_status.json';a=load(p);assert a['returncode']==0;timings.append(dict(evidence=str(p.relative_to(R)),SHA256=sha(p),steps=steps,days=days,MPI=4,OMP=1,actual_wall_s=a['elapsed_s'],actual_netcdf_bytes=a['netcdf_bytes'],seconds_per_step=a['elapsed_s']/steps,bytes_per_day=a['netcdf_bytes']/days))
 budgets=[]
 for name,days,count in [('2022_March25_fresh_continuous',17,1),('seasonal_new_background',16,6)]:
  steps=days*1440;est=[x['seconds_per_step']*steps for x in timings];vol=[x['bytes_per_day']*days for x in timings];budgets.append(dict(proposal=name,days_per_run=days,runs=count,steps_per_run=steps,predicted_wall_s_min=min(est),predicted_wall_s_max=max(est),planning_safety_factor=1.5,planning_wall_budget_s_per_run=1.5*max(est),predicted_netcdf_bytes_min=min(vol),predicted_netcdf_bytes_max=max(vol),sequential_total_estimated_wall_s=count*max(est),sequential_total_safety_wall_s=count*1.5*max(est),total_netcdf_bytes_max=count*max(vol),MPI=4,OMP=1,GPU=0,additional_authorization_required=True,estimate_not_confidence_bound=True))
 plans=[]
 for y in [2021,2022]:
  for month,day,season in [(3,23,'spring_development_reference'),(6,21,'summer_candidate'),(9,23,'autumn_candidate'),(12,21,'winter_candidate')]:
   dt=datetime.date(y,month,day);start=dt-datetime.timedelta(days=14);stop=dt+datetime.timedelta(days=2);rawstart=start-datetime.timedelta(days=2);rawstop=stop+datetime.timedelta(days=2);plans.append(dict(year=y,season=season,evaluation_date=str(dt),candidate_window_start=str(dt),candidate_window_stop=str(stop),simulation_start=str(start),simulation_stop=str(stop),candidate_spinup_days=14,run_days=16,steps=23040,primary_records=17,secondary_records=384,GPI_raw_start=str(rawstart),GPI_raw_stop=str(rawstop),Fobs_support_start=str(rawstart-datetime.timedelta(days=40)),Fobs_support_stop=str(rawstop+datetime.timedelta(days=40)),Fobs_days=101,Kp_three_hour_buckets=168,existing_B14=month==3,new_integration_required=month!=3,new_observation_status='EXISTING_DEVELOPMENT_DAY' if month==3 else 'NOT_ACQUIRED_NOT_READ',date_selection='fixed calendar seasonal coverage, not density-error ranking or claimed astronomical event timing',solar_geomagnetic_class='NOT_ASSIGNED; audit official drivers before authorizing a quiet/disturbed panel',spinup_science='14-day candidate only, not proof of seasonal convergence'))
 table('seasonal_expansion_candidates.csv',plans);dump('expansion_audit.json',dict(PASS=True,inventory_groups=len(rows),inventory_schema_limit='metadata only outside registered target; not full-field engineering requalification',inventory_errors=invalid,year2022=dict(actual_first=str(min(available)),actual_last=str(max(available)),missing_full_day_hourly_frames=24,missing_direct_query_frames=20,missing_primary_boundary='2022-03-26T00:00:00',existing_GPI=gpi,input_source_config=source,restart_consistency='FAIL',no_native_continuation_authorized=True,required_new_continuous_identity='17days Mar09-toMar26 if approved; no silent append',GPI_conservative_plan='If retaining original +/-2day raw support: Mar07-Mar28, centered Fobs Jan26-May07,102 Fobs and176Kp buckets; audit local gaps anew, generate nothing now'),historical_cost_evidence=timings,budgets=budgets,new_integrations=0,wall_s=time.perf_counter()-started))
 return rows,gaprows,budgets

def target_models():
 result={};coverage=[];audit=[];lo=np.datetime64(DAY+'T00');hi=np.datetime64('2021-03-26T00')
 for case,folder in FOLDERS.items():
  parent=R/folder;old=load(parent/'data_audit.json');status=load(parent/'run_status.json');assert old['engineering_PASS'] and status['returncode']==0;files=[];prim=[];primfiles=[];actual=[]
  for ent in old['files']:
   tt=[np.datetime64(x.replace('+00:00','')) for x in ent.get('UTC',[])];wanted=[t for t in tt if lo<=t<=hi]
   if not wanted:continue
   p=parent/ent['file'];assert sha(p)==ent['SHA256'],str(p)
   with Dataset(p) as n:
    times=calendar(n);assert all(t in times for t in wanted);history=getattr(n,'history_type','')
    if history=='primary':prim.extend(wanted);primfiles.append(dict(path=str(p.relative_to(R)),SHA256=ent['SHA256']))
    elif history=='secondary':
     files.append(dict(path=str(p.relative_to(R)),SHA256=ent['SHA256']));n.set_auto_mask(False)
     for i,t in enumerate(times):
      if not lo<=t<=hi:continue
      actual.append(t)
      for field,unit in [('DEN','g/cm3'),('ZG','cm')]:
       v=n[field];assert v.dimensions==('time','ilev','lat','lon') and v.units==unit;x=np.asarray(v[i]);bad=~np.isfinite(x)|(abs(x)>1e30)
       for attr in ['_FillValue','missing_value']:
        if hasattr(v,attr):bad|=x==np.asarray(getattr(v,attr),dtype=x.dtype)
       if field=='DEN':bad|=x<=0
       monotonic=bool(np.all(np.diff(x,axis=0)>0)) if field=='ZG' else True;assert not bad.any() and monotonic,(case,field,str(t));audit.append(dict(case=case,file=p.name,UTC=str(t),field=field,invalid=0,ZG_monotonic=monotonic))
  target=[lo+np.timedelta64(i,'h') for i in range(25)];complete=all(t in actual for t in target);assert lo in prim and hi in prim
  for t in target:coverage.append(dict(year=2021,case=case,UTC=str(t),secondary_exists=t in actual,primary_exists=t in prim,DEN_ZG_checked=True,engineering='PASS',full_state_science='NOT_PASS'))
  if case=='B14':assert complete,'B14 full target day incomplete'
  result[case]=dict(folder=folder,secondary_files=files,primary_files=primfiles,complete=complete,primary_boundaries=[str(lo),str(hi)],run_evidence=dict(path=str((parent/'run_status.json').relative_to(R)),SHA256=sha(parent/'run_status.json')),data_audit_SHA256=sha(parent/'data_audit.json'),input=dict(path=str((parent/'input.inp').relative_to(R)),SHA256=sha(parent/'input.inp')),elapsed_spinup_at_06Z_days=16.25 if case=='B14' else 9.25,elapsed_spinup_at_18Z_days=16.75 if case=='B14' else 9.75)
 table('model_coverage.csv',coverage);dump('target_field_audit.json',dict(rows=audit,primary_boundaries_verified=True,model_raw_bytes_unchanged=True));return result

def observation():
 stem='SW_OPER_DNSAPOD_2__20210325T000000_20210325T235930_0301';found=[p for p in (R/'data/raw').rglob(stem+'.*') if p.suffix.lower() in ['.zip','.cdf','.hdr']];source=load(R/'experiments/causal_density_latitude_v1/source_manifest.json')['cached_official_receipts'];receipt=next(x for x in source if x['year']==2021);ls=R/receipt['cached_listing_source']['path'];assert sha(ls)==receipt['cached_listing_source']['SHA256'];data=load(ls);items=[]
 def walk(x):
  if isinstance(x,dict):
   if x.get('name')==stem+'.ZIP':items.append(x)
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(data);assert len(items)==1;item=items[0];assert item['size']==140187 and item['path']=='swarm/Level2daily/Latest_baselines/DNS/POD/Sat_A/'+stem+'.ZIP';url='https://swarm-diss.eo.esa.int/?'+urllib.parse.urlencode(dict(do='download',file=item['path']));budget=Budget();plan=dict(stem=stem,URL=url,expected_bytes=item['size'],cached_listing=dict(path=str(ls.relative_to(R)),SHA256=sha(ls)),existing_actual_products=[str(p.relative_to(R)) for p in found],network_budget_bytes=2**20,no_listing_download=True,no_other_product_allowed=True);dump('observation_acquisition_plan.json',plan)
 D.mkdir(exist_ok=True);assert subprocess.run(['git','check-ignore','-q',str(D/(stem+'.ZIP'))]).returncode==0
 zp=next((p for p in found if p.suffix.lower()=='.zip'),D/(stem+'.ZIP'))
 try:
  receipt=download_zip(url,zp,item['size'],stem,budget);members=extract_members(zp,stem,budget,zp.parent);cp=zp.parent/(stem+'.cdf');hp=zp.parent/(stem+'.HDR');digest=sha(cp);hapi=load(R/'experiments/causal_density_latitude_correction_v1/source_manifest.json')['hapi'];assert sha(R/hapi['path'])==hapi['SHA256'];_,a,con=read_swarm_pod(cp,R/hapi['path'],digest,satellite='A')
  with cdflib.CDF(cp) as c:assert c.varinq('time').Data_Type==31;direct=cdflib.cdfepoch.to_datetime(c.varget('time'));np.testing.assert_array_equal(direct,a['utc']);assert con['global_attributes']['TITLE']==[stem]
  root=ET.parse(hp).getroot();fixed=root.find('Fixed_Header');assert fixed.findtext('File_Name')==stem and fixed.findtext('Mission')=='Swarm' and fixed.findtext('File_Type')=='DNSAPOD_2_' and fixed.findtext('File_Version')=='0301';assert fixed.findtext('Validity_Period/Validity_Start')=='UTC=2021-03-25T00:00:00' and fixed.findtext('Validity_Period/Validity_Stop')=='UTC=2021-03-25T23:59:30';crc,length=posix_cksum(cp);assert crc==int(root.findtext('Variable_Header/MPH/CRC')) and length==int(root.findtext('Variable_Header/MPH/Tot_Size'))
  assert len(a['utc'])==2880 and a['utc'][0]==np.datetime64(DAY+'T00') and a['utc'][-1]==np.datetime64(DAY+'T23:59:30') and np.all(np.diff(a['utc'])==np.timedelta64(30,'s'))
  for k,u in [('density','kg/m3'),('latitude','deg'),('longitude','deg'),('altitude','m')]:assert con['variables'][k]['UNITS']==u
  _,fl=quality_mask(a['density'],a['validity_flag']);required=np.zeros(2880,bool)
  for hour in [6,18]:m=RollingOrigin(DAY,hour).masks(a['utc']);required|=m['analysis']|m['future_6h']
  assert a['quality'][required].all(),'Quality holes in registered target windows';audit=dict(PASS=True,product='SW_OPER_DNSAPOD_2_',version='0301',satellite='A',CDF=dict(path=str(cp.relative_to(R)),SHA256=digest),hapi=hapi,ZIP=receipt,extracted_members=members,network_bytes=budget.network_bytes,extracted_bytes=budget.extracted_bytes,HDR_POSIX_CRC=crc,records=2880,cadence_s=30,UTC_start=str(a['utc'][0]),UTC_stop=str(a['utc'][-1]),flag0=int((a['validity_flag']==0).sum()),flag1=int((a['validity_flag']==1).sum()),unknown_flags=int(fl['unknown'].sum()),invalid_density=int(fl['invalid_density'].sum()),quality_valid=int(a['quality'].sum()),target_required=2160,target_valid=int(a['quality'][required].sum()),coordinate_contract='GRS80 product metadata; formal ZG datum unverified',official_checksum_claim='SHA is local provenance, not a publisher-provided checksum');dump('observation_acquisition_audit.json',audit);return a,audit
 except Exception as e:
  dump('observation_acquisition_audit.json',dict(PASS=False,error_type=type(e).__name__,error=str(e),network_bytes=budget.network_bytes,extracted_bytes=budget.extracted_bytes,partial_files_retained=True,no_retry=True));return None,None

def main():
 start=time.perf_counter();cpu=time.process_time();warnings_seen=[];warnings.showwarning=lambda message,category,filename,lineno,file=None,line=None:warnings_seen.append(dict(message=str(message),category=category.__name__))
 protected=load(F/'audit_run_plan.json')['protected_SHA256'];inventory,gaps,budgets=expansion_audit();models=target_models();a,oa=observation()
 if a is None:
  dump('preflight.json',dict(PASS=False,reason='OBSERVATION_GATE_FAILED',expansion_audit_complete=True));dump('frozen_protocol.json',dict(status='NOT_RUN_NO_EVALUATION_FREEZE',reason='observation gate failure'))
  for name in ['metrics.csv','region_metrics.csv','joint_assessment.csv','pointwise_diagnostics.csv']:table(name,[dict(status='NOT_RUN',reason='OBSERVATION_GATE_FAILED')])
  dump('correction_parameters.json',dict(status='NOT_RUN',fits=0));dump('result.json',dict(NEW_DATE_VALIDATION='BLOCKED',MULTIDATE_EXPANSION_PLAN='COMPLETE',scientific_gates_unchanged=True));return
 required=np.zeros(len(a['utc']),bool)
 for hour in [6,18]:m=RollingOrigin(DAY,hour).masks(a['utc']);required|=m['analysis']|m['future_6h']
 a={k:v[required] for k,v in a.items()};raw={};queryaudit=[];probes=[]
 with (F/'queries_local.jsonl').open('x') as trace:
  for case,src in models.items():
   values=np.full(len(a['utc']),np.nan);ok=True
   for hour in [6,18]:
    masks=RollingOrigin(DAY,hour).masks(a['utc']);sel=masks['analysis']|masks['future_6h'];files=[R/x['path'] for x in src['secondary_files']];p=HourlyTiegcmObservation(files,{x.name:next(y['SHA256'] for y in src['secondary_files'] if (R/y['path']).name==x.name) for x in files},DAY+f'T{hour-3:02d}:00:00',('2021-03-26T00:00:00' if hour==18 else DAY+'T12:00:00'),case);ii=np.flatnonzero(sel);queries=map_a_queries(a['utc'][sel],a['latitude'][sel],a['longitude'][sel],a['altitude'][sel]);nvalid=0
    for index,(j,q) in enumerate(zip(ii,queries)):
     r,c=observe_map_a(p,q);trace.write(json.dumps(dict(case=case,cutoff=hour,UTC=str(a['utc'][j]),valid=r.valid,reason=r.reason,coordinates=c,metadata=r.metadata))+'\n')
     if not r.valid or len(r.metadata['columns'])!=8:ok=False;continue
     values[j]=r.rho_kg_m3;nvalid+=1
     if index in [0,360,1079]:
      md=r.metadata;w=md['weights'];ww=np.array([1-w['time'],w['time']])[:,None,None]*np.array([1-w['latitude'],w['latitude']])[None,:,None]*np.array([1-w['longitude'],w['longitude']])[None,None,:];terms=[]
      for col in md['columns']:
       k=next(k for k,(_,pa,rec) in enumerate(p.records) if pa.name==col['file'] and rec==col['record']);z,rho=p._column(k,col['lat_index'],col['lon_index']);terms.append(np.exp(np.interp(c['model_zg_m'],z,np.log(rho))))
      independent=float(np.sum(ww*np.array(terms).reshape(2,2,2)));assert np.isclose(independent,r.rho_kg_m3,rtol=1e-13,atol=0);probes.append(dict(case=case,cutoff=hour,index=int(j),relative_difference=abs(independent/r.rho_kg_m3-1)))
    queryaudit.append(dict(case=case,cutoff=hour,N_requested=len(ii),N_valid=nvalid,frames=len(p.records),eight_columns=True,no_extrapolation=True));p.close()
   if ok:raw[case]=values
   elif case=='B14':raise ValueError('B14 observation operator gate failed; no evaluation allowed')
 dump('query_admission.json',dict(PASS='B14' in raw,rows=queryaudit,independent_probes=probes));dump('preflight.json',dict(PASS=True,CDF_SHA=oa['CDF']['SHA256'],cases_eligible=list(raw),B14_complete=True,query_coverage=1.,coefficients_not_yet_computed=True))
 code=['scripts/run_new_date_validation_v1.py','scripts/verify_new_date_validation_v1.py','src/evaluation/causal_density_latitude.py','src/evaluation/late_day_correction.py','src/evaluation/swarm_crossyear.py','src/evaluation/swarm_density_comparison.py','src/atmosphere/provisional_coordinate_adapter.py','src/atmosphere/causal_observation_operator.py','src/atmosphere/hourly_tiegcm_observation.py','src/observations/bounded_swarm_acquisition.py']
 protocol=dict(identity='NEW_DATE_REPLICATION / SAME_CONTINUOUS_TIE_RUN / HINDCAST / PROVISIONAL Map-A / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED',date=DAY,cutoffs=[6,18],half_open=True,history_hours=3,future_hours=[1,3,6],nonoverlap_hours=[[0,1],[1,3],[3,6]],primary='B14',controls=['A7','B7'],cases_eligible=list(raw),A14='EXCLUDED',methods06=['Raw','GlobalAdaptive06'],methods18=['Raw','GlobalAdaptive18','LatitudeAdaptive18','Stale06'],Stale06='same-date same-background GlobalAdaptive06; all eligible backgrounds, no cross-case reuse',estimator='unchanged median ln(obs)-ln(model)',latitude='abs original GRS80lat <30,30<=abs<60,>=60; hemisphere merged',min_history_and_region_future_N=30,no_fallback=True,joint='unchanged four criteria; N/A is not PASS',new_factor='observation date only; same continuous trajectories, actual warm elapsed time differs and is recorded',window_identity='new observation correction evaluation date; model frames were previously available to other research, not blind or cross-season',no_height_decay_or_new_loss=True,parameter_freeze_before_future_metrics=True,future_poison_factor=1e20,metrics_rtol=1e-13,metrics_atol=0,plot_prior_comparison='B14 2021March23/24/25 18Z6h, LatitudeMarch24 N/A because never run',code_SHA256={n:sha(R/n) for n in code},resources=dict(wall_s=600,RSS_GiB=4,download_MiB=1,public_MiB=150,GPU=0,TIE=0,DART=0,orbit=0),frozen_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
 dump('source_manifest.json',dict(models=models,observation=oa,protected_SHA256=protected));dump('frozen_protocol.json',protocol);psha=sha(F/'frozen_protocol.json');dump('protocol_sha256.json',dict(SHA256=psha));print('ADMISSION PASS; EVALUATION PROTOCOL FROZEN; FUTURE METRICS NOT COMPUTED',flush=True)
 params={};resrows=[]
 for case,p in raw.items():
  c6,m6=fit_global_history(a['utc'],a['latitude'],a['density'],p,a['quality'],day=DAY,hour=6);c18,m18=fit_history(a['utc'],a['latitude'],a['density'],p,a['quality'],day=DAY,hour=18);params[case]=dict(GlobalAdaptive06=c6,GlobalAdaptive18=c18['global_fit'],LatitudeAdaptive18=c18['latitude'],Stale06_reference='GlobalAdaptive06',CDF_SHA256=oa['CDF']['SHA256'],protocol_SHA256=psha)
  for h,mm in [(6,m6),(18,m18)]:
   e=residual(a['density'][mm],p[mm]);bb=latitude_band(a['latitude'][mm])
   for j,k in enumerate(np.flatnonzero(mm)):resrows.append(dict(case=case,cutoff=h,UTC=str(a['utc'][k]),region=['low','mid','high'][bb[j]],latitude_deg=float(a['latitude'][k]),log_residual=float(e[j])))
 dump('correction_parameters.json',dict(protocol_SHA256=psha,date=DAY,parameters=params,all_before_future_metrics=True));paramsha=sha(F/'correction_parameters.json');dump('parameter_sha256.json',dict(SHA256=paramsha));table('calibration_residuals.csv',resrows)
 poison=[]
 for case,p in raw.items():
  for hour in [6,18]:
   changed=a['density'].copy();changed[a['utc']>=np.datetime64(DAY+f'T{hour:02d}')]*=1e20
   if hour==6:c,_=fit_global_history(a['utc'],a['latitude'],changed,p,a['quality'],day=DAY,hour=6);assert c==params[case]['GlobalAdaptive06']
   else:c,_=fit_history(a['utc'],a['latitude'],changed,p,a['quality'],day=DAY,hour=18);assert c['global_fit']==params[case]['GlobalAdaptive18'] and c['latitude']==params[case]['LatitudeAdaptive18']
   poison.append(dict(case=case,cutoff=hour,PASS=True))
 dump('future_poison_test.json',dict(PASS=True,checks=poison,parameter_SHA256=paramsha));assert sha(F/'correction_parameters.json')==paramsha;print('PARAMETERS FROZEN; POISON PASS; FUTURE SCORES BEGIN',flush=True)
 metrics=[];regions=[];joints=[];point=[];timeblocks=[];rep=[];cover=[];arrays={k:v for k,v in a.items()};predictions={}
 for case,p in raw.items():
  c=params[case];local,support=apply_latitude(p,a['latitude'],c['LatitudeAdaptive18']);predictions[case]={6:{'Raw':p,'GlobalAdaptive06':apply_global(p,c['GlobalAdaptive06'])},18:{'Raw':p,'GlobalAdaptive18':apply_global(p,c['GlobalAdaptive18']),'LatitudeAdaptive18':local,'Stale06':apply_global(p,c['GlobalAdaptive06'])}};bb=latitude_band(a['latitude']);rr={'all':np.ones(len(p),bool),**{name:bb==i for i,name in enumerate(['low','mid','high'])}}
  for hour,pp in predictions[case].items():
   masks=RollingOrigin(DAY,hour).masks(a['utc']);masks['block_0_1h']=masks['future_1h'];history=masks['analysis'];histmed={reg:statistics(residual(a['density'][history&rm],p[history&rm])) for reg,rm in rr.items()}
   for win,wm in masks.items():
    scores={reg:{} for reg in rr}
    for method,pred in pp.items():
     ss=support if method=='LatitudeAdaptive18' else np.ones(len(p),bool);cover.append(dict(case=case,cutoff=hour,window=win,method=method,N=int(wm.sum()),N_supported=int((wm&ss).sum()),sample_ID_SHA256=hashlib.sha256(a['utc'][wm].astype('<i8').tobytes()).hexdigest(),query_coverage=1.))
     for reg,rm in rr.items():
      score=supported_metric(pred,a['density'],a['quality'],a['quality'],wm&rm,ss);scores[reg][method]=score;row=dict(case=case,cutoff=hour,window=win,region=reg,method=method,**score);(metrics if reg=='all' else regions).append(row)
      if reg=='all' and win.startswith('block_'):timeblocks.append(row)
      if method!='Raw':
       m=wm&rm&ss;er=abs(p[m]-a['density'][m]);ec=abs(pred[m]-a['density'][m]);point.append(dict(case=case,cutoff=hour,window=win,region=reg,method=method,N=int((wm&rm).sum()),N_supported=int(m.sum()),improved=int((ec<er).sum()),worsened=int((ec>er).sum()),unchanged=int((ec==er).sum())))
    for method in list(pp)[1:]:
     flag=assess_joint(scores['all']['Raw'],scores['all'][method],{k:scores[k]['Raw'] for k in ['low','mid','high']},{k:scores[k][method] for k in ['low','mid','high']},bool((support if method=='LatitudeAdaptive18' else np.ones(len(p),bool))[wm].all()));v=scores['all'][method];base=scores['all']['Raw'];joints.append(dict(case=case,cutoff=hour,window=win,method=method,N=int(wm.sum()),RMSE_gain_pct=100*(1-v['RMSE']/base['RMSE']) if v['RMSE'] is not None else None,relative_RMS_gain_pct=100*(1-v['relative_RMS']/base['relative_RMS']) if v['relative_RMS'] is not None else None,**flag))
    for reg,rm in rr.items():
     sf=statistics(residual(a['density'][wm&rm],p[wm&rm]));hh=histmed[reg];rep.append(dict(case=case,cutoff=hour,window=win,region=reg,N=sf['N'],status=sf['status'],b_H=hh['median'],b_F_DIAGNOSTIC_ONLY=sf['median'],delta_b=sf['median']-hh['median'] if sf['median'] is not None and hh['median'] is not None else None,future_median_never_used_for_prediction=True))
   for method,pred in pp.items():arrays[f'{case}_{hour}_{method}']=pred
  arrays[case+'_Raw']=p
  arrays[case+'_latitude_support']=support
 table('metrics.csv',metrics);table('region_metrics.csv',regions);table('joint_assessment.csv',joints);table('pointwise_diagnostics.csv',point);table('time_block_metrics.csv',timeblocks);table('history_future_representativeness.csv',rep);table('coverage.csv',cover);np.savez_compressed(F/'matched_local.npz',**arrays)
 # Six fixed figures, without choosing the best forecast window.
 (F/'figures').mkdir();fig,axs=plt.subplots(1,2,figsize=(11,4))
 for ax,h in zip(axs,[6,18]):
  e=residual(a['density'],raw['B14']);m=RollingOrigin(DAY,h).masks(a['utc']);bins=np.linspace(float(e.min())-1e-8,float(e.max())+1e-8,81)
  for win in ['analysis','future_1h','future_3h','future_6h']:ax.hist(e[m[win]],bins=bins,density=True,histtype='step',label=win)
  ax.set(title=f'{DAY} {h:02d}Z B14',xlabel='ln(obs/model)',ylabel='Descriptive histogram density');ax.legend(fontsize=6)
 save(fig,'01_residual_history_future.png');fig,axs=plt.subplots(2,1,figsize=(12,7))
 for ax,h in zip(axs,[6,18]):
  mm=RollingOrigin(DAY,h).masks(a['utc'])['future_6h'];hours=(a['utc']-np.datetime64(DAY))/np.timedelta64(1,'h');ax.plot(hours[mm],a['density'][mm]*1e12,'k',label='Swarm A POD')
  for met,pred in predictions['B14'][h].items():ax.plot(hours[mm],pred[mm]*1e12,label=met)
  ax.set(xlabel='UTC hour',ylabel='Density [1e-12 kg/m3]',title=f'B14 {h:02d}Z, all future samples');ax.legend(fontsize=7)
 save(fig,'02_future_density.png');fig,axs=plt.subplots(2,2,figsize=(12,7))
 for row,h in enumerate([6,18]):
  for ax,key in zip(axs[row],['RMSE_gain_pct','relative_RMS_gain_pct']):
   for method in list(predictions['B14'][h])[1:]:ax.plot([1,3,6],[next(x[key] for x in joints if x['case']=='B14' and x['cutoff']==h and x['window']==f'future_{lead}h' and x['method']==method) for lead in [1,3,6]],'o-',label=method)
   ax.axhline(0,color='k');ax.set(title=f'{h:02d}Z {key}',xlabel='Cumulative lead hours',ylabel='Reduction versus Raw [%]');ax.legend(fontsize=6)
 save(fig,'03_metric_gains.png');fig,axs=plt.subplots(1,2,figsize=(12,4))
 for ax,h in zip(axs,[6,18]):
  for method in predictions['B14'][h]:ax.plot([0,1,2],[next(x['relative_RMS']*100 if x['relative_RMS'] is not None else np.nan for x in regions if x['case']=='B14' and x['cutoff']==h and x['window']=='future_6h' and x['region']==reg and x['method']==method) for reg in ['low','mid','high']],'o-',label=method)
  ax.set(xticks=[0,1,2],xticklabels=['low','mid','high'],ylabel='Relative RMS [%]',title=f'B14 {h:02d}Z 6h');ax.legend(fontsize=6)
 save(fig,'04_latitude_errors.png');fig,axs=plt.subplots(1,2,figsize=(12,4));old23=list(csv.DictReader((R/'experiments/causal_density_latitude_correction_v1/metrics.csv').open()));old24=list(csv.DictReader((R/'experiments/causal_density_late_day_v1/metrics.csv').open()))
 for ax,key,label,scale in [(axs[0],'RMSE','RMSE [1e-13 kg/m3]',1e13),(axs[1],'relative_RMS','Relative RMS [%]',100)]:
  for method,alias23,alias24 in [('Raw','Raw','Raw'),('GlobalAdaptive18','GlobalAdaptive18','Adaptive18'),('LatitudeAdaptive18','LatitudeAdaptive18',None)]:
   values=[]
   for rows,alias in [(old23,alias23),(old24,alias24)]:
    rr=[x for x in rows if x.get('year')=='2021' and x['case']=='B14' and x['window']=='future_6h' and x['method']==alias];values.append(float(rr[0][key])*scale if rr else np.nan)
   values.append(next(x[key]*scale if x[key] is not None else np.nan for x in metrics if x['case']=='B14' and x['cutoff']==18 and x['window']=='future_6h' and x['method']==method));ax.plot([23,24,25],values,'o-',label=method)
  ax.set(xticks=[23,24,25],xlabel='2021 March date; 18Z 6h',ylabel=label,title='Same continuous B14; elapsed warm time changes');ax.legend(fontsize=6)
 save(fig,'05_march23_25_comparison.png');fig,axs=plt.subplots(1,2,figsize=(12,4));axs[0].step(range(25),[int(x['exists']) for x in gaps],where='mid',label='2022-03-25 actual B14');axs[0].plot(range(25),np.ones(25),'--',label='Required full-day hourly frames');axs[0].set(xlabel='Hours from2022-03-25 00Z',ylabel='Frame available (0/1)',yticks=[0,1]);axs[0].legend(fontsize=6)
 for y in [2021,2022]:axs[1].scatter([3],[y],label=f'{y} existing B14 March');axs[1].scatter([6,9,12],[y]*3,marker='x',color='gray')
 axs[1].set(xticks=[3,6,9,12],yticks=[2021,2022],xlabel='Calendar month',ylabel='Year',title='Cross-season x markers PROPOSED / NOT RUN');axs[1].legend(fontsize=6);save(fig,'06_actual_and_proposed_coverage.png')
 from verify_new_date_validation_v1 import verify
 verify()
 assert sha(F/'correction_parameters.json')==paramsha
 for n,h in protected.items():assert sha(R/n)==h,n
 dump('warnings_local.json',warnings_seen);dump('result.json',dict(NEW_DATE_VALIDATION='COMPLETE',MULTIDATE_EXPANSION_PLAN='COMPLETE',model_queries=sum(x['N_requested'] for x in queryaudit),successful_queries=sum(x['N_valid'] for x in queryaudit),network_bytes=oa['network_bytes'],new_integrations=0,GPU=0,DART=0,orbit=0,wall_s=time.perf_counter()-start,CPU_s=time.process_time()-cpu,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,science_gates_unchanged=True));print('NEW-DATE REPLICATION COMPLETE; EXPANSION PLANS NOT EXECUTED',flush=True)
if __name__=='__main__':main()
