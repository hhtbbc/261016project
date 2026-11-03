"""Twelve-hour H6 condition propagation; staged Base gate before Tight."""
from pathlib import Path
import argparse,json,sys,time,resource,subprocess,os,signal,shutil,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from astropy.time import Time,TimeDelta
from atmosphere.fourcastden_density import FourCastDENDensity,reconstruct_native_zg,HEIGHT_SOURCE
from atmosphere.event_aware_density import EventAwareDensity
from atmosphere.provisional_event_bridge import ProvisionalEventBridge,LABEL
from atmosphere.density_interface import DensityQuery
from orbit.frames import configure_time_data,transform_state
from evaluation.orbit_data import load_sp3_reference
from evaluation.orbit_interpolation import HermiteOrbit
from prepare_fourcastden_swarm_observation_v1 import sha,dump,inside
from analyze_fourcastden_swarm_observation_v1 import table
from run_fourcastden_ideal_update_6h import reference,oldpaths
from audit_fourcastden_coordinate_update_v1 import load
TAG='fourcastden_orbit_update_12h_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG
DAY='2023-01-04';EPOCH=DAY+'T01:00:00';EVENT=DAY+'T07:00:00'
LABELS='HISTORICAL_SP3_INITIALIZED_VIRTUAL_PROPAGATION / PROVISIONAL_COORDINATE_A / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST / FORCE_MODEL_INCOMPLETE / PROVISIONAL_EPHEMERIS'


from run_fourcastden_orbit_update_event_v1 import providers


