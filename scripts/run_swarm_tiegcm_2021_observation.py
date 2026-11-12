"""Frozen one-day four-trajectory observation comparison; no model launches."""
from pathlib import Path
import sys,json,time,resource,csv,zipfile,urllib.parse
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from prepare_fourcastden_swarm_observation_v1 import bounded_get,sha,dump,inside
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from atmosphere.provisional_coordinate_adapter import ProvisionalCoordinateAdapter,A_WGS84,B_SPHERE
from atmosphere.density_interface import DensityQuery
from atmosphere.tiegcm_density_provider import DATUM
from evaluation.swarm_density_comparison import quality_mask,compare_density,paired_valid_mask
from orbit.swarm_force_inputs import cdf_epoch_utc64
from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u
import cdflib
TAG='swarm_tiegcm_2021_spinup_observation_v1'
F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG;D=ROOT/'data/raw'/TAG
GROUPS={'A7':'tiegcm_training_mar23_v2_2021_longrun','B7':'tiegcm_2021_spinup_initial_condition_v1/B','A14':'tiegcm_2021_spinup_14day_v1/A14','B14':'tiegcm_2021_spinup_14day_v1/B14'}
def table(p,rows):
    with inside(p).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    started=time.perf_counter()
    for p in (F,O,D):inside(p);p.mkdir(exist_ok=False)
    dump(F/'config.json',dict(date='2021-03-24',end='2021-03-25T00:00:00',download_limit=10*2**20,wall_limit_s=1800,RSS_limit_GiB=4,groups=GROUPS,maps=['A','B','D','E'],sphere_radius_m=6371000,quality='0301 flag0 nominal; unknown rejected',formal_datum='EXTERNAL_DATUM_UNVERIFIED',relative_denominator='positive instantaneous observed density; no floor',common='intersection of all 16 predictions and quality',expected_wall_s=300,expected_RSS_MiB=350))
    folder='swarm/Level2daily/Latest_baselines/DNS/POD/Sat_A'
    url='https://swarm-diss.eo.esa.int/?'+urllib.parse.urlencode(dict(do='list',maxfiles=10000,pos=0,file=folder))
    listing=bounded_get(url,D/'listing.json',6*2**20)
    items=[x for x in json.loads((D/'listing.json').read_text())['results'] if '20210324T000000' in x['name']]
    if len(items)!=1:raise ValueError('Need unique official target')
    item=items[0];assert item['name'].endswith('_0301.ZIP')
    dump(F/'download_plan.json',dict(item=item,listing=listing,remaining_budget_bytes=10*2**20-listing['bytes']))
    receipt=bounded_get('https://swarm-diss.eo.esa.int/?'+urllib.parse.urlencode(dict(do='download',file=item['path'])),D/item['name'],10*2**20-listing['bytes'],item['size'])
    members=[]
    with zipfile.ZipFile(D/item['name']) as z:
        assert z.testzip() is None
        for x in z.infolist():
            assert Path(x.filename).name==x.filename
            p=D/x.filename
            with p.open('xb') as f:f.write(z.read(x))
            members.append(dict(path=str(p.relative_to(ROOT)),SHA256=sha(p),CRC32=x.CRC))
    info=bounded_get('https://vires.services/hapi/info?id=SW_OPER_DNSAPOD_2_',D/'HAPI_info.json',65536)
    params={x['name']:x for x in json.loads((D/'HAPI_info.json').read_text())['parameters']}
    assert params['validity_flag']['description']=='0 = nominal data, 1 = anomalous data'
    assert 'GRS80' in params['Latitude_GD']['description']
    assert listing['bytes']+receipt['bytes']+info['bytes']<=10*2**20
    dump(F/'downloads.json',dict(listing=listing,product=receipt,members=members,info=info,total_bytes=listing['bytes']+receipt['bytes']+info['bytes']))
    with cdflib.CDF(next(D.glob('*.cdf'))) as c:
        assert c.globalattsget()['TIME SYSTEM']==['UTC']
        assert c.varattsget('density')['UNITS']=='kg/m3'
        ts=cdf_epoch_utc64(c.varget('time'));obs=c.varget('density');flag=c.varget('validity_flag');la=c.varget('latitude');lo=c.varget('longitude');h=c.varget('altitude')
        dump(F/'CDF_contract.json',dict(global_attributes=c.globalattsget(),variables={k:c.varattsget(k) for k in c.cdf_info().zVariables}))
    assert len(ts)==2880 and np.all(np.diff(ts)==np.timedelta64(30,'s'))
    good,why=quality_mask(obs,flag);dump(F/'quality.json',dict(total=len(ts),valid=int(good.sum()),flags={str(k):int(n) for k,n in zip(*np.unique(flag,return_counts=True))}))
    loc=EarthLocation.from_geodetic(lo*u.deg,la*u.deg,h*u.m,ellipsoid='GRS80');xyz=np.column_stack([x.to_value(u.m) for x in loc.geocentric]);times=Time(ts)
    coords=[]
    for t,r in zip(times,xyz):
        q=DensityQuery.from_itrs(t,r);a=ProvisionalCoordinateAdapter(assumption=A_WGS84).adapt(q);b=ProvisionalCoordinateAdapter(assumption=B_SPHERE,sphere_radius_m=6371000).adapt(q)
        coords.append([(a.model_latitude_deg,lo[len(coords)],a.model_zg_m),(b.model_latitude_deg,lo[len(coords)],b.model_zg_m),(b.model_latitude_deg,lo[len(coords)],a.model_zg_m),(a.model_latitude_deg,lo[len(coords)],b.model_zg_m)])
    values=np.full((4,4,len(ts)),np.nan);rows=[];audit={};providers=[]
    for gi,(group,folder) in enumerate(GROUPS.items()):
        path=ROOT/'experiments'/folder;j=json.loads((path/'data_audit.json').read_text());entries=[e for e in j['files'] if e['file'].startswith('secondary') and any('2021-03-24' in t or '2021-03-25T00:00' in t for t in e['UTC'])]
        expected={e['file']:e.get('SHA256',e.get('sha256')) for e in entries}
        p=HourlyTiegcmObservation([path/e['file'] for e in entries],expected,'2021-03-24','2021-03-25',group);providers.append(p)
        audit[group]=dict(files=entries,frames=len(p.records),shape=list(p.arrays[0][0].shape),DEN='ilev g/cm3 *1000 => kg/m3',ZG='ilev cm *.01 => m',lat=p.lat.tolist(),lon=p.lon.tolist(),ilev=p.ilev.tolist())
        if gi:assert np.array_equal(p.lat,providers[0].lat) and np.array_equal(p.ilev,providers[0].ilev)
        for mi,mapping in enumerate('ABDE'):
            for i,t in enumerate(times):
                if time.perf_counter()-started>1800:raise RuntimeError('Time budget')
                if not good[i]:continue
                r=p.query_native(t,*coords[i][mi],datum=DATUM)
                if r.valid:values[mi,gi,i]=r.rho_kg_m3
                rows.append(dict(sample=i,UTC=str(ts[i]),mapping=mapping,group=group,valid=r.valid,reason=r.reason,rho=r.rho_kg_m3,top_margin_m=r.metadata.get('top_margin_m')))
        print(group,'complete',flush=True)
    dump(F/'inputs.json',audit);table(O/'queries_local.csv',rows)
    common=paired_valid_mask(good,*values.reshape(16,-1));np.savez_compressed(O/'aligned_local.npz',values=values,observed=obs,quality=good,common=common,utc=ts,coords=coords)
    metrics=[];coverage=[];pairs=[]
    regions={'all':np.ones(len(ts),bool),'south':la<=-60,'north':la>=60,'midlow':abs(la)<60}
    for mi,mapping in enumerate('ABDE'):
        for gi,group in enumerate(GROUPS):
            for region,rm in regions.items():
                mask=common&rm;met=compare_density(values[mi,gi,mask],obs[mask]);x=values[mi,gi,mask];y=obs[mask]
                corr=float(np.corrcoef(x,y)[0,1]) if len(x)>1 and np.std(x)>0 and np.std(y)>0 else None
                metrics.append(dict(mapping=mapping,group=group,region=region,Pearson=corr,**met))
            rr=[r for r in rows if r['mapping']==mapping and r['group']==group];reasons={}
            for r in rr:
                if not r['valid']:reasons[r['reason']]=reasons.get(r['reason'],0)+1
            coverage.append(dict(mapping=mapping,group=group,eligible=int(good.sum()),valid=int(np.isfinite(values[mi,gi]).sum()),common=int(common.sum()),reasons=json.dumps(reasons)))
        for a,b in [(0,2),(1,3),(0,1),(2,3)]:
            pairs.append(dict(mapping=mapping,pair=list(GROUPS)[b]+'-'+list(GROUPS)[a],**compare_density(values[mi,b,common],values[mi,a,common])))
    table(O/'metrics.csv',metrics);table(O/'coverage.csv',coverage);table(O/'paired_simulation_differences.csv',pairs)
    dump(F/'runtime.json',dict(wall_s=time.perf_counter()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,queries=len(rows),common=int(common.sum()),model_launches=0))
if __name__=='__main__':main()
