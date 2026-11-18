"""V14-B: source-verified preparation only; never calls the TIE-GCM executable."""
from pathlib import Path
import sys,json,re,hashlib,os,subprocess,shutil,csv,time,resource,math,urllib.parse,xml.etree.ElementTree as ET
from datetime import date,datetime,timedelta,timezone
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R/'scripts'),str(R)]
import numpy as np,cdflib
from netCDF4 import Dataset
from observations.bounded_swarm_acquisition import Budget,download_zip,extract_members,posix_cksum
from observations.density_catalog import read_swarm_pod
from atmosphere.restart_validation import inspect_restart,check_source_clock,REQUIRED
from atmosphere.tiegcm_drivers import GpiDriver
from runtime.supervisor import supervise,Limits
import prepare_tiegcm_training_drivers as builder
from prepare_tiegcm_mar23_drivers import independent
F=R/'experiments/tiegcm_2022_mar25_preparation_v1';OLD=R/'experiments/tiegcm_2022_b14_exploratory_pair_v2/B14';RUN=F/'run'
def inside(p):
 p=Path(p);p.resolve().relative_to(R);return p
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as s:
  for b in iter(lambda:s.read(2**20),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_text())
def dump(n,v):
 with inside(F/n).open('x') as s:json.dump(v,s,indent=2,allow_nan=False);s.write('\n')
def utc(d):return datetime.combine(d,datetime.min.time(),timezone.utc)
def entry(p):return dict(path=str(Path(p).relative_to(R)),SHA256=sha(p),bytes=Path(p).stat().st_size)
def namelist(text):
 matches=list(re.finditer(r'(?mi)^\s*([A-Z][A-Z0-9_]*)\s*=',text));return {m[1].upper():text[m.end():matches[i+1].start() if i+1<len(matches) else text.rfind('/')].strip() for i,m in enumerate(matches)}
def extended_text(original,gpi):
 changes={'STOP':'85 0 0','SECSTOP':'85 0 0','OUTPUT':', '.join(f"'primary_{i:03d}.nc'" for i in range(1,19)),'SECOUT':', '.join(f"'secondary_{i:03d}.nc'" for i in range(1,18)),'GPI_NCFILE':"'"+str(gpi)+"'"}
 text=original
 for k,v in changes.items():text,n=re.subn(rf'(?m)^\s*{k}\s*=.*$',f' {k} = {v}',text);assert n==1,k
 a,b=namelist(original),namelist(text);assert set(a)==set(b);assert {k for k in a if a[k]!=b[k]}==set(changes)
 assert not set(a)&{'KP','POWER','CTPOTEN','F107','F107A'}
 return text

