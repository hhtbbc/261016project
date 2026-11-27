"""Exercise the frozen TIE-GCM query kernel on a sealed synthetic hourly background."""
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from itertools import product
from pathlib import Path
import tempfile

from astropy.time import Time
from netCDF4 import Dataset, num2date
import numpy as np

from audit_2021_gfz_revision_v54 import ROOT
from atmosphere.tiegcm_density_provider import DATUM, TiegcmDensityProvider
from runtime.tiegcm_rank_exit import write_once

OUT=ROOT/'experiments/thermosphere_external_evidence_handoff_v55'
ORIGIN=datetime(2020,1,1,tzinfo=timezone.utc)
LAT=np.array([-87.5,-82.5,82.5,87.5])
# Global even periodic grid; retain only two extreme latitude bands in the synthetic fixture.
LON=np.arange(-180.,180.,5.)
BASE=1e-12
K=2e-5


class HourlyFixtureProvider(TiegcmDensityProvider):
    """Read one explicitly synthetic file; reuse the unchanged query and column kernels."""
    def __init__(self,path):
        path=Path(path)
        if path.resolve()!=path or not path.is_relative_to(OUT):
            raise ValueError('Synthetic fixture outside experiment directory')
        self.source='V55 synthetic native hourly fixture'
        self.limit=256
        self.cache=OrderedDict()
        self.closed=False
        self.manifests={}
        self.reads=0
        with Dataset(path) as n:
            if n.getncattr('V55_fixture')!='SYNTHETIC_ONLY':
                raise ValueError('Synthetic fixture marker required')
            self.lat=np.array(n['lat'][:],float)
            self.lon=np.array(n['lon'][:],float)
            for key,unit in [('DEN','g/cm3'),('ZG','cm')]:
                if n[key].dimensions!=('time','ilev','lat','lon') or n[key].units!=unit:
                    raise ValueError('Unexpected schema/units')
            tvar=n['time']
            dates=num2date(tvar[:],tvar.units,only_use_cftime_datetimes=False,
                           only_use_python_datetimes=True)
            tk=[Time(t.replace(tzinfo=timezone.utc)) for t in dates]
        self.epoch=tk[0]
        self.records=[(t,path,i) for i,t in enumerate(tk)]
        self.seconds=np.asarray([(t-self.epoch).sec for t in tk])
        if len(tk)!=2 or not np.allclose(np.diff(self.seconds),3600,atol=1e-8,rtol=0):
            raise ValueError('Incomplete hourly fixture')
        if not np.all(np.diff(self.lat)>0) or not np.all(np.diff(self.lon)>0) or not np.allclose(
                np.diff(np.r_[self.lon,self.lon[0]+360]),5):
            raise ValueError('Invalid grid')


def factor(time_fraction,lat,seam_lon):
    y=lat/90
    x=(seam_lon-175)/5
    t=time_fraction
    return 1.5+.09*x+.16*y+.12*t+.05*x*y+.07*t*y+.03*x*t+.02*x*y*t


def fixture(path,variant='valid'):
    with Dataset(path,'w',format='NETCDF3_CLASSIC') as d:
        d.V55_fixture='SYNTHETIC_ONLY'
        for k,n in [('time',2),('ilev',3),('lev',3),('lat',len(LAT)),('lon',len(LON))]:
            d.createDimension(k,n)
        for k,x,u in [('lat',LAT,'degrees_north'),('lon',LON,'degrees_east'),
                      ('time',[0,3600],'seconds since 2020-01-01 00:00:00')]:
            v=d.createVariable(k,'f8',(k,))
            v[:]=x
            v.units=u
        axis='lev' if variant=='wrong_level' else 'ilev'
        z=d.createVariable('ZG','f8',('time','ilev','lat','lon'),fill_value=-9e33)
        r=d.createVariable('DEN','f8',('time',axis,'lat','lon'),fill_value=-9e33)
        z.units='m' if variant=='wrong_height_unit' else 'cm'
        r.units='kg/m3' if variant=='wrong_density_unit' else 'g/cm3'
        for t,j,i in product(range(2),range(len(LAT)),range(len(LON))):
            heights=np.array([180e3,320e3,490e3])+(t+j+(i%3))*1000
            longitude={0:180.,1:185.}.get(i,175.)
            z[t,:,j,i]=100*heights
            r[t,:,j,i]=(BASE/1000)*factor(t,LAT[j],longitude)*np.exp(-K*(heights-320e3))
        # The paired column opposite the exact query vertex is still required.
        if variant=='zero_weight_missing':
            r[1,1,3,0]=r._FillValue
        if variant=='nonmonotonic':
            z[1,1,3,0]=z[1,0,3,0]
        if variant=='nonpositive':
            r[1,1,3,0]=0
        if variant=='one_column_too_low':
            z[1,2,3,0]=410e5


