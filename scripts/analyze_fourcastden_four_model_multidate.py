"""Five equal windows, common raw physical targets; January is only read."""
import sys,json,csv,time,itertools,resource
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_fourcastden_multistep import sha,dump
from run_fourcastden_four_model_multidate import F,D,JAN,JAND,MODELS
from fourcastden.four_model_windows import ALL_DATES,summarize_windows
from fourcastden.validation import NAMES,LENGTHS,UNITS,SI_UNITS,SI_FACTORS,channel_metrics,feedback_check
from fourcastden.history import history_feedback_check
from fourcastden.logden import decode_physical
TAG='fourcastden_four_model_multidate_v1'
def write(name,rows):
 with (ROOT/f'results/metrics/{TAG}_{name}.csv').open('x') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def save(fig,name):
 fig.suptitle('Official four models: five 2023 dates, common 01 UTC initialization\nHINDCAST / TIE-GCM reference / native pressure levels / extra history input for History',fontsize=9);fig.tight_layout(rect=[0,0,1,.90]);p=ROOT/f'results/figures/{TAG}_{name}.png';assert not p.exists();fig.savefig(p,dpi=150);plt.close(fig)
def source(day,model):return JAND/f'{model}.npz' if day==ALL_DATES[0] else D/f'{day}_{model}.npz'
def rawpath(day,h):
 if day==ALL_DATES[0]:return JAN/'data_view'/f'2023_01_04_{h:02d}0000.npz'
 return F/'data_view'/f"{day.replace('-','_')}_{h:02d}0000.npz"
