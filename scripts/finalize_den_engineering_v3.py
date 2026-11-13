"""CPU-only final evidence, physical plots and bounded failed-launch accounting."""
import os
from pathlib import Path
import sys,json,csv,time,resource,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from netCDF4 import Dataset
from training.den_engineering import F,O,DATA,DEN_INDICES,native_fields
from persistence_den_engineering_v3 import csvout
from run_tiegcm_mar23_2021_longrun import stream_sha

def dump(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2)
def save(fig,name):
 fig.text(.5,.015,'B14 TIE-GCM | DEN-only engineering / HINDCAST | no trained AI result',ha='center',fontsize=8)
 fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(O/name,dpi=160);plt.close(fig)
if __name__=='__main__':
 start=time.perf_counter();manifest=json.loads((F/'dataset_manifest.json').read_text());frames=manifest['frames'];lat=np.load(ROOT/'data/processed/static/lat.npy');lon=np.load(ROOT/'data/processed/static/lon.npy')
 protected=json.loads((F/'protected_files.json').read_text());assert all(stream_sha(ROOT/k)==v for k,v in protected.items())
 for yy in frames:
  for r in frames[yy]:assert stream_sha(ROOT/r['path'])==r['SHA256'] and stream_sha(ROOT/r['source'])==r['source_SHA256']
 # Retain actual native axes alongside the official 14-key frame format.
 grids={}
 for yy in frames:
  with Dataset(ROOT/frames[yy][0]['source']) as n:
   grids[yy]={k:np.asarray(n[k][:]) for k in ['lat','lon','lev','ilev']}
   np.testing.assert_array_equal(grids[yy]['lat'],lat);np.testing.assert_array_equal(grids[yy]['lon'],lon)
 for k in grids['2021']:np.testing.assert_array_equal(grids['2021'][k],grids['2022'][k])
 np.savez(DATA/'grid.npz',**grids['2021'])
 dump(F/'grid_audit.json',dict(PASS=True,axes={k:v.tolist() for k,v in grids['2021'].items()},grid_SHA256=stream_sha(DATA/'grid.npz'),DEN_grid='ilev',ZG_grid='ilev',TN_UN_VN='lev, 28 valid output levels',source_files=[frames[y][0]['source'] for y in frames]))
 with np.load(DATA/'statistics.npz') as n:means=n['means'].reshape(-1);stds=n['stds'].reshape(-1)
 stats=[];dist={};norm_stats={}
 for yy in frames:
  den=[];normalized=[]
  for r in frames[yy]:
   fields=native_fields(ROOT/r['path']);d=fields[DEN_INDICES];den.append(d*1000);normalized.append((d-means[DEN_INDICES,None,None])/stds[DEN_INDICES,None,None])
  a=np.stack(den);z=np.stack(normalized);dist[yy]=np.percentile(a,[5,50,95],axis=(0,2,3));norm_stats[yy]=(z.mean((0,2,3)),z.std((0,2,3)))
  for i in range(29):stats.append(dict(year=yy,ilev_index=i,native_ilev=float(grids[yy]['ilev'][i]),density_q05=dist[yy][0,i],density_median=dist[yy][1,i],density_q95=dist[yy][2,i],normalized_mean=norm_stats[yy][0][i],normalized_std=norm_stats[yy][1][i],statistics_fit_year=2021))
 csvout(O/'distribution_statistics.csv',stats)
 csvout(O/'normalization_174_channels.csv',[dict(channel=i,mean_native=float(means[i]),std_native=float(stds[i]),fit_year=2021,DEN=(142<=i<171)) for i in range(174)])
 rows=list(csv.DictReader((O/'persistence_summary.csv').open()))
 # Independent vectorized physical verification of all-level global errors.
 check=[];w=np.cos(np.deg2rad(lat))[None,:,None];w=np.broadcast_to(w,(29,36,72));w=w/w.sum()
 for yy in frames:
  mse=[];rel=[];bias=[]
  for a,b in zip(frames[yy][:-1],frames[yy][1:]):
   with np.load(ROOT/a['path']) as n:p=n['DEN'].astype(float)*1000
   with np.load(ROOT/b['path']) as n:t=n['DEN'].astype(float)*1000
   mse.append(np.sum(w*(p-t)**2));rel.append(np.sum(w*((p-t)/t)**2));bias.append(np.sum(w*(p-t)))
  expected=[x for x in rows if x['year']==yy and x['group']=='all' and x['region']=='global'][0]
  actual=dict(RMSE=float(np.sqrt(np.mean(mse))),relative_RMS=float(np.sqrt(np.mean(rel))),bias=float(np.mean(bias)))
  for k,v in actual.items():np.testing.assert_allclose(v,float(expected[k]),rtol=1e-11,atol=1e-24)
  check.append(dict(year=yy,**actual))
 dump(F/'independent_physical_metrics.json',dict(PASS=True,results=check,method='direct weighted array sums over all 120 pairs, no evaluation helper'))
 fig,ax=plt.subplots(figsize=(9,5))
 for yy,c in [('2021','C0'),('2022','C1')]:
  ax.semilogy(range(29),dist[yy][1],label=f'{yy} B14, n={len(frames[yy])} hours',color=c);ax.fill_between(range(29),dist[yy][0],dist[yy][2],alpha=.18,color=c)
 ax.set(xlabel='Native ilev index (not fixed geometric altitude)',ylabel='DEN [kg/m3]',title='Candidate distributions: median and spatial/time P05-P95');ax.legend();save(fig,'01_density_distribution.png')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 axes[0].semilogy(range(29),means[142:171]*1000,label='2021 fitted mean');axes[0].semilogy(range(29),stds[142:171]*1000,label='2021 fitted std');axes[0].set(ylabel='DEN [kg/m3]',xlabel='Native ilev index');axes[0].legend()
 for yy in frames:
  axes[1].plot(norm_stats[yy][0],label=f'{yy} encoded mean');axes[1].plot(norm_stats[yy][1],ls='--',label=f'{yy} encoded std')
 axes[1].set(xlabel='Native ilev index',ylabel='Dimensionless');axes[1].legend(fontsize=8);fig.suptitle('Training-only statistics; 2022 descriptive evaluation, never fitted');save(fig,'02_normalization.png')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for yy in frames:
  rr=[x for x in rows if x['year']==yy and x['region']=='global' and x['group'].startswith('level_')];rr.sort(key=lambda x:x['group']);axes[0].plot(range(29),[float(x['relative_RMS'])*100 for x in rr],label=f'{yy} persistence')
  regs=['south_high','midlow','north_high'];rr=[next(x for x in rows if x['year']==yy and x['group']=='upper20_28' and x['region']==r) for r in regs];axes[1].plot(regs,[float(x['relative_RMS'])*100 for x in rr],marker='o',label=yy)
 axes[0].set(xlabel='Native ilev index',ylabel='Relative RMS [%]',title='One-hour persistence by layer');axes[1].set(ylabel='Relative RMS [%]',title='Upper indices20-28 by latitude');[a.legend() for a in axes];save(fig,'03_persistence.png')
 # Frozen display pair0 and native ilev24; no AI panel invented after failed launch.
 first=frames['2022'];
 with np.load(ROOT/first[0]['path']) as n:p=n['DEN'][24]*1000
 with np.load(ROOT/first[1]['path']) as n:t=n['DEN'][24]*1000
 fig,axes=plt.subplots(1,3,figsize=(14,4));vmin=min(p.min(),t.min());vmax=max(p.max(),t.max())
 for ax,a,title in zip(axes,[t,p,(p-t)/t*100],['TIE-GCM t+1 reference','Persistence (current DEN)','Persistence signed relative error [%]']):
  im=ax.pcolormesh(lon,lat,a,shading='auto',**({'vmin':vmin,'vmax':vmax} if ax is not axes[2] else {'cmap':'RdBu_r'}));fig.colorbar(im,ax=ax,label='kg/m3' if ax is not axes[2] else '%');ax.set(title=title,xlabel='Longitude [deg]',ylabel='Latitude [deg]')
 fig.suptitle('Frozen sample: 2022-03-23 00 -> 01 UTC, native ilev24 (not fixed altitude)');save(fig,'04_fixed_real_DEN_sample.png')
 status=json.loads((F/'gpu_job/status.json').read_text());assert status['returncode']==1 and not (F/'GPU_result.json').exists()
 failure=dict(PASS=False,status='FAIL_BEFORE_FIRST_FORWARD',training_task_launches=1,optimizer_updates=0,model_forwards=0,checkpoints_saved=0,returncode=status['returncode'],supervised_wall_s=status['elapsed_s'],peak_sampled_tree_RSS_bytes=status['peak_sampled_tree_rss_bytes'],preflight_GPU_available=True,actual_failure='torch.cuda.is_available() assertion',proven_cause='train imports persistence_den_engineering_v3, whose module-level assignment cleared CUDA_VISIBLE_DEVICES after training set it to 0',fix='move CPU device selection under persistence __main__; import-isolation subprocess regression PASS; GPU not retried',loss_curve='NOT_AVAILABLE: no forward/loss/update',AI_validation='NOT_AVAILABLE',checkpoint_GPU_restore='NOT_TESTED',science_training_ready=False)
 dump(F/'GPU_failure_audit.json',failure)
 dump(F/'final_cpu_audit.json',dict(PASS=True,protected_files_verified=len(protected),source_and_frame_SHA_verified=True,grid_verified=True,independent_baseline_verified=True,CPU_tests_before_launch=25,post_failure_import_regression=1,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,real_training_updates=0))
 print(json.dumps(dict(PASS=True,baseline=[x for x in rows if x['region']=='global' and x['group'] in ['all','upper20_28','top28','reference_median_ZG_400_500']],resources=json.loads((F/'final_cpu_audit.json').read_text())),indent=2))
