"""Summarize and plot existing PROVISIONAL query CSVs only."""
import argparse,csv,json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
FIELDS=['sample','rho_kg_m3','valid','model_zg_m','wgs84_lat_deg','model_lat_deg','top_margin_m','bottom_margin_m','dlnrho_dh_per_m','vertical_spacing_min_m','vertical_spacing_max_m','vertical_linear_relative','horizontal_log_relative','time_log_relative','horizontal_and_time_log_relative','vertical_coarsened_log_relative','scale_height_m','geocentric_lat_deg','wgs84_height_m','model_lon_deg']
I={k:i for i,k in enumerate(FIELDS)}
def load(path):
 groups={}
 with path.open() as f:
  for row in csv.DictReader(f):
   assert row['status']=='PROVISIONAL'
   groups.setdefault(row['scenario'],[]).append([float(row[k]) if row[k] else np.nan for k in FIELDS])
 return {k:np.asarray(v) for k,v in groups.items()}
def metric(x):
 x=np.asarray(x);x=x[np.isfinite(x)]
 if not len(x):return {'n':0}
 return {'n':len(x),'min':float(x.min()),'max':float(x.max()),'mean':float(x.mean()),'median':float(np.median(x)),'p05':float(np.percentile(x,5)),'p95':float(np.percentile(x,95)),'p95_abs':float(np.percentile(abs(x),95)),'rmse':float(np.sqrt(np.mean(x*x)))}
def regions(a):
 lat=a[:,I['wgs84_lat_deg']]
 return {'global':np.ones(len(a),bool),'tropics_abs_lt30':abs(lat)<30,'north_mid_30_60':(lat>=30)&(lat<60),'south_mid_30_60':(lat<=-30)&(lat>-60),'north_polar_ge60':lat>=60,'south_polar_ge60':lat<=-60,'near_grid_edge_abs_ge85':abs(lat)>=85,'longitude_seam_abs_ge175':abs(a[:,I['model_lon_deg']])>=175}
