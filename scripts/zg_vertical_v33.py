"""Frozen historical sample, read-only native ZG gradients and local derivative audit."""
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
from collections import OrderedDict

import numpy as np
from astropy.time import Time
from netCDF4 import Dataset, num2date

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from atmosphere.causal_observation_operator import map_a_queries
from atmosphere.provisional_coordinate_adapter import (
    A_WGS84, ProvisionalCoordinateAdapter, diagnose_provisional_interpolation,
)
from atmosphere.tiegcm_density_provider import TiegcmDensityProvider
from runtime.tiegcm_rank_exit import digest as sha, write_once

EXP = ROOT/'experiments'
V30 = EXP/'thermosphere_autumn_density_validation_v30'
V31 = EXP/'thermosphere_spring_autumn_failure_mechanism_v31'
V32 = EXP/'thermosphere_coefficient_stability_zg_audit_v32'
OUT = EXP/'thermosphere_zg_vertical_sensitivity_v33'
HEAD = 'f50b40b8314ac19bbfcec779d566cb31c1250743'
IDENTITY = 'PROVISIONAL / HINDCAST / EXTERNAL_DATUM_UNVERIFIED'
INDICES = list(range(0,360,6))
SCHEMA = ('time','ilev','lat','lon')
HEIGHT_EDGES_M = (400000,450000,500000)
RTOL = 1e-13


def require(ok,message):
    if not ok:
        raise ValueError(message)


