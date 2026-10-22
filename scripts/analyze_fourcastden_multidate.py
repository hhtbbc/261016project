"""Five-window CPU analysis; official January predictions are never recomputed."""
import sys,json,csv,time
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_fourcastden_multistep import sha,dump
from fourcastden.multidate import DATES,names_for
from fourcastden.validation import NAMES,LENGTHS,SI_UNITS,SI_FACTORS,channel_metrics,feedback_check
from fourcastden.flow_validation import flow_feedback_check
F=ROOT/'experiments/fourcastden_multidate_v1';D=ROOT/'data/processed/fourcastden_multidate_v1';TAG='fourcastden_multidate_v1';ALL=('2023-01-04',)+DATES

def write(name,rows):
 with (ROOT/f'results/metrics/{TAG}_{name}.csv').open('x') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def save(fig,name):
 fig.suptitle('Official Direct / Flow, five predetermined 2023 initializations\nHINDCAST / TIE-GCM reference only / native pressure interfaces / no training',fontsize=9)
 fig.tight_layout(rect=[0,0,1,.91]);p=ROOT/f'results/figures/{TAG}_{name}.png';assert not p.exists();fig.savefig(p,dpi=150);plt.close(fig)
def load(day,model):
 if day==ALL[0]:
  tag='fourcastden_two_step_v1' if model=='Direct' else 'fourcastden_flow_two_step_v1';p=ROOT/f'data/processed/{tag}/result.npz';r=json.loads((ROOT/f'experiments/{tag}/runtime.json').read_text());expected=r['file_sha256']
 else:
  p=D/f'{day}_{model}.npz';expected=json.loads((F/f'{day}_{model}_runtime.json').read_text())['result_sha256']
 assert sha(p)==expected
 with np.load(p) as z:return {k:z[k].copy() for k in z.files}
def render_performance(records):
 styles={'Direct':'tab:blue','Flow':'tab:orange'}
 fig,axes=plt.subplots(1,3,figsize=(14,4))
 for model in styles:
  rr=[r for r in records if r['model']==model];offset=-.15 if model=='Direct' else .15;xx=np.arange(4)
  axes[0].bar(xx+offset,[r['author_loop_metrics_hooks_s'] for r in rr],width=.3,label=model)
  axes[1].plot(xx,[r['GPU_forward_ms'][0] for r in rr],'o-',label=f'{model} first of window');axes[1].plot(xx,[r['GPU_forward_ms'][1] for r in rr],'s--',label=f'{model} second')
  axes[2].bar(xx+offset,[r['read_preprocess_s']*1000 for r in rr],width=.3,label=model)
 for ax in axes:ax.set(xticks=np.arange(4),xticklabels=[d[5:] for d in DATES]);ax.legend(fontsize=6)
 axes[0].set(ylabel='Author loop including read/metrics/hooks (s)');axes[1].set(ylabel='GPU event forward time (ms)',title='Process cold: Direct first only; Flow shares kernels');axes[2].set(ylabel='Separate read/preprocess (ms)');save(fig,'performance')

