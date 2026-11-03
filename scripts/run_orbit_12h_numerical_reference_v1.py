"""Staged offline diagnostics then only two bounded NoDrag DOP853 trajectories."""
from pathlib import Path
import sys,json,time,resource,subprocess,os,signal,argparse,itertools,inspect,hashlib,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from prepare_fourcastden_swarm_observation_v1 import sha,dump,inside
from analyze_fourcastden_swarm_observation_v1 import table
from evaluation.orbit_metrics import rac_errors
OLD=ROOT/'experiments/fourcastden_orbit_update_12h_v1';F=ROOT/'experiments/orbit_12h_numerical_reference_v1';O=ROOT/'results/orbit_12h_numerical_reference_v1'
GROUPS=['A_NoDrag','B_Open','C_Updated','D_Reference'];TIMES=np.arange(0,43201,60)
def saved():
    arrays={}
    for g in GROUPS:
        for mode in ['base','tight']:
            with np.load(OLD/f'{g}_{mode}_states_local.npz') as n:arrays[g,mode]=n['states'];np.testing.assert_array_equal(n['seconds'],TIMES)
    return arrays

def offline():
    start=time.perf_counter();assert not (F/'offline_complete.json').exists();a=saved();ref=a['A_NoDrag','tight'];errors={g:a[g,'base']-a[g,'tight'] for g in GROUPS};rows=[];hour=[];summary=[];common=[];pairs=[];step=[]
    for g,e in errors.items():
        rac=rac_errors(e[:,:3],ref[:,:3],ref[:,3:]);pn=np.linalg.norm(e[:,:3],axis=1);vn=np.linalg.norm(e[:,3:],axis=1)
        summary.append(dict(group=g,max_m=float(pn.max()),terminal_m=float(pn[-1]),RMS_m=float(np.sqrt(np.mean(pn**2))),max_speed_m_s=float(vn.max()),terminal_speed_m_s=float(vn[-1]),terminal_R_m=float(rac[-1,0]),terminal_A_m=float(rac[-1,1]),terminal_C_m=float(rac[-1,2])))
        for i,t in enumerate(TIMES):
            row=dict(group=g,seconds=int(t),UTC_hour=1+t/3600,position_m=float(pn[i]),speed_m_s=float(vn[i]),**{k+'_m':float(e[i,j]) for j,k in enumerate(['dx','dy','dz'])},**{k+'_m':float(rac[i,j]) for j,k in enumerate('RAC')});rows.append(row)
            if t%3600==0:hour.append(row)
        for mode in ['base','tight']:
            m=json.loads((OLD/f'{g}_{mode}_runtime.json').read_text())
            with np.load(OLD/f'{g}_{mode}_states_local.npz') as n:
                for j,key in enumerate(['left_times','right_times']):
                    ts=n[key];dt=np.diff(ts);stats=m['segment_stats'][j];limit=30 if mode=='base' else 15
                    # Exact SciPy RK45 accounting: two startup calls + six per trial step.
                    trials=(stats['nfev']-2)/6;assert trials==int(trials);rejected=int(trials)-len(dt);assert rejected>=0
                    step.append(dict(group=g,mode=mode,segment=j,accepted=len(dt),inferred_rejected=rejected,nfev=stats['nfev'],max_step_s=float(dt.max()),fraction_at_max=float(np.mean(np.isclose(dt,limit,rtol=0,atol=1e-8))),min_step_s=float(dt.min())))
    e0=errors['A_NoDrag'][:,:3];mean=np.mean(np.stack([v[:,:3] for v in errors.values()]),axis=0)
    for g in GROUPS[1:]:
        e=errors[g][:,:3];dot=np.sum(e*e0,axis=1);den=np.linalg.norm(e,axis=1)*np.linalg.norm(e0,axis=1);valid=den>0;cos=np.full(len(TIMES),np.nan);cos[valid]=dot[valid]/den[valid];delta=np.linalg.norm(e-e0,axis=1)
        common.append(dict(group=g,terminal_dot_m2=float(dot[-1]),terminal_cosine=float(cos[-1]),min_nonzero_cosine=float(cos[valid].min()),position_vector_component_flat_correlation=float(np.corrcoef(e[1:].ravel(),e0[1:].ravel())[0,1]),max_difference_to_A_m=float(delta.max()),terminal_difference_to_A_m=float(delta[-1]),energy_fraction_A_projection=float(np.sum(dot[valid]**2/np.sum(e0[valid]**2,axis=1))/np.sum(e[valid]**2))))
    for g,h in itertools.combinations(GROUPS,2):
        lhs=errors[g]-errors[h];rhs=(a[g,'base']-a[h,'base'])-(a[g,'tight']-a[h,'tight']);np.testing.assert_array_equal(lhs,rhs)
        pairs.append(dict(pair=g+' minus '+h,vector_identity_max_abs=float(np.max(np.abs(lhs-rhs))),max_pair_position_numerical_m=float(np.linalg.norm(lhs[:,:3],axis=1).max()),max_pair_velocity_numerical_m_s=float(np.linalg.norm(lhs[:,3:],axis=1).max())))
    meanrows=[dict(seconds=int(t),UTC_hour=1+t/3600,mean_error_norm_m=float(np.linalg.norm(mean[i])),RMS_deviation_from_mean_m=float(np.sqrt(np.mean([np.sum((e[i,:3]-mean[i])**2) for e in errors.values()])))) for i,t in enumerate(TIMES)]
    blocks=[]
    for g,e in errors.items():
        pn=np.linalg.norm(e[:,:3],axis=1)
        for lo,hi in [(0,3),(3,6),(6,9),(9,12)]:
            ix=(TIMES>=lo*3600)&(TIMES<=hi*3600);blocks.append(dict(group=g,start_UTC=1+lo,stop_UTC=1+hi,RMS_m=float(np.sqrt(np.mean(pn[ix]**2))),start_m=float(pn[ix][0]),end_m=float(pn[ix][-1]),max_increment_per_output_m=float(np.diff(pn[ix]).max())))
    for n,data in [('old_error_curves.csv',rows),('old_error_hourly.csv',hour),('old_error_summary.csv',summary),('common_error.csv',common),('pair_identity.csv',pairs),('accepted_rejected_steps.csv',step),('mean_error.csv',meanrows),('error_growth_blocks.csv',blocks)]:table(O/n,data)
    dump(F/'offline_complete.json',dict(status='PASS',wall_s=time.perf_counter()-start,old_trajectories_read=8,new_integrations=0,pair_identities_exact=6,correlation_is_not_root_cause_proof=True,old_gate='FAIL_UNCHANGED'))
    print(json.dumps(dict(summary=summary,common=common,steps=step[:4]),indent=2))

