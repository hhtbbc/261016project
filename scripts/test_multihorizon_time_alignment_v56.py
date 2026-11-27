"""49-hour native synthetic test with analytical multi-affine/log-vertical truth."""
from collections import OrderedDict
from datetime import timedelta, timezone
from itertools import product
import json
from pathlib import Path

from astropy.time import Time
from netCDF4 import Dataset, num2date
import numpy as np

import build_non_target_horizon_index_v56 as idx
from atmosphere.tiegcm_density_provider import DATUM, TiegcmDensityProvider
from runtime.tiegcm_rank_exit import write_once

CASES=(('MONTH','2020-01-31T00:00:00Z','synthetic_train_fixture'),
       ('LEAP','2020-02-29T00:00:00Z','synthetic_validation_fixture'),
       ('YEAR','2020-12-31T00:00:00Z','synthetic_calendar_fixture'))
LAT=np.arange(-87.5,90.,5.)
LON=np.arange(-180.,180.,5.)
HEIGHTS=(220000.,365000.,480000.)
K=1.55e-5


def amplitude(t,y,x):
    return 1.6+.15*t+.08*y+.12*x+.04*x*y+.03*t*y+.07*t*x+.02*t*x*y


def truth(t,phi,lam,h):
    x=((lam-175)%360)/5
    return 1e-12*amplitude(t/48,phi/90,x)*np.exp(-K*(h-350000))


def fixture(path,origin):
    if path.resolve()!=path or not path.is_relative_to(idx.OUT) or path.exists():
        raise ValueError('Exclusive experiment-local fixture required')
    with Dataset(path,'w',format='NETCDF3_CLASSIC') as nc:
        nc.synthetic_marker='V56_FROZEN_SYNTHETIC_ONLY'
        for k,n in [('time',49),('ilev',4),('lat',len(LAT)),('lon',len(LON))]:
            nc.createDimension(k,n)
        for k,values,unit in [('time',np.arange(49)*3600,'seconds since '+origin.replace('T',' ').removesuffix('Z')),
                              ('lat',LAT,'degrees_north'),('lon',LON,'degrees_east')]:
            x=nc.createVariable(k,'f8',(k,));x[:]=values;x.units=unit
        dims=('time','ilev','lat','lon')
        z=nc.createVariable('ZG','f8',dims);z.units='cm'
        d=nc.createVariable('DEN','f8',dims);d.units='g/cm3'
        indices=np.arange(len(LON))
        x=np.where(indices==0,1.,np.where(indices==1,2.,0.))
        y=LAT[:,None]/90
        for t in range(49):
            shift=(t+indices%3+np.arange(len(LAT))[:,None])/5*1000
            h=np.array([140e3,270e3,390e3,515e3])[:,None,None]+shift
            z[t]=h*100
            d[t]=1e-15*amplitude(t/48,y,x)*np.exp(-K*(h-350000))


class NativeSyntheticHourly(TiegcmDensityProvider):
    """Test-only hourly reader using the frozen V55 query and column kernel."""
    def __init__(self,path):
        if path.resolve()!=path or not path.is_relative_to(idx.OUT):
            raise ValueError('Synthetic hourly fixture required')
        with Dataset(path) as nc:
            if nc.getncattr('synthetic_marker')!='V56_FROZEN_SYNTHETIC_ONLY':
                raise ValueError('Missing synthetic dataset marker')
            for key,units in [('DEN','g/cm3'),('ZG','cm')]:
                if nc[key].dimensions!=('time','ilev','lat','lon') or nc[key].units!=units:
                    raise ValueError('Unexpected native dimension or unit')
            self.lat=np.array(nc['lat'][:])
            self.lon=np.array(nc['lon'][:])
            clock=nc['time']
            frames=[x.replace(tzinfo=timezone.utc) for x in num2date(clock[:],clock.units,
                       only_use_cftime_datetimes=False,only_use_python_datetimes=True)]
        idx.grid([idx.iso(t) for t in frames])
        if len(frames)!=49 or not np.array_equal(self.lat,LAT) or not np.array_equal(self.lon,LON):
            raise ValueError('Unexpected grid extent')
        self.source='V56 synthetic interpolation only'
        self.records=[(Time(x),path,i) for i,x in enumerate(frames)]
        self.epoch=self.records[0][0]
        self.seconds=np.array([(x[0]-self.epoch).sec for x in self.records])
        self.cache=OrderedDict();self.limit=256;self.closed=False;self.manifests={};self.reads=0
        self.frames=[idx.iso(x) for x in frames]