def main():
 tick=time.perf_counter();runtime=json.loads((F/'runtime.json').read_text());assert runtime['status']=='PASS';jan=json.loads((JAN/'runtime.json').read_text());lat=np.load(ROOT/'data/processed/static/lat.npy');ilev=np.load(ROOT/'data/processed/static/ilev.npy');lev=np.load(ROOT/'data/processed/static/lev.npy');w=np.broadcast_to(np.cos(np.deg2rad(lat))[:,None],(36,72));w=w/w.mean()
 layers=[];summary=[];density=[];windows=[];native=[];nativechecks=[];conditions=[];drivers=[];reference_changes=[]
 for day in ALL_DATES:
  q={}
  for m in MODELS:
   p=source(day,m);r=next(r for r in (jan if day==ALL_DATES[0] else runtime)['records'] if r['model']==m and (day==ALL_DATES[0] or r['date']==day));assert sha(p)==r['result_sha256']
   with np.load(p) as z:q[m]={k:z[k].copy() for k in z.files}
  raw=[];heights=[]
  for h in range(4):
   with np.load(rawpath(day,h)) as z:
    raw.append(np.concatenate([z[k] for k in NAMES],axis=0).astype(float));heights.append(z['ZG'].astype(float)*.01);drivers.append(dict(date=day,hour_UTC=h,**{k:float(z[k][0]) for k in ['f107d','f107a','Kp']}))
  truth=np.stack(raw[1:]);clim=q['Direct']['climatology'].astype(float);physical={m:decode_physical(x['pred'][0],x['means'][:171],x['stds'][:171],m=='LogDEN') for m,x in q.items()};physical['Persistence']=np.repeat(truth[:1],3,axis=0)
  for h in range(1,4):
   r,_,_=channel_metrics(raw[h],raw[h-1],clim,lat);off=0
   for name,n,factor,unit in zip(NAMES,LENGTHS,SI_FACTORS,SI_UNITS):reference_changes.append(dict(date=day,from_hour_UTC=h-1,to_hour_UTC=h,variable=name,SI_unit=unit,mean_layer_reference_increment_RMSE_SI=float(r[off:off+n].mean()*factor)));off+=n
  for m,x in q.items():
   inp=[(x[f'input{k}'],x[f'scalars{k}']) for k in range(2)];out=[x[f'out{k}'] for k in range(2)]
   check=history_feedback_check(inp,out,x['full_data'],x['full_sw']) if m=='History' else feedback_check(inp,out,x['real'][0],x['full_sw'])
   for h in (1,2):
    p=x['pred'][0,h];t=x['real'][0,h,:171];nc=(x['climatology']-x['means'][:171])/x['stds'][:171];r,a,v=channel_metrics(p,t,nc,lat)
    np.testing.assert_allclose(r,x['author_normalized_rmse'][h-1],rtol=2e-5,atol=1e-25);np.testing.assert_allclose(a[v],x['author_acc'][0,h-1][v],rtol=2e-5,atol=2e-6)
    if m=='LogDEN':
     dr=np.sqrt(np.mean(w*(x['author_physical_den_pred'][h-1].astype(float)-x['author_physical_den_target'][h-1].astype(float))**2,axis=(1,2)));np.testing.assert_allclose(dr,x['author_rmse'][0,h-1,142:],rtol=2e-5,atol=1e-25)
    else:np.testing.assert_allclose(r*x['stds'][:171,0,0],x['author_rmse'][0,h-1],rtol=2e-5,atol=1e-25)
    nativechecks.append(dict(date=day,model=m,hour=h,RMSE_max_relative=float(np.max(abs(r-x['author_normalized_rmse'][h-1])/r)),ACC_max_abs=float(np.max(abs(a[v]-x['author_acc'][0,h-1][v])))))
    current=x[f'input{h-1}'][0,177:354] if m=='History' else x[f'input{h-1}'][0];di=q['Direct'][f'input{h-1}'][0];np.testing.assert_array_equal(x[f'scalars{h-1}'],q['Direct'][f'scalars{h-1}']);np.testing.assert_array_equal(current[175:],di[175:])
    conditions.append(dict(date=day,model=m,hour=h,scalar_exact=True,magnetic_exact=True,SEA_max_abs=float(np.max(abs(current[174]-di[174]))),feedback_exact=check['passed']))
    off=0
    for name,n,unit in zip(NAMES,LENGTHS,UNITS):
     for k,c in enumerate(range(off,off+n)):native.append(dict(date=day,model=m,hour=h,variable=name,layer_index=k,author_returned_RMSE=float(x['author_rmse'][0,h-1,c]),native_unit=unit,normalized_RMSE=float(r[c]),std_scaled_native_RMSE=float(r[c]*x['stds'][c,0,0]),std_scaled_unit='dex' if m=='LogDEN' and name=='DEN' else unit,author_ACC=float(x['author_acc'][0,h-1,c]),ACC_space='log10(g/cm3), own log climatology' if m=='LogDEN' and name=='DEN' else 'own physical climatology'))
     off+=n
  for h in (1,2):
   med=np.median(heights[h+1],axis=(1,2))/1000;near=np.flatnonzero((med>=400)&(med<=500));assert len(near)>0
   for m,p in physical.items():
    r,a,v=channel_metrics(p[h],truth[h],clim,lat);off=0
    for name,n,unit,factor in zip(NAMES,LENGTHS,SI_UNITS,SI_FACTORS):
     sl=slice(off,off+n);summary.append(dict(date=day,model=m,hour=h,target_hour_UTC=h+1,variable=name,SI_unit=unit,mean_layer_RMSE_SI=float(r[sl].mean()*factor),mean_layer_ACC=float(a[sl][v[sl]].mean()) if v[sl].any() else '',bias_SI=float(np.mean(w*(p[h,sl]-truth[h,sl]))*factor),prediction_min_SI=float(p[h,sl].min()*factor),prediction_max_SI=float(p[h,sl].max()*factor)))
     for k,c in enumerate(range(off,off+n)):layers.append(dict(date=day,model=m,hour=h,variable=name,layer_index=k,vertical_grid='lev' if n==28 else 'ilev',pressure_coordinate=float(lev[k] if n==28 else ilev[k]),SI_unit=unit,RMSE_SI=float(r[c]*factor),physical_ACC=float(a[c]) if v[c] else '',ACC_valid=bool(v[c])))
     off+=n
    rel=p[h,142:]/truth[h,142:]-1;ln=np.log(p[h,142:]/truth[h,142:]);g=[];polar=[]
    for region,mask in [('global',np.ones((36,72),bool)),('polar',np.broadcast_to((abs(lat)>=60)[:,None],(36,72))),('nonpolar',np.broadcast_to((abs(lat)<60)[:,None],(36,72)))]:
     ww=w[mask]/w[mask].mean()
     for k in range(29):
      e=rel[k][mask];lg=ln[k][mask];row=dict(date=day,model=m,hour=h,region=region,ilev_index=k,ilev=float(ilev[k]),reference_ZG_global_median_km=float(med[k]),relative_RMS=float(np.sqrt(np.mean(ww*e**2))),relative_P95=float(np.percentile(abs(e),95)),relative_max=float(abs(e).max()),natural_log_RMS=float(np.sqrt(np.mean(ww*lg**2))),natural_log_bias=float(np.mean(ww*lg)),positive_fraction=1.);density.append(row)
      if region=='global':g.append(row)
      if region=='polar':polar.append(row)
    windows.append(dict(date=day,model=m,hour=h,mean_DEN_layer_RMSE_kg_m3=float(r[142:].mean()*1000),DEN_all_layer_mean_relative_RMS=float(np.mean([x['relative_RMS'] for x in g])),DEN_absolute_relative_P95_all_points=float(np.percentile(abs(rel),95)),DEN_all_layer_mean_log_RMS=float(np.mean([x['natural_log_RMS'] for x in g])),near400_500_indices=','.join(map(str,near)),near400_500_medians_km=','.join(f'{med[k]:.3f}' for k in near),near400_500_mean_relative_RMS=float(np.mean([g[k]['relative_RMS'] for k in near])),near400_500_mean_log_RMS=float(np.mean([g[k]['natural_log_RMS'] for k in near])),upper20_28_mean_relative_RMS=float(np.mean([g[k]['relative_RMS'] for k in range(20,29)])),top_relative_P95=g[-1]['relative_P95'],top_relative_RMS=g[-1]['relative_RMS'],polar_relative_max=max(x['relative_max'] for x in polar),DEN_positive_fraction=1.))
  del q,physical,truth
 # Jan4 numerical values must exactly reproduce its published common-01 metrics.
 oldjan=json.loads((JAN/'analysis.json').read_text());jan_checks=0
 for r in windows:
  if r['date']!=ALL_DATES[0]:continue
  old=next(x for x in oldjan['windows'] if x['model']==r['model'] and x['hour']==r['hour'])
  for key in ['mean_DEN_layer_RMSE_kg_m3','near400_500_mean_relative_RMS','near400_500_mean_log_RMS','top_relative_P95']:
   np.testing.assert_allclose(r[key],old[key],rtol=1e-12,atol=1e-25);jan_checks+=1
 def win(d,m,h):return next(r for r in windows if r['date']==d and r['model']==m and r['hour']==h)
 aggregate=[];density_aggregate=[];pairs=[];density_pairs=[];growth=[];rankings=[]
 density_keys=['mean_DEN_layer_RMSE_kg_m3','near400_500_mean_relative_RMS','near400_500_mean_log_RMS','upper20_28_mean_relative_RMS','DEN_absolute_relative_P95_all_points']
 for h in (1,2):
  for m in MODELS:
   for name,unit in zip(NAMES,SI_UNITS):aggregate.append(dict(model=m,hour=h,variable=name,SI_unit=unit,**summarize_windows([next(r['mean_layer_RMSE_SI'] for r in summary if r['date']==d and r['model']==m and r['hour']==h and r['variable']==name) for d in ALL_DATES])))
   for key in density_keys:density_aggregate.append(dict(model=m,hour=h,metric=key,**summarize_windows([win(d,m,h)[key] for d in ALL_DATES])))
  for day in ALL_DATES:
   for key in density_keys:
    values={m:win(day,m,h)[key] for m in MODELS};rankings.append(dict(date=day,hour=h,metric=key,ranking_low_to_high=' < '.join(sorted(values,key=values.get)),**values))
   for m,n in itertools.combinations(MODELS,2):
    for key in density_keys:density_pairs.append(dict(date=day,hour=h,model_A=m,model_B=n,metric=key,A_minus_B=win(day,m,h)[key]-win(day,n,h)[key],A_over_B=win(day,m,h)[key]/win(day,n,h)[key]))
    for name,unit in zip(NAMES,SI_UNITS):
     values={mm:next(r['mean_layer_RMSE_SI'] for r in summary if r['date']==day and r['model']==mm and r['hour']==h and r['variable']==name) for mm in [m,n]};pairs.append(dict(date=day,hour=h,variable=name,SI_unit=unit,model_A=m,model_B=n,A_minus_B=values[m]-values[n],A_over_B=values[m]/values[n]))
 for day in ALL_DATES:
  for m in MODELS:
   for name in NAMES:
    vals=[next(r['mean_layer_RMSE_SI'] for r in summary if r['date']==day and r['model']==m and r['hour']==h and r['variable']==name) for h in (1,2)];growth.append(dict(date=day,model=m,variable=name,RMSE_hour2_to_hour1=vals[1]/vals[0],near400_500_RMS_hour2_to_hour1=win(day,m,2)['near400_500_mean_relative_RMS']/win(day,m,1)['near400_500_mean_relative_RMS']))
 old=json.loads((ROOT/'experiments/fourcastden_logden_multidate_v1/analysis.json').read_text());initialization=[]
 for day in ALL_DATES:
  for m in ('Direct','Flow','LogDEN'):
   for lead_old,lead_new,kind in [(1,1,'same lead, different targets'),(2,2,'same lead, different targets'),(2,1,'same target02, different lead and initial information')]:
    ow=next(x for x in old['windows'] if x['date']==day and x['model']==m and x['hour']==lead_old);nw=win(day,m,lead_new)
    for key in ['mean_DEN_layer_RMSE_kg_m3','near400_500_mean_relative_RMS']:
     initialization.append(dict(date=day,model=m,comparison=kind,old_t0_hour=0,new_t0_hour=1,old_lead=lead_old,new_lead=lead_new,metric=key,old_value=ow[key],new_value=nw[key],new_over_old=nw[key]/ow[key]))
    for name,unit in zip(NAMES,SI_UNITS):
     ov=next(x['mean_layer_RMSE_SI'] for x in old['summary'] if x['date']==day and x['model']==m and x['hour']==lead_old and x['variable']==name);nv=next(x['mean_layer_RMSE_SI'] for x in summary if x['date']==day and x['model']==m and x['hour']==lead_new and x['variable']==name);initialization.append(dict(date=day,model=m,comparison=kind,old_t0_hour=0,new_t0_hour=1,old_lead=lead_old,new_lead=lead_new,metric=name+'_RMSE_'+unit,old_value=ov,new_value=nv,new_over_old=nv/ov))
 performance=[]
 for day in ALL_DATES:
  for m in MODELS:
   r=next(x for x in (jan if day==ALL_DATES[0] else runtime)['records'] if x['model']==m and (day==ALL_DATES[0] or x['date']==day));performance.append(dict(date=day,model=m,origin='read-only historical January, separate process' if day==ALL_DATES[0] else 'current shared process; model loaded once for four dates',parameters=r['parameters'],model_load_s=r['model_load_s'],model_reused=r.get('model_reused',False),read_preprocess_s=r['read_preprocess_s'],author_loop_metrics_hooks_s=r['author_loop_metrics_hooks_s'],save_s=r['save_s'],first_forward_ms=r['GPU_forward_ms'][0],second_forward_ms=r['GPU_forward_ms'][1],peak_allocated_bytes=r['peak_allocated_bytes'],peak_reserved_bytes=r['peak_reserved_bytes'],process_peak_RSS_KiB=r['RSS_KiB'],controlled_throughput=False))
 for name,rows in [('layers',layers),('summary',summary),('density_layers',density),('windows',windows),('author_native',native),('aggregate',aggregate),('density_aggregate',density_aggregate),('pairs',pairs),('density_pairs',density_pairs),('growth',growth),('rankings',rankings),('initialization',initialization),('performance',performance),('drivers',drivers),('reference_changes',reference_changes)]:write(name,rows)
 colors=dict(Direct='tab:blue',Flow='tab:orange',LogDEN='tab:green',History='tab:purple');x=np.arange(5);labels=[d[5:] for d in ALL_DATES]
 for key,title,suffix,factor,unit in [('near400_500_mean_relative_RMS','Native layers: median reference ZG 400–500 km','high_DEN',100,'Mean layer relative RMS (%)'),('mean_DEN_layer_RMSE_kg_m3','DEN mean absolute layer RMSE','absolute_DEN',1,'kg/m³')]:
  fig,axes=plt.subplots(1,2,figsize=(12,4))
  for h,ax in zip((1,2),axes):
   for m in MODELS:ax.plot(x,[win(d,m,h)[key]*factor for d in ALL_DATES],'o-',label=m,color=colors[m])
   ax.set(xticks=x,xticklabels=labels,ylabel=unit,title=title+f' +{h}h');ax.legend()
  save(fig,suffix)
 fig,axes=plt.subplots(2,3,figsize=(14,8))
 for ax,name,unit in zip(axes.flat,NAMES,SI_UNITS):
  for m in MODELS:
   for h in (1,2):ax.plot(x,[next(r['mean_layer_RMSE_SI'] for r in summary if r['date']==d and r['model']==m and r['hour']==h and r['variable']==name) for d in ALL_DATES],'o-' if h==1 else 's--',label=f'{m} +{h}h',color=colors[m])
  ax.set(xticks=x,xticklabels=labels,ylabel=f'Mean layer RMSE ({unit})',title=name,yscale='log');ax.legend(fontsize=6)
 save(fig,'variables')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for key,ax,title in zip(['mean_DEN_layer_RMSE_kg_m3','near400_500_mean_relative_RMS'],axes,['Absolute DEN RMSE growth','Near400–500 native group relative RMS growth']):
  for m in MODELS:ax.plot(x,[win(d,m,2)[key]/win(d,m,1)[key] for d in ALL_DATES],'o-',label=m,color=colors[m])
  ax.set(xticks=x,xticklabels=labels,ylabel='+2h / +1h',title=title);ax.axhline(1,color='k',ls='--');ax.legend()
 save(fig,'growth')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for h,ax in zip((1,2),axes):
  for key,label in [('mean_DEN_layer_RMSE_kg_m3','All-layer absolute RMSE'),('near400_500_mean_relative_RMS','Near400–500 relative RMS')]:ax.plot(x,[win(d,'History',h)[key]/win(d,'Direct',h)[key] for d in ALL_DATES],'o-',label=label)
  ax.axhline(1,color='k',ls='--');ax.set(xticks=x,xticklabels=labels,ylabel='History / Direct',title=f'+{h}h; <1 favors History',yscale='log');ax.legend()
 save(fig,'history_pairs')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for h,ax in zip((1,2),axes):
  for m in ['Direct','Flow','LogDEN']:ax.plot(x,[next(r['new_over_old'] for r in initialization if r['date']==d and r['model']==m and r['comparison']=='same lead, different targets' and r['old_lead']==h and r['metric']=='near400_500_mean_relative_RMS') for d in ALL_DATES],'o-',label=m,color=colors[m])
  ax.axhline(1,color='k',ls='--');ax.set(xticks=x,xticklabels=labels,ylabel='01t0 / 00t0 near-group relative RMS',title=f'+{h}h; DIFFERENT target times');ax.legend()
 save(fig,'initialization')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for m in MODELS:
  rr=[r for r in performance if r['model']==m];axes[0].plot(x,[r['second_forward_ms'] for r in rr],'o-',label=m,color=colors[m]);axes[1].plot(x,[r['peak_allocated_bytes']/2**20 for r in rr],'o-',label=m,color=colors[m])
 axes[0].set(xticks=x,xticklabels=labels,ylabel='GPU event ms',title='Second forward; mixed runtime/cache histories');axes[1].set(xticks=x,xticklabels=labels,ylabel='MiB',title='CUDA allocated inference peak');axes[0].legend();axes[1].legend();save(fig,'performance')
 out=dict(status='PASS',dates=list(ALL_DATES),models=list(MODELS),January_rerun=False,January_density_metric_checks=jan_checks,reference='same raw physical targets02/03; ordinary physical climatology; real01 persistence',windows=windows,summary=summary,aggregate=aggregate,density_aggregate=density_aggregate,growth=growth,rankings=rankings,initialization=initialization,native_checks=nativechecks,conditions=conditions,performance=performance,drivers=drivers,reference_changes=reference_changes,CPU_analysis_s=time.perf_counter()-tick,analysis_process_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
 dump(F/'analysis.json',out);print(json.dumps(dict(status='PASS',aggregate=aggregate,density_aggregate=density_aggregate),indent=2))
if __name__=='__main__':main()
