"""Single existing 2022 trajectory vs official DNS; prior 2021 results read only."""
from pathlib import Path
import sys,json,csv,time,resource,shutil,zipfile,urllib.parse,re
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from prepare_fourcastden_swarm_observation_v1 import bounded_get,sha,dump,inside
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from atmosphere.provisional_coordinate_adapter import ProvisionalCoordinateAdapter,A_WGS84,B_SPHERE
from atmosphere.density_interface import DensityQuery
from atmosphere.tiegcm_density_provider import DATUM
from evaluation.swarm_density_comparison import quality_mask,compare_density,paired_valid_mask
from evaluation.swarm_crossyear import strata,metric_row,MIN_SAMPLES,HEIGHT_EDGES_KM
from orbit.swarm_force_inputs import cdf_epoch_utc64
from astropy.coordinates import EarthLocation
from astropy.time import Time
import astropy.units as u
from netCDF4 import Dataset
import cdflib
TAG='swarm_tiegcm_2022_observation_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG;D=ROOT/'data/raw'/TAG
OLD=ROOT/'results/swarm_tiegcm_2021_spinup_observation_v1'
CASE=ROOT/'experiments/tiegcm_training_mar23_v2_2022_longrun'
MAPS='ABDE'
def table(path,rows):
    with inside(path).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def read_observation(path):
    with cdflib.CDF(path) as c:
        g=c.globalattsget();attrs={k:c.varattsget(k) for k in c.cdf_info().zVariables}
        assert g['TIME SYSTEM']==['UTC'] and attrs['density']['UNITS']=='kg/m3'
        assert attrs['latitude']['UNITS']=='deg' and attrs['altitude']['UNITS']=='m'
        a={k:c.varget(k) for k in ['time','density','latitude','longitude','altitude','validity_flag']}
        a['utc']=cdf_epoch_utc64(a.pop('time'))
        a['quality'],_=quality_mask(a['density'],a['validity_flag'])
    return a,dict(global_attributes=g,variables=attrs)
def mapping_coordinates(a):
    loc=EarthLocation.from_geodetic(a['longitude']*u.deg,a['latitude']*u.deg,a['altitude']*u.m,ellipsoid='GRS80')
    xyz=np.column_stack([v.to_value(u.m) for v in loc.geocentric]);out=[]
    for t,r,lo in zip(Time(a['utc']),xyz,a['longitude']):
        q=DensityQuery.from_itrs(t,r);aa=ProvisionalCoordinateAdapter(assumption=A_WGS84).adapt(q);b=ProvisionalCoordinateAdapter(assumption=B_SPHERE,sphere_radius_m=6371000).adapt(q)
        out.append([(aa.model_latitude_deg,lo,aa.model_zg_m),(b.model_latitude_deg,lo,b.model_zg_m),(b.model_latitude_deg,lo,aa.model_zg_m),(aa.model_latitude_deg,lo,b.model_zg_m)])
    return np.array(out)