def force_audit():
    assert json.loads((F/'offline_complete.json').read_text())['status']=='PASS'
    from astropy.time import Time
    from orbit.frames import configure_time_data
    from orbit.common_force_model import CommonForceModel
    from scipy.integrate import DOP853,RK45,solve_ivp
    import scipy
    configure_time_data();force=CommonForceModel(Time('2023-01-04T01:00:00'),43200);a=saved()['A_NoDrag','tight'];begin=time.perf_counter();rows=[];cost=[]
    def call(t,y):
        b=time.perf_counter();out=force(float(t),y[:3],y[3:]);cost.append(time.perf_counter()-b);return out
    for i in [1,60,180,359,360,361,540,719]:
        t=float(TIMES[i]);y=a[i];base=call(t,y)
        for k in range(3):assert np.array_equal(base,call(t,y))
        for dv in [-1e-3,1e-3]:
            pert=y.copy();pert[3]+=dv;assert np.array_equal(base,call(t,pert))
        for dt in [1.,.1,.01,.001,.0001]:
            lo=call(t-dt,y);hi=call(t+dt,y);rows.append(dict(kind='time_at_fixed_state',UTC_hour=1+t/3600,delta=dt,units='s',central_slope_norm=float(np.linalg.norm((hi-lo)/(2*dt))),central_curvature_norm=float(np.linalg.norm((hi-2*base+lo)/dt**2)),delta_accel_norm=float(np.linalg.norm(hi-lo))))
        for axis in range(3):
            for dr in [1.,.01]:
                lo=y.copy();hi=y.copy();lo[axis]-=dr;hi[axis]+=dr;v0=call(t,lo);v1=call(t,hi);rows.append(dict(kind='space_axis'+str(axis),UTC_hour=1+t/3600,delta=dr,units='m',central_slope_norm=float(np.linalg.norm((v1-v0)/(2*dr))),central_curvature_norm=float(np.linalg.norm((v1-2*base+v0)/dr**2)),delta_accel_norm=float(np.linalg.norm(v1-v0))))
    table(O/'force_perturbations.csv',rows)
    sources=['src/orbit/rk45_propagator.py','src/orbit/event_segments.py','src/orbit/common_force_model.py','src/orbit/gravity_degree40.py','src/orbit/spherical_harmonics_gravity.py','src/orbit/drag.py','src/orbit/frames.py','src/orbit/third_body_gravity.py']
    src=[]
    for path in sources:
        for lineno,line in enumerate((ROOT/path).read_text().splitlines(),1):
            if any(k in line for k in ['solve_ivp(','dense_output','max_step','TimeDelta','c2t06a','transform_state(','epv00','moon98','bounded_rhs','state = seg.states','evaluate_itrs','gradient','FROM_IERS_B','update_erfa']):src.append(dict(file=path,line=lineno,code=line.strip(),SHA256=sha(ROOT/path)))
    table(O/'source_evidence.csv',src)
    # Installed integrator is read only; source copied into project audit evidence.
    dump(F/'scipy_implementation.json',dict(version=scipy.__version__,RK45_stages=RK45.n_stages,DOP853_stages=DOP853.n_stages,DOP853_extra_dense_stages=len(DOP853.A_EXTRA),RK45_step_impl=inspect.getsource(RK45._step_impl),DOP853_dense_impl=inspect.getsource(DOP853._dense_output_impl)))
    median=float(np.median(cost));p95=float(np.quantile(cost,.95));estimated=(43200/30+43200/15)*15*median;conservative=estimated*1.2+60
    dump(F/'force_audit.json',dict(status='PASS',sample_calls=len(cost),repeat_bitwise=True,velocity_invariance=True,all_finite=bool(np.isfinite([r['delta_accel_norm'] for r in rows]).all()),wall_s=time.perf_counter()-begin,median_call_s=median,P95_call_s=p95,candidate_10_5s_estimate_s=(4320+8640)*15*median,chosen_30_15s_estimate_s=estimated,safety_estimate_s=conservative,no_obvious_jump_proven_only_at_sampled_states=True,not_global_smoothness_proof=True))
    print((F/'force_audit.json').read_text())

