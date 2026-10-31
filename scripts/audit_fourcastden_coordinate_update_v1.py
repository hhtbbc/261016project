"""CPU-only existing-field/event diagnostics. No network, model or H6 launches."""
from pathlib import Path
import ast,csv,hashlib,json,resource,sys,time,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from astropy.time import Time
from atmosphere.fourcastden_density import FourCastDENDensity,reconstruct_native_zg,HEIGHT_SOURCE
from atmosphere.event_aware_density import EventAwareDensity
from atmosphere.tiegcm_density_provider import DATUM
from atmosphere.density_interface import DensityQuery
from atmosphere.provisional_coordinate_adapter import ProvisionalCoordinateAdapter,A_WGS84,B_SPHERE
from fourcastden.logden import decode_physical
from run_fourcastden_ideal_update_6h import reference,oldpaths
TAG='fourcastden_coordinate_update_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG


def sha(p):
    p=Path(p).resolve();p.relative_to(ROOT);h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
    return h.hexdigest()
def dump(p,obj):
    p.resolve().relative_to(ROOT)
    with p.open('x') as f:json.dump(obj,f,indent=2,allow_nan=False);f.write('\n')
def table(p,rows):
    p.resolve().relative_to(ROOT)
    with p.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def load(path,model):
    with np.load(path,allow_pickle=False) as n:return decode_physical(n['pred'][0],n['means'][:171],n['stds'][:171],model=='LogDEN')
def mass_input(p,tl,iv):
    ti=np.concatenate((tl,.5*(p[:,:27]+p[:,1:28]),p[:,27:28]),axis=1)
    pressure=5e-4*np.exp(-iv);pressure[-1]=pressure[-2]
    factor=8.314e7/pressure[None,:,None,None]
    return factor*p[:,142:]*ti,ti,factor


