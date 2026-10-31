"""SP3/DNS alignment and cached density residual budgets, CPU only."""
from pathlib import Path
import csv,json,sys,time,resource,collections
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import cdflib
import astropy.units as u
from astropy.time import Time,TimeDelta
from astropy.coordinates import EarthLocation
from evaluation.orbit_data import load_sp3_reference,save_standardized,OrbitSeries
from evaluation.sp3_reader import read_sp3
from evaluation.orbit_interpolation import HermiteOrbit,signed_density_budget,contiguous_lag_correlation
from orbit.frames import configure_time_data,transform_state,check_eop
import prepare_swarm_coordinate_orbit_v1 as task
from prepare_fourcastden_swarm_observation_v1 import sha,dump,inside
from analyze_fourcastden_swarm_observation_v1 import table,FIELDS,MODELS
F,O,D=task.F,task.O,task.D
PRIOR=ROOT/'results/fourcastden_swarm_observation_v1'


def statistics(x):
    x=np.asarray(x,float)
    return dict(n=len(x),mean=float(x.mean()),RMS=float(np.sqrt(np.mean(x*x))),abs_P95=float(np.quantile(abs(x),.95)),max_abs=float(abs(x).max()),minimum=float(x.min()),maximum=float(x.max()))


def main():
    begin=time.perf_counter();dump(F/'analysis_started.json',dict(new_density_queries=0,new_orbit=0,new_forward=0))
    processed=inside(ROOT/'data/processed'/task.TAG);processed.mkdir(exist_ok=False)
    protected={}
    for folder in [ROOT/'experiments/fourcastden_swarm_observation_v1']:
        prior=json.loads((folder/'protected.json').read_text());assert all(sha(ROOT/p)==h for p,h in prior.items());protected.update(prior)
    for day in ('2023-01-04','2023-03-24'):
        for p in [PRIOR/(day+'_aligned_local.npz'),PRIOR/(day+'_observations_local.csv')]:protected[str(p.relative_to(ROOT))]=sha(p)
    for p in [ROOT/'src/orbit/frames.py',ROOT/'src/evaluation/orbit_data.py',ROOT/'src/evaluation/sp3_reader.py',ROOT/'third_party/TIEGCM2.0/src/addiag.F',ROOT/'third_party/TIEGCM2.0/src/lbc.F',ROOT/'third_party/TIEGCM2.0/src/cons.F']:
        protected[str(p.relative_to(ROOT))]=sha(p)
    for rec in json.loads((F/'download_manifest.json').read_text()):
        assert sha(ROOT/rec['path'])==rec['SHA256'];protected[rec['path']]=rec['SHA256']
        for r in rec['members']:assert sha(ROOT/r['path'])==r['SHA256'];protected[r['path']]=r['SHA256']
    dump(F/'protected.json',protected)
    configure_time_data();summ=[];interps=[];inventory=[];initial=[];all_budgets=[];blocks=[];acfs=[];failures=[];densitybins=[]
    for day in ('2023-01-04','2023-03-24'):
        sp3=next((D/'extracted').glob('*'+day.replace('-','')+'T235942_0203.sp3'))
        s=load_sp3_reference([sp3]);raw=read_sp3(sp3);assert s.frame=='IGS20' and raw.interval_s==10 and len(raw.epochs)==8640
        assert np.all((np.linalg.norm(s.velocities_m_s,axis=1)>6000)&(np.linalg.norm(s.velocities_m_s,axis=1)<9000))
        save_standardized(s,processed/(day+'_native_ITRS_local.npz'))
        flags=collections.Counter((r['raw_tail'] or 'ABSENT') for r in raw.orbit_flags)
        inventory.append(dict(date=day,source=s.metadata,raw_first_epoch_GPS=raw.epochs[0].isoformat(),raw_last_epoch_GPS=raw.epochs[-1].isoformat(),
            data_type_header=sp3.read_text().splitlines()[0],native_interval_s=10,PV_records=len(raw.epochs),raw_orbit_tail_counts=dict(flags),
            time_EOP=check_eop(s.times),GPS_UTC_offset_s=float((Time(raw.epochs[0].isoformat(),scale='utc')-s.times[0]).sec),
            formal_accuracy='SP3 exponents/quality preserved; not converted to verified covariance',
            DNS_frame_realization='GRS80 geodetic known; precise ITRF realization not independently stated in CDF'))
        dns=next((ROOT/'data/raw/fourcastden_swarm_observation_v1/extracted').glob('*'+day.replace('-','')+'*.cdf'))
        with cdflib.CDF(dns) as c:
            t=cdflib.cdfepoch.to_datetime(c.varget('time'));mask=(t>=np.datetime64(day+'T01'))&(t<=np.datetime64(day+'T13'));t=t[mask]
            la,lo,alt=[c.varget(k)[mask] for k in ('latitude','longitude','altitude')]
        epoch=Time(t,scale='utc');query=HermiteOrbit(s).evaluate(epoch);assert len(t)==1441
        ds=EarthLocation.from_geodetic(lo*u.deg,la*u.deg,alt*u.m,ellipsoid='GRS80');dp=np.column_stack([v.to_value(u.m) for v in ds.geocentric])
        sl=EarthLocation.from_geocentric(*query.positions_m.T,unit=u.m);g=sl.to_geodetic('GRS80');w=sl.to_geodetic('WGS84');dw=ds.to_geodetic('WGS84')
        diff=query.positions_m-dp;norm=np.linalg.norm(diff,axis=1);dh=g.height.to_value(u.m)-alt
        dlat=g.lat.to_value(u.deg)-la;dlon=(g.lon.to_value(u.deg)-lo+180)%360-180
        seconds=(s.times.tai-s.times[0].tai).sec;x=(epoch.tai-s.times[0].tai).sec;nearest=np.min(abs(seconds[None,:]-x[:,None]),axis=1)
        polynomial=np.empty_like(query.positions_m);polyv=np.empty_like(query.velocities_m_s)
        for i,xx in enumerate(x):
            a=int(np.clip(np.searchsorted(seconds,xx)-3,0,len(seconds)-7));idx=np.arange(a,a+7);z=(seconds[idx]-xx)/10
            coef=np.linalg.solve(np.vander(z,7,increasing=True),s.positions_m[idx]);polynomial[i]=coef[0];polyv[i]=coef[1]/10
        polyerr=np.linalg.norm(query.positions_m-polynomial,axis=1)
        coarse=OrbitSeries(s.times[::2],s.positions_m[::2],s.velocities_m_s[::2],s.frame,s.metadata)
        held=np.arange(1,len(s.times)-2,2);test=HermiteOrbit(coarse,expected_step_s=20).evaluate(s.times[held])
        interps.append(dict(date=day,method='cubic P/V Hermite 10s; degree6 position polynomial independent',
            DNS_nearest_native_time_difference_s=statistics(nearest),Hermite_vs_degree6_position_m=statistics(polyerr),
            Hermite_vs_degree6_velocity_m_s=statistics(np.linalg.norm(query.velocities_m_s-polyv,axis=1)),
            native20s_holdout_position_m=statistics(np.linalg.norm(test.positions_m-s.positions_m[held],axis=1)),
            native20s_holdout_velocity_m_s=statistics(np.linalg.norm(test.velocities_m_s-s.velocities_m_s[held],axis=1)),
            holdout_is_not_independent_true_orbit_error_bound=True))
        gp,gv=transform_state(query.positions_m,query.velocities_m_s,epoch,'ITRS','GCRS');rp,rv=transform_state(gp,gv,epoch,'GCRS','ITRS')
        # IGS20 is used as aligned ITRS; no fitted Helmert/empirical correction.
        np.savez_compressed(inside(processed/(day+'_DNS_epochs_PV_local.npz')),UTC=epoch.isot,UTC_jd1=epoch.utc.jd1,UTC_jd2=epoch.utc.jd2,
            position_ITRS_m=query.positions_m,velocity_ITRS_m_s=query.velocities_m_s,position_GCRS_m=gp,velocity_GCRS_m_s=gv,
            frame_assumption='IGS20 aligned with ITRF2020/ITRS; no estimated transform')
        rows=[]
        for i in range(len(t)):
            rows.append(dict(date=day,sample=i,UTC=epoch[i].isot,nearest_SP3_epoch_distance_s=nearest[i],
                difference_x_m=diff[i,0],difference_y_m=diff[i,1],difference_z_m=diff[i,2],position_difference_m=norm[i],
                height_difference_GRS80_m=dh[i],latitude_difference_deg=dlat[i],longitude_difference_deg=dlon[i],
                height_difference_WGS84_m=w.height.to_value(u.m)[i]-dw.height.to_value(u.m)[i],
                SP3_vs_poly_position_m=polyerr[i]))
        table(O/(day+'_geometry_local.csv'),rows)
        for name,a in [('position_norm_m',norm),('height_GRS80_m',dh),('latitude_deg',dlat),('longitude_deg',dlon),
                       ('ITRS_GCRS_roundtrip_position_m',np.linalg.norm(rp-query.positions_m,axis=1)),('ITRS_GCRS_roundtrip_velocity_m_s',np.linalg.norm(rv-query.velocities_m_s,axis=1))]:
            summ.append(dict(date=day,metric=name,**statistics(a)))
        i0=np.searchsorted((s.times-Time(day+'T01:00:00',scale='utc')).sec,0)
        for label,tt,pp,vv,look in [('01UTC_interpolated',epoch[0],query.positions_m[0],query.velocities_m_s[0],float((s.times[i0]-epoch[0]).sec)),
            ('first_native_after_01UTC',s.times[i0],s.positions_m[i0],s.velocities_m_s[i0],0.)]:
            initial.append(dict(date=day,option=label,UTC=tt.isot,ITRS_position_m=pp.tolist(),ITRS_velocity_m_s=vv.tolist(),
                later_native_record_used_seconds=look,source='postprocessed0203, not available-in-real-time proof',
                interpolation_causality='retrospective; later bracket' if look else 'native PV at this epoch; product itself retrospective'))
        cached_residual_analysis(day,all_budgets,blocks,acfs,failures,densitybins)
        if time.perf_counter()-begin>1800 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>4*1024**2:raise RuntimeError('CPU resource gate')
    table(O/'geometry_summary.csv',summ);dump(F/'SP3_product_contract.json',inventory);dump(F/'interpolation_validation.json',interps);dump(F/'initialization_options_local.json',initial)
    table(O/'residual_budget.csv',all_budgets);table(O/'fixed_hour_blocks.csv',blocks);table(O/'descriptive_ACF.csv',acfs)
    table(O/'Flow_failed_samples.csv',failures);table(O/'density_level_description.csv',densitybins)
    assert all(sha(ROOT/p)==h for p,h in protected.items())
    dump(F/'analysis_complete.json',dict(wall_s=time.perf_counter()-begin,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        protected_SHA_unchanged=len(protected),new_density_queries=0,new_forward=0,new_TIE=0,new_orbit=0,
        formal_datum='EXTERNAL_DATUM_UNVERIFIED',REAL_ORBIT_VALIDATION_READY='BLOCKED',SCIENTIFIC_TRAINING_READY=False))
    print((F/'analysis_complete.json').read_text());print(json.dumps(summ,indent=2))


