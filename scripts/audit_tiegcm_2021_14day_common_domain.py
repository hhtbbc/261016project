"""Four-way same-height valid-domain check; avoids changing spatial samples in 7/14 comparison."""
from pathlib import Path
import sys,json
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from audit_tiegcm_2021_14day_acceptance import index,record,C,O,helper

def main():
 folders=[R/'experiments/tiegcm_training_mar23_v2_2021_longrun',R/'experiments/tiegcm_2021_spinup_initial_condition_v1/B',C/'A14',C/'B14'];idx=[index(p) for p in folders];heights=[200,300,400,450,475,500];store={h:[[] for _ in folders] for h in heights};times=np.arange(82*86400,85*86400+1,3600)
 for t in times:
  frames=[record(*x[t]) for x in idx]
  for h in heights:
   for j,f in enumerate(frames):store[h][j].append(helper.legacy.a3.at_height(f['ZG'],f['DEN'],h*1000))
 lat=frames[0]['lat'];rules=json.loads((C/'frozen_comparison_rules.json').read_text());regions={k:(lat>=v[0])&(lat<=v[1]) for k,v in rules['latitude_regions'].items()};periods={'candidate':times>=82*86400,'last24h':times>=84*86400,'endpoint':times==85*86400};rows=[]
 for h,v in store.items():
  v=[np.stack(q) for q in v];good=np.logical_and.reduce([np.isfinite(q) for q in v])
  for period,tm in periods.items():
   for region,sel in regions.items():
    gg=good[tm][:,sel,:];w=np.broadcast_to(np.cos(np.deg2rad(lat[sel]))[None,:,None],gg.shape)[gg];metrics={}
    for label,i,j in [('seven',0,1),('fourteen',2,3)]:
     a=v[i][tm][:,sel,:][gg];b=v[j][tm][:,sel,:][gg]
     if len(a):d=abs(b/a-1);metrics.update({label+'_relative_P95':helper.legacy.percentile(d,w,.95),label+'_absolute_RMSE':float(np.sqrt(np.average((b-a)**2,weights=w)))})
     else:metrics.update({label+'_relative_P95':None,label+'_absolute_RMSE':None})
    rows.append({'height_km':h,'period':period,'region':region,'four_way_common_coverage':float(gg.mean()),'n':int(gg.sum()),**metrics})
 helper.csvout(O/'four_way_common_height_domain.csv',rows);print('Four-way domain comparison completed')
if __name__=='__main__':main()
