"""V18 single CPU evaluation, separate history and scoring processes; no model entry."""
from pathlib import Path
import sys,os,json,csv,hashlib,time,datetime,resource,subprocess
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R),str(R/'src'),str(R/'scripts')]
import numpy as np,cdflib
from evaluation.causal_density_latitude import fit_global_history,fit_history,apply_global,apply_latitude,latitude_band,supported_metric,assess_joint
from evaluation.late_day_correction import RollingOrigin
from evaluation.swarm_density_comparison import quality_mask
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from atmosphere.causal_observation_operator import map_a_queries,observe_map_a
from runtime.readonly_audit_warning_channel import WarningChannel
F=R/'experiments/tiegcm_2022_mar25_density_validation_v18';DAY='2022-03-25'
OLD=R/'experiments/causal_density_new_date_validation_v1'
PRE=R/'experiments/tiegcm_2022_mar25_preparation_v1'
V17=R/'experiments/tiegcm_2022_mar25_postrun_acceptance_v17'
ACT=R/'experiments/tiegcm_2022_mar25_execution_review_v1/actual_run'
CDF=R/'data/raw/tiegcm_2022_mar25_preparation_v1/SW_OPER_DNSAPOD_2__20220325T000000_20220325T235930_0301.cdf'
IDENTITY='HINDCAST / PROVISIONAL Map-A / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(Path(p).read_text())
def dump(name,x):
 p=F/name;p.resolve().relative_to(R)
 with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False)
def rows(p):return list(csv.DictReader(Path(p).open()))
def table(name,x):
 with (F/name).open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(x[0]),lineterminator='\n');w.writeheader();w.writerows(x)
def epoch():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def arrays(start=None,stop=None,density=True):
 """Range access preserves the exact original quality rule and instantaneous density."""
 with cdflib.CDF(CDF) as c:
  t=cdflib.cdfepoch.to_datetime(c.varget('time'));sel=np.ones(len(t),bool) if start is None else (t>=np.datetime64(start))&(t<np.datetime64(stop));ii=np.flatnonzero(sel);assert len(ii) and np.all(np.diff(ii)==1)
  a={'utc':t[sel]}
  for k in ['latitude','longitude','altitude','validity_flag']+(['density'] if density else []):a[k]=c.varget(k,startrec=int(ii[0]),endrec=int(ii[-1]))
  coord=np.isfinite(a['latitude'])&np.isfinite(a['longitude'])&np.isfinite(a['altitude'])&(abs(a['latitude'])<=90)&(abs(a['longitude'])<=180)&(a['altitude']>0)
  if density:
   a['quality'],flags=quality_mask(a['density'],a['validity_flag']);a['quality']&=coord
   if flags['unknown'].any():raise ValueError('Unknown quality flags')
  else:a['quality']=(a['validity_flag']==0)&coord
 return a

def model(a,start,stop,phase):
 src=load(F/'source_manifest.json');files=[R/x['path'] for x in src['target_models']];expected={p.name:x['SHA256'] for p,x in zip(files,src['target_models'])};wd=F/(phase+'_warnings_local');wd.mkdir(exist_ok=False)
 reader=R/'src/atmosphere/hourly_tiegcm_observation.py'
 with WarningChannel(wd,{reader:sha(reader)}):p=HourlyTiegcmObservation(files,expected,start,stop,'V16_094fcac3949c4e2e981d3baac1a5d8bf_B14')
 pred=[];trace=[]
 try:
  for index,q in enumerate(map_a_queries(a['utc'],a['latitude'],a['longitude'],a['altitude'])):
   result,co=observe_map_a(p,q)
   if not result.valid or len(result.metadata['columns'])!=8:raise ValueError('Real eight-column admission failed at '+str(a['utc'][index]))
   pred.append(result.rho_kg_m3);trace.append(dict(UTC=str(a['utc'][index]),coordinates=co,metadata=result.metadata))
 finally:p.close()
 with (F/(phase+'_queries_local.json')).open('x') as f:json.dump(trace,f)
 return np.array(pred),dict(requested=len(pred),success=len(pred),failure=0,columns=8*len(pred),zero_weight_columns_checked=True,no_extrapolation=True)

