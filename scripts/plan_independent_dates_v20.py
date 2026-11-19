"""Offline V20 metadata audit and preregistration, no downloads/model/density access."""
from pathlib import Path
import sys,json,csv,hashlib,re,datetime,math,time,resource,subprocess,shutil,urllib.parse
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src')]
from evaluation.independent_date_planning import CANDIDATES,days,support,kp_class,valid_solar,centered,seed_status,estimate,core_protocol
from netCDF4 import Dataset
F=R/'experiments/thermosphere_independent_date_validation_plan_v20'
PRE=R/'experiments/tiegcm_2022_mar25_preparation_v1'
EX=R/'experiments/causal_density_new_date_validation_v1'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_text())
def rows(p):return list(csv.DictReader(Path(p).open()))
def put(n,x):
 p=F/n;p.resolve().relative_to(R)
 with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False)
def table(n,rr):
 with (F/n).open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rr[0]),lineterminator='\n');w.writeheader();w.writerows(rr)
def entry(p):return dict(path=str(Path(p).relative_to(R)),SHA256=sha(p),bytes=Path(p).stat().st_size)
def check(p,h):
 if sha(p)!=h:raise ValueError('Source SHA mismatch '+str(p))
def compact_ranges(values):
 dd=sorted(set(values));out=[]
 if not dd:return out
 start=prev=dd[0]
 for d in dd[1:]:
  if (d-prev).days!=1:out.append([str(start),str(prev)]);start=d
  prev=d
 out.append([str(start),str(prev)]);return out

def audit_drivers():
 solar={};kp={};sources=[];conflicts=[]
 def merge(dst,key,value,path):
  if key in dst and dst[key]!=value:conflicts.append(dict(timestamp=str(key),previous=dst[key],new=value,file=path));dst[key]=None
  else:dst[key]=value
 archive=R/'data/raw/f107_2021_recovery_v1/gfz_year.txt';receipt=next(x for x in load(R/'experiments/f107_2021_recovery_v1/gfz_requests.json') if x['name']=='gfz_year');check(archive,receipt['SHA256']);bad=[];yearrows=[]
 for line in archive.read_text().splitlines():
  a=line.split()
  if not a or a[0]!='2021':continue
  d=datetime.date(*map(int,a[:3]));v=float(a[25]);merge(solar,d,v,str(archive.relative_to(R)));yearrows.append(d)
  if not valid_solar(v):bad.append(str(d))
  for j in range(8):merge(kp,datetime.datetime.combine(d,datetime.time(3*j)),float(a[7+j]) if a[27]=='2' and 0<=float(a[7+j])<=9 else None,str(archive.relative_to(R)))
 sources.append(dict(**entry(archive),key='Fobs+definitive_Kp',records=len(yearrows),first=str(min(yearrows)),last=str(max(yearrows)),source_URL=receipt['URL'],bad_Fobs_dates=bad,source_status='SHA_VERIFIED_CACHED_OFFICIAL',quality='Fobs observed column26; D=2 definitive Kp; -1 missing; no filling',units='Fobs sfu; Kp dimensionless'))
 registry=load(PRE/'driver_source_audit.json')['sources'];raw2023=R/'data/raw/meeting_sources/gfz_Fobs_spinup_support.txt';proof2023=load(R/'logs/tiegcm2023_driver_audit.json')['sources'][str(raw2023.relative_to(R))]
 registry=registry+[dict(path=str(raw2023.relative_to(R)),SHA256=proof2023,key='Fobs',source_URL='https://kp.gfz.de/app/json/ (full request retained in logs/meeting_sources_http_round5.json)')]
 for e in registry:
  path=R/e['path'];check(path,e['SHA256']);x=load(path);key=e['key'];times=x['datetime'];vv=x[key]
  if len(times)!=len(vv) or len(times)!=len(set(times)):raise ValueError('Driver length/duplicate error')
  badtimes=[]
  for i,(t,v) in enumerate(zip(times,vv)):
   dt=datetime.datetime.fromisoformat(t.replace('Z','+00:00'));assert dt.utcoffset()==datetime.timedelta(0);dt=dt.replace(tzinfo=None);v=float(v)
   if key=='Fobs':
    if dt.time()!=datetime.time(0):raise ValueError('Solar UTC date alignment')
    merge(solar,dt.date(),v,e['path'])
    if not valid_solar(v):badtimes.append(t)
   else:
    status=x.get('status',[]);valid=len(status)==len(times) and status[i]=='def' and math.isfinite(v) and 0<=v<=9
    merge(kp,dt,v if valid else None,e['path'])
    if not valid:badtimes.append(t)
  sources.append(dict(**entry(path),key=key,records=len(times),first=times[0],last=times[-1],source_URL=e['source_URL'],bad_Fobs_dates=badtimes if key=='Fobs' else [],source_status='SHA_VERIFIED_CACHED_OFFICIAL',quality='observed positive finite Fobs, no per-record solar quality flag' if key=='Fobs' else 'def status required',units='sfu' if key=='Fobs' else '1'))
 put('driver_source_inventory.json',dict(sources=sources,conflicts=conflicts,network_downloads=0,generated_GPI=0,ignored_sources='Fadj, Ap conversions and alternative-provider estimates are not substitutes',original_builder=dict(**entry(R/'scripts/prepare_tiegcm_training_drivers.py')),actual_interpolator=dict(**entry(R/'src/atmosphere/tiegcm_drivers.py')),convention='center81 observed Fobs; solar four daily noontime interpolation nodes, Kp3h starts00/03/... interpreted at01:30/04:30/... and linearly interpolated; hpower/ctpoten derived by existing formulas; HEELIS, no fixed F107/KP/POWER/CTPOTEN overrides',future_forcing='Historical actual future drivers and centered+40day flux support are HINDCAST, not operational forecasts'))
 return solar,kp,conflicts