def prepare():
    begin=time.perf_counter()
    if (F/'protocol.json').exists():raise FileExistsError('Frozen run tag already prepared')
    old=json.loads((ROOT/'experiments/fourcastden_orbit_integration_v1/protocol.json').read_text());c=old['controls']
    protected=json.loads((ROOT/'experiments/fourcastden_ideal_update_6h_v1/protected.json').read_text())
    for p,h in protected.items():assert sha(ROOT/p)==h
    shared=json.loads((ROOT/'configs/provisional_common_force_model.json').read_text())
    for p,h in shared['implementation_sha256'].items():assert sha(ROOT/p)==h;protected[p]=h
    paths=[ROOT/'configs/provisional_common_force_model.json',ROOT/'src/orbit/event_segments.py',ROOT/'src/atmosphere/event_aware_density.py',
        ROOT/'src/atmosphere/provisional_event_bridge.py',ROOT/'src/atmosphere/fourcastden_density.py',ROOT/'tests/test_provisional_event_bridge.py',Path(__file__).resolve()]
    p=ROOT/'data/processed/fourcastden_ideal_update_6h_v1'/f'{DAY}_Direct.npz'
    assert sha(p)==json.loads((ROOT/'experiments/fourcastden_ideal_update_6h_v1'/f'{DAY}_Direct_runtime.json').read_text())['result_SHA'];paths.append(p)
    sp3=next((ROOT/'data/raw/swarm_coordinate_orbit_readiness_v1/extracted').glob('*20230104T235942_0203.sp3'));paths += [sp3,sp3.with_suffix('.HDR')]
    paths += [ROOT/'scripts/run_fourcastden_orbit_update_event_v1.py',ROOT/'tests/test_fourcastden_orbit_update_12h.py']
    for olddir in ['experiments/fourcastden_orbit_update_event_v1','results/fourcastden_orbit_update_event_v1']:
        paths += [p for p in (ROOT/olddir).rglob('*') if p.is_file()]
    for p in paths:protected[str(p.relative_to(ROOT))]=sha(p)
    disk=shutil.disk_usage(ROOT).free;assert disk>20*2**30
    dump(F/'resource_preflight.json',dict(free_disk_bytes=disk,meminfo=Path('/proc/meminfo').read_text(),processes=subprocess.check_output(['ps','-eo','pid,pcpu,pmem,comm','--sort=-pcpu'],text=True).splitlines()[:12],expected_s=6893.766,safety_s=10340.65,authorized_s=10500,no_new_download=True))
    dump(F/'protocol.json',dict(labels=LABELS,day=DAY,start=EPOCH,event=EVENT,stop=DAY+'T13:00:00',duration_s=43200,event_s=21600,
        modes=['base','tight'],groups=['A_NoDrag','B_Open','C_Updated','D_Reference'],max_complete_trajectories=8,max_RK45_segments=16,
        aero=dict(mass_kg=c['mass_kg'],area_m2=c['area_m2'],Cd=c['Cd'],wind=c['wind']),
        base=c['base'],tight=c['tight'],convergence=old['convergence'],output_step_s=60,
        limits=dict(propagation_and_numerical_s=10500,RSS_GiB=4,output_MiB=200,free_disk_GiB=20),
        estimate=dict(previous_8_trajectory_wall_s=580.941,expected_s=6893.766,conservative_s=10340.65,reserve_numerical_s=120,RSS_MiB=768,output_MiB=100),
        free_disk_bytes=disk,initial_state='Jan4 SP3 Hermite at01:00UTC then complete PV ITRS->GCRS; future2s native bracket',
        only_density_changes=True,post_t0_SP3_feedback=False,neural_forward_count=0,old_600s_budget_not_reused=True))
    dump(F/'protected.json',protected)
    dump(F/'protected_runtime_v2.json',protected)
    configure_time_data();s=load_sp3_reference([sp3]);times=Time(EPOCH)+TimeDelta(np.arange(0,43201,10),format='sec');q=HermiteOrbit(s).evaluate(times)
    gp,gv=transform_state(q.positions_m[:1],q.velocities_m_s[:1],times[:1],'ITRS','GCRS')
    np.save(inside(F/'initial_GCRS_local.npy'),np.r_[gp[0],gv[0]])
    dump(F/'initialization_metadata.json',dict(label='HISTORICAL_SP3_INITIALIZED_VIRTUAL_PROPAGATION',SP3_source=s.metadata,
        UTC=EPOCH,frame='GCRS',position_unit='m',velocity_unit='m/s',later_native_epoch_used_s=2,SP3_used_after_t0_in_force=False,initial_state_SHA256=sha(F/'initial_GCRS_local.npy'),bracket_UTC=['2023-01-04T00:59:52','2023-01-04T01:00:02']))
    ev=providers();rows=[];contracts=[]
    for name,event in ev.items():
        for side,p in [('left',event.before),('right',event.after)]:
            valid=bool(p.valid.all());assert valid,'Jan4 Direct/reference invalid thermodynamic columns'
            contracts.append(dict(group=name,branch=side,frames=len(p.epochs),start=p.epochs[0].isot,stop=p.epochs[-1].isot,
                invalid_column_times=int((~p.valid).sum()),valid_min_top_m=float(p.height[:,-1][p.valid].min()),
                valid_max_bottom_m=float(p.height[:,0][p.valid].max()),units='density kg/m3; native ZG m',all_finite_positive=True))
    table(O/'field_coverage.csv',contracts)
    for name,p in ev.items():
        rec=[];bs=[ProvisionalEventBridge(p.before,authorization_label=LABEL,branch_label='left',records=rec),ProvisionalEventBridge(p.after,authorization_label=LABEL,branch_label='right',records=rec)]
        for i,t in enumerate(times):
            query=DensityQuery.from_itrs(t,q.positions_m[i])
            try:bs[int(i>=2160)].density_kg_m3(query)
            except Exception:
                table(F/'failed_SP3_coverage_local.csv',[dict(group=name,**r) for r in rec])
                dump(F/'preflight_failure.json',dict(status='FAIL',group=name,UTC=t.isot,no_formal_propagation_started=True))
                raise
        # Both event limits at exactly the same SP3 position, additional checks.
        query=DensityQuery.from_itrs(Time(EVENT),q.positions_m[2160])
        for b in bs:b.density_kg_m3(query)
        for r in rec:rows.append(dict(group=name,**r))
    table(F/'SP3_coverage_local.csv',rows)
    dump(F/'preflight.json',dict(status='PASS',SP3_path_queries=len(rows),valid_queries=sum(r['valid'] for r in rows),query_success_fraction=1.,
        min_top_margin_m=min(r['height_upper_m']-r['assumed_native_ZG_m'] for r in rows),
        min_bottom_margin_m=min(r['assumed_native_ZG_m']-r['height_lower_m'] for r in rows),
        reference_path_not_a_replacement_for_online_checks=True,prepare_wall_s=time.perf_counter()-begin))
    print((F/'preflight.json').read_text())


