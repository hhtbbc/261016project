"""Read-only hourly historical adapter; inherited eight-column query unchanged."""
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from pathlib import Path
import hashlib
import numpy as np
from astropy.time import Time
from netCDF4 import Dataset,num2date
from .tiegcm_density_provider import TiegcmDensityProvider,ROOT

class HourlyTiegcmObservation(TiegcmDensityProvider):
    def __init__(self, files, expected_sha, start, stop, source):
        self.source=source;self.limit=0;self.cache=OrderedDict();self.closed=False
        self.manifests={};self.records=[];self.reads=0;self.arrays=[]
        for path in sorted(map(Path,files)):
            path=path.resolve();path.relative_to(ROOT)
            if hashlib.sha256(path.read_bytes()).hexdigest()!=expected_sha[path.name]:
                raise ValueError('Source SHA mismatch')
            with Dataset(path) as n:
                lat=np.asarray(n['lat'][:]);lon=np.asarray(n['lon'][:])
                if not hasattr(self,'lat'):self.lat,self.lon=lat,lon;self.ilev=np.asarray(n['ilev'][:])
                elif not all(np.array_equal(a,b) for a,b in [(lat,self.lat),(lon,self.lon),(n['ilev'][:],self.ilev)]):raise ValueError('Grid mismatch')
                for name,unit in [('DEN','g/cm3'),('ZG','cm')]:
                    if n[name].dimensions!=('time','ilev','lat','lon') or n[name].units!=unit:raise ValueError('Schema mismatch')
                for i,(year,mt) in enumerate(zip(n['year'][:],n['mtime'][:])):
                    day,h,m=map(int,mt);dt=datetime(int(year),1,1,tzinfo=timezone.utc)+timedelta(days=day-1,hours=h,minutes=m)
                    t=Time(dt)
                    cf=num2date(n['time'][i],n['time'].units,only_use_cftime_datetimes=False)
                    if abs((Time(cf)-t).sec)>1e-6:raise ValueError('Calendar mismatch')
                    if Time(start)<=t<=Time(stop):
                        z=np.ma.filled(n['ZG'][i],np.nan).astype(float)*.01
                        r=np.ma.filled(n['DEN'][i],np.nan).astype(float)*1000
                        self.records.append((t,path,i));self.arrays.append((z,r))
        order=sorted(range(len(self.records)),key=lambda i:self.records[i][0].jd)
        self.records=[self.records[i] for i in order];self.arrays=[self.arrays[i] for i in order]
        if len(self.records)<2:raise ValueError('Missing frames')
        self.epoch=self.records[0][0];self.seconds=np.array([(r[0]-self.epoch).sec for r in self.records])
        if not np.allclose(np.diff(self.seconds),3600,atol=1e-6,rtol=0):raise ValueError('Missing/duplicate hourly frames')
        if self.records[0][0]!=Time(start) or self.records[-1][0]!=Time(stop):raise ValueError('Incomplete endpoints')
        if np.any(np.diff(self.lat)<=0) or not np.allclose(np.diff(np.r_[self.lon,self.lon[0]+360]),5):raise ValueError('Grid invalid')
    def _column(self,k,j,i):
        z,r=self.arrays[k];return z[:,j,i],r[:,j,i]
