"""Read-only post-wait engineering acceptance. No fit, error metric or datum release."""
from pathlib import Path
import sys,json,re,hashlib,datetime,collections
import numpy as np
from netCDF4 import Dataset,num2date
ROOT=Path(__file__).resolve().parents[2]
START=datetime.datetime(2022,3,9);STOP=datetime.datetime(2022,3,26);STEPS=24480
CHECKS=['supervision','MPI_rank_exits','step_logs','output_files','target_observation_queries']
def require(ok,message):
 if not ok:raise ValueError(message)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def parse_progress(text,steps=STEPS,start=START):
 require(len(re.findall(r'(?m)^NORMAL EXIT\s*$',text))==1,'Each rank requires exactly one NORMAL EXIT')
 require(not re.search(r'\b(?:NaN|Inf|ERROR)\b|MPI_ABORT|bad isec_req',text,re.I),'Fatal model log')
 records=re.findall(r'Step\s+(\d+) of\s+(\d+) mtime=\s*(\d+)\s+(\d+)\s+(\d+)',text)
 numbers=[int(r[0]) for r in records];require(numbers==list(range(1,steps+1)) if steps<=100 else numbers==list(range(10,steps+1,10)),'Missing/duplicate/out-of-order step progress')
 for step,total,day,hour,minute in records:
  require(int(total)==steps,'Incorrect planned total');t=start+datetime.timedelta(minutes=int(step));require([int(day),int(hour),int(minute)]==[int(t.strftime('%j')),t.hour,t.minute],'Step/calendar mismatch')
 return dict(final_step=steps,progress_records=len(records),logging_stride=1 if steps<=100 else 10,limit='Progress + independent warm iter/time checks; no synthetic logs substitute for actual process receipts')

def inspect_density_record(n,index):
 from scripts.run_tiegcm_2022_14day import field
 for name,unit in [('DEN','g/cm3'),('ZG','cm')]:
  require(name in n.variables,'Missing '+name);v=n[name];require(v.dimensions==('time','ilev','lat','lon') and v.units==unit,'Wrong native density schema')
  # Preserve original fill and explicit NaN handling; never replace by zero.
  v.set_auto_mask(False);native=np.asarray(v[index]);raw=np.asarray(native,float);mask=np.zeros(raw.shape,bool)
  for key in ['missing_value','_FillValue']:
   if key in v.ncattrs():
    for fill in np.asarray(v.getncattr(key)).reshape(-1):mask|=native==np.asarray(fill,dtype=native.dtype)
  require(np.isfinite(raw).all() and not mask.any() and not (abs(raw)>1e30).any(),'Invalid warm '+name)
  if name=='DEN':require((raw>0).all(),'Nonpositive DEN')
  else:require((np.diff(raw,axis=0)>0).all(),'ZG nonmonotonic')
 return dict(valid=True,DEN_units='g/cm3',ZG_units='cm',dimensions=['time','ilev','lat','lon'],conversion_to_SI=[1000,.01])

def cold_identity(n,t,index):
 """Primary native cold echo inherits iter, may lack diagnostic DEN/ZG/N2."""
 if t!=START:return False
 require(getattr(n,'history_type',None)=='primary' and index==0,'Only first primary is registered cold echo')
 tv=n['time'];require(int(tv.initial_year)==2022 and int(tv.initial_day)==68 and np.array_equal(tv.initial_mtime,[68,0,0]),'Cold echo identity missing')
 return True

def validate_timelines(primary,secondary,cold_count):
 require(primary==[START+datetime.timedelta(days=i) for i in range(18)],'Primary full calendar incomplete')
 require(secondary==[START+datetime.timedelta(hours=i) for i in range(1,409)],'Secondary full calendar incomplete')
 require(cold_count==1,'Cold exception count wrong')
 return dict(primary_records=18,secondary_records=408,final_UTC=STOP.isoformat()+'Z')

def driver_difference(value,expected):
 require(not np.ma.is_masked(value),'Missing actual driver')
 value=float(value);require(np.isfinite(value),'Nonfinite actual driver')
 return abs(value-expected)

