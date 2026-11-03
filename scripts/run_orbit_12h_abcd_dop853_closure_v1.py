"""Only D reference DOP853 30/15; staged resource and physical-domain guards."""
from pathlib import Path
import sys,json,time,resource,subprocess,os,signal,shutil,argparse,csv
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from prepare_fourcastden_swarm_observation_v1 import sha,dump,inside
from analyze_fourcastden_swarm_observation_v1 import table
from run_fourcastden_orbit_update_event_v1 import providers,LABELS
from atmosphere.provisional_event_bridge import ProvisionalEventBridge,LABEL
from atmosphere.tiegcm_density_provider import DATUM
from astropy.time import Time,TimeDelta
F=ROOT/'experiments/orbit_12h_abcd_dop853_closure_v1';O=ROOT/'results/orbit_12h_abcd_dop853_closure_v1';OLD=ROOT/'experiments/fourcastden_orbit_update_12h_v1';A=ROOT/'experiments/orbit_12h_numerical_reference_v1';TIMES=np.arange(0,43201,60);GROUPS=['D_Reference']

def validate_stage(directory,mode,initial):
    for g in GROUPS:
        with np.load(directory/f'{g}_{mode}_states_local.npz') as n:
            assert n['states'].shape==(721,6) and np.isfinite(n['states']).all();np.testing.assert_array_equal(n['seconds'],TIMES);np.testing.assert_array_equal(n['states'][0],initial);np.testing.assert_array_equal(n['left_end'],n['right_start']);np.testing.assert_array_equal(n['states'][360],n['left_end'])
        m=json.loads((directory/f'{g}_{mode}_runtime.json').read_text());assert m['all_queries_valid'] and m['RHS_domains']==[[0.,21600.],[21600.,43200.]];assert m['event_records'][0]['position_jump_m']==m['event_records'][0]['velocity_jump_m_s']==0
    return dict(status='PASS',groups=GROUPS,mode=mode,records_per_run=721,event_continuous=True)

def prepare():
    begin=time.perf_counter();assert not (F/'protocol.json').exists()
    protected=json.loads((A/'protected.json').read_text());assert all(sha(ROOT/k)==v for k,v in protected.items())
    inventory=json.loads((OLD/'local_output_inventory.json').read_text());assert all(sha(ROOT/x['path'])==x['SHA256'] for x in inventory['files'])
    for name in ['DOP30','DOP15']:
        m=json.loads((A/f'{name}_runtime.json').read_text());assert sha(A/f'{name}_states_local.npz')==m['states_SHA']
    for parent in [A,ROOT/'results/orbit_12h_numerical_reference_v1']:
        for q in parent.rglob('*'):
            if q.is_file():protected[str(q.relative_to(ROOT))]=sha(q)
    bc=ROOT/'experiments/orbit_12h_bc_dop853_validation_v1'
    for g in ['B_Open','C_Updated']:
        for mode in ['DOP30','DOP15']:
            q=bc/f'{g}_{mode}_states_local.npz';m=json.loads((bc/f'{g}_{mode}_runtime.json').read_text());assert sha(q)==m['state_SHA']
    for parent in [bc,ROOT/'results/orbit_12h_bc_dop853_validation_v1']:
        for q in parent.rglob('*'):
            if q.is_file():protected[str(q.relative_to(ROOT))]=sha(q)
    ap=json.loads((A/'protocol.json').read_text());controls=json.loads((OLD/'protocol.json').read_text());disk=shutil.disk_usage(ROOT).free;assert disk>20*2**30
    p=dict(tag=F.name,epoch=ap['epoch'],duration_s=43200,event_s=21600,output_s=60,groups=GROUPS,case_order=['D_Reference DOP30','D_Reference DOP15'],rtol=ap['rtol'],atol=ap['atol'],max_steps={'DOP30':30.,'DOP15':15.},aero=controls['aero'],single_gate_m=.02,paired_gate_fraction=.01,labels=LABELS,limits=dict(wall_s=6800,RSS_GiB=4,output_MiB=50,free_disk_GiB=20),estimate=dict(expected_s=4513,safety_s=6769,peak_RSS_GiB=1,output_MiB=45),initial_file=ap['initial_state_file'],initial_SHA=ap['initial_SHA'],NoDrag_reused=True,D_new_runs=2,no_new_forward=True,no_new_TIE=True,old_numeric_gate='FAIL_UNCHANGED',real_orbit='BLOCKED',science_training=False)
    assert sha(ROOT/p['initial_file'])==p['initial_SHA'];dump(F/'protocol.json',p)
    snapshot=dict(free_disk_bytes=disk,meminfo=Path('/proc/meminfo').read_text(),processes=subprocess.check_output(['ps','-eo','pid,pcpu,pmem,comm','--sort=-pcpu'],text=True).splitlines()[:12]);dump(F/'resource_preflight.json',snapshot)
    ev=providers();coverage=[]
    for g in GROUPS:
        for side,prov in [('left',ev[g].before),('right',ev[g].after)]:
            assert prov.valid.all();coverage.append(dict(group=g,branch=side,frames=len(prov.epochs),start=prov.epochs[0].isot,stop=prov.epochs[-1].isot,invalid_column_times=int((~prov.valid).sum()),min_top_m=float(prov.height[:,-1][prov.valid].min()),max_bottom_m=float(prov.height[:,0][prov.valid].max()),units='kg/m3 and native ZG m'))
    table(O/'field_coverage.csv',coverage)
    path=OLD/'SP3_coverage_local.csv';protected[str(path.relative_to(ROOT))]=sha(path);rows=[]
    # Requery the actual prior SP3-derived native-hypothesis path, not a fixed height.
    with path.open() as file:
        for r in csv.DictReader(file):
            if r['group'] not in GROUPS:continue
            g=r['group'];pr=ev[g].before if r['branch']=='left' else ev[g].after;t=Time(r['UTC'],scale='utc');h=float(r['assumed_native_ZG_m']);out=pr.query_native(t,float(r['lat']),float(r['lon']),h,datum=DATUM)
            rows.append(dict(group=g,UTC=t.isot,branch=r['branch'],valid=out.valid,reason=out.reason,rho_kg_m3=out.rho_kg_m3,min_top_margin_m=out.metadata.get('height_coverage_m',[None,None])[1]-h if out.valid else None))
            if not out.valid:
                table(F/'failed_precheck_local.csv',rows);raise ValueError('SP3 precheck failure '+g+' '+t.isot+' '+out.reason)
    table(F/'SP3_precheck_local.csv',rows);assert len(rows)==4323
    for q in [Path(__file__).resolve(),ROOT/'src/orbit/dop853_events.py',ROOT/'tests/test_dop853_events.py']:
        protected[str(q.relative_to(ROOT))]=sha(q)
    dump(F/'protected.json',protected);dump(F/'preflight.json',dict(status='PASS',queries=len(rows),valid_queries=len(rows),old_output_SHA_verified=len(inventory['files']),NoDrag_references_verified=2,minimum_top_margin_m=min(x['min_top_margin_m'] for x in rows),preparation_s=time.perf_counter()-begin,SP3_path_is_necessary_not_online_guarantee=True))
    print((F/'preflight.json').read_text())