def freeze():
    assert json.loads((F/'force_audit.json').read_text())['status']=='PASS';assert not (F/'protocol.json').exists()
    audit=json.loads((F/'force_audit.json').read_text());assert audit['safety_estimate_s']<3600,'Budget does not fit; no automatic expansion'
    protected=json.loads((OLD/'protected_runtime_v2.json').read_text())
    for parent in [OLD,ROOT/'results/fourcastden_orbit_update_12h_v1']:
        for q in parent.rglob('*'):
            if q.is_file():protected[str(q.relative_to(ROOT))]=sha(q)
    for p in [Path(__file__).resolve(),ROOT/'configs/provisional_common_force_model.json']:
        protected[str(p.relative_to(ROOT))]=sha(p)
    assert all(sha(ROOT/p)==v for p,v in protected.items())
    dump(F/'protected.json',protected)
    dump(F/'protocol.json',dict(epoch='2023-01-04T01:00:00',duration_s=43200,event_s=21600,output_s=60,group='A_NoDrag only',solver='DOP853',cases=[dict(name='DOP30',max_step=30.),dict(name='DOP15',max_step=15.)],rtol=2.5e-13,atol=[1e-6]*3+[1e-9]*3,rtol_above_scipy_100eps_floor=True,rationale='Same tolerance for both high-order references; max30/15 chosen before results to fit measured 3600s budget; 10/5 candidates exceed budget',reference_pair_gate_m=.02,old_single_gate_m=.02,limits=dict(wall_s=3600,RSS_GiB=4,free_disk_GiB=20,output_MiB=100),estimate=audit,initial_state_file='experiments/fourcastden_orbit_update_12h_v1/initial_GCRS_local.npy',initial_SHA=sha(OLD/'initial_GCRS_local.npy'),no_SP3_feedback=True,no_old_matrix_rerun=True,no_physics_change=True))
    dump(F/'resource_preflight.json',dict(free_disk=shutil.disk_usage(ROOT).free,meminfo=Path('/proc/meminfo').read_text(),processes=subprocess.check_output(['ps','-eo','pid,pcpu,pmem,comm','--sort=-pcpu'],text=True).splitlines()[:12]))
    assert shutil.disk_usage(ROOT).free>20*2**30
    print('FROZEN: DOP853 max30/15 same2.5e-13 /1e-6m,1e-9m/s, two NoDrag only')

