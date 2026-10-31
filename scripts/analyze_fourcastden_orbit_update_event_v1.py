"""Read completed propagations; independent state/event/pair convergence checks."""
from pathlib import Path
import sys,json,time,resource,itertools,csv
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from evaluation.orbit_metrics import rac_errors
from prepare_fourcastden_swarm_observation_v1 import sha,dump,inside
from analyze_fourcastden_swarm_observation_v1 import table
from run_fourcastden_orbit_update_event_v1 import F,O,providers


def main():
    begin=time.perf_counter();protocol=json.loads((F/'protocol.json').read_text());worker=json.loads((F/'worker_complete.json').read_text());supervision=json.loads((F/'supervision.json').read_text())
    assert worker['status']==supervision['status']=='PASS';groups=protocol['groups'];state={};times=None
    continuity=[];performance=[];jumps=[];pairs=[];curves=[];convergence=[]
    initial=np.load(F/'initial_GCRS_local.npy')
    for mode in protocol['modes']:
        for name in groups:
            with np.load(F/f'{name}_{mode}_states_local.npz',allow_pickle=False) as n:
                s=n['states'];t=n['seconds'];end=n['left_end'];start=n['right_start'];left=n['left_times'];right=n['right_times']
            assert s.shape==(61,6) and np.isfinite(s).all();np.testing.assert_array_equal(s[0],initial)
            np.testing.assert_array_equal(end,start);np.testing.assert_array_equal(s[30],end)
            assert left[0]==0 and left[-1]==1800 and right[0]==1800 and right[-1]==3600
            state[(name,mode)]=s;times=t
            m=json.loads((F/f'{name}_{mode}_runtime.json').read_text());assert m['all_density_queries_valid']
            assert m['actual_rhs_time_domains']==[[0.,1800.],[1800.,3600.]]
            np.testing.assert_array_equal(m['event_records'][0]['position_jump_m'],0.)
            np.testing.assert_array_equal(m['event_records'][0]['velocity_jump_m_s'],0.)
            limits=m['event_density_drag_limits'];al=np.array(limits[0]['drag_gcrs_m_s2']);ar=np.array(limits[1]['drag_gcrs_m_s2'])
            rl,rr=limits[0]['rho_kg_m3'],limits[1]['rho_kg_m3']
            if name!='A_NoDrag':np.testing.assert_allclose(ar*rl,al*rr,rtol=1e-12,atol=1e-35)
            continuity.append(dict(group=name,mode=mode,position_jump_m=float(np.linalg.norm(start[:3]-end[:3])),velocity_jump_m_s=float(np.linalg.norm(start[3:]-end[3:])),
                state_identical=True,initial_state_identical=True,left_end_s=float(left[-1]),right_start_s=float(right[0]),RHS_domain_checked=True))
            jumps.append(dict(group=name,mode=mode,rho_left_kg_m3=rl,rho_right_kg_m3=rr,
                density_jump_relative=(rr/rl-1) if rl else None,drag_left_norm_m_s2=limits[0]['drag_norm_m_s2'],drag_right_norm_m_s2=limits[1]['drag_norm_m_s2'],
                drag_jump_vector_norm_m_s2=float(np.linalg.norm(ar-al)),drag_norm_jump_m_s2=float(np.linalg.norm(ar)-np.linalg.norm(al)),
                position_jump_m=0.,velocity_jump_m_s=0.))
            performance.append(dict(group=name,mode=mode,integration_s=m['integration_s'],total_with_diagnostics_s=m['total_with_diagnostics_s'],nfev=m['nfev'],
                actual_RHS_with_event_diagnostics=m['RHS_count_with_event_diagnostics'],rhs_density_queries=m['rhs_density_queries'],all_density_queries=m['all_density_queries'],
                valid_fraction=1. if m['all_density_queries'] else None,query_s=m['query_elapsed_s'],peak_RSS_MiB=m['peak_RSS_MiB']))
        # No feedback or hidden reset: identical first half for B and C.
        np.testing.assert_array_equal(state[('B_Open',mode)][:31],state[('C_Updated',mode)][:31])
        ref=state[('A_NoDrag',mode)]
        for a,b in [('C_Updated','B_Open'),('B_Open','D_Reference'),('C_Updated','D_Reference'),('B_Open','A_NoDrag'),('C_Updated','A_NoDrag'),('D_Reference','A_NoDrag')]:
            delta=state[(a,mode)][:,:3]-state[(b,mode)][:,:3];rac=rac_errors(delta,ref[:,:3],ref[:,3:]);norm=np.linalg.norm(delta,axis=1)
            pairs.append(dict(mode=mode,comparison=a+' minus '+b,terminal_m=float(norm[-1]),max_m=float(norm.max()),RMS_m=float(np.sqrt(np.mean(norm**2))),
                event_m=float(norm[30]),terminal_R_m=float(rac[-1,0]),terminal_A_m=float(rac[-1,1]),terminal_C_m=float(rac[-1,2]),
                RMS_R_m=float(np.sqrt(np.mean(rac[:,0]**2))),RMS_A_m=float(np.sqrt(np.mean(rac[:,1]**2))),RMS_C_m=float(np.sqrt(np.mean(rac[:,2]**2)))))
            for sec,d,rc,n in zip(times,delta,rac,norm):curves.append(dict(mode=mode,comparison=a+' minus '+b,seconds=int(sec),norm_m=float(n),dx_m=float(d[0]),dy_m=float(d[1]),dz_m=float(d[2]),R_m=float(rc[0]),A_m=float(rc[1]),C_m=float(rc[2])))
    # Same frozen prior single-track and pair-vector engineering tolerances.
    for name in groups:
        e=state[(name,'base')][:,:3]-state[(name,'tight')][:,:3];err=float(np.linalg.norm(e,axis=1).max());limit=protocol['convergence']['single_trajectory_max_m']
        convergence.append(dict(type='single',comparison=name,error_max_m=err,response_max_m=None,limit_m=limit,ratio_to_response=None,passed=err<=limit))
    for a,b in itertools.combinations(groups,2):
        base=state[(a,'base')][:,:3]-state[(b,'base')][:,:3];tight=state[(a,'tight')][:,:3]-state[(b,'tight')][:,:3]
        err=float(np.linalg.norm(base-tight,axis=1).max());response=float(np.linalg.norm(tight,axis=1).max());limit=response*protocol['convergence']['paired_drag_response_fraction']
        convergence.append(dict(type='pair_vector',comparison=a+' minus '+b,error_max_m=err,response_max_m=response,limit_m=limit,
            ratio_to_response=err/response if response else None,passed=err<=limit))
    table(O/'event_continuity.csv',continuity);table(O/'event_density_drag_jump.csv',jumps);table(O/'performance.csv',performance)
    table(O/'pair_summary.csv',pairs);table(O/'pair_curves.csv',curves);table(O/'numerical_convergence.csv',convergence)
    for p,h in json.loads((F/'protected_runtime_v2.json').read_text()).items():assert sha(ROOT/p)==h,p
    # Prospective data support only, not a full12h orbit or new path queries.
    pv=providers();height=[]
    for name,event in pv.items():
        for branch,p in [('before',event.before),('after',event.after)]:
            height.append(dict(group=name,branch=branch,start=p.epochs[0].isot,stop=p.epochs[-1].isot,frames=len(p.epochs),invalid_column_times=int((~p.valid).sum()),
                valid_min_top_m=float(p.height[:,-1][p.valid].min()),valid_max_bottom_m=float(p.height[:,0][p.valid].max()),
                interpretation='native column availability, not proven full12h free-orbit coverage'))
    table(O/'twelve_hour_data_support.csv',height)
    onehour=sum(r['total_with_diagnostics_s'] for r in performance)
    nodrag=sum(r['total_with_diagnostics_s'] for r in performance if r['group']=='A_NoDrag')
    dump(F/'twelve_hour_estimate.json',dict(based_on_actual_hour_s=onehour,assumption_A_4_groups_base_tight_estimated_s=12*onehour,
        assumption_A_1point5_safety_s=18*onehour,assumptions_A_B_7_groups_base_tight_estimated_s=12*(2*onehour-nodrag),
        current_1800s_budget_not_sufficient_for_projected_full_matrix=12*onehour>1800,
        current_task_does_not_authorize_12h=True,other_models_or_windows_not_covered=True,physical_datums_still_unverified=True))
    elapsed=time.perf_counter()-begin;used=supervision['wall_s']+json.loads((F/'preflight.json').read_text())['prepare_wall_s']+elapsed
    assert used<1800
    dump(F/'analysis.json',dict(status='PASS' if all(r['passed'] for r in convergence) else 'NUMERICAL_GATE_FAIL_RETAINED',
        all8_completed=True,event_states_bitwise_continuous=True,B_C_pre_event_bitwise_equal=True,convergence_PASS=all(r['passed'] for r in convergence),
        analysis_wall_s=elapsed,budget_compute_used_s=used,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        no_real_orbit_accuracy_claim=True,no_SP3_after_t0_feedback=True,SCIENTIFIC_TRAINING_READY=False))
    print((F/'analysis.json').read_text());print(json.dumps(pairs,indent=2))


if __name__=='__main__':main()
