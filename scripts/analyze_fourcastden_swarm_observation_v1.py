"""Actual along-track density comparisons, conditional datum, CPU only."""
from pathlib import Path
import csv,json,sys,time,resource,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u
import cdflib
from atmosphere.fourcastden_density import FourCastDENDensity,reconstruct_native_zg,HEIGHT_SOURCE
from atmosphere.event_aware_density import EventAwareDensity
from atmosphere.tiegcm_density_provider import DATUM
from atmosphere.density_interface import DensityQuery
from atmosphere.provisional_coordinate_adapter import ProvisionalCoordinateAdapter,A_WGS84,B_SPHERE
from evaluation.swarm_density_comparison import quality_mask,compare_density,periods,paired_valid_mask
import prepare_fourcastden_swarm_observation_v1 as task
from audit_fourcastden_coordinate_update_v1 import load
from run_fourcastden_ideal_update_6h import reference,oldpaths
F,O,D=task.F,task.O,task.D
MODELS=('Direct','Flow','LogDEN','History');FIELDS=('Reference',)+tuple(m+'_'+s for m in MODELS for s in ('Open','Updated'));MAPS=('A','B','D_lat_only','E_height_only')


def table(path,rows):
    with task.inside(path).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def sensitivity(p,t,la,lo,h):
    k,keys,w=p._stencil(t,la,lo)
    heights=[p.height[kk,:,j,i] for kk,j,i in keys];density=[p.rho[kk,:,j,i] for kk,j,i in keys]
    values=np.array([np.exp(np.interp(h,z,np.log(r))) for z,r in zip(heights,density)]).reshape(2,2,2)
    wt=float((t-p.epochs[k]).sec)/3600
    spatial=w.reshape(2,2,2).sum(axis=0);frames=(values*spatial[None]).sum(axis=(1,2));v=float(w@values.reshape(-1))
    linear=np.array([np.interp(h,z,r) for z,r in zip(heights,density)])
    coarse=[]
    for z,r in zip(heights,density):
        keep=np.unique(np.r_[np.arange(0,len(z),2),len(z)-1]);coarse.append(np.exp(np.interp(h,z[keep],np.log(r[keep]))))
    hi=p.query_native(t,la,lo,h+1000,datum=DATUM);low=p.query_native(t,la,lo,h-1000,datum=DATUM)
    return dict(reference_A_rho=v,time_log_vs_linear_relative=float(np.exp((1-wt)*np.log(frames[0])+wt*np.log(frames[1]))/v-1),
        horizontal_log_vs_linear_relative=float(np.dot([1-wt,wt],np.exp((np.log(values)*spatial[None]).sum(axis=(1,2))))/v-1),
        vertical_linear_vs_log_relative=float(w@linear/v-1),vertical_coarsened_log_relative=float(w@coarse/v-1),
        height_plus_1km_relative=hi.rho_kg_m3/v-1 if hi.valid else None,
        height_minus_1km_relative=low.rho_kg_m3/v-1 if low.valid else None,
        local_dlnrho_dh_per_m=float((np.log(hi.rho_kg_m3)-np.log(low.rho_kg_m3))/2000) if hi.valid and low.valid else None)


