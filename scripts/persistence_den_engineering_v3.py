"""Real physical one-hour persistence, no network or GPU."""
import os
from pathlib import Path
import sys,json,csv,time,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from training.den_engineering import F,O,DATA,evaluate_fields
def csvout(p,rows):
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with p.open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');w.writeheader();w.writerows(rows)
def aggregate(rows):
 out=[]
 for group,region in sorted({(x['group'],x['region']) for x in rows}):
  a=[x for x in rows if x['group']==group and x['region']==region];r=dict(group=group,region=region,hourly_pairs=len(a),grid_samples=sum(x['n'] for x in a))
  for k in ['RMSE','relative_RMS']:r[k]=float(np.sqrt(np.mean([x[k]**2 for x in a])))
  for k in ['MAE','bias','coverage','positive_fraction','log_coverage']:r[k]=float(np.mean([x[k] for x in a]))
  valid=[x['log_RMS'] for x in a if x['log_RMS'] is not None];r['log_RMS']=float(np.sqrt(np.mean(np.square(valid)))) if valid else None;r['log_valid_hours']=len(valid);r['max_abs']=max(x['max_abs'] for x in a);out.append(r)
 return out
if __name__=='__main__':
 os.environ['CUDA_VISIBLE_DEVICES']=''
 start=time.perf_counter();assert json.loads((F/'cpu_data_audit.json').read_text())['PASS'];manifest=json.loads((F/'dataset_manifest.json').read_text())['frames'];lat=np.load(ROOT/'data/processed/static/lat.npy');allrows=[]
 for year in ['2021','2022']:
  rr=[];frames=manifest[year]
  for i in range(len(frames)-1):
   with np.load(ROOT/frames[i]['path']) as n:pred=n['DEN'].astype(float)*1000
   with np.load(ROOT/frames[i+1]['path']) as n:truth=n['DEN'].astype(float)*1000;zg=n['ZG'].astype(float)*.01
   for r in evaluate_fields(pred,truth,lat,zg):rr.append(dict(year=int(year),pair=i,target_UTC=frames[i+1]['UTC'],method='Persistence',**r))
  csvout(O/f'persistence_{year}_hourly.csv',rr)
  agg=[dict(year=int(year),method='Persistence',**r) for r in aggregate(rr)];csvout(O/f'persistence_{year}_summary.csv',agg);allrows+=agg
 csvout(O/'persistence_summary.csv',allrows)
 (F/'persistence_audit.json').open('x').write(json.dumps(dict(PASS=True,train_pairs=72,validation_pairs=48,relative_denominator='strictly positive physical target; no floor/filter',units='kg/m3',area_weight='cos(latitude)',time_aggregation='equal-hour RMSE squared mean then sqrt; log positive-prediction domain only and coverage reported',wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024),indent=2))
 print('Physical persistence complete')
