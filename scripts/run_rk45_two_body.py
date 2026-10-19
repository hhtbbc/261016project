"""Offline circle verification then single-initialization Swarm propagation."""
from pathlib import Path
import sys, json, argparse, hashlib, csv, platform
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import scipy
from scipy.optimize import brentq
import matplotlib.pyplot as plt
from astropy.time import Time, TimeDelta
from orbit.two_body import EARTH_MU, EARTH_EQUATORIAL_RADIUS, two_body_rhs, invariants
from orbit.rk45_propagator import propagate
from orbit.frames import configure_time_data, transform_state, check_eop
from evaluation.orbit_data import load_sp3_reference
from evaluation.orbit_metrics import rac_errors, summarize_errors


def circle_case(rtol, position_atol, max_step):
    radius=EARTH_EQUATORIAL_RADIUS+400000
    speed=np.sqrt(EARTH_MU/radius); period=2*np.pi*np.sqrt(radius**3/EARTH_MU)
    initial=np.array([radius,0,0,0,speed,0.])
    times=np.linspace(0,10*period,2001)
    run=propagate(two_body_rhs,initial[:3],initial[3:],(0,10*period),times,
                  rtol=rtol,atol=[position_atol]*3+[position_atol/1000]*3,max_step=max_step)
    energy,h=invariants(run.states)
    crossing=brentq(lambda t:run.dense_solution(t)[1],.9*period,1.1*period,xtol=1e-9)
    closure=run.dense_solution(period)-initial
    angle=2*np.pi*times/period
    analytic=np.column_stack([radius*np.cos(angle),radius*np.sin(angle),np.zeros(len(times))])
    result={'theoretical_period_s':period,'computed_period_s':crossing,'period_error_s':crossing-period,
        'one_period_position_closure_m':float(np.linalg.norm(closure[:3])),
        'one_period_velocity_closure_m_s':float(np.linalg.norm(closure[3:])),
        'max_analytic_position_error_10_orbits_m':float(np.linalg.norm(run.states[:,:3]-analytic,axis=1).max()),
        'max_relative_energy_drift':float(np.max(abs((energy-energy[0])/energy[0]))),
        'max_relative_h_vector_drift':float(np.max(np.linalg.norm(h-h[0],axis=1)/np.linalg.norm(h[0]))),
        'integration':run.statistics}
    return run,result,(energy-energy[0])/abs(energy[0]),np.linalg.norm(h-h[0],axis=1)/np.linalg.norm(h[0])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-tag',default='rk45_two_body_v1')
    tag=parser.parse_args().run_tag
    if not tag or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in tag):raise ValueError('Invalid tag')
    for path in [ROOT/'src',ROOT/'experiments',ROOT/'results/figures',ROOT/'results/metrics',ROOT/'logs']:
        if not path.resolve().is_relative_to(ROOT):raise ValueError('Workspace escape')
    out=ROOT/'experiments'/tag;out.mkdir(exist_ok=False)
    protected=list((ROOT/'data/raw/orbits').rglob('*'))+list((ROOT/'experiments/20261020_sgp4_60s').glob('*'))+list((ROOT/'results').rglob('20261020_sgp4*'))+[ROOT/'reports/SGP4_SP3_BASELINE_2026-10-20.md']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()}
    (out/'preserved_inputs.json').write_text(json.dumps(hashes,indent=2))
    cases={}; runs={}
    settings={'loose':(1e-7,.1,120.),'baseline':(1e-10,1e-3,30.),'tight':(1e-12,1e-5,30.),'step15':(1e-10,1e-3,15.),'step120':(1e-10,1e-3,120.)}
    for name,setting in settings.items():
        runs[name],cases[name],de,dh=circle_case(*setting)
        if name=='baseline':energy_drift=de;h_drift=dh
    baseline=cases['baseline']
    if not (abs(baseline['period_error_s'])<1e-4 and baseline['one_period_position_closure_m']<.1 and baseline['max_relative_energy_drift']<1e-8 and baseline['max_relative_h_vector_drift']<1e-8 and cases['tight']['max_analytic_position_error_10_orbits_m']<baseline['max_analytic_position_error_10_orbits_m']):
        raise RuntimeError('Independent circle verification failed; real propagation blocked')
    print('Circle validation passed',json.dumps(cases,indent=2),flush=True)
    table,time_meta=configure_time_data()
    reference=load_sp3_reference((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))
    if reference.frame!='IGS20':raise ValueError('Unexpected SP3 frame')
    t0=Time('2023-03-21T00:00:02',scale='utc');elapsed=np.arange(0,172801,60,dtype=float)
    times=t0+TimeDelta(elapsed,format='sec');ref=reference.take_exact(times)
    # Only this one native P/V record initializes propagation; no future fitting.
    initial=reference.take_exact(times[:1])
    r0,v0=transform_state(initial.positions_m,initial.velocities_m_s,times[:1],'ITRS','GCRS')
    run=propagate(two_body_rhs,r0[0],v0[0],(0,172800),elapsed)
    tight=propagate(two_body_rhs,r0[0],v0[0],(0,172800),elapsed,rtol=1e-12,atol=[1e-5]*3+[1e-8]*3,max_step=15.)
    p,v=transform_state(run.states[:,:3],run.states[:,3:],times,'GCRS','ITRS')
    rg,vg=transform_state(ref.positions_m,ref.velocities_m_s,times,'ITRS','GCRS')
    backr,backv=transform_state(r0,v0,times[:1],'GCRS','ITRS')
    delta=p-ref.positions_m;rac=rac_errors(run.states[:,:3]-rg,rg,vg);error=np.linalg.norm(delta,axis=1)
    np.testing.assert_allclose(np.linalg.norm(rac,axis=1),error,atol=1e-5,rtol=1e-10)
    old=np.load(ROOT/'experiments/20261020_sgp4_60s/states.npz')
    np.testing.assert_array_equal(old['elapsed_s'],elapsed)
    if np.max(abs((Time(old['utc_jd1'],old['utc_jd2'],format='jd',scale='utc')-times).sec))>1e-6:raise ValueError('SGP4 epochs differ')
    olderror=np.linalg.norm(old['delta_itrs_m'],axis=1)
    energy,h=invariants(run.states)
    summary={'status':'passed','mu_m3_s2':EARTH_MU,'circle_reference_radius_m':EARTH_EQUATORIAL_RADIUS+400000,
        'constant_source':'https://earth-info.nga.mil/index.php?action=wgs84&dir=wgs84',
        'solver_source':'https://docs.scipy.org/doc/scipy-1.15.3/reference/generated/scipy.integrate.solve_ivp.html',
        'circle_cases':cases,'start_utc':times[0].utc.isot,'end_utc':times[-1].utc.isot,
        'initialization':'Single SP3 native P/V epoch, retrospective reduced-dynamic product, full ITRS -> GCRS state; no subsequent updates',
        'initial_itrs_m':initial.positions_m[0].tolist(),'initial_itrs_m_s':initial.velocities_m_s[0].tolist(),
        'initial_gcrs_m':r0[0].tolist(),'initial_gcrs_m_s':v0[0].tolist(),
        'initial_state_roundtrip_position_m':float(np.linalg.norm(backr-initial.positions_m)),
        'initial_state_roundtrip_velocity_m_s':float(np.linalg.norm(backv-initial.velocities_m_s)),
        'initial_radius_m':float(np.linalg.norm(r0)),'initial_speed_m_s':float(np.linalg.norm(v0)),
        'sp3_metadata':ref.metadata,'time_data':time_meta,'eop':check_eop(times,table),
        'integration':run.statistics,'tight_integration':tight.statistics,
        'max_tight_baseline_position_difference_m':float(np.linalg.norm(run.states[:,:3]-tight.states[:,:3],axis=1).max()),
        'real_max_relative_energy_drift':float(np.max(abs((energy-energy[0])/energy[0]))),
        'real_max_relative_h_vector_drift':float(np.max(np.linalg.norm(h-h[0],axis=1)/np.linalg.norm(h[0]))),
        'metrics':summarize_errors(delta,rac),'hourly_error_m':{str(hour):float(error[hour*60]) for hour in [1,3,6,12,24,48]},
        'versions':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__},
        'comparison_warning':'SGP4: fixed historical TLE; RK45: SP3 single-epoch P/V. Different initializations and physics; not an integrator accuracy ranking.'}
    np.savez_compressed(out/'states.npz',elapsed_s=elapsed,utc_jd1=times.utc.jd1,utc_jd2=times.utc.jd2,gcrs_states=run.states,itrs_position_m=p,itrs_velocity_m_s=v,sp3_gcrs_position_m=rg,sp3_gcrs_velocity_m_s=vg,rac_m=rac,delta_itrs_m=delta,internal_times_s=run.internal_times_s)
    np.savez_compressed(out/'circle.npz',times_s=runs['baseline'].times_s,states=runs['baseline'].states,relative_energy_drift=energy_drift,relative_h_vector_drift=h_drift)
    with (ROOT/f'results/metrics/{tag}_circle.csv').open('x',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['elapsed_s','relative_energy_drift','relative_h_vector_drift'])
        writer.writerows(zip(runs['baseline'].times_s,energy_drift,h_drift))
    csvpath=ROOT/f'results/metrics/{tag}_errors.csv'
    with csvpath.open('x',newline='') as f:
        writer=csv.writer(f);writer.writerow(['utc','elapsed_s','error_3d_m','radial_m','along_track_m','normal_m','dx_itrs_m','dy_itrs_m','dz_itrs_m'])
        writer.writerows([times[i].utc.isot,elapsed[i],error[i],*rac[i],*delta[i]] for i in range(len(times)))
    def save(name):
        path=ROOT/f'results/figures/{tag}_{name}.png'
        if path.exists():raise FileExistsError(path)
        plt.tight_layout();plt.savefig(path,dpi=160);plt.close()
    fig=plt.figure();ax=fig.add_subplot(projection='3d')
    ax.plot(*(run.states[:,:3]/1000).T,label='RK45 central gravity')
    ax.plot(*(rg/1000).T,label='SP3 reference',alpha=.6)
    ax.set(xlabel='GCRS X (km)',ylabel='GCRS Y (km)',zlabel='GCRS Z (km)',title='Swarm-A: 48 h, single SP3 P/V initialization');ax.legend();save('orbit_3d')
    for values,label,name in [(energy_drift,'(E - E0) / |E0|','circle_energy'),(h_drift,'|h - h0| / |h0|','circle_angular_momentum')]:
        plt.figure();plt.plot(runs['baseline'].times_s/3600,values,label='RK45 400 km circular test');plt.xlabel('Elapsed time (h)');plt.ylabel(label);plt.title('Central gravity: 10 circular orbits');plt.legend();plt.grid();save(name)
    plt.figure();plt.plot(elapsed/3600,error/1000,label='RK45 two-body vs SP3');plt.xlabel('Prediction time (h)');plt.ylabel('3D position difference (km)');plt.title('Swarm-A: single SP3 P/V initialization');plt.legend();plt.grid();save('position_error')
    plt.figure();plt.semilogy(elapsed/3600,olderror,label='SGP4: historical TLE initialization');plt.semilogy(elapsed[1:]/3600,error[1:],label='RK45 central only: SP3 P/V initialization');plt.xlabel('Prediction time (h)');plt.ylabel('3D position difference (m, log scale)');plt.title('Different initial states and force models; not an integrator ranking');plt.legend(fontsize=8);plt.grid();save('comparison')
    plt.figure()
    for i,label in enumerate(['R outward','A along-track','C orbit normal']):plt.plot(elapsed/3600,rac[:,i]/1000,label=label)
    plt.xlabel('Prediction time (h)');plt.ylabel('Signed reference RAC difference (km)');plt.title('Swarm-A: predicted minus reference, GCRS RAC');plt.legend();plt.grid();save('rac_errors')
    summary['preserved_input_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==sha for p,sha in hashes.items())
    if not summary['preserved_input_hashes_unchanged']:raise RuntimeError('Existing input changed')
    (out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
    print(json.dumps({k:summary[k] for k in ['metrics','hourly_error_m','integration','max_tight_baseline_position_difference_m']},indent=2),flush=True)

if __name__=='__main__':main()
