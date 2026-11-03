"""Read-only four-group high-order closure; never integrates any trajectory."""
from pathlib import Path
import sys,json,csv,time,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_orbit_12h_abcd_dop853_closure_v1 import F,O,A,OLD,TIMES,validate_stage
from prepare_fourcastden_swarm_observation_v1 import sha,dump
from analyze_fourcastden_swarm_observation_v1 import table
from evaluation.orbit_metrics import rac_errors
BC=ROOT/'experiments/orbit_12h_bc_dop853_validation_v1';BO=ROOT/'results/orbit_12h_bc_dop853_validation_v1'
GROUPS=['A_NoDrag','B_Open','C_Updated','D_Reference']
PAIRS=[('B_Open','A_NoDrag'),('C_Updated','A_NoDrag'),('D_Reference','A_NoDrag'),('C_Updated','B_Open'),('B_Open','D_Reference'),('C_Updated','D_Reference')]
def load(g,m):
    folder=A if g=='A_NoDrag' else F if g=='D_Reference' else BC
    name=m if g=='A_NoDrag' else g+'_'+m
    path=folder/(name+'_states_local.npz');meta=json.loads((folder/(name+'_runtime.json')).read_text());assert sha(path)==meta.get('state_SHA',meta.get('states_SHA'))
    with np.load(path) as n:
        np.testing.assert_array_equal(n['seconds'],TIMES);y=n['states'];assert y.shape==(721,6) and np.isfinite(y).all();np.testing.assert_array_equal(n['left_end'],n['right_start'])
    return y

def intervals(mask):
    out=[];start=None
    for i,v in enumerate(np.r_[mask,False]):
        if v and start is None:start=i
        if not v and start is not None:
            out.append(dict(start_UTC=f'{1+int(TIMES[start])//3600:02d}:{(int(TIMES[start])%3600)//60:02d}:00',stop_UTC=f'{1+int(TIMES[i-1])//3600:02d}:{(int(TIMES[i-1])%3600)//60:02d}:00',samples=i-start));start=None
    return out