def observation_requirements():
 receipt=load(R/'experiments/causal_density_latitude_v1/source_manifest.json')['cached_official_receipts'][0]['cached_listing_source'];path=R/receipt['path'];check(path,receipt['SHA256']);items={}
 def walk(x):
  if isinstance(x,dict):
   if x.get('name','').endswith('.ZIP'):items[x['name']]=x
   for v in x.values():walk(v)
  elif isinstance(x,list):
   for v in x:walk(v)
 walk(load(path));raw_files=[p for p in (R/'data/raw').rglob('*') if p.is_file()];result=[]
 for y,season,day in CANDIDATES:
  ds=day.replace('-','');stem=f'SW_OPER_DNSAPOD_2__{ds}T000000_{ds}T235930_0301';it=items.get(stem+'.ZIP');actual=[str(p.relative_to(R)) for p in raw_files if p.stem==stem and p.suffix.lower() in ['.zip','.cdf','.hdr']]
  result.append(dict(date=day,season=season,product=stem+'.ZIP',cached_index_status='INDEX_CONFIRMED_ONLY' if it else 'NOT_VERIFIED',local_actual_status='LOCAL_PRESENT_UNAUDITED' if actual else 'NOT_ACQUIRED',local_paths=';'.join(actual),cached_bytes=it['size'] if it else None,official_path=it['path'] if it else '',official_download_URL='https://swarm-diss.eo.esa.int/?'+urllib.parse.urlencode(dict(do='download',file=it['path'])) if it else '',cached_index_SHA256=receipt['SHA256'],current_server_existence='NOT_VERIFIED_NO_NETWORK',CDF_contract='0301 DNSAPOD_2_ UTC instantaneous density kg/m3; GRS80 lat/lon degrees and ellipsoid altitude m; validated general contract reused, candidate bytes not read',quality_status='NOT_VERIFIED',target_03_12_and15_24_coverage='NOT_VERIFIED',required_checks='ZIP size/CRC/path-safe extraction/SHA; CDF identity/UTC2880/cadence30s/no duplicate; flag0 nominal flag1 anomalous unknown reject; finite positive density/valid coords; per-band N>=30; all8 model columns no extrapolation',expected_uncompressed_bytes='about0.2MiB per product from prior days; candidate size not verified'))
 table('observation_data_requirements.csv',result);return result

