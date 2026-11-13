"""Read-only physical audit, v7/v8 comparison and9 figures. No model inference."""
from pathlib import Path
import sys,json,csv,time,resource
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from train_den_multisample_v8 import F,O,sha,dump
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from training.den_engineering import evaluate_fields,load_statistics,pairs,DEN_INDICES
from persistence_den_engineering_v3 import csvout,aggregate
from finalize_den_continuation_v6 import log_pair
OLD=ROOT/'results/fourcastden_den_multisample_v7';OLD_F=ROOT/'experiments/fourcastden_den_multisample_v7'
def read(p):return list(csv.DictReader(p.open()))
def choose(rows,group='all',region='global',**kw):return next(r for r in rows if r['group']==group and r['region']==region and all(str(r[k])==str(v) for k,v in kw.items()))
def save(fig,name):
 fig.text(.5,.012,'TIE-GCM B14 | 2021 train / 2022 dev NOT blind | DEN-only ENGINEERING / HINDCAST | v7 historical200 + v8 resumed720',ha='center',fontsize=7)
 fig.tight_layout(rect=(0,.045,1,.94));fig.savefig(O/name,dpi=160);plt.close(fig)
def main():
 start=time.perf_counter();g=json.loads((F/'GPU_result.json').read_text());plan=json.loads((F/'plan.json').read_text());status=json.loads((F/'gpu_job/status.json').read_text());assert json.loads((F/'engineering_gate.json').read_text())['PASS'] and g['model_forwards']==642 and g['optimizer_updates']==520 and g['cumulative_step']==720 and status['returncode']==0
 protected=json.loads((F/'protected_inputs.json').read_text())
 for p,h in protected.items():assert sha(ROOT/p)==h,p
 assert sha(F/'step720.pt')==g['checkpoint_SHA256'];assert json.loads((F/'initial_restore_gate.json').read_text())['DEN_array_bitwise_exact']
 frames=json.loads((ROOT/'experiments/fourcastden_den_engineering_v3/dataset_manifest.json').read_text())['frames'];lat=np.asarray(plan['training_config']['latitude_deg']);lon=np.load(ROOT/'data/processed/static/lon.npy');w=np.broadcast_to(np.cos(np.deg2rad(lat))[None,:,None],(29,36,72));w=w/w.sum();norm=load_statistics();latw=np.cos(np.deg2rad(lat))[None,:,None];latw/=latw.mean()
 history=[dict(source='v7_history_readonly',**json.loads(x)) for x in (OLD_F/'updates.jsonl').read_text().splitlines()];new=[dict(source='v8_new_update',**json.loads(x)) for x in (F/'updates.jsonl').read_text().splitlines()];rows=history+new
 assert [r['step'] for r in new]==list(range(201,721)) and [r['new_update'] for r in new]==list(range(1,521)) and all(r['model_training'] for r in new);assert [r['step'] for r in rows]==list(range(1,721)) and [r['pair_index'] for r in rows]==[i%72 for i in range(720)]
 assert all(r['head_parameter_delta_l2']>0 and r['nonDEN_head_parameters_exact'] and r['finite_nonzero_gradient_tensors']==148 for r in new);csvout(O/'combined_training_updates_1_720.csv',rows)
 matrix=np.array([r['loss'] for r in rows]).reshape(10,72);epochrows=[]
 for epoch,a in enumerate(matrix,1):epochrows.append(dict(traversal=epoch,start_step=72*(epoch-1)+1,end_step=72*epoch,preupdate_loss_mean=float(a.mean()),preupdate_loss_median=float(np.median(a)),preupdate_loss_min=float(a.min()),preupdate_loss_max=float(a.max()),model_weights_vary_within_traversal=True))
 csvout(O/'complete72_visit_descriptions.csv',epochrows);csvout(O/'pair10_visits_loss.csv',[dict(pair_index=i,visit=j+1,step=j*72+i+1,preupdate_loss=float(matrix[j,i])) for j in range(10) for i in range(72)]);csvout(O/'cumulative_exposures.csv',[dict(pair_index=i,visits=10,actual_visits=sum(r['pair_index']==i for r in rows)) for i in range(72)])
 summaries={};hourlies={};persist={};comp=[];pairedlog=[];independent=[];validity=[];layerloss=[];display=None;globalcheck=0
 for year,n in [(2021,72),(2022,48)]:
  hourly=read(O/f'AI_{year}_hourly.csv');summary=read(O/f'AI_{year}_summary.csv');oldsummary=read(OLD/f'AI_{year}_summary.csv');hourlies[year]=hourly;summaries[year]=summary;pp=[];recomputed=[];nloss=[];dataset=pairs(year)
  with np.load(O/f'AI_{year}_predictions_local.npz') as z:pred=z['prediction_kg_m3'];times=z['target_UTC'];assert pred.shape==(n,29,36,72) and list(times)==[x['UTC'] for x in frames[str(year)][1:]]
  for i,a in enumerate(pred):
   with np.load(ROOT/frames[str(year)][i]['path']) as z:p=z['DEN'].astype(float)*1000
   with np.load(ROOT/frames[str(year)][i+1]['path']) as z:t=z['DEN'].astype(float)*1000;zg=z['ZG'].astype(float)*.01
   assert np.isfinite(a).all() and (t>0).all() and (p>0).all();delta=a-t;r=dict(year=year,pair=i,RMSE=float(np.sqrt(np.sum(w*delta**2))),relative_RMS=float(np.sqrt(np.sum(w*(delta/t)**2))),bias=float(np.sum(w*delta)))
   logged=choose(hourly,pair=i)
   for k in ['RMSE','relative_RMS','bias']:np.testing.assert_allclose(r[k],float(logged[k]),rtol=1e-12,atol=1e-25)
   globalcheck+=1;independent.append(r)
   for x in evaluate_fields(p,t,lat,zg):pp.append(dict(year=year,pair=i,**x))
   for x in evaluate_fields(a,t,lat,zg):recomputed.append(dict(year=year,pair=i,**x))
   enc=(a/1000-norm.means[DEN_INDICES])/norm.stds[DEN_INDICES];target=dataset[i][2][DEN_INDICES.tolist()].numpy().astype(float);nloss.append((((enc-target)**2)*latw).mean((1,2)))
   for group,lev in [('all',np.arange(29)),('upper20_28',np.arange(20,29)),('top28',np.array([28]))]:pairedlog.append(dict(year=year,pair=i,group=group,**log_pair(a[lev],p[lev],t[lev],lat)))
   if year==2022 and i==0:display=(t[24],p[24],a[24])
  persistence=aggregate(pp);persist[year]=persistence;oldpersist=read(ROOT/f'results/fourcastden_den_engineering_v3/persistence_{year}_summary.csv')
  for result,reference in [(aggregate(recomputed),summary),(persistence,oldpersist)]:
   for r in result:
    ref=choose(reference,r['group'],r['region'])
    for k in ['RMSE','relative_RMS','bias','log_RMS','positive_fraction','log_coverage']:np.testing.assert_allclose(r[k] if r[k] is not None else np.nan,float(ref[k]) if ref[k] else np.nan,rtol=1e-12,atol=1e-25,equal_nan=True)
  nl=np.mean(nloss,axis=0);np.testing.assert_allclose(nl.mean(),g['train_normalized_loss' if year==2021 else 'validation_normalized_loss'],rtol=2e-6,atol=1e-9)
  layerloss += [dict(year=year,ilev=i,normalized_weighted_MSE=float(v)) for i,v in enumerate(nl)];csvout(O/f'Persistence_{year}_summary.csv',persistence)
  for r in summary:
   p=choose(persistence,r['group'],r['region']);old=choose(oldsummary,r['group'],r['region']);assert int(r['grid_samples'])==p['grid_samples']==int(old['grid_samples'])
   comp.append(dict(year=year,group=r['group'],region=r['region'],pairs=n,grid_samples=p['grid_samples'],v7_relative_RMS=float(old['relative_RMS']),v8_relative_RMS=float(r['relative_RMS']),Persistence_relative_RMS=p['relative_RMS'],relative_RMS_reduction_percent=100*(1-float(r['relative_RMS'])/float(old['relative_RMS'])),v8_to_Persistence_ratio=float(r['relative_RMS'])/p['relative_RMS'],v7_RMSE=float(old['RMSE']),v8_RMSE=float(r['RMSE']),Persistence_RMSE=p['RMSE'],v8_bias=float(r['bias']),Persistence_bias=p['bias'],v8_positive_fraction=float(r['positive_fraction']),v8_log_RMS=float(r['log_RMS']) if r['log_RMS'] else None,v8_log_coverage=float(r['log_coverage'])))
  regions={'global':np.ones(len(lat),bool),'south_high':lat<=-60,'north_high':lat>=60,'midlow':abs(lat)<60}
  for lev in range(29):
   for region,mask in regions.items():
    a=pred[:,lev,mask,:];validity.append(dict(year=year,ilev=lev,region=region,nonpositive=int((a<=0).sum()),total=int(a.size),positive_fraction=float((a>0).mean()),finite_fraction=float(np.isfinite(a).mean()),log_coverage=float((a>0).mean())))
 csvout(O/'v7_v8_Persistence.csv',comp);csvout(O/'independent_array_metrics.csv',independent);csvout(O/'matched_positive_log.csv',pairedlog);csvout(O/'physical_validity_by_layer_region.csv',validity);csvout(O/'normalized_layer_MSE.csv',layerloss)
 groups=['all','upper20_28','top28'];fig,axes=plt.subplots(1,2,figsize=(13,4))
 for rr,label in [(history,'v7 actual1--200, readonly'),(new,'v8 resumed201--720')]:axes[0].semilogy([r['step'] for r in rr],[r['loss'] for r in rr],label=label,alpha=.7)
 for epoch in range(1,11):axes[0].axvline(epoch*72,color='grey',lw=.5,alpha=.4)
 axes[0].legend(fontsize=8);axes[0].set(xlabel='Actual cumulative optimizer step',ylabel='Pre-update normalized DEN loss');axes[1].plot(range(1,11),matrix.mean(1),marker='o');axes[1].set_yscale('log');axes[1].set(xlabel='Complete72-visit traversal (varying weights)',ylabel='Descriptive mean pre-update loss');fig.suptitle('Varying training pairs: adjacent losses are not a fixed-sample convergence test');save(fig,'01_loss_1_720.png')
 fig,axes=plt.subplots(1,2,figsize=(13,4));im=axes[0].imshow(np.log10(matrix),aspect='auto',origin='lower',extent=[-.5,71.5,.5,10.5]);fig.colorbar(im,ax=axes[0],label='log10 pre-update normalized loss');axes[0].set(xlabel='Frozen training pair index',ylabel='Visit number');axes[1].plot(range(1,11),matrix,alpha=.2,color='C0');axes[1].plot(range(1,11),np.median(matrix,axis=1),color='k',marker='o',label='Across-pair median');axes[1].set_yscale('log');axes[1].set(xlabel='Same pair visit number',ylabel='Pre-update normalized loss');axes[1].legend();save(fig,'02_pair10_visit_losses.png')
 for year,num in [(2021,3),(2022,4)]:
  fig,ax=plt.subplots(figsize=(9,4));ix=np.arange(3)
  for off,key,label in [(-.25,'v7_relative_RMS','v7 historical200'),(0,'v8_relative_RMS','v8 final720'),(.25,'Persistence_relative_RMS','Persistence')]:ax.bar(ix+off,[choose(comp,group,year=year)[key]*100 for group in groups],.25,label=label)
  ax.set_xticks(ix,groups);ax.set(ylabel='Physical relative RMS [%]',title=f'{year} all{72 if year==2021 else 48} pairs, '+('training' if year==2021 else 'development, NOT blind'));ax.legend();save(fig,f'0{num}_{year}_v7_v8_Persistence.png')
 fig,axes=plt.subplots(1,2,figsize=(13,4))
 for ax,year in zip(axes,[2021,2022]):
  for key,label,ls in [('v7_relative_RMS','v7 historical200',':'),('v8_relative_RMS','v8 final720','-'),('Persistence_relative_RMS','Persistence','--')]:ax.plot(range(29),[choose(comp,f'level_{i:02d}',year=year)[key]*100 for i in range(29)],ls,label=label)
  ax.set(xlabel='Native ilev index (not fixed altitude)',ylabel='Relative RMS [%]',title=str(year));ax.legend()
 save(fig,'05_all29_layer_errors.png')
 fig,ax=plt.subplots(figsize=(11,4));oldhours=read(OLD/'AI_2021_hourly.csv');phours=read(ROOT/'results/fourcastden_den_engineering_v3/persistence_2021_hourly.csv')
 for rr,label in [(oldhours,'v7 historical200'),(hourlies[2021],'v8 final720'),(phours,'Persistence')]:ax.plot(range(72),[float(choose(rr,pair=i)['relative_RMS'])*100 for i in range(72)],label=label)
 ax.set(xlabel='All72 training pair indices; target Mar23 01--Mar26 00 UTC',ylabel='Relative RMS [%]');ax.legend();save(fig,'06_all72_training_pair_errors.png')
 fig,axes=plt.subplots(1,3,figsize=(14,4));lo=min(a.min() for a in display);hi=max(a.max() for a in display)
 for ax,a,title in zip(axes,display,['TIE-GCM DEN label','Persistence','AFNONet step720']):
  im=ax.pcolormesh(lon,lat,a,shading='auto',vmin=lo,vmax=hi);ax.set(title=title,xlabel='Longitude [deg]',ylabel='Latitude [deg]');fig.colorbar(im,ax=ax,label='DEN [kg/m3]')
 fig.suptitle('Pre-fixed2022 dev pair0, Mar23 01 UTC, native ilev24, shared physical color scale');save(fig,'07_fixed2022_pair0_ilev24.png')
 fig,axes=plt.subplots(1,2,figsize=(13,4))
 for year in [2021,2022]:
  for region,ls in [('global','-'),('north_high','--'),('south_high',':')]:
   rr=[r for r in validity if r['year']==year and r['region']==region];axes[0].plot(range(29),[r['nonpositive'] for r in rr],ls,label=f'{year} {region}');axes[1].plot(range(29),[r['positive_fraction']*100 for r in rr],ls,label=f'{year} {region}')
 axes[0].set(ylabel='Actual nonpositive prediction count');axes[1].set(ylabel='Physical positive/log coverage [%]');[a.set_xlabel('Native ilev index') for a in axes];axes[0].legend(fontsize=7);fig.suptitle('All finite predictions retained in ordinary metrics; no clipping/filtering');save(fig,'08_physical_validity.png')
 fig,axes=plt.subplots(1,3,figsize=(14,4));axes[0].plot([r['step'] for r in new],[r['wall_s'] for r in new]);axes[0].set(xlabel='New cumulative updates201--720',ylabel='Actual update wall [s]');ss=status['samples'];axes[1].plot([r['wall_s'] for r in ss],[r.get('GPU_process_bytes',0)/2**30 for r in ss],label='Process GPU sample');axes[1].plot([r['wall_s'] for r in ss],[(r.get('rss_bytes') or 0)/2**30 for r in ss],label='CPU tree RSS');axes[1].set(xlabel='Supervised wall [s]',ylabel='GiB');axes[1].legend();axes[2].bar(['Cache','Restore200','520 updates','Eval72','Eval48','Save/restore','Save arrays'],[g['cache_setup_s'],g['initial_restore_s'],g['pure_update_wall_s'],g['evaluation_times']['train_evaluation'],g['evaluation_times']['validation'],g['save_restore_s'],g['save_outputs_s']]);axes[2].tick_params(axis='x',rotation=60);axes[2].set(ylabel='Measured component wall [s]');save(fig,'09_actual_training_resources.png')
 learning=dict(pair_last_visit_loss_below_visit3=int((matrix[-1]<matrix[2]).sum()),pair_visit10_below_visit9=int((matrix[-1]<matrix[-2]).sum()),all10_epoch_descriptions=epochrows,clipped_new_updates=sum(r['gradient_clipped'] for r in new),gradient_L2_min=min(r['gradient_l2_before_clip'] for r in new),gradient_L2_max=max(r['gradient_l2_before_clip'] for r in new),last72_preupdate_loss_mean=float(matrix[-1].mean()),last72_preupdate_loss_min=float(matrix[-1].min()),last72_preupdate_loss_max=float(matrix[-1].max()),last72_mean_reduction_vs_previous_percent=100*(1-matrix[-1].mean()/matrix[-2].mean()),training_layers_better_than_Persistence=[i for i in range(29) if choose(comp,f'level_{i:02d}',year=2021)['v8_relative_RMS']<choose(comp,f'level_{i:02d}',year=2021)['Persistence_relative_RMS']],development_layers_better_than_Persistence=[i for i in range(29) if choose(comp,f'level_{i:02d}',year=2022)['v8_relative_RMS']<choose(comp,f'level_{i:02d}',year=2022)['Persistence_relative_RMS']],train_pairs_better_than_Persistence=sum(float(choose(hourlies[2021],pair=i)['relative_RMS'])<float(choose(phours,pair=i)['relative_RMS']) for i in range(72)))
 dump(F/'learning_summary.json',learning);dump(F/'final_audit.json',dict(PASS=True,new_updates=520,cumulative_updates=720,actual_model_forwards=642,protected_assets_verified=len(protected),old_assets_unchanged=True,checkpoint_SHA_verified=True,independent_physical_global_metrics_pairs=globalcheck,all_layer_region_AI_metrics_recomputed=True,Persistence120_pairs_recomputed_exact=True,normalized_layer_loss_audit_PASS=True,source_model_mode_and_RNG_audit_PASS=True,config_max200_preserved=True,uninterrupted720_bitwise_equivalence='NOT_TESTED',science_training_ready=False,CPU_postprocess_wall_s=time.perf_counter()-start,CPU_peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
 print(json.dumps(dict(PASS=True,learning=learning,main=[r for r in comp if r['group'] in groups and r['region']=='global']),indent=2))
if __name__=='__main__':main()
