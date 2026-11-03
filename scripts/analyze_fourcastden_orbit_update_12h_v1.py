"""Offline full-window differences and frozen numerical tests; never propagates."""
from pathlib import Path
import sys,json,time,itertools,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_fourcastden_orbit_update_12h_v1 import F,O,validate_base
from prepare_fourcastden_swarm_observation_v1 import sha,dump
from analyze_fourcastden_swarm_observation_v1 import table
from evaluation.orbit_metrics import rac_errors
PAIRS=[('C_Updated','B_Open'),('B_Open','D_Reference'),('C_Updated','D_Reference'),('B_Open','A_NoDrag'),('C_Updated','A_NoDrag'),('D_Reference','A_NoDrag')]
def main():
    begin=time.perf_counter();p=json.loads((F/'protocol.json').read_text());worker=json.loads((F/'worker_complete.json').read_text());supervisor=json.loads((F/'supervision.json').read_text());assert worker['status']==supervisor['status']=='PASS'
    initial=np.load(F/'initial_GCRS_local.npy');assert validate_base(F,p,initial)['status']=='PASS'
    states={};stat={};times=np.arange(0,43201,60);cont=[];events=[];perf=[]
    for mode in p['modes']:
        for g in p['groups']:
            with np.load(F/f'{g}_{mode}_states_local.npz') as n:
                s=n['states'];np.testing.assert_array_equal(n['seconds'],times);np.testing.assert_array_equal(s[0],initial);np.testing.assert_array_equal(n['left_end'],n['right_start']);np.testing.assert_array_equal(s[360],n['left_end'])
                assert s.shape==(721,6) and np.isfinite(s).all();assert n['left_times'][0]==0 and n['left_times'][-1]==21600 and n['right_times'][0]==21600 and n['right_times'][-1]==43200
            states[g,mode]=s;m=json.loads((F/f'{g}_{mode}_runtime.json').read_text());stat[g,mode]=m
            assert m['all_density_queries_valid'] and m['actual_rhs_time_domains']==[[0.,21600.],[21600.,43200.]]
            e=m['event_records'][0];assert e['position_jump_m']==e['velocity_jump_m_s']==0
            cont.append(dict(group=g,mode=mode,initial_state_identical=True,position_jump_m=0.,velocity_jump_m_s=0.,output_records=721,time_gap=False,left_end_UTC='07:00',right_start_UTC='07:00'))
            l,r=m['event_density_drag_limits'];al=np.array(l['drag_gcrs_m_s2']);ar=np.array(r['drag_gcrs_m_s2']);rl=l['rho_kg_m3'];rr=r['rho_kg_m3']
            if g!='A_NoDrag':np.testing.assert_allclose(ar*rl,al*rr,rtol=1e-12,atol=1e-35)
            events.append(dict(group=g,mode=mode,rho_left_kg_m3=rl,rho_right_kg_m3=rr,density_jump_fraction=rr/rl-1 if rl else None,
                drag_left_m_s2=l['drag_norm_m_s2'],drag_right_m_s2=r['drag_norm_m_s2'],drag_vector_jump_m_s2=float(np.linalg.norm(ar-al)),position_jump_m=0.,velocity_jump_m_s=0.))
            perf.append(dict(group=g,mode=mode,integration_s=m['integration_s'],total_s=m['total_with_diagnostics_s'],nfev=m['nfev'],actual_RHS=m['RHS_count_with_event_diagnostics'],RHS_density_queries=m['rhs_density_queries'],all_density_queries=m['all_density_queries'],all_valid=True,query_s=m['query_elapsed_s'],peak_RSS_MiB=m['peak_RSS_MiB']))
        np.testing.assert_array_equal(states['B_Open',mode][:361],states['C_Updated',mode][:361])
    summary=[];curves=[];leads=[];blocks=[]
    for mode in p['modes']:
        ref=states['A_NoDrag',mode]
        for g,h in PAIRS:
            delta=states[g,mode]-states[h,mode];pos=np.linalg.norm(delta[:,:3],axis=1);vel=np.linalg.norm(delta[:,3:],axis=1);rac=rac_errors(delta[:,:3],ref[:,:3],ref[:,3:]);vrac=rac_errors(delta[:,3:],ref[:,:3],ref[:,3:]);label=g+' minus '+h
            summary.append(dict(mode=mode,comparison=label,terminal_m=float(pos[-1]),max_m=float(pos.max()),RMS_m=float(np.sqrt(np.mean(pos**2))),terminal_speed_m_s=float(vel[-1]),max_speed_m_s=float(vel.max()),RMS_speed_m_s=float(np.sqrt(np.mean(vel**2))),**{f'terminal_{k}_m':float(rac[-1,i]) for i,k in enumerate('RAC')}))
            for i,t in enumerate(times):curves.append(dict(mode=mode,comparison=label,seconds=int(t),UTC_hour=1+t/3600,norm_m=float(pos[i]),speed_norm_m_s=float(vel[i]),**{f'd{k}_m':float(delta[i,j]) for j,k in enumerate('xyz')},**{f'RAC_{k}_m':float(rac[i,j]) for j,k in enumerate('RAC')},**{f'RAC_v{k}_m_s':float(vrac[i,j]) for j,k in enumerate('RAC')}))
            for hour,side in [(1,'ordinary'),(3,'ordinary'),(6,'left'),(6,'right'),(7,'ordinary'),(9,'ordinary'),(12,'ordinary')]:
                i=hour*60;leads.append(dict(mode=mode,comparison=label,lead_h=hour,UTC_hour=1+hour,event_side=side,position_m=float(pos[i]),speed_m_s=float(vel[i]),**{k+'_m':float(rac[i,j]) for j,k in enumerate('RAC')}))
            for a,b in [(0,3),(3,6),(6,9),(9,12)]:
                idx=(times>=a*3600)&(times<=b*3600);blocks.append(dict(mode=mode,comparison=label,start_lead_h=a,stop_lead_h=b,endpoint_shared_for_descriptive_blocks=True,N=int(idx.sum()),RMS_m=float(np.sqrt(np.mean(pos[idx]**2))),max_m=float(pos[idx].max()),RMS_speed_m_s=float(np.sqrt(np.mean(vel[idx]**2)))))
    conv=[]
    for g in p['groups']:
        d=states[g,'base']-states[g,'tight'];ep=float(np.linalg.norm(d[:,:3],axis=1).max());ev=float(np.linalg.norm(d[:,3:],axis=1).max())
        conv.append(dict(type='single',comparison=g,max_position_m=ep,max_speed_m_s=ev,response_max_m=None,limit_m=.02,ratio=None,passed=ep<=.02))
    for g,h in itertools.combinations(p['groups'],2):
        b=states[g,'base']-states[h,'base'];t=states[g,'tight']-states[h,'tight'];d=b-t;err=float(np.linalg.norm(d[:,:3],axis=1).max());response=float(np.linalg.norm(t[:,:3],axis=1).max());ratio=err/response if response else None
        conv.append(dict(type='pair_vector',comparison=g+' minus '+h,max_position_m=err,max_speed_m_s=float(np.linalg.norm(d[:,3:],axis=1).max()),response_max_m=response,limit_m=.01*response,ratio=ratio,passed=err<=.01*response))
    proximity=[];s=states['B_Open','tight'];u=states['C_Updated','tight'];r=states['D_Reference','tight'];bo=np.linalg.norm(s[:,:3]-r[:,:3],axis=1);up=np.linalg.norm(u[:,:3]-r[:,:3],axis=1)
    for i,t in enumerate(times):proximity.append(dict(seconds=int(t),UTC_hour=1+t/3600,open_reference_m=float(bo[i]),updated_reference_m=float(up[i]),updated_minus_open_distance_m=float(up[i]-bo[i]),updated_closer=bool(up[i]<bo[i]),updated_farther=bool(up[i]>bo[i]),after_event=bool(t>21600)))
    farther=times[(times>21600)&(up>bo)];intervals=[]
    for x in farther:
        if not intervals or x>intervals[-1][1]+60:intervals.append([int(x),int(x)])
        else:intervals[-1][1]=int(x)
    post=times>21600
    effect=dict(terminal_open_reference_m=float(bo[-1]),terminal_updated_reference_m=float(up[-1]),terminal_reduction_fraction=float(1-up[-1]/bo[-1]),full_RMS_open_m=float(np.sqrt(np.mean(bo**2))),full_RMS_updated_m=float(np.sqrt(np.mean(up**2))),post_RMS_open_m=float(np.sqrt(np.mean(bo[post]**2))),post_RMS_updated_m=float(np.sqrt(np.mean(up[post]**2))),post_samples=360,post_closer_samples=int(np.sum((up<bo)&post)),post_farther_samples=int(np.sum((up>bo)&post)),farther_intervals_seconds_since01=intervals,strict_comparison_no_extra_threshold=True,claims_only_at_60s_outputs=True)
    for name,data in [('event_continuity.csv',cont),('event_density_drag_jump.csv',events),('performance.csv',perf),('pair_summary.csv',summary),('pair_curves.csv',curves),('lead_time_summary.csv',leads),('time_block_summary.csv',blocks),('numerical_convergence.csv',conv),('reference_proximity.csv',proximity)]:table(O/name,data)
    dump(F/'update_effect.json',effect)
    elapsed=time.perf_counter()-begin;budget=supervisor['wall_s']+json.loads((F/'preflight.json').read_text())['prepare_wall_s']+elapsed
    states_ready=all(np.isfinite(v).all() for v in states.values());gates=dict(TWELVE_HOUR_DATA_COVERAGE_READY='PASS',TWELVE_HOUR_ORBIT_BASE_READY='PASS',TWELVE_HOUR_ORBIT_TIGHT_READY='PASS' if states_ready else 'FAIL',EVENT_CONTINUITY_READY='PASS',ORBIT_NUMERICAL_CONVERGENCE_READY='PASS' if all(r['passed'] for r in conv) else 'FAIL',SCIENTIFIC_REAL_ORBIT_VALIDATION_READY='BLOCKED')
    dump(F/'analysis.json',dict(gates=gates,wall_s=elapsed,budget_compute_s=budget,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,completed_trajectories=8,event_segments=16,all_queries_valid=True,total_queries=sum(x['all_density_queries'] for x in perf),new_GPU=0,new_TIE=0,scientific_training_READY=False,retain_failed_numerical_gates=True))
    assert budget<10500
    print(json.dumps(dict(gates=gates,effect=effect,convergence=conv),indent=2))
if __name__=='__main__':main()
