"""CPU-only independent physical audit and plots. No additional model forwards."""
from pathlib import Path
import sys,json,csv,time,resource
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from train_den_multisample_v7 import F,O,sha,dump
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from training.den_engineering import evaluate_fields
from persistence_den_engineering_v3 import csvout,aggregate
from finalize_den_continuation_v6 import log_pair

def read(p):return list(csv.DictReader(p.open()))
def choose(rows,group='all',region='global',**kw):return next(r for r in rows if r['group']==group and r['region']==region and all(str(r[k])==str(v) for k,v in kw.items()))
def save(fig,name):
 fig.text(.5,.012,'TIE-GCM B14 2021 train / 2022 dev | DEN-only ENGINEERING / HINDCAST | 200 updates; not scientific qualification',ha='center',fontsize=7)
 fig.tight_layout(rect=(0,.045,1,.94));fig.savefig(O/name,dpi=160);plt.close(fig)
def main():
 start=time.perf_counter();g=json.loads((F/'GPU_result.json').read_text());plan=json.loads((F/'plan.json').read_text());status=json.loads((F/'gpu_job/status.json').read_text());assert json.loads((F/'engineering_gate.json').read_text())['PASS'] and g['model_forwards']==321 and g['optimizer_updates']==200 and status['returncode']==0
 protected=json.loads((F/'protected_inputs.json').read_text())
 for p,h in protected.items():assert sha(ROOT/p)==h,p
 assert sha(F/'step200.pt')==g['checkpoint_SHA256'];frames=json.loads((ROOT/'experiments/fourcastden_den_engineering_v3/dataset_manifest.json').read_text())['frames'];lat=np.asarray(plan['training_config']['latitude_deg']);lon=np.load(ROOT/'data/processed/static/lon.npy');w=np.broadcast_to(np.cos(np.deg2rad(lat))[None,:,None],(29,36,72));w=w/w.sum()
 rows=[json.loads(x) for x in (F/'updates.jsonl').read_text().splitlines()];assert [r['step'] for r in rows]==list(range(1,201)) and [r['pair_index'] for r in rows]==plan['train_order'];assert all(r['head_parameter_delta_l2']>0 and r['nonDEN_head_parameters_exact'] and r['finite_nonzero_gradient_tensors']==148 for r in rows)
 summaries={};hourlies={};persist={};pairedlog=[];independent=[];validity=[];comparisons=[];display=None
 for year,n in [(2021,72),(2022,48)]:
  hourly=read(O/f'AI_{year}_hourly.csv');summary=read(O/f'AI_{year}_summary.csv');hourlies[year]=hourly;summaries[year]=summary;pp=[]
  with np.load(O/f'AI_{year}_predictions_local.npz') as z:pred=z['prediction_kg_m3'];times=z['target_UTC'];assert pred.shape==(n,29,36,72) and list(times)==[x['UTC'] for x in frames[str(year)][1:]]
  for i,a in enumerate(pred):
   with np.load(ROOT/frames[str(year)][i]['path']) as z:p=z['DEN'].astype(float)*1000
   with np.load(ROOT/frames[str(year)][i+1]['path']) as z:t=z['DEN'].astype(float)*1000;zg=z['ZG'].astype(float)*.01
   assert np.isfinite(a).all() and (t>0).all() and (p>0).all();delta=a-t;r=dict(year=year,pair=i,RMSE=float(np.sqrt(np.sum(w*delta**2))),relative_RMS=float(np.sqrt(np.sum(w*(delta/t)**2))),bias=float(np.sum(w*delta)))
   logged=choose(hourly,pair=i)
   for k in ['RMSE','relative_RMS','bias']:np.testing.assert_allclose(r[k],float(logged[k]),rtol=1e-12,atol=1e-25)
   independent.append(r)
   for x in evaluate_fields(p,t,lat,zg):pp.append(dict(year=year,pair=i,**x))
   for group,lev in [('all',np.arange(29)),('upper20_28',np.arange(20,29)),('top28',np.array([28]))]:pairedlog.append(dict(year=year,pair=i,group=group,**log_pair(a[lev],p[lev],t[lev],lat)))
   if year==2022 and i==0:display=(t[24],p[24],a[24])
  persistence=aggregate(pp);persist[year]=persistence
  old=read(ROOT/f'results/fourcastden_den_engineering_v3/persistence_{year}_summary.csv')
  for r in persistence:
   reference=choose(old,r['group'],r['region'])
   for k in ['RMSE','relative_RMS','bias','log_RMS']:np.testing.assert_allclose(r[k],float(reference[k]),rtol=1e-12,atol=1e-25)
  csvout(O/f'Persistence_{year}_summary.csv',persistence)
  for r in summary:
   p=choose(persistence,r['group'],r['region']);assert int(r['grid_samples'])==p['grid_samples']
   comparisons.append(dict(year=year,group=r['group'],region=r['region'],pairs=n,grid_samples=p['grid_samples'],AI_relative_RMS=float(r['relative_RMS']),Persistence_relative_RMS=p['relative_RMS'],AI_RMSE=float(r['RMSE']),Persistence_RMSE=p['RMSE'],AI_bias=float(r['bias']),Persistence_bias=p['bias'],AI_positive_fraction=float(r['positive_fraction']),AI_log_RMS=float(r['log_RMS']) if r['log_RMS'] else None,AI_log_coverage=float(r['log_coverage'])))
  for lev in range(29):validity.append(dict(year=year,ilev=lev,nonpositive=int((pred[:,lev]<=0).sum()),total=int(pred[:,lev].size),positive_fraction=float((pred[:,lev]>0).mean()),finite_fraction=float(np.isfinite(pred[:,lev]).mean()),log_coverage=float((pred[:,lev]>0).mean())))
 csvout(O/'independent_array_metrics.csv',independent);csvout(O/'matched_positive_log.csv',pairedlog);csvout(O/'physical_validity_by_layer.csv',validity);csvout(O/'AI_vs_Persistence.csv',comparisons)
 v6out=ROOT/'results/fourcastden_den_overfit_continuation_v6';v6fixed=read(v6out/'combined_fixed_AI_vs_Persistence.csv');v6val=read(v6out/'validation_summary.csv');controlled=[];groups=['all','upper20_28','top28']
 for group in groups:
  old=choose(v6fixed,group,step=200);new=choose(hourlies[2021],group,pair=0);p=float(old['Persistence_relative_RMS'])
  controlled.append(dict(domain='first2021pair',group=group,v6_relative_RMS=float(old['AI_relative_RMS']),v7_relative_RMS=float(new['relative_RMS']),Persistence_relative_RMS=p))
  controlled.append(dict(domain='2022_all48',group=group,v6_relative_RMS=float(choose(v6val,group)['relative_RMS']),v7_relative_RMS=float(choose(summaries[2022],group)['relative_RMS']),Persistence_relative_RMS=choose(persist[2022],group)['relative_RMS']))
 csvout(O/'controlled_v6_v7_comparison.csv',controlled)
 visits=[]
 for i in range(72):
  rr=[r for r in rows if r['pair_index']==i];visits.append(dict(pair_index=i,exposures=len(rr),first_preupdate_loss=rr[0]['loss'],last_preupdate_loss=rr[-1]['loss'],last_below_first=rr[-1]['loss']<rr[0]['loss']))
 csvout(O/'same_pair_visit_loss.csv',visits)
 fig,axes=plt.subplots(2,1,figsize=(11,6),sharex=True);loss=np.array([r['loss'] for r in rows]);trend=np.full(200,np.nan);trend[23:]=np.convolve(loss,np.ones(24)/24,'valid');axes[0].semilogy(range(1,201),loss,label='Actual pre-update loss, varying pairs',alpha=.65);axes[0].semilogy(range(1,201),trend,label='Frozen trailing24 descriptive mean');axes[0].set(ylabel='Normalized DEN MSE');axes[0].legend();axes[1].plot(range(1,201),plan['train_order']);axes[1].set(xlabel='Actual optimizer update',ylabel='Pair index');[a.axvline(k,color='grey',ls='--') for a in axes for k in [72,144]];fig.suptitle('2021 Mar23--26: cyclic72 pairs,200 updates, fresh seed20261113');save(fig,'01_training_loss_and_order.png')
 fig,ax=plt.subplots(figsize=(11,4))
 for method,rr in [('AFNONet',hourlies[2021]),('Persistence',read(ROOT/'results/fourcastden_den_engineering_v3/persistence_2021_hourly.csv'))]:
  selected=sorted([r for r in rr if r['group']=='all' and r['region']=='global'],key=lambda r:int(r['pair']));ax.plot(range(72),[float(r['relative_RMS'])*100 for r in selected],label=method)
 ax.set(xlabel='All72 training pair indices (target Mar23 01--Mar26 00 UTC)',ylabel='Relative RMS [%]',title='Final step200, no sample selection');ax.legend();save(fig,'02_all72_training_pairs.png')
 fig,axes=plt.subplots(1,2,figsize=(11,4));ix=np.arange(3)
 for ax,year in zip(axes,[2021,2022]):
  for off,key,label in [(-.18,'AI_relative_RMS','AFNONet200'),(.18,'Persistence_relative_RMS','Persistence')]:ax.bar(ix+off,[choose(comparisons,group,year=year)[key]*100 for group in groups],.36,label=label)
  ax.set_xticks(ix,groups);ax.set(ylabel='Relative RMS [%]',title=f'{year} all{72 if year==2021 else 48} pairs');ax.legend()
 save(fig,'03_train_development_validation.png')
 fig,ax=plt.subplots(figsize=(9,4));rr=[r for r in controlled if r['domain']=='first2021pair']
 for off,key,label in [(-.25,'v6_relative_RMS','v6 single-pair200 (history)'),(0,'v7_relative_RMS','v7 cyclic72-pair200'),(.25,'Persistence_relative_RMS','Persistence')]:ax.bar(ix+off,[r[key]*100 for r in rr],.25,label=label)
 ax.set_xticks(ix,groups);ax.set(ylabel='Relative RMS [%]',title='Same first2021pair: Mar23 00->01 UTC');ax.legend();save(fig,'04_v6_v7_first_pair.png')
 fig,ax=plt.subplots(figsize=(10,4))
 for year in [2021,2022]:
  for key,label,style in [('AI_relative_RMS','AFNONet','-'),('Persistence_relative_RMS','Persistence','--')]:ax.plot(range(29),[choose(comparisons,f'level_{i:02d}',year=year)[key]*100 for i in range(29)],style,label=f'{year} {label}')
 ax.set(xlabel='Native ilev index, not fixed geometric altitude',ylabel='Relative RMS [%]',title='All29 native levels retained');ax.legend();save(fig,'05_layer_relative_RMS.png')
 fig,axes=plt.subplots(1,3,figsize=(14,4));vmin=min(a.min() for a in display);vmax=max(a.max() for a in display)
 for ax,a,title in zip(axes,display,['TIE-GCM target','Persistence','AFNONet step200']):
  im=ax.pcolormesh(lon,lat,a,shading='auto',vmin=vmin,vmax=vmax);ax.set(title=title,xlabel='Longitude [deg]',ylabel='Latitude [deg]');fig.colorbar(im,ax=ax,label='DEN [kg/m3]')
 fig.suptitle('Frozen2022 dev pair0, Mar23 01 UTC, native ilev24, common color scale');save(fig,'06_fixed_validation_pair0_ilev24.png')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for year in [2021,2022]:
  rr=[r for r in validity if r['year']==year];axes[0].plot(range(29),[r['nonpositive'] for r in rr],label=str(year));axes[1].plot(range(29),[r['positive_fraction']*100 for r in rr],label=f'{year} positive / log domain')
 axes[0].set(ylabel='Actual nonpositive density count');axes[1].set(ylabel='Physical positive/log coverage [%]');[a.set_xlabel('Native ilev index') for a in axes];[a.legend() for a in axes];fig.suptitle('Ordinary physical errors retain all finite predictions; no clipping');save(fig,'07_physical_validity.png')
 fig,axes=plt.subplots(1,3,figsize=(14,4));axes[0].plot(range(1,201),[r['wall_s'] for r in rows]);axes[0].set(xlabel='Optimizer update',ylabel='Actual update wall [s]');ss=status['samples'];axes[1].plot([r['wall_s'] for r in ss],[r.get('GPU_process_bytes',0)/2**30 for r in ss],label='Process sample');axes[1].plot([r['wall_s'] for r in ss],[(r.get('rss_bytes') or 0)/2**30 for r in ss],label='CPU tree RSS');axes[1].set(xlabel='Supervised wall [s]',ylabel='GiB');axes[1].legend();axes[2].bar(['CPU cache','Build','200 updates','Eval72','Eval48','Save/restore','Save arrays'],[g['cache_setup_s'],g['construction_s'],g['pure_update_wall_s'],g['evaluation_times']['train_evaluation'],g['evaluation_times']['validation'],g['save_restore_s'],g['save_outputs_s']]);axes[2].tick_params(axis='x',rotation=60);axes[2].set(ylabel='Measured component wall [s]');save(fig,'08_actual_training_resources.png')
 learning=dict(pairs_first_last_loss_improved=sum(r['last_below_first'] for r in visits),pairs_total=72,first_visit_mean_loss=float(np.mean([r['first_preupdate_loss'] for r in visits])),last_visit_mean_loss=float(np.mean([r['last_preupdate_loss'] for r in visits])),first_visit_is_not_full_initial_model_evaluation=True,clipped_updates=sum(r['gradient_clipped'] for r in rows),unused_parameters=rows[0].get('unused_parameters'),mean_update_s=g['pure_update_wall_s']/200,training_layers_better_than_Persistence=[i for i in range(29) if choose(comparisons,f'level_{i:02d}',year=2021)['AI_relative_RMS']<choose(comparisons,f'level_{i:02d}',year=2021)['Persistence_relative_RMS']],validation_layers_better_than_Persistence=[i for i in range(29) if choose(comparisons,f'level_{i:02d}',year=2022)['AI_relative_RMS']<choose(comparisons,f'level_{i:02d}',year=2022)['Persistence_relative_RMS']],train_pairs_better_than_Persistence=sum(float(choose(hourlies[2021],pair=i)['relative_RMS'])<float(choose(read(ROOT/'results/fourcastden_den_engineering_v3/persistence_2021_hourly.csv'),pair=i)['relative_RMS']) for i in range(72)))
 dump(F/'learning_summary.json',learning);dump(F/'final_audit.json',dict(PASS=True,actual_updates=200,actual_model_forwards=321,protected_assets_verified=len(protected),old_assets_unchanged=True,checkpoint_SHA_verified=True,independent_physical_metrics_120_pairs_PASS=True,Persistence120_pairs_recomputed_exact=True,model_initialization_exact=True,v6_model_not_loaded=True,v6_full72_metrics='NOT_AVAILABLE; no extra inference',science_training_ready=False,CPU_postprocess_wall_s=time.perf_counter()-start,CPU_peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
 print(json.dumps(dict(PASS=True,learning=learning,main=[r for r in comparisons if r['group'] in groups and r['region']=='global'],controlled=controlled),indent=2))
if __name__=='__main__':main()