def model_inventory():
 old=rows(EX/'existing_model_inventory.csv');known={x['folder'] for x in old};inventory=[]
 for x in old:inventory.append(dict(folder=x['folder'],first_secondary_UTC=x['first_UTC'],last_secondary_UTC=x['last_UTC'],secondary_files=x['secondary_files'],records=x['unique_UTC'],identity=x['identity'],source_evidence='experiments/causal_density_new_date_validation_v1/existing_model_inventory.csv',current_qualification='HISTORICAL_IDENTITY_ONLY; no requalification',candidate_season_overlap=False))
 groups={}
 for p in (R/'experiments').rglob('secondary*.nc'):
  rel=str(p.relative_to(R));parts=p.relative_to(R).parts
  if any('_local' in a or 'test' in a or a in ['fixtures'] for a in parts):continue
  folder=str(p.parent.relative_to(R))
  if folder not in known:groups.setdefault(folder,[]).append(p)
 newheaders=[]
 for folder,files in groups.items():
  times=[];count=0
  # Only the two endpoint files are read for calendar coordinates; no physical variable data.
  for p in sorted(set([min(files),max(files)])):
   with Dataset(p) as n:
    if 'year' not in n.variables or 'mtime' not in n.variables:continue
    for i in [0,len(n['year'])-1]:
     y=int(n['year'][i]);mt=list(map(int,n['mtime'][i]));times.append(datetime.datetime(y,1,1)+datetime.timedelta(days=mt[0]-1,hours=mt[1],minutes=mt[2]))
    newheaders.append(dict(file=str(p.relative_to(R)),bytes=p.stat().st_size,variables_read=['year endpoints','mtime endpoints'],DEN_ZG_values_read=False))
  if not times:continue
  v16=folder=='experiments/tiegcm_2022_mar25_execution_review_v1/actual_run';inventory.append(dict(folder=folder,first_secondary_UTC=min(times).isoformat(),last_secondary_UTC=max(times).isoformat(),secondary_files=len(files),records=408 if v16 else 'NOT_COUNTED',identity='NEW17DAY_B14_V16_ENGINEERING_V17_PASS_NUMERICS_V19_CLOSED' if v16 else 'UNCLASSIFIED_NOT_POOLED',source_evidence='V16 manifest+V17 acceptance+V19 result_closed' if v16 else 'endpoint headers only',current_qualification='ENGINEERING_PASS_NOT_FULL_PHYSICAL_CONVERGENCE' if v16 else 'NOT_VERIFIED',candidate_season_overlap=any(min(times).date()<=datetime.date.fromisoformat(d)<=max(times).date() for _,_,d in CANDIDATES)))
 table('existing_model_inventory_updated.csv',inventory);put('metadata_read_audit.json',dict(reused_old_inventory_groups=len(old),new_endpoint_files_read=newheaders,large_NetCDF_physical_values_read=0,original_full_model_SHA_sweep=False,no_density_CDF_opened=True))
 v19=load(R/'experiments/tiegcm_2022_mar25_independent_verification_v19/result_closed.json');assert v19['status']=='VERIFICATION_CLOSED_PASS' and v19['year2022_cumulative_joint_PASS']==0 and v19['year2021_cumulative_joint_PASS']==1
 matrix=[]
 for y in [2021,2022]:
  for dd in [23,24,25]:
   new=y==2022 and dd==25;folder='experiments/tiegcm_2022_mar25_execution_review_v1/actual_run' if new else ('experiments/tiegcm_2021_spinup_14day_v1/B14' if y==2021 else 'experiments/tiegcm_2022_b14_exploratory_pair_v2/B14')
   matrix.append(dict(date=f'{y}-03-{dd}',role_now='USED_VALIDATION_NOT_FUTURE_HOLDOUT' if dd in [23,25] else 'USED_DEVELOPMENT_NOT_BLIND',model=folder,model_run_identity='NEW17DAY_V16' if new else ('2021_B14_17DAY' if y==2021 else 'OLD2022_B14_16DAY'),complete_target_day=True,Swarm_A='ACQUIRED_QUALITY_MATCHED',scoring='V18 single score+V19 closed' if new else ('V13 latitude' if dd==23 else ('V14A new-date' if dd==25 else 'V10/V11/V12 development')),new_run_needed=False,independent_season=False,spinup_at_06_days=dd-9+.25,spinup_at_18_days=dd-9+.75,oldMarch25gap='CLOSED_V16_TO_V19' if new else 'not applicable'))
 table('existing_date_coverage.csv',matrix)
 put('obsolete_plan_corrections.json',dict(original_plan_preserved=True,old2022Mar25_model_gap='CLOSED; do not run again',old2022Mar25_observation_gap='CLOSED; CDF verified and matched2880',old17day_recommendation='ALREADY_EXECUTED_V16_ENGINEERING_V17_NUMERICS_V19',remaining_new_B14_mature_unused_dates_in_existing_runs=0,new_run_vs_old16day='Same original smax seed/solver/science options; independently launched cold run with STOP/output schedule and GPI coverage extension; common drivers validated by prior preparation, no claim of fresh independent date or new initialization perturbation'))
 return inventory,matrix