def main():
    started=time.perf_counter()
    for p in (F,O,D):inside(p);p.mkdir(exist_ok=False)
    protected={str(p.relative_to(ROOT)):sha(p) for folder in [OLD,ROOT/'experiments/swarm_tiegcm_2021_spinup_observation_v1'] for p in folder.rglob('*') if p.is_file()}
    for rel in ['reports/SWARM_TIEGCM_2021_SPINUP_OBSERVATION_V1.md','src/atmosphere/hourly_tiegcm_observation.py','src/atmosphere/tiegcm_density_provider.py','src/atmosphere/provisional_coordinate_adapter.py','src/evaluation/swarm_density_comparison.py']:
        protected[rel]=sha(ROOT/rel)
    dump(F/'protected_before.json',protected)
    assert shutil.disk_usage(ROOT).free>20*2**30
    dump(F/'protocol.json',dict(date='2022-03-24',primary_comparison='2021 A7 vs 2022 single smin seven-day trajectory; NOT single-factor year experiment',maps=list(MAPS),primary_map='A',sphere_radius_m=6371000,minimum_samples=MIN_SAMPLES,height_edges_km=HEIGHT_EDGES_KM,latitude='low abs<30; mid30<=abs<60; high abs>=60; north>=60/south<=-60; hemispheres>=0/<0',UTC_blocks_hours=3,quality='0301:0 nominal,1 anomalous,unknown rejected; instantaneous positive finite density',relative_denominator='observed instantaneous density; no floor',relative_bias='mean((model-observed)/observed); separately bias/mean(observed)',common_domain='within-year intersection of quality and ALL mappings (2021 frozen four trajectories/16 combinations; 2022 four combinations); no cross-year sample identity asserted',interpolation='existing hourly adapter; all eight columns; vertical logDEN/horizontal density bilinear/time density linear',download_limit_bytes=10*2**20,CPU_wall_limit_s=1800,RSS_limit_GiB=4,expected_wall_s=180,expected_RSS_MiB=350,output_limit_MiB=100,free_disk_bytes=shutil.disk_usage(ROOT).free,meminfo_available=[s for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable')],external_datum='EXTERNAL_DATUM_UNVERIFIED',no_training=True,no_model_launches=True))
    # Verify actually matching initialization and static physical configuration.
    config_audit={};namelists=[]
    for year in [2021,2022]:
        folder=ROOT/f'experiments/tiegcm_training_mar23_v2_{year}_longrun'
        pre=json.loads((folder/'preflight.json').read_text());cfg=json.loads((folder/'configuration.json').read_text())
        text=(folder/'input.inp').read_text();assert sha(folder/'input.inp')==pre['input_sha256']
        vals={k:v.strip() for k,v in re.findall(r'^\s*(\w+)\s*=\s*(.*?)\s*$',text,re.M)}
        source=Path(vals['SOURCE'].strip("'"));gpi=Path(vals['GPI_NCFILE'].strip("'"))
        assert sha(source)==pre['restart_sha256'] and sha(gpi)==pre['gpi_sha256']
        protected[str(source.relative_to(ROOT))]=pre['restart_sha256'];protected[str(gpi.relative_to(ROOT))]=pre['gpi_sha256']
        config_audit[str(year)]=dict(preflight=pre,source=str(source.relative_to(ROOT)),source_SHA=sha(source),gpi=str(gpi.relative_to(ROOT)),gpi_SHA=sha(gpi),namelist=vals,input_SHA=sha(folder/'input.inp'))
        namelists.append(vals)
    for k in ['SOURCE','SOURCE_START','STEP','POTENTIAL_MODEL','CALC_HELIUM','GSWM_MI_DI_NCFILE','GSWM_MI_SDI_NCFILE','HIST','SECHIST','SECFLDS']:
        assert namelists[0][k]==namelists[1][k],k
    for k in ['restart_sha256','executable_sha256','apex_sha256']:
        assert config_audit['2021']['preflight'][k]==config_audit['2022']['preflight'][k]
    dump(F/'configuration_comparability.json',config_audit)
    # Official directory and bounded unique product download.
    folder='swarm/Level2daily/Latest_baselines/DNS/POD/Sat_A'
    listing=bounded_get('https://swarm-diss.eo.esa.int/?'+urllib.parse.urlencode(dict(do='list',maxfiles=10000,pos=0,file=folder)),D/'listing.json',6*2**20)
    items=[x for x in json.loads((D/'listing.json').read_text())['results'] if '20220324T000000' in x['name']]
    if len(items)!=1 or not items[0]['name'].endswith('_0301.ZIP'):raise ValueError('Actual unique0301 product required')
    item=items[0];assert item['size']+listing['bytes']+65536<10*2**20
    dump(F/'download_plan.json',dict(item=item,listing=listing,remaining_bytes=10*2**20-listing['bytes']))
    receipt=bounded_get('https://swarm-diss.eo.esa.int/?'+urllib.parse.urlencode(dict(do='download',file=item['path'])),D/item['name'],10*2**20-listing['bytes']-65536,item['size'])
    members=[]
    with zipfile.ZipFile(D/item['name']) as z:
        assert z.testzip() is None and sum(i.file_size for i in z.infolist())<4*2**20
        for x in z.infolist():
            assert Path(x.filename).name==x.filename
            p=D/x.filename
            with p.open('xb') as f:f.write(z.read(x))
            members.append(dict(path=str(p.relative_to(ROOT)),SHA256=sha(p),CRC32=x.CRC))
    info=bounded_get('https://vires.services/hapi/info?id=SW_OPER_DNSAPOD_2_',D/'HAPI_info.json',65536)
    params={p['name']:p for p in json.loads((D/'HAPI_info.json').read_text())['parameters']}
    assert params['validity_flag']['description']=='0 = nominal data, 1 = anomalous data' and 'GRS80' in params['Latitude_GD']['description']
    dump(F/'downloads.json',dict(listing=listing,product=receipt,members=members,info=info,total_bytes=listing['bytes']+receipt['bytes']+info['bytes']))
    a,contract=read_observation(next(D.glob('*.cdf')));dump(F/'CDF_contract_local.json',contract)
    assert len(a['utc'])==2880 and np.all(np.diff(a['utc'])==np.timedelta64(30,'s'))
    assert str(a['utc'][0]).startswith('2022-03-24T00:00:00') and str(a['utc'][-1]).startswith('2022-03-24T23:59:30')
    dump(F/'quality.json',dict(records=len(a['utc']),valid=int(a['quality'].sum()),flag_distribution={str(k):int(n) for k,n in zip(*np.unique(a['validity_flag'],return_counts=True))},CDF_schema={k:v for k,v in contract['variables'].items()}))
    coords=mapping_coordinates(a)
    j=json.loads((CASE/'data_audit.json').read_text());entries=[e for e in j['files'] if e['file'].startswith('secondary') and any('2022-03-24' in t or '2022-03-25T00:00' in t for t in e['UTC'])]
    expected={e['file']:e['SHA256'] for e in entries};p=HourlyTiegcmObservation([CASE/e['file'] for e in entries],expected,'2022-03-24','2022-03-25','2022_A7')
    dump(F/'inputs.json',dict(files=entries,frames=len(p.records),grid_shape=list(p.arrays[0][0].shape),lat=p.lat.tolist(),lon=p.lon.tolist(),ilev=p.ilev.tolist(),units='DEN g/cm3*1000;ZG cm*.01;both ilev'))
    for e in entries:protected[str((CASE/e['file']).relative_to(ROOT))]=e['SHA256']
    # Small actual grid-point check before full-day query.
    height=float(np.mean(p.arrays[0][0][20:22,18,10]));r=p.query_native('2022-03-24',p.lat[18],p.lon[10],height,datum=DATUM)
    direct=np.exp(np.interp(height,p.arrays[0][0][:,18,10],np.log(p.arrays[0][1][:,18,10])))
    assert r.valid and np.isclose(r.rho_kg_m3,direct,rtol=1e-13)
    for z,rho in p.arrays:assert np.isfinite(z).all() and np.isfinite(rho).all() and (rho>0).all() and (np.diff(z,axis=0)>0).all()
    values=np.full((4,len(a['utc'])),np.nan);queries=[]
    for mi,ma in enumerate(MAPS):
        for i,t in enumerate(Time(a['utc'])):
            if time.perf_counter()-started>1800 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>4*1024**2:raise RuntimeError('Resource budget')
            if not a['quality'][i]:continue
            r=p.query_native(t,*coords[i,mi],datum=DATUM)
            if r.valid:values[mi,i]=r.rho_kg_m3
            queries.append(dict(sample=i,UTC=str(a['utc'][i]),mapping=ma,valid=r.valid,reason=r.reason,rho_kg_m3=r.rho_kg_m3,top_margin_m=r.metadata.get('top_margin_m')))
        print('2022 mapping',ma,'complete',flush=True)
    common=paired_valid_mask(a['quality'],*values);table(O/'queries_local.csv',queries)
    np.savez_compressed(O/'aligned_local.npz',values=values,common=common,coords=coords,**a)
    # Recheck 2021 stored metrics without re-querying or modifying prior outputs.
    old=np.load(OLD/'aligned_local.npz');assert np.array_equal(old['common'],paired_valid_mask(old['quality'],*old['values'].reshape(16,-1)))
    oldmetrics=list(csv.DictReader((OLD/'metrics.csv').open()))
    for r in oldmetrics:
        if r['region']!='all':continue
        x=old['values'][MAPS.index(r['mapping']),['A7','B7','A14','B14'].index(r['group']),old['common']];met=compare_density(x,old['observed'][old['common']])
        for k in ['MAE','RMSE','bias','relative_RMS']:assert np.isclose(float(r[k]),met[k],rtol=1e-13,atol=0)
    oldraw=next((ROOT/'data/raw/swarm_tiegcm_2021_spinup_observation_v1').glob('*.cdf'));a21,_=read_observation(oldraw)
    assert np.array_equal(a21['utc'],old['utc']) and np.array_equal(a21['density'],old['observed'])
    metrics=[];coverage=[];drives=[];geometry=[]
    for year,aa,vv,mask,cc in [(2021,a21,old['values'][:,0],old['common'],old['coords']),(2022,a,values,common,coords)]:
        for mi,ma in enumerate(MAPS):
            for name,region in strata(aa['latitude'],aa['altitude'],aa['utc']).items():
                metrics.append(dict(year=year,trajectory='A7_smin',spinup_days=7,mapping=ma,region=name,**metric_row(vv[mi],aa['density'],aa['quality'],mask,region)))
            reasons={}
            if year==2022:
                for q in queries:
                    if q['mapping']==ma and not q['valid']:reasons[q['reason']]=reasons.get(q['reason'],0)+1
            coverage.append(dict(year=year,mapping=ma,records=len(mask),quality=int(aa['quality'].sum()),own_valid=int(np.isfinite(vv[mi]).sum()),common=int(mask.sum()),failures=json.dumps(reasons)))
        geometry.append(dict(year=year,height_A_min_m=float(cc[:,0,2].min()),height_A_max_m=float(cc[:,0,2].max()),B_minus_A_height_min_m=float((cc[:,1,2]-cc[:,0,2]).min()),B_minus_A_height_max_m=float((cc[:,1,2]-cc[:,0,2]).max()),B_minus_A_lat_abs_max_deg=float(np.abs(cc[:,1,0]-cc[:,0,0]).max())))
        folder=ROOT/f'experiments/tiegcm_training_mar23_v2_{year}_longrun';audit=json.loads((folder/'data_audit.json').read_text())
        for e in audit['files']:
            if not e['file'].startswith('secondary') or not any(str(year)+'-03-24' in t for t in e['UTC']):continue
            assert sha(folder/e['file'])==e['SHA256']
            with Dataset(folder/e['file']) as n:
                for i,t in enumerate(e['UTC']):
                    if str(year)+'-03-24' in t:drives.append(dict(year=year,UTC=t,**{k:float(n[k][i]) for k in ['f107d','f107a','Kp']}))
    table(O/'metrics.csv',metrics);table(O/'coverage.csv',coverage);table(O/'geometry.csv',geometry);table(O/'drivers.csv',drives)
    sensitivity=[]
    for year,vv,mask in [(2021,old['values'][:,0],old['common']),(2022,values,common)]:
        for mi,ma in enumerate(MAPS[1:],1):
            rel=vv[mi,mask]/vv[0,mask]-1
            sensitivity.append(dict(year=year,mapping=ma,comparison='mapping/A-1; same model,same UTC,position',n=int(mask.sum()),signed_mean=float(rel.mean()),absolute_P95=float(np.percentile(abs(rel),95)),absolute_max=float(abs(rel).max())))
    table(O/'mapping_sensitivity.csv',sensitivity)
    assert all(sha(ROOT/rel)==h for rel,h in protected.items())
    dump(F/'independent_audit.json',dict(PASS=True,protected_assets=len(protected),old_2021_metrics_reproduced=16,small_actual_gridpoint_PASS=True,source_files_checked=len(entries),model_launches=0))
    dump(F/'protected_after.json',protected)
    dump(F/'runtime.json',dict(wall_s=time.perf_counter()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,queries=len(queries),common=int(common.sum()),model_launches=0))
if __name__=='__main__':main()
