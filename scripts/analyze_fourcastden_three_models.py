"""Common raw-physical-target evaluation; never runs Direct/Flow or any model."""
import sys,json,csv,time
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_fourcastden_multistep import sha,dump
from analyze_fourcastden_multidate import load as old_load
from fourcastden.validation import NAMES,LENGTHS,UNITS,SI_UNITS,SI_FACTORS,channel_metrics,feedback_check
from fourcastden.logden import decode_physical
from fourcastden.multidate import DATES
F=ROOT/'experiments/fourcastden_logden_multidate_v1';D=ROOT/'data/processed/fourcastden_logden_multidate_v1';ALL=('2023-01-04',)+DATES;MODELS=('Direct','Flow','LogDEN');TAG='fourcastden_three_model_v1'
def load(day,model):
 if model!='LogDEN':return old_load(day,model)
 p=D/f'{day}.npz';assert sha(p)==json.loads((F/f'{day}_runtime.json').read_text())['result_sha256']
 with np.load(p) as z:return {k:z[k].copy() for k in z.files}
def write(name,rows):
 with (ROOT/f'results/metrics/{TAG}_{name}.csv').open('x') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def save(fig,name):
 fig.suptitle('Official Direct / Flow / log-DEN: five 2023 initializations, +1h / +2h\nHINDCAST / common raw physical TIE-GCM reference / native pressure levels / no training',fontsize=9)
 fig.tight_layout(rect=[0,0,1,.91]);p=ROOT/f'results/figures/{TAG}_{name}.png';assert not p.exists();fig.savefig(p,dpi=150);plt.close(fig)
