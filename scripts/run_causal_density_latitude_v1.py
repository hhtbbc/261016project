"""Frozen latitude-representation single-factor experiment; no new data or physics."""
from pathlib import Path
import sys,json,csv,time,resource,warnings
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from netCDF4 import Dataset
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from atmosphere.causal_observation_operator import map_a_queries,observe_map_a
from observations.density_catalog import read_swarm_pod
from evaluation.late_day_correction import RollingOrigin
from evaluation.causal_density_latitude import BANDS,latitude_band,fit_history,fit_global_history,apply_global,apply_latitude,supported_metric,assess_joint,exclusive_json
from prepare_fourcastden_swarm_observation_v1 import sha
F=ROOT/'experiments/causal_density_latitude_correction_v1';CASES=['B14','A7','B7'];METHODS=['Raw','GlobalAdaptive18','LatitudeAdaptive18','Stale06']
def dump(n,x):exclusive_json(F/n,x)
def table(n,rows):
 with (F/n).open('x',newline='') as out:w=csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def save(fig,n):
 fig.suptitle('2021/2022-03-23 UTC | latitude representation only | B14 primary',fontsize=11);fig.text(.5,.006,'PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED | DATE_HELD_OUT / SAME_CONTINUOUS_TIE_RUN',ha='center',fontsize=7);fig.tight_layout(rect=(0,.04,1,.96));fig.savefig(F/'figures'/n,dpi=145);plt.close(fig)