def main():
    start=time.perf_counter()
    for p in (F,O):p.resolve().relative_to(ROOT);p.mkdir(exist_ok=False)
    dump(F/'protocol.json',dict(offline_CPU_only=True,budget=dict(wall_s=600,RSS_GiB=2,new_MiB=200,free_disk_GiB=20),
        new_forward=0,new_TIE=0,new_full_orbit=0,synthetic_ODE_seconds=120,
        synthetic_ODE_tolerances=[1e-8,1e-10,1e-12],event='07:00 UTC; left and right preserved',
        mass_range=[4,32],coordinate_formal_status='EXTERNAL_DATUM_UNVERIFIED',
        real_query_locations=[(0,0),(-65,90),(65,90)],native_query_height_m=450000,
        algebra='exact symmetric product delta(rho*T)=delta(rho)*mean(T)+mean(rho)*delta(T)',
        perturbation='1e-6 relative interface mass, alternating signs; numerical sensitivity only'))
    protected={}
    old=json.loads((ROOT/'experiments/fourcastden_ideal_update_6h_v1/protected.json').read_text())
    for p,h in old.items():assert sha(ROOT/p)==h;protected[p]=h
    for p in (ROOT/'data/processed/fourcastden_ideal_update_6h_v1').glob('*.npz'):
        expected=json.loads((ROOT/'experiments/fourcastden_ideal_update_6h_v1'/f'{p.stem}_runtime.json').read_text())['result_SHA']
        assert sha(p)==expected;protected[str(p.relative_to(ROOT))]=expected
    for p in [ROOT/'src/atmosphere/fourcastden_density.py',ROOT/'src/atmosphere/provisional_coordinate_adapter.py',
              ROOT/'src/orbit/rk45_propagator.py',ROOT/'src/orbit/common_force_model.py',
              ROOT/'results/metrics/swarm_provisional_v1_mapping_components.csv',ROOT/'results/metrics/swarm_provisional_v1_coarse_S7.csv',
              ROOT/'third_party/TIEGCM2.0/src/addiag.F',ROOT/'third_party/TIEGCM2.0/src/dt.F',
              ROOT/'third_party/TIEGCM2.0/src/lbc.F',ROOT/'third_party/TIEGCM2.0/src/cons.F',
              ROOT/'third_party/TIEGCM2.0/src/getapex.F',ROOT/'third_party/TIEGCM2.0/src/apex.F90']:
        protected[str(p.relative_to(ROOT))]=sha(p)
    dump(F/'protected.json',protected)
    if shutil.disk_usage(ROOT).free<20*2**30:raise RuntimeError('Disk guard')
    lat=np.load(ROOT/'data/processed/static/lat.npy');lon=np.load(ROOT/'data/processed/static/lon.npy');iv=np.load(ROOT/'data/processed/static/ilev.npy')
    queryrows=[];frame_audit=[]
    for day in ('2023-01-04','2023-03-24'):
        tl=np.stack([reference(day,h)[2] for h in range(1,14)])
        for model in ('Direct','Flow','LogDEN','History'):
            p=load(oldpaths(day)[1]/f'{day}_{model}.npz',model)
            q=load(ROOT/'data/processed/fourcastden_ideal_update_6h_v1'/f'{day}_{model}.npz',model)
            providers=[]
            for values,hours,lbc,branch in [(p,range(1,14),tl,'Open'),(q,range(7,14),tl[6:],'Updated')]:
                height,valid,mass=reconstruct_native_zg(values[:,:28],values[:,142:],values[:,113:142],lbc,lat,iv)
                providers.append(FourCastDENDensity([f'{day}T{h:02d}:00:00' for h in hours],lat,lon,values[:,142:],height,
                    source=model+'_'+branch,height_source=HEIGHT_SOURCE,valid_columns=valid))
                frame_audit.append(dict(date=day,model=model,branch=branch,frames=len(values),invalid_column_times=int((~valid).sum())))
            event=EventAwareDensity(*providers,day+'T07:00:00')
            for stamp,side in [('06:00:00','auto'),('06:30:00','auto'),('06:59:59','auto'),('07:00:00','left'),
                               ('07:00:00','right'),('07:00:01','auto'),('07:30:00','auto'),('08:00:00','auto')]:
                for la,lo in [(0,0),(-65,90),(65,90)]:
                    t=day+'T'+stamp;r=event.query_native(t,la,lo,450000,datum=DATUM,event_side=side)
                    chosen=event.before if stamp<'07:00:00' or side=='left' else event.after
                    direct=chosen.query_native(t,la,lo,450000,datum=DATUM)
                    assert r.valid==direct.valid
                    if r.valid:assert r.rho_kg_m3==direct.rho_kg_m3
                    pr=event.query_pressure(t,la,lo,22,event_side=side)
                    queryrows.append(dict(date=day,model=model,UTC=t,event_side=side,branch=r.metadata['event_branch'],lat=la,lon=lo,
                        native_ZG_m=450000,valid=r.valid,reason=r.reason,rho_kg_m3=r.rho_kg_m3,
                        pressure_index22_rho_kg_m3=pr.rho_kg_m3,time_bracket=';'.join(r.metadata.get('time_utc',[])),
                        exact_branch_match=True))
            del p,q,event,providers
    table(O/'real_event_queries.csv',queryrows);table(O/'branch_frame_audit.csv',frame_audit)
    coordinate_review(protected)
    flow_diagnostics(lat,lon,iv)
    synthetic_integration()
    observation_review(protected)
    changed=[p for p,h in protected.items() if sha(ROOT/p)!=h];assert not changed
    total=sum(p.stat().st_size for d in (F,O) for p in d.rglob('*') if p.is_file())
    wall=time.perf_counter()-start;peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
    assert wall<600 and peak<2048 and total<200*2**20
    dump(F/'final_audit.json',dict(input_assets_unchanged=len(protected),changed=changed,wall_s=wall,peak_RSS_MiB=peak,
        output_bytes=total,real_event_queries=len(queryrows),failed_queries=sum(not r['valid'] for r in queryrows),
        numerical_branch_match=True,new_GPU_forward=0,new_TIE=0,new_H6_orbit=0,
        external_registration='BLOCKED',event_interface='PASS',synthetic_segmented_RK45='PASS',
        conditional_12h_orbit='PARTIAL; separate authorization and full path valid coverage required',
        real_satellite_orbit='BLOCKED',SCIENTIFIC_TRAINING_READY=False))
    print((F/'final_audit.json').read_text())


