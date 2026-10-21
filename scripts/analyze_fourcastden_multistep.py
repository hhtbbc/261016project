"""CPU-only physical-unit/pressure-level evaluation of saved official predictions."""
import sys,json,csv,time,hashlib
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from fourcastden.validation import NAMES,LENGTHS,UNITS,SI_UNITS,SI_FACTORS,channel_metrics,feedback_check
F=ROOT/'experiments/fourcastden_two_step_v1';D=ROOT/'data/processed/fourcastden_two_step_v1';TAG='fourcastden_two_step_v1'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for x in iter(lambda:f.read(4*1024*1024),b''):h.update(x)
 return h.hexdigest()
def write(name,rows):
 with (ROOT/f'results/metrics/{TAG}_{name}.csv').open('x') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def save(fig,name):
 fig.suptitle('FourCastDEN official Direct / HINDCAST / TIE-GCM reference only\n2023-01-04 00 UTC initialization; prescribed target-hour external conditions',fontsize=8);fig.tight_layout(rect=[0,0,1,.90]);p=ROOT/f'results/figures/{TAG}_{name}.png';assert not p.exists();fig.savefig(p,dpi=150);plt.close(fig)
def main():
 tick=time.perf_counter();runtime=json.loads((F/'runtime.json').read_text());assert runtime['status'].startswith('two_step_execution_passed')
 with np.load(D/'result.npz') as z:q={k:z[k].copy() for k in z.files}
 assert sha(D/'result.npz')==runtime['file_sha256'];real=q['real'][0];pn=q['pred'][0];mu=q['means'][:171].astype(float);sig=q['stds'][:171].astype(float);clim=q['climatology'].astype(float);pred=pn.astype(float)*sig+mu;ref=real[:,:171].astype(float)*sig+mu;pers=ref[0].copy();lat=np.load(ROOT/'data/processed/static/lat.npy');lon=np.load(ROOT/'data/processed/static/lon.npy');lev=np.load(ROOT/'data/processed/static/lev.npy');ilev=np.load(ROOT/'data/processed/static/ilev.npy');w=np.cos(np.deg2rad(lat));w=w/w.mean();w=w[:,None]
 assert np.isfinite(pred).all() and (pred[:,142:]>0).all()
 feedback=feedback_check([(q['input0'],q['scalars0']),(q['input1'],q['scalars1'])],[q['out0'],q['out1']],real,np.vstack([np.zeros(4),q['scalars0'].reshape(4),q['scalars1'].reshape(4)]))
 rows=[];summaries=[];density=[];rmse_comparison=[];reconstruction={};denerrors={};out=dict(status='independent_checks_passed',labels=['HINDCAST','TIEGCM_REFERENCE_ONLY'],feedback=feedback,variables=[],historical_single_hour_not_new=True,evaluation='Author cos(latitude) weighted per-channel RMSE and climatology ACC; all native valid grid points; aggregate is mean of layer RMSEs, not a fixed-altitude/global pooled score',persistence='Frozen t0 physical 171-channel state for BOTH targets; no 01h truth update',ACC_NA='zero/nonfinite anomaly denominator -> N/A',new_GPU_forwards=0)
 for h in [1,2]:
  ar,ac,av=channel_metrics(pred[h],ref[h],clim,lat);pr,pc,pv=channel_metrics(pers,ref[h],clim,lat)
  np.testing.assert_allclose(ar,q['author_rmse'][0,h-1],rtol=2e-5,atol=1e-25)
  np.testing.assert_allclose(ac[av],q['author_acc'][0,h-1][av],rtol=2e-5,atol=2e-6)
  rmse_comparison.append(float(np.max(abs(ar-q['author_rmse'][0,h-1])/np.maximum(abs(ar),1e-30))))
  with np.load(ROOT/f'data/raw/test_minimal_2023/2023_01_04_0{h}0000.npz') as n:
   raw=np.concatenate([n[k] for k in NAMES],axis=0).astype(float);zg=n['ZG'].astype(float)*.01
  reconstruction[str(h)]={'max_abs_by_variable_native':{}};offset=0
  for name,length,unit,si_unit,factor in zip(NAMES,LENGTHS,UNITS,SI_UNITS,SI_FACTORS):
   idx=slice(offset,offset+length);summary=dict(hour=h,variable=name,native_unit=unit,SI_unit=si_unit,AI_mean_layer_RMSE_native=float(ar[idx].mean()),persistence_mean_layer_RMSE_native=float(pr[idx].mean()),AI_mean_layer_RMSE_SI=float(ar[idx].mean()*factor),persistence_mean_layer_RMSE_SI=float(pr[idx].mean()*factor),AI_mean_layer_ACC=float(ac[idx][av[idx]].mean()) if av[idx].any() else None,persistence_mean_layer_ACC=float(pc[idx][pv[idx]].mean()) if pv[idx].any() else None,valid_AI_ACC_layers=int(av[idx].sum()),AI_better_RMSE_layers=int((ar[idx]<pr[idx]).sum()),layers=length,skill_ratio_of_mean_layer_RMSE=float(1-ar[idx].mean()/pr[idx].mean()) if pr[idx].mean()>0 else None);summaries.append(summary)
   reconstruction[str(h)]['max_abs_by_variable_native'][name]=float(np.max(abs(ref[h,idx]-raw[idx])))
   for k,c in enumerate(range(offset,offset+length)):
    rows.append(dict(hour=h,variable=name,layer_index=k,vertical_coordinate='lev' if length==28 else 'ilev',log_pressure_coordinate=float(lev[k] if length==28 else ilev[k]),native_unit=unit,SI_unit=si_unit,AI_weighted_RMSE_native=ar[c],AI_weighted_RMSE_SI=ar[c]*factor,persistence_weighted_RMSE_native=pr[c],persistence_weighted_RMSE_SI=pr[c]*factor,author_RMSE_native=float(q['author_rmse'][0,h-1,c]),AI_ACC=ac[c] if av[c] else '',persistence_ACC=pc[c] if pv[c] else '',ACC_valid=bool(av[c]),RMSE_skill=1-ar[c]/pr[c] if pr[c]>0 else ''))
   offset+=length
  denp=pred[h,142:]*1000;denr=ref[h,142:]*1000;denb=pers[142:]*1000;assert (denp>0).all() and (denr>0).all();denerrors[h]={}
  for label,value in [('AI',denp),('persistence',denb)]:
   rel=value/denr-1;log=np.log(value/denr);denerrors[h][label]=rel
   for k in range(29):density.append(dict(hour=h,model=label,ilev_index=k,ilev=float(ilev[k]),reference_ZG_global_median_km=float(np.median(zg[k])/1000),reference_ZG_min_km=float(zg[k].min()/1000),reference_ZG_max_km=float(zg[k].max()/1000),rho_reference_min_kg_m3=float(denr[k].min()),rho_prediction_min_kg_m3=float(value[k].min()),weighted_relative_RMS=float(np.sqrt(np.mean(w*rel[k]**2))),absolute_relative_P95=float(np.percentile(abs(rel[k]),95)),weighted_log_RMS=float(np.sqrt(np.mean(w*log[k]**2))),log_bias=float(np.mean(w*log[k]))))
  # Select pressure interface closest to 450km reference global median, not a fixed-height interpolation.
  k=int(np.argmin(abs(np.median(zg,axis=(1,2))-450000)));fig,axes=plt.subplots(1,3,figsize=(13,4));logs=[np.log10(denr[k]),np.log10(denp[k])];low=min(x.min() for x in logs);high=max(x.max() for x in logs)
  for ax,a,title in zip(axes[:2],logs,['TIE-GCM reference','Direct prediction']):
   im=ax.pcolormesh(lon,lat,a,shading='auto',vmin=low,vmax=high);fig.colorbar(im,ax=ax,label='log10 density (kg/m³)');ax.set_title(title)
  err=100*(denp[k]/denr[k]-1);m=float(abs(err).max());im=axes[2].pcolormesh(lon,lat,err,shading='auto',cmap='RdBu_r',vmin=-m,vmax=m);fig.colorbar(im,ax=axes[2],label='Relative difference (%)');axes[2].set_title('Prediction / reference - 1')
  for ax in axes:ax.set(xlabel='Model geographic longitude (deg)',ylabel='Model geographic latitude (deg)')
  axes[0].text(.5,-.30,f'+{h}h; ilev={ilev[k]:g}; reference ZG median={np.median(zg[k])/1000:.1f} km; variable-height pressure surface',transform=axes[0].transAxes,fontsize=8);save(fig,f'density_map_hour{h}')
 write('layers',rows);write('summary',summaries);write('density_layers',density)
 out.update(variables=summaries,raw_reference_normalization_roundoff=reconstruction,independent_RMSE_max_relative_difference=max(rmse_comparison),author_metric_matches_numpy=True,den_positive_fraction=1.,density_layers=density)
 fig,axes=plt.subplots(2,3,figsize=(12,7))
 for ax,name,unit in zip(axes.flat,NAMES,SI_UNITS):
  ss=[x for x in summaries if x['variable']==name];ax.plot([1,2],[x['AI_mean_layer_RMSE_SI'] for x in ss],'-o',label='Direct');ax.plot([1,2],[x['persistence_mean_layer_RMSE_SI'] for x in ss],'-o',label='Frozen t0 persistence');ax.set(title=name,xlabel='Lead time (h)',ylabel='Mean layer RMSE ('+unit+')',xticks=[1,2]);ax.grid();ax.legend(fontsize=7)
 save(fig,'variables_vs_persistence')
 fig,axes=plt.subplots(1,2,figsize=(10,5))
 for h in [1,2]:
  for label in ['AI','persistence']:
   ss=[x for x in density if x['hour']==h and x['model']==label];axes[0].semilogx([x['weighted_relative_RMS'] for x in ss],ilev,label=f'{label} +{h}h');axes[1].semilogx([x['weighted_log_RMS'] for x in ss],ilev,label=f'{label} +{h}h')
 for ax,xlabel in zip(axes,['Relative RMS','ln-density RMS']):ax.set(xlabel=xlabel,ylabel='Native interface log-pressure coordinate');ax.grid();ax.legend(fontsize=7)
 save(fig,'density_vertical_errors')
 fig,ax=plt.subplots(figsize=(8,4));ax.bar(['network +1h','network +2h'],json.loads((F/'runtime.json').read_text())['network_GPU_ms']);ax.set(ylabel='CUDA-event elapsed time (ms)',title='Two first-use forwards; not warmed throughput benchmark');save(fig,'network_timing')
 for p,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==h,p
 out['protected_unchanged']=True;out['analysis_wall_s']=time.perf_counter()-tick
 with (F/'analysis.json').open('x') as f:json.dump(out,f,indent=2,allow_nan=False)
 print(json.dumps({k:v for k,v in out.items() if k!='density_layers'},indent=2))
if __name__=='__main__':main()
