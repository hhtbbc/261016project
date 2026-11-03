"""Independent array/query/accounting audit, preserving numerical FAIL evidence."""
from pathlib import Path
import sys,csv,json,itertools,time,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_fourcastden_orbit_update_12h_v1 import F,O
from prepare_fourcastden_swarm_observation_v1 import sha,dump
from analyze_fourcastden_swarm_observation_v1 import table
from PIL import Image

def main():
    begin=time.perf_counter();p=json.loads((F/'protocol.json').read_text());old=json.loads((ROOT/'experiments/fourcastden_orbit_update_event_v1/protocol.json').read_text());analysis=json.loads((F/'analysis.json').read_text())
    for k in ['base','tight','aero','convergence']:assert p[k]==old[k]
    arrays={};queryrows=[]
    for mode in ['base','tight']:
        for g in p['groups']:
            with np.load(F/f'{g}_{mode}_states_local.npz') as n:
                arrays[g,mode]=n['states'];np.testing.assert_array_equal(n['left_end'],n['right_start']);np.testing.assert_array_equal(n['seconds'],np.arange(0,43201,60));assert n['states'].shape==(721,6)
            m=json.loads((F/f'{g}_{mode}_runtime.json').read_text());count=0;min_top=None;min_bottom=None;counts={'left':0,'right':0}
            if g!='A_NoDrag':
                with (F/f'{g}_{mode}_queries_local.csv').open() as file:
                    for r in csv.DictReader(file):
                        count+=1;counts[r['branch']]+=1;assert r['valid']=='True' and float(r['rho_kg_m3'])>0
                        lo,hi=map(float,[r['height_lower_m'],r['height_upper_m']]);h=float(r['assumed_native_ZG_m']);assert lo<=h<=hi
                        min_top=hi-h if min_top is None else min(min_top,hi-h);min_bottom=h-lo if min_bottom is None else min(min_bottom,h-lo)
                        a,b=r['time_bracket'].split(';')
                        if r['branch']=='left':assert a>='2023-01-04T01:00:00.000' and b<='2023-01-04T07:00:00.000' and r['UTC']<='2023-01-04T07:00:00.000'
                        else:assert a>='2023-01-04T07:00:00.000' and b<='2023-01-04T13:00:00.000' and r['UTC']>='2023-01-04T07:00:00.000'
                assert m['rhs_density_queries']==m['nfev']+2 and count==m['rhs_density_queries']+721+2
            else:assert m['all_density_queries']==m['rhs_density_queries']==0
            assert count==m['all_density_queries'];queryrows.append(dict(group=g,mode=mode,query_count=count,valid_count=count,left_count=counts['left'],right_count=counts['right'],min_top_margin_m=min_top,min_bottom_margin_m=min_bottom,no_cross_event_interpolation=True))
        np.testing.assert_array_equal(arrays['B_Open',mode][:361],arrays['C_Updated',mode][:361])
    check=[];numeric=[]
    for g in p['groups']:
        d=arrays[g,'base']-arrays[g,'tight'];err=float(np.sqrt(np.sum(d[:,:3]**2,axis=1)).max());passed=err<=.02;numeric.append(passed);check.append(dict(type='single',comparison=g,error_m=err,limit_m=.02,passed=passed))
    for g,h in itertools.combinations(p['groups'],2):
        a=arrays[g,'base']-arrays[h,'base'];b=arrays[g,'tight']-arrays[h,'tight'];err=float(np.sqrt(np.sum((a[:,:3]-b[:,:3])**2,axis=1)).max());response=float(np.sqrt(np.sum(b[:,:3]**2,axis=1)).max());passed=err<=.01*response;numeric.append(passed);check.append(dict(type='pair_vector',comparison=g+' minus '+h,error_m=err,limit_m=.01*response,passed=passed))
    assert (analysis['gates']['ORBIT_NUMERICAL_CONVERGENCE_READY']=='PASS')==all(numeric)
    manifest=json.loads((F/'protected_runtime_v2.json').read_text());assert all(sha(ROOT/p)==v for p,v in manifest.items())
    historical=json.loads((ROOT/'experiments/tiegcm_runtime_restart_audit_v1/protected_files.json').read_text());assert all(sha(ROOT/p)==v for p,v in historical.items())
    png=list(O.glob('*.png'));assert len(png)==8
    for path in png:
        with Image.open(path) as im:im.verify()
    table(O/'independent_query_accounting.csv',queryrows);table(O/'independent_numerical_check.csv',check)
    wall=time.perf_counter()-begin;budget=analysis['budget_compute_s']+wall;assert budget<10500
    dump(F/'independent_audit.json',dict(audit_status='PASS',numerical_status='PASS' if all(numeric) else 'FAIL_RETAINED',single_PASS=sum(numeric[:4]),paired_PASS=sum(numeric[4:]),all_queries=sum(r['query_count'] for r in queryrows),all_valid=True,event_P_V_bitwise_continuous=True,pre_event_B_C_bitwise_equal=True,protected_assets_unchanged=len(manifest),historical_assets_unchanged=len(historical),PNG_verified=8,wall_s=wall,recorded_compute_s=budget,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,no_threshold_change=True,formal_external_datum='EXTERNAL_DATUM_UNVERIFIED',scientific_training_READY=False))
    print((F/'independent_audit.json').read_text())
if __name__=='__main__':main()