def inspect_outputs(run):
 # Reuse mature, year-adapted primary completeness and full warm physical-field checks.
 from scripts.run_tiegcm_2022_14day import basic_file,field
 inventories=[];primary=[];secondary=[];cold_count=0;grids=None
 from atmosphere.tiegcm_drivers import GpiDriver
 drv=GpiDriver(ROOT/'experiments/tiegcm_2022_mar25_preparation_v1/gpi_2022_extended.nc');driver_max=0.
 for kind,volumes in [('primary',18),('secondary',17)]:
  paths=sorted(run.glob(kind+'_*.nc'));require([p.name for p in paths]==[f'{kind}_{i:03d}.nc' for i in range(1,volumes+1)],'Wrong output file set '+kind)
  for path in paths:
   require(path.stat().st_size<=256*2**20,'Volume budget exceeded');basic_file(path)
   with Dataset(path) as n:
    require(n.history_type==kind and n.data_model=='NETCDF3_CLASSIC','History type/format mismatch')
    require(len(n.dimensions['time'])==(1 if kind=='primary' else 24),'Wrong per-volume record count')
    require(int(np.asarray(n['timestep'][:]).item())==60 and np.all(n['calendar_advance'][:]==1),'Step/calendar setting mismatch')
    actual_grid=[np.asarray(n[k][:]) for k in ['lat','lon','lev','ilev']]
    for k,a in zip(['lat','lon','lev','ilev'],actual_grid):require(np.array_equal(a,np.load(ROOT/f'data/processed/static/{k}.npy')),'Grid mismatch '+k)
    if grids is None:grids=actual_grid
    require(all(np.array_equal(a,b) for a,b in zip(grids,actual_grid)),'Grid changed')
    cf=num2date(n['time'][:],n['time'].units);times=[]
    for i,v in enumerate(cf):
     t=datetime.datetime(v.year,v.month,v.day,v.hour,v.minute,v.second);times.append(t)
     require(int(n['year'][i])==2022 and np.array_equal(n['mtime'][i],[int(t.strftime('%j')),t.hour,t.minute]),'CF time and mtime disagree')
     require(int(n['day'][i])==int(t.strftime('%j')),'Native day disagrees')
     cold=cold_identity(n,t,i)
     if cold:cold_count+=1
     else:
      # Cold source iter is inherited; NEVER infer completed updates by subtracting it.
      elapsed=int((t-START).total_seconds()/60);require(int(n['iter'][i])==68*1440+elapsed,'Warm iter not aligned with actual elapsed minutes')
     if kind=='secondary':
      inspect_density_record(n,i)
      expected=drv.at(2022000+int(t.strftime('%j')),t.hour*3600+t.minute*60)
      for name,value in expected.items():driver_max=max(driver_max,driver_difference(field(n[name])[i],value))
      require(driver_max<1e-10,'Actual model drivers differ from frozen GPI')
    require(all(a<b for a,b in zip(times,times[1:])),'Nonmonotonic within-volume time')
    (primary if kind=='primary' else secondary).extend(times)
    inventories.append(dict(file=path.name,SHA256=sha(path),bytes=path.stat().st_size,records=len(times),first_UTC=times[0].isoformat()+'Z',last_UTC=times[-1].isoformat()+'Z'))
 validate_timelines(primary,secondary,cold_count)
 return dict(files=inventories,primary_records=len(primary),secondary_records=len(secondary),actual_GPI_max_abs_difference=driver_max,cold_primary_echo=1,cold_iter_not_used=True,warm_iter_and_step_alignment=True,target_day_hourly_frames=25,primary_DEN_ZG='not primary restart variables; no requirement to invent them',secondary_DEN_ZG='ilev fully checked, including all warm records')

def validate_exits(run,run_id,protocol):
 files=sorted(run.glob('rank_*_exit.json'));require([p.name for p in files]==[f'rank_{i:03d}_exit.json' for i in range(4)],'Four rank direct-wait receipts required')
 rows=[];sid=json.loads((run/'status.json').read_text())['identity']['sid']
 for rank,path in enumerate(files):
  e=json.loads(path.read_text());require(e['rank']==rank and e['size']==4 and e['run_id']==run_id,'Rank identity mismatch')
  require(e['returncode']==0 and e['error'] is None and not e['received_signals'] and e['wait_source']=='direct subprocess.Popen.wait','Rank model child did not exit normally')
  require(e['model_SHA256']==protocol['executable']['SHA256'] and e['input_SHA256']==protocol['input']['SHA256'],'Rank model/input identity mismatch')
  require(e['ended_unix']>=e['started_unix'] and e['child_pid']>0,'Invalid process wait evidence')
  require(e['wrapper_sid']==sid and e['child_sid']==sid,'Rank/model escaped monitored session')
  start=json.loads((run/f'rank_{rank:03d}_started.json').read_text());require(all(start[k]==e[k] for k in start),'Rank started/exit receipts disagree')
  rows.append(dict(rank=rank,returncode=e['returncode'],receipt_SHA256=sha(path),model_SHA256=e['model_SHA256'],input_SHA256=e['input_SHA256']))
 return dict(ranks=rows,source='rank wrapper direct child wait plus root MPI parent wait; not inferred from NORMAL EXIT count')

