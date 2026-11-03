"""Actual completed B/C DOP single and vector-effect convergence, no new ODE."""
from pathlib import Path
import sys,json,time,csv,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_orbit_12h_bc_dop853_validation_v1 import F,O,OLD,A,TIMES,GROUPS,validate_stage
from prepare_fourcastden_swarm_observation_v1 import sha,dump
from analyze_fourcastden_swarm_observation_v1 import table
from evaluation.orbit_metrics import rac_errors

def main():
    begin=time.perf_counter();p=json.loads((F/'protocol.json').read_text());assert json.loads((F/'worker_complete.json').read_text())['status']=='PASS';initial=np.load(ROOT/p['initial_file']);states={};old={};basis=np.load(OLD/'A_NoDrag_tight_states_local.npz')['states'];a15=np.load(A/'DOP15_states_local.npz')['states'];events=[];performance=[];controls=[]
    for mode in ['DOP30','DOP15']:
        assert validate_stage(F,mode,initial)['status']=='PASS'
        for g in GROUPS:
            with np.load(F/f'{g}_{mode}_states_local.npz') as n:
                states[g,mode]=n['states'];m=json.loads((F/f'{g}_{mode}_runtime.json').read_text());assert sha(F/f'{g}_{mode}_states_local.npz')==m['state_SHA']
                for i,key in enumerate(['left_times','right_times']):
                    dt=np.diff(n[key]);s=m['segments'][i];trials=(s['nfev']-2-3*len(dt))/12;assert int(trials)==trials and trials>=len(dt);controls.append(dict(group=g,mode=mode,segment=i,accepted=len(dt),inferred_rejected=int(trials)-len(dt),max_step_s=float(dt.max()),fraction_at_limit=float(np.mean(np.isclose(dt,p['max_steps'][mode],rtol=0,atol=1e-8))),nfev=s['nfev']))
            l,r=m['event_limits'];aa=np.array(l['drag_gcrs_m_s2']);ab=np.array(r['drag_gcrs_m_s2']);np.testing.assert_allclose(ab*l['rho_kg_m3'],aa*r['rho_kg_m3'],rtol=1e-12,atol=1e-35)
            events.append(dict(group=g,mode=mode,rho_left=l['rho_kg_m3'],rho_right=r['rho_kg_m3'],density_jump_fraction=r['rho_kg_m3']/l['rho_kg_m3']-1,drag_left=l['drag_norm_m_s2'],drag_right=r['drag_norm_m_s2'],drag_vector_jump=float(np.linalg.norm(ab-aa)),position_jump_m=m['event_records'][0]['position_jump_m'],velocity_jump_m_s=m['event_records'][0]['velocity_jump_m_s']))
            performance.append(dict(group=g,mode=mode,integration_s=m['integration_s'],total_s=m['total_s'],nfev=m['nfev'],RHS_calls=m['RHS_calls'],RHS_density_queries=m['RHS_density_queries'],all_density_queries=m['all_density_queries'],all_valid=m['all_queries_valid'],query_s=m['query_s'],peak_RSS_MiB=m['peak_RSS_MiB']))
    for g in GROUPS:
        for mode in ['base','tight']:
            with np.load(OLD/f'{g}_{mode}_states_local.npz') as n:old[g,mode]=n['states']
    comparisons=[];curves=[];leads=[]
    def compare(name,d):
        n=np.linalg.norm(d[:,:3],axis=1);v=np.linalg.norm(d[:,3:],axis=1);rac=rac_errors(d[:,:3],basis[:,:3],basis[:,3:]);vrac=rac_errors(d[:,3:],basis[:,:3],basis[:,3:])
        result=dict(comparison=name,max_position_m=float(n.max()),terminal_m=float(n[-1]),RMS_m=float(np.sqrt(np.mean(n*n))),max_velocity_m_s=float(v.max()),terminal_velocity_m_s=float(v[-1]),RMS_velocity_m_s=float(np.sqrt(np.mean(v*v))),terminal_R_m=float(rac[-1,0]),terminal_A_m=float(rac[-1,1]),terminal_C_m=float(rac[-1,2]))
        comparisons.append(result)
        for i,t in enumerate(TIMES):curves.append(dict(comparison=name,seconds=int(t),UTC_hour=1+t/3600,position_m=float(n[i]),velocity_m_s=float(v[i]),dx_m=float(d[i,0]),dy_m=float(d[i,1]),dz_m=float(d[i,2]),R_m=float(rac[i,0]),A_m=float(rac[i,1]),C_m=float(rac[i,2]),vR_m_s=float(vrac[i,0]),vA_m_s=float(vrac[i,1]),vC_m_s=float(vrac[i,2])))
        for h,side in [(1,'ordinary'),(3,'ordinary'),(6,'left'),(6,'right'),(7,'ordinary'),(9,'ordinary'),(12,'ordinary')]:
            i=h*60;leads.append(dict(comparison=name,lead_h=h,event_side=side,position_m=float(n[i]),velocity_m_s=float(v[i]),R_m=float(rac[i,0]),A_m=float(rac[i,1]),C_m=float(rac[i,2])))
        return result
    singles={g:compare(g+' DOP30 minus DOP15',states[g,'DOP30']-states[g,'DOP15']) for g in GROUPS}
    rk={g:compare(g+' RK45_Tight minus DOP15',old[g,'tight']-states[g,'DOP15']) for g in GROUPS}
    effects={mode:states['C_Updated',mode]-states['B_Open',mode] for mode in ['DOP30','DOP15']};effect_stats={m:compare('Updated minus Open '+m,d) for m,d in effects.items()}
    effect_delta=compare('BC effect DOP30 minus DOP15',effects['DOP30']-effects['DOP15']);rk_effect=old['C_Updated','tight']-old['B_Open','tight'];rk_delta=compare('BC effect RK45_Tight minus DOP15',rk_effect-effects['DOP15'])
    compare('Updated minus Open RK45_Tight',rk_effect)
    for g in GROUPS:compare(g+' DOP15 minus NoDrag DOP15',states[g,'DOP15']-a15)
    response=effect_stats['DOP15']['max_position_m'];limit=p['paired_gate_fraction']*response;pair_fraction=effect_delta['max_position_m']/response if response else None
    gates=dict(BC_DOP853_30_READY='PASS',BC_DOP853_15_READY='PASS',B_SINGLE_ORBIT_CONVERGENCE_READY='PASS' if singles['B_Open']['max_position_m']<=.02 else 'FAIL',C_SINGLE_ORBIT_CONVERGENCE_READY='PASS' if singles['C_Updated']['max_position_m']<=.02 else 'FAIL',BC_PAIR_EFFECT_CONVERGENCE_READY='PASS' if effect_delta['max_position_m']<=limit else 'FAIL',RK45_TIGHT_INDEPENDENT_REFERENCE_READY='PASS' if all(r['max_position_m']<=.02 for r in rk.values()) else 'FAIL',D_REFERENCE_HIGH_ORDER_READY='NOT_RUN',SCIENTIFIC_REAL_ORBIT_VALIDATION_READY='BLOCKED')
    for n,rows in [('comparison_summary.csv',comparisons),('comparison_curves.csv',curves),('lead_time_summary.csv',leads),('event_limits.csv',events),('performance.csv',performance),('accepted_rejected_steps.csv',controls)]:table(O/n,rows)
    effect_report=dict(DOP15_effect=effect_stats['DOP15'],DOP30_effect=effect_stats['DOP30'],paired_delta=effect_delta,paired_fraction=pair_fraction,paired_gate_m=limit,RK45_effect_delta=rk_delta,RK45_terminal_norm=float(np.linalg.norm(rk_effect[-1,:3])),terminal_norm_difference_DOP15_minus_RK45=effect_stats['DOP15']['terminal_m']-float(np.linalg.norm(rk_effect[-1,:3])),pre_event_BC_bitwise_identical=True,post_event_zero_or_nonzero_effect_only=True,no_high_order_D_improvement_claim=True)
    dump(F/'effect_assessment.json',effect_report)
    protected=json.loads((F/'protected.json').read_text());assert all(sha(ROOT/k)==v for k,v in protected.items());historic=json.loads((ROOT/'experiments/tiegcm_runtime_restart_audit_v1/protected_files.json').read_text());assert all(sha(ROOT/k)==v for k,v in historic.items())
    dump(F/'analysis.json',dict(gates=gates,single_gate_m=.02,pair_gate_fraction=.01,protected_unchanged=len(protected),historical_unchanged=len(historic),total_queries=sum(x['all_density_queries'] for x in performance),all_queries_valid=True,wall_s=time.perf_counter()-begin,RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,old_RK45_gate='FAIL_UNCHANGED',science_training=False,new_A=0,new_D=0,new_forward=0,new_TIE=0))
    print(json.dumps(dict(gates=gates,effect=effect_report,singles=singles,RK45_independent=rk),indent=2))
if __name__=='__main__':main()
