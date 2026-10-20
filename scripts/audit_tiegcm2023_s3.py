"""Read-only S3 audit and reproducible plots. Never launches an integrator."""
from pathlib import Path
import argparse,importlib.util,sys,json,re,csv,datetime
import numpy as np
from netCDF4 import Dataset,num2date
import matplotlib.pyplot as plt
from astropy.coordinates import EarthLocation
import astropy.units as u
from astropy.time import Time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from atmosphere.tiegcm_drivers import GpiDriver
from atmosphere.restart_validation import REQUIRED
from evaluation.orbit_data import load_sp3_reference
from orbit.frames import configure_time_data
sp=importlib.util.spec_from_file_location('s3',ROOT/'scripts/run_tiegcm2023_s3.py');s3=importlib.util.module_from_spec(sp);sp.loader.exec_module(s3)


def at_height(z,density,height):
    """Column log-density interpolation in native ZG; never extrapolate."""
    idx=(z<=height).sum(axis=0)-1;valid=(idx>=0)&(idx<z.shape[0]-1)
    safe=np.clip(idx,0,z.shape[0]-2)[None,...]
    z0=np.take_along_axis(z,safe,axis=0)[0];z1=np.take_along_axis(z,safe+1,axis=0)[0]
    a=np.take_along_axis(density,safe,axis=0)[0];b=np.take_along_axis(density,safe+1,axis=0)[0]
    valid&=np.isfinite(z0)&np.isfinite(z1)&(z1>z0)&(a>0)&(b>0)
    out=np.full(valid.shape,np.nan)
    out[valid]=np.exp(np.log(a[valid])+(height-z0[valid])/(z1[valid]-z0[valid])*(np.log(b[valid])-np.log(a[valid])))
    return out