def coordinate_review(protected):
    components=list(csv.DictReader((ROOT/'results/metrics/swarm_provisional_v1_mapping_components.csv').open()))
    coarse=list(csv.DictReader((ROOT/'results/metrics/swarm_provisional_v1_coarse_S7.csv').open()))
    base={(r['sample'],r['scenario']):r for r in coarse}
    comp={(r['sample'],r['assumption']):r for r in components if r['source']=='S7'}
    rows=[]
    for (sample,label),r in comp.items():
        if label!='D_LAT_ONLY':continue
        b=comp[(sample,'E_HEIGHT_ONLY')];a=base[(sample,'A+0km')];s=base[(sample,'B_R6371km')]
        query=DensityQuery.from_itrs(Time(r['utc'],scale='utc'),np.array(ast.literal_eval(r['itrs_m'])))
        ca=ProvisionalCoordinateAdapter(assumption=A_WGS84).adapt(query)
        cb=ProvisionalCoordinateAdapter(assumption=B_SPHERE,sphere_radius_m=6371000.).adapt(query)
        np.testing.assert_allclose([float(r['model_lat_deg']),float(r['model_zg_m']),float(b['model_lat_deg']),float(b['model_zg_m'])],
            [cb.model_latitude_deg,ca.model_zg_m,ca.model_latitude_deg,cb.model_zg_m],rtol=0,atol=1e-7)
        ar=float(a['rho_kg_m3']);dr=float(r['rho_kg_m3']);er=float(b['rho_kg_m3']);br=float(s['rho_kg_m3'])
        rows.append(dict(sample=sample,UTC=r['utc'],A_lat_deg=ca.model_latitude_deg,B_lat_deg=cb.model_latitude_deg,
            delta_lat_deg=cb.model_latitude_deg-ca.model_latitude_deg,A_height_m=ca.model_zg_m,B_height_m=cb.model_zg_m,
            delta_height_m=cb.model_zg_m-ca.model_zg_m,A_rho=ar,B_rho=br,latitude_only_rho=dr,height_only_rho=er,
            latitude_only_relative=dr/ar-1,height_only_relative=er/ar-1,combined_relative=br/ar-1,
            interaction_relative=(br-dr-er+ar)/ar,dlnrho_dh_per_m=float(a['dlnrho_dh_per_m']),
            height_plus_1km_local_sensitivity=np.expm1(float(a['dlnrho_dh_per_m'])*1000),
            A_top_margin_m=float(a['top_margin_m']),B_top_margin_m=float(s['top_margin_m']),
            status='PROVISIONAL_SENSITIVITY_NOT_MAPPING_ERROR'))
    table(O/'coordinate_single_factor_review.csv',rows)
    summaries=[]
    for region in ['global','equatorial','midlatitude','polar']:
        rr=[r for r in rows if region=='global' or (abs(r['A_lat_deg'])<20 if region=='equatorial' else 20<=abs(r['A_lat_deg'])<60 if region=='midlatitude' else abs(r['A_lat_deg'])>=60)]
        for key in ['delta_lat_deg','delta_height_m','latitude_only_relative','height_only_relative','combined_relative','interaction_relative','height_plus_1km_local_sensitivity']:
            x=np.array([r[key] for r in rr]);summaries.append(dict(region=region,metric=key,count=len(x),minimum=float(x.min()),maximum=float(x.max()),abs_P95=float(np.percentile(abs(x),95)),mean=float(x.mean())))
    table(O/'coordinate_region_summary.csv',summaries)
    dump(O/'coordinate_release_gate.json',dict(status='EXTERNAL_DATUM_UNVERIFIED',existing_source='S7/SP3 2023-03-21 to 23; not Jan4/Mar24',
        existing_single_factor_samples=len(rows),new_density_queries=0,independent_ITRS_recalculation=True,
        missing=['external lower-boundary zero reference and error budget','model geographic latitude vs Earth-fixed registration',
                 'independently validated forward/inverse external mapping'],
        official_grid_URL='https://www.hao.ucar.edu/modeling/tgcm/tiegcm2.0/userguide/html/grid.html'))


