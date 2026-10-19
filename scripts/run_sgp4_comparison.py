"""Reproducible fixed-TLE historical comparison, offline after setup.

Run the 300 s pilot first. The 60 s run requires its passed pilot manifest.
Outputs are exclusive-create; choose another run directory for intentional reruns.
"""
from pathlib import Path
import sys,json,argparse,hashlib,time,csv,importlib.metadata,warnings,re
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import astropy.units as u
from astropy.time import Time,TimeDelta
from astropy.utils import iers
import erfa
from orbit.frames import configure_time_data,check_eop,transform_state
from orbit.sgp4_baseline import read_archive,select_before,propagate
from evaluation.orbit_data import load_sp3_reference,save_standardized
from evaluation.orbit_metrics import rac_errors,summarize_errors


def write_json(path,data):
    with Path(path).open('x') as f:json.dump(data,f,indent=2,ensure_ascii=False)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cadence',type=int,choices=[300,60],default=300)
    parser.add_argument('--run-tag',default='20261020_sgp4',help='New output prefix for safe reruns; alphanumeric/underscore/hyphen only')
    args=parser.parse_args();step=args.cadence;tag=args.run_tag
    if re.fullmatch(r'[A-Za-z0-9_-]+',tag) is None:raise ValueError('Invalid run tag')
    output=ROOT/f'experiments/{tag}_{step}s'
    output.mkdir(exist_ok=False)
    if step==60:
        pilot=json.loads((ROOT/f'experiments/{tag}_300s/summary.json').read_text())
        if pilot['validation_status']!='passed':raise RuntimeError('Pilot must pass first')
    table,time_meta=configure_time_data()
    ref=load_sp3_reference((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))
    if ref.frame!='IGS20':raise ValueError('Unexpected terrestrial realization')
    standardized=ROOT/'data/processed/swarm_a_sp3_standard_20261020.npz'
    if step==300:
        if standardized.exists():
            with np.load(standardized,allow_pickle=False) as cached:
                np.testing.assert_array_equal(cached['position_m'],ref.positions_m)
                np.testing.assert_array_equal(cached['velocity_m_s'],ref.velocities_m_s)
                np.testing.assert_array_equal(cached['utc_jd1'],ref.times.utc.jd1)
                np.testing.assert_array_equal(cached['utc_jd2'],ref.times.utc.jd2)
        else:
            save_standardized(ref,standardized)
            write_json(standardized.with_suffix('.json'),ref.metadata)
    t0=Time('2023-03-21T00:00:02',scale='utc')
    elapsed=np.arange(0,48*3600+1,step,dtype=float)
    times=t0+TimeDelta(elapsed,format='sec');times.precision=9
    reference=ref.take_exact(times)
    if np.max(abs((reference.times-times).to_value(u.s)))>1e-6:raise ValueError('Reference/prediction time mismatch')
    eop=check_eop(times,table)
    records=read_archive(ROOT/'data/raw/orbits/tle/swarm_a_20230320_23_eth_archive.json')
    selected=select_before(records,t0,allow_unverified_availability=True)
    frozen=(ROOT/'data/raw/orbits/tle/swarm_a_selected_before_t0.tle').read_text().splitlines()[-2:]
    if [selected.line1,selected.line2]!=frozen:raise ValueError('Selected TLE differs from frozen prior-day choice')
    tle_meta={'source':'ETH Satellite Database / CelesTrak archive','archive_id':selected.archive_id,'epoch_utc':selected.epoch.utc.to_value('isot',subfmt='date_hms'),'age_at_start_hours':float((t0-selected.epoch).to_value(u.hour)),'line1':selected.line1,'line2':selected.line2,'gravity_constants':'WGS72','sgp4_operation_mode':'improved (i)','publication_time':None,'availability_before_start_verified':False,'selection_rule':'latest epoch <= t0, frozen before comparing SP3 errors','all_eight_epochs_utc':[x.epoch.utc.isot for x in records]}
    write_json(output/'tle_metadata.json',tle_meta)
    started=time.perf_counter()
    p_teme,v_teme,codes=propagate(selected,times)
    if not np.all((6e6<np.linalg.norm(p_teme,axis=1))&(np.linalg.norm(p_teme,axis=1)<8e6)):raise ValueError('SGP4 radius out of range')
    if not np.all((6000<np.linalg.norm(v_teme,axis=1))&(np.linalg.norm(v_teme,axis=1)<9000)):raise ValueError('SGP4 speed out of range')
    p_itrs,v_itrs=transform_state(p_teme,v_teme,times,'TEME','ITRS')
    pr,vr=transform_state(p_itrs,v_itrs,times,'ITRS','TEME')
    p_ref_g,v_ref_g=transform_state(reference.positions_m,reference.velocities_m_s,times,'ITRS','GCRS')
    p_g,v_g=transform_state(p_itrs,v_itrs,times,'ITRS','GCRS')
    p_ref_back,v_ref_back=transform_state(p_ref_g,v_ref_g,times,'GCRS','ITRS')
    delta=p_itrs-reference.positions_m;delta_g=p_g-p_ref_g
    rac=rac_errors(delta_g,p_ref_g,v_ref_g);error=np.linalg.norm(delta,axis=1)
    closure=np.max(abs(np.linalg.norm(rac,axis=1)-error))
    roundtrip_position=float(np.max(np.linalg.norm(pr-p_teme,axis=1)))
    roundtrip_velocity=float(np.max(np.linalg.norm(vr-v_teme,axis=1)))
    ref_roundtrip_position=float(np.max(np.linalg.norm(p_ref_back-reference.positions_m,axis=1)))
    ref_roundtrip_velocity=float(np.max(np.linalg.norm(v_ref_back-reference.velocities_m_s,axis=1)))
    # Independent GMST82 polynomial plus polar-motion matrix, not calling Astropy TEME transform.
    ut1=times.ut1;T=((ut1.jd1-2451545.)+ut1.jd2)/36525.
    theta=np.remainder(67310.54841+(876600*3600+8640184.812866)*T+.093104*T*T-6.2e-6*T**3,86400)*(2*np.pi/86400)
    co=np.cos(theta);si=np.sin(theta)
    pef=np.column_stack([co*p_teme[:,0]+si*p_teme[:,1],-si*p_teme[:,0]+co*p_teme[:,1],p_teme[:,2]])
    xp,yp=table.pm_xy(times);pm=erfa.pom00(xp.to_value(u.rad),yp.to_value(u.rad),np.zeros(len(times)))
    independent=np.einsum('nij,nj->ni',pm,pef)
    independent_frame_diff=float(np.max(np.linalg.norm(independent-p_itrs,axis=1)))
    if max(roundtrip_position,ref_roundtrip_position)>1e-3 or max(roundtrip_velocity,ref_roundtrip_velocity)>1e-4:raise ValueError('State roundtrip tolerance exceeded')
    if closure>1e-5 or independent_frame_diff>1e-2:raise ValueError('RAC/independent coordinate validation failure')
    if np.any(codes) or not np.isfinite(error).all():raise ValueError('Invalid propagation/error')
    summary=summarize_errors(delta,rac)
    summary.update({'validation_status':'passed','experiment_kind':'historical single-TLE propagation comparison; publication-time causality unverified','cadence_s':step,'start_utc':times[0].utc.isot,'stop_utc':times[-1].utc.isot,'duration_s':float((times[-1]-times[0]).to_value(u.s)),'tle':tle_meta,'comparison_frame':'ITRS, reference interpreted from IGS20/ITRF2020 aligned realization; no Helmert fit','rac_frame':'reference GCRS; R outward, A=C cross R, C=r cross v; error=SGP4-SP3','max_error_utc':times[summary['max_index']].utc.isot,'eop':eop,'roundtrip_position_m':roundtrip_position,'roundtrip_velocity_m_s':roundtrip_velocity,'reference_roundtrip_position_m':ref_roundtrip_position,'reference_roundtrip_velocity_m_s':ref_roundtrip_velocity,'rac_norm_closure_m':float(closure),'independent_gmst82_position_diff_m':independent_frame_diff,'reference_time_mismatch_s':reference.metadata['time_match_max_s'],'sgp4_nonzero_errors':int(np.count_nonzero(codes)),'compute_seconds':time.perf_counter()-started,'time_data':time_meta,'versions':{n:importlib.metadata.version(n) for n in ['numpy','scipy','sgp4','astropy','astropy-iers-data','pyerfa','matplotlib']},'reference_metadata':ref.metadata})
    mjd=table['MJD'].value;mask=(mjd>=np.floor(times[0].utc.mjd))&(mjd<=np.ceil(times[-1].utc.mjd))
    rows=table[mask]
    rows.write(output/'eop_rows.ecsv',format='ascii.ecsv',overwrite=False)
    summary['eop_formal_uncertainty_max']={name:{'value':float(np.max(abs(rows[name].value))),'unit':str(rows[name].unit)} for name in ['e_PM_x','e_PM_y','e_UT1_UTC','e_dX_2000A','e_dY_2000A']}
    summary['erfa_dat_2023_s']=float(erfa.dat(2023,3,21,0.))
    summary['effective_erfa_leaps_sha256']=hashlib.sha256(erfa.leap_seconds.get().tobytes()).hexdigest()
    csv_path=ROOT/f'results/metrics/{tag}_{step}s_errors.csv'
    with csv_path.open('x',newline='') as f:
        writer=csv.writer(f);writer.writerow(['utc','elapsed_s','error_3d_m','radial_m','along_track_m','normal_m','dx_itrs_m','dy_itrs_m','dz_itrs_m','sgp4_x_itrs_m','sgp4_y_itrs_m','sgp4_z_itrs_m','sp3_x_itrs_m','sp3_y_itrs_m','sp3_z_itrs_m'])
        for i in range(len(times)):writer.writerow([times[i].utc.isot,elapsed[i],error[i],*rac[i],*delta[i],*p_itrs[i],*reference.positions_m[i]])
    np.savez_compressed(output/'states.npz',utc_jd1=times.utc.jd1,utc_jd2=times.utc.jd2,elapsed_s=elapsed,sgp4_teme_m=p_teme,sgp4_teme_m_s=v_teme,sgp4_itrs_m=p_itrs,sgp4_itrs_m_s=v_itrs,sp3_itrs_m=reference.positions_m,sp3_itrs_m_s=reference.velocities_m_s,delta_itrs_m=delta,rac_m=rac,sgp4_codes=codes)
    if step==60:
        # All coarse epochs coincide with fine epochs. Agreement is checked before plotting.
        with np.load(ROOT/f'experiments/{tag}_300s/states.npz') as coarse:
            np.testing.assert_allclose(coarse['delta_itrs_m'],delta[::5],atol=1e-7,rtol=0)
            summary['pilot_common_epoch_error_agreement_m']=float(np.max(abs(coarse['delta_itrs_m']-delta[::5])))
        import matplotlib.pyplot as plt
        hours=elapsed/3600
        def save(fig,name):
            path=ROOT/f'results/figures/{tag}_{name}.png'
            if path.exists():raise FileExistsError(path)
            fig.savefig(path,dpi=170,bbox_inches='tight');plt.close(fig)
        fig=plt.figure(figsize=(9,8));ax=fig.add_subplot(111,projection='3d')
        ax.plot(*(reference.positions_m/1000).T,label='ESA SP3 (IGS20 as ITRS)',lw=.7,alpha=.8)
        ax.plot(*(p_itrs/1000).T,label='Fixed historical TLE / SGP4',lw=.7,alpha=.8)
        ax.set(xlabel='ITRS X (km)',ylabel='ITRS Y (km)',zlabel='ITRS Z (km)',title='Swarm-A: 48-hour orbit comparison, 60 s samples\n2023-03-21 00:00:02 to 03-23 00:00:02 UTC')
        ax.set_box_aspect(np.ptp(reference.positions_m,axis=0));ax.legend(loc='upper left');save(fig,'orbit_3d')
        fig,ax=plt.subplots(figsize=(10,4.8));ax.plot(hours,error/1000,label='3D norm |SGP4 - SP3|',lw=.9)
        ax.scatter([0,48],[error[0]/1000,error[-1]/1000],label='Initial and terminal',color='black',s=22)
        ax.set(xlabel='Elapsed time from experiment start (h)',ylabel='Position error (km)',title='Swarm-A fixed-TLE position difference relative to SP3 (60 s)');ax.grid(alpha=.3);ax.legend();save(fig,'position_error')
        fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True,constrained_layout=True)
        for j,(label,color) in enumerate(zip(['Radial R (outward)','Along-track A (forward)','Normal C (r x v)'],['C0','C1','C2'])):
            axes[j].plot(hours,rac[:,j]/1000,label=label,color=color,lw=.8);axes[j].set_ylabel('Error (km)');axes[j].grid(alpha=.3);axes[j].legend(loc='upper left')
        axes[-1].set_xlabel('Elapsed time from experiment start (h)');fig.suptitle('Swarm-A signed RAC position errors: SGP4 - SP3\nBasis from the simultaneous reference GCRS position and velocity');save(fig,'rac_errors')
    write_json(output/'summary.json',summary)
    print(json.dumps({k:summary[k] for k in ['validation_status','samples','start_utc','stop_utc','initial_m','mean_norm_m','rmse_3d_m','max_norm_m','terminal_m','roundtrip_position_m','roundtrip_velocity_m_s','independent_gmst82_position_diff_m']},indent=2))

if __name__=='__main__':
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        try:main()
        finally:
            path=ROOT/'logs'/f'20261020_runtime_warnings_{time.time_ns()}.json'
            if not path.exists():path.write_text(json.dumps([{'category':x.category.__name__,'message':str(x.message)} for x in caught],indent=2))