def write_csv(path,rows):
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-tag',required=True);args=parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+',args.run_tag):raise ValueError('Bad tag')
    out=s3.s.inside(ROOT/'experiments'/args.run_tag)
    if (out/'data_audit.json').exists():raise FileExistsError('Audit exists')
    status=json.loads((out/'run_status.json').read_text())
    if (out/'guardian_status.json').exists():
        guardian=json.loads((out/'guardian_status.json').read_text());assert guardian['stop_reason'] is None
        status['resource_samples']+=guardian['resource_samples'];status['resource_samples'].sort(key=lambda v:v['wall_s'])
        status['peak_sampled_tree_rss_bytes']=max(status['peak_sampled_tree_rss_bytes'],guardian['peak_sampled_tree_rss_bytes'])
    assert status['returncode']==0 and status['stop_reason'] is None and status['normal_exit_count']==4
    log=(ROOT/'logs'/f'{out.name}.log').read_text();assert 'init: iyear= 2023 iday=   77' in log and 'calling apxparm: start_year= 2023' in log
    assert len(re.findall(r'nstep=\s*7210 step=\s*60',log))==4
    suspicious=re.findall(r'(?im)^.*(?:\bNaN\b|\bInf\b|WARNING|ERROR|bad isec_req).*$',log);assert not suspicious,suspicious[:5]
    for day in range(77,82):assert re.search(rf'Advancing day \(previous,present\)=\s*{day}\s*2023\s*{day+1}\s*2023',log)
    drv=GpiDriver(s3.s.GPI);p,q=s3.schedules();files=[];rows=[];drivers=[];snapshots={};primary_times=[];secondary_times=[];common450=[]
    heights=[200,300,400,450,475,500]
    ranges={name:[float('inf'),-float('inf')] for name in ['DEN','ZG','TN','UN','VN','O1','O2','N2','HE']}
    for primary,volumes in [(True,p),(False,q)]:
        prefix='primary' if primary else 'secondary';actual=sorted(out.glob(prefix+'_*.nc'));assert len(actual)==len(volumes)
        for path,expected in zip(actual,volumes):
            s3.basic_file(path)
            with Dataset(path) as n:
                times=np.asarray(n['mtime'][:],int);secs=[s3.c.seconds(t) for t in times];assert secs==expected
                assert np.all(n['year'][:]==2023) and np.all(n['calendar_advance'][:]==1) and int(n['timestep'][:])==60
                dates=[str(x) for x in num2date(n['time'][:],n['time'].units)]
                independent=[str(datetime.datetime(2023,1,1)+datetime.timedelta(seconds=int(t-86400))) for t in secs];assert dates==independent
                assert np.array_equal(n['day'][:],times[:,0]);assert np.allclose(n['ut'][:]*3600,times[:,1]*3600+times[:,2]*60,atol=1e-8,rtol=0)
                if primary:
                    primary_times+=secs
                    assert all(n[k].dtype==np.dtype('float64') for k in REQUIRED)
                    if secs[0]!=77*86400:assert int(n['iter'][0])==secs[0]//60
                else:secondary_times+=secs
                schema={name:{'units':getattr(v,'units',None),'dimensions':list(v.dimensions),'dtype':str(v.dtype)} for name,v in n.variables.items() if name in (REQUIRED if primary else ranges)}
                if not primary:
                    for name in ranges:
                        v=n[name];assert v.dimensions==('time','ilev' if name in ['DEN','ZG'] else 'lev','lat','lon')
                        assert v.units=={'DEN':'g/cm3','ZG':'cm','TN':'K','UN':'cm/s','VN':'cm/s'}.get(name,'mmr')
                files.append({'file':path.name,'bytes':path.stat().st_size,'sha256':s3.s.sha(path),'utc':dates,'fields':schema})
                for i,(t,date) in enumerate(zip(secs,dates)):
                    if t!=77*86400:
                        e=drv.at(2023000+t//86400,t%86400);values={k:float(n[k][i]) for k in e};err=max(abs(values[k]-e[k]) for k in e);assert err<1e-10
                        drivers.append({'file':path.name,'utc':date,**values,'max_independent_difference':err})
                    if primary or t==77*86400:continue  # Native cold echo diagnostics uncomputed, not a prediction
                    fields={name:s3.field(n[name])[i] for name in ranges}
                    for name,v in fields.items():
                        ranges[name][0]=min(ranges[name][0],float(v.min()));ranges[name][1]=max(ranges[name][1],float(v.max()))
                    for name in ['TN','UN','VN']:
                        mask=np.ma.getmaskarray(fields[name]);assert mask[-1].all() and not mask[:-1].any()
                    z=np.asarray(fields['ZG'])*.01;den=np.asarray(fields['DEN'])*1000;lat=np.asarray(n['lat'][:]);lon=np.asarray(n['lon'][:]);weights=np.broadcast_to(np.cos(np.deg2rad(lat))[:,None],den[0].shape)
                    row={'utc':date,'model_seconds':t,'TN_min_K':float(fields['TN'].min()),'TN_max_K':float(fields['TN'].max()),'UN_absmax_m_s':float(abs(fields['UN']).max()*.01),'VN_absmax_m_s':float(abs(fields['VN']).max()*.01),'top_min_km':float(z[-1].min()/1000),'top_max_km':float(z[-1].max()/1000),'F107':float(n['f107d'][i]),'F107A':float(n['f107a'][i]),'Kp':float(n['Kp'][i]),'POWER_GW':float(n['hpower'][i]),'CTPOTEN_kV':float(n['ctpoten'][i])}
                    for name in ['O1','O2','N2','HE']:row[name+'_mean_mmr']=float(fields[name].mean())
                    for h in heights:
                        d=at_height(z,den,h*1000)
                        if h==450 and t>=80*86400:common450.append(d.copy())
                        valid=np.isfinite(d);row[f'DEN_ZG{h}km_valid_fraction']=float(valid.mean());row[f'DEN_ZG{h}km_weighted_mean_kg_m3']=float(np.average(d[valid],weights=weights[valid])) if valid.any() else float('nan')
                    rows.append(row)
                    if t in [77*86400,78*86400,79*86400,80*86400,81*86400,82*86400,82*86400+600]:snapshots[date]={'density450':at_height(z,den,450000),'top_km':z[-1]/1000,'lat':lat,'lon':lon}
    assert primary_times==sum(p,[]) and secondary_times==sum(q,[]) and len(secondary_times)==293
    assert len([t for t in secondary_times if t>=80*86400])==290
    seen=set();max_logerr=0
    pattern=r'GPI run: mtime=\s*(\d+)\s+(\d+)\s+(\d+) power=\s*([\d.]+) ctpoten=\s*([\d.]+) f107=\s*([\d.]+) f107a=\s*([\d.]+)'
    for d,h,m,power,cp,f,fa in re.findall(pattern,log):
        e=drv.at(2023000+int(d),int(h)*3600+int(m)*60);seen.add((int(d),int(h),int(m)))
        for value,key in [(power,'hpower'),(cp,'ctpoten'),(f,'f107d'),(fa,'f107a')]:max_logerr=max(max_logerr,abs(float(value)-e[key]));assert abs(float(value)-e[key])<=.000501
    # Swarm review deliberately stops before declaring exact vertical datum equivalence.
    configure_time_data();ref=load_sp3_reference((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'));elapsed=(ref.times-Time('2023-03-21T00:00:02',scale='utc')).to_value(u.s);select=(elapsed>=-1e-6)&(elapsed<=172800+1e-6)
    loc=EarthLocation.from_geocentric(*ref.positions_m[select].T,unit=u.m);orbit={'SP3_frame':ref.frame,'samples':int(select.sum()),'WGS84_height_km':[float(loc.height.to_value(u.km).min()),float(loc.height.to_value(u.km).max())],'radial_height_above_6371km_sphere_km':[float((np.linalg.norm(ref.positions_m[select],axis=1)/1000-6371).min()),float((np.linalg.norm(ref.positions_m[select],axis=1)/1000-6371).max())],'precise_density_query_valid_fraction':None,'reason':'Native ZG geographic/datum correspondence to WGS84 and horizontal stencil not yet validated; no extrapolation or density queries performed'}
    maps=np.asarray(common450);assert len(maps)==290
    mid=maps[1:289:2];left=maps[:288:2];right=maps[2:290:2]
    valid=np.isfinite(mid)&np.isfinite(left)&np.isfinite(right)&(mid>0)&(left>0)&(right>0)
    delta=(.5*(np.log(left[valid])+np.log(right[valid]))-np.log(mid[valid]));relative=np.abs(np.expm1(delta))
    decimation={'native_height_km':450,'valid_fraction':float(valid.mean()),'samples':int(valid.sum()),'log_density_RMSE':float(np.sqrt(np.mean(delta**2))),'absolute_relative_error_P95':float(np.percentile(relative,95)),'max_absolute_relative_error':float(relative.max()),'interpretation':'20-min-anchor log interpolation vs actual middle 10-min samples; not proof of native 10-min interpolation accuracy or Swarm along-track validity'}
    changed=[]
    for rel,digest in json.loads((out/'protected_files.json').read_text()).items():
        if s3.s.sha(ROOT/rel)!=digest:changed.append(rel)
    assert not changed
    result={'status':'basic_engineering_audit_passed_not_spinup_convergence','primary_records':len(primary_times),'secondary_records':len(secondary_times),'common_window_records':290,'cold_secondary_diagnostic_record_unavailable':True,'physical_stats_records':292,'runtime_GPI_unique_print_times':len(seen),'runtime_GPI_max_rounding_difference':max_logerr,'stored_drivers_max_difference':max(x['max_independent_difference'] for x in drivers),'field_ranges_native':ranges,'Swarm_review':orbit,'temporal_decimation_native_ZG450km':decimation,'protected_files_changed':changed,'files':files,'model_launches':1,'S7_run':False}
    write_csv(ROOT/'results/metrics'/f'{out.name}_evolution.csv',rows);write_csv(ROOT/'results/metrics'/f'{out.name}_drivers.csv',drivers)
    plt.rcParams.update({'font.size':10});x=np.array([(v['model_seconds']-77*86400)/86400 for v in rows])
    def save(fig,suffix):
        path=ROOT/'results/figures'/f'{out.name}_{suffix}.png'
        if path.exists():raise FileExistsError(path)
        fig.tight_layout();fig.savefig(path,dpi=150);plt.close(fig)
    fig,axes=plt.subplots(3,1,figsize=(10,9),sharex=True)
    for h in [200,300,400,450,475,500]:axes[0].plot(x,[v[f'DEN_ZG{h}km_weighted_mean_kg_m3'] for v in rows],label=f'Native ZG {h} km')
    axes[0].set_yscale('log');axes[0].set_ylabel('Area-weighted density (kg/m³)');axes[0].legend(ncol=3);axes[0].set_title('S3 hindcast: sparse daily warm-up samples, then 10-min outputs')
    axes[1].plot(x,[v['TN_max_K'] for v in rows],label='Global max TN');axes[1].set_ylabel('Temperature (K)');axes[1].legend()
    axes[2].plot(x,[v['Kp'] for v in rows],label='Stored Kp; cold echo excluded');axes[2].set_ylabel('Kp');axes[2].set_xlabel('Days since 2023-03-18 00:00 UTC');axes[2].legend()
    for ax in axes:ax.axvline(3,color='gray',linestyle='--');ax.grid(alpha=.25)
    save(fig,'evolution')
    selected=snapshots['2023-03-21 00:00:00'];fig,ax=plt.subplots(figsize=(10,4));im=ax.pcolormesh(selected['lon'],selected['lat'],selected['density450'],shading='auto');fig.colorbar(im,ax=ax,label='Density (kg/m³)');ax.set(xlabel='Model longitude (deg)',ylabel='Model latitude (deg)',title='2023-03-21 00:00 UTC: native ZG = 450 km (not WGS84 altitude)');save(fig,'density_map')
    fig,ax=plt.subplots(figsize=(10,4));im=ax.pcolormesh(selected['lon'],selected['lat'],selected['top_km'],shading='auto');fig.colorbar(im,ax=ax,label='Top native ZG (km)');ax.set(xlabel='Model longitude (deg)',ylabel='Model latitude (deg)',title='S3 model top: 2023-03-21 00:00 UTC');save(fig,'top_map')
    fig,ax=plt.subplots(figsize=(8,5))
    for row in rows:
        if row['model_seconds'] in [77*86400,78*86400,79*86400,80*86400,81*86400,82*86400]:ax.plot([row[f'DEN_ZG{h}km_weighted_mean_kg_m3'] for h in heights],heights,'o-',label=row['utc'][:10])
    ax.set_xscale('log');ax.set(xlabel='Area-weighted density (kg/m³), valid columns only',ylabel='Native ZG height (km)',title='S3 density by native geometric height; no extrapolation');ax.legend();ax.grid(alpha=.25);save(fig,'height_profiles')
    fig,axes=plt.subplots(3,1,figsize=(10,9),sharex=True)
    for name in ['UN','VN']:axes[0].plot(x,[v[name+'_absmax_m_s'] for v in rows],label=name+' max absolute')
    axes[0].set_ylabel('Wind component (m/s)');axes[0].legend();axes[0].set_title('S3 computed fields and actual stored drivers (cold echo excluded)')
    for name in ['O1','O2','N2','HE']:axes[1].plot(x,[v[name+'_mean_mmr'] for v in rows],label=name)
    axes[1].set_yscale('log');axes[1].set_ylabel('Unweighted grid mean mmr');axes[1].legend(ncol=4)
    axes[2].plot(x,[v['F107'] for v in rows],label='F10.7');axes[2].plot(x,[v['F107A'] for v in rows],label='F10.7A');axes[2].set(ylabel='Solar flux (sfu)',xlabel='Days since 2023-03-18 00:00 UTC');axes[2].legend()
    for ax in axes:ax.axvline(3,color='gray',linestyle='--');ax.grid(alpha=.25)
    save(fig,'fields_drivers')
    samples=status['resource_samples'];fig,axes=plt.subplots(2,1,figsize=(9,6),sharex=True);axes[0].plot([v['wall_s'] for v in samples],[v['rss_bytes']/1024**2 for v in samples]);axes[0].set_ylabel('Sampled tree RSS (MiB)');axes[0].set_title('S3 monitored resources (shared pages counted repeatedly)');axes[1].plot([v['wall_s'] for v in samples],[v['generated_bytes']/1024**3 for v in samples]);axes[1].set(ylabel='Generated output (GiB)',xlabel='Wall time (s)');save(fig,'resources')
    (out/'data_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))
if __name__=='__main__':main()
