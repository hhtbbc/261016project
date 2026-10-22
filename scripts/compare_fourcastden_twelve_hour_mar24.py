"""Two-window offline comparison: saved Jan4 is read-only, zero network forwards."""
import json,csv,sys
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_fourcastden_multistep import dump,sha
from run_fourcastden_twelve_hour_mar24 import F,MODELS
TAG='fourcastden_twelve_hour_mar24_v1_two_window'
def write(name,rows):
 with (ROOT/f'results/metrics/{TAG}_{name}.csv').open('x') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def save(fig,name):
 fig.suptitle('Jan4 / Mar24: official four-model continuous 12h, 01 UTC initialization\nHINDCAST / TIEGCM_REFERENCE_ONLY / native pressure levels / NOT a causal geomagnetic experiment',fontsize=9);fig.tight_layout(rect=[0,0,1,.91]);p=ROOT/f'results/figures/{TAG}_{name}.png';assert not p.exists();fig.savefig(p,dpi=150);plt.close(fig)
def main():
 jan=ROOT/'experiments/fourcastden_twelve_hour_jan4_v1';a=json.loads((F/'analysis.json').read_text());j=json.loads((jan/'analysis.json').read_text());old=json.loads((ROOT/'experiments/fourcastden_six_hour_v1/analysis.json').read_text());assert a['status']==j['status']=='PASS'
 prefix=[]
 for m in MODELS:
  for h in range(1,7):
   for n in ['TN','UN','VN','WN','Z','DEN']:
    x=next(x for x in a['summary'] if x['model']==m and x['hour']==h and x['variable']==n);y=next(x for x in old['summary'] if x['date']=='2023-03-24' and x['model']==m and x['hour']==h and x['variable']==n);assert x==y
   x=next(x for x in a['windows'] if x['model']==m and x['hour']==h);y=next(x for x in old['windows'] if x['date']=='2023-03-24' and x['model']==m and x['hour']==h);assert all(x[k]==v for k,v in y.items());prefix.append(dict(model=m,hour=h,all_old_metrics_exact=True))
 dump(F/'prefix_metrics_gate.json',dict(status='PASS',records=prefix))
 windows=j['windows']+a['windows'];summary=j['summary']+a['summary'];write('windows',windows);write('summary',summary)
 dates=('2023-01-04','2023-03-24');colors=dict(Direct='tab:blue',Flow='tab:orange',LogDEN='tab:green',History='tab:purple')
 def win(d,m,h):return next(x for x in windows if x['date']==d and x['model']==m and x['hour']==h)
 growth=[]
 for d in dates:
  for m in MODELS:
   for key in ['near400_500_mean_relative_RMS','mean_DEN_layer_RMSE_kg_m3','upper20_28_mean_relative_RMS']:
    first=win(d,m,1)[key];six=win(d,m,6)[key];last=win(d,m,12)[key];values=[win(d,m,h)[key] for h in range(1,13)]
    growth.append(dict(date=d,model=m,metric=key,value_1h=first,value_6h=six,value_12h=last,ratio_12_to_1=last/first,ratio_12_to_6=last/six,absolute_increment_12_minus_1=last-first,absolute_increment_12_minus_6=last-six,maximum=max(values),peak_lead_hour=1+int(np.argmax(values)),decreasing_steps=int((np.diff(values)<0).sum())))
 write('growth',growth)
 polar=[]
 for date,tag in zip(dates,['fourcastden_twelve_hour_jan4_v1','fourcastden_twelve_hour_mar24_v1']):
  with (ROOT/f'results/metrics/{tag}_density_layers.csv').open() as f:rr=list(csv.DictReader(f))
  for m in MODELS:
   for h in range(1,13):
    r=[x for x in rr if x['model']==m and int(x['hour'])==h and x['region']=='polar' and 20<=int(x['ilev_index'])<=28]
    polar.append(dict(date=date,model=m,hour=h,polar_upper20_28_mean_relative_RMS=np.mean([float(x['relative_RMS']) for x in r]),polar_upper20_28_max_relative_error=max(float(x['relative_max']) for x in r)))
 write('polar',polar)
 perf=[]
 for date,folder in zip(dates,[jan,F]):
  rt=json.loads((folder/'runtime.json').read_text());analysis=j if date==dates[0] else a
  for r in rt['records']:
   row=next(x for x in analysis['performance'] if x['model']==r['model']).copy();row['physical_decode_hook_s']=r.get('physical_decode_hook_s','N/A, not separately timed');row['model_checkpoint_SHA256']=r['checkpoint_sha256'];perf.append(row)
 write('performance',perf)
 drivers=[]
 for tag in ['fourcastden_twelve_hour_jan4_v1','fourcastden_twelve_hour_mar24_v1']:
  with (ROOT/f'results/metrics/{tag}_drivers.csv').open() as f:drivers.extend(list(csv.DictReader(f)))
 write('drivers',drivers)
 for key,factor,unit,suffix in [('near400_500_mean_relative_RMS',100,'Mean layer relative RMS (%)','high_DEN'),('mean_DEN_layer_RMSE_kg_m3',1,'Mean layer RMSE (kg/m3)','absolute_DEN'),('upper20_28_mean_relative_RMS',100,'Fixed upper20-28 relative RMS (%)','fixed_upper')]:
  fig,axes=plt.subplots(1,2,figsize=(12,4))
  for d,ax in zip(dates,axes):
   for m in MODELS:ax.plot(range(1,13),[win(d,m,h)[key]*factor for h in range(1,13)],'o-',label=m,color=colors[m])
   ax.set(title=d,xlabel='Lead (h)',ylabel=unit);ax.legend()
  save(fig,suffix)
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for d,ax in zip(dates,axes):
  x=np.arange(4)
  for delta,h in [(-.18,6),(.18,12)]:ax.bar(x+delta,[win(d,m,h)['near400_500_mean_relative_RMS']*100 for m in MODELS],width=.36,label=f'+{h}h')
  ax.set(xticks=x,xticklabels=MODELS,ylabel='Near-group relative RMS (%)',title=d);ax.legend()
 save(fig,'6_vs_12')
 fig,axes=plt.subplots(2,2,figsize=(12,8))
 for row,d in enumerate(dates):
  for col,key,label in [(0,'ratio_12_to_1','12h / 1h'),(1,'absolute_increment_12_minus_1','12h minus 1h (percentage points)')]:
   ax=axes[row,col];r=[x for x in growth if x['date']==d and x['metric']=='near400_500_mean_relative_RMS'];ax.bar(MODELS,[x[key]*(100 if col else 1) for x in r]);ax.set(title=d,ylabel=label)
 save(fig,'growth_absolute_and_ratio')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for d,ax in zip(dates,axes):
  for m in MODELS:ax.plot(range(1,13),[next(x['polar_upper20_28_mean_relative_RMS'] for x in polar if x['date']==d and x['model']==m and x['hour']==h)*100 for h in range(1,13)],label=m,color=colors[m])
  ax.set(title=d,xlabel='Lead (h)',ylabel='Polar fixed upper20-28 relative RMS (%)');ax.legend()
 save(fig,'polar')
 fig,axes=plt.subplots(2,3,figsize=(14,8))
 for ax,n in zip(axes.flat,['TN','UN','VN','WN','Z','DEN']):
  rr=[x for x in summary if x['variable']==n]
  for d in dates:
   for m in MODELS:ax.plot(range(1,13),[next(x['mean_layer_RMSE_SI'] for x in rr if x['date']==d and x['model']==m and x['hour']==h) for h in range(1,13)],'-' if d==dates[0] else '--',color=colors[m],label=m+' '+d[5:])
  ax.set(title=n,xlabel='Lead (h)',ylabel=rr[0]['SI_unit'],yscale='log');ax.legend(fontsize=6)
 save(fig,'variables')
 fig,axes=plt.subplots(1,3,figsize=(14,4));labels=[x['date'][5:]+' '+x['model'] for x in perf]
 for ax,key,title,div in [(axes[0],'network_total_GPU_ms','12 network forwards (ms; cold state differs)',1),(axes[1],'author_loop_metrics_hooks_s','Author loop incl metrics / IO / hooks (s)',1),(axes[2],'peak_allocated_bytes','CUDA allocated peak (MiB)',2**20)]:
  ax.bar(range(8),[x[key]/div for x in perf]);ax.set(xticks=range(8),xticklabels=labels,title=title);ax.tick_params(axis='x',rotation=70,labelsize=7)
 save(fig,'performance')
 dump(F/'two_window_comparison.json',dict(status='PASS',jan4_analysis_SHA256=sha(jan/'analysis.json'),mar24_analysis_SHA256=sha(F/'analysis.json'),growth=growth,polar=polar,performance=perf,drivers=drivers,windows=windows,summary=summary,old_metrics_exact=True))
 print('Two-window offline comparison PASS; Jan4 not rerun')
if __name__=='__main__':main()