def main():
    begin=time.perf_counter();assert json.loads((F/'worker_complete.json').read_text())['status']=='PASS';p=json.loads((F/'protocol.json').read_text());initial=np.load(ROOT/p['initial_file']);states={(g,m):load(g,m) for g in GROUPS for m in ['DOP30','DOP15']};basis=np.load(OLD/'A_NoDrag_tight_states_local.npz')['states'];summaries=[];curves=[];leads=[]
    for y in states.values():np.testing.assert_array_equal(y[0],initial)
    for m in ['DOP30','DOP15']:validate_stage(F,m,initial);np.testing.assert_array_equal(states['B_Open',m][:361],states['C_Updated',m][:361])
    def compare(label,d):
        r=np.linalg.norm(d[:,:3],axis=1);v=np.linalg.norm(d[:,3:],axis=1);rac=rac_errors(d[:,:3],basis[:,:3],basis[:,3:]);s=dict(comparison=label,max_position_m=float(r.max()),terminal_m=float(r[-1]),RMS_m=float(np.sqrt(np.mean(r*r))),post6h_RMS_m=float(np.sqrt(np.mean(r[TIMES>21600]**2))),max_velocity_m_s=float(v.max()),terminal_velocity_m_s=float(v[-1]),terminal_R_m=float(rac[-1,0]),terminal_A_m=float(rac[-1,1]),terminal_C_m=float(rac[-1,2]));summaries.append(s)
        for i,t in enumerate(TIMES):curves.append(dict(comparison=label,seconds=int(t),UTC_hour=1+t/3600,position_m=float(r[i]),velocity_m_s=float(v[i]),dx_m=float(d[i,0]),dy_m=float(d[i,1]),dz_m=float(d[i,2]),R_m=float(rac[i,0]),A_m=float(rac[i,1]),C_m=float(rac[i,2])))
        for h,side in [(1,'ordinary'),(3,'ordinary'),(6,'left'),(6,'right'),(7,'ordinary'),(9,'ordinary'),(12,'ordinary')]:
            i=h*60;leads.append(dict(comparison=label,lead_h=h,event_side=side,position_m=float(r[i]),velocity_m_s=float(v[i]),R_m=float(rac[i,0]),A_m=float(rac[i,1]),C_m=float(rac[i,2])))
        return s
    singles={g:compare(g+' DOP30 minus DOP15',states[g,'DOP30']-states[g,'DOP15']) for g in GROUPS}
    oldd=np.load(OLD/'D_Reference_tight_states_local.npz')['states'];rk=compare('D_Reference RK45_Tight minus DOP15',oldd-states['D_Reference','DOP15']);pairs=[];stats={}
    for x,y in PAIRS:
        name=x+' minus '+y;ds={m:states[x,m]-states[y,m] for m in ['DOP30','DOP15']}
        for m in ds:stats[name,m]=compare(name+' '+m,ds[m])
        delta=compare(name+' effect DOP30 minus DOP15',ds['DOP30']-ds['DOP15']);response=stats[name,'DOP15']['max_position_m'];fraction=delta['max_position_m']/response if response else None
        pairs.append(dict(comparison=name,max_DOP15_response_m=response,max_effect_vector_sensitivity_m=delta['max_position_m'],terminal_effect_vector_sensitivity_m=delta['terminal_m'],relative_sensitivity_fraction=fraction,limit_m=.01*response,gate='PASS' if delta['max_position_m']<=.01*response else 'FAIL'))
    eopen=np.linalg.norm((states['B_Open','DOP15']-states['D_Reference','DOP15'])[:,:3],axis=1);eupdated=np.linalg.norm((states['C_Updated','DOP15']-states['D_Reference','DOP15'])[:,:3],axis=1);post=TIMES>21600;better=post&(eupdated<eopen);worse=post&(eupdated>eopen);equal=post&(eupdated==eopen)
    openstats=stats['B_Open minus D_Reference','DOP15'];upstats=stats['C_Updated minus D_Reference','DOP15'];effect=dict(open=openstats,updated=upstats,endpoint_reduction_percent=100*(1-eupdated[-1]/eopen[-1]),full_RMS_reduction_percent=100*(1-upstats['RMS_m']/openstats['RMS_m']),post6h_RMS_reduction_percent=100*(1-upstats['post6h_RMS_m']/openstats['post6h_RMS_m']),post_samples=int(post.sum()),closer_samples=int(better.sum()),farther_samples=int(worse.sum()),equal_samples=int(equal.sum()),closer_intervals=intervals(better),farther_intervals=intervals(worse),sample_cadence_s=60,samples_not_independent=True,historical_RK45_endpoint_open_m=9.177625127182976,historical_RK45_endpoint_updated_m=4.4824348326751995,historical_RK45_endpoint_reduction_percent=51.15909867141131)
    table(O/'update_benefit_timeseries.csv',[dict(seconds=int(t),UTC_hour=1+t/3600,Open_to_D_m=float(eopen[i]),Updated_to_D_m=float(eupdated[i]),reduction_m=float(eopen[i]-eupdated[i]),relation='pre_event' if not post[i] else 'closer' if better[i] else 'farther' if worse[i] else 'equal') for i,t in enumerate(TIMES)])
    performance=[];events=[]
    for m in ['DOP30','DOP15']:
        meta=json.loads((F/f'D_Reference_{m}_runtime.json').read_text());assert meta['all_queries_valid'];assert meta['all_density_queries']==meta['nfev']+725
        performance.append({k:meta[k] for k in ['group','mode','integration_s','total_s','nfev','all_density_queries','all_queries_valid','peak_RSS_MiB','query_s']})
        l,r=meta['event_limits'];events.append(dict(group='D_Reference',mode=m,rho_left=l['rho_kg_m3'],rho_right=r['rho_kg_m3'],drag_left=l['drag_norm_m_s2'],drag_right=r['drag_norm_m_s2'],position_jump_m=meta['event_records'][0]['position_jump_m'],velocity_jump_m_s=meta['event_records'][0]['velocity_jump_m_s']))
    ds=singles['D_Reference']['max_position_m']<=.02;all_single=all(s['max_position_m']<=.02 for s in singles.values());all_pairs=all(s['gate']=='PASS' for s in pairs)
    gates=dict(D_DOP853_30_READY='PASS',D_DOP853_15_READY='PASS',D_SINGLE_ORBIT_CONVERGENCE_READY='PASS' if ds else 'FAIL',ABCD_HIGH_ORDER_COMPARISON_READY='PASS' if all_single else 'FAIL',SIX_PAIR_EFFECT_CONVERGENCE_READY='PASS' if all_pairs and ds else 'FAIL',IDEAL_UPDATE_ORBIT_EFFECT_VALIDATED='PASS' if all_single and all_pairs else 'FAIL',SCIENTIFIC_REAL_ORBIT_VALIDATION_READY='BLOCKED')
    for name,rows in [('comparison_summary.csv',summaries),('comparison_curves.csv',curves),('pair_convergence.csv',pairs),('lead_time_summary.csv',leads),('performance.csv',performance),('event_limits.csv',events)]:table(O/name,rows)
    dump(F/'effect_assessment.json',effect);protected=json.loads((F/'protected.json').read_text());assert all(sha(ROOT/k)==v for k,v in protected.items());historic=json.loads((ROOT/'experiments/tiegcm_runtime_restart_audit_v1/protected_files.json').read_text());assert all(sha(ROOT/k)==v for k,v in historic.items())
    dump(F/'analysis.json',dict(gates=gates,singles=singles,D_RK45_Tight_vs_DOP15=rk,pairs=pairs,protected_unchanged=len(protected),historical_unchanged=len(historic),new_trajectories=2,new_A_B_C=0,new_forward=0,new_TIE=0,total_new_queries=sum(x['all_density_queries'] for x in performance),wall_s=time.perf_counter()-begin,RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,old_RK45_gate='FAIL_UNCHANGED',science_training=False,formal_external_datum='EXTERNAL_DATUM_UNVERIFIED'))
    print(json.dumps(dict(gates=gates,effect=effect,D_single=singles['D_Reference'],D_RK45=rk,pairs=pairs),indent=2))
if __name__=='__main__':main()
