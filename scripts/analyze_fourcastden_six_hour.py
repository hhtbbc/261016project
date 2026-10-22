"""Offline six-lead physical and native evaluation, no extra model forwards."""
import sys,json,csv,time,resource
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_fourcastden_multistep import sha,dump
from run_fourcastden_six_hour import F,D,DATES,MODELS
from fourcastden.validation import NAMES,LENGTHS,UNITS,SI_UNITS,SI_FACTORS,channel_metrics
from fourcastden.logden import decode_physical
from fourcastden.autoregression import check_autoregression
TAG='fourcastden_six_hour_v1'
def write(name,rows):
 with (ROOT/f'results/metrics/{TAG}_{name}.csv').open('x') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def save(fig,name):
 fig.suptitle('Official Direct / Flow / log-DEN / History: continuous 6h from 01 UTC\nHINDCAST / TIE-GCM reference / native pressure levels / History has extra real00 state',fontsize=9);fig.tight_layout(rect=[0,0,1,.91]);p=ROOT/f'results/figures/{TAG}_{name}.png';assert not p.exists();fig.savefig(p,dpi=150);plt.close(fig)
def main():
 tick=time.perf_counter();rt=json.loads((F/'runtime.json').read_text());assert rt['status']=='PASS';lat=np.load(ROOT/'data/processed/static/lat.npy');ilev=np.load(ROOT/'data/processed/static/ilev.npy');lev=np.load(ROOT/'data/processed/static/lev.npy');w=np.broadcast_to(np.cos(np.deg2rad(lat))[:,None],(36,72));w=w/w.mean();layers=[];summary=[];density=[];windows=[];native=[];nativechecks=[];conditions=[];prefix=[]
 for day in DATES:
  q={}
  for m in MODELS:
   path=D/f'{day}_{m}.npz';assert sha(path)==next(r['result_sha256'] for r in rt['records'] if r['date']==day and r['model']==m)
   with np.load(path) as z:q[m]={k:z[k].copy() for k in z.files}
  raw=[];heights=[]
  for h in range(8):
   with np.load(F/'data_view'/f"{day.replace('-','_')}_{h:02d}0000.npz") as z:raw.append(np.concatenate([z[k] for k in NAMES]).astype(float));heights.append(z['ZG'].astype(float)*.01)
  truth=np.stack(raw[1:]);clim=q['Direct']['climatology'].astype(float);physical={m:decode_physical(x['pred'][0],x['means'][:171],x['stds'][:171],m=='LogDEN') for m,x in q.items()};physical['Persistence']=np.repeat(truth[:1],7,axis=0)
  for m,x in q.items():
   hist=int(m=='History');real=x['full_data'][hist:];inputs=[(x['inputs'][k:k+1],x['scalars'][k:k+1]) for k in range(6)];outputs=[x['pred'][0,k+1:k+2] for k in range(6)];rawout=[x['raw_network'][k:k+1] for k in range(6)];check=check_autoregression(inputs,outputs,x['full_data'],x['full_sw'],hist,rawout,m=='Flow')
   if day==DATES[0]:
    with np.load(ROOT/f'data/processed/fourcastden_history_comparison_v1/{m}.npz') as old:
     delta=float(np.max(abs(old['pred']-x['pred'][:,:3])));np.testing.assert_array_equal(old['pred'],x['pred'][:,:3]);prefix.append(dict(model=m,first_two_predictions_vs_historical_max_normalized_difference=delta,exact=True))
   for h in range(1,7):
    nc=(x['climatology']-x['means'][:171])/x['stds'][:171];r,a,v=channel_metrics(x['pred'][0,h],real[h,:171],nc,lat);np.testing.assert_allclose(r,x['author_normalized_rmse'][h-1],rtol=2e-5,atol=1e-25);np.testing.assert_allclose(a[v],x['author_acc'][0,h-1][v],rtol=2e-5,atol=2e-6)
    if m=='LogDEN':dr=np.sqrt(np.mean(w*(x['author_physical_den_pred'][h-1].astype(float)-x['author_physical_den_target'][h-1].astype(float))**2,axis=(1,2)));np.testing.assert_allclose(dr,x['author_rmse'][0,h-1,142:],rtol=2e-5,atol=1e-25)
    else:np.testing.assert_allclose(r*x['stds'][:171,0,0],x['author_rmse'][0,h-1],rtol=2e-5,atol=1e-25)
    nativechecks.append(dict(date=day,model=m,hour=h,normalized_RMSE_max_relative=float(np.max(abs(r-x['author_normalized_rmse'][h-1])/r)),ACC_max_abs=float(np.max(abs(a[v]-x['author_acc'][0,h-1][v])))))
    block=x['inputs'][h-1,177:354] if hist else x['inputs'][h-1];direct=q['Direct'];np.testing.assert_array_equal(x['scalars'][h-1],direct['scalars'][h-1]);np.testing.assert_array_equal(block[175:],direct['inputs'][h-1,175:]);conditions.append(dict(date=day,model=m,hour=h,scalar_exact=True,magnetic_exact=True,SEA_max_abs=float(np.max(abs(block[174]-direct['inputs'][h-1,174]))),feedback_exact=check['passed']))
    off=0
    for name,n,unit in zip(NAMES,LENGTHS,UNITS):
     for k,c in enumerate(range(off,off+n)):native.append(dict(date=day,model=m,hour=h,variable=name,layer_index=k,author_returned_RMSE=float(x['author_rmse'][0,h-1,c]),author_RMSE_unit=unit,normalized_RMSE=float(r[c]),std_scaled_native_RMSE=float(r[c]*x['stds'][c,0,0]),std_scaled_unit='dex' if m=='LogDEN' and name=='DEN' else unit,author_ACC=float(x['author_acc'][0,h-1,c]),ACC_space='log10(g/cm3), own log climatology' if m=='LogDEN' and name=='DEN' else 'own physical climatology'))
     off+=n
  for h in range(1,7):
   med=np.median(heights[h+1],axis=(1,2))/1000;near=np.flatnonzero((med>=400)&(med<=500));assert len(near)>0
   for m,p in physical.items():
    r,a,v=channel_metrics(p[h],truth[h],clim,lat);off=0
    for name,n,unit,factor in zip(NAMES,LENGTHS,SI_UNITS,SI_FACTORS):
     sl=slice(off,off+n);summary.append(dict(date=day,model=m,hour=h,target_hour_UTC=h+1,variable=name,SI_unit=unit,mean_layer_RMSE_SI=float(r[sl].mean()*factor),mean_layer_ACC=float(a[sl][v[sl]].mean()) if v[sl].any() else '',weighted_bias_SI=float(np.mean(w*(p[h,sl]-truth[h,sl]))*factor),prediction_min_SI=float(p[h,sl].min()*factor),prediction_max_SI=float(p[h,sl].max()*factor),nonfinite_count=int((~np.isfinite(p[h,sl])).sum())))
     for k,c in enumerate(range(off,off+n)):layers.append(dict(date=day,model=m,hour=h,variable=name,layer_index=k,vertical_grid='lev' if n==28 else 'ilev',pressure_coordinate=float(lev[k] if n==28 else ilev[k]),SI_unit=unit,RMSE_SI=float(r[c]*factor),physical_ACC=float(a[c]) if v[c] else '',ACC_valid=bool(v[c])))
     off+=n
    rel=p[h,142:]/truth[h,142:]-1;ln=np.log(p[h,142:]/truth[h,142:]);g=[];pol=[]
    for region,mask in [('global',np.ones((36,72),bool)),('polar',np.broadcast_to((abs(lat)>=60)[:,None],(36,72))),('nonpolar',np.broadcast_to((abs(lat)<60)[:,None],(36,72)))]:
     ww=w[mask]/w[mask].mean()
     for k in range(29):
      e=rel[k][mask];lg=ln[k][mask];row=dict(date=day,model=m,hour=h,region=region,ilev_index=k,ilev=float(ilev[k]),reference_ZG_global_median_km=float(med[k]),relative_RMS=float(np.sqrt(np.mean(ww*e**2))),relative_P95=float(np.percentile(abs(e),95)),relative_max=float(abs(e).max()),natural_log_RMS=float(np.sqrt(np.mean(ww*lg**2))),natural_log_bias=float(np.mean(ww*lg)),DEN_positive_fraction=float((p[h,142+k][mask]>0).mean()));density.append(row)
      if region=='global':g.append(row)
      if region=='polar':pol.append(row)
    windows.append(dict(date=day,model=m,hour=h,mean_DEN_layer_RMSE_kg_m3=float(r[142:].mean()*1000),all_layer_mean_relative_RMS=float(np.mean([x['relative_RMS'] for x in g])),all_point_relative_P95=float(np.percentile(abs(rel),95)),all_layer_mean_log_RMS=float(np.mean([x['natural_log_RMS'] for x in g])),near400_500_indices=','.join(map(str,near)),near400_500_median_km=','.join(f'{med[k]:.3f}' for k in near),near400_500_mean_relative_RMS=float(np.mean([g[k]['relative_RMS'] for k in near])),near400_500_mean_log_RMS=float(np.mean([g[k]['natural_log_RMS'] for k in near])),upper20_28_mean_relative_RMS=float(np.mean([g[k]['relative_RMS'] for k in range(20,29)])),top_relative_RMS=g[-1]['relative_RMS'],top_relative_P95=g[-1]['relative_P95'],polar_relative_max=max(x['relative_max'] for x in pol),upper_log_bias=float(np.mean([g[k]['natural_log_bias'] for k in range(20,29)])),DEN_positive_fraction=1.))
  del q,physical,truth
 def win(d,m,h):return next(r for r in windows if r['date']==d and r['model']==m and r['hour']==h)
 growth=[]
 for d in DATES:
  for m in MODELS:
   for name in NAMES:
    vals=np.array([next(r['mean_layer_RMSE_SI'] for r in summary if r['date']==d and r['model']==m and r['hour']==h and r['variable']==name) for h in range(1,7)]);growth.append(dict(date=d,model=m,variable=name,RMSE_6h_to_1h=float(vals[-1]/vals[0]),increasing_steps=int((np.diff(vals)>0).sum()),decreasing_steps=int((np.diff(vals)<0).sum()),first_lead_at_least_double_1h=next((i+1 for i,x in enumerate(vals) if x>=2*vals[0]),None),near_group_6h_to_1h=win(d,m,6)['near400_500_mean_relative_RMS']/win(d,m,1)['near400_500_mean_relative_RMS'],near_group_first_double=next((h for h in range(1,7) if win(d,m,h)['near400_500_mean_relative_RMS']>=2*win(d,m,1)['near400_500_mean_relative_RMS']),None)))
 performance=[]
 for r in rt['records']:performance.append(dict(date=r['date'],model=r['model'],parameters=r['parameters'],model_load_s=r['model_load_s'],model_reused=r['model_reused'],read_decode_s=r['read_decode_s'],normalization_s=r['normalization_s'],other_preprocess_s=r['preprocess_excluding_read_s']-r['normalization_s'],read_preprocess_total_s=r['read_preprocess_s'],author_loop_metrics_hooks_s=r['author_loop_metrics_hooks_s'],native_metrics_GPU_ms=r['native_metrics_GPU_ms'],native_metrics_calls_wall_s=r['native_metrics_call_wall_s'],first_formal_forward_ms=r['GPU_forward_ms'][0],later_forward_mean_ms=float(np.mean(r['GPU_forward_ms'][1:])),network_total_GPU_ms=sum(r['GPU_forward_ms']),save_s=r['save_s'],peak_allocated_bytes=r['peak_allocated_bytes'],peak_reserved_bytes=r['peak_reserved_bytes'],process_peak_RSS_KiB=r['RSS_KiB'],controlled_throughput=False))
 for name,rows in [('layers',layers),('summary',summary),('density_layers',density),('windows',windows),('author_native',native),('growth',growth),('performance',performance)]:write(name,rows)
 drivers=json.loads((F/'driver_comparison.json').read_text());write('drivers',drivers['rows'])
 colors=dict(Direct='tab:blue',Flow='tab:orange',LogDEN='tab:green',History='tab:purple')
 for key,title,suffix,factor,unit in [('near400_500_mean_relative_RMS','Native groups with median refZG 400–500km','high_DEN',100,'Mean layer relative RMS (%)'),('mean_DEN_layer_RMSE_kg_m3','DEN mean layer absolute RMSE','absolute_DEN',1,'kg/m³')]:
  fig,axes=plt.subplots(1,2,figsize=(12,4))
  for d,ax in zip(DATES,axes):
   for m in MODELS:ax.plot(range(1,7),[win(d,m,h)[key]*factor for h in range(1,7)],'o-',label=m,color=colors[m])
   ax.set(xlabel='Lead time (h)',xticks=range(1,7),ylabel=unit,title=d+': '+title);ax.legend()
  save(fig,suffix)
 fig,axes=plt.subplots(2,3,figsize=(14,8))
 for ax,name,unit in zip(axes.flat,NAMES,SI_UNITS):
  for m in MODELS:
   for d in DATES:ax.plot(range(1,7),[next(r['mean_layer_RMSE_SI'] for r in summary if r['date']==d and r['model']==m and r['hour']==h and r['variable']==name) for h in range(1,7)],'o-' if d==DATES[0] else 's--',color=colors[m],label=f'{m} {d[5:]}')
  ax.set(xlabel='Lead time (h)',ylabel=f'Mean layer RMSE ({unit})',title=name,yscale='log');ax.legend(fontsize=6)
 save(fig,'variables')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for d,ax in zip(DATES,axes):
  for m in MODELS:ax.plot(range(1,7),[win(d,m,h)['near400_500_mean_relative_RMS']/win(d,m,1)['near400_500_mean_relative_RMS'] for h in range(1,7)],'o-',label=m,color=colors[m])
  ax.set(xlabel='Lead time (h)',ylabel='Near-group relative RMS / first-hour RMS',title=d+'; ratio alone is not stability');ax.axhline(2,color='k',ls='--');ax.legend()
 save(fig,'growth')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for key,ax,title in zip(['near400_500_mean_relative_RMS','mean_DEN_layer_RMSE_kg_m3'],axes,['Near-group relative RMS','DEN mean absolute RMSE']):
  for m in MODELS:ax.plot(range(1,7),[win(DATES[1],m,h)[key]/win(DATES[0],m,h)[key] for h in range(1,7)],'o-',label=m,color=colors[m])
  ax.set(xlabel='Lead time (h)',ylabel='Mar24 / Jan4',title=title+'; NOT a causal storm response');ax.axhline(1,color='k',ls='--');ax.legend()
 save(fig,'two_dates')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for d,ax in zip(DATES,axes):
  for m in MODELS:ax.plot(ilev,[next(r['relative_RMS'] for r in density if r['date']==d and r['model']==m and r['hour']==6 and r['region']=='global' and r['ilev_index']==k)*100 for k in range(29)],color=colors[m],label=m)
  ax.set(xlabel='Native ilev (not geometric height)',ylabel='Relative RMS (%)',yscale='log',title=d+' +6h');ax.legend()
 save(fig,'layers_6h')
 fig,axes=plt.subplots(1,3,figsize=(14,4));labels=[r['date'][5:]+' '+r['model'] for r in performance]
 for ax,key,title,unit in [(axes[0],'network_total_GPU_ms','Six actual network forwards','GPU event ms'),(axes[1],'author_loop_metrics_hooks_s','Author loop incl. I/O/metrics/hooks','s'),(axes[2],'peak_allocated_bytes','Inference CUDA allocated peak','MiB')]:
  ax.bar(range(8),[r[key]/2**20 if key=='peak_allocated_bytes' else r[key] for r in performance]);ax.set(xticks=range(8),xticklabels=labels,ylabel=unit,title=title);ax.tick_params(axis='x',rotation=75,labelsize=7)
 save(fig,'performance')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for d,ax in zip(DATES,axes):
  rr=[r for r in drivers['rows'] if r['date']==d];ax.plot(range(8),[r['author_Kp'] for r in rr],'o-',label='Author NPZ Kp')
  valid=[r for r in rr if r['GFZ_Kp'] is not None]
  if valid:ax.step([r['hour_UTC'] for r in valid],[r['GFZ_Kp'] for r in valid],where='post',label='GFZ three-hour bucket (not substituted)')
  ax.set(xlabel='UTC hour',ylabel='Kp',title=d);ax.legend(fontsize=7)
 save(fig,'drivers')
 result=dict(status='PASS',dates=list(DATES),models=list(MODELS),summary=summary,windows=windows,growth=growth,native_checks=nativechecks,conditions=conditions,historical_Jan4_prefix=prefix,performance=performance,CPU_analysis_s=time.perf_counter()-tick,analysis_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
 dump(F/'analysis.json',result);print(json.dumps(dict(status='PASS',last_hour=[r for r in windows if r['hour']==6],growth=growth),indent=2))
if __name__=='__main__':main()
