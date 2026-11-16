"""Frozen 2021 method replication; one scalar per background, no future fitting."""
from pathlib import Path
import sys,json,csv,time,resource,warnings
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from astropy.time import Time
from netCDF4 import Dataset
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from atmosphere.causal_observation_operator import map_a_queries,observe_map_a
from evaluation.cross_year_correction import CausalDay,frozen_transfer
from evaluation.swarm_crossyear import strata,metric_row
from run_swarm_tiegcm_2022_observation import read_observation
from prepare_fourcastden_swarm_observation_v1 import sha
F=ROOT/'experiments/cross_year_causal_density_validation_v1';OLD=ROOT/'experiments/causal_density_correction_v1';CASES=['B14','A7','B7','A14']
def dump(n,x):
 with (F/n).open('x') as out:json.dump(x,out,indent=2,allow_nan=False)
def table(n,rows):
 with (F/n).open('x',newline='') as out:
  w=csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def save(fig,name):
 fig.suptitle('CROSS_YEAR_METHOD_REPLICATION | 2021-03-24 UTC | B14 primary',fontsize=11);fig.text(.5,.006,'PROVISIONAL Map-A / HINDCAST / EXTERNAL_DATUM_UNVERIFIED | A14 sensitivity only (2021 engineering PASS; 2022 PARTIAL)',ha='center',fontsize=7);fig.tight_layout(rect=(0,.035,1,.96));fig.savefig(F/'figures'/name,dpi=145);plt.close(fig)