def main():
 tick=time.perf_counter();rt=json.loads((F/'runtime.json').read_text());assert rt['status']=='PASS'
 lat=np.load(ROOT/'data/processed/static/lat.npy');lon=np.load(ROOT/'data/processed/static/lon.npy');ilev=np.load(ROOT/'data/processed/static/ilev.npy');lev=np.load(ROOT/'data/processed/static/lev.npy');weight=np.broadcast_to(np.cos(np.deg2rad(lat))[:,None],(36,72));weight=weight/weight.mean()
 masks=dict(global_=np.ones((36,72),bool),polar=np.broadcast_to((abs(lat)>=60)[:,None],(36,72)),nonpolar=np.broadcast_to((abs(lat)<60)[:,None],(36,72)))
 layers=[];summary=[];density=[];windows=[];native_rows=[];checks=[];roundtrip=[];maps={}
 for day in ALL:
  q={m:load(day,m) for m in MODELS};rawdir=ROOT/('data/raw/test_minimal_2023' if day==ALL[0] else 'data/raw/fourcastden_multidate_v1');raw=[];heights={}
  for h in range(3):
   with np.load(rawdir/f"{day.replace('-','_')}_{h:02d}0000.npz") as z:raw.append(np.concatenate([z[k] for k in NAMES],axis=0).astype(float));heights[h]=z['ZG'].astype(float)*.01
  reference=np.stack(raw);clim=q['Direct']['climatology'].astype(float);physical={m:decode_physical(x['pred'][0],x['means'][:171],x['stds'][:171],m=='LogDEN') for m,x in q.items()};physical['Persistence']=np.repeat(reference[:1],3,axis=0)
  for model,x in q.items():
   # Audit author-space metrics separately from common raw physical evaluation.
   if model=='LogDEN':
    feedback_check([(x['input0'],x['scalars0']),(x['input1'],x['scalars1'])],[x['out0'],x['out1']],x['real'][0],np.vstack([np.zeros(4),x['scalars0'].reshape(4),x['scalars1'].reshape(4)]))
   native_ref=decode_physical(x['real'][0,:,:171],x['means'][:171],x['stds'][:171],model=='LogDEN')
   roundtrip.append(dict(date=day,model=model,initial_DEN_max_relative=float(np.max(abs(native_ref[0,142:]/reference[0,142:]-1))),targets_DEN_max_relative=float(np.max(abs(native_ref[1:,142:]/reference[1:,142:]-1))),nonDEN_max_abs_native=float(np.max(abs(native_ref[:,:142]-reference[:,:142])))))
   for h in (1,2):
    if model!='LogDEN':
     nr,na,nv=channel_metrics(physical[model][h],native_ref[h],x['climatology'],lat);np.testing.assert_allclose(nr,x['author_rmse'][0,h-1],rtol=2e-5,atol=1e-25);np.testing.assert_allclose(na[nv],x['author_acc'][0,h-1][nv],rtol=2e-5,atol=2e-6)
     checks.append(dict(date=day,hour=h,model=model,metric='original_space',RMSE_max_relative=float(np.max(abs(nr-x['author_rmse'][0,h-1])/np.maximum(nr,1e-30))),ACC_max_absolute=float(np.max(abs(na[nv]-x['author_acc'][0,h-1][nv])))))
    else:
     nc=(x['climatology']-x['means'][:171])/x['stds'][:171];nr,na,nv=channel_metrics(x['pred'][0,h],x['real'][0,h,:171],nc,lat)
     np.testing.assert_allclose(nr,x['author_normalized_rmse'][h-1],rtol=2e-5,atol=1e-25);np.testing.assert_allclose(na[nv],x['author_acc'][0,h-1][nv],rtol=2e-5,atol=2e-6)
     dr=np.sqrt(np.mean(weight*(x['author_physical_den_pred'][h-1].astype(float)-x['author_physical_den_target'][h-1].astype(float))**2,axis=(-1,-2)));np.testing.assert_allclose(dr,x['author_rmse'][0,h-1,142:],rtol=2e-5,atol=1e-25)
     np.testing.assert_allclose(nr[:142]*x['stds'][:142,0,0],x['author_rmse'][0,h-1,:142],rtol=2e-5,atol=1e-25)
     checks.append(dict(date=day,hour=h,model=model,metric='normalized_RMSE_and_native_log_ACC',RMSE_max_relative=float(np.max(abs(nr-x['author_normalized_rmse'][h-1])/np.maximum(nr,1e-30))),ACC_max_absolute=float(np.max(abs(na[nv]-x['author_acc'][0,h-1][nv]))),DEN_physical_RMSE_max_relative=float(np.max(abs(dr-x['author_rmse'][0,h-1,142:])/np.maximum(dr,1e-30)))))
     offset=0
     for name,n,unit in zip(NAMES,LENGTHS,UNITS):
      for k,c in enumerate(range(offset,offset+n)):native_rows.append(dict(date=day,hour=h,variable=name,layer_index=k,author_returned_RMSE=float(x['author_rmse'][0,h-1,c]),author_RMSE_unit=unit,author_ACC=float(x['author_acc'][0,h-1,c]),ACC_space='log10(g/cm3), own log climatology' if name=='DEN' else 'own native physical climatology',normalized_RMSE=float(x['author_normalized_rmse'][h-1,c]),scaled_native_RMSE=float(x['author_native_space_rmse'][h-1,c]),scaled_native_unit='dex' if name=='DEN' else unit))
      offset+=n
  for h in (1,2):
   zg=heights[h];med=np.median(zg,axis=(1,2))/1000;near=np.flatnonzero((med>=400)&(med<=500));assert len(near)>0
   for model,p in physical.items():
    rmse,acc,valid=channel_metrics(p[h],reference[h],clim,lat);offset=0
    for name,n,unit,factor in zip(NAMES,LENGTHS,SI_UNITS,SI_FACTORS):
     idx=slice(offset,offset+n);err=p[h,idx]-reference[h,idx]
     summary.append(dict(date=day,hour=h,model=model,variable=name,SI_unit=unit,mean_layer_RMSE_SI=float(rmse[idx].mean()*factor),mean_layer_ACC=float(acc[idx][valid[idx]].mean()) if valid[idx].any() else '',weighted_bias_SI=float(np.mean(weight*err)*factor),prediction_min_SI=float(p[h,idx].min()*factor),prediction_max_SI=float(p[h,idx].max()*factor)))
     for k,c in enumerate(range(offset,offset+n)):layers.append(dict(date=day,hour=h,model=model,variable=name,layer_index=k,coordinate='lev' if n==28 else 'ilev',pressure_coordinate=float(lev[k] if n==28 else ilev[k]),SI_unit=unit,RMSE_SI=float(rmse[c]*factor),physical_ACC=float(acc[c]) if valid[c] else '',ACC_valid=bool(valid[c])))
     offset+=n
    rho=p[h,142:]*1000;truth=reference[h,142:]*1000;rel=rho/truth-1;log=np.log(rho/truth);g=[];polar=[]
    for region,mask in masks.items():
     w=weight[mask];w=w/w.mean()
     for k in range(29):
      e=rel[k][mask];lg=log[k][mask];r=dict(date=day,hour=h,model=model,region='global' if region=='global_' else region,ilev_index=k,ilev=float(ilev[k]),reference_ZG_global_median_km=float(med[k]),relative_P95=float(np.percentile(abs(e),95)),relative_max=float(abs(e).max()),weighted_relative_RMS=float(np.sqrt(np.mean(w*e**2))),weighted_log_RMS=float(np.sqrt(np.mean(w*lg**2))),weighted_log_bias=float(np.mean(w*lg)),positive_fraction=float((rho[k][mask]>0).mean()))
      density.append(r)
      if region=='global_':g.append(r)
      if region=='polar':polar.append(r)
    upper=list(range(20,29));windows.append(dict(date=day,hour=h,model=model,mean_DEN_layer_RMSE_kg_m3=float(rmse[142:].mean()*1000),lowermost_DEN_RMSE_kg_m3=float(rmse[142]*1000),lowermost_relative_RMS=g[0]['weighted_relative_RMS'],upper_native_mean_relative_RMS=float(np.mean([g[k]['weighted_relative_RMS'] for k in upper])),upper_native_mean_log_RMS=float(np.mean([g[k]['weighted_log_RMS'] for k in upper])),near400_500_indices=','.join(map(str,near)),near400_500_median_km=','.join(f'{med[k]:.3f}' for k in near),near400_500_mean_relative_RMS=float(np.mean([g[k]['weighted_relative_RMS'] for k in near])),near400_500_mean_log_RMS=float(np.mean([g[k]['weighted_log_RMS'] for k in near])),top_relative_P95=g[28]['relative_P95'],top_log_RMS=g[28]['weighted_log_RMS'],top_relative_RMS=g[28]['weighted_relative_RMS'],polar_relative_max=max(r['relative_max'] for r in polar),upper_mean_log_bias=float(np.mean([g[k]['weighted_log_bias'] for k in upper]))))
   if h==2:
    k=int(np.argmin(abs(med-450)));maps[day]=dict(index=k,median_km=float(med[k]),**{m:100*(physical[m][h,142+k]/reference[h,142+k]-1) for m in MODELS})
  del q,physical,reference
 write('layers',layers);write('summary',summary);write('density_layers',density);write('windows',windows);write('author_native_logden',native_rows)
 paired=[];aggregate=[]
 for day in ALL:
  for h in (1,2):
   for name in NAMES:
    values={m:next(r for r in summary if r['date']==day and r['hour']==h and r['model']==m and r['variable']==name)['mean_layer_RMSE_SI'] for m in MODELS}
    paired.append(dict(date=day,hour=h,variable=name,**values,best=min(values,key=values.get),LogDEN_to_Direct=values['LogDEN']/values['Direct'],LogDEN_to_Flow=values['LogDEN']/values['Flow']))
 for h in (1,2):
  for name in NAMES:
   rr=[r for r in paired if r['hour']==h and r['variable']==name];aggregate.append(dict(hour=h,variable=name,windows=5,**{m+'_best_windows':sum(r['best']==m for r in rr) for m in MODELS},**{m+'_equal_window_mean_RMSE':float(np.mean([r[m] for r in rr])) for m in MODELS}))
 write('paired',paired);write('aggregate',aggregate)
 performance=[]
 oldmulti=json.loads((ROOT/'experiments/fourcastden_multidate_v1/runtime.json').read_text())
 for day in ALL:
  for model in MODELS:
   if model=='LogDEN':r=next(x for x in rt['records'] if x['date']==day);fwd=r['GPU_forward_ms'];loop=r['author_loop_metrics_hooks_s'];read=r['read_preprocess_s'];loadtime=r['model_load_s'];inverse=r['inverse_pow10_two_target_fields_gpu_ms'];origin='this task, separate model process'
   elif day==ALL[0]:
    tag='fourcastden_two_step_v1' if model=='Direct' else 'fourcastden_flow_two_step_v1';r=json.loads((ROOT/f'experiments/{tag}/runtime.json').read_text());fwd=r['network_GPU_ms'];loop=r.get('author_inference_plus_metrics_and_hooks_s',r.get('author_loop_metrics_hooks_s'));read=r.get('data_read_preprocess_s',r.get('preprocess_read_s'));loadtime=r.get('model_load_s',r.get('model_load_including_CUDA_initialization_s'));inverse='';origin='historical independent January task'
   else:r=next(x for x in oldmulti['records'] if x['date']==day and x['model']==model);fwd=r['GPU_forward_ms'];loop=r['author_loop_metrics_hooks_s'];read=r['read_preprocess_s'];loadtime=r['model_load_s'];inverse='';origin='historical multidate task, Direct then Flow'
   performance.append(dict(date=day,model=model,model_load_s=loadtime,read_preprocess_s=read,author_loop_metrics_hooks_s=loop,first_forward_ms=fwd[0],second_forward_ms=fwd[1],inverse_batch_pow10_ms=inverse,origin=origin,strict_throughput_comparison=False))
 write('performance',performance)
 colors=dict(Direct='tab:blue',Flow='tab:orange',LogDEN='tab:green');x=np.arange(5);labels=[d[5:] for d in ALL]
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for h,ax in zip((1,2),axes):
  for m in MODELS:ax.plot(x,[next(r for r in windows if r['date']==day and r['hour']==h and r['model']==m)['near400_500_mean_relative_RMS']*100 for day in ALL],'o-',color=colors[m],label=m)
  ax.set(xticks=x,xticklabels=labels,ylabel='Mean layer relative RMS (%)',title=f'+{h}h; native layers with median refZG 400–500km');ax.legend()
 save(fig,'near400_500')
 fig,axes=plt.subplots(2,3,figsize=(14,8));extent=[-.5,4.5,ilev.min()-.25,ilev.max()+.25]
 for i,m in enumerate(MODELS):
  for j,h in enumerate((1,2)):
   matrix=np.array([[next(r for r in density if r['date']==day and r['hour']==h and r['model']==m and r['region']=='global' and r['ilev_index']==k)['weighted_relative_RMS'] for day in ALL] for k in range(29)]);im=axes[j,i].imshow(np.log10(matrix*100),origin='lower',aspect='auto',extent=extent);fig.colorbar(im,ax=axes[j,i],label='log10 relative RMS (%)');axes[j,i].set(xticks=x,xticklabels=labels,ylabel='Native ilev',title=f'{m} +{h}h')
 save(fig,'DEN_layers')
 fig,axes=plt.subplots(2,3,figsize=(14,8))
 for ax,name,unit in zip(axes.flat,NAMES,SI_UNITS):
  for m in MODELS:
   for h in (1,2):ax.plot(x,[next(r for r in summary if r['date']==day and r['hour']==h and r['model']==m and r['variable']==name)['mean_layer_RMSE_SI'] for day in ALL],'o-' if h==1 else 's--',color=colors[m],label=f'{m} +{h}h')
  ax.set(xticks=x,xticklabels=labels,ylabel=f'Mean layer RMSE ({unit})',title=name,yscale='log');ax.legend(fontsize=6)
 save(fig,'variables')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for ax,key,title in zip(axes,['mean_DEN_layer_RMSE_kg_m3','upper_native_mean_relative_RMS'],['DEN mean absolute layer RMSE','Upper native-layer relative RMS']):
  for m in MODELS:
   ys=[next(r for r in windows if r['date']==day and r['hour']==2 and r['model']==m)[key]/next(r for r in windows if r['date']==day and r['hour']==1 and r['model']==m)[key] for day in ALL];ax.plot(x,ys,'o-',color=colors[m],label=m)
  ax.axhline(1,color='k',ls='--');ax.set(xticks=x,xticklabels=labels,ylabel='Hour2/hour1',title=title);ax.legend()
 save(fig,'growth')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for ax,key,title in zip(axes,['top_relative_P95','polar_relative_max'],['Top native layer P95','Polar worst native point']):
  for m in MODELS:ax.plot(x,[next(r for r in windows if r['date']==day and r['hour']==2 and r['model']==m)[key]*100 for day in ALL],'o-',color=colors[m],label=m)
  ax.set(xticks=x,xticklabels=labels,ylabel='Absolute relative difference (%)',title=title+' (+2h)');ax.legend()
 save(fig,'top_polar')
 fig,axes=plt.subplots(1,3,figsize=(14,4))
 for m in MODELS:
  rr=[r for r in performance if r['model']==m];axes[0].plot(x,[r['first_forward_ms'] for r in rr],'o-',color=colors[m],label=m);axes[1].plot(x,[r['second_forward_ms'] for r in rr],'o-',color=colors[m],label=m)
 for ax,title in zip(axes[:2],['First forward (mixed cold/cache histories)','Second forward (not controlled throughput)']):ax.set(xticks=x,xticklabels=labels,ylabel='GPU event ms',title=title);ax.legend()
 axes[2].bar(x,[r['inverse_pow10_two_target_fields_gpu_ms'] for r in rt['records']],color=colors['LogDEN']);axes[2].set(xticks=x,xticklabels=labels,ylabel='GPU event ms',title='log-DEN batch output pow10 only');save(fig,'performance')
 out=dict(status='PASS',labels=['HINDCAST','TIEGCM_REFERENCE_ONLY','NO_TRAINING'],reference='same raw original NPZ physical fields for all three models; ordinary physical climatology',old_metrics_not_overwritten=True,models=list(MODELS),dates=list(ALL),Direct_Flow_rerun=False,native_checks=checks,normalization_roundtrip=roundtrip,summary=summary,windows=windows,paired=paired,aggregate=aggregate,performance=performance,CPU_analysis_s=time.perf_counter()-tick)
 dump(F/'analysis.json',out);print(json.dumps(dict(status='PASS',aggregate=aggregate,windows=[w for w in windows if w['model']=='LogDEN']),indent=2))
if __name__=='__main__':main()