def prepare():
 F.resolve().relative_to(R);assert not F.exists(),'No existing evaluation may be overwritten';F.mkdir()
 acceptance=load(V17/'acceptance.json');assert acceptance['overall']=='PASS';result=load(V17/'result.json');assert result['overall']=='ENGINEERING_PASS' and result['batch_parent_returncode']==0
 oldprotocol=load(PRE/'frozen_evaluation_protocol.json')
 for k in ['metric_source','latitude_source','Map_A_source','operator_source','hourly_reader_source']:
  x=oldprotocol[k];assert sha(R/x['path'])==x['SHA256'],k
 assert sha(CDF)=='d2f647f723f774a446e6c07c9b1108c1dc521b76bb21a2d524d321d379b440a8'
 # Protect every existing tracked scientific asset; preserve historical untracked logs too by never opening them for writing.
 tracked=subprocess.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0');protected={n:sha(R/n) for n in tracked if n and (R/n).is_file() and n not in ['STATUS.md','WORKLOG.md','.gitignore']}
 manifest=rows(R/'experiments/tiegcm_2022_mar25_formal_run_v1/model_output_manifest.csv');out=[]
 for x in manifest:
  p=ACT/Path(x['file']).name;assert sha(p)==x['SHA256'];out.append(dict(path=str(p.relative_to(R)),SHA256=x['SHA256'],bytes=p.stat().st_size))
 target=[x for x in out if Path(x['path']).name in ['secondary_016.nc','secondary_017.nc']];assert len(target)==2
 with cdflib.CDF(CDF) as c:
  assert c.globalattsget()['TITLE']==[CDF.stem] and c.globalattsget()['TIME SYSTEM']==['UTC'];assert c.varinq('time').Data_Type==31
  for k,u in [('density','kg/m3'),('latitude','deg'),('longitude','deg'),('altitude','m')]:assert c.varattsget(k)['UNITS']==u
 a=arrays(density=False);assert len(a['utc'])==2880 and a['utc'][0]==np.datetime64(DAY) and a['utc'][-1]==np.datetime64(DAY+'T23:59:30') and np.all(np.diff(a['utc'])==np.timedelta64(30,'s'));assert a['quality'].all()
 info=load(PRE/'observation_acquisition_audit.json')['hapi'];assert sha(R/info['path'])==info['SHA256'];contract=load(R/info['path']);assert contract['x_dataset']=='SW_OPER_DNSAPOD_2_' and any('GRS80' in x.get('description','') for x in contract['parameters'])
 assert sha(OLD/'correction_parameters.json')=='bd72dd92e08cd8e6e4ba3ad760662642db6742850553a8f59d757fed7870eb51'
 src=dict(run_id='094fcac3949c4e2e981d3baac1a5d8bf',CDF=dict(path=str(CDF.relative_to(R)),SHA256=sha(CDF)),hapi=info,model_outputs=out,target_models=target,protected_SHA256=protected,reference_2021={n:sha(OLD/n) for n in ['correction_parameters.json','metrics.csv','region_metrics.csv','joint_assessment.csv','frozen_protocol.json']})
 dump('source_manifest.json',src)
 protocol=dict(**oldprotocol,V18_authorization='User authorizes evaluation; original no_evaluation_or_fitting_this_task is historical scope and remains unmodified in original file',original_protocol_SHA256=sha(PRE/'frozen_evaluation_protocol.json'),stages=['metadata and SHA admission without future density access','history-only separate process reads only 03-06 and15-18 density records and freezes coefficients','separate scoring process reads future density; separate-cutoff poison before any score','persist Raw metrics before applying corrections','frozen corrected metrics and independent verification'],coefficient_file_exclusive=True,rtol=1e-13,atol=0,code_HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip(),new_scripts={n:sha(R/n) for n in ['scripts/run_density_validation_v18.py','scripts/verify_density_validation_v18.py','scripts/plot_density_validation_v18.py','scripts/launch_density_validation_v18.py']},frozen_UTC=epoch())
 dump('frozen_protocol.json',protocol);dump('preflight.json',dict(PASS=True,V17_ENGINEERING_PASS=True,all35_model_SHA_match=True,target_day_files=len(target),metadata_records=2880,future_density_values_read=0,initial_flags_nominal=2880,frozen_science_sources_match=True,original_protocol_unchanged=True,UTC=epoch()))
 dump('commands.json',dict(prepare='python scripts/run_density_validation_v18.py prepare',unique_supervised_analysis='python scripts/launch_density_validation_v18.py',stages=['history','score'],model_commands=0,no_downloads=True))
 print('V18 ADMISSION AND PROTOCOL FREEZE PASS',flush=True)

