"""Independent B/C single/pair and full query accounting; no propagation."""
from pathlib import Path
import sys,csv,json,time
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_orbit_12h_bc_dop853_validation_v1 import F,O,OLD,A,GROUPS,TIMES
from prepare_fourcastden_swarm_observation_v1 import sha,dump
from analyze_fourcastden_swarm_observation_v1 import table

def main():
    begin=time.perf_counter();p=json.loads((F/'protocol.json').read_text());assessment=json.loads((F/'analysis.json').read_text());effect=json.loads((F/'effect_assessment.json').read_text());s={};qrows=[];initial=np.load(ROOT/p['initial_file']);derived=[]
    for mode in ['DOP30','DOP15']:
        for g in GROUPS:
            with np.load(F/f'{g}_{mode}_states_local.npz') as n:
                s[g,mode]=n['states'];np.testing.assert_array_equal(n['states'][0],initial);np.testing.assert_array_equal(n['seconds'],TIMES);np.testing.assert_array_equal(n['left_end'],n['right_start']);np.testing.assert_array_equal(n['states'][360],n['left_end']);assert np.isfinite(n['states']).all()
                for key in ['left_times','right_times']:assert np.diff(n[key]).min()>0 and np.diff(n[key]).max()<=p['max_steps'][mode]+1e-8
            m=json.loads((F/f'{g}_{mode}_runtime.json').read_text());count=0;top=float('inf');bottom=float('inf');sides={'left':0,'right':0}
            for row in csv.DictReader((F/f'{g}_{mode}_queries_local.csv').open()):
                count+=1;sides[row['branch']]+=1;assert row['valid']=='True' and float(row['rho_kg_m3'])>0
                lo,hi=float(row['height_lower_m']),float(row['height_upper_m']);z=float(row['assumed_native_ZG_m']);assert lo<=z<=hi;top=min(top,hi-z);bottom=min(bottom,z-lo);a,b=row['time_bracket'].split(';')
                if row['branch']=='left':assert a>='2023-01-04T01:00:00.000' and b<='2023-01-04T07:00:00.000' and row['UTC']<='2023-01-04T07:00:00.000'
                else:assert a>='2023-01-04T07:00:00.000' and b<='2023-01-04T13:00:00.000' and row['UTC']>='2023-01-04T07:00:00.000'
            assert count==m['all_density_queries']==m['nfev']+725 and m['RHS_calls']==m['RHS_density_queries']==m['nfev']+2
            qrows.append(dict(group=g,mode=mode,total_queries=count,valid_queries=count,left=sides['left'],right=sides['right'],minimum_top_margin_m=top,minimum_bottom_margin_m=bottom,branch_time_brackets_qualified=True))
            # Saved physical diagnostic relation, no future fields or new queries.
            for row in csv.DictReader((O/f'{g}_{mode}_samples.csv').open()):
                rho=float(row['rho_kg_m3']);v=float(row['relative_speed_m_s']);norm=float(row['drag_norm_m_s2']);expected=.5*rho*p['aero']['Cd']*p['aero']['area_m2']/p['aero']['mass_kg']*v*v
                np.testing.assert_allclose(norm,expected,rtol=1e-12,atol=0)
        np.testing.assert_array_equal(s['B_Open',mode][:361],s['C_Updated',mode][:361])
    for g in GROUPS:
        d=s[g,'DOP30']-s[g,'DOP15'];norm=np.sqrt(sum(d[:,i]**2 for i in range(3)));derived.append(dict(item=g,max_position_m=float(norm.max()),terminal_m=float(norm[-1]),gate_m=.02,passed=bool(norm.max()<=.02)))
    delta30=s['C_Updated','DOP30']-s['B_Open','DOP30'];delta15=s['C_Updated','DOP15']-s['B_Open','DOP15'];diff=delta30-delta15;err=float(np.sqrt(sum(diff[:,i]**2 for i in range(3))).max());response=float(np.sqrt(sum(delta15[:,i]**2 for i in range(3))).max());np.testing.assert_allclose(err,effect['paired_delta']['max_position_m'],rtol=1e-13,atol=1e-14);derived.append(dict(item='BC effect vector',max_position_m=err,terminal_m=float(np.linalg.norm(diff[-1,:3])),gate_m=.01*response,passed=err<=.01*response))
    olddelta=np.load(OLD/'C_Updated_tight_states_local.npz')['states']-np.load(OLD/'B_Open_tight_states_local.npz')['states'];np.testing.assert_allclose(np.linalg.norm((olddelta-delta15)[:,:3],axis=1).max(),effect['RK45_effect_delta']['max_position_m'],rtol=1e-13,atol=1e-14)
    for name in ['DOP30','DOP15']:
        m=json.loads((A/f'{name}_runtime.json').read_text());assert sha(A/f'{name}_states_local.npz')==m['states_SHA']
    protected=json.loads((F/'protected.json').read_text());assert all(sha(ROOT/k)==v for k,v in protected.items())
    historical=json.loads((ROOT/'experiments/tiegcm_runtime_restart_audit_v1/protected_files.json').read_text());assert all(sha(ROOT/k)==v for k,v in historical.items())
    pngs=list(O.glob('*.png'));assert len(pngs)==8
    for q in pngs:
        with Image.open(q) as im:im.verify()
    for row in csv.DictReader((O/'figure_sources.csv').open()):assert sha(O/row['figure'])==row['SHA256']
    sup=json.loads((F/'supervision.json').read_text());assert sup['status']=='PASS' and sup['wall_s']<13620 and sup['peak_tree_RSS_bytes']<4*2**30
    table(O/'independent_query_accounting.csv',qrows);table(O/'independent_convergence.csv',derived)
    dump(F/'independent_audit.json',dict(audit_status='PASS',new_trajectories=4,new_A=0,new_D=0,all_queries=sum(r['total_queries'] for r in qrows),all_valid=True,pre_event_BC_bitwise_identical=True,event_P_V_bitwise_continuous=True,vector_effect_independently_verified=True,protected_SHA_unchanged=len(protected),historical_SHA_unchanged=len(historical),NoDrag_SHA_verified=2,PNGs_verified=8,old_RK45_gate='FAIL_UNCHANGED',current_BC_gates=assessment['gates'],wall_s=time.perf_counter()-begin,real_orbit='BLOCKED',science_training=False))
    print((F/'independent_audit.json').read_text())
if __name__=='__main__':main()