def validate_base(directory,protocol,initial):
    checked=[]
    for name in protocol['groups']:
        with np.load(directory/f'{name}_base_states_local.npz') as n:
            assert n['states'].shape==(721,6) and np.isfinite(n['states']).all()
            np.testing.assert_array_equal(n['seconds'],np.arange(0,43201,60))
            np.testing.assert_array_equal(n['states'][0],initial)
            np.testing.assert_array_equal(n['left_end'],n['right_start'])
            np.testing.assert_array_equal(n['states'][360],n['left_end'])
            assert n['left_times'][0]==0 and n['left_times'][-1]==21600
            assert n['right_times'][0]==21600 and n['right_times'][-1]==43200
        m=json.loads((directory/f'{name}_base_runtime.json').read_text())
        assert m['all_density_queries_valid'] and m['actual_rhs_time_domains']==[[0.,21600.],[21600.,43200.]]
        assert m['event_records'][0]['position_jump_m']==0 and m['event_records'][0]['velocity_jump_m_s']==0
        checked.append(name)
    with np.load(directory/'B_Open_base_states_local.npz') as b,np.load(directory/'C_Updated_base_states_local.npz') as c:
        np.testing.assert_array_equal(b['states'][:361],c['states'][:361])
    return dict(status='PASS',checked=checked,finite_complete_continuous=True,pre_event_B_C_bitwise_equal=True,Tight_permitted=True)