def native(provider,sec,lat,lon,h):
    return provider.query_native(Time(ORIGIN+timedelta(seconds=sec)),lat,lon,h,datum=DATUM)


def results():
    errors=[]
    rejected=[]
    with tempfile.TemporaryDirectory(dir=OUT,prefix='.synthetic-') as tmp:
        p=Path(tmp)/'analytic.nc'
        fixture(p)
        with HourlyFixtureProvider(p) as provider:
            for t,(j,phi),(i,lam),h in product(range(0,3601,30),
                    enumerate([82.5,86.1,87.5,-86.7,-87.5]),enumerate([175.,179.,-180.,-181.,539.]),[280e3,425e3]):
                sample=f't{t:04d}-j{j}-i{i}-h{int(h)}'
                wrapped=175+(lam-175)%360
                expected=BASE*factor(t/3600,phi,wrapped)*np.exp(-K*(h-320e3))
                actual=native(provider,t,phi,lam,h)
                assert actual.valid and len(actual.metadata['columns'])==8, (sample,actual.reason)
                errors.append(dict(sample_id=sample,seconds=t,relative_error=abs(actual.rho_kg_m3/expected-1),
                                   absolute_error_kg_m3=abs(actual.rho_kg_m3-expected)))
            for label,args,expected in [
                ('outside_time',(-30,85,179,300e3),'TIME_OUTSIDE'),
                ('after_time',(3630,85,179,300e3),'TIME_OUTSIDE'),
                ('pole',(300,90,179,300e3),'POLAR_CAP_UNSUPPORTED'),
                ('below',(300,85,179,50e3),'VERTICAL_OUTSIDE'),
                ('above',(300,85,179,600e3),'VERTICAL_OUTSIDE'),
                ('nan',(300,np.nan,179,300e3),'NONFINITE_QUERY')]:
                answer=native(provider,*args)
                assert not answer.valid and answer.reason==expected
                rejected.append(dict(sample_id=label,reason=answer.reason))
            assert provider.query_external(object()).reason=='EXTERNAL_DATUM_UNVERIFIED'
            rejected.append(dict(sample_id='external',reason='EXTERNAL_DATUM_UNVERIFIED'))
        for variant,expected in [('zero_weight_missing','INVALID_COLUMN'),('nonmonotonic','INVALID_COLUMN'),
                                ('nonpositive','INVALID_COLUMN'),('one_column_too_low','VERTICAL_OUTSIDE')]:
            p=Path(tmp)/(variant+'.nc')
            fixture(p,variant)
            with HourlyFixtureProvider(p) as pr:
                answer=native(pr,0,82.5,175.,425e3)
                assert not answer.valid and answer.reason==expected, (variant,answer)
                rejected.append(dict(sample_id=variant,reason=answer.reason))
        for variant in ('wrong_level','wrong_height_unit','wrong_density_unit'):
            p=Path(tmp)/(variant+'.nc')
            fixture(p,variant)
            try:
                HourlyFixtureProvider(p)
            except ValueError as e:
                rejected.append(dict(sample_id=variant,reason=str(e)))
            else:
                raise AssertionError('Bad schema was admitted')
    err=[r['relative_error'] for r in errors]
    assert max(err)<1e-11
    return dict(state='NUMERICAL_INTERPOLATION_VERIFIED',control_points=len(errors),negative_cases=rejected,
        maximum_relative=float(max(err)),P95_relative=float(np.percentile(err,95)),
        maximum_absolute_kg_m3=float(max(r['absolute_error_kg_m3'] for r in errors)),
        sample_ids_unique=len({r['sample_id'] for r in errors})==len(errors),
        sample_ids=[r['sample_id'] for r in errors],synthetic=True,model_runs=0,
        official_external_datum='EXTERNAL_DATUM_UNVERIFIED')


if __name__=='__main__':
    write_once(OUT/'synthetic_interpolation.json',results())
