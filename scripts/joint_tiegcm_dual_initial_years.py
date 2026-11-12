"""Compare matched target dates/window lengths at native ZG, without model launches."""
from pathlib import Path
import sys,json,time
import numpy as np
from netCDF4 import Dataset
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from audit_tiegcm_2021_14day_acceptance import index,record
import compare_tiegcm_2021_initial_conditions as h
from prepare_fourcastden_swarm_observation_v1 import sha,dump
TAG='tiegcm_2022_dual_initial_spinup_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG

def main():
    started=time.perf_counter();rows=[];hourly=[];verified={}
    cases={'2021_7day':(ROOT/'experiments/tiegcm_training_mar23_v2_2021_longrun',ROOT/'experiments/tiegcm_2021_spinup_initial_condition_v1/B'),'2021_14day':(ROOT/'experiments/tiegcm_2021_spinup_14day_v1/A14',ROOT/'experiments/tiegcm_2021_spinup_14day_v1/B14'),'2022_7day':(ROOT/'experiments/tiegcm_training_mar23_v2_2022_longrun',F)}
    rules=json.loads((F/'frozen_comparison_rules.json').read_text())
    for case,(ap,bp) in cases.items():
        ia,ib=index(ap),index(bp);aa={height:[] for height in rules['common_native_ZG_heights_km']};bb={height:[] for height in aa}
        for folder in [ap,bp]:
            audit=json.loads((folder/'data_audit.json').read_text())
            for e in audit['files']:
                if e['file'].startswith('secondary') and any('-03-23' in t or '-03-24' in t or '-03-25T00:00' in t for t in e['UTC']):assert sha(folder/e['file'])==e['SHA256'];verified[str((folder/e['file']).relative_to(ROOT))]=e['SHA256']
        for t in range(82*86400,84*86400+1,3600):
            a,b=record(*ia[t]),record(*ib[t]);lat=a['lat'];weight=np.cos(np.deg2rad(lat))[:,None]
            for height in aa:
                x=h.legacy.a3.at_height(a['ZG'],a['DEN'],height*1000);y=h.legacy.a3.at_height(b['ZG'],b['DEN'],height*1000);aa[height].append(x);bb[height].append(y)
                hourly.append(dict(case=case,height_km=height,time_doy_seconds=t,hours_since_Mar23=(t-82*86400)/3600,**h.metrics(y,x,weight,.05,True,0,True)))
        for height in aa:
            x,y=np.array(aa[height]),np.array(bb[height])
            for period,sel in [('matched_49h_frames',np.ones(49,bool)),('matched_last24h',np.arange(49)>=24),('matched_endpoint',np.arange(49)==48)]:
                for region,lim in rules['latitude_regions'].items():
                    ls=(lat>=lim[0])&(lat<=lim[1]);rows.append(dict(case=case,height_km=height,period=period,region=region,**h.metrics(y[sel][:,ls,:],x[sel][:,ls,:],weight[ls],.05,True,0,True)))
    h.csvout(O/'joint_matched_native_ZG.csv',rows);h.csvout(O/'joint_matched_native_ZG_hourly.csv',hourly)
    dump(F/'joint_audit.json',dict(verified_files=verified,matched_window='each year March23 00 to March25 00;49 hourlyframes',no_original_results_modified=True,wall_s=time.perf_counter()-started))
if __name__=='__main__':main()
