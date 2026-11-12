"""Matched 49-frame native-variable comparison; all original trajectory files read only."""
from pathlib import Path
import sys,json,time,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from audit_tiegcm_2021_14day_acceptance import index,record
import compare_tiegcm_2021_initial_conditions as h
TAG='tiegcm_2022_dual_initial_spinup_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG

def main():
    started=time.perf_counter();rules=json.loads((F/'frozen_comparison_rules.json').read_text());rows=[];gates=[]
    cases={'2021_7day':(ROOT/'experiments/tiegcm_training_mar23_v2_2021_longrun',ROOT/'experiments/tiegcm_2021_spinup_initial_condition_v1/B'),'2021_14day':(ROOT/'experiments/tiegcm_2021_spinup_14day_v1/A14',ROOT/'experiments/tiegcm_2021_spinup_14day_v1/B14'),'2022_7day':(ROOT/'experiments/tiegcm_training_mar23_v2_2022_longrun',F)}
    names=['DEN','TN','O1','O2','N2','HE','WIND_VECTOR']
    for case,(ap,bp) in cases.items():
        ai,bi=index(ap),index(bp);xx={k:[] for k in names};yy={k:[] for k in names}
        for t in range(82*86400,84*86400+1,3600):
            a,b=record(*ai[t]),record(*bi[t]);lat=a['lat']
            for k in names:
                if k=='WIND_VECTOR':x=np.hypot(b['UN']-a['UN'],b['VN']-a['VN']);y=np.zeros_like(x)
                else:x,y=b[k],a[k]
                xx[k].append(x);yy[k].append(y)
        regions={k:(lat>=v[0])&(lat<=v[1]) for k,v in rules['latitude_regions'].items()};w=np.cos(np.deg2rad(lat))[None,:,None]
        for k in names:
            x,y=np.array(xx.pop(k)),np.array(yy.pop(k));relative=k not in ['TN','WIND_VECTOR'];limit=10 if k=='TN' else 20 if k=='WIND_VECTOR' else .05;floor=1e-8 if k in ['O1','O2','N2','HE'] else 0
            for period,mask in [('matched_candidate49',np.ones(49,bool)),('matched_last24h',np.arange(49)>=24),('matched_endpoint',np.arange(49)==48)]:
                for region,sel in regions.items():rows.append(dict(case=case,variable=k,period=period,region=region,**h.metrics(x[mask][:,:,sel,:],y[mask][:,:,sel,:],w[:,sel],limit,relative,floor,k=='DEN')))
                q=h.gate_cells(x,y,mask,regions,limit,relative,floor);gates.append(dict(case=case,variable=k,period=period,evaluated_cells=q['evaluated_time_level_region_cells'],failed_cells=q['failed_cells'],worst_fraction=q['worst_fraction'],PASS=q['passed']))
            del x,y
    h.csvout(O/'joint_native_matched.csv',rows);h.csvout(O/'joint_native_matched_gates.csv',gates)
    with (F/'joint_native_matched_runtime.json').open('x') as f:json.dump(dict(wall_s=time.perf_counter()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,matched_windows=True,metrics_and_gates_reused_unchanged=True),f,indent=2)
    print('Matched native variable comparison complete')
if __name__=='__main__':main()
