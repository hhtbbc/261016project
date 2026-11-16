"""Frozen two-year late-day scalar pilot. No state assimilation or parameter search."""
from pathlib import Path
import sys,json,csv,time,resource,warnings
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from netCDF4 import Dataset
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from atmosphere.causal_observation_operator import map_a_queries,observe_map_a
from atmosphere.causal_density_correction import LogMedianCorrection
from evaluation.late_day_correction import RollingOrigin,diagnostic_quintiles,joint_flags
from evaluation.swarm_crossyear import strata,metric_row
from run_swarm_tiegcm_2022_observation import read_observation
from prepare_fourcastden_swarm_observation_v1 import sha
F=ROOT/'experiments/causal_density_late_day_v1';CASES=['B14','A7','B7'];METHODS=['Raw','Adaptive18','Stale06','CrossYearTransfer18']
def dump(n,x):
 with (F/n).open('x') as out:json.dump(x,out,indent=2,allow_nan=False)
def table(n,rows):
 with (F/n).open('x',newline='') as out:w=csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def save(fig,n):
 fig.suptitle('LATE_DAY_ROLLING_ORIGIN | 2021/2022-03-24 UTC | B14 primary',fontsize=11);fig.text(.5,.005,'PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED | observations are POD-derived, not error-free truth',ha='center',fontsize=7);fig.tight_layout(rect=(0,.035,1,.96));fig.savefig(F/'figures'/n,dpi=145);plt.close(fig)