def worker():
    from orbit.frames import configure_time_data
    from orbit.common_force_model import CommonForceModel
    from orbit.drag import EarthFixedFrame,DragForce,DragProperties
    from orbit.two_body import make_state_derivative
    from orbit.dop853_events import propagate_dop853_events
    assert not (F/'worker_once.json').exists();dump(F/'worker_once.json',dict(start=time.time(),new_trajectories=2,no_retry=True));p=json.loads((F/'protocol.json').read_text());assert json.loads((F/'preflight.json').read_text())['status']=='PASS';assert all(sha(ROOT/k)==v for k,v in json.loads((F/'protected.json').read_text()).items())
    configure_time_data();epoch=Time(p['epoch']);force=CommonForceModel(epoch,43200);frame=EarthFixedFrame(epoch);ev=providers();initial=np.load(ROOT/p['initial_file']);a=p['aero'];props=DragProperties(a['mass_kg'],a['area_m2'],a['Cd'],LABELS);begin=time.perf_counter();runs=[]
    def guard():
        if time.perf_counter()-begin>6740:raise RuntimeError('6800s budget guard; preserve partials')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>4*1024**2:raise RuntimeError('4GiB RSS')
    for mode in ['DOP30','DOP15']:
        if mode=='DOP15':
            dump(F/'DOP30_gate.json',validate_stage(F,'DOP30',initial));remaining=6800-(time.perf_counter()-begin);estimate=2.15*sum(x['total_s'] for x in runs)+90;dump(F/'DOP15_budget_gate.json',dict(remaining_s=remaining,expected_s=estimate,passed=estimate<=remaining))
            if estimate>remaining:dump(F/'partial_complete.json',dict(reason='insufficient remaining budget',runs=runs));return
        for group in GROUPS:
            guard();dump(F/f'{group}_{mode}_launch.json',dict(group=group,mode=mode,start=time.time()));records=[];drags=[];rhs=[];ranges=[[],[]];progress=[time.perf_counter()]
            for side,prov in [('left',ev[group].before),('right',ev[group].after)]:
                bridge=ProvisionalEventBridge(prov,authorization_label=LABEL,branch_label=side,records=records);drag=DragForce(frame,bridge,props);drags.append(drag);rhs.append(make_state_derivative([force,drag]))
            def factory(i):
                def fun(t,y):
                    guard();ranges[i].append(float(t))
                    if time.perf_counter()-progress[0]>=45:print('PROGRESS',group,mode,'seconds',t,'elapsed_s',time.perf_counter()-begin,flush=True);progress[0]=time.perf_counter()
                    return rhs[i](t,y)
                return fun
            print('BEGIN',group,mode,flush=True);tick=time.perf_counter()
            try:
                sol=propagate_dop853_events(factory,initial[:3],initial[3:],(0.,43200.),TIMES,[21600.],rtol=p['rtol'],atol=p['atol'],max_step=p['max_steps'][mode]);integration=time.perf_counter()-tick
                np.savez_compressed(inside(F/f'{group}_{mode}_states_local.npz'),seconds=TIMES,states=sol.states,left_times=sol.segments[0].internal_times_s,right_times=sol.segments[1].internal_times_s,left_end=sol.segments[0].states[-1],right_start=sol.segments[1].states[0]);rhs_queries=len(records);samples=[]
                for t,y in zip(TIMES,sol.states):
                    z=drags[int(t>=21600)].evaluate(t,y[:3],y[3:]);aa=z['acceleration_gcrs_m_s2'];samples.append(dict(group=group,mode=mode,seconds=int(t),UTC=(epoch+TimeDelta(t,format='sec')).isot,rho_kg_m3=z['density_kg_m3'],drag_norm_m_s2=float(np.linalg.norm(aa)),drag_x=float(aa[0]),drag_y=float(aa[1]),drag_z=float(aa[2]),relative_speed_m_s=float(np.linalg.norm(z['relative_velocity_itrs_m_s']))))
                table(O/f'{group}_{mode}_samples.csv',samples);limits=[];y=sol.segments[0].states[-1]
                for i,side in enumerate(['left','right']):
                    z=drags[i].evaluate(21600,y[:3],y[3:]);limits.append(dict(side=side,rho_kg_m3=z['density_kg_m3'],drag_gcrs_m_s2=z['acceleration_gcrs_m_s2'].tolist(),drag_norm_m_s2=float(np.linalg.norm(z['acceleration_gcrs_m_s2']))))
                m=dict(group=group,mode=mode,total_s=time.perf_counter()-tick,integration_s=integration,nfev=sum(x.statistics['nfev'] for x in sol.segments),segments=[x.statistics for x in sol.segments],event_records=sol.event_records,event_limits=limits,RHS_domains=[[min(x),max(x)] for x in ranges],RHS_calls=sum(map(len,ranges)),RHS_density_queries=rhs_queries,all_density_queries=len(records),all_queries_valid=all(r['valid'] for r in records),query_s=sum(r['query_s'] for r in records),peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,state_SHA=sha(F/f'{group}_{mode}_states_local.npz'));dump(F/f'{group}_{mode}_runtime.json',m);runs.append(m);print('END',group,mode,m['total_s'],flush=True)
            finally:
                if records:table(F/f'{group}_{mode}_queries_local.csv',records)
            guard()
            if sum(q.stat().st_size for q in F.rglob('*') if q.is_file())>50*2**20:raise RuntimeError('50MiB output guard')
    dump(F/'DOP15_gate.json',validate_stage(F,'DOP15',initial));dump(F/'worker_complete.json',dict(status='PASS',wall_s=time.perf_counter()-begin,runs=runs))