def initial_audit():
 receipt=load(R/'experiments/tiegcm_2021_spinup_initial_condition_v1/directory_request.json');html=R/'data/raw/tiegcm_2021_spinup_initial_condition_v1/directory.html';check(html,receipt['SHA256']);text=html.read_text();actual=R/'data/raw/tiegcm_2021_spinup_initial_condition_v1/tiegcm_res5.0_mareqx_smax_prim.nc';check(actual,'a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7');audit=load(R/'experiments/tiegcm_2021_spinup_initial_condition_v1/initial_state_audit.json');cfg=load(PRE/'model_configuration_manifest.json')
 with Dataset(actual) as n:
  record_year=int(n['year'][0]);record_mtime=list(map(int,n['mtime'][0]));req=audit['complete_required_variables'];dimensions={k:len(v) for k,v in n.dimensions.items()};actual_version=getattr(n,'model_version','NOT_SET')
 registry=[]
 for season,key in [('summer','junsol'),('autumn','sepeqx'),('winter','decsol')]:
  stem=f'tiegcm_res5.0_{key}_smax_prim.nc';cached=f'href="{stem}"' in text;found=list((R/'data/raw').rglob(stem));registry.append(dict(season=season,product=stem,cached_official_index='INDEX_CONFIRMED_ONLY' if cached else 'NOT_VERIFIED',URL=receipt['URL']+stem,local_present=bool(found),exact_bytes='NOT_VERIFIED; cached HTML approximate16M',suggested_bounded_download_MiB=20,internal_record_year='UNKNOWN_NOT_ACQUIRED',SOURCE_START='MUST_READ_ACTUAL_RECORD; NEVER_INFER_FROM_NAME',state_completeness='NOT_VERIFIED_NOT_ACQUIRED',grid_and_units='NOT_VERIFIED_NOT_ACQUIRED',season_adaptation='UNVERIFIED'))
 table('seasonal_initial_asset_requirements.csv',registry)
 out=dict(existing_march_seed=entry(actual),official_directory=entry(html),current_seed_record_year=record_year,current_seed_SOURCE_START=record_mtime,current_seed_dimensions=dimensions,full_state_count_previously_verified=req,original_source_version_field=actual_version,existing_march_seed_status=seed_status(True,audit['B']['structure_complete'],record_mtime[1:]==[0,0],False),current_binary='experiments/tiegcm2_apex2023_v1/tiegcm2.0',expected_binary_SHA256=cfg['verified_assets']['experiments/tiegcm2_apex2023_v1/tiegcm2.0'],binary_exists=(R/'experiments/tiegcm2_apex2023_v1/tiegcm2.0').exists(),actual_version=cfg['base_release'],apex_update=cfg['apex_update'],physical_defaults=cfg['derived_runtime_defaults'],physics=dict(grid='5degrees,36latx72lon,29ilev; DEN/ZG remainilev',STEP=60,MPI=4,OMP=1,POTENTIAL_MODEL='HEELIS',CALC_HELIUM=1,GSWM_migrating_diurnal=True,GSWM_migrating_semidiurnal=True,ibgrddata=0),source_policy='PENDING: preserving exact mareqx cold seed keeps initializer fixed but summer/winter adaptation unproved. Seasonal official smax seeds are acquisition/audit candidates only, not automatic primary replacements. Before run, explicitly approve/freeze one exact seed SHA per season pair. A changed seed changes background identity; cross-season comparison cannot then isolate date alone.',source_clock_gate='Actual00:00 complete primary record required for00:00 START; SOURCE_START must equal actual native selection, not rename/relabel or fabricate_NM',spinup='14days candidate only, not proven seasonal convergence; warm elapsed14.25days at06Z and14.75days at18Z',restart='FAIL; no restart/append, independently cold-start each run')
 check(R/out['current_binary'],out['expected_binary_SHA256']);put('initial_field_and_configuration_audit.json',out);return registry,out

