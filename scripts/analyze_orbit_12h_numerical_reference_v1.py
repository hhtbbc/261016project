"""Compare new high-order NoDrag references with immutable prior RK45 outputs."""
from pathlib import Path
import sys,json,time,csv,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_orbit_12h_numerical_reference_v1 import F,O,OLD,TIMES,saved
from prepare_fourcastden_swarm_observation_v1 import dump,sha
from analyze_fourcastden_swarm_observation_v1 import table
from evaluation.orbit_metrics import rac_errors

def main():
    start=time.perf_counter();p=json.loads((F/'protocol.json').read_text());assert json.loads((F/'worker_complete.json').read_text())['status']=='PASS';old=saved();base=old['A_NoDrag','base'];tight=old['A_NoDrag','tight'];states={'RK45_Base':base,'RK45_Tight':tight};runs=[];steps=[];oldconfig=json.loads((OLD/'protocol.json').read_text())
    for case in p['cases']:
        name=case['name']
        with np.load(F/f'{name}_states_local.npz') as n:
            states[name]=n['states'];np.testing.assert_array_equal(n['seconds'],TIMES);np.testing.assert_array_equal(n['states'][0],tight[0]);np.testing.assert_array_equal(n['left_end'],n['right_start']);np.testing.assert_array_equal(n['states'][360],n['left_end']);assert n['states'].shape==(721,6) and np.isfinite(n['states']).all()
            m=json.loads((F/f'{name}_runtime.json').read_text());assert sha(F/f'{name}_states_local.npz')==m['states_SHA']
            for i,k in enumerate(['left_times','right_times']):
                dt=np.diff(n[k]);assert np.all(dt>0) and dt.max()<=case['max_step']+1e-8;seg=m['segments'][i];nacc=len(dt);trials=(seg['nfev']-2-3*nacc)/12;assert int(trials)==trials and trials>=nacc
                steps.append(dict(case=name,segment=i,accepted=nacc,inferred_rejected=int(trials)-nacc,max_step_s=float(dt.max()),fraction_at_max=float(np.mean(np.isclose(dt,case['max_step'],rtol=0,atol=1e-8))),nfev=seg['nfev']))
        runs.append(dict(name=name,total_s=m['total_s'],nfev=m['nfev'],state_SHA=m['states_SHA']))
    ref=states['DOP15'];basis=tight;summary=[];curves=[];hour=[]
    for name,state in states.items():
        if name=='DOP15':continue
        d=state-ref;r=rac_errors(d[:,:3],basis[:,:3],basis[:,3:]);pn=np.linalg.norm(d[:,:3],axis=1);vn=np.linalg.norm(d[:,3:],axis=1)
        summary.append(dict(comparison=name+' minus DOP15',max_position_m=float(pn.max()),terminal_m=float(pn[-1]),RMS_m=float(np.sqrt(np.mean(pn**2))),max_speed_m_s=float(vn.max()),terminal_speed_m_s=float(vn[-1]),terminal_R_m=float(r[-1,0]),terminal_A_m=float(r[-1,1]),terminal_C_m=float(r[-1,2]),below_original_002m=bool(pn.max()<=.02)))
        for i,t in enumerate(TIMES):
            row=dict(comparison=name+' minus DOP15',seconds=int(t),UTC_hour=1+t/3600,position_m=float(pn[i]),speed_m_s=float(vn[i]),dx_m=float(d[i,0]),dy_m=float(d[i,1]),dz_m=float(d[i,2]),R_m=float(r[i,0]),A_m=float(r[i,1]),C_m=float(r[i,2]));curves.append(row)
            if t%3600==0:hour.append(row)
    dp=states['DOP30']-ref;refdiff=float(np.linalg.norm(dp[:,:3],axis=1).max());qualified=refdiff<=p['reference_pair_gate_m']
    be=base-ref;te=tight-ref;bn=np.linalg.norm(be[:,:3],axis=1);tn=np.linalg.norm(te[:,:3],axis=1);ratio=float(bn[-1]/tn[-1]);order=float(np.log2(ratio)) if ratio>0 else None
    # At accepted max-step-limited RK45 paths, such a ratio supports but does not
    # separately prove a tolerance vs max-step causal attribution.
    ratio_rows=[]
    for h in range(1,13):
        i=h*60;ratio_rows.append(dict(lead_h=h,UTC_hour=h+1,Base_to_reference_m=float(bn[i]),Tight_to_reference_m=float(tn[i]),ratio=float(bn[i]/tn[i]) if tn[i]>0 else None,interpretation='descriptive; old tolerances and max_step changed together'))
    for n,rows in [('reference_comparison.csv',summary),('reference_curves.csv',curves),('reference_hourly.csv',hour),('reference_runtime.csv',runs),('DOP_accepted_rejected.csv',steps),('step_ratio_evidence.csv',ratio_rows)]:table(O/n,rows)
    protected=json.loads((F/'protected.json').read_text());assert all(sha(ROOT/k)==v for k,v in protected.items());historical=json.loads((ROOT/'experiments/tiegcm_runtime_restart_audit_v1/protected_files.json').read_text());assert all(sha(ROOT/k)==v for k,v in historical.items())
    wall=time.perf_counter()-start;supervision=json.loads((F/'supervision.json').read_text());assert supervision['wall_s']<3600 and supervision['peak_tree_RSS_bytes']<4*2**30
    dump(F/'reference_assessment.json',dict(reference_status='PASS_BOUNDED' if qualified else 'FAIL',DOP30_DOP15_max_position_m=refdiff,original_reference_gate_m=.02,RK45_Tight_to_DOP15_max_m=float(tn.max()),RK45_Base_to_DOP15_max_m=float(bn.max()),terminal_error_ratio_Base_over_Tight=ratio,descriptive_halving_order=order,max_step_limited_RK45_paths_observed=True,ratio_is_descriptive_not_isolated_causal_test=True,isolated_tolerance_ablation_performed=False,old_ORBIT_NUMERICAL_CONVERGENCE_READY='FAIL_UNCHANGED',new_reference_does_not_rewrite_history=True,common_force_physical_accuracy_not_validated=True,B_C_D_new_reference_status='NOT_COMPUTED',previous_updated_open_4point698m='supported by old paired sensitivity only; no independent high-order B/C verification',protected_unchanged=len(protected),historical_unchanged=len(historical),analysis_wall_s=wall,analysis_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
    print(json.dumps(dict(summary=summary,assessment=json.loads((F/'reference_assessment.json').read_text())),indent=2))
if __name__=='__main__':main()
