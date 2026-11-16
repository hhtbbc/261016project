"""One frozen scalar correction per case; future observations are evaluation only."""
from pathlib import Path
import sys,json,csv,time,resource,warnings
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from atmosphere.causal_density_correction import fit_past_A
from atmosphere.causal_observation_operator import split_masks
from evaluation.swarm_crossyear import metric_row
from prepare_fourcastden_swarm_observation_v1 import sha
F=ROOT/'experiments/causal_density_correction_v1';FIG=F/'figures'
CASES=['B14','A7','B7','A14'];COLORS=dict(zip(CASES,['C0','C1','C2','C3']))
def dump(n,obj):
 with (F/n).open('x') as out:json.dump(obj,out,indent=2,allow_nan=False)
def table(n,rows):
 with (F/n).open('x',newline='') as out:
  w=csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def save(fig,name):
 fig.suptitle('2022-03-24 UTC | conditional density output correction | B14 primary',fontsize=11)
 fig.text(.5,.006,'PROVISIONAL Map-A / EXTERNAL_DATUM_UNVERIFIED / HINDCAST | A14 engineering PARTIAL | POD density is not error-free truth',ha='center',fontsize=7);fig.tight_layout(rect=(0,.035,1,.96));fig.savefig(FIG/name,dpi=145);plt.close(fig)
