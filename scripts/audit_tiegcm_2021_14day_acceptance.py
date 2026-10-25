"""Stream same-epoch records into per-level/region acceptance matrices for all three periods."""
from pathlib import Path
import sys,json,csv,importlib.util
import numpy as np
from netCDF4 import Dataset
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import compare_tiegcm_2021_initial_conditions as helper
C=R/'experiments/tiegcm_2021_spinup_14day_v1';O=R/'results/tiegcm_2021_spinup_14day_v1'
def index(folder):
 out={}
 for p in sorted(folder.glob('secondary_*.nc')):
  with Dataset(p) as n:
   for i,v in enumerate(n['mtime'][:]):
    t=int(v[0])*86400+int(v[1])*3600+int(v[2])*60;assert t not in out;out[t]=(p,i)
 return out
def record(p,i):
 with Dataset(p) as n:
  n.set_auto_mask(False);z={}
  for k in ['DEN','ZG','TN','UN','VN','O1','O2','N2','HE']:
   v=np.asarray(n[k][i],float);assert np.isfinite(v).all();v[abs(v)>1e30]=np.nan;z[k]=v*{'DEN':1000,'ZG':.01,'UN':.01,'VN':.01}.get(k,1)
  z['lat']=np.array(n['lat'][:]);return z

def main():
 rules=json.loads((C/'frozen_comparison_rules.json').read_text());rows=[]
 cases={'7day':(R/'experiments/tiegcm_training_mar23_v2_2021_longrun',R/'experiments/tiegcm_2021_spinup_initial_condition_v1/B'),'14day':(C/'A14',C/'B14')}
 for case,(ap,bp) in cases.items():
  ai=index(ap);bi=index(bp);acc={}
  for t in range(82*86400,85*86400+1,3600):
   a=record(*ai[t]);b=record(*bi[t]);lat=a['lat'];regions={k:(lat>=v[0])&(lat<=v[1]) for k,v in rules['latitude_regions'].items()};periods=['candidate']+(['last24h'] if t>=84*86400 else [])+(['endpoint'] if t==85*86400 else [])
   fields={k:(b[k],a[k],.05,True,1e-8 if k in ['O1','O2','N2','HE'] else 0) for k in ['DEN','O1','O2','N2','HE']};fields['TN']=(b['TN'],a['TN'],10,False,0);wind=np.hypot(b['UN']-a['UN'],b['VN']-a['VN']);fields['WIND_VECTOR']=(wind,np.zeros_like(wind),20,False,0)
   for h in rules['common_native_ZG_heights_km']:
    x=helper.legacy.a3.at_height(b['ZG'],b['DEN'],h*1000);y=helper.legacy.a3.at_height(a['ZG'],a['DEN'],h*1000);fields[f'ZG_{h}km']=(x[None],y[None],.05,True,0)
   for k,(x,y,limit,rel,floor) in fields.items():
    good=np.isfinite(x)&np.isfinite(y);e=abs(x-y)
    if rel:good&=abs(y)>floor;e=np.divide(e,abs(y),out=np.full_like(e,np.nan),where=good)
    for region,sel in regions.items():
     g=good[:,sel,:];n=g.sum(axis=(1,2));fractions=np.divide(((e[:,sel,:]<limit)&g).sum(axis=(1,2)),n,out=np.full(n.shape,np.nan),where=n>0);coverage=n/g.shape[1]/g.shape[2]
     for level in range(len(n)):
      for period in periods:
       key=(k,period,region,level);v=acc.setdefault(key,{'evaluated_hours':0,'failed_hours':0,'missing_hours':0,'minimum_fraction':1.,'maximum_fraction':0.,'coverage_min':1.,'coverage_max':0.});v['coverage_min']=min(v['coverage_min'],float(coverage[level]));v['coverage_max']=max(v['coverage_max'],float(coverage[level]))
       if not n[level]:v['missing_hours']+=1;continue
       f=float(fractions[level]);v['evaluated_hours']+=1;v['failed_hours']+=int(f<.95);v['minimum_fraction']=min(v['minimum_fraction'],f);v['maximum_fraction']=max(v['maximum_fraction'],f)
  for (variable,period,region,level),v in acc.items():rows.append({'case':case,'variable':variable,'period':period,'region':region,'native_level_or_single_height':level,**v,'PASS':v['evaluated_hours']>0 and v['failed_hours']==0})
 p=O/'acceptance_region_level_matrix.csv';helper.csvout(p,rows)
 summary={}
 for case in cases:
  summary[case]={}
  for period in ['candidate','last24h','endpoint']:
   summary[case][period]={}
   for k in sorted({r['variable'] for r in rows}):
    q=[r for r in rows if r['case']==case and r['period']==period and r['variable']==k and r['evaluated_hours']>0];summary[case][period][k]={'evaluated_time_level_region_cells':sum(r['evaluated_hours'] for r in q),'failed_cells':sum(r['failed_hours'] for r in q),'worst_fraction':min(r['minimum_fraction'] for r in q),'PASS':all(r['PASS'] for r in q)}
  previous=R/'results/tiegcm_2021_spinup_initial_condition_v1/comparison/summary.json' if case=='7day' else O/'delta14/summary.json';previous=json.loads(previous.read_text())
  for k,v in previous['strict_last24h_native_gates'].items():
   assert summary[case]['last24h'][k]['failed_cells']==v['failed_cells'];assert summary[case]['last24h'][k]['evaluated_time_level_region_cells']==v['evaluated_time_level_region_cells']
 (O/'acceptance_by_period.json').open('x').write(json.dumps(summary,indent=2)+'\n');print('Acceptance matrices PASS; old and new last24h gate counts independently reproduced')
if __name__=='__main__':main()