def history():
 assert not (F/'correction_parameters.json').exists();params={};audits=[];cal=[]
 for h in [6,18]:
  start=DAY+f'T{h-3:02d}:00:00';stop=DAY+f'T{h:02d}:00:00';a=arrays(start,stop);assert len(a['utc'])==360 and a['quality'].all();p,au=model(a,start,stop,'history'+str(h));au['cutoff']=h;audits.append(au)
  if h==6:g,_=fit_global_history(a['utc'],a['latitude'],a['density'],p,a['quality'],day=DAY,hour=h);params['GlobalAdaptive06']=g
  else:
   c,_=fit_history(a['utc'],a['latitude'],a['density'],p,a['quality'],day=DAY,hour=h);params['GlobalAdaptive18']=c['global_fit'];params['LatitudeAdaptive18']=c['latitude']
  np.savez_compressed(F/f'history{h}_local.npz',**a,raw=p)
  for i,e in enumerate(np.log(a['density'])-np.log(p)):cal.append(dict(cutoff=h,UTC=str(a['utc'][i]),band=['low','mid','high'][latitude_band(a['latitude'])[i]],log_residual=float(e)))
 params['Stale06_reference']='GlobalAdaptive06 same date, exact coefficient';dump('correction_parameters.json',dict(date=DAY,protocol_SHA256=sha(F/'frozen_protocol.json'),observation_SHA256=sha(CDF),parameters=params,freeze_UTC=epoch(),future_density_records_read_by_fitting=0));digest=sha(F/'correction_parameters.json');dump('parameter_freeze_receipt.json',dict(SHA256=digest,UTC=epoch(),future_scores_computed=0));table('calibration_residuals.csv',cal);dump('history_admission.json',dict(PASS=True,queries=audits,only_history_density_access=True));print('V18 HISTORY PARAMETER FREEZE COMPLETE',flush=True)