def cached_residual_analysis(day,budgets,blocks,acfs,failures,bins):
    with np.load(PRIOR/(day+'_aligned_local.npz'),allow_pickle=False) as n:
        v=n['predictions'];valid=n['valid'];obs=n['observed'];h=n['hours'];good=n['quality'];co=n['coordinates']
    common=good&valid[:2].all(axis=(0,1));la=co[:,0,0]
    for mp,mapping in enumerate(('A','B')):
        for mi,model in enumerate(MODELS):
            for scheme,idx in [('Open',1+mi*2),('Updated',2+mi*2)]:
                for region,rm in [('global',np.ones(len(h),bool)),('south',la<=-60),('north',la>=60),('midlow',abs(la)<60)]:
                    for period,pm in [('pre',(h>=1)&(h<7)),('post',(h>=8)&(h<=13))]:
                        mask=common&rm&pm
                        if not mask.any():continue
                        b=signed_density_budget(v[mp,idx,mask],v[mp,0,mask],obs[mask]);budgets.append(dict(date=day,mapping=mapping,model=model,scheme=scheme,region=region,period=period,**b))
                # Consecutive fixed UTC blocks, not an inferential bootstrap.
                for hour in range(1,13):
                    mask=common&(h>=hour)&(h<hour+1)&(h!=7)
                    if mask.any():blocks.append(dict(date=day,mapping=mapping,model=model,scheme=scheme,hour_UTC=hour,
                        **signed_density_budget(v[mp,idx,mask],v[mp,0,mask],obs[mask])))
                mask=common&(h>=8)&(h<=13);ids=np.flatnonzero(mask);err=(v[mp,idx,mask]-obs[mask])/obs[mask]
                for a in contiguous_lag_correlation(err,ids,120):acfs.append(dict(date=day,mapping=mapping,model=model,scheme=scheme,
                    lag_seconds=30*a['lag_samples'],n_window=len(err),**a))
                # Fixed physical bins, declared diagnostic only; no fitting.
                for lower,upper in [(0,1e-12),(1e-12,2e-12),(2e-12,np.inf)]:
                    ms=mask&(obs>=lower)&(obs<upper)
                    if ms.any():bins.append(dict(date=day,mapping=mapping,model=model,scheme=scheme,observed_bin_low=lower,
                        observed_bin_high=upper if np.isfinite(upper) else 'infinity',**signed_density_budget(v[mp,idx,ms],v[mp,0,ms],obs[ms])))
        failed=np.flatnonzero(good&(h>=8)&(h<=13)&~valid[mp,FIELDS.index('Flow_Updated')])
        for i in failed:failures.append(dict(date=day,mapping=mapping,sample=int(i),UTC_hour=float(h[i]),latitude_WGS84_deg=co[i,0,0],
            reason='INVALID_HEIGHT_RECONSTRUCTION_COLUMN',retained=True))


if __name__=='__main__':main()