def costs(obs):
 evidence=[]
 for folder,steps,nd in [('tiegcm_2021_spinup_14day_v1/B14',24480,17),('tiegcm_2022_b14_exploratory_pair_v2/B14',23040,16)]:
  p=R/'experiments'/folder/'run_status.json';x=load(p);evidence.append(dict(source=str(p.relative_to(R)),SHA256=sha(p),steps=steps,days=nd,wall_s=x['elapsed_s'],output_bytes=x['netcdf_bytes'],CPU_s=(x.get('children_user_cpu_s',0)+x.get('children_system_cpu_s',0)) or None,peak_sampled_RSS_bytes=x['peak_sampled_tree_rss_bytes']))
 x=load(R/'experiments/tiegcm_2022_mar25_formal_run_v1/result.json');res=load(R/'experiments/tiegcm_2022_mar25_formal_run_v1/resource_audit.json');evidence.append(dict(source='experiments/tiegcm_2022_mar25_formal_run_v1/result.json + resource_audit.json',SHA256=sha(R/'experiments/tiegcm_2022_mar25_formal_run_v1/resource_audit.json'),steps=24480,days=17,wall_s=x['model_supervised_wall_s'],output_bytes=res['model']['netCDF_bytes'],CPU_s=res['model']['model_children_CPU_user_s']+res['model']['model_children_CPU_system_s'],peak_sampled_RSS_bytes=res['model']['peak_sampled_model_tree_RSS_bytes']))
 rr=[]
 for label,count in [('one_new_date',1),('summer_pair',2),('all_six_season_dates',6)]:
  z=estimate(evidence,16,count);z['batch']=label;z['observation_ZIP_bytes_cached']=max(o['cached_bytes'] for o in obs) if count==1 else (sum(o['cached_bytes'] for o in obs if o['season']=='summer') if count==2 else sum(o['cached_bytes'] for o in obs));z['daily_GPI_records']=21*count;z['raw_Fobs_requested_before_reuse']=101*count;z['raw_Kp_buckets_before_reuse']=168*count;z['actual_same_season_pair_driver_reuse']='Physical driver dates differ by year; no cross-year substitution';rr.append(z)
 table('resource_requirements.csv',rr);put('resource_estimation_evidence.json',dict(historical_runs=evidence,formulas='elapsed/actualsteps*23040; output/actualdays*16; actual user+system CPU/steps*23040; 1.5x max soft planning; requested hard4800 distinct from estimate',historical_engineering=dict(V17_wall_s=load(R/'experiments/tiegcm_2022_mar25_postrun_acceptance_v17/result.json')['read_only_wall_s'],records=408),historical_scoring=dict(V18_wall_s=load(R/'experiments/tiegcm_2022_mar25_density_validation_v18/supervision_result.json')['elapsed_s'],scope='one actual score plus partial independent verifier; exit1, not a fully successful future pipeline timing'),historical_verification=dict(V19_supervised_s=load(R/'experiments/tiegcm_2022_mar25_independent_verification_v19/resource_audit.json')['supervised_wall_s'],scope='C1/C2 and complete table checkpoint, no scoring'),afterrun_requests='Separate engineering600s/RSS4GiB, score600s/RSS4GiB, independent verification600s/RSS4GiB perdate, no automatic retry',sampling_limits_are_not_OS_isolation=True))
 return rr

