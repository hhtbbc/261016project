"""CPU-only completed-job verification, fair persistence and actual research figures."""
from pathlib import Path
import sys,json,csv,time,resource
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from train_den_gpu_smoke_v4 import F,O,sha,dump
from training.den_engineering import evaluate_fields
from persistence_den_engineering_v3 import csvout,aggregate

def readcsv(p):return list(csv.DictReader(p.open()))
def save(fig,name):
 fig.text(.5,.012,'TIE-GCM B14 labels | HINDCAST / DEN-only engineering | random AFNONet, 10 updates',ha='center',fontsize=8);fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(O/name,dpi=160);plt.close(fig)
def main():
 start=time.perf_counter();assert json.loads((F/'engineering_gate.json').read_text())['PASS'];gpu=json.loads((F/'GPU_result.json').read_text());status=json.loads((F/'gpu_job/status.json').read_text());assert gpu['optimizer_updates']==10 and gpu['validation_pairs']==48 and status['returncode']==0
 for n,h in json.loads((F/'protected_inputs.json').read_text()).items():assert sha(ROOT/n)==h,n
 assert gpu['checkpoint_restore']['PASS'] and gpu['validation_model_and_optimizer_exact']
 for n,h in gpu['checkpoints_SHA256'].items():assert sha(F/n)==h
 m=json.loads((ROOT/'experiments/fourcastden_den_engineering_v3/dataset_manifest.json').read_text())['frames']['2022'];lat=np.load(ROOT/'data/processed/static/lat.npy');lon=np.load(ROOT/'data/processed/static/lon.npy')
 with np.load(O/'AI_validation_local.npz') as n:pred=n['prediction_kg_m3'];times=n['target_UTC'];assert pred.shape==(48,29,36,72) and np.isfinite(pred).all();assert list(times)==[r['UTC'] for r in m[1:]]
 # Fairness: retain every target time, layer, latitude and invalid/nonpositive prediction.
 pp=[];independent=[];matched_log=[];w=np.broadcast_to(np.cos(np.deg2rad(lat))[None,:,None],(29,36,72));w=w/w.sum()
 perhour=readcsv(O/'AI_validation_hourly.csv')
 for i in range(48):
  with np.load(ROOT/m[i]['path']) as n:p=n['DEN'].astype(float)*1000
  with np.load(ROOT/m[i+1]['path']) as n:t=n['DEN'].astype(float)*1000;zg=n['ZG'].astype(float)*.01
  for r in evaluate_fields(p,t,lat,zg):pp.append(dict(year=2022,pair=i,target_UTC=m[i+1]['UTC'],method='Persistence',**r))
  # Independent all-layer direct physical errors from the saved float32 output.
  # Log is undefined for nonpositive AI: compare BOTH methods on the same
  # disclosed positive-AI subset, without altering ordinary all-point metrics.
  for group,levels in [('all',np.arange(29)),('upper20_28',np.arange(20,29)),('top28',np.array([28]))]:
   ap=pred[i,levels].astype(float);tt=t[levels];ppp=p[levels];ok=ap>0;ww=np.broadcast_to(np.cos(np.deg2rad(lat))[None,:,None],ap.shape)
   matched_log.append(dict(pair=i,group=group,positive_points=int(ok.sum()),all_points=int(ok.size),coverage=float(ok.mean()),AI_log_RMS=float(np.sqrt(np.average(np.log(ap[ok]/tt[ok])**2,weights=ww[ok]))) if ok.any() else None,Persistence_log_RMS=float(np.sqrt(np.average(np.log(ppp[ok]/tt[ok])**2,weights=ww[ok]))) if ok.any() else None))
  d=pred[i].astype(float)-t
  actual=dict(RMSE=float(np.sqrt(np.sum(w*d*d))),relative_RMS=float(np.sqrt(np.sum(w*(d/t)**2))),bias=float(np.sum(w*d)))
  old=next(x for x in perhour if int(x['pair'])==i and x['group']=='all' and x['region']=='global')
  for k,v in actual.items():np.testing.assert_allclose(v,float(old[k]),rtol=5e-6,atol=1e-20)
  independent.append(dict(pair=i,**actual))
 persist=aggregate(pp);old=readcsv(ROOT/'results/fourcastden_den_engineering_v3/persistence_2022_summary.csv')
 for x in persist:
  y=next(z for z in old if z['group']==x['group'] and z['region']==x['region'])
  for k in ['RMSE','relative_RMS','bias','log_RMS','positive_fraction','coverage']:np.testing.assert_allclose(x[k],float(y[k]),rtol=1e-12,atol=1e-25)
 csvout(O/'matched_positive_log_hourly.csv',matched_log);csvout(O/'Persistence_validation_summary.csv',persist);csvout(O/'independent_AI_all_layer_metrics.csv',independent)
 ai=readcsv(O/'AI_validation_summary.csv');comparison=[]
 for x in ai:
  y=next(z for z in persist if z['group']==x['group'] and z['region']==x['region'])
  assert int(x['hourly_pairs'])==y['hourly_pairs'] and int(x['grid_samples'])==y['grid_samples']
  comparison.append(dict(group=x['group'],region=x['region'],hourly_pairs=y['hourly_pairs'],grid_samples=y['grid_samples'],AI_RMSE=float(x['RMSE']),Persistence_RMSE=y['RMSE'],AI_relative_RMS=float(x['relative_RMS']),Persistence_relative_RMS=y['relative_RMS'],AI_bias=float(x['bias']),Persistence_bias=y['bias'],AI_log_RMS=float(x['log_RMS']) if x['log_RMS'] else None,Persistence_log_RMS=y['log_RMS'],AI_positive_fraction=float(x['positive_fraction']),AI_log_coverage=float(x['log_coverage']),finite_coverage=float(x['coverage'])))
 csvout(O/'AI_vs_Persistence.csv',comparison);rows=gpu['records'];csvout(O/'training_updates.csv',rows)
 steps=[r['step'] for r in rows]
 fig,ax=plt.subplots(figsize=(8,4));ax.plot(steps,[r['loss'] for r in rows],marker='o');ax.set(xlabel='Actual optimizer update',ylabel='Normalized DEN29 weighted MSE',title='2021-03-23 01:00-10:00 UTC targets; consecutive training pairs');ax.set_xticks(steps);save(fig,'01_actual_training_loss.png')
 fig,axes=plt.subplots(1,2,figsize=(11,4));axes[0].bar(['2021 fixed pair\nbefore','2021 fixed pair\nafter','2022 48 pairs\nafter'],[gpu['initial_fixed_train_loss'],gpu['final_fixed_train_loss'],gpu['validation_normalized_loss']]);axes[0].set(ylabel='Normalized DEN29 weighted MSE',title='Different samples; not a generalization estimate')
 select=[x for x in comparison if x['region']=='global' and x['group'] in ['all','upper20_28','top28']];xx=np.arange(len(select));axes[1].bar(xx-.18,[x['AI_relative_RMS']*100 for x in select],width=.36,label='AI10 updates');axes[1].bar(xx+.18,[x['Persistence_relative_RMS']*100 for x in select],width=.36,label='Persistence');axes[1].set_xticks(xx,[x['group'] for x in select]);axes[1].set(ylabel='Physical relative RMS [%]',title='2022 full48 independent validation pairs');axes[1].legend();save(fig,'02_training_validation_separate_metrics.png')
 levels=[x for x in comparison if x['region']=='global' and x['group'].startswith('level_')];levels.sort(key=lambda x:x['group']);fig,axes=plt.subplots(1,2,figsize=(11,4))
 for key,label in [('AI','AI10 updates'),('Persistence','Persistence')]:
  axes[0].plot(range(29),[x[key+'_relative_RMS']*100 for x in levels],label=label);axes[1].semilogy(range(29),[x[key+'_RMSE'] for x in levels],label=label)
 axes[0].axvspan(20,28,alpha=.1,color='grey');axes[0].set(ylabel='Relative RMS [%]');axes[1].set(ylabel='RMSE [kg/m3]');[a.set_xlabel('Native ilev index (not fixed altitude)') for a in axes];[a.legend() for a in axes];fig.suptitle('2022-03-23 01 UTC to03-25 00 UTC,48 pairs, all retained');save(fig,'03_AI_persistence_by_layer.png')
 with np.load(ROOT/m[0]['path']) as n:p=n['DEN'][24].astype(float)*1000
 with np.load(ROOT/m[1]['path']) as n:t=n['DEN'][24].astype(float)*1000
 a=pred[0,24];vmin=min(t.min(),p.min(),a.min());vmax=max(t.max(),p.max(),a.max());fig,axes=plt.subplots(1,3,figsize=(14,4))
 for ax,data,title in zip(axes,[t,p,a],['TIE-GCM target t+1','Persistence','AFNONet after10 updates']):
  im=ax.pcolormesh(lon,lat,data,shading='auto',vmin=vmin,vmax=vmax);ax.set(title=title,xlabel='Longitude [deg]',ylabel='Latitude [deg]');fig.colorbar(im,ax=ax,label='DEN [kg/m3]')
 fig.suptitle('Frozen display:2022-03-23 00->01 UTC, native ilev24, no selection by skill');save(fig,'04_frozen_real_DEN_prediction.png')
 fig,axes=plt.subplots(1,3,figsize=(13,4));axes[0].plot(steps,[r['wall_s'] for r in rows],marker='o');axes[0].set(xlabel='Actual update',ylabel='Train update wall [s]');axes[1].plot(steps,[r['peak_allocated_bytes']/2**30 for r in rows],label='Allocator peak');samples=status['samples'];axes[2].plot([x['wall_s'] for x in samples],[x.get('GPU_process_bytes',0)/2**30 for x in samples]);axes[1].set(xlabel='Actual update',ylabel='Allocated [GiB]');axes[2].set(xlabel='Supervised wall [s]',ylabel='Sampled process GPU [GiB]');fig.suptitle('Measured resource records;10 actual optimizer updates');save(fig,'05_GPU_resources.png')
 dump(F/'final_audit.json',dict(PASS=True,v3_data_and_statistics_unchanged=True,protected_input_files=len(json.loads((F/'protected_inputs.json').read_text())),checkpoint_SHA_verified=True,independent_AI_metrics_PASS=True,independent_AI_metric_float32_serialization_rtol=5e-6,persistence_recomputed_48_pairs_exact=True,same_validation_times_and_samples=True,nonpositive_predictions=gpu['nonpositive_predictions'],nonfinite_predictions=gpu['nonfinite_predictions'],wall_s=time.perf_counter()-start,CPU_peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,science_training_ready=False))
 print(json.dumps(dict(PASS=True,global_comparisons=select,wall_s=time.perf_counter()-start),indent=2))
if __name__=='__main__':main()