def main():
 start=time.perf_counter()
 def warning(message,category,filename,lineno,file=None,line=None):
  with (F/'warnings_local.jsonl').open('a') as out:out.write(json.dumps(dict(message=str(message),category=category.__name__,filename=filename,line=lineno))+'\n')
 warnings.showwarning=warning;source=json.loads((F/'source_manifest.json').read_text());pr=json.loads((F/'frozen_protocol.json').read_text());assert json.loads((F/'preflight.json').read_text())['PASS'];assert not (F/'correction_parameters.json').exists();(F/'figures').mkdir(exist_ok=False)
 for n,h in source['protected_inputs'].items():assert sha(ROOT/n)==h,n
 data={};raw={};coverage_audit=[];probe=[];scans=[]
 with (F/'query_trace_local.jsonl').open('x') as trace:
  for y in ['2021','2022']:
   a,_=read_observation(ROOT/source['observations'][y]['source_file']);assert len(a['utc'])==2880 and a['quality'].sum()==2880 and np.all(np.diff(a['utc'])==np.timedelta64(30,'s'));rolling=RollingOrigin(y+'-03-24');m=rolling.masks(a['utc']);keep=m['analysis']|m['future_6h'];a={k:v[keep] for k,v in a.items()};data[y]=a;queries=map_a_queries(a['utc'],a['latitude'],a['longitude'],a['altitude']);raw[y]={}
   for c in CASES:
    t0=time.perf_counter();s=source['cases'][y][c];folder=ROOT/s['folder'];expected={e['file']:e['SHA256'] for e in s['files']};p=HourlyTiegcmObservation([folder/e['file'] for e in s['files']],expected,y+'-03-24T15:00:00',y+'-03-25T00:00:00',y+'_'+c);assert len(p.records)==10
    for e in s['files']:
     with Dataset(folder/e['file']) as n:
      n.set_auto_mask(False);mt=np.asarray(n['mtime'][:]);used=np.where(((mt[:,0]==83)&(mt[:,1]>=15))|((mt[:,0]==84)&(mt[:,1]==0)))[0]
      for name in ['DEN','ZG']:
       badsum=0;total=0
       for k in used:
        v=n[name];arr=np.asarray(v[int(k)]);bad=~np.isfinite(arr)|(abs(arr)>1e30)
        for attr in ['_FillValue','missing_value']:
         if hasattr(v,attr):bad|=arr==np.asarray(getattr(v,attr),dtype=arr.dtype)
        if name=='DEN':bad|=arr<=0
        badsum+=int(bad.sum());total+=arr.size
       assert badsum==0,(y,c,name,badsum);scans.append(dict(year=y,case=c,file=e['file'],variable=name,values_scanned=total,invalid=badsum))
    vals=np.full(len(queries),np.nan);fail={}
    for i,q in enumerate(queries):
     r,coord=observe_map_a(p,q)
     if r.valid:vals[i]=r.rho_kg_m3
     else:fail[r.reason]=fail.get(r.reason,0)+1
     trace.write(json.dumps(dict(year=y,case=c,index=i,UTC=str(a['utc'][i])+'Z',valid=r.valid,reason=r.reason,rho_kg_m3=r.rho_kg_m3,coordinate=coord,metadata=r.metadata))+'\n')
     if i in [0,360,1079] and r.valid:
      md=r.metadata;w=md['weights'];ww=np.array([1-w['time'],w['time']])[:,None,None]*np.array([1-w['latitude'],w['latitude']])[None,:,None]*np.array([1-w['longitude'],w['longitude']])[None,None,:];terms=[]
      for col in md['columns']:
       k=next(k for k,(_,path,rec) in enumerate(p.records) if path.name==col['file'] and rec==col['record']);z,den=p._column(k,col['lat_index'],col['lon_index']);terms.append(np.exp(np.interp(coord['model_zg_m'],z,np.log(den))))
      direct=float(np.sum(ww*np.array(terms).reshape(2,2,2)));assert np.isclose(direct,r.rho_kg_m3,rtol=1e-13,atol=0);probe.append(dict(year=y,case=c,index=i,relative_difference=abs(direct/r.rho_kg_m3-1)))
    assert not fail,'Incomplete late-day preregistered window: stop; do not choose another cutoff'
    raw[y][c]=vals;coverage_audit.append(dict(year=y,case=c,queries=len(vals),valid=int(np.isfinite(vals).sum()),first_frame=p.records[0][0].utc.isot,last_frame=p.records[-1][0].utc.isot,frames=10,failure_reasons=fail,wall_s=time.perf_counter()-t0));p.close();print('MATCHED',y,c,flush=True)
 # All six local-history parameters are completed before any future error calculation.
 params={};residuals=[];predictions={};common={};coefobjects={}
 for y,a in data.items():
  common[y]=a['quality'].copy()
  for c in CASES:common[y]&=np.isfinite(raw[y][c])&(raw[y][c]>0)
  rolling=RollingOrigin(y+'-03-24');masks=rolling.masks(a['utc']);assert [int(masks[n].sum()) for n in ['analysis','future_1h','future_3h','future_6h']]==[360,120,360,720];params[y]={};coefobjects[y]={}
  for c in CASES:
   fit,m,e=rolling.fit(a['utc'],a['density'],raw[y][c],common[y],satellite='A');assert fit.sample_count==360;poison=a['density'].copy();poison[~m]*=1e20;again,_,_=rolling.fit(a['utc'],poison,raw[y][c],common[y],satellite='A');assert fit==again;coefobjects[y][c]=fit
   params[y][c]=dict(b18=fit.log_bias,multiplier18=fit.multiplier,N=fit.sample_count,first_fit_UTC=str(a['utc'][m][0]),last_fit_UTC=str(a['utc'][m][-1]),future_poison_invariant=True)
   for i,v in zip(np.flatnonzero(m),e):residuals.append(dict(year=y,case=c,UTC=str(a['utc'][i])+'Z',latitude_deg=float(a['latitude'][i]),height_m=float(a['altitude'][i]),log_obs_minus_model=float(v)))
 applied={}
 for y in data:
  other='2022' if y=='2021' else '2021';applied[y]=dict(Adaptive18=params[y]['B14']['b18'],Stale06=float(pr['stale06_coefficients'][y]),CrossYearTransfer18=params[other]['B14']['b18'])
 dump('correction_parameters.json',dict(protocol_SHA256=sha(F/'frozen_protocol.json'),adaptive18=params,B14_applied_b=applied,all_parameters_frozen_before_future_metrics=True,Swarm_A_only=True,no_C_or_B_read=True));table('calibration_residuals.csv',residuals);print('ALL HISTORY COEFFICIENTS FROZEN BEFORE FUTURE SCORES',flush=True)
 metrics=[];regionrows=[];timeblocks=[];coverage=[];pointwise=[];joint=[];binsout=[];identities=[]
 for y,a in data.items():
  masks=RollingOrigin(y+'-03-24').masks(a['utc']);masks['block_0_1h']=masks['future_1h'];predictions[y]={};regions={k:v for k,v in strata(a['latitude'],a['altitude'],a['utc']).items() if not k.startswith('UTC_')}
  for latname in ['low','mid','high']:
   for heightname in [n for n in regions if n.startswith('height_') and n!='height_outside_bins']:regions[latname+'__'+heightname]=regions[latname]&regions[heightname]
  for c in CASES:
   methods=['Raw','Adaptive18']+(['Stale06','CrossYearTransfer18'] if c=='B14' else []);pp={'Raw':raw[y][c],'Adaptive18':coefobjects[y][c].apply(raw[y][c])}
   for method in methods[2:]:pp[method]=LogMedianCorrection(applied[y][method],360).apply(raw[y][c])
   predictions[y][c]=pp
   for window,win in masks.items():
    selected=win&common[y];eligible=int((win&a['quality']).sum());coverage.append(dict(year=y,case=c,window=window,N_eligible=eligible,N_query_valid=int((win&np.isfinite(raw[y][c])).sum()),N_common=int(selected.sum()),coverage=float(selected.sum()/eligible),failure_reasons='{}'))
    scores={}
    for region,reg in regions.items():
     scores[region]={};m=selected&reg
     for method,pred in pp.items():
      row=metric_row(pred,a['density'],a['quality'],common[y],win&reg);scores[region][method]=row;rec=dict(year=y,case=c,window=window,region=region,method=method,**row)
      (metrics if region=='all' else regionrows).append(rec)
      if region=='all' and window.startswith('block_'):timeblocks.append(rec)
      if method!='Raw':
       er=abs(raw[y][c][m]-a['density'][m]);ec=abs(pred[m]-a['density'][m]);pointwise.append(dict(year=y,case=c,window=window,region=region,method=method,N=int(m.sum()),improved=int((ec<er).sum()),worsened=int((ec>er).sum()),unchanged=int((ec==er).sum())))
    for method in methods[1:]:
     rawscore=scores['all']['Raw'];score=scores['all'][method];joint.append(dict(year=y,case=c,window=window,method=method,N=score['n'],RMSE_gain_pct=100*(1-score['RMSE']/rawscore['RMSE']),relative_RMS_gain_pct=100*(1-score['relative_RMS']/rawscore['relative_RMS']),**joint_flags(rawscore,score,scores['low']['Raw'],scores['low'][method])))
    if window=='analysis' or window=='block_0_1h':continue # duplicate1h appears once in decomposition
    obs=a['density'][selected];idx,edges=diagnostic_quintiles(obs)
    for method,predall in pp.items():
     pred=predall[selected];err=pred-obs;rel=pred/obs-1;N=len(obs);sse=float(np.sum(err**2));rsse=float(np.sum(rel**2));weighted=float(np.mean(obs**2*rel**2));assert np.isclose(weighted,np.mean(err**2),rtol=1e-13,atol=0)
     identities.append(dict(year=y,case=c,window=window,method=method,N=N,RMSE_squared=float(np.mean(err**2)),density_weighted_relative_MSE=weighted,relative_MSE=float(np.mean(rel**2))))
     for b in range(5):
      mask=idx==b;n=int(mask.sum());abs_part=float(np.sum(err[mask]**2));rel_part=float(np.sum(rel[mask]**2))
      binsout.append(dict(year=y,case=c,window=window,method=method,quintile=b+1,N=n,window_N=N,density_lower_kg_m3=float(edges[b]),density_upper_kg_m3=float(edges[b+1]),observed_mean_kg_m3=float(np.mean(obs[mask])) if n else None,absolute_SSE=abs_part,absolute_MSE_contribution=abs_part/N,absolute_SSE_share=abs_part/sse if sse else None,total_absolute_SSE=sse,relative_SSE=rel_part,relative_MSE_contribution=rel_part/N,relative_SSE_share=rel_part/rsse if rsse else None,total_relative_SSE=rsse,mean_relative_bias=float(np.mean(rel[mask])) if n else None,log_RMS=float(np.sqrt(np.mean(np.log(pred[mask]/obs[mask])**2))) if n else None))
 table('metrics.csv',metrics);table('region_metrics.csv',regionrows);table('time_block_metrics.csv',timeblocks);table('coverage.csv',coverage);table('pointwise_diagnostics.csv',pointwise);table('density_bin_decomposition.csv',binsout);table('joint_assessment.csv',joint);table('weight_identity_checks.csv',identities)
 dump('query_audit.json',dict(cases=coverage_audit,real_interpolation_probes=probe,explicit_fill_scan=scans));arrays={}
 for y,a in data.items():
  for k,v in a.items():arrays[y+'_'+k]=v
  arrays[y+'_common']=common[y]
  for c in CASES:
   for method,pred in predictions[y][c].items():arrays[y+'_'+c+'_'+method]=pred
 np.savez_compressed(F/'matched_local.npz',**arrays)
 # All displayed primary series and bins were fixed before evaluation.
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for y,ax in zip(data,axes):
  for c in CASES:ax.hist([x['log_obs_minus_model'] for x in residuals if x['year']==y and x['case']==c],bins=25,alpha=.4,label=c)
  ax.set(xlabel='ln(observed / model)',ylabel='30-second historical records',title=y+' [15,18)');ax.legend()
 save(fig,'01_late_history_residuals.png')
 fig,axes=plt.subplots(1,2,figsize=(10,4));xx=np.arange(2)
 for i,(name,vals) in enumerate([('06Z stale',[float(pr['stale06_coefficients'][y]) for y in data]),('18Z adaptive',[params[y]['B14']['b18'] for y in data])]):axes[0].bar(xx+(i-.5)*.35,vals,.35,label=name);axes[1].bar(xx+(i-.5)*.35,np.exp(vals),.35,label=name)
 for ax,title in zip(axes,['B14 log correction b','B14 density multiplier']):ax.set(xticks=xx,xticklabels=list(data),ylabel='Dimensionless',title=title);ax.legend(fontsize=8)
 axes[0].axhline(0,color='k',lw=.7);axes[1].axhline(1,color='k',lw=.7);save(fig,'02_morning_evening_coefficients.png')
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for y,ax in zip(data,axes):
  for method in ['Adaptive18','CrossYearTransfer18','Stale06']:ax.plot([1,3,6],[next(x['RMSE_gain_pct'] for x in joint if x['year']==y and x['case']=='B14' and x['method']==method and x['window']==f'future_{h}h') for h in [1,3,6]],'o-',label=method)
  ax.axhline(0,color='k',ls='--');ax.set(xlabel='Cumulative forecast window [h]',ylabel='RMSE reduction [%]',title=y+' B14 (other-year transfer)');ax.legend(fontsize=7)
 save(fig,'03_bidirectional_transfer.png')
 fig,axes=plt.subplots(2,1,figsize=(12,7))
 for y,ax in zip(data,axes):
  a=data[y];hours=(a['utc']-np.datetime64(y+'-03-24'))/np.timedelta64(1,'h');future=RollingOrigin(y+'-03-24').masks(a['utc'])['future_6h'];ax.plot(hours[future],a['density'][future]*1e12,'k',label='POD observation')
  for method,pred in predictions[y]['B14'].items():ax.plot(hours[future],pred[future]*1e12,label=method,lw=.8)
  for h in [18,19,21,24]:ax.axvline(h,color='gray',ls=':',lw=.6)
  ax.set(xlabel='UTC hour',ylabel='Density [1e-12 kg/m3]',title=y+' future [18,24)');ax.legend(fontsize=7)
 save(fig,'04_future_density_series.png')
 fig,axes=plt.subplots(2,2,figsize=(12,7))
 for row,y in enumerate(data):
  for ax,key,label in zip(axes[row],['RMSE_gain_pct','relative_RMS_gain_pct'],['RMSE reduction [%]','Relative RMS reduction [%]']):
   for method in METHODS[1:]:ax.plot([1,3,6],[next(x[key] for x in joint if x['year']==y and x['case']=='B14' and x['method']==method and x['window']==f'future_{h}h') for h in [1,3,6]],'o-',label=method)
   ax.axhline(0,color='k',ls='--');ax.set(xlabel='Cumulative window [h]',ylabel=label,title=y);ax.legend(fontsize=7)
 save(fig,'05_absolute_relative_gains.png')
 for num,contrib,label in [('06','absolute_MSE_contribution','Contribution to total absolute MSE [kg2/m6]'),('07','relative_MSE_contribution','Contribution to total relative MSE [dimensionless]')]:
  fig,axes=plt.subplots(1,2,figsize=(12,4));x=np.arange(5)
  for y,ax in zip(data,axes):
   for i,method in enumerate(METHODS):
    rr=[r for r in binsout if r['year']==y and r['case']=='B14' and r['window']=='future_6h' and r['method']==method];ax.bar(x+(i-1.5)*.19,[r[contrib] for r in rr],.19,label=method)
   ax.set(xticks=x,xticklabels=['Q1 low','Q2','Q3','Q4','Q5 high'],ylabel=label,title=y+' future720 records; descriptive bins');ax.legend(fontsize=7)
  save(fig,num+'_density_bin_contribution.png')
 fig,axes=plt.subplots(2,2,figsize=(12,7));hs=['height_400_430km','height_430_440km','height_440_450km','height_450_460km','height_460_470km','height_470_500km']
 for row,y in enumerate(data):
  for col,method in enumerate(['Adaptive18','CrossYearTransfer18']):
   arr=np.full((3,len(hs)),np.nan)
   for j,lat in enumerate(['low','mid','high']):
    for k,h in enumerate(hs):
     rr=[x for x in regionrows if x['year']==y and x['case']=='B14' and x['window']=='future_6h' and x['region']==lat+'__'+h];v={x['method']:x for x in rr}
     if v[method]['status']=='OK':arr[j,k]=100*(1-v[method]['relative_RMS']/v['Raw']['relative_RMS'])
   ax=axes[row,col];im=ax.imshow(np.ma.masked_invalid(arr),aspect='auto',vmin=-100,vmax=100,cmap='RdBu');ax.set(xticks=np.arange(len(hs)),xticklabels=['400-430','430-440','440-450','450-460','460-470','470-500'],yticks=[0,1,2],yticklabels=['low','mid','high'],xlabel='Observed ellipsoid height [km]',title=y+' '+method+' relativeRMS gain [%]')
   for j in range(3):
    for k in range(len(hs)):ax.text(k,j,'N/A' if not np.isfinite(arr[j,k]) else f'{arr[j,k]:.1f}',ha='center',va='center',fontsize=7)
   fig.colorbar(im,ax=ax)
 save(fig,'08_latitude_height_structure.png')
 fig,axes=plt.subplots(2,2,figsize=(12,7));wins=['block_0_1h','block_1_3h','block_3_6h']
 for row,y in enumerate(data):
  for ax,key,label in zip(axes[row],['RMSE_gain_pct','relative_RMS_gain_pct'],['RMSE reduction [%]','Relative RMS reduction [%]']):
   for method in METHODS[1:]:ax.plot([0,1,2],[next(x[key] for x in joint if x['year']==y and x['case']=='B14' and x['window']==w and x['method']==method) for w in wins],'o-',label=method)
   ax.axhline(0,color='k',ls='--');ax.set(xticks=[0,1,2],xticklabels=['[18,19)','[19,21)','[21,24)'],ylabel=label,title=y+' nonoverlap');ax.legend(fontsize=7)
 save(fig,'09_time_block_effects.png')
 for n,h in source['protected_inputs'].items():assert sha(ROOT/n)==h,n
 dump('run_result.json',dict(PASS=True,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,queries=6480,all_queries_valid=True,history_per_year_case=360,future_per_year=720,plots=9,no_future_fitting=True,Swarm_B_C_read=False,new_observation_bytes=0,GPU=0,TIE=0,DART=0,orbit=0));print('LATE DAY PILOT COMPLETE',flush=True)
if __name__=='__main__':main()
