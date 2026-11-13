"""Independent CPU analysis/figures from completed v5 arrays; no model execution."""
from pathlib import Path
import sys,json,csv,time,resource
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from train_den_overfit_v5 import F,O,sha,dump
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from training.den_engineering import evaluate_fields,load_statistics,pairs,DEN_INDICES
from persistence_den_engineering_v3 import csvout,aggregate

def read(p):return list(csv.DictReader(p.open()))
def save(fig,name):
 fig.text(.5,.012,'TIE-GCM B14 | DEN-only / ENGINEERING / HINDCAST | fixed2021 pair, 100 updates',ha='center',fontsize=8);fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(O/name,dpi=160);plt.close(fig)
def paired_log(ap,pp,tt,lat):
 mask=ap>0;w=np.broadcast_to(np.cos(np.deg2rad(lat))[None,:,None],ap.shape)
 return dict(log_points=int(mask.sum()),all_points=int(mask.size),log_coverage=float(mask.mean()),AI_log_RMS=float(np.sqrt(np.average(np.log(ap[mask]/tt[mask])**2,weights=w[mask]))) if mask.any() else None,Persistence_log_RMS=float(np.sqrt(np.average(np.log(pp[mask]/tt[mask])**2,weights=w[mask]))) if mask.any() else None)