def supervise():
    assert not (F/'supervisor_once.json').exists();dump(F/'supervisor_once.json',dict(start=time.time(),wall_limit_s=6800,no_retry=True));begin=time.perf_counter();peak=0;reason=None
    def rss(pid):
        try:
            s=Path(f'/proc/{pid}/status').read_text().splitlines();v=next(int(x.split()[1])*1024 for x in s if x.startswith('VmRSS:'));c=Path(f'/proc/{pid}/task/{pid}/children').read_text().split();return v+sum(rss(int(k)) for k in c)
        except (FileNotFoundError,StopIteration,ProcessLookupError):return 0
    with inside(ROOT/'logs/orbit_12h_abcd_dop853_closure_v1_worker.log').open('x') as log:
        child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'worker'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        while child.poll() is None:
            peak=max(peak,rss(os.getpid()))
            if time.perf_counter()-begin>6790 or peak>4*2**30 or shutil.disk_usage(ROOT).free<20*2**30:
                reason='RESOURCE_LIMIT';os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=10);break
            time.sleep(.5)
    dump(F/'supervision.json',dict(exit_code=child.returncode,reason=reason,wall_s=time.perf_counter()-begin,peak_tree_RSS_bytes=peak,status='PASS' if child.returncode==0 and reason is None else 'FAIL'))
    if child.returncode:raise RuntimeError('Failure retained; no retry')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','worker','supervise']);args=p.parse_args();globals()[args.phase]()
