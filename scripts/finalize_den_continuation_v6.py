"""CPU-only combined history and independent v6 metric verification; no old model rerun."""
from pathlib import Path
import sys,json,csv,time,resource
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from train_den_continuation_v6 import F,O,sha,dump
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from training.den_engineering import evaluate_fields,load_statistics,pairs,DEN_INDICES
from persistence_den_engineering_v3 import csvout,aggregate

def read(p):return list(csv.DictReader(p.open()))
def save(fig,name):
 fig.text(.5,.012,'TIE-GCM B14 | fixed2021 pair | DEN-only ENGINEERING/HINDCAST | v5 history + v6 continuation',ha='center',fontsize=8);fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(O/name,dpi=160);plt.close(fig)
def log_pair(a,p,t,lat):
 ok=a>0;w=np.broadcast_to(np.cos(np.deg2rad(lat))[None,:,None],a.shape)
 return dict(log_points=int(ok.sum()),all_points=int(ok.size),log_coverage=float(ok.mean()),AI_log_RMS=float(np.sqrt(np.average(np.log(a[ok]/t[ok])**2,weights=w[ok]))) if ok.any() else None,Persistence_log_RMS=float(np.sqrt(np.average(np.log(p[ok]/t[ok])**2,weights=w[ok]))) if ok.any() else None)