def flow_diagnostics(lat,lon,iv):
    day='2023-03-24';truth=np.stack([reference(day,h)[0].astype(float) for h in range(1,14)])
    tl=np.stack([reference(day,h)[2] for h in range(1,14)])
    p=load(oldpaths(day)[1]/f'{day}_Flow.npz','Flow');q=load(ROOT/'data/processed/fourcastden_ideal_update_6h_v1'/f'{day}_Flow.npz','Flow')
    A=np.zeros((29,29));A[0,:2]=[1.5,-.5]
    for k in range(1,29):A[k,k-1:k+1]=.5
    inv=np.linalg.inv(A)
    rows=[];points=[];layers=[];numbers=[]
    b_ref,ti_ref,factor=mass_input(truth,tl,iv)
    mr=np.einsum('ij,tjxy->tixy',inv,b_ref)
    all_cases=[('Reference',truth,range(1,14),tl),('Open',p,range(1,14),tl),('Updated',q,range(7,14),tl[6:])]
    for label,ph,hours,lbc in all_cases:
        zg,valid,mass=reconstruct_native_zg(ph[:,:28],ph[:,142:],ph[:,113:142],lbc,lat,iv)
        bi,ti,fact=mass_input(ph,lbc,iv);direct=np.einsum('ij,tjxy->tixy',inv,bi)
        np.testing.assert_allclose(direct,mass,rtol=1e-12,atol=1e-11)
        long=np.empty_like(bi,dtype=np.longdouble);long[:,0]=.5*(bi[:,0].astype(np.longdouble)+bi[:,1].astype(np.longdouble))
        for k in range(1,29):long[:,k]=2*bi[:,k].astype(np.longdouble)-long[:,k-1]
        f32=bi.astype(np.float32);mm=f32.copy();mm[:,0]=.5*(f32[:,0]+f32[:,1])
        for k in range(1,29):mm[:,k]=2*f32[:,k]-mm[:,k-1]
        pert=bi*1e-6*((-1.)**np.arange(29))[None,:,None,None]
        dm=np.einsum('ij,tjxy->tixy',inv,pert)
        for it,hour in enumerate(hours):
            ir=hour-1;rho=ph[it,142:];rr=truth[ir,142:]
            # Exact symmetric bilinear decomposition. No replacement forecast.
            bd=fact[0]*(rho-rr)*.5*(ti[it]+ti_ref[ir])
            bt=fact[0]*.5*(rho+rr)*(ti[it]-ti_ref[ir])
            md=np.einsum('ij,jxy->ixy',inv,bd);mt=np.einsum('ij,jxy->ixy',inv,bt)
            closure=mass[it]-mr[ir]-md-mt
            assert np.max(abs(closure))<1e-10
            bad=(mass[it]<4)|(mass[it]>32);cols=bad.any(axis=0)
            upper_only=cols & ~bad[:27].any(axis=0)
            for region,masklat in [('global',np.ones(len(lat),bool)),('south',lat<=-60),('north',lat>=60),('midlow',abs(lat)<60)]:
                mask=np.broadcast_to(masklat[:,None],cols.shape)
                rows.append(dict(scheme=label,hour_UTC=hour,region=region,total_columns=int(mask.sum()),
                    invalid_columns=int((cols&mask).sum()),only_indices27_28=int((upper_only&mask).sum()),
                    mass_min=float(mass[it,:,mask].min()),mass_max=float(mass[it,:,mask].max()),
                    Z_nonmonotone=int(((np.diff(ph[it,113:142],axis=0)<=0).any(axis=0)&mask).sum()),
                    decomposition_closure_max=float(abs(closure[:,mask]).max())))
            for k in range(29):
                for region,masklat in [('south',lat<=-60),('north',lat>=60),('midlow',abs(lat)<60)]:
                    mid=.5*(zg[it,k]+zg[it,k+1]) if k<28 else np.full_like(zg[it,0],np.nan)
                    ma=mass[it,k,masklat];dd=md[k,masklat];dt=mt[k,masklat]
                    layers.append(dict(scheme=label,hour_UTC=hour,index=k,region=region,grid='lev midpoint; 28 is upper auxiliary',
                        inverse_mass_min=float(ma.min()),inverse_mass_max=float(ma.max()),invalid_points=int(bad[k,masklat].sum()),
                        DEN_contribution_RMS=float(np.sqrt(np.mean(dd**2))),TN_contribution_RMS=float(np.sqrt(np.mean(dt**2))),
                        mass_difference_RMS=float(np.sqrt(np.mean((ma-mr[ir,k,masklat])**2))),
                        height_derived_from='diagnostic reconstructed adjacent ZG; invalid columns retained, not qualified geometry',
                        midpoint_median_km=float(np.median(mid[masklat])/1000) if k<28 else '',used_in_calczg_increment=bool(k<27)))
            if label=='Updated':
                for j,i in zip(*np.nonzero(cols)):
                    over=np.maximum(4-mass[it,:,j,i],mass[it,:,j,i]-32);k=int(np.argmax(over))
                    points.append(dict(hour_UTC=hour,lat=float(lat[j]),lon=float(lon[i]),worst_index=k,
                        inferred_mass=float(mass[it,k,j,i]),reference_inferred_mass=float(mr[ir,k,j,i]),
                        DEN_mass_difference_contribution=float(md[k,j,i]),TN_mass_difference_contribution=float(mt[k,j,i]),
                        closure=float(closure[k,j,i]),interface_input_mass=float(bi[it,k,j,i]),
                        interface_inputs_all_inside_4_32=bool(((bi[it,:,j,i]>=4)&(bi[it,:,j,i]<=32)).all()),
                        only_unused_for_ZG_increment=bool(upper_only[j,i]),excess_over_bound=float(over[k])))
            numbers.append(dict(scheme=label,hour_UTC=hour,max_double_vs_longdouble=float(abs(mass[it]-long[it]).max()),
                max_float32_recurrence_difference=float(abs(mass[it]-mm[it]).max()),
                max_mass_response_to_alternating_1ppm_B=float(abs(dm[it]).max()),
                direct_matrix_vs_recurrence_max=float(abs(direct[it]-mass[it]).max()),
                max_forward_roundtrip_residual=float(abs(np.einsum('ij,jxy->ixy',A,mass[it])-bi[it]).max())))
    table(O/'flow_region_times.csv',rows);table(O/'flow_failed_columns.csv',points);table(O/'flow_layer_diagnosis.csv',layers);table(O/'flow_numerical_sensitivity.csv',numbers)
    dump(O/'flow_inverse_analysis.json',dict(matrix_condition_2=float(np.linalg.cond(A)),inverse_infinity_norm=float(np.linalg.norm(inv,np.inf)),
        forward_infinity_norm=float(np.linalg.norm(A,np.inf)),double_vs_longdouble_max=max(x['max_double_vs_longdouble'] for x in numbers),
        float32_recurrence_difference_max=max(x['max_float32_recurrence_difference'] for x in numbers),
        failed_updated_columns=len(points),all_interface_masses_inside_among_failed=sum(x['interface_inputs_all_inside_4_32'] for x in points),
        source_notes=['addiag.F:93-124 M to B smoothing and lower extrapolation','dt.F:220-245 density from B,T_interface',
            'addiag.F:267-275 calczg uses inferred midpoint indices0..26 for increments; top ZG extrapolated',
            'legacy validator still tests0..28; no gate changed'],
        statements=dict(proven='linear inverse can amplify alternating interface errors; TN/DEN product perturbations decompose exactly; Z absent from mass inversion',
            not_proven='a conservation-law violation, causal network failure mechanism, or exact future true height error')))