def main():
 p=argparse.ArgumentParser();p.add_argument('--run-tag',default='swarm_provisional_v1');p.add_argument('--preview',action='store_true');args=p.parse_args();tag=args.run_tag
 if not tag.replace('_','').isalnum():raise ValueError('Unsafe tag')
 out=ROOT/'experiments'/tag
 data={s:load(ROOT/f'results/metrics/{tag}_coarse_{s}.csv') for s in ['S3','S7']}
 report={'status':'PROVISIONAL','weighting':'equal trajectory-time samples, not global area','coarse_offset_sensitivity':{},'coarse_S3_S7':{},'coarse_interpolation':{},'full':{}}
 for source,groups in data.items():
  base=groups['A+0km'];source_out={}
  for scenario,a in groups.items():
   assert np.array_equal(a[:,0],base[:,0])
   valid=(a[:,I['valid']]==1)&(base[:,I['valid']]==1)
   relative=a[:,I['rho_kg_m3']]/base[:,I['rho_kg_m3']]-1
   offset=a[:,I['model_zg_m']]-base[:,I['model_zg_m']]
   predicted=np.expm1(base[:,I['dlnrho_dh_per_m']]*offset)
   source_out[scenario]={r:{'relative_density':metric(relative[mask&valid]),'log_density':metric(np.log1p(relative[mask&valid])),'local_slope_prediction_residual':metric((relative-predicted)[mask&valid])} for r,mask in regions(a).items()}
   source_out[scenario]['coverage']={'samples':len(a),'valid_count':int((a[:,I['valid']]==1).sum()),'min_top_margin_m':float(np.nanmin(a[:,I['top_margin_m']])),'min_bottom_margin_m':float(np.nanmin(a[:,I['bottom_margin_m']]))}
  report['coarse_offset_sensitivity'][source]=source_out
  report['coarse_interpolation'][source]={scenario:{r:{k:metric(a[mask,I[k]]) for k in ['vertical_linear_relative','horizontal_log_relative','time_log_relative','horizontal_and_time_log_relative','vertical_coarsened_log_relative','vertical_spacing_min_m','vertical_spacing_max_m','dlnrho_dh_per_m','scale_height_m']} for r,mask in regions(a).items()} for scenario,a in groups.items() if scenario in ['A+0km','B_R6371km']}
 for scenario in data['S3']:
  a,b=data['S3'][scenario],data['S7'][scenario];valid=(a[:,I['valid']]==1)&(b[:,I['valid']]==1)
  log=np.log(a[:,I['rho_kg_m3']]/b[:,I['rho_kg_m3']]);rel=np.expm1(log)
  report['coarse_S3_S7'][scenario]={r:{'relative_density':metric(rel[mask&valid]),'log_density':metric(log[mask&valid])} for r,mask in regions(a).items()}
 if args.preview:
  dest=out/'preview_statistics.json'
  with dest.open('x') as f:json.dump(report,f,indent=2,allow_nan=False)
  print(json.dumps({s:{k:v['global']['relative_density']['median'] for k,v in g.items()} for s,g in report['coarse_offset_sensitivity'].items()},indent=2));return
 full={s:load(ROOT/f'data/processed/{tag}/PROVISIONAL_full_{s}.csv') for s in ['S3','S7']}
 for scenario in ['A+0km','B_R6371km']:
  a,b=full['S3'][scenario],full['S7'][scenario]
  assert len(a)==17281 and np.array_equal(a[:,0],b[:,0])
  valid=(a[:,I['valid']]==1)&(b[:,I['valid']]==1)
  rel=a[:,I['rho_kg_m3']]/b[:,I['rho_kg_m3']]-1;log=np.log1p(rel)
  region_stats={r:{'relative_density':metric(rel[mask&valid]),'log_density':metric(log[mask&valid])} for r,mask in regions(a).items()}
  hours=a[:,0]*10/3600
  bins=[{'start_hour':h,'stop_hour':h+6,'relative_density':metric(rel[(hours>=h)&(hours<h+6)&valid]),'log_density':metric(log[(hours>=h)&(hours<h+6)&valid])} for h in range(0,48,6)]
  report['full'][scenario]={'S3_S7':region_stats,'six_hour_bins':bins,'common_valid_count':int(valid.sum()),'common_valid_fraction':float(valid.mean()),'sources':{s:{'rho_kg_m3':metric(g[scenario][:,I['rho_kg_m3']]),'min_top_margin_m':float(np.min(g[scenario][:,I['top_margin_m']])),'min_bottom_margin_m':float(np.min(g[scenario][:,I['bottom_margin_m']])),'interpolation':{k:metric(g[scenario][:,I[k]]) for k in ['vertical_linear_relative','horizontal_log_relative','time_log_relative','vertical_coarsened_log_relative']}} for s,g in full.items()}}
 report['full_mapping_B_vs_A']={}
 for source,g in full.items():
  a,b=g['A+0km'],g['B_R6371km'];rel=b[:,I['rho_kg_m3']]/a[:,I['rho_kg_m3']]-1
  report['full_mapping_B_vs_A'][source]={'relative_density':metric(rel),'geodetic_minus_geocentric_lat_deg':metric(a[:,I['wgs84_lat_deg']]-a[:,I['geocentric_lat_deg']]),'B_minus_A_height_m':metric(b[:,I['model_zg_m']]-a[:,I['model_zg_m']])}
 dest=out/'statistics.json'
 with dest.open('x') as f:json.dump(report,f,indent=2,allow_nan=False)
 # Compact public tables; all raw full trajectory CSVs remain local.
 with (ROOT/f'results/metrics/{tag}_sensitivity_summary.csv').open('x') as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['status','source','scenario','region','n','mean_relative','median_relative','p95_abs_relative','log_RMSE'])
  for source,groups in report['coarse_offset_sensitivity'].items():
   for scenario,rr in groups.items():
    for region,stats in rr.items():
     if region=='coverage':continue
     m=stats['relative_density'];w.writerow(['PROVISIONAL',source,scenario,region,m['n'],m.get('mean'),m.get('median'),m.get('p95_abs'),stats['log_density'].get('rmse')])
 hours=full['S3']['A+0km'][:,0]*10/3600
 fig,ax=plt.subplots(2,1,figsize=(11,7),sharex=True)
 for source,g in full.items():
  for name,style in [('A+0km','-'),('B_R6371km','--')]:ax[0].plot(hours,g[name][:,I['rho_kg_m3']],style,label=f'{source} {name}',lw=.6)
 for name in ['A+0km','B_R6371km']:
  ax[1].plot(hours,np.log(full['S3'][name][:,I['rho_kg_m3']]/full['S7'][name][:,I['rho_kg_m3']]),label=name,lw=.6)
 ax[0].set(ylabel='Conditional density (kg/m³)',title='PROVISIONAL Swarm-A mappings: full 10 s samples')
 ax[1].set(xlabel='Hours since 2023-03-21 00:00:02 UTC',ylabel='ln(S3 / S7)',title='PROVISIONAL spin-up-history sensitivity')
 for a in ax:a.legend();a.grid(alpha=.25)
 fig.tight_layout();fig.savefig(ROOT/f'results/figures/{tag}_alongtrack.png',dpi=160);plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for source,groups in report['coarse_offset_sensitivity'].items():
  names=[f'A{x:+d}km' for x in [-10,-5,-2,0,2,5,10]]
  axes[0].plot([-10,-5,-2,0,2,5,10],[groups[n]['global']['relative_density']['median']*100 for n in names],'o-',label=source)
 for source,g in full.items():axes[1].plot(hours,(g['B_R6371km'][:,I['rho_kg_m3']]/g['A+0km'][:,I['rho_kg_m3']]-1)*100,label=source,lw=.5)
 axes[0].set(xlabel='Artificial height offset (km)',ylabel='Median density change vs A0 (%)',title='PROVISIONAL offsets: 5 min samples (not bounds)')
 axes[1].set(xlabel='Hours from start',ylabel='B / A0 - 1 (%)',title='PROVISIONAL combined latitude / height mapping')
 for a in axes:a.legend();a.grid(alpha=.25)
 fig.tight_layout();fig.savefig(ROOT/f'results/figures/{tag}_coordinate_sensitivity.png',dpi=160);plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for source,g in full.items():
  a=g['A+0km'];axes[0].plot(hours,a[:,I['vertical_linear_relative']]*100,label=source,lw=.5)
  axes[1].scatter(a[::20,I['vertical_spacing_max_m']]/1000,a[::20,I['vertical_linear_relative']]*100,label=source,s=4,alpha=.4)
 axes[0].set(xlabel='Hours from start',ylabel='Linear vertical / log vertical - 1 (%)',title='PROVISIONAL interpolation-method sensitivity')
 axes[1].set(xlabel='Largest bracketing interval among 8 columns (km)',ylabel='Linear / log vertical - 1 (%)',title='PROVISIONAL grid spacing; every 20th sample')
 for a in axes:a.legend();a.grid(alpha=.25)
 fig.tight_layout();fig.savefig(ROOT/f'results/figures/{tag}_interpolation.png',dpi=160);plt.close(fig)
 print(json.dumps({'status':'PROVISIONAL','full':report['full'],'mapping':report['full_mapping_B_vs_A']},indent=2))
if __name__=='__main__':main()
