"""Two years x two starts x two warmups, exact 49-frame/shared height domains."""
from pathlib import Path
import sys,json,time
import numpy as np
from netCDF4 import Dataset
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from audit_tiegcm_2021_14day_acceptance import index
import compare_tiegcm_2021_initial_conditions as h
from prepare_fourcastden_swarm_observation_v1 import sha,dump
TAG='tiegcm_2022_spinup_14day_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG
CASES={2021:[ROOT/'experiments/tiegcm_training_mar23_v2_2021_longrun',ROOT/'experiments/tiegcm_2021_spinup_initial_condition_v1/B',ROOT/'experiments/tiegcm_2021_spinup_14day_v1/A14',ROOT/'experiments/tiegcm_2021_spinup_14day_v1/B14'],2022:[ROOT/'experiments/tiegcm_training_mar23_v2_2022_longrun',ROOT/'experiments/tiegcm_2022_dual_initial_spinup_v1',F/'A14',F/'B14']}

def main():
    started=time.perf_counter();heights=[200,300,400,450,475,500];arrays=np.full((2,6,4,49,36,72),np.nan);protected={}
    for yi,(year,folders) in enumerate(CASES.items()):
        for gi,folder in enumerate(folders):
            ix=index(folder);audit=json.loads((folder/'data_audit.json').read_text())
            for e in audit['files']:
                if e['file'].startswith('secondary') and any('-03-23' in t or '-03-24' in t or '-03-25T00:00' in t for t in e['UTC']):assert sha(folder/e['file'])==e['SHA256'];protected[str((folder/e['file']).relative_to(ROOT))]=e['SHA256']
            for ti,t in enumerate(range(82*86400,84*86400+1,3600)):
                p,i=ix[t]
                with Dataset(p) as n:
                    assert int(n['year'][i])==year;z=np.asarray(n['ZG'][i],float)*.01;rho=np.asarray(n['DEN'][i],float)*1000;lat=np.array(n['lat'][:]);lon=np.array(n['lon'][:])
                    assert np.isfinite(z).all() and np.isfinite(rho).all() and (rho>0).all() and (np.diff(z,axis=0)>0).all()
                for hi,height in enumerate(heights):arrays[yi,hi,gi,ti]=h.legacy.a3.at_height(z,rho,height*1000)
    rules=json.loads((F/'frozen_comparison_rules.json').read_text());regions={k:(lat>=v[0])&(lat<=v[1]) for k,v in rules['latitude_regions'].items()};w=np.cos(np.deg2rad(lat))[:,None];rows=[];masks=[]
    for yi,year in enumerate(CASES):
        for hi,height in enumerate(heights):
            peryear=np.isfinite(arrays[yi,hi]).all(axis=0);allyears=np.isfinite(arrays[:,hi]).all(axis=(0,1))
            for scheme,(ia,ib) in {'7day':(0,1),'14day':(2,3)}.items():
                x,y=arrays[yi,hi,ib],arrays[yi,hi,ia];pair=np.isfinite(x)&np.isfinite(y)
                for domain,mask in [('own_pair',pair),('within_year_four_common',peryear),('cross_year_eight_common',allyears)]:
                    xx=np.where(mask,x,np.nan);yy=np.where(mask,y,np.nan)
                    for period,tm in [('candidate',np.ones(49,bool)),('last24h',np.arange(49)>=24),('endpoint',np.arange(49)==48)]:
                        for region,ls in regions.items():rows.append(dict(year=year,scheme=scheme,height_km=height,domain=domain,period=period,region=region,**h.metrics(xx[tm][:,ls,:],yy[tm][:,ls,:],w[ls],.05,True,0,True)))
                masks.append(dict(year=year,scheme=scheme,height_km=height,own_pair_fraction=float(pair.mean()),within_year_four_fraction=float(peryear.mean()),cross_year_eight_fraction=float(allyears.mean())))
    h.csvout(O/'joint_height_summary.csv',rows);h.csvout(O/'height_domain_coverage.csv',masks)
    np.savez_compressed(O/'joint_heights_local.npz',values=arrays,heights_km=heights,lat=lat,lon=lon)
    dump(F/'joint_height_audit.json',dict(PASS=True,protected_files=protected,matched_window='each year Mar23 00-Mar25 00:49 frames',common_domain='within-year four-way main; cross-year eight-way spatial/time-slot diagnostic, not same actual UTC',wall_s=time.perf_counter()-started))
    # Reuse already-computed 2021/2022 seven-day matched native diagnostics.
    import csv
    prior=ROOT/'results/tiegcm_2022_dual_initial_spinup_v1';summary=[];gates=[]
    for filename,target in [('joint_native_matched.csv',summary),('joint_native_matched_gates.csv',gates)]:
        with (prior/filename).open() as f:target.extend(csv.DictReader(f))
    with (O/'delta14/native_summary.csv').open() as f:
        for r in csv.DictReader(f):
            if r['variable'] in ['DEN','TN','WIND_VECTOR','O1','O2','N2','HE']:
                summary.append(dict(r,case='2022_14day',period={'candidate':'matched_candidate49','last24h':'matched_last24h','endpoint':'matched_endpoint'}[r['period']]))
    q=json.loads((O/'delta14/summary.json').read_text())
    for period,vs in q['gates'].items():
        for var,g in vs.items():
            if var.startswith('ZG_'):continue
            gates.append(dict(case='2022_14day',variable=var,period={'candidate':'matched_candidate49','last24h':'matched_last24h','endpoint':'matched_endpoint'}[period],evaluated_cells=g['evaluated_time_level_region_cells'],failed_cells=g['failed_cells'],worst_fraction=g['worst_fraction'],PASS=g['passed']))
    h.csvout(O/'joint_native_summary.csv',summary);h.csvout(O/'joint_native_gates.csv',gates)
    print('Joint four-way and eight-way domains completed')
if __name__=='__main__':main()