def synthetic_integration():
    # Import the analytic oracle, not a second gravitational/drag implementation.
    import importlib.util
    spec=importlib.util.spec_from_file_location('event_test',ROOT/'tests/test_event_aware_density.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    rows=[];summ=[]
    for tol,step in [(1e-8,20),(1e-10,10),(1e-12,5)]:
        r,calls=m.run_drag(tol,step);truth=m.analytic_drag(r.times_s);error=r.states-truth
        summ.append(dict(rtol=tol,max_step_s=step,max_position_error_m=float(abs(error[:,:3]).max()),max_velocity_error_m_s=float(abs(error[:,3:]).max()),
            position_event_jump_m=r.event_records[0]['position_jump_m'],velocity_event_jump_m_s=r.event_records[0]['velocity_jump_m_s'],
            acceleration_left_m_s2=r.event_records[0]['acceleration_left'][0],acceleration_right_m_s2=r.event_records[0]['acceleration_right'][0],
            left_last_rhs_s=max(calls[0]),right_first_rhs_s=min(calls[1]),nfev=sum(s.statistics['nfev'] for s in r.segments)))
        for t,y,z in zip(r.times_s,r.states,truth):rows.append(dict(rtol=tol,t_s=t,position_x_m=y[0],velocity_x_m_s=y[3],analytic_x_m=z[0],analytic_v_m_s=z[3]))
    assert summ[-1]['max_position_error_m']<1e-6
    table(O/'synthetic_event_convergence.csv',summ);table(O/'synthetic_event_trajectory.csv',rows)


def observation_review(protected):
    import cdflib
    rows=[];variables=[]
    for p in sorted((ROOT/'data/raw/swarm_drag/extracted').glob('*DNSAPOD*.cdf')):
        protected[str(p.relative_to(ROOT))]=sha(p)
        with cdflib.CDF(p) as c:
            times=cdflib.cdfepoch.to_datetime(c.varget('time'))
            flags=c.varget('validity_flag');rho=c.varget('density')
            rows.append(dict(product=p.name,version='0301',SHA256=sha(p),time_system=c.globalattsget()['TIME SYSTEM'][0],
                records=len(times),start_UTC=str(times[0]),end_UTC=str(times[-1]),cadence_s=float(np.median(np.diff(times)/np.timedelta64(1,'s'))),
                nominal_flags=int((flags==0).sum()),finite_positive_density=int((np.isfinite(rho)&(rho>0)&(rho<1e20)).sum()),
                Jan4_01_13_overlap=int(((times>=np.datetime64('2023-01-04T01'))&(times<=np.datetime64('2023-01-04T13'))).sum()),
                Mar24_01_13_overlap=int(((times>=np.datetime64('2023-03-24T01'))&(times<=np.datetime64('2023-03-24T13'))).sum())))
            for name in c.cdf_info().zVariables:
                info=c.varinq(name);attrs=c.varattsget(name)
                variables.append(dict(product=p.name,variable=name,units=attrs.get('UNITS',''),meaning=attrs.get('VARIABLE DESCRIPTION',''),dtype=info.Data_Type_Description))
    table(O/'local_Swarm_observation_inventory.csv',rows);table(O/'local_Swarm_variable_contract.csv',variables)
    sp3=[]
    for p in sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3')):
        protected[str(p.relative_to(ROOT))]=sha(p)
        lines=p.read_text().splitlines();epochs=[x for x in lines if x.startswith('*')]
        sp3.append(dict(product=p.name,SHA256=sha(p),first_epoch_raw_GPS=epochs[0],last_epoch_raw_GPS=epochs[-1],
            epochs=len(epochs),header=lines[0],known_time_frame='GPS calendar / IGS20; use existing frozen conversion, not UTC relabel',
            requested_Jan4_Mar24_overlap=False))
    table(O/'local_SP3_inventory.csv',sp3)
    dump(F/'protected_final.json',protected)


if __name__=='__main__':main()
