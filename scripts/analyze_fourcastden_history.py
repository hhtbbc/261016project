"""Four official models at a common 01 UTC initialization; no model execution."""
import sys,json,csv,time
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_fourcastden_multistep import sha,dump
from fourcastden.validation import NAMES,LENGTHS,SI_UNITS,SI_FACTORS,channel_metrics
from fourcastden.logden import decode_physical
from run_fourcastden_history_comparison import F,D,MODELS
TAG='fourcastden_history_v1'
def write(name,rows):
 with (ROOT/f'results/metrics/{TAG}_{name}.csv').open('x') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def save(fig,name):
 fig.suptitle('Official four-model comparison: Jan 4 2023, 01 UTC -> 02 / 03 UTC\nHINDCAST / TIE-GCM reference / native pressure levels / History has extra 00 UTC state',fontsize=9);fig.tight_layout(rect=[0,0,1,.91]);p=ROOT/f'results/figures/{TAG}_{name}.png';assert not p.exists();fig.savefig(p,dpi=150);plt.close(fig)
def main():
 tick=time.perf_counter();runtime=json.loads((F/'runtime.json').read_text());assert runtime['status']=='PASS';q={}
 for m in MODELS:
  assert sha(D/f'{m}.npz')==next(r['result_sha256'] for r in runtime['records'] if r['model']==m)
  with np.load(D/f'{m}.npz') as x:q[m]={k:x[k].copy() for k in x.files}
 raw=[];zg=[];drivers=[]
 for h in range(4):
  with np.load(F/'data_view'/f'2023_01_04_{h:02d}0000.npz') as z:
   raw.append(np.concatenate([z[k] for k in NAMES],axis=0).astype(float));zg.append(z['ZG'].astype(float)*.01);drivers.append(dict(hour_UTC=h,**{k:float(z[k][0]) for k in ['f107d','f107a','Kp']}))
 reference=np.stack(raw[1:]);clim=q['Direct']['climatology'].astype(float);lat=np.load(ROOT/'data/processed/static/lat.npy');ilev=np.load(ROOT/'data/processed/static/ilev.npy');lev=np.load(ROOT/'data/processed/static/lev.npy');w=np.broadcast_to(np.cos(np.deg2rad(lat))[:,None],(36,72));w=w/w.mean()
 physical={m:decode_physical(x['pred'][0],x['means'][:171],x['stds'][:171],m=='LogDEN') for m,x in q.items()};physical['Persistence']=np.repeat(reference[:1],3,axis=0)
 checks=[];native=[];conditions=[];roundtrip=[]
 for m,x in q.items():
  nr=decode_physical(x['real'][0,:,:171],x['means'][:171],x['stds'][:171],m=='LogDEN');roundtrip.append(dict(model=m,initial_DEN_max_relative=float(np.max(abs(nr[0,142:]/reference[0,142:]-1)))))
  for h in (1,2):
   if m=='LogDEN':
    nc=(x['climatology']-x['means'][:171])/x['stds'][:171];r,a,v=channel_metrics(x['pred'][0,h],x['real'][0,h,:171],nc,lat);np.testing.assert_allclose(r,x['author_normalized_rmse'][h-1],rtol=2e-5,atol=1e-25);np.testing.assert_allclose(a[v],x['author_acc'][0,h-1][v],rtol=2e-5,atol=2e-6)
    den=np.sqrt(np.mean(w*(x['author_physical_den_pred'][h-1].astype(float)-x['author_physical_den_target'][h-1].astype(float))**2,axis=(1,2)));np.testing.assert_allclose(den,x['author_rmse'][0,h-1,142:],rtol=2e-5,atol=1e-25)
    native.append(dict(hour=h,model=m,normalized_RMSE_max_relative=float(np.max(abs(r-x['author_normalized_rmse'][h-1])/r)),ACC_max_absolute=float(np.max(abs(a[v]-x['author_acc'][0,h-1][v]))),DEN_physical_RMSE_max_relative=float(np.max(abs(den-x['author_rmse'][0,h-1,142:])/den))))
   else:
    r,a,v=channel_metrics(physical[m][h],nr[h],x['climatology'],lat);np.testing.assert_allclose(r,x['author_rmse'][0,h-1],rtol=2e-5,atol=1e-25);np.testing.assert_allclose(a[v],x['author_acc'][0,h-1][v],rtol=2e-5,atol=2e-6)
    native.append(dict(hour=h,model=m,RMSE_max_relative=float(np.max(abs(r-x['author_rmse'][0,h-1])/r)),ACC_max_absolute=float(np.max(abs(a[v]-x['author_acc'][0,h-1][v])))))
   # Compare target-time scalars and newest state's future auxiliaries. History additionally has one older auxiliary block.
   d=q['Direct'];np.testing.assert_array_equal(x[f'scalars{h-1}'],d[f'scalars{h-1}']);current=x[f'input{h-1}'][0,177:354] if m=='History' else x[f'input{h-1}'][0]
   conditions.append(dict(model=m,hour=h,scalar_exact=True,magnetic_exact=bool(np.array_equal(current[175:],d[f'input{h-1}'][0,175:])),SEA_max_difference=float(np.max(abs(current[174]-d[f'input{h-1}'][0,174])))))
 layers=[];summary=[];density=[];windows=[]
 for h in (1,2):
  med=np.median(zg[h+1],axis=(1,2))/1000;near=np.flatnonzero((med>=400)&(med<=500));assert len(near)>0
  for m,p in physical.items():
   r,a,v=channel_metrics(p[h],reference[h],clim,lat);offset=0
   for name,n,unit,factor in zip(NAMES,LENGTHS,SI_UNITS,SI_FACTORS):
    sl=slice(offset,offset+n);summary.append(dict(model=m,hour=h,target_hour_UTC=h+1,variable=name,SI_unit=unit,mean_layer_RMSE_SI=float(r[sl].mean()*factor),mean_layer_ACC=float(a[sl][v[sl]].mean()) if v[sl].any() else '',bias_SI=float(np.mean(w*(p[h,sl]-reference[h,sl]))*factor),min_SI=float(p[h,sl].min()*factor),max_SI=float(p[h,sl].max()*factor)))
    for k,c in enumerate(range(offset,offset+n)):layers.append(dict(model=m,hour=h,variable=name,layer_index=k,pressure_coordinate=float(lev[k] if n==28 else ilev[k]),vertical_grid='lev' if n==28 else 'ilev',SI_unit=unit,RMSE_SI=float(r[c]*factor),physical_ACC=float(a[c]) if v[c] else '',ACC_valid=bool(v[c])))
    offset+=n
   rel=p[h,142:]/reference[h,142:]-1;log=np.log(p[h,142:]/reference[h,142:]);global_rows=[];polar_rows=[]
   for region,mask in [('global',np.ones((36,72),bool)),('polar',np.broadcast_to((abs(lat)>=60)[:,None],(36,72))),('nonpolar',np.broadcast_to((abs(lat)<60)[:,None],(36,72)))]:
    ww=w[mask]/w[mask].mean()
    for k in range(29):
     e=rel[k][mask];lg=log[k][mask];row=dict(model=m,hour=h,region=region,ilev_index=k,ilev=float(ilev[k]),reference_ZG_median_km=float(med[k]),relative_RMS=float(np.sqrt(np.mean(ww*e**2))),relative_P95=float(np.percentile(abs(e),95)),relative_max=float(abs(e).max()),natural_log_RMS=float(np.sqrt(np.mean(ww*lg**2))),natural_log_bias=float(np.mean(ww*lg)),positive_fraction=float((p[h,142+k][mask]>0).mean()));density.append(row)
     if region=='global':global_rows.append(row)
     if region=='polar':polar_rows.append(row)
   windows.append(dict(model=m,hour=h,target_hour_UTC=h+1,mean_DEN_layer_RMSE_kg_m3=float(r[142:].mean()*1000),DEN_relative_RMS_all_layer_mean=float(np.mean([z['relative_RMS'] for z in global_rows])),DEN_relative_P95_all_points=float(np.percentile(abs(rel),95)),DEN_natural_log_RMS_all_layer_mean=float(np.mean([z['natural_log_RMS'] for z in global_rows])),near400_500_indices=','.join(map(str,near)),near400_500_medians_km=','.join(f'{med[k]:.3f}' for k in near),near400_500_mean_relative_RMS=float(np.mean([global_rows[k]['relative_RMS'] for k in near])),near400_500_mean_log_RMS=float(np.mean([global_rows[k]['natural_log_RMS'] for k in near])),upper20_28_mean_relative_RMS=float(np.mean([global_rows[k]['relative_RMS'] for k in range(20,29)])),top_relative_RMS=global_rows[-1]['relative_RMS'],top_relative_P95=global_rows[-1]['relative_P95'],polar_relative_max=max(z['relative_max'] for z in polar_rows),DEN_positive_fraction=1.))
 growth=[]
 for m in MODELS:
  for name in NAMES:
   rows=[next(r for r in summary if r['model']==m and r['variable']==name and r['hour']==h) for h in (1,2)];growth.append(dict(model=m,variable=name,RMSE_hour2_to_hour1=rows[1]['mean_layer_RMSE_SI']/rows[0]['mean_layer_RMSE_SI']))
 performance=[]
 for r in runtime['records']:
  performance.append(dict(model=r['model'],parameters=r['parameters'],checkpoint_bytes=r['checkpoint_bytes'],model_load_s=r['model_load_s'],read_preprocess_s=r['read_preprocess_s'],author_loop_metrics_hooks_s=r['author_loop_metrics_hooks_s'],save_s=r['save_s'],formal_first_forward_ms=r['GPU_forward_ms'][0],formal_second_forward_ms=r['GPU_forward_ms'][1],preflight_first_cold_forward_ms=r['history_precheck']['network_GPU_ms'] if r['history_precheck'] else '',peak_allocated_bytes=r['peak_allocated_bytes'],peak_reserved_bytes=r['peak_reserved_bytes'],loading_peak_allocated_bytes=r['loading_peak_allocated_bytes'],process_peak_RSS_KiB=r['RSS_KiB'],controlled_throughput=False))
 for name,rows in [('layers',layers),('summary',summary),('density_layers',density),('windows',windows),('growth',growth),('performance',performance),('drivers',drivers)]:write(name,rows)
 colors=dict(Direct='tab:blue',Flow='tab:orange',LogDEN='tab:green',History='tab:purple');x=np.arange(2)
 fig,ax=plt.subplots(figsize=(9,4))
 for m in MODELS:ax.plot([1,2],[next(r for r in windows if r['model']==m and r['hour']==h)['near400_500_mean_relative_RMS']*100 for h in (1,2)],'o-',label=m,color=colors[m])
 ax.set(xticks=[1,2],xlabel='Lead time (h); targets 02 / 03 UTC',ylabel='Mean layer relative RMS (%)',title='Native layers with global median reference ZG 400–500 km');ax.legend();save(fig,'near400_500')
 fig,axes=plt.subplots(2,3,figsize=(13,8))
 for ax,name,unit in zip(axes.flat,NAMES,SI_UNITS):
  for m in MODELS:ax.plot([1,2],[next(r for r in summary if r['model']==m and r['variable']==name and r['hour']==h)['mean_layer_RMSE_SI'] for h in (1,2)],'o-',label=m,color=colors[m])
  ax.set(xticks=[1,2],xlabel='Lead time (h)',ylabel=f'Mean layer RMSE ({unit})',title=name);ax.legend(fontsize=7)
 save(fig,'variables')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for h,ax in zip((1,2),axes):
  for m in MODELS:ax.plot(ilev,[next(r for r in density if r['model']==m and r['hour']==h and r['region']=='global' and r['ilev_index']==k)['relative_RMS']*100 for k in range(29)],label=m,color=colors[m])
  ax.set(xlabel='Native ilev pressure coordinate',ylabel='Relative RMS (%)',yscale='log',title=f'+{h}h DEN; pressure is not fixed altitude');ax.legend()
 save(fig,'DEN_layers')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for m in MODELS:
  axes[0].plot(NAMES,[r['RMSE_hour2_to_hour1'] for r in growth if r['model']==m],'o-',label=m,color=colors[m]);axes[1].plot([1,2],[next(r for r in windows if r['model']==m and r['hour']==h)['top_relative_P95']*100 for h in (1,2)],'o-',label=m,color=colors[m])
 axes[0].set(ylabel='RMSE +2h / +1h',title='Error growth by variable');axes[0].axhline(1,color='k',ls='--');axes[1].set(xticks=[1,2],xlabel='Lead time (h)',ylabel='Top pressure-layer P95 relative error (%)');axes[0].legend();axes[1].legend();save(fig,'growth_top')
 fig,axes=plt.subplots(1,3,figsize=(13,4))
 for i,r in enumerate(performance):
  m=r['model'];axes[0].bar(i,r['parameters']/1e6,color=colors[m]);axes[1].bar(i,r['formal_second_forward_ms'],color=colors[m]);axes[2].bar(i,r['peak_allocated_bytes']/2**20,color=colors[m])
 for ax,title,unit in zip(axes,['Parameters','Second formal forward (mixed warm-up history)','Inference peak CUDA allocated'],['Millions','GPU event ms','MiB']):ax.set(xticks=range(4),xticklabels=MODELS,ylabel=unit,title=title);ax.tick_params(axis='x',rotation=20)
 save(fig,'performance')
 dump(F/'analysis.json',dict(status='PASS',reference='raw physical target 02/03; common ordinary physical climatology; persistence fixed real01',summary=summary,windows=windows,native_checks=native,conditions=conditions,roundtrip=roundtrip,growth=growth,performance=performance,drivers=drivers,CPU_analysis_s=time.perf_counter()-tick));print(json.dumps(dict(status='PASS',windows=[r for r in windows if r['model']!='Persistence'],summary=[r for r in summary if r['model']!='Persistence']),indent=2))
if __name__=='__main__':main()