def main():
 tick=time.perf_counter();rt=json.loads((F/'runtime.json').read_text());assert rt['status']=='PASS'
 lat=np.load(ROOT/'data/processed/static/lat.npy');lon=np.load(ROOT/'data/processed/static/lon.npy');lev=np.load(ROOT/'data/processed/static/lev.npy');ilev=np.load(ROOT/'data/processed/static/ilev.npy');w=np.cos(np.deg2rad(lat));w=w/w.mean();w2=np.broadcast_to(w[:,None],(36,72));masks={'global':np.ones((36,72),bool),'polar':np.broadcast_to((abs(lat)>=60)[:,None],(36,72)),'nonpolar':np.broadcast_to((abs(lat)<60)[:,None],(36,72))}
 layers=[];summaries=[];density=[];windows=[];drivers=[];checks=[];maps={};protocol=json.loads((F/'analysis_protocol.json').read_text())
 for day in ALL:
  q={m:load(day,m) for m in ['Direct','Flow']};a=q['Direct'];b=q['Flow']
  for key in ['real','means','stds','climatology']:np.testing.assert_array_equal(a[key],b[key])
  for k in range(2):np.testing.assert_array_equal(a[f'input{k}'][:,171:],b[f'input{k}'][:,171:]);np.testing.assert_array_equal(a[f'scalars{k}'],b[f'scalars{k}'])
  for model,x in q.items():
   ins=[(x['input0'],x['scalars0']),(x['input1'],x['scalars1'])];outputs=[x['increment0'],x['increment1']] if day==ALL[0] and model=='Flow' else [x['out0'],x['out1']]
   sw=np.vstack([np.zeros(4),x['scalars0'].reshape(4),x['scalars1'].reshape(4)])
   if model=='Flow':flow_feedback_check(ins,outputs,x['real'][0],x['pred'][0],sw)
   else:feedback_check(ins,outputs,x['real'][0],sw)
  mu=a['means'][:171].astype(float);sig=a['stds'][:171].astype(float);ref=a['real'][0,:,:171].astype(float)*sig+mu;clim=a['climatology'].astype(float)
  physical={m:x['pred'][0].astype(float)*sig+mu for m,x in q.items()};physical['Persistence']=np.repeat(ref[:1],3,axis=0)
  rawdir=ROOT/('data/raw/test_minimal_2023' if day==ALL[0] else 'data/raw/fourcastden_multidate_v1')
  for h in range(3):
   p=rawdir/f"{day.replace('-','_')}_{h:02d}0000.npz"
   with np.load(p) as z:
    drivers.append(dict(date=day,hour=h,UTC=f'{day}T{h:02d}:00:00Z',f107d=float(z['f107d'][0]),f107a=float(z['f107a'][0]),Kp=float(z['Kp'][0]),source_sha256=sha(p),condition='Prescribed author model input, not autonomous prediction'))
    if h:
     scalar=a[f'scalars{h-1}'].reshape(-1)
     np.testing.assert_allclose(scalar[:3],[(float(z['f107d'][0])-190)/110,(float(z['f107a'][0])-190)/110,(float(z['Kp'][0])-4.5)/4.5],rtol=1e-5,atol=1e-6)
  for h in (1,2):
   with np.load(rawdir/f"{day.replace('-','_')}_{h:02d}0000.npz") as z:zg=z['ZG'].astype(float)*.01
   heights=np.median(zg,axis=(1,2))/1000;near=np.flatnonzero((heights>=400)&(heights<=500));assert len(near)>0
   for model,p in physical.items():
    assert np.isfinite(p).all() and (p[:,142:]>0).all();rmse,acc,valid=channel_metrics(p[h],ref[h],clim,lat)
    # Independent alternative weighted-sum formula, including ACC, for every model/window/channel.
    err=p[h]-ref[h];alt=np.sqrt(np.sum(err**2*w2,axis=(1,2))/w2.sum());np.testing.assert_allclose(alt,rmse,rtol=1e-12,atol=1e-25)
    if model!='Persistence':
     np.testing.assert_allclose(rmse,q[model]['author_rmse'][0,h-1],rtol=2e-5,atol=1e-25)
     np.testing.assert_allclose(acc[valid],q[model]['author_acc'][0,h-1][valid],rtol=2e-5,atol=2e-6)
     checks.append(dict(date=day,hour=h,model=model,max_RMSE_relative=float(np.max(abs(rmse-q[model]['author_rmse'][0,h-1])/np.maximum(rmse,1e-30))),max_ACC_absolute=float(np.max(abs(acc[valid]-q[model]['author_acc'][0,h-1][valid])))))
    offset=0
    for name,length,unit,factor in zip(NAMES,LENGTHS,SI_UNITS,SI_FACTORS):
     idx=slice(offset,offset+length)
     summaries.append(dict(date=day,hour=h,model=model,variable=name,unit=unit,mean_layer_RMSE_SI=float(rmse[idx].mean()*factor),mean_layer_ACC=float(acc[idx][valid[idx]].mean()) if valid[idx].any() else '',weighted_bias_SI=float(np.mean(w2*err[idx])*factor),prediction_min_SI=float(p[h,idx].min()*factor),prediction_max_SI=float(p[h,idx].max()*factor),finite_fraction=float(np.isfinite(p[h,idx]).mean())))
     for k,c in enumerate(range(offset,offset+length)):layers.append(dict(date=day,hour=h,model=model,variable=name,layer_index=k,coordinate='lev' if length==28 else 'ilev',pressure_coordinate=float(lev[k] if length==28 else ilev[k]),SI_unit=unit,RMSE_SI=float(rmse[c]*factor),ACC=float(acc[c]) if valid[c] else '',ACC_valid=bool(valid[c])))
     offset+=length
    rho=p[h,142:]*1000;truth=ref[h,142:]*1000;rel=rho/truth-1;log=np.log(rho/truth);g=[]
    for region,mask in masks.items():
     weight=w2[mask];weight=weight/weight.mean()
     for k in range(29):
      e=rel[k][mask];lg=log[k][mask]
      rec=dict(date=day,hour=h,model=model,region=region,ilev_index=k,ilev=float(ilev[k]),reference_ZG_global_median_km=float(heights[k]),reference_ZG_min_km=float(zg[k].min()/1000),reference_ZG_max_km=float(zg[k].max()/1000),grid_points=int(mask.sum()),relative_P95=float(np.percentile(abs(e),95)),relative_max=float(abs(e).max()),weighted_relative_RMS=float(np.sqrt(np.mean(weight*e**2))),weighted_log_RMS=float(np.sqrt(np.mean(weight*lg**2))),weighted_log_bias=float(np.mean(weight*lg)),positive_fraction=float((rho[k][mask]>0).mean()))
      density.append(rec)
      if region=='global':g.append(rec)
    upper=protocol['upper_native_pressure_indices']
    windows.append(dict(date=day,hour=h,model=model,mean_DEN_layer_RMSE_kg_m3=float(rmse[142:].mean()*1000),lowermost_DEN_RMSE_kg_m3=float(rmse[142]*1000),upper_native_mean_relative_RMS=float(np.mean([g[k]['weighted_relative_RMS'] for k in upper])),upper_native_mean_log_RMS=float(np.mean([g[k]['weighted_log_RMS'] for k in upper])),near400_500_indices=','.join(map(str,near)),near400_500_reference_median_km=','.join(f'{heights[k]:.3f}' for k in near),near400_500_mean_relative_RMS=float(np.mean([g[k]['weighted_relative_RMS'] for k in near])),near400_500_mean_log_RMS=float(np.mean([g[k]['weighted_log_RMS'] for k in near])),near400_500_mean_layer_P95=float(np.mean([g[k]['relative_P95'] for k in near])),top_relative_P95=g[28]['relative_P95'],polar_relative_max=max(x['relative_max'] for x in density if x['date']==day and x['hour']==h and x['model']==model and x['region']=='polar')))
   k=int(np.argmin(abs(heights-450)))
   if h==2:maps[day]=dict(index=k,median_km=float(heights[k]),Direct=100*(physical['Direct'][h,142+k]/ref[h,142+k]-1),Flow=100*(physical['Flow'][h,142+k]/ref[h,142+k]-1))
  del q,a,b,physical,ref
 write('layers',layers);write('summary',summaries);write('density_layers',density);write('windows',windows);write('drivers',drivers)
 compare=[]
 for day in ALL:
  for h in (1,2):
   for n in NAMES:
    rr={m:next(x for x in summaries if x['date']==day and x['hour']==h and x['model']==m and x['variable']==n)['mean_layer_RMSE_SI'] for m in ['Direct','Flow','Persistence']}
    compare.append(dict(date=day,hour=h,variable=n,Direct=rr['Direct'],Flow=rr['Flow'],Persistence=rr['Persistence'],Flow_to_Direct=rr['Flow']/rr['Direct'],winner='Flow' if rr['Flow']<rr['Direct'] else 'Direct',Direct_skill_vs_persistence=1-rr['Direct']/rr['Persistence'],Flow_skill_vs_persistence=1-rr['Flow']/rr['Persistence']))
 write('paired',compare)
 aggregate=[]
 for h in (1,2):
  for n in NAMES:
   rr=[x for x in compare if x['hour']==h and x['variable']==n]
   aggregate.append(dict(hour=h,variable=n,independent_initializations=5,Flow_lower_RMSE_windows=sum(x['winner']=='Flow' for x in rr),Direct_lower_RMSE_windows=sum(x['winner']=='Direct' for x in rr),equal_window_mean_Direct_RMSE=float(np.mean([x['Direct'] for x in rr])),equal_window_mean_Flow_RMSE=float(np.mean([x['Flow'] for x in rr])),median_window_Flow_to_Direct=float(np.median([x['Flow_to_Direct'] for x in rr]))))
 write('aggregate',aggregate)
 x=np.arange(5);labels=[d[5:] for d in ALL];styles={'Direct':'tab:blue','Flow':'tab:orange'}
 fig,axes=plt.subplots(2,3,figsize=(13,8))
 for ax,n,unit in zip(axes.flat,NAMES,SI_UNITS):
  for model in styles:
   for h in (1,2):
    ys=[next(r for r in summaries if r['date']==day and r['hour']==h and r['model']==model and r['variable']==n)['mean_layer_RMSE_SI'] for day in ALL]
    ax.plot(x,ys,'o-' if h==1 else 's--',color=styles[model],label=f'{model} +{h}h')
  ax.set(xticks=x,xticklabels=labels,ylabel=f'Mean layer RMSE ({unit})',title=n,yscale='log');ax.legend(fontsize=6)
 save(fig,'variables')
 fig,axes=plt.subplots(2,2,figsize=(11,8))
 for i,model in enumerate(['Direct','Flow']):
  for j,h in enumerate((1,2)):
   a=np.array([[next(r for r in density if r['date']==day and r['hour']==h and r['model']==model and r['region']=='global' and r['ilev_index']==k)['weighted_relative_RMS'] for day in ALL] for k in range(29)])
   im=axes[j,i].imshow(np.log10(a*100),origin='lower',aspect='auto',extent=[-.5,4.5,ilev.min()-(ilev[1]-ilev[0])/2,ilev.max()+(ilev[1]-ilev[0])/2]);fig.colorbar(im,ax=axes[j,i],label='log10 relative RMS (%)');axes[j,i].set(xticks=x,xticklabels=labels,ylabel='Native ilev',title=f'{model} +{h}h')
 save(fig,'DEN_layers')
 fig,axes=plt.subplots(2,3,figsize=(13,8))
 for ax,n in zip(axes.flat,NAMES):
  for model in styles:
   ratios=[]
   for day in ALL:
    rr=[next(r for r in summaries if r['date']==day and r['hour']==h and r['model']==model and r['variable']==n)['mean_layer_RMSE_SI'] for h in (1,2)];ratios.append(rr[1]/rr[0])
   ax.plot(x,ratios,'o-',color=styles[model],label=model)
  ax.axhline(1,color='k',ls='--');ax.set(xticks=x,xticklabels=labels,ylabel='Hour2/hour1 mean layer RMSE',title=n);ax.legend(fontsize=7)
 save(fig,'growth')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for h,ax in zip((1,2),axes):
  for model in styles:
   ys=[next(r for r in windows if r['date']==day and r['hour']==h and r['model']==model)['near400_500_mean_relative_RMS']*100 for day in ALL];ax.plot(x,ys,'o-',color=styles[model],label=model)
  ax.set(xticks=x,xticklabels=labels,ylabel='Mean native-layer relative RMS (%)',title=f'+{h}h; reference median ZG in 400–500km');ax.legend()
 save(fig,'near400_500')
 fig,axes=plt.subplots(2,5,figsize=(16,6));limit=max(abs(maps[d][m]).max() for d in ALL for m in styles)
 for i,model in enumerate(styles):
  for j,day in enumerate(ALL):
   ax=axes[i,j];im=ax.pcolormesh(lon,lat,maps[day][model],shading='auto',cmap='RdBu_r',vmin=-limit,vmax=limit);ax.set(xlabel='Model lon (deg)',ylabel='Model lat (deg)',title=f"{day[5:]} {model}\nk={maps[day]['index']}, medZG={maps[day]['median_km']:.0f}km",xticks=[-180,0,180],yticks=[-60,0,60]);fig.colorbar(im,ax=ax,label='Density rel difference (%)')
 save(fig,'density_maps')
 fig,axes=plt.subplots(3,1,figsize=(12,9));xx=np.arange(15)
 axes[0].plot(xx,[r['Kp'] for r in drivers],'o-');axes[0].set(ylabel='Actual sample Kp (unitless)',title='Author-prescribed conditions, 00 / 01 / 02 UTC per date')
 axes[1].plot(xx,[r['f107d'] for r in drivers],'o-',label='F10.7');axes[1].plot(xx,[r['f107a'] for r in drivers],'s-',label='F10.7A');axes[1].set(ylabel='Solar flux (sfu)');axes[1].legend()
 for model in styles:axes[2].plot(x,[next(r for r in windows if r['date']==day and r['hour']==2 and r['model']==model)['upper_native_mean_relative_RMS']*100 for day in ALL],'o-',color=styles[model],label=model)
 for ax in axes[:2]:ax.set(xticks=[1,4,7,10,13],xticklabels=labels)
 axes[2].set(xticks=x,xticklabels=labels,ylabel='Upper native mean relative RMS (%)',title='+2h; descriptive, n=5; no causal or significance claim');axes[2].legend();save(fig,'drivers_errors')
 render_performance(rt['records'])
 out=dict(status='PASS',initial_windows=list(ALL),new_sequences=8,new_forwards=16,historical_January_replayed=False,independent_metric_checks=checks,aggregate=aggregate,windows=windows,comparison=compare,drivers=drivers,all_finite=True,DEN_positive_fraction=1.,analysis_protocol=protocol,CPU_analysis_s=time.perf_counter()-tick,map_layers={day:{k:v for k,v in m.items() if k not in styles} for day,m in maps.items()})
 dump(F/'analysis.json',out);print(json.dumps(dict(status='PASS',aggregate=aggregate,windows=windows),indent=2))
if __name__=='__main__':main()