def acquisition():
 budget=Budget();stem='SW_OPER_DNSAPOD_2__20220325T000000_20220325T235930_0301';raw=R/'data/raw/tiegcm_2022_mar25_preparation_v1';inside(raw).mkdir(exist_ok=False)
 try:
  previous=load(R/'experiments/causal_density_latitude_v1/source_manifest.json');receipt=next(x for x in previous['cached_official_receipts'] if x['year']==2022)['cached_listing_source'];ls=R/receipt['path'];assert sha(ls)==receipt['SHA256'];items=[]
  def walk(x):
   if isinstance(x,dict):
    if x.get('name')==stem+'.ZIP':items.append(x)
    for v in x.values():walk(v)
   elif isinstance(x,list):
    for v in x:walk(v)
  walk(load(ls));assert len(items)==1;item=items[0];assert item['size']==139665 and item['path']=='swarm/Level2daily/Latest_baselines/DNS/POD/Sat_A/'+stem+'.ZIP'
  found=[p for p in (R/'data/raw').rglob(stem+'.*') if p.suffix.lower() in ['.zip','.cdf','.hdr']];z=next((p for p in found if p.suffix.lower()=='.zip'),raw/(stem+'.ZIP'));assert subprocess.run(['git','check-ignore','-q',str(z)]).returncode==0
  url='https://swarm-diss.eo.esa.int/?'+urllib.parse.urlencode(dict(do='download',file=item['path']));download=download_zip(url,z,item['size'],stem,budget);members=extract_members(z,stem,budget,z.parent);cp=z.parent/(stem+'.cdf');hp=z.parent/(stem+'.HDR');hapi=load(R/'experiments/causal_density_latitude_correction_v1/source_manifest.json')['hapi'];assert sha(R/hapi['path'])==hapi['SHA256']
  _,a,contract=read_swarm_pod(cp,R/hapi['path'],sha(cp),satellite='A');assert len(a['utc'])==2880 and a['utc'][0]==np.datetime64('2022-03-25T00') and a['utc'][-1]==np.datetime64('2022-03-25T23:59:30') and np.all(np.diff(a['utc'])==np.timedelta64(30,'s'))
  with cdflib.CDF(cp) as c:assert c.varinq('time').Data_Type==31;np.testing.assert_array_equal(cdflib.cdfepoch.to_datetime(c.varget('time')),a['utc'])
  for k,u in [('density','kg/m3'),('latitude','deg'),('longitude','deg'),('altitude','m')]:assert contract['variables'][k]['UNITS']==u
  root=ET.parse(hp).getroot();hdr=root.find('Fixed_Header');assert hdr.findtext('File_Name')==stem and hdr.findtext('Mission')=='Swarm' and hdr.findtext('File_Type')=='DNSAPOD_2_' and hdr.findtext('File_Version')=='0301';assert hdr.findtext('Validity_Period/Validity_Start')=='UTC=2022-03-25T00:00:00' and hdr.findtext('Validity_Period/Validity_Stop')=='UTC=2022-03-25T23:59:30'
  crc,size=posix_cksum(cp);assert crc==int(root.findtext('Variable_Header/MPH/CRC')) and size==int(root.findtext('Variable_Header/MPH/Tot_Size'))
  rows=[];lat=abs(a['latitude']);bands={'all':np.ones(2880,bool),'low':lat<30,'mid':(lat>=30)&(lat<60),'high':lat>=60}
  for lo,hi in [(3,6),(6,12),(15,18),(18,24)]:
   mask=(a['utc']>=np.datetime64('2022-03-25T00')+np.timedelta64(lo,'h'))&(a['utc']<np.datetime64('2022-03-25T00')+np.timedelta64(hi,'h'))
   for band,bb in bands.items():rows.append(dict(window=f'[{lo:02d},{hi:02d})',region=band,N=int((mask&bb).sum()),N_valid=int((mask&bb&a['quality']).sum())))
  with (F/'observation_window_counts.csv').open('x',newline='') as s:w=csv.DictWriter(s,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  flag=a['validity_flag'];audit=dict(PASS=True,product=stem,ZIP=download,members=members,CDF=entry(cp),HDR=entry(hp),hapi=hapi,cached_listing=receipt,records=2880,UTC_start=str(a['utc'][0]),UTC_stop=str(a['utc'][-1]),cadence_s=30,flag0=int((flag==0).sum()),flag1=int((flag==1).sum()),unknown_flags=int((~np.isin(flag,[0,1])).sum()),invalid_density=int((~np.isfinite(a['density'])|(a['density']<=0)).sum()),quality_valid=int(a['quality'].sum()),coordinates='GRS80 geodetic product contract; formal ZG datum unverified',HDR_POSIX_CRC=crc,network_bytes=budget.network_bytes,extracted_bytes=budget.extracted_bytes,official_checksum_claim=False)
 except Exception as e:audit=dict(PASS=False,error_type=type(e).__name__,error=str(e).replace(str(R),'$PROJECT'),network_bytes=budget.network_bytes,no_retry=True)
 dump('observation_acquisition_audit.json',audit);return audit

def drivers():
 prior=load(R/'experiments/tiegcm_2022_spinup_14day_v1/driver_audit.json');sources=prior['sources'];solar={};kp={};aud=[]
 for x in sources:
  p=R/x['path'];assert sha(p)==x['SHA256'];payload=load(p);key='Fobs' if 'Fobs' in payload else 'Kp';values=builder.decode(payload,key);target=solar if key=='Fobs' else kp;assert not set(target)&set(values),'Duplicate source dates'
  target.update(values);aud.append(dict(**entry(p),key=key,records=len(values),first=min(values).isoformat(),last=max(values).isoformat(),source_URL=x.get('URL','https://kp.gfz.de/en/data'),quality='definitive' if key=='Kp' else 'observed, no per-record quality flag'))
 lo,hi=date(2022,3,7),date(2022,3,28);sl,sh=lo-timedelta(days=40),hi+timedelta(days=40)
 ss=[utc(d) for d in builder.dates(sl,sh)];kk=[utc(d)+timedelta(hours=i) for d in builder.dates(lo,hi) for i in range(0,24,3)];missing_s=[x.isoformat() for x in ss if x not in solar];missing_k=[x.isoformat() for x in kk if x not in kp]
 audit=dict(PASS=not missing_s and not missing_k,sources=aud,required_solar=[str(sl),str(sh)],required_GPI=[str(lo),str(hi)],required_Fobs=102,required_Kp=176,missing_Fobs=missing_s,missing_Kp=missing_k,all_raw_sources_reused=True,network_driver_bytes=0,estimated_or_adjusted_used=False,duplicate_records=0)
 dump('driver_source_audit.json',audit)
 if not audit['PASS']:
  dump('gpi_coverage_audit.json',dict(PASS=False,status='GPI_INPUT_BLOCKED'));dump('gpi_common_interval_comparison.json',dict(status='NOT_RUN'));return None
 ds,f,a,k=builder.arrays(solar,kp,lo,hi);mean=np.array([math.fsum(solar[utc(d)+timedelta(days=i)] for i in range(-40,41))/81 for d in ds]);assert np.max(abs(a-mean))<1e-12
 oldpath=R/'data/processed/tiegcm_2022_spinup_14day_v1/gpi_2022_14day.nc';assert sha(oldpath)==prior['SHA256'];g=F/'gpi_2022_extended.nc'
 # Verify common raw daily arrays BEFORE writing any extended file.
 with Dataset(oldpath) as n:
  days=np.asarray(n['year_day'][:]);ind=[ds.index(datetime.strptime(str(int(t)),'%Y%j').date()) for t in days];comparison={v:bool(np.array_equal(np.asarray(n[v][:]),arr[ind])) for v,arr in [('f107d',f),('f107a',a),('kp',k)]};assert all(comparison.values()),'Common GPI differs; no new GPI written'
 builder.write_gpi(g,ds,f,a,k,date(2022,3,9),date(2022,3,26));g.chmod(0o444);driver=GpiDriver(g);old=GpiDriver(oldpath);maxerr=0.;commonerr=0.
 for i in range(24481):
  absolute=68*86400+i*60;day,sec=divmod(absolute,86400);v=driver.at(2022000+day,sec);assert v['f107d']>0 and v['f107a']>0 and 0<=v['Kp']<=9 and all(np.isfinite(x) for x in v.values())
  if day<=84:
   vv=old.at(2022000+day,sec);commonerr=max(commonerr,max(abs(v[x]-vv[x]) for x in v))
 for day in builder.dates(date(2022,3,9),date(2022,3,26)):
  for sec in [0,60,5399,5400,10800,43199,43200,86399]:
   v=driver.at(int(day.strftime('%Y%j')),sec);q=independent(g,int(day.strftime('%Y%j')),sec);maxerr=max(maxerr,max(abs(v[x]-q[x]) for x in v))
 assert commonerr==0 and maxerr<1e-10
 dump('gpi_common_interval_comparison.json',dict(PASS=True,arrays_bitwise_equal=comparison,raw_common_days=21,common_Kp_buckets=168,minute_node_common_max_abs=commonerr,old_GPI=entry(oldpath),new_GPI=entry(g),tolerance_relaxed=False))
 dump('gpi_coverage_audit.json',dict(PASS=True,GPI=entry(g),ndays=22,nkp=176,Fobs=102,first='2022-03-07',last='2022-03-28',valid_start='2022-03-09',valid_end='2022-03-26',NETCDF='NETCDF3_CLASSIC',schema={'year_day':'int32 YYYYDDD','f107d':'float64 sfu','f107a':'float64 sfu','kp':'float64 dimensionless (22,8)'},minute_nodes=24481,independent_mean_max_abs=float(np.max(abs(a-mean))),independent_interpolation_max_abs=maxerr,F107A='centered 81 days observed Fobs',no_missing_fill=True))
 return g

def environment_checks():
 env=dict(os.environ,OMPI_ALLOW_RUN_AS_ROOT='1',OMPI_ALLOW_RUN_AS_ROOT_CONFIRM='1',OMPI_MCA_pml='ob1',OMPI_MCA_btl='self,tcp',OMPI_MCA_osc='rdma',PMIX_MCA_gds='hash',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1');exe=R/'experiments/tiegcm2_apex2023_v1/tiegcm2.0';mpi=Path(shutil.which('mpirun'));assert mpi.resolve().is_relative_to(R)
 ldd=subprocess.check_output(['ldd',str(exe)],text=True,env=env);assert 'not found' not in ldd;libs=[]
 for line in ldd.splitlines():
  m=re.search(r'=>\s+(\S+)\s+\(',line)
  if m:
   p=Path(m[1]).resolve();libs.append(dict(name=line.split()[0],location=str(p.relative_to(R)) if p.is_relative_to(R) else '$SYSTEM_LIBRARY/'+p.name,SHA256=sha(p)))
 assert any('netcdff' in v['name'] for v in libs) and any('mpi' in v['name'] for v in libs)
 job=F/'mpi_probe_local';job.mkdir();helper='import os,json,time;print(json.dumps(dict(rank=int(os.environ["OMPI_COMM_WORLD_RANK"]),size=int(os.environ["OMPI_COMM_WORLD_SIZE"]))),flush=True);time.sleep(.3)'
 st=supervise([str(mpi),'-np','4',sys.executable,'-c',helper],job,Limits(30,2**30,20*2**30,8*2**20,2**20,.1,.2,3,10),env=env,total_dir=F);assert st['qualification']=='PASS' and st['returncode']==0 and st['cleanup_verified'] and not st['gaps']
 ranks=[json.loads(x) for x in (job/'stdout.log').read_text().splitlines() if x.startswith('{')];assert sorted(x['rank'] for x in ranks)==list(range(4)) and all(x['size']==4 for x in ranks)
 # Ordinary CPU helper forces a deadline and validates termination; never model code.
 job=F/'termination_probe_local';job.mkdir();stop=supervise([sys.executable,'-c','import time;time.sleep(20)'],job,Limits(.3,2**30,20*2**30,8*2**20,2**20,.05,.2),env=env,total_dir=F);assert stop['stop_reason']=='wall_timeout' and stop['cleanup_verified'] and stop['returncode']<0
 dump('environment_audit.json',dict(PASS=True,executable=entry(exe),mpirun=entry(mpi.resolve()),MPI_version=subprocess.check_output([str(mpi),'--version'],text=True).splitlines()[0],dependencies=libs,MPI_python_probe=dict(returncode=st['returncode'],qualification=st['qualification'],ranks=ranks,wall_s=st['elapsed_s'],cleanup_verified=True),termination_helper=dict(reason=stop['stop_reason'],returncode=stop['returncode'],cleanup_verified=True,wall_s=stop['elapsed_s']),model_launches=0,limitation='Python ranks + dynamic linkage only; no model first-step test; launch resource values must be rechecked'))
 return exe,mpi

def model_configuration(g):
 m=load(R/'experiments/tiegcm_zg_external_registration_v2/model_configuration_manifest.json');static=load(R/'experiments/tiegcm_supervision_repair_v1/B14_static_preflight.json');assert sha(OLD/'input.inp')==m['B14_cases']['2022']['input']['SHA256'];assets={}
 for group in ['base_sources','actual_compiled_resolution','build','patches']:
  for key,e in m[group].items():
   if isinstance(e,dict) and 'path' in e and 'SHA256' in e:assert sha(R/e['path'])==e['SHA256'];assets[e['path']]=e['SHA256']
 for n,h in static['input_SHA256'].items():assert sha(R/n)==h;assets[n]=h
 for e in m['B14_cases']['2022']['physical_inputs'].values():assert sha(R/e['path'])==e['SHA256'];assets[e['path']]=e['SHA256']
 for e in load(OLD/'data_audit.json')['files']:assert sha(OLD/e['file'])==e['SHA256']
 source=R/m['B14_cases']['2022']['physical_inputs']['SOURCE']['path'];sa=inspect_restart(source,[80,0,0]);sa['file']=str(source.relative_to(R));assert sa['structure_complete'] and sa['record_available'] and len(REQUIRED)==34;check_source_clock([68,0,0],[80,0,0])
 with Dataset(source) as n:
  assert n['year'][0]==2002
  fields={}
  for k in REQUIRED:
   v=n[k][:];assert np.isfinite(v.compressed()).all() and v.count()>0;fields[k]=dict(shape=list(v.shape),units=getattr(n[k],'units',None),native_masked=int(np.ma.getmaskarray(v).sum()))
  assert len(n.dimensions['lat'])==36 and len(n.dimensions['lon'])==72
 sa['required_native_fields']=fields;sa['native_mask_preserved']=True;dump('initial_state_audit.json',sa)
 original=(OLD/'input.inp').read_text();text=extended_text(original,g) if g else None;RUN.mkdir(exist_ok=False)
 if text:(RUN/'input.inp').open('x').write(text)
 oldcfg=namelist(original);newcfg=namelist(text) if text else {};diff={k:dict(old=v.replace(str(R)+'/', ''),new=newcfg[k].replace(str(R)+'/', '')) for k,v in oldcfg.items() if text and v!=newcfg[k]}
 manifest=dict(PASS=bool(g),base_release=m['base_release'],apex_update=m['apex_update'],verified_assets=assets,old_input=entry(OLD/'input.inp'),new_input=entry(RUN/'input.inp') if text else None,old_run_status=entry(OLD/'run_status.json'),old_data_audit=entry(OLD/'data_audit.json'),configuration={k:v.replace(str(R)+'/', '') for k,v in newcfg.items()},derived_runtime_defaults={k:m['B14_cases']['2022'][k] for k in ['ibgrddata','zbound_formula','zbound_approx_km','GSWM_migrating_diurnal','GSWM_migrating_semidiurnal','GSWM_nonmigrating_diurnal','GSWM_nonmigrating_semidiurnal']},source_identity='official complete smax 2002 day80, unchanged SOURCE_START; independently cold-start year2022',not_author_2023_config=True,label_legacy_unchanged='Old LABEL says nine-day/spinup unverified; actual START/STOP/protocol determine17day run. Retained to avoid unrelated config change.',current_restart_consistency='FAIL; not used by this fresh continuous protocol')
 dump('model_configuration_manifest.json',manifest);dump('configuration.json',manifest['configuration']);dump('configuration_diff.json',dict(PASS=bool(g),allowed=['STOP','SECSTOP','OUTPUT','SECOUT','GPI_NCFILE'],changes=diff,no_other_physics_change=True,output_primary_volumes=18,output_secondary_volumes=17,primary_records=18,secondary_records=408,expected_steps=24480))
 return manifest

def resource_check():
 free=shutil.disk_usage(R).free;mem=int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1])*1024;active=[]
 for p in Path('/proc').glob('[0-9]*/comm'):
  try:
   if p.read_text().strip()=='tiegcm2.0':active.append(int(p.parent.name))
  except OSError:pass
 costs=load(R/'experiments/causal_density_new_date_validation_v1/expansion_audit.json');b=costs['budgets'][0];assert 1.5*b['predicted_wall_s_max']<4800
 probe=RUN/'write_probe_local';probe.open('x').write('exclusive write check');probe.unlink()
 out=dict(PASS=free>25*2**30 and mem>16*2**30 and len(os.sched_getaffinity(0))>=4 and not active,free_disk_bytes=free,MemAvailable_bytes=mem,cpu_affinity_count=len(os.sched_getaffinity(0)),active_model_count=len(active),output_dir=str(RUN.relative_to(R)),output_directory_empty_of_NetCDF=not list(RUN.glob('*.nc')),exclusive_writable=True,history_estimation_evidence=costs['historical_cost_evidence'],estimate=b,limits=dict(wall_s=4800,supervisor_stop_s=4770,cleanup_reserve_s=30,RSS_bytes=16*2**30,output_bytes=5*2**30,disk_floor_bytes=20*2**30,MPI=4,OMP=1,model_max_launches=1,retry=0,GPU=0),resources_dynamic_recheck_required=True)
 dump('resource_preflight.json',out);return out

