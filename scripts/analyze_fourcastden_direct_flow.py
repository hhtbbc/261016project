"""CPU-only paired evaluation of saved official Direct and Flow results."""
import sys,json,csv,time
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from fourcastden.validation import NAMES,LENGTHS,UNITS,SI_UNITS,SI_FACTORS,channel_metrics
from fourcastden.flow_validation import flow_feedback_check
from run_fourcastden_multistep import sha,dump
F=ROOT/'experiments/fourcastden_flow_two_step_v1';TAG='fourcastden_direct_flow_v1'
def write(name,rows):
 with (ROOT/f'results/metrics/{TAG}_{name}.csv').open('x') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def save(fig,name):
 fig.suptitle('Official Direct / Flow: single Jan4 00 UTC initialization, +1h / +2h\nHINDCAST / TIE-GCM reference only / no training / native pressure levels',fontsize=9)
 fig.tight_layout(rect=[0,0,1,.90]);p=ROOT/f'results/figures/{TAG}_{name}.png';assert not p.exists();fig.savefig(p,dpi=150);plt.close(fig)
def main():
 tick=time.perf_counter();rt=json.loads((F/'runtime.json').read_text());assert rt['status'].startswith('Flow_two_step_passed')
 qs={}
 for model,tag in [('Direct','fourcastden_two_step_v1'),('Flow','fourcastden_flow_two_step_v1')]:
  p=ROOT/f'data/processed/{tag}/result.npz';r=json.loads((ROOT/f'experiments/{tag}/runtime.json').read_text());assert sha(p)==r['file_sha256']
  with np.load(p) as z:qs[model]={k:z[k].copy() for k in z.files}
 q=qs['Flow'];d=qs['Direct'];real=q['real'][0]
 for k in ['real','means','stds','climatology']:np.testing.assert_array_equal(q[k],d[k])
 for k in range(2):
  np.testing.assert_array_equal(q[f'input{k}'][:,171:],d[f'input{k}'][:,171:]);np.testing.assert_array_equal(q[f'scalars{k}'],d[f'scalars{k}'])
 feedback=flow_feedback_check([(q['input0'],q['scalars0']),(q['input1'],q['scalars1'])],[q['increment0'],q['increment1']],real,q['pred'][0],np.vstack([np.zeros(4),q['scalars0'].reshape(4),q['scalars1'].reshape(4)]))
 mu=q['means'][:171].astype(float);sig=q['stds'][:171].astype(float);ref=real[:,:171].astype(float)*sig+mu
 physical={k:v['pred'][0].astype(float)*sig+mu for k,v in qs.items()};physical['Persistence']=np.repeat(ref[:1],3,axis=0)
 lat=np.load(ROOT/'data/processed/static/lat.npy');lon=np.load(ROOT/'data/processed/static/lon.npy');lev=np.load(ROOT/'data/processed/static/lev.npy');ilev=np.load(ROOT/'data/processed/static/ilev.npy');clim=q['climatology'].astype(float)
 w=np.cos(np.deg2rad(lat));w=w/w.mean();w=w[:,None];layers=[];summary=[];denrows=[];paired=[];errors={};checks={};maplayers=[]
 for h in (1,2):
  errors[h]={}
  with np.load(ROOT/f'data/raw/test_minimal_2023/2023_01_04_0{h}0000.npz') as n:zg=n['ZG'].astype(float)*.01
  for model,p in physical.items():
   assert np.isfinite(p).all() and (p[:,142:]>0).all()
   rmse,acc,valid=channel_metrics(p[h],ref[h],clim,lat);errors[h][model]=rmse
   if model!='Persistence':
    np.testing.assert_allclose(rmse,qs[model]['author_rmse'][0,h-1],rtol=2e-5,atol=1e-25)
    np.testing.assert_allclose(acc[valid],qs[model]['author_acc'][0,h-1][valid],rtol=2e-5,atol=2e-6)
    checks[f'{model}_{h}']=dict(RMSE_max_relative=float(np.max(abs(rmse-qs[model]['author_rmse'][0,h-1])/np.maximum(rmse,1e-30))),ACC_max_absolute=float(np.max(abs(acc[valid]-qs[model]['author_acc'][0,h-1][valid]))))
   offset=0
   for name,length,unit,si,factor in zip(NAMES,LENGTHS,UNITS,SI_UNITS,SI_FACTORS):
    idx=slice(offset,offset+length);err=p[h,idx]-ref[h,idx]
    summary.append(dict(hour=h,model=model,variable=name,unit=si,mean_layer_RMSE_SI=float(rmse[idx].mean()*factor),mean_layer_ACC=float(acc[idx][valid[idx]].mean()) if valid[idx].any() else '',valid_ACC_layers=int(valid[idx].sum()),layers=length,weighted_bias_SI=float(np.mean(w*err)*factor),prediction_min_SI=float(p[h,idx].min()*factor),prediction_max_SI=float(p[h,idx].max()*factor),finite_fraction=float(np.isfinite(p[h,idx]).mean())))
    for k,c in enumerate(range(offset,offset+length)):
     layers.append(dict(hour=h,model=model,variable=name,layer_index=k,coordinate='lev' if length==28 else 'ilev',pressure_coordinate=float(lev[k] if length==28 else ilev[k]),native_unit=unit,SI_unit=si,RMSE_native=float(rmse[c]),RMSE_SI=float(rmse[c]*factor),ACC=float(acc[c]) if valid[c] else '',ACC_valid=bool(valid[c]),weighted_bias_SI=float(np.mean(w*err[k])*factor)))
    offset+=length
   rho=p[h,142:]*1000;truth=ref[h,142:]*1000;rel=rho/truth-1;log=np.log(rho/truth)
   for k in range(29):
    denrows.append(dict(hour=h,model=model,ilev_index=k,ilev=float(ilev[k]),reference_ZG_median_km=float(np.median(zg[k])/1000),reference_ZG_min_km=float(zg[k].min()/1000),reference_ZG_max_km=float(zg[k].max()/1000),positive_fraction=float((rho[k]>0).mean()),rho_min_kg_m3=float(rho[k].min()),rho_max_kg_m3=float(rho[k].max()),relative_P95=float(np.percentile(abs(rel[k]),95)),weighted_relative_RMS=float(np.sqrt(np.mean(w*rel[k]**2))),weighted_log_RMS=float(np.sqrt(np.mean(w*log[k]**2))),weighted_log_bias=float(np.mean(w*log[k]))))
  offset=0
  for name,length in zip(NAMES,LENGTHS):
   idx=slice(offset,offset+length);a=errors[h]['Direct'][idx];b=errors[h]['Flow'][idx];baseline=errors[h]['Persistence'][idx]
   paired.append(dict(hour=h,variable=name,layers=length,Flow_lower_RMSE_layers=int((b<a).sum()),Direct_lower_RMSE_layers=int((a<b).sum()),equal_layers=int((a==b).sum()),Flow_to_Direct_mean_layer_RMSE=float(b.mean()/a.mean()),Flow_beats_persistence_layers=int((b<baseline).sum()),Direct_beats_persistence_layers=int((a<baseline).sum())))
   offset+=length
  k=int(np.argmin(abs(np.median(zg,axis=(1,2))-450000)));med=float(np.median(zg[k])/1000);maplayers.append(dict(hour=h,ilev_index=k,ilev=float(ilev[k]),reference_median_ZG_km=med,reference_min_ZG_km=float(zg[k].min()/1000),reference_max_ZG_km=float(zg[k].max()/1000)))
  arrays=[ref[h,142+k]*1000,physical['Direct'][h,142+k]*1000,physical['Flow'][h,142+k]*1000]
  lo=min(np.log10(a).min() for a in arrays);hi=max(np.log10(a).max() for a in arrays);fig,axes=plt.subplots(1,3,figsize=(13,4))
  for ax,a,name in zip(axes,arrays,['TIE-GCM reference','Direct (historical)','Flow (new)']):
   im=ax.pcolormesh(lon,lat,np.log10(a),shading='auto',vmin=lo,vmax=hi);fig.colorbar(im,ax=ax,label='log10 density (kg/m³)');ax.set_title(name);ax.set(xlabel='Model longitude (deg)',ylabel='Model latitude (deg)')
  fig.text(.5,.01,f'+{h}h; ilev index={k}; reference median ZG={med:.1f} km; variable-height pressure surface',ha='center',fontsize=8);save(fig,f'density_hour{h}')
  fig,axes=plt.subplots(1,2,figsize=(11,4));vals=[100*(a/arrays[0]-1) for a in arrays[1:]];limit=max(abs(v).max() for v in vals)
  for ax,a,name in zip(axes,vals,['Direct','Flow']):
   im=ax.pcolormesh(lon,lat,a,shading='auto',cmap='RdBu_r',vmin=-limit,vmax=limit);fig.colorbar(im,ax=ax,label='Prediction / reference - 1 (%)');ax.set_title(name);ax.set(xlabel='Model longitude (deg)',ylabel='Model latitude (deg)')
  fig.text(.5,.01,f'+{h}h; same ilev={k}, median reference ZG={med:.1f} km; no fixed-altitude claim',ha='center',fontsize=8);save(fig,f'relative_hour{h}')
 write('layers',layers);write('summary',summary);write('density_layers',denrows);write('paired',paired)
 fig,axes=plt.subplots(2,2,figsize=(11,8))
 for h in (1,2):
  for model in ['Direct','Flow','Persistence']:
   rows=[r for r in denrows if r['hour']==h and r['model']==model];axes[0,h-1].semilogx([r['weighted_relative_RMS']*100 for r in rows],ilev,label=model);axes[1,h-1].semilogx([r['weighted_log_RMS'] for r in rows],ilev,label=model)
  axes[0,h-1].set(xlabel='Weighted density relative RMS (%)',ylabel='Native ilev log-pressure coordinate',title=f'+{h}h');axes[1,h-1].set(xlabel='Weighted log density RMS',ylabel='Native ilev log-pressure coordinate');axes[0,h-1].legend();axes[1,h-1].legend()
 save(fig,'DEN_layers')
 fig,axes=plt.subplots(2,3,figsize=(13,8))
 for ax,name,unit in zip(axes.flat,NAMES,SI_UNITS):
  for model in ['Direct','Flow','Persistence']:
   rows=[r for r in summary if r['variable']==name and r['model']==model];ax.plot([1,2],[r['mean_layer_RMSE_SI'] for r in rows],'o-',label=model)
  ax.set(xlabel='Forecast horizon (h)',ylabel=f'Mean layer RMSE ({unit})',title=name,yscale='log',xticks=[1,2]);ax.legend(fontsize=7)
 save(fig,'variable_RMSE')
 fig,ax=plt.subplots(figsize=(10,4));x=np.arange(6)
 for j,model in enumerate(['Direct','Flow']):
  ratios=[]
  for name in NAMES:
   a=[r['mean_layer_RMSE_SI'] for r in summary if r['model']==model and r['variable']==name];ratios.append(a[1]/a[0])
  ax.bar(x+(j-.5)*.35,ratios,width=.35,label=model)
 ax.axhline(1,color='k',ls='--');ax.set(xticks=x,xticklabels=NAMES,ylabel='Hour 2 / hour 1 mean layer RMSE',title='Error growth, single initialization');ax.legend();save(fig,'error_growth')
 dr=json.loads((ROOT/'experiments/fourcastden_two_step_v1/runtime.json').read_text());fig,ax=plt.subplots(figsize=(8,4))
 for j,(name,r) in enumerate([('Direct historical',dr),('Flow new',rt)]):ax.bar(np.array([0,1])+(j-.5)*.3,r['network_GPU_ms'],width=.3,label=name)
 ax.set(xticks=[0,1],xticklabels=['First forward (cold)','Second forward'],ylabel='GPU event time (ms)',title='Single runs on different dates; not a throughput benchmark');ax.legend();save(fig,'GPU_timing')
 analysis=dict(status='paired_independent_validation_PASS',feedback=feedback,labels=['HINDCAST','TIEGCM_REFERENCE_ONLY','NO_TRAINING'],Direct_network_runs_this_task=0,Flow_formal_runs=1,Flow_real_forwards=2,independent_metric_checks=checks,summary=summary,paired=paired,map_pressure_layers=maplayers,all_predictions_finite=True,Flow_DEN_positive_fraction=rt['DEN_positive_fraction'],ACC_definition='cos(latitude)-weighted climatology anomaly correlation; zero denominator -> N/A',mask='all native valid 36x72 grid points per channel; no clipping or calibration',DEN_height_warning='Reference ZG describes each native interface, not a fixed geometric-height target; output Z is geopotential height',timing_warning='Historical Direct timing only; single cold/warm forwards cannot establish robust speedup',CPU_analysis_s=time.perf_counter()-tick)
 dump(F/'analysis.json',analysis)
 print(json.dumps(dict(status=analysis['status'],paired=paired,independent_metric_checks=checks),indent=2))
if __name__=='__main__':main()