def worker():
    from astropy.time import Time
    from orbit.frames import configure_time_data
    from orbit.common_force_model import CommonForceModel
    from scipy.integrate import solve_ivp
    assert not (F/'worker_once.json').exists();dump(F/'worker_once.json',dict(start=time.time(),no_retry=True));p=json.loads((F/'protocol.json').read_text());assert all(sha(ROOT/k)==v for k,v in json.loads((F/'protected.json').read_text()).items())
    configure_time_data();force=CommonForceModel(Time(p['epoch']),43200);initial=np.load(OLD/'initial_GCRS_local.npy');begin=time.perf_counter();runs=[];progress=[begin]
    for case in p['cases']:
        if runs:
            estimate=2.1*runs[0]['total_s']+30;remaining=3600-(time.perf_counter()-begin)
            dump(F/'second_run_budget_gate.json',dict(remaining_s=remaining,estimated_s=estimate,passed=estimate<=remaining))
            if estimate>remaining:dump(F/'partial_complete.json',dict(reason='second reference exceeds budget',runs=runs));return
        name=case['name'];print('BEGIN',name,flush=True);tick=time.perf_counter();state=initial.copy();states=np.empty((721,6));segments=[];left_end=None;all_t=[];runtimes=[]
        def rhs(t,y):
            if time.perf_counter()-begin>3570:raise RuntimeError('3600s budget reserve guard')
            if time.perf_counter()-progress[0]>45:print('PROGRESS',name,'seconds',t,'wall_s',time.perf_counter()-begin,flush=True);progress[0]=time.perf_counter()
            return np.r_[y[3:],force(t,y[:3],y[3:])]
        for i,(lo,hi) in enumerate([(0.,21600.),(21600.,43200.)]):
            original=state.copy();part=time.perf_counter();sol=solve_ivp(rhs,(lo,hi),state,method='DOP853',rtol=p['rtol'],atol=p['atol'],max_step=case['max_step'],dense_output=True)
            assert sol.success and sol.status==0 and sol.t[-1]==hi and np.isfinite(sol.y).all();np.testing.assert_array_equal(sol.y[:,0],original)
            if i:np.testing.assert_array_equal(original,left_end)
            take=(TIMES>=lo)&((TIMES<hi) if i==0 else (TIMES<=hi));states[take]=sol.sol(TIMES[take]).T;state=sol.y[:,-1].copy()
            if i==0:left_end=state.copy()
            all_t.append(sol.t);segments.append(dict(start_s=lo,stop_s=hi,nfev=sol.nfev,accepted=len(sol.t)-1,min_step=float(np.diff(sol.t).min()),max_step=float(np.diff(sol.t).max()),wall_s=time.perf_counter()-part))
        assert states.shape==(721,6) and np.isfinite(states).all();np.testing.assert_array_equal(states[0],initial);np.testing.assert_array_equal(states[360],left_end)
        np.savez_compressed(inside(F/f'{name}_states_local.npz'),seconds=TIMES,states=states,left_times=all_t[0],right_times=all_t[1],left_end=left_end,right_start=states[360])
        m=dict(name=name,total_s=time.perf_counter()-tick,segments=segments,nfev=sum(x['nfev'] for x in segments),position_event_jump_m=0.,velocity_event_jump_m_s=0.,states_SHA=sha(F/f'{name}_states_local.npz'));dump(F/f'{name}_runtime.json',m);runs.append(m);print('END',name,m['total_s'],flush=True)
    dump(F/'worker_complete.json',dict(status='PASS',wall_s=time.perf_counter()-begin,runs=runs))

def supervise():
    assert not (F/'supervisor_once.json').exists();dump(F/'supervisor_once.json',dict(start=time.time(),wall_limit_s=3600));begin=time.perf_counter();peak=0;reason=None
    def rss(pid):
        try:
            a=Path(f'/proc/{pid}/status').read_text().splitlines();n=next(int(x.split()[1])*1024 for x in a if x.startswith('VmRSS:'));c=Path(f'/proc/{pid}/task/{pid}/children').read_text().split();return n+sum(rss(int(k)) for k in c)
        except (FileNotFoundError,StopIteration,ProcessLookupError):return 0
    with inside(ROOT/'logs/orbit_12h_numerical_reference_v1_worker.log').open('x') as log:
        child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'worker'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        while child.poll() is None:
            peak=max(peak,rss(os.getpid()))
            if time.perf_counter()-begin>3590 or peak>4*2**30 or shutil.disk_usage(ROOT).free<20*2**30:
                reason='resource limit';os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=10);break
            time.sleep(.5)
    dump(F/'supervision.json',dict(exit_code=child.returncode,reason=reason,wall_s=time.perf_counter()-begin,peak_tree_RSS_bytes=peak,status='PASS' if child.returncode==0 and reason is None else 'FAIL'))
    if child.returncode:raise RuntimeError('Retain failure, no retry')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['offline','force_audit','freeze','worker','supervise']);args=parser.parse_args();globals()[args.phase]()