def score():
 receipt=load(F/'parameter_freeze_receipt.json');assert sha(F/'correction_parameters.json')==receipt['SHA256'];pars=load(F/'correction_parameters.json')['parameters'];a=arrays();assert a['quality'].all() and len(a['utc'])==2880;p,qa=model(a,DAY+'T00:00:00','2022-03-26T00:00:00','full_day');dump('query_admission.json',dict(PASS=True,**qa,quality_eligible=2880,quality_flag_counts={str(k):int((a['validity_flag']==k).sum()) for k in np.unique(a['validity_flag'])},future_first_access_after_parameter_receipt=True,UTC=epoch()))
 for h in [6,18]:
  old=np.load(F/f'history{h}_local.npz');m=RollingOrigin(DAY,h).masks(a['utc'])['analysis'];np.testing.assert_array_equal(old['density'],a['density'][m]);np.testing.assert_allclose(old['raw'],p[m],rtol=1e-13,atol=0);p[m]=old['raw']  # preserve the exact historical inputs, not a re-read with another time origin
 poison=[]
 for h in [6,18]:
  poisoned=a['density'].copy();poisoned[a['utc']>=np.datetime64(DAY+f'T{h:02d}')]*=1e20
  if h==6:c,_=fit_global_history(a['utc'],a['latitude'],poisoned,p,a['quality'],day=DAY,hour=h);assert c==pars['GlobalAdaptive06']
  else:c,_=fit_history(a['utc'],a['latitude'],poisoned,p,a['quality'],day=DAY,hour=h);assert c['global_fit']==pars['GlobalAdaptive18'] and c['latitude']==pars['LatitudeAdaptive18']
  poison.append(dict(cutoff=h,PASS=True,separate_input=True,exact_dict_equality=True))
 dump('future_poison_test.json',dict(PASS=True,factor=1e20,checks=poison,Stale06_is_same_frozen_Global06=True,parameter_SHA256=receipt['SHA256'],scores_not_started=True,UTC=epoch()))
 band=latitude_band(a['latitude']);regions={'all':np.ones(len(p),bool),**{k:band==i for i,k in enumerate(['low','mid','high'])}};metrics=[];regrows=[];points=[];joints=[];coverage=[];gap=[];scoremap={}
 def calculate(h,met,pred,support):
  masks=RollingOrigin(DAY,h).masks(a['utc']);masks['block_0_1h']=masks['future_1h'];out={}
  for win,wm in masks.items():
   for reg,rm in regions.items():
    s=supported_metric(pred,a['density'],a['quality'],a['quality'],wm&rm,support);row=dict(year=2022,case='B14',cutoff=h,window=win,region=reg,method=met,**s);(metrics if reg=='all' else regrows).append(row);out[win,reg]=s
    if met!='Raw':
     m=wm&rm&support;oldabs=abs(p[m]-a['density'][m]);newabs=abs(pred[m]-a['density'][m]);points.append(dict(cutoff=h,window=win,region=reg,method=met,N=int((wm&rm).sum()),supported=int(m.sum()),improved=int((newabs<oldabs).sum()),worsened=int((newabs>oldabs).sum()),unchanged=int((newabs==oldabs).sum())))
   ids=a['utc'][wm].astype('<i8').tobytes();coverage.append(dict(cutoff=h,window=win,method=met,N=int(wm.sum()),quality_N=int((wm&a['quality']).sum()),supported_N=int((wm&support).sum()),query_coverage=1.,common_ID_SHA256=hashlib.sha256(ids).hexdigest()))
  return out
 # Raw is evaluated and persisted first; coefficients already immutable but have not been applied.
 for h in [6,18]:scoremap[h,'Raw']=calculate(h,'Raw',p,np.ones(len(p),bool))
 table('raw_metrics.csv',metrics.copy());table('raw_region_metrics.csv',regrows.copy());dump('raw_scoring_receipt.json',dict(UTC=epoch(),before_any_correction_application=True,parameter_SHA256=receipt['SHA256']))
 predictions={}
 for h in [6,18]:
  pp={'Raw':p,f'GlobalAdaptive{h:02d}':apply_global(p,pars[f'GlobalAdaptive{h:02d}'])};support=np.ones(len(p),bool)
  if h==18:pp['LatitudeAdaptive18'],support=apply_latitude(p,a['latitude'],pars['LatitudeAdaptive18']);pp['Stale06']=apply_global(p,pars['GlobalAdaptive06'])
  predictions[h]=pp
  for met,pred in list(pp.items())[1:]:
   sup=support if met=='LatitudeAdaptive18' else np.ones(len(p),bool);ss=calculate(h,met,pred,sup);scoremap[h,met]=ss
   for win in RollingOrigin(DAY,h).masks(a['utc']):
    if win=='analysis':continue
    raw=scoremap[h,'Raw'];flags=assess_joint(raw[win,'all'],ss[win,'all'],{k:raw[win,k] for k in ['low','mid','high']},{k:ss[win,k] for k in ['low','mid','high']},bool(sup[RollingOrigin(DAY,h).masks(a['utc'])[win]].all()));base=raw[win,'all'];co=ss[win,'all'];joints.append(dict(year=2022,case='B14',cutoff=h,window=win,method=met,N=co['n'],RMSE_gain_pct=100*(1-co['RMSE']/base['RMSE']) if co['RMSE'] is not None else None,relative_RMS_gain_pct=100*(1-co['relative_RMS']/base['relative_RMS']) if co['relative_RMS'] is not None else None,**flags))
  masks=RollingOrigin(DAY,h).masks(a['utc']);hist=masks['analysis'];e=np.log(a['density'])-np.log(p)
  for win,m in masks.items():
   for reg,rm in regions.items():
    hn=int((hist&rm).sum());fn=int((m&rm).sum());bh=float(np.median(e[hist&rm])) if hn>=30 else None;bf=float(np.median(e[m&rm])) if fn>=30 else None;gap.append(dict(cutoff=h,window=win,region=reg,history_N=hn,future_N=fn,b_H=bh,b_F_DIAGNOSTIC_ONLY=bf,delta_b=bf-bh if bh is not None and bf is not None else None,future_median_used_for_prediction=False))
 table('metrics.csv',metrics);table('region_metrics.csv',regrows);table('joint_assessment.csv',joints);table('time_block_metrics.csv',[x for x in metrics if x['window'].startswith('block_')]);table('pointwise_diagnostics.csv',points);table('coverage.csv',coverage);table('history_future_residual_gap.csv',gap)
 # Complete observations, matched predictions and IDs are LOCAL ONLY.
 np.savez_compressed(F/'matched_local.npz',**a,raw=p,**{f'{h}_{met}':v for h,pp in predictions.items() for met,v in pp.items()})
 with (F/'common_sample_ids_local.csv').open('x',newline='') as f:
  w=csv.writer(f);w.writerow(['observation_id','UTC','latitude_deg','longitude_deg','GRS80_height_m','flag','quality','model_density_kg_m3'])
  for i,t in enumerate(a['utc']):w.writerow(['Swarm/A/0301/'+str(t)+'Z',str(t)+'Z',a['latitude'][i],a['longitude'][i],a['altitude'][i],a['validity_flag'][i],a['quality'][i],p[i]])
 compare=[];oldmetrics=rows(OLD/'metrics.csv');oldregions=rows(OLD/'region_metrics.csv')
 for old in oldmetrics+oldregions:
  if old['case']=='B14':compare.append(dict(year=2021,**{k:old[k] for k in ['cutoff','window','region','method','n','RMSE','relative_RMS','relative_P95','bias','relative_bias','log_RMS','Pearson','status']}))
 for x in metrics+regrows:compare.append(dict(year=2022,**{k:x[k] for k in ['cutoff','window','region','method','n','RMSE','relative_RMS','relative_P95','bias','relative_bias','log_RMS','Pearson','status']}))
 table('cross_year_comparison.csv',compare)
 from verify_density_validation_v18 import verify
 verify()
 from plot_density_validation_v18 import plot
 plot()
 assert sha(F/'correction_parameters.json')==receipt['SHA256']
 for n,h in load(F/'source_manifest.json')['protected_SHA256'].items():assert sha(R/n)==h,n
 dump('result.json',dict(status='COMPLETE',engineering_admission='PASS',independent_verification='PASS',future_poison='PASS',queries=qa,scientific_scoring_attempts=1,new_model_launches=0,no_threshold_changes=True,protected_old_assets_unchanged=True,parameter_SHA256=receipt['SHA256'],joint_cumulative_pass=sum(x['JOINT_NO_REGRET']=='PASS' for x in joints if x['window'].startswith('future_')),joint_cumulative_total=sum(x['window'].startswith('future_') for x in joints),gates_unchanged=True,UTC=epoch()))
 print('V18 SCIENTIFIC EVALUATION FINISHED; STOP',flush=True)

def worker():
 start=time.perf_counter()
 for mode in ['history','score']:
  subprocess.run([sys.executable,__file__,mode],cwd=R,check=True)
 dump('worker_resource.json',dict(wall_s=time.perf_counter()-start,children_CPU_user_s=resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime,children_CPU_system_s=resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime,children_max_RSS_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss))
if __name__=='__main__':{'prepare':prepare,'history':history,'score':score,'worker':worker}[sys.argv[1]]()