def main():
 tick=time.perf_counter();assert json.loads((F/'engineering_gate.json').read_text())['PASS'];g=json.loads((F/'GPU_result.json').read_text());plan=json.loads((F/'plan.json').read_text());status=json.loads((F/'gpu_job/status.json').read_text());assert g['additional_updates']==100 and g['end_step']==200 and g['validation_passes']==1 and status['returncode']==0
 protected=json.loads((F/'protected_inputs.json').read_text())
 for n,h in protected.items():assert sha(ROOT/n)==h,n
 assert sha(F/'step200.pt')==g['checkpoint_SHA256']
 old=ROOT/'experiments/fourcastden_den_overfit_v5';oldout=ROOT/'results/fourcastden_den_overfit_v5';oldgpu=json.loads((old/'GPU_result.json').read_text());oldrows=[json.loads(x) for x in (old/'updates.jsonl').read_text().splitlines()];newrows=[json.loads(x) for x in (F/'updates.jsonl').read_text().splitlines()];assert [x['step'] for x in newrows]==list(range(101,201)) and all(x['optimizer_internal_step']==x['step'] for x in newrows);assert {x['learning_rate'] for x in newrows}=={1e-4}
 combined=[dict(experiment='v5_history_readonly',**x) for x in oldrows]+[dict(experiment='v6_continuation',**x) for x in newrows];csvout(O/'combined_updates_1_200.csv',combined)
 historical_metrics=read(oldout/'fixed_sample_metrics.csv');newmetrics=read(O/'fixed_sample_metrics.csv')
 # Historical0--100 values are read-only citations. Only new v6 arrays recomputed.
 for r in [x for x in newmetrics if int(x['step'])==100]:
  b=next(x for x in historical_metrics if int(x['step'])==100 and x['group']==r['group'] and x['region']==r['region'])
  for k in ['normalized_loss','RMSE','relative_RMS','bias']:np.testing.assert_allclose(float(r[k]),float(b[k]),rtol=1e-10,atol=1e-12)
 history=[dict(source='v5_historical_readonly',**x) for x in historical_metrics]+[dict(source='v6_new_continuation',**x) for x in newmetrics if int(x['step'])>100];csvout(O/'combined_fixed_metrics.csv',history)
 frames=json.loads((ROOT/'experiments/fourcastden_den_engineering_v3/dataset_manifest.json').read_text())['frames'];lat=np.asarray(plan['training_config']['latitude_deg']);lon=np.load(ROOT/'data/processed/static/lon.npy')
 with np.load(ROOT/frames['2021'][0]['path']) as n:pers=n['DEN'].astype(float)*1000
 with np.load(ROOT/frames['2021'][1]['path']) as n:truth=n['DEN'].astype(float)*1000;zg=n['ZG'].astype(float)*.01
 with np.load(O/'fixed_predictions_local.npz') as n:steps=n['steps'];fixed=n['prediction_kg_m3'];assert list(steps)==[100,150,200]
 base=read(O/'fixed_Persistence.csv');norm=load_statistics();actual_y=pairs(2021)[0][2][DEN_INDICES.tolist()].numpy().astype(float);weights=np.cos(np.deg2rad(lat))[None,:,None];weights/=weights.mean();normalized=[];matched=[]
 for step,a in zip(steps,fixed):
  rr=evaluate_fields(a,truth,lat,zg)
  for x in rr:
   b=next(r for r in newmetrics if int(r['step'])==step and r['group']==x['group'] and r['region']==x['region'])
   for k in ['RMSE','relative_RMS','bias','positive_fraction']:np.testing.assert_allclose(x[k],float(b[k]),rtol=1e-12,atol=1e-25)
  enc=(a/1000-norm.means[DEN_INDICES])/norm.stds[DEN_INDICES];perlevel=(((enc-actual_y)**2)*weights).mean((1,2));logged=next(x['normalized_loss'] for x in g['fixed_snapshots'] if x['step']==step);np.testing.assert_allclose(perlevel.mean(),logged,rtol=2e-6,atol=1e-9)
  for i,v in enumerate(perlevel):normalized.append(dict(step=int(step),ilev_index=i,normalized_weighted_MSE=float(v)))
  for group,lev in [('all',np.arange(29)),('upper20_28',np.arange(20,29)),('top28',np.array([28]))]:matched.append(dict(domain='fixed2021',step=int(step),group=group,**log_pair(a[lev],pers[lev],truth[lev],lat)))
 csvout(O/'new_fixed_normalized_layer_audit.csv',normalized)
 comparison=[]
 for a in history:
  b=next(x for x in base if x['group']==a['group'] and x['region']==a['region'])
  comparison.append(dict(step=int(a['step']),source=a['source'],group=a['group'],region=a['region'],AI_RMSE=float(a['RMSE']),AI_relative_RMS=float(a['relative_RMS']),AI_bias=float(a['bias']),AI_log_RMS=float(a['log_RMS']) if a['log_RMS'] else None,AI_positive_fraction=float(a['positive_fraction']),Persistence_RMSE=float(b['RMSE']),Persistence_relative_RMS=float(b['relative_RMS']),Persistence_bias=float(b['bias'])))
 csvout(O/'combined_fixed_AI_vs_Persistence.csv',comparison)
 with np.load(O/'validation_predictions_local.npz') as n:pred=n['prediction_kg_m3'];times=n['target_UTC'];assert pred.shape==(48,29,36,72) and list(times)==[x['UTC'] for x in frames['2022'][1:]]
 pp=[];independent=[];w=np.broadcast_to(np.cos(np.deg2rad(lat))[None,:,None],(29,36,72));w=w/w.sum();hourly=read(O/'validation_hourly.csv')
 for i,a in enumerate(pred):
  with np.load(ROOT/frames['2022'][i]['path']) as n:p=n['DEN'].astype(float)*1000
  with np.load(ROOT/frames['2022'][i+1]['path']) as n:t=n['DEN'].astype(float)*1000;zz=n['ZG'].astype(float)*.01
  for x in evaluate_fields(p,t,lat,zz):pp.append(dict(pair=i,**x))
  delta=a-t;r=dict(pair=i,RMSE=float(np.sqrt(np.sum(w*delta*delta))),relative_RMS=float(np.sqrt(np.sum(w*(delta/t)**2))),bias=float(np.sum(w*delta)))
  b=next(x for x in hourly if int(x['pair'])==i and x['group']=='all' and x['region']=='global')
  for k in ['RMSE','relative_RMS','bias']:np.testing.assert_allclose(r[k],float(b[k]),rtol=1e-12,atol=1e-25)
  independent.append(r)
  for group,lev in [('all',np.arange(29)),('upper20_28',np.arange(20,29)),('top28',np.array([28]))]:matched.append(dict(domain='validation2022',pair=i,group=group,**log_pair(a[lev],p[lev],t[lev],lat)))
 persistence=aggregate(pp);oldpersist=read(oldout/'Persistence_validation_summary.csv')
 for x in persistence:
  b=next(r for r in oldpersist if r['group']==x['group'] and r['region']==x['region'])
  for k in ['RMSE','relative_RMS','bias','log_RMS']:np.testing.assert_allclose(x[k],float(b[k]),rtol=1e-12,atol=1e-25)
 validation=read(O/'validation_summary.csv');oldval=read(oldout/'validation_summary.csv');valcomp=[]
 for a in validation:
  b=next(x for x in persistence if x['group']==a['group'] and x['region']==a['region']);v=next(x for x in oldval if x['group']==a['group'] and x['region']==a['region']);assert int(a['grid_samples'])==b['grid_samples']==int(v['grid_samples'])
  valcomp.append(dict(group=a['group'],region=a['region'],hourly_pairs=48,grid_samples=b['grid_samples'],step100_relative_RMS=float(v['relative_RMS']),step200_relative_RMS=float(a['relative_RMS']),Persistence_relative_RMS=b['relative_RMS'],step100_RMSE=float(v['RMSE']),step200_RMSE=float(a['RMSE']),Persistence_RMSE=b['RMSE'],step200_bias=float(a['bias']),step200_log_RMS=float(a['log_RMS']) if a['log_RMS'] else None,step200_positive_fraction=float(a['positive_fraction']),step200_log_coverage=float(a['log_coverage'])))
 csvout(O/'validation_100_200_Persistence.csv',valcomp);csvout(O/'matched_positive_log.csv',matched);csvout(O/'independent_validation_metrics.csv',independent);csvout(O/'Persistence_validation_summary.csv',persistence)
 snaps=oldgpu['fixed_snapshots']+[s for s in g['fixed_snapshots'] if s['step']>100];steps6=[s['step'] for s in snaps];groups=['all','upper20_28','top28']
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for rr,label,color in [(oldrows,'v5 historical','C0'),(newrows,'v6 resumed','C1')]:axes[0].semilogy([x['step'] for x in rr],[x['loss'] for x in rr],label=label,color=color)
 axes[0].scatter(steps6,[x['normalized_loss'] for x in snaps],color='k',s=18,label='post-update evaluation');axes[0].axvline(100,color='grey',ls='--');axes[0].set(xlabel='Cumulative optimizer step',ylabel='Normalized DEN loss [log]',title='Complete history, no old model rerun');axes[0].legend(fontsize=8)
 late=[x for x in newrows if x['step']>=150];axes[1].plot([x['step'] for x in late],[x['loss'] for x in late],color='C1');axes[1].set(xlabel='Cumulative optimizer step',ylabel='Pre-update normalized loss',title='Last50 new updates, raw values');save(fig,'01_loss_0_200_and_late_detail.png')
 fig,ax=plt.subplots(figsize=(9,4))
 for group in groups:
  rr=[next(x for x in comparison if x['step']==s and x['group']==group and x['region']=='global') for s in steps6];line=ax.plot(steps6,[x['AI_relative_RMS']*100 for x in rr],marker='o',label=group)[0];ax.axhline(rr[0]['Persistence_relative_RMS']*100,color=line.get_color(),ls='--',alpha=.7)
 ax.axvline(100,color='grey',ls=':');ax.set(xlabel='Measured cumulative checkpoint step',ylabel='Relative RMS [%]',title='Fixed2021-03-23 00->01 UTC; dashed lines=Persistence');ax.legend();save(fig,'02_fixed_relative_RMS_0_200.png')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for step in [100,150,200]:
  rr=sorted([x for x in comparison if x['step']==step and x['region']=='global' and x['group'].startswith('level_')],key=lambda x:x['group']);axes[0].plot(range(29),[x['AI_relative_RMS']*100 for x in rr],label=f'step{step}');axes[1].plot(range(29),[x['AI_RMSE'] for x in rr],label=f'step{step}')
 axes[0].plot(range(29),[x['Persistence_relative_RMS']*100 for x in rr],ls='--',color='k',label='Persistence');axes[1].semilogy(range(29),[x['Persistence_RMSE'] for x in rr],ls='--',color='k',label='Persistence');axes[1].set_yscale('log');axes[0].set(ylabel='Relative RMS [%]');axes[1].set(ylabel='RMSE [kg/m3]');[a.set_xlabel('Native ilev index (not fixed altitude)') for a in axes];[a.legend() for a in axes];fig.suptitle('All29 layers retained, fixed2021 pair');save(fig,'03_fixed_layer_100_200.png')
 fig,axes=plt.subplots(1,4,figsize=(17,4));arrays=[truth[24],pers[24],fixed[0,24],fixed[-1,24]];vmin=min(x.min() for x in arrays);vmax=max(x.max() for x in arrays)
 for ax,a,title in zip(axes,arrays,['TIE-GCM label','Persistence','Restored step100','Resumed step200']):
  im=ax.pcolormesh(lon,lat,a,shading='auto',vmin=vmin,vmax=vmax);ax.set(title=title,xlabel='Longitude [deg]',ylabel='Latitude [deg]');fig.colorbar(im,ax=ax,label='DEN [kg/m3]')
 fig.suptitle('Frozen native ilev24,2021-03-23 01 UTC, shared physical color scale');save(fig,'04_fixed_density_100_200.png')
 fig,axes=plt.subplots(1,2,figsize=(12,4));axes[0].plot(steps6,[s['nonpositive_count'] for s in snaps],marker='o');axes[0].set(xlabel='Measured checkpoint step',ylabel='Nonpositive DEN count');twin=axes[0].twinx();twin.plot(steps6,[s['positive_fraction']*100 for s in snaps],color='C1',ls='--');twin.set_ylabel('Positive density [%]',color='C1');axes[1].plot([r['step'] for r in newrows],[r['gradient_l2_before_clip'] for r in newrows]);axes[1].axhline(1.,ls='--',color='k',label='Frozen clip threshold1');axes[1].set(xlabel='Actual new cumulative update',ylabel='Pre-clip gradient L2');axes[1].legend();fig.suptitle('No invented intermediate physical checks; clipping from101--200 logs');save(fig,'05_positivity_and_clipping.png')
 fig,axes=plt.subplots(1,2,figsize=(12,4));ix=np.arange(3);rr=[next(x for x in valcomp if x['region']=='global' and x['group']==group) for group in groups]
 for off,key,label in [(-.25,'step100','v5 historical100'),(0,'step200','v6 final200'),(.25,'Persistence','Persistence')]:axes[0].bar(ix+off,[x[key+'_relative_RMS']*100 for x in rr],.25,label=label)
 axes[0].set_xticks(ix,groups);axes[0].set(ylabel='Relative RMS [%]');layers=sorted([x for x in valcomp if x['region']=='global' and x['group'].startswith('level_')],key=lambda x:x['group'])
 for key,label in [('step100','v5 historical100'),('step200','v6 final200'),('Persistence','Persistence')]:axes[1].plot(range(29),[x[key+'_relative_RMS']*100 for x in layers],label=label)
 axes[1].set(xlabel='Native ilev index',ylabel='Relative RMS [%]');[a.legend(fontsize=8) for a in axes];fig.suptitle('2022-03-23 01 to03-25 00 UTC,48 pairs, final-only dev validation NOT blind');save(fig,'06_2022_step100_step200_Persistence.png')
 fig,axes=plt.subplots(1,3,figsize=(13,4));axes[0].plot([x['step'] for x in newrows],[x['wall_s'] for x in newrows]);axes[0].set(xlabel='New cumulative step',ylabel='Update compute wall [s]');ss=status['samples'];axes[1].plot([x['wall_s'] for x in ss],[x.get('GPU_process_bytes',0)/2**30 for x in ss]);axes[1].set(xlabel='Supervised wall [s]',ylabel='Sampled GPU process [GiB]');axes[2].bar(['Load100','Updates','Fixed eval','Save/restore','Final val','Save arrays'],[g['initial_restore_s'],g['pure_update_wall_s'],g['fixed_evaluation_s'],g['save_restore_s'],g['validation_s'],g['save_metrics_s']]);axes[2].tick_params(axis='x',rotation=45);axes[2].set(ylabel='Measured component wall [s]');fig.suptitle('New100 updates only; CPU finalization timing separate');save(fig,'07_new_training_resources.png')
 old100=oldgpu['fixed_snapshots'][-1];last=g['fixed_snapshots'][-1];fixedall=lambda s:next(x['relative_RMS'] for x in s['global_metrics'] if x['group']=='all');learning=dict(loss100=old100['normalized_loss'],loss200=last['normalized_loss'],fixed_relative_RMS100=fixedall(old100),fixed_relative_RMS200=fixedall(last),relative_RMS_reduction_percent=100*(1-fixedall(last)/fixedall(old100)),new_loss_increases=sum(b['loss']>a['loss'] for a,b in zip(newrows,newrows[1:])),new_adjacent_comparisons=99,clipped_updates=sum(x['gradient_clipped'] for x in newrows),last20_mean_preupdate_loss=float(np.mean([x['loss'] for x in newrows[-20:]])),last20_min_preupdate_loss=min(x['loss'] for x in newrows[-20:]),last20_max_preupdate_loss=max(x['loss'] for x in newrows[-20:]),fixed_step200_layers_beating_Persistence=[x['group'] for x in comparison if x['step']==200 and x['region']=='global' and x['group'].startswith('level_') and x['AI_relative_RMS']<x['Persistence_relative_RMS']],validation_nonpositive_by_ilev=(pred<=0).sum((0,2,3)).tolist())
 dump(F/'learning_summary.json',learning);dump(F/'final_audit.json',dict(PASS=True,additional_updates=100,cumulative_step200=True,config_max100_preserved=True,source_restore_gate_PASS=True,new_fixed_physical_and_normalized_metrics_recomputed=True,historical0_100_not_rerun=True,old_v5_validation_readonly=True,independent_validation_metrics_PASS=True,Persistence48_pairs_recomputed_exact=True,final_checkpoint_SHA_verified=True,protected_assets_verified=len(protected),old_assets_unchanged=True,wall_s=time.perf_counter()-tick,CPU_peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,science_training_ready=False))
 print(json.dumps(dict(PASS=True,learning=learning,validation_global=rr,postprocess_s=time.perf_counter()-tick),indent=2))
if __name__=='__main__':main()