def main():
    protocol=idx.pin(idx.V37)
    core=protocol['V20_core']
    rows=[]; outputs=[]; rejected=[]; interval=[]; sources=[]
    for name,origin,split in CASES:
        path=idx.OUT/f'synthetic_{name}.nc'
        fixture(path,origin)
        digest=idx.sha(path)
        start=idx.utc(origin)
        with NativeSyntheticHourly(path) as p:
            interval.append((split,p.frames[0],p.frames[-1]))
            cutoffs=[idx.iso(start+timedelta(hours=n+h)) for n in (0,24) for h in core['cutoffs']]
            originals=idx.build(p.frames,cutoffs,name,split,digest,core)
            rows.extend(originals)
            sources.append(dict(source=name,split=split,start=origin,stop=p.frames[-1],
                                frames=len(p.frames),file=path.name,sha256=digest))
            for row in originals:
                target=idx.utc(row['target_UTC'])
                for off,phi,lam,h in product((-30,0,30),(-87.5,-84.2,85.,87.5),(175.5,179.9,-180.,-181.),HEIGHTS):
                    instant=target+timedelta(seconds=off)
                    if instant>idx.utc(p.frames[-1]):
                        continue
                    result=p.query_native(Time(instant),phi,lam,h,datum=DATUM)
                    assert result.valid and len(result.metadata['columns'])==8
                    delta=(instant-start).total_seconds()/3600
                    answer=truth(delta,phi,lam,h)
                    outputs.append(dict(control_id=idx.identity((row['sample_id'],off,phi,lam,h)),
                        sample_id=row['sample_id'],source=name,cutoff_UTC=row['cutoff_UTC'],
                        lead=row['horizon_hours'],UTC=idx.iso(instant),lat=phi,lon=lam,altitude_m=h,
                        actual_kg_m3=result.rho_kg_m3,abs_error_kg_m3=abs(result.rho_kg_m3-answer),
                        relative_error=abs(result.rho_kg_m3/answer-1)))
            for label,t,lat,h,reason in [('before',start-timedelta(seconds=30),85,350e3,'TIME_OUTSIDE'),
                ('after',start+timedelta(hours=49),85,350e3,'TIME_OUTSIDE'),
                ('polar',start,90,350e3,'POLAR_CAP_UNSUPPORTED'),
                ('low',start,85,50e3,'VERTICAL_OUTSIDE'),
                ('high',start,85,620e3,'VERTICAL_OUTSIDE')]:
                ans=p.query_native(Time(t),lat,179.,h,datum=DATUM)
                assert not ans.valid and ans.reason==reason
                rejected.append(dict(id=name+'_'+label,reason=ans.reason))
            assert p.query_external(object()).reason=='EXTERNAL_DATUM_UNVERIFIED'
            rejected.append(dict(id=name+'_external',reason='EXTERNAL_DATUM_UNVERIFIED'))
    idx.check_split(interval)
    assert len(rows)==len({r['sample_id'] for r in rows})
    assert len(outputs)==len({r['control_id'] for r in outputs})
    assert max(r['relative_error'] for r in outputs)<1e-11
    idx.output('horizon_index.csv',rows)
    idx.output('synthetic_query_controls.csv',outputs)
    tracks,summary=idx.metadata_index(protocol)
    idx.output('swarm_metadata_time_index.csv',tracks)
    groups=[]
    for key in ('lead','altitude_m','cutoff_hour'):
        for value in sorted({int(r['cutoff_UTC'][11:13]) if key=='cutoff_hour' else r[key] for r in outputs}):
            a=[r for r in outputs if (int(r['cutoff_UTC'][11:13]) if key=='cutoff_hour' else r[key])==value]
            groups.append(dict(group=key,key=value,n=len(a),max_relative=max(r['relative_error'] for r in a),
               max_absolute_kg_m3=max(r['abs_error_kg_m3'] for r in a),
               P95_relative=float(np.percentile([r['relative_error'] for r in a],95))))
    idx.output('interpolation_error_groups.csv',groups)
    write_once(idx.OUT/'hourly_results.json',dict(sources=sources,endpoints=len(rows),controls=len(outputs),
        maximum_relative=max(r['relative_error'] for r in outputs),
        maximum_absolute_kg_m3=max(r['abs_error_kg_m3'] for r in outputs),
        P95_relative=float(np.percentile([r['relative_error'] for r in outputs],95)),
        rejected=rejected,metadata_index_status='OBSERVATION_METADATA_TIME_INDEX_VERIFIED',
        metadata_rows=len(tracks),metadata_unique=len({r['sample_id'] for r in tracks}),metadata_groups=summary))


if __name__=='__main__':
    main()