def main():
 started=time.perf_counter();cpu=time.process_time();F.resolve().relative_to(R);
 if F.exists():
  assert {p.name for p in F.iterdir()}<={'protected_before.json','supervision_result.json'},'Planning outputs already exist; refuse overwrite'
 else:F.mkdir(exist_ok=False)
 assert (R/'logs/v20_planning_tests.log').read_text().rstrip().endswith('OK')
 # Protect only relevant small prior plans, reports, protocols and index receipts; no large output rehash.
 refs=['AGENTS.md','docs/TIEGCM_V19_NEXT_DECISION.md','reports/TIEGCM_2022_MAR25_INDEPENDENT_VERIFICATION_V19.md','reports/TIEGCM_2022_MAR25_DENSITY_VALIDATION_V18.md','docs/THERMOSPHERE_MULTIDATE_DATA_EXPANSION_PLAN_V1.md','experiments/causal_density_new_date_validation_v1/seasonal_expansion_candidates.csv','experiments/causal_density_new_date_validation_v1/existing_model_inventory.csv','experiments/tiegcm_2022_mar25_preparation_v1/frozen_evaluation_protocol.json','experiments/tiegcm_2022_mar25_independent_verification_v19/result_closed.json']
 for folder in ['tiegcm_2022_mar25_formal_run_v1','tiegcm_2022_mar25_postrun_acceptance_v17','tiegcm_2022_mar25_density_validation_v18','tiegcm_2022_mar25_independent_verification_v19']:
  refs.extend(str(p.relative_to(R)) for p in (R/'experiments'/folder).glob('*.json') if '_local' not in p.name)
 protected={n:sha(R/n) for n in set(refs)}
 if (F/'protected_before.json').exists():assert load(F/'protected_before.json')==protected
 else:put('protected_before.json',protected)
 inventory,matrix=model_inventory();solar,kp,conflicts=audit_drivers();observations=observation_requirements();seeds,initial=initial_audit();resource_rows=costs(observations)
 driver_rows=[];gaps=[];activities=[];candidates=[]
 for rank,(year,season,target) in enumerate(CANDIDATES,1):
  q=support(target);required_s=days(datetime.date.fromisoformat(q['solar_start']),datetime.date.fromisoformat(q['solar_stop']));missing_s=[d for d in required_s if not valid_solar(solar.get(d))];required_k=[datetime.datetime.combine(d,datetime.time(h)) for d in days(datetime.date.fromisoformat(q['raw_start']),datetime.date.fromisoformat(q['raw_stop'])) for h in range(0,24,3)];missing_k=[t for t in required_k if kp.get(t) is None];badvalues=[d for d in missing_s if d in solar];absent=[d for d in missing_s if d not in solar];day=datetime.date.fromisoformat(target);flux=solar.get(day);avg,avg_missing=centered(solar,day);kday=[kp.get(datetime.datetime.combine(day,datetime.time(h))) for h in range(0,24,3)];clazz=kp_class(kday,['def']*8 if all(v is not None for v in kday) else ['unknown']*8)
  available_mean_days=sum(centered(solar,d)[0] is not None for d in days(datetime.date.fromisoformat(q['raw_start']),datetime.date.fromisoformat(q['raw_stop'])));status='COMPLETE_RAW_NO_GPI_GENERATED' if not missing_s and not missing_k else 'GPI_INPUT_BLOCKED'
  driver_rows.append(dict(date=target,season=season,**{k:v for k,v in q.items() if k!='target_date'},Fobs_valid=101-len(missing_s),Fobs_not_acquired=len(absent),Fobs_invalid_or_disputed=len(badvalues),invalid_dates=';'.join(map(str,badvalues)),missing_Fobs_ranges=json.dumps(compact_ranges(missing_s)),Kp_valid=168-len(missing_k),Kp_missing=len(missing_k),F107A_daily_means_supported=available_mean_days,status=status,existing_GPI_for_candidate='NOT_GENERATED',no_fill_or_interpolation=True))
  for d in missing_s:gaps.append(dict(date=target,index='Fobs',UTC=str(d)+'T00:00:00Z',reason='INVALID_CACHED_VALUE' if d in solar else 'NOT_ACQUIRED',raw_value=solar.get(d),required_for='center81 daily means; no imputation'))
  for t in missing_k:gaps.append(dict(date=target,index='Kp',UTC=t.isoformat()+'Z',reason='NOT_ACQUIRED_OR_NOT_DEFINITIVE',raw_value=kp.get(t),required_for='existing getgpi centers/interpolation'))
  activities.append(dict(date=target,Fobs_sfu=flux if valid_solar(flux) else None,F107A_center81_sfu=avg,F107A_missing_count=len(avg_missing),F107A_missing_dates=';'.join(map(str,avg_missing)),Kp_valid_bins=sum(v is not None for v in kday),Kp_max=max(kday) if all(v is not None for v in kday) else None,Kp_day_class=clazz,class_rule='8def bins; QUIET max<=2,ENHANCED max>=5,otherwiseINTERMEDIATE; incompleteUNKNOWN',solar_class='CONTINUOUS_VALUES_ONLY_NO_HIGH_LOW_LABEL',selection_based_on_density=False))
  overlap=[x['folder'] for x in inventory if str(x['first_secondary_UTC'])[:10]<=target<=str(x['last_secondary_UTC'])[:10]];assert not overlap,'Candidate already covered; inspect identity before proceeding'
  candidates.append(dict(priority=rank,pair_order={'summer':1,'autumn':2,'winter':3}[season],date=target,season=season,selection='original calendar preregistration; no target density read',observation_status=next(x['local_actual_status'] for x in observations if x['date']==target),model_status='NO_EXISTING_TARGET_FIELD',driver_status=status,seasonal_initial_status='NOT_ACQUIRED_NOT_QUALIFIED',primary_seed_policy='PENDING_EXPLICIT_IDENTITY_APPROVAL',Kp_class=clazz,run_ready=False,data_acquisition_priority='SUMMER_FIRST' if season=='summer' else 'PREDECLARED_BACKUP_AUTUMN' if season=='autumn' else 'THIRD_STAGE',compute_feasibility_note='2021autumn has complete raw drivers and is a declared fallback; all still need seed and observations; no automatic swap' if target=='2021-09-23' else 'summer2021 blocked by May09 andJune16 Fobs' if target=='2021-06-21' else 'observation/driver/seed gates before run'))
 table('driver_requirements.csv',driver_rows);table('driver_gap_details.csv',gaps);table('activity_conditions.csv',activities);table('candidate_priority.csv',candidates)
 base=load(PRE/'frozen_evaluation_protocol.json');core=core_protocol(base)
 prereg=dict(identity='DATE_HELD_OUT_PREREG / HINDCAST / PROVISIONAL Map-A / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED',planning_status='PARTIALLY_READY',fixed_scientific_core=core,core_source_SHA256=sha(PRE/'frozen_evaluation_protocol.json'),fixed_dates=[d for _,_,d in CANDIDATES],fixed_pair_order=['summer','autumn','winter'],background='B14 candidate class, same solver/grid/physics; exact season seed identity not yet approved',initial_identity_gate='Exact source SHA/SOURCE_START/actual34states/source-clock/season applicability required; seasonal seed not silently substituted for fixed mareqx. Pair same seed SHA; any change must be approved and disclosed before target errors are read.',activity_rule=dict(unit='Kp dimensionless',daily_complete_bins=8,definitive_only=True,quiet_max_le=2,enhanced_max_ge=5,other='INTERMEDIATE',incomplete='UNKNOWN',role='Operational study grouping, not a new official storm-intensity definition; frozen before candidate density access',solar='report actual daily Fobs and center81 mean continuously; no solar high/low bins or error-tuned thresholds',previous_24h='optional context only, not a fitting predictor or date-selection rule',group_minimum='at least2distinct dates per contrasted geomagnetic category including both years; otherwise group-comparison N/A, perdate results retained; this is support threshold, not statistical power proof'),method_execution='Metadata/quality audit before fitting; fitting process reads historical data only. Freeze b and numpy multiplier, source IDs and SHA before future scoring; same-date Stale06; independent checkpoint tests; poisoned copies separate by cutoff; V19 frozen multiplier contract and rtol1e-13 atol0 for verification',query_admission='All quality-eligible requested window points require eight finite valid columns, zero weights included, no extrapolation; do not drop failed points by model error. Lack of support is N/A or admission failure, never PASS.',dataset_roles='March23/24/25 years2021/22 are used development/validation references, not new holdout. Six seasonal target density values not accessed. If any date later used to choose a new method, downgrade it to development permanently and preregister another test panel before access.',comparison='Raw vs each registered method within date/common IDs; same-calendar crossyear pair; keep season/seed/run identities separate. No pooled gridpoint IID inference, no composite score or error-driven date replacement.',failure='keep all failures/NA; no retries/alternate dates or initial-state relabeling without new task; negative scientific result is retained, not reason to retune on holdout',unresolved=['actual candidate CDF quality/coverage','2021May09 andJune16 Fobs missing observations','2022driver support acquisition','seasonal initial physical identity and00clock','14day seasonal adaptation not proven','geomagnetic classes for2022 and balanced category support unknown'],frozen_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),target_density_values_read=0,new_scoring=0,new_fits=0)
 put('preregistered_protocol.json',prereg);put('protocol_sha256.json',dict(SHA256=sha(F/'preregistered_protocol.json'),status='CORE_AND_DATES_FROZEN_DATA_AND_INITIAL_IDENTITY_PENDING'))
 put('next_acquisition_request.json',dict(execution_now=False,stage='First acquire and inspect missing summer inputs, no model or score',Swarm_products=[{k:x[k] for k in ['date','product','official_download_URL','cached_bytes']} for x in observations if x['season']=='summer'],Swarm_expected_bytes=sum(x['cached_bytes'] for x in observations if x['season']=='summer'),small_network_total_cap_MiB=1,ZIP_extraction_cap_MiB=2,GFZ2022=dict(Fobs_missing='2022-05-20 through2022-08-04 inclusive77daily values',URL='https://kp.gfz.de/app/json/?start=2022-05-20T00:00:00Z&end=2022-08-04T23:59:59Z&index=Fobs',Kp_missing='2022-06-05 through2022-06-25 inclusive168def bins',Kp_URL='https://kp.gfz.de/app/json/?start=2022-06-05T00:00:00Z&end=2022-06-25T23:59:59Z&index=Kp&status=def'),GFZ2021=dict(existing='365day archive and summer Kp already present',bad_Fobs=['2021-05-09','2021-06-16'],new_minimal_check='One small official June16 Fobs response/quality or revision evidence; if -1 persists remain blocked. Do not repeat unchanged May09 full-year/provider-comparison audits or silently use Fadj/INT.',no_imputation=True),seasonal_source=dict(product='tiegcm_res5.0_junsol_smax_prim.nc',URL='https://download.hao.ucar.edu/pub/tgcm/data/tiegcm2.0/tiegcm_res5.0_junsol_smax_prim.nc',cached_size='approx16M NOT Content-Length verified',separate_network_cap_MiB=20,checks='officialTLS/HTTP/Content-Length/bounded atomic download/SHA; native complete34primary fields/grid/units/year/mtime/00clock; SOURCE_START from actualrecord only; independent seasonal applicability review'),total_authorization_network_cap_MiB=21,no_directory_listing_download=True,no_other_satellites_or_dates=True,if_blocked='Keep summer2021 blocked. Report2022summer independent readiness. Autumn23pair is predeclared alternative requiring explicit approval before switching; no automatic date selection.',output_new_directory_only=True,CPU_budget_s=600,RSS_budget_GiB=4,no_model_no_GPI_generation_without_separate_preparation_authorization=True))
 for n,h in protected.items():check(R/n,h)
 put('protected_after.json',dict(PASS=True,files=len(protected),old_plans_and_V16_to_V19_summaries_unchanged=True,large_model_physical_rescans=0))
 put('source_manifest.json',dict(references=[entry(R/n) for n in sorted(set(refs))],old_source_records_reused=True,NetCDF_model_values_read=0,Swarm_density_values_read=0,full_large_output_SHA_rescans=0,code={n:sha(R/n) for n in ['src/evaluation/independent_date_planning.py','scripts/plan_independent_dates_v20.py','tests/test_independent_date_planning_v20.py']}))
 put('result.json',dict(status='PARTIALLY_READY',science_core_preregistration='FROZEN',data_and_initial_identity='PENDING',candidate_dates=6,new_seasonal_CDFs_acquired=0,cached_index_products_confirmed=6,run_ready_candidates=0,complete_driver_candidate_dates=[x['date'] for x in driver_rows if x['status']=='COMPLETE_RAW_NO_GPI_GENERATED'],existing_2022Mar25_gap='CLOSED_NO_REPEAT_RUN',new_integrations=0,new_scores=0,new_fits=0,new_download_bytes=0,GPU=0,DART=0,orbit=0,wall_s=time.perf_counter()-started,CPU_s=time.process_time()-cpu,peak_self_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,scientific_gates_unchanged=True))
 print('V20 OFFLINE AUDIT COMPLETE; CORE FROZEN; NO DATA ACQUISITION OR MODEL',flush=True)
if __name__=='__main__':main()