def worker():
    from orbit.common_force_model import CommonForceModel
    from orbit.drag import DragForce,DragProperties,EarthFixedFrame
    from orbit.two_body import make_state_derivative
    from orbit.event_segments import propagate_event_segments
    if (F/'worker_once.json').exists():raise FileExistsError('No automatic retry')
    dump(F/'worker_once.json',dict(start=time.time(),trajectories=8))
    protocol=json.loads((F/'protocol.json').read_text());prepare_wall=json.loads((F/'preflight.json').read_text())['prepare_wall_s'];assert json.loads((F/'preflight.json').read_text())['status']=='PASS'
    assert all(sha(ROOT/p)==h for p,h in json.loads((F/'protected_runtime_v2.json').read_text()).items())
    started=time.perf_counter();configure_time_data();epoch=Time(EPOCH);force=CommonForceModel(epoch,43200);frame=EarthFixedFrame(epoch)
    atmosphere=providers();a=protocol['aero'];props=DragProperties(a['mass_kg'],a['area_m2'],a['Cd'],LABELS)
    initial=np.load(F/'initial_GCRS_local.npy');output=np.arange(0,43201,60);performance=[]
    def guard():
        if time.perf_counter()-started>10500-prepare_wall-120:raise RuntimeError('10500s shared budget')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>4*1024**2:raise RuntimeError('RSS limit')
        if shutil.disk_usage(ROOT).free<20*2**30:raise RuntimeError('Disk floor')
    for mode in ('base','tight'):
        if mode=='tight':
            gate=validate_base(F,protocol,initial)
            dump(F/'base_gate.json',gate)
            if gate['status']!='PASS':raise RuntimeError('Base incomplete; Tight blocked')
            elapsed=time.perf_counter()-started
            remaining=10500-json.loads((F/'preflight.json').read_text())['prepare_wall_s']-elapsed
            estimated=sum(x['total_with_diagnostics_s'] for x in performance)*2.15+120
            dump(F/'tight_budget_gate.json',dict(remaining_s=remaining,estimated_tight_and_validation_s=estimated,passed=estimated<=remaining))
            if estimated>remaining:raise RuntimeError('Tight resource prediction exceeds remaining authorized budget; Base retained')
        for name in protocol['groups']:
            guard();dump(F/f'{name}_{mode}_launch.json',dict(mode=mode,name=name,labels=LABELS))
            records=[];drags=[];rhs=[];rhs_ranges=[[],[]];progress=[time.perf_counter()]
            for side in ('left','right'):
                drag=None
                if name!='A_NoDrag':
                    p=atmosphere[name].before if side=='left' else atmosphere[name].after
                    bridge=ProvisionalEventBridge(p,authorization_label=LABEL,branch_label=side,records=records)
                    drag=DragForce(frame,bridge,props)
                drags.append(drag);rhs.append(make_state_derivative([force] if drag is None else [force,drag]))
            def factory(i):
                def fun(t,y):
                    guard();rhs_ranges[i].append(float(t))
                    if time.perf_counter()-progress[0]>=45:
                        print('PROGRESS',name,mode,'seconds',t,'elapsed',time.perf_counter()-started,flush=True);progress[0]=time.perf_counter()
                    return rhs[i](t,y)
                return fun
            print('BEGIN',name,mode,flush=True);tick=time.perf_counter()
            try:
                solution=propagate_event_segments(factory,initial[:3],initial[3:],(0,43200),output,[21600],**protocol[mode])
                integration_s=time.perf_counter()-tick
                np.savez_compressed(inside(F/f'{name}_{mode}_states_local.npz'),seconds=output,states=solution.states,
                    left_times=solution.segments[0].internal_times_s,right_times=solution.segments[1].internal_times_s,
                    left_end=solution.segments[0].states[-1],right_start=solution.segments[1].states[0])
                n_rhs_queries=len(records);samples=[]
                for t,y in zip(output,solution.states):
                    i=int(t>=21600);drag=drags[i];z=drag.evaluate(t,y[:3],y[3:]) if drag else None
                    samples.append(dict(group=name,mode=mode,seconds=int(t),UTC=(epoch+TimeDelta(t,format='sec')).isot,
                        rho_kg_m3=z['density_kg_m3'] if z else None,drag_norm_m_s2=float(np.linalg.norm(z['acceleration_gcrs_m_s2'])) if z else 0.,
                        drag_x=z['acceleration_gcrs_m_s2'][0] if z else 0.,drag_y=z['acceleration_gcrs_m_s2'][1] if z else 0.,drag_z=z['acceleration_gcrs_m_s2'][2] if z else 0.))
                table(O/f'{name}_{mode}_samples.csv',samples)
                y=solution.segments[0].states[-1];limits=[]
                for i,side in enumerate(('left','right')):
                    z=drags[i].evaluate(21600,y[:3],y[3:]) if drags[i] else None
                    limits.append(dict(side=side,rho_kg_m3=z['density_kg_m3'] if z else None,
                        drag_gcrs_m_s2=z['acceleration_gcrs_m_s2'].tolist() if z else [0.,0.,0.],
                        drag_norm_m_s2=float(np.linalg.norm(z['acceleration_gcrs_m_s2'])) if z else 0.))
                total=time.perf_counter()-tick;stat=dict(group=name,mode=mode,integration_s=integration_s,total_with_diagnostics_s=total,
                    nfev=sum(s.statistics['nfev'] for s in solution.segments),segment_stats=[s.statistics for s in solution.segments],
                    event_records=solution.event_records,event_density_drag_limits=limits,
                    RHS_count_with_event_diagnostics=sum(len(v) for v in rhs_ranges),
                    actual_rhs_time_domains=[[min(v),max(v)] for v in rhs_ranges],
                    rhs_density_queries=n_rhs_queries,all_density_queries=len(records),all_density_queries_valid=all(r['valid'] for r in records),
                    query_elapsed_s=sum(r['query_s'] for r in records),peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
                dump(F/f'{name}_{mode}_runtime.json',stat);performance.append(stat)
            finally:
                if records:table(F/f'{name}_{mode}_queries_local.csv',records)
            guard();print('END',name,mode,stat['integration_s'],flush=True)
            if sum(p.stat().st_size for p in F.rglob('*') if p.is_file())>200*2**20:raise RuntimeError('Output size guard')
    dump(F/'worker_complete.json',dict(status='PASS',wall_s=time.perf_counter()-started,runs=performance,labels=LABELS))
    print('WORKER_COMPLETE',time.perf_counter()-started,flush=True)


def supervise():
    if (F/'supervisor_once.json').exists():raise FileExistsError('Formal supervisor tag already used')
    dump(F/'supervisor_once.json',dict(trajectories=8,no_retry=True))
    begin=time.perf_counter();peak=0;reason=None;prepare_wall=json.loads((F/'preflight.json').read_text())['prepare_wall_s']
    with inside(ROOT/'logs/fourcastden_orbit_update_12h_v1_worker.log').open('x') as log:
        p=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'worker'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        while p.poll() is None:
            def rss_tree(pid):
                try:
                    lines=Path(f'/proc/{pid}/status').read_text().splitlines()
                    rss=next((int(x.split()[1])*1024 for x in lines if x.startswith('VmRSS:')),0)
                    children=Path(f'/proc/{pid}/task/{pid}/children').read_text().split()
                    return rss+sum(rss_tree(int(child)) for child in children)
                except (FileNotFoundError,ProcessLookupError):return 0
            rss=rss_tree(os.getpid())
            peak=max(peak,rss)
            if time.perf_counter()-begin>10500-prepare_wall-120 or rss>4*2**30:
                reason='SUPERVISOR_RESOURCE_LIMIT';os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=10);break
            time.sleep(.5)
    dump(F/'supervision.json',dict(exit_code=p.returncode,reason=reason,wall_s=time.perf_counter()-begin,peak_tree_RSS_bytes=peak,status='PASS' if p.returncode==0 and reason is None else 'FAIL'))
    if p.returncode!=0:raise RuntimeError('Formal run failed; no retry; inspect retained log')
    print((F/'supervision.json').read_text())


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['prepare','worker','supervise']);a=ap.parse_args()
    try:globals()[a.phase]()
    except Exception:
        traceback.print_exc();raise