def main():
 start=time.perf_counter();assert json.loads((F/'engineering_gate.json').read_text())['PASS'];gpu=json.loads((F/'GPU_result.json').read_text());plan=json.loads((F/'plan.json').read_text());status=json.loads((F/'gpu_job/status.json').read_text());assert gpu['actual_updates']==100 and gpu['validation_passes']==1 and status['returncode']==0
 protected=json.loads((F/'protected_inputs.json').read_text())
 for name,h in protected.items():assert sha(ROOT/name)==h,name
 assert sha(F/'step100.pt')==gpu['checkpoint_SHA256']
 rows=[json.loads(x) for x in (F/'updates.jsonl').read_text().splitlines()];assert [x['step'] for x in rows]==list(range(1,101)) and {x['train_pair_index'] for x in rows}=={0} and len({x['source_input_SHA256'] for x in rows})==1
 assert all(x['gradient_l2_before_clip']>0 and x['head_parameter_delta_l2']>0 and x['nonDEN_head_gradient_absmax']==0 for x in rows)
 lat=np.asarray(plan['training_config']['latitude_deg']);lon=np.load(ROOT/'data/processed/static/lon.npy');m=json.loads((ROOT/'experiments/fourcastden_den_engineering_v3/dataset_manifest.json').read_text())['frames']
 with np.load(ROOT/m['2021'][0]['path']) as n:pers=n['DEN'].astype(float)*1000
 with np.load(ROOT/m['2021'][1]['path']) as n:truth=n['DEN'].astype(float)*1000;zg=n['ZG'].astype(float)*.01
 with np.load(O/'fixed_predictions_local.npz') as n:steps=n['steps'];fixed=n['prediction_kg_m3'];assert list(steps)==[0,10,50,100]
 fixed_metrics=read(O/'fixed_sample_metrics.csv');baseline=read(O/'fixed_Persistence.csv');comparison=[];logs=[]
 for step,a in zip(steps,fixed):
  metrics=evaluate_fields(a,truth,lat,zg)
  for x in metrics:
   old=next(z for z in fixed_metrics if int(z['step'])==step and z['group']==x['group'] and z['region']==x['region'])
   for k in ['RMSE','relative_RMS','bias','positive_fraction']:np.testing.assert_allclose(x[k],float(old[k]),rtol=1e-12,atol=1e-25)
   b=next(z for z in baseline if z['group']==x['group'] and z['region']==x['region'])
   comparison.append(dict(step=int(step),group=x['group'],region=x['region'],AI_RMSE=x['RMSE'],AI_relative_RMS=x['relative_RMS'],AI_bias=x['bias'],AI_log_RMS=x['log_RMS'],AI_positive_fraction=x['positive_fraction'],AI_log_coverage=x['log_coverage'],Persistence_RMSE=float(b['RMSE']),Persistence_relative_RMS=float(b['relative_RMS']),Persistence_bias=float(b['bias'])))
  for name,lev in [('all',np.arange(29)),('upper20_28',np.arange(20,29)),('top28',np.array([28]))]:logs.append(dict(domain='fixed2021',step=int(step),group=name,**paired_log(a[lev],pers[lev],truth[lev],lat)))
 csvout(O/'fixed_AI_vs_Persistence.csv',comparison)
 # Independent normalized-space audit, using the actual float32 training target.
 norm=load_statistics();actual_y=pairs(2021)[0][2][DEN_INDICES.tolist()].numpy().astype(float);weights=np.cos(np.deg2rad(lat))[None,:,None];weights=weights/weights.mean();normalized_rows=[]
 for step,a in zip(steps,fixed):
  encoded=(a/1000-norm.means[DEN_INDICES])/norm.stds[DEN_INDICES];perlevel=(((encoded-actual_y)**2)*weights).mean((1,2));measured=next(x['normalized_loss'] for x in gpu['fixed_snapshots'] if x['step']==step);np.testing.assert_allclose(perlevel.mean(),measured,rtol=2e-6,atol=1e-9)
  for level,loss in enumerate(perlevel):
   ratio=(norm.stds[142+level,0,0]*1000)/truth[level]
   normalized_rows.append(dict(step=int(step),ilev_index=level,normalized_weighted_MSE=float(loss),std_to_target_median=float(np.median(ratio)),std_to_target_min=float(ratio.min()),std_to_target_max=float(ratio.max())))
 csvout(O/'fixed_normalized_layer_audit.csv',normalized_rows)
 with np.load(O/'validation_predictions_local.npz') as n:pred=n['prediction_kg_m3'];times=n['target_UTC'];assert pred.shape==(48,29,36,72) and list(times)==[x['UTC'] for x in m['2022'][1:]]
 pp=[];direct=[];w=np.broadcast_to(np.cos(np.deg2rad(lat))[None,:,None],(29,36,72));w=w/w.sum();hourly=read(O/'validation_hourly.csv')
 for i,a in enumerate(pred):
  with np.load(ROOT/m['2022'][i]['path']) as n:p=n['DEN'].astype(float)*1000
  with np.load(ROOT/m['2022'][i+1]['path']) as n:t=n['DEN'].astype(float)*1000;zz=n['ZG'].astype(float)*.01
  for x in evaluate_fields(p,t,lat,zz):pp.append(dict(pair=i,**x))
  d=a-t;r=dict(pair=i,RMSE=float(np.sqrt(np.sum(w*d*d))),relative_RMS=float(np.sqrt(np.sum(w*(d/t)**2))),bias=float(np.sum(w*d)))
  old=next(z for z in hourly if int(z['pair'])==i and z['group']=='all' and z['region']=='global')
  for k in ['RMSE','relative_RMS','bias']:np.testing.assert_allclose(r[k],float(old[k]),rtol=1e-12,atol=1e-25)
  direct.append(r)
  for name,lev in [('all',np.arange(29)),('upper20_28',np.arange(20,29)),('top28',np.array([28]))]:logs.append(dict(domain='validation2022',pair=i,group=name,**paired_log(a[lev],p[lev],t[lev],lat)))
 psummary=aggregate(pp);old=read(ROOT/'results/fourcastden_den_engineering_v3/persistence_2022_summary.csv')
 for x in psummary:
  b=next(z for z in old if z['group']==x['group'] and z['region']==x['region'])
  for k in ['RMSE','relative_RMS','bias','log_RMS']:np.testing.assert_allclose(x[k],float(b[k]),rtol=1e-12,atol=1e-25)
 ai=read(O/'validation_summary.csv');valcomp=[]
 for a in ai:
  b=next(z for z in psummary if z['group']==a['group'] and z['region']==a['region']);assert int(a['grid_samples'])==b['grid_samples'] and int(a['hourly_pairs'])==b['hourly_pairs']==48
  valcomp.append(dict(group=a['group'],region=a['region'],hourly_pairs=48,grid_samples=b['grid_samples'],AI_RMSE=float(a['RMSE']),AI_relative_RMS=float(a['relative_RMS']),AI_bias=float(a['bias']),AI_log_RMS=float(a['log_RMS']) if a['log_RMS'] else None,AI_positive_fraction=float(a['positive_fraction']),AI_log_coverage=float(a['log_coverage']),Persistence_RMSE=b['RMSE'],Persistence_relative_RMS=b['relative_RMS'],Persistence_bias=b['bias']))
 csvout(O/'validation_AI_vs_Persistence.csv',valcomp);csvout(O/'matched_positive_log.csv',logs);csvout(O/'independent_validation_metrics.csv',direct)
 csvout(O/'Persistence_validation_summary.csv',psummary)
 groups=['all','upper20_28','top28'];snap=gpu['fixed_snapshots']
 fig,ax=plt.subplots(figsize=(9,4));ax.plot([x['step'] for x in rows],[x['loss'] for x in rows],label='Loss before each actual update');ax.scatter(steps,[x['normalized_loss'] for x in snap],color='C1',label='no_grad checkpoints after0/10/50/100');ax.set(xlabel='Actual optimizer update',ylabel='Normalized DEN29 weighted MSE',title='Same2021-03-23 00->01 UTC pair throughout');ax.legend();save(fig,'01_fixed_100_update_loss.png')
 fig,ax=plt.subplots(figsize=(9,4))
 for name in groups:
  rr=[next(x for x in comparison if x['step']==step and x['group']==name and x['region']=='global') for step in steps];line=ax.plot(steps,[x['AI_relative_RMS']*100 for x in rr],marker='o',label='AI '+name)[0];ax.axhline(rr[0]['Persistence_relative_RMS']*100,color=line.get_color(),ls='--',alpha=.7,label='Persistence '+name)
 ax.set(xlabel='Measured checkpoint step',ylabel='Physical relative RMS [%]',title='Fixed2021 pair; measured checkpoints only');ax.legend(ncol=2,fontsize=8);save(fig,'02_fixed_physical_error_checkpoints.png')
 fig,ax=plt.subplots(figsize=(10,4))
 for step in steps:
  rr=sorted([x for x in comparison if x['step']==step and x['region']=='global' and x['group'].startswith('level_')],key=lambda x:x['group']);ax.plot(range(29),[x['AI_relative_RMS']*100 for x in rr],label=f'AI step{step}')
 ax.plot(range(29),[x['Persistence_relative_RMS']*100 for x in rr],color='k',ls='--',label='Persistence');ax.axvspan(20,28,color='grey',alpha=.1);ax.set(xlabel='Native ilev index (not fixed altitude)',ylabel='Relative RMS [%]',title='All29 layers, fixed2021 sample, no layer selection');ax.legend(ncol=3);save(fig,'03_fixed_by_layer.png')
 fig,axes=plt.subplots(1,4,figsize=(17,4));arrays=[truth[24],pers[24],fixed[0,24],fixed[-1,24]];vmin=min(a.min() for a in arrays);vmax=max(a.max() for a in arrays)
 for ax,a,title in zip(axes,arrays,['TIE-GCM target','Persistence','Random step0','AFNONet step100']):
  im=ax.pcolormesh(lon,lat,a,shading='auto',vmin=vmin,vmax=vmax);ax.set(title=title,xlabel='Longitude [deg]',ylabel='Latitude [deg]');fig.colorbar(im,ax=ax,label='DEN [kg/m3]')
 fig.suptitle('Preselected native ilev24, 2021-03-23 01 UTC; common color scale includes step0');save(fig,'04_fixed_density_maps.png')
 fig,axes=plt.subplots(1,2,figsize=(10,4));axes[0].plot(steps,[x['nonpositive_count'] for x in snap],marker='o');axes[0].set(ylabel='Nonpositive DEN values [count]');axes[1].plot(steps,[x['positive_fraction']*100 for x in snap],marker='o');axes[1].set(ylabel='Physical positive fraction [%]');[a.set_xlabel('Measured checkpoint step') for a in axes];fig.suptitle('Fixed2021 pair; no measurements invented between checkpoints');save(fig,'05_nonpositive_checkpoints.png')
 fig,axes=plt.subplots(1,2,figsize=(12,4));rr=[next(x for x in valcomp if x['group']==g and x['region']=='global') for g in groups];ix=np.arange(3)
 axes[0].bar(ix-.18,[x['AI_relative_RMS']*100 for x in rr],.36,label='Final step100');axes[0].bar(ix+.18,[x['Persistence_relative_RMS']*100 for x in rr],.36,label='Persistence');axes[0].set_xticks(ix,groups);axes[0].set(ylabel='Relative RMS [%]');levels=sorted([x for x in valcomp if x['region']=='global' and x['group'].startswith('level_')],key=lambda x:x['group'])
 for key,label in [('AI','Final step100'),('Persistence','Persistence')]:axes[1].plot(range(29),[x[key+'_relative_RMS']*100 for x in levels],label=label)
 axes[1].set(xlabel='Native ilev index',ylabel='Relative RMS [%]');[a.legend() for a in axes];fig.suptitle('2022-03-23 01 UTC to03-25 00 UTC, final-only48 pairs; not blind test');save(fig,'06_2022_final_validation.png')
 fig,axes=plt.subplots(1,3,figsize=(13,4));axes[0].plot([x['step'] for x in rows],[x['wall_s'] for x in rows]);axes[0].set(xlabel='Actual update',ylabel='Update compute wall [s]');ss=status['samples'];axes[1].plot([x['wall_s'] for x in ss],[x.get('GPU_process_bytes',0)/2**30 for x in ss]);axes[1].set(xlabel='Supervised wall [s]',ylabel='Sampled GPU process [GiB]');axes[2].bar(['Updates','Fixed eval','Save/restore','Final val','Save arrays'],[gpu['pure_update_wall_s'],gpu['fixed_evaluation_s'],gpu['save_restore_s'],gpu['validation_s'],gpu['save_metrics_s']]);axes[2].tick_params(axis='x',rotation=35);axes[2].set(ylabel='Measured component wall [s]');fig.suptitle('Measured runtime components; CPU finalization recorded separately');save(fig,'07_resources_and_timing.png')
 dump(F/'final_audit.json',dict(PASS=True,actual_updates=100,fixed_pair_only=True,fixed_check_steps=steps.tolist(),initial_seed_hash_matches_v4=True,protected_files_verified=len(protected),old_data_statistics_v4_unchanged=True,final_checkpoint_SHA_verified=True,fixed_metrics_recomputed=True,normalized_loss_independently_recomputed=True,independent_validation_metrics=True,Persistence_recomputed48_pairs_matches_v3=True,one_final_validation_pass=True,wall_s=time.perf_counter()-start,CPU_peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,science_training_ready=False))
 print(json.dumps(dict(PASS=True,fixed_global=[x for x in comparison if x['region']=='global' and x['group'] in groups],validation_global=rr,postprocess_wall_s=time.perf_counter()-start),indent=2))
if __name__=='__main__':main()