def query_coverage(run,inventory):
 from observations.density_catalog import read_swarm_pod
 from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
 from atmosphere.causal_observation_operator import map_a_queries,observe_map_a
 prep=ROOT/'experiments/tiegcm_2022_mar25_preparation_v1';a=json.loads((prep/'observation_acquisition_audit.json').read_text());h=a['hapi'];require(sha(ROOT/h['path'])==h['SHA256'],'Observation contract changed')
 _,obs,_=read_swarm_pod(ROOT/a['CDF']['path'],ROOT/h['path'],a['CDF']['SHA256'],satellite='A');eligible=obs['quality'];require(eligible.sum()>0,'No eligible real observations')
 # Only25 target-day model frames are loaded; do not cache all17days.
 entries=inventory['files'];files=[run/e['file'] for e in entries if e['file'].startswith('secondary_') and e['last_UTC']>='2022-03-25T00:00:00Z'];expected={e['file']:e['SHA256'] for e in entries}
 p=HourlyTiegcmObservation(files,expected,'2022-03-25T00:00:00','2022-03-26T00:00:00','2022 new B14 continuous');reasons=collections.Counter();success=0;failure_examples=[]
 try:
  for t,q in zip(obs['utc'][eligible],map_a_queries(obs['utc'][eligible],obs['latitude'][eligible],obs['longitude'][eligible],obs['altitude'][eligible])):
   result,coords=observe_map_a(p,q);columns=result.metadata.get('columns',[])
   if result.valid and len(columns)==8:success+=1
   else:
    why=result.reason or 'INCOMPLETE_EIGHT_COLUMNS';reasons[why]+=1
    if len(failure_examples)<10:failure_examples.append(dict(UTC=str(t),reason=why))
 finally:p.close()
 total=int(eligible.sum());require(success==total,'Incomplete target-day eight-column coverage: '+json.dumps(dict(eligible=total,success=success,failed=total-success,reasons=dict(reasons),examples=failure_examples)))
 return dict(eligible=total,success=success,failed=total-success,reason_counts=dict(reasons),failure_examples=failure_examples,eight_columns=True,zero_weight_columns_checked=True,extrapolation=False,identity='PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED',no_density_error_metrics=True)

def accept_run(run,run_id,protocol,query_observations=True):
 run=Path(run);run.resolve().relative_to(ROOT);checks={k:dict(status='NOT_RUN',evidence='No actual completed model available') for k in CHECKS}
 answer=dict(ACTUAL_MODEL_RUN='NOT_RUN',overall='NOT_RUN',checks=checks,scientific_gates_unchanged=True)
 if not (run/'status.json').exists():
  if run.exists():
   answer.update(ACTUAL_MODEL_RUN='UNKNOWN',overall='FAIL');checks['supervision']=dict(status='FAIL',evidence='Reserved/partial run exists without completed direct wait; no inferred exit code')
  return answer
 answer['ACTUAL_MODEL_RUN']='ATTEMPTED'
 def check(name,function):
  try:checks[name]=dict(status='PASS',evidence=function());return True
  except Exception as e:checks[name]=dict(status='FAIL',error_type=type(e).__name__,evidence=str(e).replace(str(ROOT),'$PROJECT'));return False
 def supervision():
  s=json.loads((run/'status.json').read_text());require(s['returncode']==0 and s['qualification']=='PASS' and not s['gaps'] and s['cleanup_verified'],'MPI parent/supervision did not pass');require(s['wait_source']=='direct subprocess.Popen.wait' and s['elapsed_s']<=4800,'No bounded direct parent wait')
  require(sha(run/'input.inp')==protocol['input']['SHA256'],'Staged input changed')
  for e in [protocol['input'],protocol['GPI'],protocol['executable']]:require(sha(ROOT/e['path'])==e['SHA256'],'Input provenance changed during/after model run')
  return dict(returncode=0,wait_source=s['wait_source'],cleanup_verified=True,status_SHA256=sha(run/'status.json'),input=protocol['input'],GPI=protocol['GPI'],executable=protocol['executable'])
 if not check('supervision',supervision):answer['overall']='FAIL';return answer
 ok=check('MPI_rank_exits',lambda:validate_exits(run,run_id,protocol))
 if ok:check('step_logs',lambda:dict(per_rank=[parse_progress((run/f'rank_{i:03d}.log').read_text()) for i in range(4)]))
 if check('output_files',lambda:inspect_outputs(run)) and query_observations:check('target_observation_queries',lambda:query_coverage(run,checks['output_files']['evidence']))
 answer['overall']='PASS' if all(v['status']=='PASS' for v in checks.values()) else 'FAIL'
 return answer