def main():
 start=time.perf_counter();protocol=json.loads((F/'frozen_protocol.json').read_text());assert sha(F/'matched_local.npz')==protocol['read_only_matching_sha'];assert json.loads((F/'preflight.json').read_text())['PASS'];assert not (F/'correction_parameters.json').exists();FIG.mkdir(exist_ok=False)
 z=np.load(F/'matched_local.npz');params={};residuals=[];maskA=split_masks(z['A_utc']);arrays={};diagnostics=[]
 # Parameter file is written before any future-error evaluation. No C values passed here.
 for case in CASES:
  fit,m,e=fit_past_A(z['A_utc'],z['A_density'],z[case+'_A'],z['A_quality'],satellite='A');assert fit.sample_count==360
  poison=z['A_density'].copy();poison[~maskA['calibration']]*=1e20;again,_,_=fit_past_A(z['A_utc'],poison,z[case+'_A'],z['A_quality'],satellite='A');assert fit==again
  params[case]=dict(b=fit.log_bias,density_multiplier=fit.multiplier,calibration_N=fit.sample_count,engineering='PARTIAL' if case=='A14' else 'PASS',calibration_first_UTC=str(z['A_utc'][m][0]),calibration_last_UTC=str(z['A_utc'][m][-1]),future_poison_invariance=True)
  arrays[case]=dict(fit=fit,m=m,e=e)
  for i,v in zip(np.flatnonzero(m),e):residuals.append(dict(case=case,engineering=params[case]['engineering'],satellite='A',UTC=str(z['A_utc'][i])+'Z',latitude_deg=float(z['A_latitude'][i]),height_m=float(z['A_altitude'][i]),log_obs_minus_model=float(v)))
  diagnostics.append(dict(case=case,N=len(e),median=float(np.median(e)),P05=float(np.percentile(e,5)),P95=float(np.percentile(e,95)),std=float(np.std(e)),correlation_with_height=float(np.corrcoef(e,z['A_altitude'][m])[0,1]),correlation_with_latitude=float(np.corrcoef(e,z['A_latitude'][m])[0,1])))
 dump('correction_parameters.json',dict(protocol_SHA256=sha(F/'frozen_protocol.json'),parameters=params,estimated_before_future_evaluation=True));table('calibration_residuals.csv',residuals);table('residual_structure.csv',diagnostics);print('FOUR HISTORY ONLY PARAMETERS FROZEN',flush=True)
 metrics=[];coverage=[];improvements=[]
 for sat in ['A','C']:
  utc=z[sat+'_utc'];obs=z[sat+'_density'];quality=z[sat+'_quality'];windows=split_masks(utc)
  if sat=='C':windows.pop('calibration')
  else:windows['analysis']=windows.pop('calibration')
  t=(utc-np.datetime64('2022-03-24'))/np.timedelta64(1,'h')
  for name,a,b in [('incremental_1_3h',7,9),('incremental_3_6h',9,12)]:windows[name]=(t>=a)&(t<b)
  valid_main=quality.copy()
  for case in ['B14','A7','B7']:valid_main&=np.isfinite(z[case+'_'+sat])&(z[case+'_'+sat]>0)
  for case in CASES:
   raw=z[case+'_'+sat];valid=quality&np.isfinite(raw)&(raw>0);common=valid_main&valid;corrected=np.full_like(raw,np.nan);corrected[valid]=arrays[case]['fit'].apply(raw[valid]);arrays[case][sat]=corrected
   for name,win in windows.items():
    if not win.any():continue
    coverage.append(dict(case=case,engineering=params[case]['engineering'],satellite=sat,window=name,N_eligible=int((quality&win).sum()),N_query_valid=int((valid&win).sum()),N_common=int((common&win).sum()),query_coverage=float((valid&win).sum()/(quality&win).sum()),failure_reasons='{}'))
    for region,r in [('all',np.ones(len(utc),bool)),('low',abs(z[sat+'_latitude'])<30),('mid',(abs(z[sat+'_latitude'])>=30)&(abs(z[sat+'_latitude'])<60)),('high',abs(z[sat+'_latitude'])>=60)]:
     row={}
     for method,pred in [('raw',raw),('corrected',corrected)]:
      mm=metric_row(pred,obs,quality,common,win&r);selected=common&win&r;mm['mean_log_model_minus_obs']=float(np.mean(np.log(pred[selected]/obs[selected]))) if selected.sum()>=30 else None
      row[method]=mm;metrics.append(dict(case=case,engineering=params[case]['engineering'],satellite=sat,window=name,region=region,method=method,**mm))
     if region=='all':improvements.append(dict(case=case,engineering=params[case]['engineering'],satellite=sat,window=name,N=row['raw']['n'],raw_RMSE=row['raw']['RMSE'],corrected_RMSE=row['corrected']['RMSE'],RMSE_improvement_pct=100*(1-row['corrected']['RMSE']/row['raw']['RMSE']),raw_relative_RMS_pct=100*row['raw']['relative_RMS'],corrected_relative_RMS_pct=100*row['corrected']['relative_RMS'],relative_RMS_improvement_pct=100*(1-row['corrected']['relative_RMS']/row['raw']['relative_RMS'])))
 table('metrics.csv',metrics);table('coverage.csv',coverage);table('improvements.csv',improvements)
 # All examples fixed beforehand: B14 primary; no best-case sample selection.
 m=arrays['B14']['m'];hours=(z['A_utc']-np.datetime64('2022-03-24'))/np.timedelta64(1,'h');e=arrays['B14']['e'];b=params['B14']['b']
 fig,axes=plt.subplots(1,3,figsize=(14,4))
 for case in CASES:axes[0].plot(hours[m],arrays[case]['e'],lw=.8,label=case+(' PARTIAL' if case=='A14' else ''))
 axes[0].set(xlabel='UTC hour',ylabel='ln(observed / model)',title='A history [03,06)');axes[0].legend(fontsize=7)
 axes[1].scatter(z['A_altitude'][m]/1000,e,s=5);axes[1].set(xlabel='GRS80 height [km]',ylabel='ln(observed / B14)',title='Frozen calibration residuals')
 axes[2].scatter(z['A_latitude'][m],e,s=5);axes[2].set(xlabel='Geodetic latitude [deg]',ylabel='ln(observed / B14)',title='Frozen calibration residuals');save(fig,'01_history_residual_structure.png')
 fig,axes=plt.subplots(1,2,figsize=(10,4));axes[0].hist(e,bins=25);axes[0].axvline(b,color='r',label=f'median={b:.6f}');axes[0].legend();axes[0].set(xlabel='ln(observed / B14)',ylabel='30-second records (correlated)',title='Past A only')
 axes[1].bar(CASES,[params[c]['density_multiplier'] for c in CASES]);axes[1].axhline(1,color='k',ls='--');axes[1].set(ylabel='exp(b) [dimensionless]',title='History-only frozen multiplier');save(fig,'02_coefficients_and_histogram.png')
 for sat,num in [('A','03'),('C','04')]:
  utc=z[sat+'_utc'];h=(utc-np.datetime64('2022-03-24'))/np.timedelta64(1,'h');mask=split_masks(utc)['future_6h'];fig,axes=plt.subplots(2,1,figsize=(11,6),sharex=True)
  for label,y,color in [('POD observation',z[sat+'_density'],'k'),('B14 raw',z['B14_'+sat],'C0'),('B14 corrected',arrays['B14'][sat],'C1')]:axes[0].plot(h[mask],y[mask]*1e12,label=label,color=color,lw=1)
  axes[0].set(ylabel='Density [1e-12 kg/m3]',title=f'Swarm {sat} | '+('future temporal extrapolation' if sat=='A' else 'cross-satellite development diagnostic'));axes[0].legend(fontsize=8)
  for label,y in [('raw',z['B14_'+sat]),('corrected',arrays['B14'][sat])]:axes[1].plot(h[mask],100*(y[mask]/z[sat+'_density'][mask]-1),label=label)
  for ax in axes:
   for x in [6,7,9,12]:ax.axvline(x,color='gray',ls=':',lw=.7)
  axes[1].set(xlabel='2022-03-24 UTC hour',ylabel='Signed relative residual [%]');axes[1].legend();save(fig,f'{num}_Swarm_{sat}_future.png')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for ax,sat in zip(axes,['A','C']):
  rr=[next(x for x in improvements if x['case']=='B14' and x['satellite']==sat and x['window']==f'future_{h}h') for h in [1,3,6]];xx=np.arange(3);ax.bar(xx-.18,[x['raw_RMSE']*1e13 for x in rr],.36,label='raw');ax.bar(xx+.18,[x['corrected_RMSE']*1e13 for x in rr],.36,label='corrected');ax.set(xticks=xx,xticklabels=['[06,07)','[06,09)','[06,12)'],ylabel='RMSE [1e-13 kg/m3]',title=f'B14 vs Swarm {sat}');ax.legend()
 save(fig,'05_future_RMSE.png')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for ax,sat in zip(axes,['A','C']):
  for case in CASES:
   rr=[next(x for x in improvements if x['case']==case and x['satellite']==sat and x['window']==f'future_{h}h') for h in [1,3,6]];ax.plot([1,3,6],[x['RMSE_improvement_pct'] for x in rr],'o-',label=case+(' PARTIAL' if case=='A14' else ''))
  ax.axhline(0,color='k',ls='--');ax.set(xlabel='Cumulative future window [h]',ylabel='RMSE reduction [%]; negative=worse',title=f'Swarm {sat}');ax.legend(fontsize=7)
 save(fig,'06_improvement_by_horizon.png')
 # Explicit final numerical audit on identical sample arrays, without refitting.
 verify=[]
 for case in CASES:
  for sat in ['A','C']:
   mm=split_masks(z[sat+'_utc'])['future_6h'];p=z[case+'_'+sat][mm];obs=z[sat+'_density'][mm];pred=p*params[case]['density_multiplier'];rr=np.sqrt(np.mean((pred-obs)**2));target=next(x for x in improvements if x['case']==case and x['satellite']==sat and x['window']=='future_6h');assert np.isclose(rr,target['corrected_RMSE'],rtol=1e-14,atol=0);verify.append(dict(case=case,satellite=sat,N=len(p),direct_RMSE=rr,PASS=True))
 dump('fit_evaluation_verification.json',dict(PASS=True,future_poison_invariance_all_cases=True,parameters_frozen_before_future_metrics=True,Swarm_C_fit_samples=0,Swarm_B_read=False,direct_metrics=verify,identical_raw_corrected_masks=True))
 for n,h in json.loads((F/'matched_samples_manifest.json').read_text())['protected_inputs'].items():assert sha(ROOT/n)==h,n
 dump('evaluation_run.json',dict(PASS=True,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,parameters=4,new_physics_runs=0,plots=6));print('CAUSAL SCALAR PILOT COMPLETE',flush=True)
if __name__=='__main__':main()
