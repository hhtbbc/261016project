"""Offline controlled central vs central+J2 experiment; no parameter fitting."""
from pathlib import Path
import sys, json, argparse, hashlib, csv, unittest, platform, importlib.metadata
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
import numpy as np
import matplotlib.pyplot as plt
from astropy.time import Time, TimeDelta
from orbit.two_body import EARTH_MU, central_gravity, make_state_derivative
from orbit.j2 import J2_COEFFICIENT, J2_REFERENCE_RADIUS_M, j2_acceleration, terrestrial_z_in_gcrs, EarthFigureAxis
from orbit.rk45_propagator import propagate
from orbit.frames import configure_time_data, transform_state, check_eop
from evaluation.orbit_data import load_sp3_reference
from evaluation.orbit_metrics import rac_errors, summarize_errors
from test_j2 import J2Tests, fixed_axis_experiment


def write_json(path,value):
    with path.open('x') as f:json.dump(value,f,ensure_ascii=False,indent=2)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-tag',default='rk45_j2_v1');args=parser.parse_args();tag=args.run_tag
    if not tag or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in tag):raise ValueError('Invalid tag')
    for p in ['src','tests','experiments','results/figures','results/metrics','logs','data/raw','reports']:
        if not (ROOT/p).resolve().is_relative_to(ROOT):raise ValueError('Path outside workspace')
    output=ROOT/'experiments'/tag;output.mkdir(exist_ok=False)
    protected=[p for parent in ['data/raw/orbits','data/raw/earth_orientation','experiments','results/figures','results/metrics','reports'] for p in (ROOT/parent).rglob('*') if p.is_file() and not p.is_relative_to(output)]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    write_json(output/'preserved_inputs.json',hashes)
    # Physical and frame tests gate access to the real experiment.
    checks=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(J2Tests))
    if not checks.wasSuccessful():raise RuntimeError('Independent J2 tests failed; real experiment blocked')
    fixed,fixed_stats,energy,hz,raan=fixed_axis_experiment()
    np.savez_compressed(output/'fixed_axis_validation.npz',elapsed_s=fixed.times_s,states=fixed.states,total_specific_energy_j_kg=energy,axial_specific_h_m2_s=hz,raan_rad=raan)
    print('Independent validation',json.dumps(fixed_stats,indent=2),flush=True)
    table,time_metadata=configure_time_data()
    t0=Time('2023-03-21T00:00:02',scale='utc');elapsed=np.arange(0.,172801.,60.)
    times=t0+TimeDelta(elapsed,format='sec')
    reference=load_sp3_reference((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))
    if reference.frame!='IGS20':raise ValueError('Unverified SP3 frame')
    ref=reference.take_exact(times);initial=reference.take_exact(times[:1])
    r0,v0=transform_state(initial.positions_m,initial.velocities_m_s,times[:1],'ITRS','GCRS')
    prior_meta=json.loads((ROOT/'experiments/rk45_two_body_v1/summary.json').read_text())
    np.testing.assert_array_equal(r0[0],prior_meta['initial_gcrs_m']);np.testing.assert_array_equal(v0[0],prior_meta['initial_gcrs_m_s'])
    axis=EarthFigureAxis(t0,172800.,cadence_s=60.)
    mids=(axis.grid_s[:-1]+axis.grid_s[1:])/2
    direct=terrestrial_z_in_gcrs(t0+TimeDelta(mids,format='sec'))
    interpolation_error=np.linalg.norm(np.array([axis(t) for t in mids])-direct,axis=1)
    if interpolation_error.max()>1e-11:raise RuntimeError('Axis interpolation failed')
    rhs_A=make_state_derivative([central_gravity]);rhs_B=make_state_derivative([central_gravity,axis.acceleration])
    A=propagate(rhs_A,r0[0],v0[0],(0,172800),elapsed)
    B=propagate(rhs_B,r0[0],v0[0],(0,172800),elapsed)
    tight=propagate(rhs_B,r0[0],v0[0],(0,172800),elapsed,rtol=1e-12,atol=[1e-5]*3+[1e-8]*3,max_step=15.)
    old=np.load(ROOT/'experiments/rk45_two_body_v1/states.npz')
    np.testing.assert_array_equal(A.states,old['gcrs_states'])
    np.testing.assert_array_equal(A.times_s,old['elapsed_s'])
    if np.max(abs((Time(old['utc_jd1'],old['utc_jd2'],format='jd',scale='utc')-times).sec))>1e-6:raise ValueError('Previous time grid mismatch')
    rg,vg=transform_state(ref.positions_m,ref.velocities_m_s,times,'ITRS','GCRS')
    results={};norms={};racs={};terrestrial={}
    for name,run in [('A_central',A),('B_central_J2',B)]:
        p,v=transform_state(run.states[:,:3],run.states[:,3:],times,'GCRS','ITRS')
        delta=p-ref.positions_m;rac=rac_errors(run.states[:,:3]-rg,rg,vg)
        error=np.linalg.norm(delta,axis=1)
        np.testing.assert_allclose(np.linalg.norm(rac,axis=1),error,atol=1e-5,rtol=1e-10)
        if not np.isfinite(error).all():raise ValueError('Nonfinite errors')
        results[name]={'metrics':summarize_errors(delta,rac),'integration':run.statistics,
                       'hourly_error_m':{str(h):float(error[h*60]) for h in [1,3,6,12,24,48]},
                       'max_error_utc':times[int(np.argmax(error))].utc.isot,
                       'rac_mse_fraction':(np.mean(rac**2,axis=0)/np.mean(error**2)).tolist()}
        norms[name]=error;racs[name]=rac;terrestrial[name]=(p,v)
    position_diff=np.linalg.norm(B.states[:,:3]-tight.states[:,:3],axis=1)
    velocity_diff=np.linalg.norm(B.states[:,3:]-tight.states[:,3:],axis=1)
    # Direct-vs-interpolated direction check at every midpoint, and empirical
    # acceleration sensitivity there, evaluated on the independent tight orbit.
    mid_states=tight.dense_solution(mids).T
    acceleration_differences=np.array([np.linalg.norm(j2_acceleration(y[:3],axis(t))-j2_acceleration(y[:3],k)) for t,y,k in zip(mids,mid_states,direct)])
    if position_diff.max()>10:raise RuntimeError('J2 numerical convergence difference exceeds pre-set 10 m threshold')
    accel_table=[]
    for label,r in [('equator_400km',[6778137.,0,0]),('axis_400km',[0,0,6778137.]),('45deg_400km',np.array([1.,0,1.])*6778137/np.sqrt(2)),('equator_double_radius',[13556274.,0,0])]:
        g=central_gravity(0,r,None);j=j2_acceleration(r)
        accel_table.append({'location':label,'position_axis_frame_m':np.asarray(r).tolist(),'central_m_s2':g.tolist(),'j2_m_s2':j.tolist(),'central_norm_m_s2':float(np.linalg.norm(g)),'j2_norm_m_s2':float(np.linalg.norm(j)),'ratio':float(np.linalg.norm(j)/np.linalg.norm(g))})
    # Same machine, paired short repeats. Each is a full 48 h CPU integration;
    # times below exclude EOP setup, transforms, evaluation, and plotting.
    timings={'A_central':[A.statistics['elapsed_s']],'B_central_J2':[B.statistics['elapsed_s']]}
    for _ in range(2):
        for name,rhs in [('A_central',rhs_A),('B_central_J2',rhs_B)]:
            bench=propagate(rhs,r0[0],v0[0],(0,172800),elapsed)
            timings[name].append(bench.statistics['elapsed_s'])
    summary={'status':'passed','constants':{'mu_m3_s2':EARTH_MU,'J2':J2_COEFFICIENT,'J2_reference_radius_m':J2_REFERENCE_RADIUS_M,'source':'https://hpiers.obspm.fr/eop-pc/index.php?index=constants&lang=en','tide_convention':'nominal zero-tide IERS J2; fixed scalar, no secular/time-variable geopotential'},
        'start_utc':times[0].utc.isot,'end_utc':times[-1].utc.isot,'initial_gcrs_position_m':r0[0].tolist(),'initial_gcrs_velocity_m_s':v0[0].tolist(),
        'initialization':'same single native SP3 P/V epoch as preserved two-body baseline; no refitting or updates',
        'sp3_metadata':ref.metadata,'time_data':time_metadata,'eop':check_eop(times,table),'fixed_axis_validation':fixed_stats,
        'axis_model':{'definition':'ITRS figure Z expressed in GCRS; ERFA c2t06a (IAU 2006/2000A), TT/UT1/xp/yp; no observed dX/dY correction, consistent with Astropy','interpolation':'normalized cubic spline, 60 s grid, no extrapolation',
        'initial_direction_gcrs':axis(0).tolist(),'final_direction_gcrs':axis(172800).tolist(),'initial_tilt_from_gcrs_z_deg':float(np.rad2deg(np.arccos(axis(0)[2]))),
        'max_midpoint_direction_difference':float(interpolation_error.max()),'max_midpoint_acceleration_difference_m_s2':float(acceleration_differences.max())},
        'experiments':results,'convergence':{'max_position_difference_m':float(position_diff.max()),'terminal_position_difference_m':float(position_diff[-1]),'max_velocity_difference_m_s':float(velocity_diff.max()),'tight_integration':tight.statistics,'threshold_m':10,'passed':True},
        'timings':{name:{'samples_s':values,'median_s':float(np.median(values))} for name,values in timings.items()},
        'typical_accelerations':accel_table,'A_identical_to_preserved_baseline':True,
        'versions':{name:importlib.metadata.version(name) for name in ['numpy','scipy','astropy','pyerfa','matplotlib']},'python':platform.python_version()}
    a=results['A_central']['metrics'];b=results['B_central_J2']['metrics']
    summary['comparison']={'rmse_reduction_percent':100*(1-b['rmse_3d_m']/a['rmse_3d_m']),'terminal_reduction_percent':100*(1-b['terminal_m']/a['terminal_m']),
        'B_better_samples':int(np.sum(norms['B_central_J2']<norms['A_central'])),'samples':len(elapsed),
        'rac_rmse_reduction_percent':(100*(1-np.array(b['rac_rmse_m'])/a['rac_rmse_m'])).tolist()}
    np.savez_compressed(output/'states.npz',elapsed_s=elapsed,utc_jd1=times.utc.jd1,utc_jd2=times.utc.jd2,A_gcrs_states=A.states,B_gcrs_states=B.states,tight_gcrs_states=tight.states,A_itrs_position_m=terrestrial['A_central'][0],B_itrs_position_m=terrestrial['B_central_J2'][0],sp3_itrs_position_m=ref.positions_m,sp3_gcrs_position_m=rg,sp3_gcrs_velocity_m_s=vg,A_rac_m=racs['A_central'],B_rac_m=racs['B_central_J2'],axis_grid_s=axis.grid_s,axis_grid_gcrs=axis.directions,A_internal_times_s=A.internal_times_s,B_internal_times_s=B.internal_times_s)
    with (ROOT/f'results/metrics/{tag}_errors.csv').open('x',newline='') as f:
        writer=csv.writer(f);writer.writerow(['utc','elapsed_s','A_3d_m','B_3d_m','A_R_m','A_A_m','A_C_m','B_R_m','B_A_m','B_C_m','B_tight_position_difference_m','B_tight_velocity_difference_m_s'])
        writer.writerows([times[i].utc.isot,elapsed[i],norms['A_central'][i],norms['B_central_J2'][i],*racs['A_central'][i],*racs['B_central_J2'][i],position_diff[i],velocity_diff[i]] for i in range(len(elapsed)))
    with (ROOT/f'results/metrics/{tag}_timings.csv').open('x',newline='') as f:
        writer=csv.writer(f);writer.writerow(['model','accepted_steps','nfev','integration_elapsed_s','median_3_runs_s'])
        for name in results:
            z=results[name]['integration'];writer.writerow([name,z['accepted_steps'],z['nfev'],z['elapsed_s'],summary['timings'][name]['median_s']])
    write_json(output/'accelerations.json',accel_table)
    def save(name):
        path=ROOT/f'results/figures/{tag}_{name}.png'
        if path.exists():raise FileExistsError(path)
        plt.tight_layout();plt.savefig(path,dpi=160);plt.close()
    plt.figure()
    for name in norms:plt.plot(elapsed[1:]/3600,norms[name][1:]/1000,label=name)
    plt.yscale('log');plt.xlabel('Prediction time (h)');plt.ylabel('3D position difference (km, log)');plt.title('Swarm-A vs SP3: identical single-epoch P/V initialization');plt.legend();plt.grid();save('position_comparison')
    fig,axes=plt.subplots(3,1,figsize=(9,9),sharex=True)
    for j,label in enumerate(['Radial R','Along-track A','Normal C']):
        for name in racs:axes[j].plot(elapsed/3600,racs[name][:,j]/1000,label=name)
        axes[j].set_ylabel(label+' (km)');axes[j].legend();axes[j].grid()
    axes[-1].set_xlabel('Prediction time (h)');fig.suptitle('Predicted minus SP3: reference GCRS RAC');save('rac_comparison')
    fig,axes=plt.subplots(2,1,sharex=True)
    axes[0].plot(elapsed/3600,position_diff,label='Baseline minus tight, position');axes[0].set_ylabel('Position difference (m)')
    axes[1].plot(elapsed/3600,velocity_diff,label='Baseline minus tight, velocity');axes[1].set_ylabel('Velocity difference (m/s)');axes[1].set_xlabel('Prediction time (h)')
    for ax in axes:ax.legend();ax.grid()
    fig.suptitle('J2 numerical convergence: rtol 1e-10/30 s vs 1e-12/15 s');save('convergence')
    plt.figure(figsize=(9,5));x=np.arange(len(accel_table));plt.bar(x-.18,[v['central_norm_m_s2'] for v in accel_table],width=.36,label='Central');plt.bar(x+.18,[v['j2_norm_m_s2'] for v in accel_table],width=.36,label='J2 perturbation');plt.xticks(x,[v['location'] for v in accel_table],rotation=15);plt.yscale('log');plt.ylabel('Acceleration norm (m/s², log)');plt.title('Analytical positions in the J2 symmetry-axis frame');plt.legend();save('accelerations')
    fig,axes=plt.subplots(3,1,figsize=(8,9),sharex=True)
    axes[0].plot(fixed.times_s/3600,(energy-energy[0])/abs(energy[0]),label='Total central + J2 energy');axes[0].set_ylabel('Relative energy drift')
    axes[1].plot(fixed.times_s/3600,(hz-hz[0])/abs(hz[0]),label='Axial angular momentum');axes[1].set_ylabel('Relative axial h drift')
    theory=np.deg2rad(fixed_stats['raan_theory_deg_day'])/86400
    axes[2].plot(fixed.times_s/3600,np.rad2deg(raan-raan[0]),label='Numerical osculating RAAN');axes[2].plot(fixed.times_s/3600,np.rad2deg(theory*fixed.times_s),'--',label='First-order secular theory');axes[2].set_ylabel('Node change (deg)');axes[2].set_xlabel('Elapsed time (h)')
    for ax in axes:ax.legend();ax.grid()
    fig.suptitle('Independent fixed-axis validation: 7000 km, e=0.01, i=55 deg');save('fixed_axis_validation')
    plt.figure()
    for j,label in enumerate(['R','A','C']):plt.plot(elapsed/3600,racs['B_central_J2'][:,j]/1000,label=label)
    plt.xlabel('Prediction time (h)');plt.ylabel('Signed position difference (km)');plt.title('J2 residual RAC vs SP3 (same initialization)');plt.legend();plt.grid();save('j2_residual_rac')
    summary['preserved_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in hashes.items())
    if not summary['preserved_hashes_unchanged']:raise RuntimeError('Existing experiment/input modified')
    write_json(output/'summary.json',summary)
    print(json.dumps({k:summary[k] for k in ['experiments','comparison','convergence','axis_model','timings']},indent=2),flush=True)

if __name__=='__main__':main()