def load(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def table(path,data):
    with path.open('x',newline='') as stream:
        fields=list(dict.fromkeys(k for row in data for k in row))
        writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n')
        writer.writeheader()
        writer.writerows(data)


def pin(path,wanted):
    require(path.resolve(strict=True)==path and sha(path)==wanted,'Unexpected SHA or path: '+path.name)


def git_pin(path):
    data=subprocess.check_output(['git','show',f'{HEAD}:{path.relative_to(ROOT)}'])
    digest=hashlib.sha256(data).hexdigest()
    pin(path,digest)
    return digest


def sample_identity(t):
    return hashlib.sha256(np.asarray(t,dtype='datetime64[ns]').astype('<i8').tobytes()).hexdigest()


def dates(year,hour):
    require(year in (2021,2022) and hour in (6,18),'Only registered autumn development windows')
    stop=f'{year}-09-23T{hour:02d}:00:00'
    start=f'{year}-09-23T{hour-3:02d}:00:00'
    return start,stop


def freeze():
    require(ROOT==Path.cwd().resolve() and OUT.resolve()==OUT,'Wrong project location')
    OUT.mkdir()
    pins={}
    for folder in (V30,V31,V32):
        manifest=folder/'publication_SHA256.json'
        pins[str(manifest.relative_to(ROOT))]=git_pin(manifest)
        for name,digest in load(manifest).items():
            pin(ROOT/name,digest)
            pins[name]=digest
    expected=load(V32/'zg_review_receipt.json')['files_rechecked']
    for name,digest in expected.items():
        pin(ROOT/name,digest)
        pins[name]=digest
    evidence=[]
    for entry in rows(V32/'zg_evidence_matrix.csv'):
        pin(ROOT/entry['source_path'],entry['source_SHA256'])
        evidence.append(dict(entry,V33_update='Verified cached source; no new independent datum evidence'))
    table(OUT/'external_evidence_update.csv',evidence)
    protected_roles=load(V32/'data_roles.json')
    source=load(V30/'source_manifest.json')['years']
    histories=load(V32/'history_freeze.json')['history_caches']
    manifest=[]
    for year in (2021,2022):
        info=source[str(year)]
        require(any(r['date']==f'{year}-09-23' and r['role']=='DEVELOPMENT_SOURCE' for r in protected_roles['dates']),
                'Unseen target prohibited')
        cdf=info['CDF']
        pin(ROOT/cdf['path'],cdf['SHA256'])
        pins[cdf['path']]=cdf['SHA256']
        for h in (6,18):
            start,stop=dates(year,h)
            hist=next(x for x in histories if x['date']==f'{year}-09-23' and x['cutoff']==h)
            path=ROOT/hist['path']
            pin(path,hist['SHA256']);pins[hist['path']]=hist['SHA256']
            with np.load(path,allow_pickle=False) as data:
                times=data['utc']
                require(np.array_equal(times,np.datetime64(start)+np.arange(360)*np.timedelta64(30,'s'))
                        and data['quality'].all(),'History grid or quality changed')
                chosen=times[INDICES]
            volumes=[r for r in info['target_models'] if r['first_UTC']<=stop+'Z' and r['last_UTC']>=start+'Z']
            require(volumes,'No original model volume for history')
            for q in volumes:
                pin(ROOT/q['path'],q['SHA256']);pins[q['path']]=q['SHA256']
            manifest.append(dict(year=year,cutoff=h,start_UTC=start,stop_UTC=stop,
                history_path=hist['path'],history_SHA256=hist['SHA256'],trajectory_CDF=cdf,
                source_run_id=info['run_id'],model_volumes=volumes,
                indices=INDICES,selected_utc_SHA256=sample_identity(chosen),
                utc=[str(t)+'Z' for t in chosen]))
    write_once(OUT/'sample_freeze.json',dict(identity=IDENTITY,selection='zero-based 0:360:6 per window',
        windows=manifest,samples=240,observed_density_read=False,assumption=A_WGS84,
        height_offset_m=0,native_ZG_unit='cm',native_DEN_unit='g/cm3',level='ilev',
        numeric_steps='min(1 m, nearest of all 16 active bracket bounds/8), then halve twice',
        height_strata_m=list(HEIGHT_EDGES_M),physical_offset_status='FIXED_OFFSET_NOT_ADMITTED',
        independent_height_bound=None,source_SHA256=pins,code_SHA256=sha(Path(__file__))))


def validate_schema(ds):
    for key,unit in [('ZG','cm'),('DEN','g/cm3')]:
        var=ds[key]
        require(var.dimensions==SCHEMA and var.units==unit,'Wrong ilev schema or unit: '+key)
    require(np.all(np.diff(ds['ilev'][:])>0),'Invalid interface coordinate')


class HistoricalColumns(TiegcmDensityProvider):
    """Hourly index only, using unchanged native query and bounded column cache."""
    def __init__(self,spec):
        self.source=spec['source_run_id']
        self.limit=512
        self.cache=OrderedDict()
        self.closed=False
        self.records=[]
        self.reads=0
        self.manifests={}
        start,stop=Time(spec['start_UTC']),Time(spec['stop_UTC'])
        for item in spec['model_volumes']:
            path=ROOT/item['path']
            pin(path,item['SHA256'])
            with Dataset(path,'r') as ds:
                validate_schema(ds)
                lat,lon=np.asarray(ds['lat'][:],float),np.asarray(ds['lon'][:],float)
                if hasattr(self,'lat'):
                    require(np.array_equal(self.lat,lat) and np.array_equal(self.lon,lon),'Grid drift')
                else:
                    self.lat,self.lon=lat,lon
                for i,(y,mt) in enumerate(zip(ds['year'][:],ds['mtime'][:])):
                    date=datetime(int(y),1,1,tzinfo=timezone.utc)+timedelta(days=int(mt[0])-1,
                                                                          hours=int(mt[1]),minutes=int(mt[2]))
                    t=Time(date)
                    if start<=t<=stop:
                        cf=num2date(ds['time'][i],ds['time'].units,only_use_cftime_datetimes=False)
                        require(abs((Time(cf)-t).sec)<1e-6,'Native/CF calendar mismatch')
                        self.records.append((t,path,i))
        self.records.sort(key=lambda record:record[0].jd)
        self.epoch=self.records[0][0]
        self.seconds=np.array([(r[0]-self.epoch).sec for r in self.records])
        require(len(self.records)==4 and self.epoch==start and self.records[-1][0]==stop
                and np.allclose(np.diff(self.seconds),3600,atol=1e-6,rtol=0),'Wrong history hourly grid')
        require(np.all(np.diff(self.lat)>0) and np.allclose(np.diff(np.r_[self.lon,self.lon[0]+360]),5),
                'Invalid horizontal grid')


def weight_vector(w):
    a=np.array([w['time'],w['latitude'],w['longitude']])
    require(np.isfinite(a).all() and ((a>=0)&(a<=1)).all(),'Invalid time/horizontal weights')
    w=np.array([(i if k else 1-i)*(j if p else 1-j)*(u if q else 1-u)
                for k in (0,1) for p in (0,1) for q in (0,1) for i,j,u in [a]])
    require(np.isclose(w.sum(),1,rtol=0,atol=8*np.finfo(float).eps),'Weight sum failure')
    return w


def section(z,r,h):
    require(z.shape==r.shape and z.ndim==1 and z.size>=2 and np.isfinite(z).all()
            and np.isfinite(r).all() and (r>0).all() and (np.diff(z)>0).all(),'Invalid raw column')
    require(z[0]<=h<=z[-1],'Native vertical query outside interval')
    k=min(int(np.searchsorted(z,h,side='right'))-1,len(z)-2)
    lo,hi=z[k:k+2]
    logr=np.log(r[k:k+2])
    slope=float((logr[1]-logr[0])/(hi-lo))
    return dict(bracket=k,lower_m=float(lo),upper_m=float(hi),
                bottom_m=float(z[0]),top_m=float(z[-1]),dlnrho_dh_per_m=slope,
                H_m=-1/slope if slope<0 else None,sign='negative' if slope<0 else 'nonnegative',
                log_rho=float(np.interp(h,z,np.log(r))))


def eight(col,w):
    require(len(col)==8 and len(w)==8,'Stencil must contain eight columns')
    values=np.exp([row['log_rho'] for row in col])
    total=float(w@values)
    slope=float((w*values)@np.array([row['dlnrho_dh_per_m'] for row in col])/total)
    return total,slope


def math_steps(h,cols):
    safe=min(min(h-c['lower_m'],c['upper_m']-h) for c in cols)
    if safe<=0:
        return []
    step=min(1.0,safe/8)
    return [step,step/2,step/4] if step/4>=1e-5 else []


def diagnostic():
    start_clock=time.perf_counter()
    f=load(OUT/'sample_freeze.json')
    require(f['code_SHA256']==sha(Path(__file__)) and f['height_offset_m']==0,'Frozen plan mismatch')
    all_queries=[];column_rows=[]
    for spec in f['windows']:
        year,hour=spec['year'],spec['cutoff']
        pin(ROOT/spec['history_path'],spec['history_SHA256'])
        verify_selection=spec['indices']==INDICES
        require(verify_selection,'Frozen fixed indices changed')
        with np.load(ROOT/spec['history_path'],allow_pickle=False) as a:
            utc,lat,lon,alt,ref=[a[key][INDICES] for key in ('utc','latitude','longitude','altitude','raw')]
        require(sample_identity(utc)==spec['selected_utc_SHA256'],'Query sample identity mismatch')
        q=map_a_queries(utc,lat,lon,alt)
        adapter=ProvisionalCoordinateAdapter(assumption=A_WGS84)
        with HistoricalColumns(spec) as provider:
            lookup={(p.name,r):k for k,(_,p,r) in enumerate(provider.records)}
            for j,query in enumerate(q):
                info=dict(year=year,cutoff=hour,index=INDICES[j],UTC=str(utc[j])+'Z',
                    lat_region=('low','mid','high')[int(np.digitize(abs(lat[j]),[30,60]))],
                    height_stratum=int(np.digitize(alt[j],HEIGHT_EDGES_M)))
                p=adapter.query_provisional(provider,query)
                if not p.native_result.valid:
                    all_queries.append(dict(**info,status='INVALID',reason=p.native_result.reason))
                    continue
                n=p.native_result
                hd=p.coordinates.model_zg_m
                diag=diagnose_provisional_interpolation(provider,p)
                w=weight_vector(n.metadata['weights'])
                cols=[]
                for k,meta in enumerate(n.metadata['columns']):
                    z,r=provider._column(lookup[(meta['file'],meta['record'])],meta['lat_index'],meta['lon_index'])
                    v=section(z,r,hd)
                    require(v['bracket']==n.metadata['vertical_brackets'][k]['lower_index'],'Native bracket mismatch')
                    cols.append(v)
                    column_rows.append(dict(**info,ordinal=k,**meta,weight=float(w[k]),**v))
                value,derivative=eight(cols,w)
                require(np.isclose(value,n.rho_kg_m3,rtol=RTOL,atol=0)
                        and np.isclose(value,ref[j],rtol=RTOL,atol=0)
                        and np.isclose(derivative,diag['dlnrho_dh_per_m'],rtol=RTOL,atol=0),'Frozen Map-A or diagnostic drift')
                low=max(v['bottom_m'] for v in cols)
                high=min(v['top_m'] for v in cols)
                slopes=[v['dlnrho_dh_per_m'] for v in cols]
                spacings=[v['upper_m']-v['lower_m'] for v in cols]
                steps=math_steps(hd,cols)
                require(np.isclose(low,hd-diag['bottom_margin_m']) and np.isclose(high,hd+diag['top_margin_m']),
                        'Common interval mismatch')
                all_queries.append(dict(**info,status='OK',reason='',height_m=hd,
                    baseline_kg_m3=value,frozen_Map_A_kg_m3=float(ref[j]),
                    dlnrho_dh_per_m=derivative,H_m=-1/derivative if derivative<0 else None,
                    sign='negative' if derivative<0 else 'nonnegative',
                    common_low_m=low,common_high_m=high,bottom_margin_m=hd-low,top_margin_m=high-hd,
                    spacing_min_m=min(spacings),spacing_max_m=max(spacings),
                    slope_min=min(slopes),slope_max=max(slopes),zero_weight_columns=int((w==0).sum()),
                    fd_applicable=bool(steps),step1_m=steps[0] if steps else None,
                    nearest_bracket_boundary_m=min(min(hd-c['lower_m'],c['upper_m']-hd) for c in cols),
                    **{f'weight_{k}':float(x) for k,x in n.metadata['weights'].items()}))
    require(len(all_queries)==240,'Inconsistent frozen sample count')
    table(OUT/'query_gradients.csv',all_queries)
    table(OUT/'native_column_brackets.csv',column_rows)
    usable=[r for r in all_queries if r['status']=='OK']
    groups=[('all','all',all_queries)]
    for key in ('year','cutoff','lat_region','height_stratum'):
        groups += [(key,str(v),[r for r in all_queries if r[key]==v])
                   for v in sorted({r[key] for r in all_queries})]
    for y in (2021,2022):
        for h in (6,18):
            groups.append(('year_cutoff',f'{y}_{h}',[r for r in all_queries if r['year']==y and r['cutoff']==h]))
    stats=[]
    for axis,level,rs in groups:
        ok=[x for x in rs if x['status']=='OK']
        stats.append(dict(axis=axis,group=level,N=len(rs),valid=len(ok),failed=len(rs)-len(ok),
            N_ge_30=len(ok)>=30,coverage=len(ok)/len(rs),
            **{key+'_'+stat:float(fn([r[key] for r in ok if r[key] is not None])) if any(r[key] is not None for r in ok) else None
               for key in ('dlnrho_dh_per_m','H_m','top_margin_m','bottom_margin_m')
               for stat,fn in [('min',min),('median',np.median),('max',max)]}))
    table(OUT/'gradient_strata.csv',stats)
    write_once(OUT/'main_receipt.json',dict(samples=len(all_queries),valid=len(usable),columns=len(column_rows),
        code_SHA256=sha(Path(__file__)),frozen_plan_SHA256=sha(OUT/'sample_freeze.json'),
        wall_s=time.perf_counter()-start_clock,CPU_s=time.process_time(),
        peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        no_GPU=True,no_integrations=True,no_observed_density_read=True,formal_offset_trials=0))


if __name__=='__main__':
    {'freeze':freeze,'diagnostic':diagnostic}[sys.argv[1]]()