def main():
 start=time.perf_counter()
 def warning(message,category,filename,lineno,file=None,line=None):
  with (F/'warnings_local.jsonl').open('a') as out:out.write(json.dumps(dict(message=str(message),category=category.__name__,filename=filename,line=lineno))+'\n')
 warnings.showwarning=warning
 protocol=json.loads((F/'frozen_protocol.json').read_text());source=json.loads((F/'source_manifest.json').read_text());assert json.loads((F/'preflight.json').read_text())['PASS'];assert not (F/'correction_parameters.json').exists();(F/'figures').mkdir(exist_ok=False)
 for n,h in source['protected_inputs'].items():assert sha(ROOT/n)==h,n
 a,contract=read_observation(ROOT/source['observation']['source_file']);assert len(a['utc'])==2880 and a['quality'].sum()==2880 and np.all(np.diff(a['utc'])==np.timedelta64(30,'s'));assert contract['global_attributes']['TIME SYSTEM']==['UTC']
 day=CausalDay(protocol['day']);masks=day.masks(a['utc']);keep=masks['analysis']|masks['future_6h'];a={k:v[keep] for k,v in a.items()};masks=day.masks(a['utc']);assert [int(masks[k].sum()) for k in ['analysis','future_1h','future_3h','future_6h']]==[360,120,360,720]
 queries=map_a_queries(a['utc'],a['latitude'],a['longitude'],a['altitude']);raw={};case_audit=[];probes=[];gridscan=[]
 with (F/'query_trace_local.jsonl').open('x') as trace:
  for case in CASES:
   case_start=time.perf_counter();s=source['cases'][case];folder=ROOT/s['folder'];expected={e['file']:e['SHA256'] for e in s['files']};p=HourlyTiegcmObservation([folder/e['file'] for e in s['files']],expected,'2021-03-24T03:00:00','2021-03-24T12:00:00',case);assert len(p.records)==10;raw[case]=np.full(len(queries),np.nan);fail={}
   for e in s['files']:
    with Dataset(folder/e['file']) as n:
     n.set_auto_mask(False);mt=np.asarray(n['mtime'][:]);used=np.where((mt[:,0]==83)&(mt[:,1]>=3)&(mt[:,1]<=12))[0]
     for name in ['DEN','ZG']:
      badsum=0;total=0
      for i in used:
       v=n[name];arr=np.asarray(v[int(i)]);bad=~np.isfinite(arr)|(abs(arr)>1e30)
       for attr in ['_FillValue','missing_value']:
        if hasattr(v,attr):bad|=arr==np.asarray(getattr(v,attr),dtype=arr.dtype)
       if name=='DEN':bad|=arr<=0
       badsum+=int(bad.sum());total+=arr.size
      assert badsum==0,(case,name);gridscan.append(dict(case=case,file=e['file'],field=name,values_scanned=total,invalid=badsum))
   for i,q in enumerate(queries):
    v,coord=observe_map_a(p,q)
    if v.valid:raw[case][i]=v.rho_kg_m3
    else:fail[v.reason]=fail.get(v.reason,0)+1
    trace.write(json.dumps(dict(case=case,sample=i,UTC=str(a['utc'][i])+'Z',quality_flag=int(a['validity_flag'][i]),coordinate=coord,valid=v.valid,reason=v.reason,rho_kg_m3=v.rho_kg_m3,metadata=v.metadata))+'\n')
    if i in [0,360,1079] and v.valid:
     md=v.metadata;w=md['weights'];weights=np.array([1-w['time'],w['time']])[:,None,None]*np.array([1-w['latitude'],w['latitude']])[None,:,None]*np.array([1-w['longitude'],w['longitude']])[None,None,:];terms=[]
     for c in md['columns']:
      k=next(k for k,(_,path,rec) in enumerate(p.records) if path.name==c['file'] and rec==c['record']);zz,rr=p._column(k,c['lat_index'],c['lon_index']);terms.append(np.exp(np.interp(coord['model_zg_m'],zz,np.log(rr))))
     direct=float(np.sum(weights*np.array(terms).reshape(2,2,2)));assert np.isclose(direct,v.rho_kg_m3,rtol=1e-13,atol=0);probes.append(dict(case=case,sample=i,relative_difference=abs(direct/v.rho_kg_m3-1)))
   case_audit.append(dict(case=case,engineering=s['engineering'],role=s['role'],frames=len(p.records),queries=len(queries),valid=int(np.isfinite(raw[case]).sum()),failure_reasons=fail,wall_s=time.perf_counter()-case_start));p.close();print('MATCHED',case,'failures',fail,flush=True)
 common=a['quality'].copy()
 for c in CASES:common&=np.isfinite(raw[c])&(raw[c]>0)
 assert common[masks['analysis']].sum()==360,'Incomplete shared past window; stop rather than alter sample set'
 dump('matched_samples_manifest.json',dict(cases=case_audit,all_case_common=int(common.sum()),observation_file=source['observation'],interpolation_probes=probes,explicit_fill_scan=gridscan,coordinate='GRS80 geodetic ->ITRS ->WGS84 Map-A as native ZG; no formal datum equivalence'))
 # Fit only past A. Write frozen parameters before any future errors are evaluated.
 params={};predictions={};residualrows=[];histstats=[]
 for c in CASES:
  fit,selected,e=day.fit(a['utc'],a['density'],raw[c],common,satellite='A');assert fit.sample_count==360
  poison=a['density'].copy();poison[~masks['analysis']]*=1e20;fit2,_,_=day.fit(a['utc'],poison,raw[c],common,satellite='A');assert fit==fit2
  params[c]=dict(b_2021=fit.log_bias,multiplier_2021=fit.multiplier,N=fit.sample_count,source_satellite='A',first_UTC=str(a['utc'][selected][0]),last_UTC=str(a['utc'][selected][-1]),engineering='PASS',role=source['cases'][c]['role'],future_poison_invariance=True)
  predictions[c]={'Raw':raw[c],'Adaptive':np.where(common,fit.apply(raw[c][common]),np.nan) if common.all() else raw[c].copy()}
  if not common.all():predictions[c]['Adaptive'][common]=fit.apply(raw[c][common]);predictions[c]['Adaptive'][~common]=np.nan
  for i,x in zip(np.flatnonzero(selected),e):residualrows.append(dict(year=2021,case=c,UTC=str(a['utc'][i])+'Z',latitude_deg=float(a['latitude'][i]),height_m=float(a['altitude'][i]),log_obs_minus_model=float(x)))
  histstats.append(dict(year=2021,case=c,N=len(e),mean=float(np.mean(e)),median=float(np.median(e)),multiplier=fit.multiplier,P05=float(np.percentile(e,5)),P95=float(np.percentile(e,95)),std=float(np.std(e)),height_correlation=float(np.corrcoef(e,a['altitude'][selected])[0,1]),latitude_correlation=float(np.corrcoef(e,a['latitude'][selected])[0,1])))
 predictions['B14']['Transfer']=frozen_transfer('B14',protocol['transfer_b']).apply(raw['B14'])
 dump('correction_parameters.json',dict(protocol_SHA256=sha(F/'frozen_protocol.json'),adaptive=params,transfer={'case':'B14','b_2022':protocol['transfer_b'],'multiplier':protocol['transfer_multiplier'],'source_SHA256':sha(OLD/'correction_parameters.json'),'no2021_fit':True},parameters_frozen_before_future_metrics=True));table('calibration_residuals.csv',residualrows);print('PAST PARAMETERS FROZEN',flush=True)
 oldres=list(csv.DictReader((OLD/'calibration_residuals.csv').open()));oldparams=json.loads((OLD/'correction_parameters.json').read_text())['parameters']
 for c in CASES:
  rr=[x for x in oldres if x['case']==c];e=np.array([float(x['log_obs_minus_model']) for x in rr]);hh=np.array([float(x['height_m']) for x in rr]);lat=np.array([float(x['latitude_deg']) for x in rr]);histstats.append(dict(year=2022,case=c,N=len(e),mean=float(np.mean(e)),median=float(np.median(e)),multiplier=oldparams[c]['density_multiplier'],P05=float(np.percentile(e,5)),P95=float(np.percentile(e,95)),std=float(np.std(e)),height_correlation=float(np.corrcoef(e,hh)[0,1]),latitude_correlation=float(np.corrcoef(e,lat)[0,1])))
 table('historical_residual_comparison.csv',histstats);metrics=[];regions=[];gains=[];coverage=[];pointwise=[];bins=strata(a['latitude'],a['altitude'],a['utc']);regions_used={k:v for k,v in bins.items() if not k.startswith('UTC_')}
 for c in CASES:
  for window,win in masks.items():
   qmask=common&win;eligible=int((a['quality']&win).sum());coverage.append(dict(case=c,window=window,eligible=eligible,query_valid=int((np.isfinite(raw[c])&win).sum()),common_N=int(qmask.sum()),coverage=float(qmask.sum()/eligible),failure_reasons='{}' if np.isfinite(raw[c]).all() else 'see query trace'))
   for region,reg in regions_used.items():
    m=qmask&reg;ref=None
    for method,pred in predictions[c].items():
     score=metric_row(pred,a['density'],a['quality'],common,win&reg);score['mean_log_model_minus_obs']=float(np.mean(np.log(pred[m]/a['density'][m]))) if m.sum()>=30 else None;row=dict(year=2021,case=c,role=source['cases'][c]['role'],window=window,region=region,method=method,**score)
     (metrics if region=='all' else regions).append(row)
     if method=='Raw':ref=score
     elif score['RMSE'] is not None:
      gains.append(dict(case=c,window=window,region=region,method=method,N=score['n'],RMSE_improvement_pct=100*(1-score['RMSE']/ref['RMSE']),relative_RMS_improvement_pct=100*(1-score['relative_RMS']/ref['relative_RMS'])))
     if method!='Raw':
      rerr=abs(raw[c][m]-a['density'][m]);cerr=abs(pred[m]-a['density'][m]);pointwise.append(dict(case=c,window=window,region=region,method=method,N=int(m.sum()),improved=int((cerr<rerr).sum()),worsened=int((cerr>rerr).sum()),unchanged=int((cerr==rerr).sum())))
 table('metrics.csv',metrics);table('region_metrics.csv',regions);table('improvements.csv',gains);table('coverage.csv',coverage);table('pointwise_diagnostics.csv',pointwise)
 np.savez_compressed(F/'matched_local.npz',**a,common=common,**{c+'_Raw':raw[c] for c in CASES},**{c+'_Adaptive':predictions[c]['Adaptive'] for c in CASES},B14_Transfer=predictions['B14']['Transfer'])
 # Figures fixed to primary and full controls, no future-based example selection.
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for year,ax in zip([2021,2022],axes):
  for c in CASES:
   ee=np.array([float(x['log_obs_minus_model']) for x in (residualrows if year==2021 else oldres) if x['case']==c]);ax.hist(ee,bins=25,alpha=.35,label=c)
  ax.set(xlabel='ln(observation/model)',ylabel='Past 30-second records (correlated)',title=f'{year}-03-24 [03,06)');ax.legend(fontsize=7)
 save(fig,'01_history_residual_distribution.png')
 fig,axes=plt.subplots(1,2,figsize=(11,4));xx=np.arange(4)
 for i,year in enumerate([2021,2022]):
  rr=[next(x for x in histstats if x['year']==year and x['case']==c) for c in CASES];axes[0].bar(xx+(i-.5)*.36,[x['median'] for x in rr],.36,label=str(year));axes[1].bar(xx+(i-.5)*.36,[x['multiplier'] for x in rr],.36,label=str(year))
 for ax,title in zip(axes,['Median log correction b','Density multiplier exp(b)']):ax.set(xticks=xx,xticklabels=CASES,ylabel='Dimensionless',title=title);ax.legend()
 axes[0].axhline(0,color='k',lw=.6);axes[1].axhline(1,color='k',lw=.6);save(fig,'02_coefficients_cross_year.png')
 hours=(a['utc']-np.datetime64('2021-03-24'))/np.timedelta64(1,'h');future=masks['future_6h'];fig,axes=plt.subplots(2,1,figsize=(11,6),sharex=True);axes[0].plot(hours[future],a['density'][future]*1e13,'k',label='POD observation')
 for method,pred in predictions['B14'].items():axes[0].plot(hours[future],pred[future]*1e13,label=method,lw=1);axes[1].plot(hours[future],100*(pred[future]/a['density'][future]-1),label=method)
 for ax in axes:
  for h in [6,7,9,12]:ax.axvline(h,color='gray',ls=':',lw=.6)
  ax.legend(fontsize=8)
 axes[0].set(ylabel='Density [1e-13 kg/m3]',title='B14 future observations never fitted');axes[1].set(xlabel='2021-03-24 UTC hour',ylabel='Signed relative residual [%]');save(fig,'03_B14_future_density.png')
 fig,axes=plt.subplots(1,3,figsize=(14,4))
 for c,ax in zip(['A7','B7','A14'],axes):
  for method in ['Raw','Adaptive']:ax.plot(hours[future],100*(predictions[c][method][future]/a['density'][future]-1),label=method,lw=.8)
  ax.set(title=c+(' sensitivity' if c=='A14' else ' control'),xlabel='UTC hour',ylabel='Relative residual [%]');ax.legend()
 save(fig,'04_background_sensitivity.png')
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for ax,key,label in zip(axes,['RMSE_improvement_pct','relative_RMS_improvement_pct'],['RMSE reduction [%]','Relative RMS reduction [%]']):
  for c in CASES:
   methods=['Adaptive','Transfer'] if c=='B14' else ['Adaptive']
   for method in methods:ax.plot([1,3,6],[next(x[key] for x in gains if x['case']==c and x['method']==method and x['window']==f'future_{h}h' and x['region']=='all') for h in [1,3,6]],'o-',label=c+' '+method)
  ax.axhline(0,color='k',ls='--');ax.set(xlabel='Cumulative future window [h]',ylabel=label);ax.legend(fontsize=6)
 save(fig,'05_future_improvement.png')
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for method,ax in zip(['Transfer','Adaptive'],axes):
  pred=predictions['B14'][method];delta=abs(pred[future]-a['density'][future])-abs(raw['B14'][future]-a['density'][future]);ax.scatter(hours[future],delta*1e13,s=5,c=np.where(delta>0,'C3','C0'));ax.axhline(0,color='k');ax.set(xlabel='UTC hour',ylabel='Change in absolute error [1e-13 kg/m3]',title=method+'; positive=worse')
 save(fig,'06_pointwise_improvement.png')
 fig,axes=plt.subplots(2,3,figsize=(13,7))
 for row,year in enumerate([2021,2022]):
  rr=[x for x in (residualrows if year==2021 else oldres) if x['case']=='B14'];ee=np.array([float(x['log_obs_minus_model']) for x in rr]);lat=np.array([float(x['latitude_deg']) for x in rr]);hh=np.array([float(x['height_m'])/1000 for x in rr]);tt=(np.array([x['UTC'][:-1] for x in rr],dtype='datetime64[ns]')-np.datetime64(f'{year}-03-24'))/np.timedelta64(1,'h')
  for ax,x,label in zip(axes[row],[tt,lat,hh],['UTC hour','Latitude [deg]','GRS80 height [km]']):ax.scatter(x,ee,s=5);ax.set(xlabel=label,ylabel='ln(obs/B14)',title=f'{year} history only')
 save(fig,'07_history_residual_structure.png')
 for n,h in source['protected_inputs'].items():assert sha(ROOT/n)==h,n
 dump('run_result.json',dict(PASS=True,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,queries=4320,query_valid=int(sum(np.isfinite(raw[c]).sum() for c in CASES)),history_samples_per_case=360,future_samples=720,parameters_frozen_before_future_evaluation=True,plots=7,fit_2022=False,C_B_read=False,downloads=0,GPU=0,TIE=0,DART=0,orbit=0));print('CROSS YEAR PILOT COMPLETE',flush=True)
if __name__=='__main__':main()