def main():
    started=time.perf_counter()
    if (F/'analysis_started.json').exists():raise FileExistsError('Analysis tag already started; preserve outputs')
    task.dump(F/'analysis_started.json',dict(start_UTC=Time.now().isot,models=MODELS,mappings=MAPS))
    def guard():
        if time.perf_counter()-started>1800:raise RuntimeError('1800s phase limit')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>4*1024**2:raise RuntimeError('4GiB RSS limit')
        if shutil.disk_usage(ROOT).free<20*2**30:raise RuntimeError('20GiB free disk floor')
        if sum(p.stat().st_size for d in (F,O) for p in d.rglob('*') if p.is_file())>500*2**20:raise RuntimeError('500MiB output limit')
    protected=json.loads((ROOT/'experiments/fourcastden_ideal_update_6h_v1/protected.json').read_text())
    for p,h in protected.items():assert task.sha(ROOT/p)==h
    for p in (ROOT/'data/processed/fourcastden_ideal_update_6h_v1').glob('*.npz'):
        h=json.loads((ROOT/'experiments/fourcastden_ideal_update_6h_v1'/f'{p.stem}_runtime.json').read_text())['result_SHA'];assert task.sha(p)==h;protected[str(p.relative_to(ROOT))]=h
    for item in json.loads((F/'download_manifest.json').read_text()):
        assert task.sha(ROOT/item['path'])==item['SHA256'];protected[item['path']]=item['SHA256']
        for x in item['members']:assert task.sha(ROOT/x['path'])==x['SHA256'];protected[x['path']]=x['SHA256']
    for rel in ['src/atmosphere/fourcastden_density.py','src/atmosphere/event_aware_density.py','src/atmosphere/provisional_coordinate_adapter.py']:
        protected[rel]=task.sha(ROOT/rel)
    task.dump(F/'protected.json',protected)
    lat=np.load(ROOT/'data/processed/static/lat.npy');lon=np.load(ROOT/'data/processed/static/lon.npy');iv=np.load(ROOT/'data/processed/static/ilev.npy')
    all_metrics=[];counts=[];qc=[];paired=[];geometry=[];interp=[];events=[];coverage=[];hourly=[]
    queryfile=task.inside(O/'queries_local.csv')
    with queryfile.open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['date','sample','UTC','mapping','field','valid','reason','rho_kg_m3','height_lower_m','height_upper_m','time_bracket'],lineterminator='\n');writer.writeheader()
        for day in ('2023-01-04','2023-03-24'):
            path=next((D/'extracted').glob('*'+day.replace('-','')+'*.cdf'))
            with cdflib.CDF(path) as c:
                times=cdflib.cdfepoch.to_datetime(c.varget('time'));obs=c.varget('density');meanobs=c.varget('density_orbitmean');flags=c.varget('validity_flag')
                mask=(times>=np.datetime64(day+'T01:00:00'))&(times<=np.datetime64(day+'T13:00:00'))
                arrays={k:c.varget(k)[mask] for k in ['latitude','longitude','altitude']}
                goodfull,reasons=quality_mask(obs,flags)
                for scope,m in [('full_day',np.ones(len(times),bool)),('target',mask)]:
                    unique,n=np.unique(flags[m],return_counts=True)
                    qc.append(dict(date=day,scope=scope,records=int(m.sum()),quality_valid=int((m&goodfull).sum()),
                        flag_counts=json.dumps({str(k):int(v) for k,v in zip(unique,n)}),
                        anomalous=int((m&reasons['anomalous']).sum()),unknown_flags=int((m&reasons['unknown']).sum()),invalid_density=int((m&reasons['invalid_density']).sum())))
                obs=obs[mask];meanobs=meanobs[mask];flags=flags[mask];good=goodfull[mask];times=times[mask]
            assert len(times)==1441 and np.all(np.diff(times)==np.timedelta64(30,'s'))
            epochs=Time(times,scale='utc');et=[epochs[i] for i in range(len(epochs))];hours=((times-np.datetime64(day))/np.timedelta64(1,'h')).astype(float)
            # Official service actually verifies these original CDF geodetic fields
            # against GRS80 at one same record per date. No GPS relabelling.
            loc=EarthLocation.from_geodetic(arrays['longitude']*u.deg,arrays['latitude']*u.deg,arrays['altitude']*u.m,ellipsoid='GRS80')
            positions=np.column_stack([v.to_value(u.m) for v in loc.geocentric]);coords=[];obsrows=[]
            for i,(t,r) in enumerate(zip(et,positions)):
                query=DensityQuery.from_itrs(t,r)
                a=ProvisionalCoordinateAdapter(assumption=A_WGS84).adapt(query);b=ProvisionalCoordinateAdapter(assumption=B_SPHERE,sphere_radius_m=6371000).adapt(query)
                item=[(a.model_latitude_deg,a.model_longitude_deg,a.model_zg_m),(b.model_latitude_deg,b.model_longitude_deg,b.model_zg_m),
                      (b.model_latitude_deg,a.model_longitude_deg,a.model_zg_m),(a.model_latitude_deg,a.model_longitude_deg,b.model_zg_m)]
                coords.append(item);obsrows.append(dict(sample=i,UTC=t.isot,instantaneous_density_kg_m3=obs[i],orbitmean_density_kg_m3=meanobs[i],
                    validity_flag=int(flags[i]),quality_valid=bool(good[i]),source_lat_GRS80=arrays['latitude'][i],source_lon=arrays['longitude'][i],source_height_GRS80_m=arrays['altitude'][i]))
                geometry.append(dict(date=day,sample=i,UTC=t.isot,A_latitude_deg=item[0][0],A_height_m=item[0][2],
                    B_latitude_deg=item[1][0],B_height_m=item[1][2],delta_latitude_deg=item[1][0]-item[0][0],delta_height_m=item[1][2]-item[0][2],
                    source_GRS80_to_WGS84_height_m=item[0][2]-arrays['altitude'][i]))
            table(O/(day+'_observations_local.csv'),obsrows)
            truth=np.stack([reference(day,h)[0].astype(float) for h in range(1,14)])
            zref=np.stack([reference(day,h)[1] for h in range(1,14)]);tl=np.stack([reference(day,h)[2] for h in range(1,14)])
            epochstrings=[day+f'T{h:02d}:00:00' for h in range(1,14)]
            rf=FourCastDENDensity(epochstrings,lat,lon,truth[:,142:],zref,source='TIEGCM_reference',height_source='AUTHOR_REFERENCE_ZG')
            values=np.full((4,len(FIELDS),len(times)),np.nan);valid=np.zeros_like(values,dtype=bool);why=np.full(values.shape,'NOT_QUERIED',dtype=object)
            def query_provider(provider,field_index):
                for mapping in range(4):
                    for i,t in enumerate(et):
                        if i%200==0:guard()
                        if not good[i]:why[mapping,field_index,i]='OBSERVATION_QUALITY_REJECTED';continue
                        la,lo,h=coords[i][mapping]
                        r=provider.query_native(t,la,lo,h,datum=DATUM)
                        valid[mapping,field_index,i]=r.valid;why[mapping,field_index,i]=r.reason
                        if r.valid:values[mapping,field_index,i]=r.rho_kg_m3
                        hh=r.metadata.get('height_coverage_m',[None,None]);tt=r.metadata.get('time_utc',[])
                        writer.writerow(dict(date=day,sample=i,UTC=t.isot,mapping=MAPS[mapping],field=FIELDS[field_index],valid=r.valid,reason=r.reason,rho_kg_m3=r.rho_kg_m3,
                            height_lower_m=hh[0],height_upper_m=hh[1],time_bracket=';'.join(tt)))
                        if mapping==0 and field_index==0 and r.valid:
                            interp.append(dict(date=day,sample=i,UTC=t.isot,**sensitivity(rf,t,la,lo,h)))
                f.flush();print(day,FIELDS[field_index],'queried',flush=True)
            query_provider(rf,0)
            for mi,model in enumerate(MODELS):
                p=load(oldpaths(day)[1]/f'{day}_{model}.npz',model);q=load(ROOT/'data/processed/fourcastden_ideal_update_6h_v1'/f'{day}_{model}.npz',model)
                providers=[]
                for ph,ep,lbc in [(p,epochstrings,tl),(q,epochstrings[6:],tl[6:])]:
                    zg,v,mass=reconstruct_native_zg(ph[:,:28],ph[:,142:],ph[:,113:142],lbc,lat,iv)
                    providers.append(FourCastDENDensity(ep,lat,lon,ph[:,142:],zg,source=model,height_source=HEIGHT_SOURCE,valid_columns=v))
                event=EventAwareDensity(*providers,day+'T07:00:00')
                query_provider(providers[0],1+2*mi);query_provider(event,2+2*mi)
                before=hours<7
                np.testing.assert_array_equal(values[:,1+2*mi,before],values[:,2+2*mi,before])
                index=int(np.flatnonzero(hours==7)[0]);t=et[index]
                for mapping in range(4):
                    la,lo,h=coords[index][mapping]
                    for side in ('left','right'):
                        r=event.query_native(t,la,lo,h,datum=DATUM,event_side=side)
                        events.append(dict(date=day,model=model,mapping=MAPS[mapping],sample=index,UTC=t.isot,event_side=side,
                            observed_density_kg_m3=obs[index],reference_density_kg_m3=values[mapping,0,index],valid=r.valid,reason=r.reason,rho_kg_m3=r.rho_kg_m3,
                            relative_difference_to_observation=r.rho_kg_m3/obs[index]-1 if r.valid else None,forecast_score=False))
                del p,q,providers,event
            np.savez_compressed(task.inside(O/(day+'_aligned_local.npz')),predictions=values,valid=valid,observed=obs,hours=hours,quality=good,coordinates=np.array(coords),utc=times)
            # All-model/all-A-B intersection is frozen before examining errors.
            common=good&valid[:2].all(axis=(0,1));own_mapping=[good&valid[k].all(axis=0) for k in range(4)]
            regionlat=np.array(coords)[:,0,0]
            regions={'global':np.ones(len(times),bool),'south':regionlat<=-60,'north':regionlat>=60,'midlow':abs(regionlat)<60}
            masks=periods(hours)
            for period,pm in masks.items():
                if period=='event':continue
                for region,rm in regions.items():
                    eligible=pm&rm&good;primary=eligible&common
                    coverage.append(dict(date=day,period=period,region=region,quality_eligible=int(eligible.sum()),common_AB_all_models=int(primary.sum()),
                        common_fraction=float(primary.sum()/eligible.sum()) if eligible.any() else None,excluded_quality_or_query=int((pm&rm).sum()-primary.sum())))
                    for mapping in range(4):
                        for fi,field in enumerate(FIELDS):
                            failed=eligible&~valid[mapping,fi];rs,n=np.unique(why[mapping,fi,failed],return_counts=True)
                            counts.append(dict(date=day,period=period,region=region,mapping=MAPS[mapping],field=field,eligible=int(eligible.sum()),valid=int((eligible&valid[mapping,fi]).sum()),
                                valid_fraction=float(valid[mapping,fi,eligible].mean()) if eligible.any() else None,rejected_reasons=json.dumps(dict(zip(rs.tolist(),n.tolist())))))
                        for model_i,model in enumerate(MODELS):
                            a,b=1+2*model_i,2+2*model_i
                            pairmask=eligible&valid[mapping,0]&valid[mapping,a]&valid[mapping,b]
                            # Primary A/B and diagnostic single factors use the
                            # SAME common AB mask, with any D/E failures explicit.
                            for domain,ms in [('common_AB_all_models',primary&valid[mapping,0]&valid[mapping,a]&valid[mapping,b]),('within_model_pair',pairmask)]:
                                metrics={}
                                for name,idx in [('Reference',0),('Open',a),('Updated',b)]:
                                    met=compare_density(values[mapping,idx,ms],obs[ms]);metrics[name]=met
                                    all_metrics.append(dict(date=day,period=period,region=region,mapping=MAPS[mapping],model=model,scheme=name,domain=domain,
                                        eligible=int(eligible.sum()),comparison_fraction=float(ms.sum()/eligible.sum()) if eligible.any() else None,**met))
                                if period=='post':
                                    ar,br=metrics['Open']['RMSE'],metrics['Updated']['RMSE'];av,bv=metrics['Open']['relative_RMS'],metrics['Updated']['relative_RMS']
                                    paired.append(dict(date=day,region=region,mapping=MAPS[mapping],model=model,domain=domain,n=int(ms.sum()),
                                        open_RMSE=ar,updated_RMSE=br,RMSE_reduction_pct=100*(ar-br)/ar if ar else None,
                                        open_relative_RMS=av,updated_relative_RMS=bv,relative_RMS_reduction_pct=100*(av-bv)/av if av else None,
                                        open_bias=metrics['Open']['bias'],updated_bias=metrics['Updated']['bias'],reference_RMSE=metrics['Reference']['RMSE']))
            for hour in range(1,14):
                hm=(hours>=hour)&(hours<hour+1)&(hours!=7)
                if hour==13:hm=hours==13
                ms=hm&common
                for mapping in range(2):
                    for fi,field in enumerate(FIELDS):hourly.append(dict(date=day,hour_UTC=hour,mapping=MAPS[mapping],field=field,
                        interval='hour-start bins;13 endpoint only',**compare_density(values[mapping,fi,ms],obs[ms])))
            # Coordinate effects hold the observation and physical reference
            # field fixed; intersection is identical for all four maps.
            cm=good&valid[:,0].all(axis=0)
            sens=[]
            for i in range(len(times)):
                a,b,d,e=values[:,0,i]
                sens.append(dict(date=day,sample=i,UTC=et[i].isot,quality_valid=bool(good[i]),all_maps_reference_valid=bool(cm[i]),
                    reference_A=a if np.isfinite(a) else '',reference_B=b if np.isfinite(b) else '',
                    combined_relative=b/a-1 if cm[i] else '',latitude_only_relative=d/a-1 if cm[i] else '',height_only_relative=e/a-1 if cm[i] else '',
                    interaction_relative=(b-d-e+a)/a if cm[i] else ''))
            table(O/(day+'_coordinate_density_sensitivity_local.csv'),sens)
            print(day,'finished',time.perf_counter()-started,flush=True)
    table(O/'metrics.csv',all_metrics);table(O/'query_validity.csv',counts);table(O/'paired_update_changes.csv',paired)
    table(O/'quality_audit.csv',qc);table(O/'common_sample_coverage.csv',coverage);table(O/'hourly_metrics.csv',hourly)
    table(O/'event_07_left_right_local.csv',events);table(O/'geometry_local.csv',geometry);table(O/'interpolation_sensitivity_local.csv',interp)
    assert all(task.sha(ROOT/p)==h for p,h in protected.items())
    guard();task.dump(F/'analysis_completed.json',dict(wall_s=time.perf_counter()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        protected_assets_unchanged=len(protected),metrics=len(all_metrics),new_forward=0,new_TIE=0,new_orbit=0,
        label='PROVISIONAL_OBSERVATION_COMPARISON',formal_datum='EXTERNAL_DATUM_UNVERIFIED',SCIENTIFIC_TRAINING_READY=False))
    print((F/'analysis_completed.json').read_text())


if __name__=='__main__':main()
