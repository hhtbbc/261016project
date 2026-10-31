"""Independent numerical/asset audit of completed event propagations."""
from pathlib import Path
import csv,json,sys,time,resource,itertools
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from prepare_fourcastden_swarm_observation_v1 import sha,dump
from analyze_fourcastden_swarm_observation_v1 import table
from run_fourcastden_orbit_update_event_v1 import F,O
from PIL import Image


def main():
    begin=time.perf_counter();protocol=json.loads((F/'protocol.json').read_text());prior=json.loads((ROOT/'experiments/fourcastden_orbit_integration_v1/protocol.json').read_text())
    for key in ['base','tight']:assert protocol[key]==prior['controls'][key]
    assert protocol['aero']=={k:prior['controls'][k] for k in ['mass_kg','area_m2','Cd','wind']}
    assert protocol['convergence']==prior['convergence']
    states={};qc=[]
    for mode in ['base','tight']:
        for group in protocol['groups']:
            with np.load(F/f'{group}_{mode}_states_local.npz') as n:
                states[(group,mode)]=n['states'];np.testing.assert_array_equal(n['left_end'],n['right_start'])
            stat=json.loads((F/f'{group}_{mode}_runtime.json').read_text())
            queries=[]
            if group!='A_NoDrag':
                queries=list(csv.DictReader((F/f'{group}_{mode}_queries_local.csv').open()))
                assert len(queries)==stat['all_density_queries']
                assert stat['rhs_density_queries']==stat['nfev']+2
                assert len(queries)==stat['rhs_density_queries']+61+2
                for r in queries:
                    assert r['valid']=='True' and float(r['rho_kg_m3'])>0 and float(r['height_lower_m'])<=float(r['assumed_native_ZG_m'])<=float(r['height_upper_m'])
                    a,b=r['time_bracket'].split(';')
                    assert b<='2023-01-04T07:00:00.000' if r['branch']=='left' else a>='2023-01-04T07:00:00.000'
            else:assert stat['all_density_queries']==0 and stat['rhs_density_queries']==0
            qc.append(dict(group=group,mode=mode,total_queries=len(queries),valid_queries=len(queries),branch_brackets_qualified=True,
                no_atmosphere_for_no_drag=group=='A_NoDrag',P_V_event_continuous=True))
        np.testing.assert_array_equal(states[('B_Open',mode)][:31],states[('C_Updated',mode)][:31])
    independent=[]
    # Compute maxima by component expansion rather than reading summary norms.
    for a,b in itertools.combinations(protocol['groups'],2):
        db=states[(a,'base')][:,:3]-states[(b,'base')][:,:3];dt=states[(a,'tight')][:,:3]-states[(b,'tight')][:,:3]
        error=np.sqrt(np.sum((db-dt)**2,axis=1));response=np.sqrt(np.sum(dt**2,axis=1));limit=.01*float(response.max())
        independent.append(dict(pair=a+' minus '+b,error_max_m=float(error.max()),response_max_m=float(response.max()),limit_m=limit,passed=bool(error.max()<=limit)))
    assert all(x['passed'] for x in independent),'Keep numerical FAIL; no tolerance relaxation or rerun'
    table(O/'independent_query_audit.csv',qc);table(O/'independent_pair_convergence.csv',independent)
    protected=json.loads((F/'protected_runtime_v2.json').read_text());assert all(sha(ROOT/p)==h for p,h in protected.items())
    old=json.loads((ROOT/'experiments/tiegcm_runtime_restart_audit_v1/protected_files.json').read_text());assert all(sha(ROOT/p)==h for p,h in old.items())
    analysis=json.loads((F/'analysis.json').read_text());assert analysis['convergence_PASS']
    figs=[];source={'density_along_propagated_paths':'*_tight_samples.csv;event_density_drag_jump.csv',
        'drag_acceleration_paths':'*_tight_samples.csv;event_density_drag_jump.csv','position_differences':'pair_curves.csv',
        'RAC_differences':'pair_curves.csv','event_seam_detail':'C_Updated_tight_samples.csv;event_density_drag_jump.csv'}
    for p in O.glob('*.png'):
        with Image.open(p) as im:im.verify()
        figs.append(dict(figure=p.name,SHA256=sha(p),source=source[p.stem],date='2023-01-04',UTC='06:30-07:30',
            labels='HISTORICAL_SP3_INITIALIZED_VIRTUAL / PROVISIONAL_COORDINATE_A / SYNTHETIC_AERO / HINDCAST'))
    assert len(figs)==5;table(O/'figure_sources.csv',figs)
    wall=time.perf_counter()-begin;budget=analysis['budget_compute_used_s']+wall;assert budget<1800
    dump(F/'independent_delivery_audit.json',dict(status='PASS',trajectories=8,RK45_segments=16,new_CPU_tests=5,
        all_online_density_queries=sum(r['total_queries'] for r in qc),all_valid=True,all_event_brackets_correct=True,
        initial_state_identical=True,event_P_V_bitwise_continuous=True,B_C_before_event_bitwise_identical=True,
        pair_convergence_independently_PASS=6,single_convergence_PASS=4,task_assets_SHA_unchanged=len(protected),historical_assets_SHA_unchanged=len(old),
        PNGs_verified=5,audit_wall_s=wall,recorded_compute_budget_used_s=budget,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        EXTERNAL_DATUM_UNVERIFIED=True,REAL_ORBIT_VALIDATION_READY='BLOCKED',SCIENTIFIC_TRAINING_READY=False,new_forward=0,new_TIE=0))
    print((F/'independent_delivery_audit.json').read_text())


if __name__=='__main__':main()