def main():
 start=time.perf_counter()
 def warning(message,category,filename,lineno,file=None,line=None):
  with (F/'logs/worker_warnings_local.jsonl').open('a') as out:out.write(json.dumps(dict(message=str(message),category=category.__name__,filename=filename,line=lineno))+'\n')
 warnings.showwarning=warning;assert json.loads((F/'preflight.json').read_text())['PASS'];pr=json.loads((F/'frozen_protocol.json').read_text());protocolsha=sha(F/'frozen_protocol.json');assert json.loads((F/'protocol_sha256.json').read_text())['SHA256']==protocolsha
 for n,h in pr['code_SHA256'].items():assert sha(ROOT/n)==h,n
 source=json.loads((F/'source_manifest.json').read_text())
 for n,h in source['protected_history_SHA256'].items():assert sha(ROOT/n)==h,n
 assert sha(F/'early_matches_local.npz')==pr['early_match_SHA256'];early=np.load(F/'early_matches_local.npz');assert not (F/'correction_parameters.json').exists();(F/'figures').mkdir(exist_ok=False);data={};raw={};modelaudit=[];scans=[];probes=[]
 with (F/'late_queries_local.jsonl').open('x') as trace:
  for y in ['2021','2022']:
   cdf=source['CDFs'][y];assert sha(ROOT/cdf['file'])==cdf['SHA256'];_,a,_=read_swarm_pod(ROOT/cdf['file'],ROOT/source['hapi']['path'],cdf['SHA256'],satellite='A');m=RollingOrigin(y+'-03-23').masks(a['utc']);keep=m['analysis']|m['future_6h'];a={k:v[keep] for k,v in a.items()};assert len(a['utc'])==1080;data[y]=a;raw[y]={};queries=map_a_queries(a['utc'],a['latitude'],a['longitude'],a['altitude'])
   for case in CASES:
    t0=time.perf_counter();s=source['cases'][y][case];path=ROOT/s['file'];p=HourlyTiegcmObservation([path],{path.name:s['SHA256']},y+'-03-23T15:00:00',y+'-03-24T00:00:00',y+'_'+case);assert len(p.records)==10
    with Dataset(path) as n:
     n.set_auto_mask(False);mt=np.asarray(n['mtime'][:]);used=np.where(((mt[:,0]==82)&(mt[:,1]>=15))|((mt[:,0]==83)&(mt[:,1]==0)))[0];assert len(used)==10
     for field in ['DEN','ZG']:
      v=n[field];assert v.dimensions==('time','ilev','lat','lon') and v.units==('g/cm3' if field=='DEN' else 'cm');badn=0;nonmono=0
      for k in used:
       arr=np.asarray(v[int(k)]);bad=~np.isfinite(arr)|(abs(arr)>1e30)
       for attr in ['_FillValue','missing_value']:
        if hasattr(v,attr):bad|=arr==np.asarray(getattr(v,attr),dtype=arr.dtype)
       if field=='DEN':bad|=arr<=0
       else:nonmono+=int((np.diff(arr,axis=0)<=0).sum())
       badn+=int(bad.sum())
      assert badn==0 and nonmono==0;scans.append(dict(year=y,case=case,field=field,frames=10,invalid=badn,nonmonotonic_ZG=nonmono))
    vals=[]
    for i,q in enumerate(queries):
     r,coord=observe_map_a(p,q);trace.write(json.dumps(dict(year=y,case=case,index=i,UTC=str(a['utc'][i])+'Z',valid=r.valid,reason=r.reason,rho_model=r.rho_kg_m3,coordinate=coord,metadata=r.metadata))+'\n');assert r.valid and len(r.metadata['columns'])==8,(y,case,i,r.reason);vals.append(r.rho_kg_m3)
     if i in [0,360,1079]:
      md=r.metadata;w=md['weights'];ww=np.array([1-w['time'],w['time']])[:,None,None]*np.array([1-w['latitude'],w['latitude']])[None,:,None]*np.array([1-w['longitude'],w['longitude']])[None,None,:];terms=[]
      for col in md['columns']:
       k=next(k for k,(_,pa,rec) in enumerate(p.records) if pa.name==col['file'] and rec==col['record']);z,den=p._column(k,col['lat_index'],col['lon_index']);terms.append(np.exp(np.interp(coord['model_zg_m'],z,np.log(den))))
      direct=float(np.sum(ww*np.array(terms).reshape(2,2,2)));assert np.isclose(direct,r.rho_kg_m3,rtol=1e-13,atol=0);probes.append(dict(year=y,case=case,index=i,relative_difference=abs(direct/r.rho_kg_m3-1)))
    raw[y][case]=np.array(vals);modelaudit.append(dict(year=y,case=case,frames=10,queries=1080,valid=1080,failed=0,first_frame=p.records[0][0].utc.isot,last_frame=p.records[-1][0].utc.isot,wall_s=time.perf_counter()-t0));p.close();print('LATE COVERAGE PASS',y,case,flush=True)
 dump('model_query_audit.json',dict(cases=modelaudit,explicit_scan=scans,interpolation_probes=probes,all_eight_columns=True))
 params={};stale={};residuals=[];common={};combos={}
 for y,a in data.items():
  common[y]=a['quality'].copy()
  for case in CASES:common[y]&=np.isfinite(raw[y][case])&(raw[y][case]>0)
  params[y]={}
  for case in CASES:
   coeff,m=fit_history(a['utc'],a['latitude'],a['density'],raw[y][case],common[y],day=y+'-03-23');assert coeff['global_fit']['status']=='SUPPORTED' and coeff['global_fit']['N']==360
   params[y][case]=dict(**coeff,CDF_SHA256=source['CDFs'][y]['SHA256'],NetCDF_SHA256=source['cases'][y][case]['SHA256'],protocol_SHA256=protocolsha,future_poison_test='future_poison_test.json after parameter freeze')
   e=np.log(a['density'][m])-np.log(raw[y][case][m]);bb=latitude_band(a['latitude'][m])
   for i,j in enumerate(np.flatnonzero(m)):residuals.append(dict(year=y,case=case,UTC=str(a['utc'][j])+'Z',latitude_deg=float(a['latitude'][j]),region=BANDS[int(bb[i])],log_obs_minus_model=float(e[i])))
  combo=dict(utc=np.r_[early[y+'_utc'],a['utc']],latitude=np.r_[early[y+'_latitude'],a['latitude']],observed=np.r_[early[y+'_density'],a['density']],background=np.r_[early[y+'_model'],raw[y]['B14']],quality=np.r_[early[y+'_quality'],common[y]]);combos[y]=combo;g,m=fit_global_history(**combo,day=y+'-03-23',hour=6);assert g['N']==360 and g['status']=='SUPPORTED'
  stale[y]=dict(coefficient=g,day=y+'-03-23',background='B14',history='[03,06)',CDF_SHA256=source['CDFs'][y]['SHA256'],NetCDF_SHA256=source['cases'][y]['B14']['SHA256'],protocol_SHA256=protocolsha,future_poison_test='future_poison_test.json after parameter freeze')
 dump('correction_parameters.json',dict(protocol_SHA256=protocolsha,Global_and_Latitude=params,Stale06=stale,all_coefficients_before_future_scores=True));paramsha=sha(F/'correction_parameters.json');dump('parameter_sha256.json',dict(SHA256=paramsha));table('calibration_residuals.csv',residuals)
 poison=[]
 for y,a in data.items():
  for case in CASES:
   changed=a['density'].copy();changed[a['utc']>=np.datetime64(y+'-03-23T18')]*=1e20;again,_=fit_history(a['utc'],a['latitude'],changed,raw[y][case],common[y],day=y+'-03-23');original=params[y][case]
   assert all(again[k]==original[k] for k in ['global_fit','latitude','day','cutoff','satellite']);poison.append(dict(year=y,case=case,GlobalAdaptive18_PASS=True,LatitudeAdaptive18_PASS=True))
  cc={k:v.copy() for k,v in combos[y].items()};cc['observed'][cc['utc']>=np.datetime64(y+'-03-23T18')]*=1e20;again,_=fit_global_history(**cc,day=y+'-03-23',hour=6);assert again==stale[y]['coefficient'];poison.append(dict(year=y,case='B14_Stale06',Stale06_PASS=True))
 assert sha(F/'correction_parameters.json')==paramsha;dump('future_poison_test.json',dict(PASS=True,after_parameter_SHA_freeze=True,parameter_SHA256_unchanged=paramsha,checks=poison));print('ALL COEFFICIENTS FROZEN; POISON TEST PASS; FUTURE SCORES BEGIN',flush=True)
 predictions={};supports={};metrics=[];regions=[];joint=[];timeblocks=[];coverage=[];pointwise=[];sample_ids={}
 for y,a in data.items():
  masks=RollingOrigin(y+'-03-23').masks(a['utc']);masks['block_0_1h']=masks['future_1h'];bands=latitude_band(a['latitude']);rr={'all':np.ones(len(bands),bool),**{name:bands==i for i,name in enumerate(BANDS)}};predictions[y]={};supports[y]={};sample_ids[y]={}
  for case in CASES:
   c=params[y][case];local,support=apply_latitude(raw[y][case],a['latitude'],c['latitude']);pp={'Raw':raw[y][case],'GlobalAdaptive18':apply_global(raw[y][case],c['global_fit']),'LatitudeAdaptive18':local};ss={method:np.ones(len(bands),bool) for method in pp};ss['LatitudeAdaptive18']=support
   if case=='B14':pp['Stale06']=apply_global(raw[y][case],stale[y]['coefficient']);ss['Stale06']=np.ones(len(bands),bool)
   predictions[y][case]=pp;supports[y][case]=ss;sample_ids[y][case]={}
   for wn,wm in masks.items():
    selected=wm&common[y];scores={region:{} for region in rr};eligible=int((a['quality']&wm).sum());sample_ids[y][case][wn]=sha_ids(a['utc'][selected]);n=int(selected.sum())
    for method,pred in pp.items():
     ns=int((selected&ss[method]).sum());coverage.append(dict(year=y,case=case,window=wn,method=method,N_eligible=eligible,N_model_valid=n,N_method_supported=ns,query_coverage=n/eligible if eligible else None,method_support_coverage=ns/n if n else None,sample_ID_SHA256=sample_ids[y][case][wn]))
     for region,rm in rr.items():
      score=supported_metric(pred,a['density'],a['quality'],common[y],wm&rm,ss[method]);scores[region][method]=score;rec=dict(year=y,case=case,window=wn,region=region,method=method,**score);(metrics if region=='all' else regions).append(rec)
      if region=='all' and wn.startswith('block_'):timeblocks.append(rec)
      if method!='Raw':
       m=selected&rm&ss[method];er=abs(raw[y][case][m]-a['density'][m]);ec=abs(pred[m]-a['density'][m]);pointwise.append(dict(year=y,case=case,window=wn,region=region,method=method,N_requested=int((selected&rm).sum()),N_compared=int(m.sum()),N_unsupported=int((selected&rm&~ss[method]).sum()),improved=int((ec<er).sum()),worsened=int((ec>er).sum()),unchanged=int((ec==er).sum())))
    for method in list(pp)[1:]:
     f=assess_joint(scores['all']['Raw'],scores['all'][method],{k:scores[k]['Raw'] for k in BANDS},{k:scores[k][method] for k in BANDS},bool(ss[method][selected].all()));rawscore=scores['all']['Raw'];s=scores['all'][method];joint.append(dict(year=y,case=case,window=wn,method=method,N=n,RMSE_gain_pct=100*(1-s['RMSE']/rawscore['RMSE']) if s['RMSE'] is not None else None,relative_RMS_gain_pct=100*(1-s['relative_RMS']/rawscore['relative_RMS']) if s['relative_RMS'] is not None else None,**f))
 table('metrics.csv',metrics);table('region_metrics.csv',regions);table('joint_assessment.csv',joint);table('time_block_metrics.csv',timeblocks);table('coverage.csv',coverage);table('pointwise_diagnostics.csv',pointwise);dump('shared_sample_identity.json',dict(year_case_window=sample_ids,Raw_corrected_identical_requested_IDs=True,unsupported_never_dropped_to_make_full_score=True))
 arrays={}
 for y,a in data.items():
  for k,v in a.items():arrays[y+'_'+k]=v
  arrays[y+'_common']=common[y]
  for case,pp in predictions[y].items():
   for method,pred in pp.items():arrays[y+'_'+case+'_'+method]=pred;arrays[y+'_'+case+'_'+method+'_support']=supports[y][case][method]
 np.savez_compressed(F/'matched_local.npz',**arrays)
 # Fixed plots, no result-dependent date/region/sample selection.
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for y,ax in zip(data,axes):
  for region in BANDS:
   r=[x for x in residuals if x['year']==y and x['case']=='B14' and x['region']==region];ax.scatter([x['latitude_deg'] for x in r],[x['log_obs_minus_model'] for x in r],s=7,label=region)
  for lat in [-60,-30,30,60]:ax.axvline(lat,color='gray',ls=':',lw=.6)
  ax.set(xlabel='GRS80 geodetic latitude [deg]',ylabel='ln(obs/model)',title=y+' history [15,18)');ax.legend()
 save(fig,'01_history_latitude_residuals.png')
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for y,ax in zip(data,axes):
  c=params[y]['B14'];values=[c['global_fit']['b']]+[c['latitude'][k]['b'] if c['latitude'][k]['b'] is not None else np.nan for k in BANDS];ax.bar(['global',*BANDS],values);ax.axhline(0,color='k');ax.set(ylabel='Log correction b [dimensionless]',title=y+' B14 history-only medians')
 save(fig,'02_global_latitude_coefficients.png')
 fig,axes=plt.subplots(2,1,figsize=(12,7))
 for y,ax in zip(data,axes):
  a=data[y];m=RollingOrigin(y+'-03-23').masks(a['utc'])['future_6h'];hours=(a['utc']-np.datetime64(y+'-03-23'))/np.timedelta64(1,'h');ax.plot(hours[m],a['density'][m]*1e12,'k',label='POD observation')
  for method,p in predictions[y]['B14'].items():ax.plot(hours[m],p[m]*1e12,label=method,lw=.8)
  for h in [18,19,21,24]:ax.axvline(h,color='gray',ls=':',lw=.6)
  ax.set(xlabel='UTC hour',ylabel='Density [1e-12 kg/m3]',title=y+' future [18,24)');ax.legend(fontsize=7)
 save(fig,'03_B14_future_density.png')
 for num,key,label in [('04','RMSE_gain_pct','RMSE reduction [%]'),('05','relative_RMS_gain_pct','Relative RMS reduction [%]')]:
  fig,axes=plt.subplots(1,2,figsize=(12,4))
  for y,ax in zip(data,axes):
   for method in METHODS[1:]:ax.plot([1,3,6],[next(x[key] if x[key] is not None else np.nan for x in joint if x['year']==y and x['case']=='B14' and x['window']==f'future_{h}h' and x['method']==method) for h in [1,3,6]],'o-',label=method)
   ax.axhline(0,color='k',ls='--');ax.set(xlabel='Cumulative future window [h]',ylabel=label,title=y);ax.legend(fontsize=7)
  save(fig,num+'_future_gains.png')
 fig,axes=plt.subplots(2,2,figsize=(12,7));x=np.arange(3)
 for row,y in enumerate(data):
  for col,(key,label,scale) in enumerate([('RMSE','RMSE [1e-13 kg/m3]',1e13),('relative_RMS','Relative RMS [%]',100)]):
   ax=axes[row,col]
   for i,method in enumerate(METHODS):
    v=[next(z[key] if z[key] is not None else np.nan for z in regions if z['year']==y and z['case']=='B14' and z['window']=='future_6h' and z['region']==r and z['method']==method)*scale for r in BANDS];ax.bar(x+(i-1.5)*.19,v,.19,label=method)
   ax.set(xticks=x,xticklabels=BANDS,ylabel=label,title=y+' six-hour full regions');ax.legend(fontsize=6)
 save(fig,'06_regional_RMS.png')
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for y,ax in zip(data,axes):
  v=[next(z['relative_bias'] if z['relative_bias'] is not None else np.nan for z in regions if z['year']==y and z['case']=='B14' and z['window']=='future_6h' and z['region']=='low' and z['method']==method)*100 for method in METHODS];ax.bar(METHODS,v);ax.tick_params(axis='x',rotation=15,labelsize=7);ax.axhline(0,color='k');ax.set(ylabel='Low-lat signed relative Bias [%]',title=y+' six-hour')
 save(fig,'07_low_latitude_bias.png')
 fig,axes=plt.subplots(2,2,figsize=(12,7));wins=['block_0_1h','block_1_3h','block_3_6h']
 for row,y in enumerate(data):
  for ax,key,label in zip(axes[row],['RMSE_gain_pct','relative_RMS_gain_pct'],['RMSE reduction [%]','Relative RMS reduction [%]']):
   for method in METHODS[1:]:ax.plot([0,1,2],[next(x[key] if x[key] is not None else np.nan for x in joint if x['year']==y and x['case']=='B14' and x['window']==w and x['method']==method) for w in wins],'o-',label=method)
   ax.axhline(0,color='k',ls='--');ax.set(xticks=[0,1,2],xticklabels=['[18,19)','[19,21)','[21,24)'],ylabel=label,title=y+' non-overlapping');ax.legend(fontsize=6)
 save(fig,'08_time_blocks.png')
 assert sha(F/'correction_parameters.json')==paramsha
 for n,h in source['protected_history_SHA256'].items():assert sha(ROOT/n)==h,n
 dump('run_result.json',dict(engineering_workflow_PASS=True,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,late_queries=6480,late_valid=6480,early_queries_reused_from_gate=720,new_early_queries_in_run=0,all_parameters_before_future_metrics=True,future_poison_PASS=True,plots=8,downloads=0,GPU=0,TIE=0,DART=0,orbit=0));print('LATITUDE PILOT COMPLETE; SCIENCE GATES RETAINED',flush=True)
def sha_ids(utc):
 import hashlib
 return hashlib.sha256(np.asarray(utc,dtype='datetime64[ns]').astype('<i8').tobytes()).hexdigest()
if __name__=='__main__':main()