def main():
 start=time.perf_counter();cpu=time.process_time();assert F.exists() and not (F/'preflight.json').exists();obs=acquisition();print('Observation acquisition checked; no density metrics computed',flush=True);g=drivers();print('Raw drivers and GPI audited',flush=True);model=model_configuration(g);exe,mpi=environment_checks();rp=resource_check()
 evaluation=dict(identity='HINDCAST / PROVISIONAL Map-A / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED',date='2022-03-25',primary='B14 new continuous run',reference='2021-03-25 frozen B14 results only',cutoffs=[6,18],history_hours=3,half_open=True,future_hours=[1,3,6],nonoverlap_blocks=[[0,1],[1,3],[3,6]],methods06=['Raw','GlobalAdaptive06'],methods18=['Raw','GlobalAdaptive18','LatitudeAdaptive18','Stale06'],estimator='median ln(obs)-ln(model)',latitude_definitions=['abs(lat)<30','30<=abs(lat)<60','abs(lat)>=60'],min_history_and_future_region_N=30,no_fallback=True,Stale06='same date B14 03-06 historical coefficient; never March23/24',future_poison_factor=1e20,freeze_parameters_before_future_metrics=True,joint=['RMSE strictly lower','relative RMS strictly lower','relative P95 no higher','abs low-lat relative Bias no higher'],NA_never_PASS=True,metric_source=entry(R/'src/evaluation/swarm_crossyear.py'),latitude_source=entry(R/'src/evaluation/causal_density_latitude.py'),Map_A_source=entry(R/'src/atmosphere/provisional_coordinate_adapter.py'),operator_source=entry(R/'src/atmosphere/causal_observation_operator.py'),hourly_reader_source=entry(R/'src/atmosphere/hourly_tiegcm_observation.py'),after_run_gates=['direct parent exit0 and4 normal exits','24480steps,18primary,408hourlysecondary','native cold echo exception only; warm fields valid','NetCDF SHA and UTC full target day+Mar26boundary','all eight columns valid no extrapolation for actualSwarm samples','common IDs; historical-only coefficients and poison test','independent metrics and joint review'],no_evaluation_or_fitting_this_task=True,no_IID_significance=True)
 dump('frozen_evaluation_protocol.json',evaluation)
 launch=dict(start_UTC='2022-03-09T00:00:00Z',stop_UTC='2022-03-26T00:00:00Z',step_s=60,steps=24480,mode='independent cold-start continuous; no restart or append',cwd=str(RUN.relative_to(R)),argv=[str(mpi.relative_to(R)),'-np','4',str(exe.relative_to(R)),'input.inp'],executable=entry(exe),input=entry(RUN/'input.inp') if g else None,GPI=entry(g) if g else None,environment_activation='source scripts/activate_tiegcm.sh',limits=rp['limits'],launch_authorization='NOT_GRANTED_THIS_TASK; next explicit user instruction and --authorize-17day-run required',model_started=False,once_marker='run/launch_once.json created by supervisor; never remove to retry',supervisor=entry(R/'src/runtime/supervisor.py'),original_environment_policy='same MPI5 stack and runtime settings as old B14; inherited environment plus explicit MPI transport and OMP settings',frozen_evaluation_SHA256=sha(F/'frozen_evaluation_protocol.json'))
 dump('launch_protocol.json',launch);dump('run_protocol.json',launch)
 ready=obs['PASS'] and bool(g) and model['PASS'] and rp['PASS'];dump('preflight.json',dict(PASS=ready,status='RUN_READY_NOT_LAUNCHED' if ready else 'BLOCKED',observation_PASS=obs['PASS'],GPI_PASS=bool(g),model_static_PASS=model['PASS'],resource_PASS=rp['PASS'],new_model_launches=0,correction_fits=0,metrics_computed=0,external_datum='UNVERIFIED',restart='FAIL',DART='NOT_ADMITTED',real_orbit='BLOCKED'))
 for n,h in load(F/'protected_assets_local.json').items():assert sha(R/n)==h,n
 dump('preparation_result.json',dict(status='RUN_READY_NOT_LAUNCHED' if ready else 'BLOCKED',wall_s=time.perf_counter()-start,CPU_s=time.process_time()-cpu,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,old_assets_unchanged=True,new_model_launches=0));print('Preparation complete; model NOT LAUNCHED',flush=True)
if __name__=='__main__':main()
