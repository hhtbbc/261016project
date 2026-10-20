"""Conservative native TIE-GCM ZG queries; external datum deliberately gated."""
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timedelta, timezone
import json
import hashlib
import numpy as np
from astropy.time import Time
from netCDF4 import Dataset, num2date
from .coverage import stencil_coverage

DATUM = 'TIEGCM_NATIVE_ZG'
ROOT = Path(__file__).resolve().parents[2]

@dataclass(frozen=True)
class DensityResult:
    valid: bool
    rho_kg_m3: float | None = None
    reason: str = ''
    metadata: dict = field(default_factory=dict)

class TiegcmDensityProvider:
    """Index once, bounded column LRU, context-managed reads (no retained handles).

    Vertical log-density, then bilinear density, then linear density in time.
    All eight columns are required even when an interpolation weight is zero.
    Not thread safe. Paths must resolve within the project root.
    """
    def __init__(self, files, source, start='2023-03-21T00:00:00',
                 stop='2023-03-23T00:10:00', cache_columns=256):
        if cache_columns < 0: raise ValueError('cache_columns must be nonnegative')
        self.source=source; self.limit=cache_columns; self.cache=OrderedDict(); self.closed=False
        self.records=[]; self.reads=0; self.manifests={}
        a,b=Time(start,scale='utc'),Time(stop,scale='utc')
        for item in sorted(map(Path,files)):
            p=item.resolve(); p.relative_to(ROOT)
            manifest=p.parent/'data_audit.json'
            if manifest.exists() and str(manifest) not in self.manifests:
                raw=manifest.read_bytes(); entries=json.loads(raw)['files']
                self.manifests[str(manifest)]={'path':str(manifest.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest(),'files':{e['file']:e['sha256'] for e in entries}}
            with Dataset(p) as n:
                lat=np.asarray(n['lat'][:],float); lon=np.asarray(n['lon'][:],float)
                if not hasattr(self,'lat'): self.lat,self.lon=lat,lon
                elif not (np.array_equal(lat,self.lat) and np.array_equal(lon,self.lon)): raise ValueError('Grid mismatch')
                for name,unit in [('DEN','g/cm3'),('ZG','cm')]:
                    v=n[name]
                    if v.dimensions!=('time','ilev','lat','lon') or v.units!=unit: raise ValueError('Unexpected schema/units: '+name)
                for i,(year,mt) in enumerate(zip(n['year'][:],n['mtime'][:])):
                    day,hour,minute=map(int,mt)
                    dt=datetime(int(year),1,1,tzinfo=timezone.utc)+timedelta(days=day-1,hours=hour,minutes=minute)
                    t=Time(dt)
                    if 'time' in n.variables:
                        cf=num2date(n['time'][i],n['time'].units,only_use_cftime_datetimes=False,only_use_python_datetimes=True)
                        if abs((Time(cf)-t).sec)>1e-6: raise ValueError('CF/model calendar mismatch')
                    if a<=t<=b: self.records.append((t,p,i))
        self.records.sort(key=lambda r:r[0].jd)
        if len(self.records)<2: raise ValueError('Need two time frames')
        self.epoch=self.records[0][0]; self.seconds=np.array([(r[0]-self.epoch).sec for r in self.records])
        if np.any(np.diff(self.seconds)<=0) or not np.allclose(np.diff(self.seconds),600,atol=1e-6,rtol=0): raise ValueError('Duplicate/missing/non-ten-minute frames')
        if len(self.lat)<2 or len(self.lon)<2 or np.any(np.diff(self.lat)<=0) or np.any(np.diff(self.lon)<=0): raise ValueError('Invalid grid')
        if not np.allclose(np.diff(np.r_[self.lon,self.lon[0]+360]),np.diff(self.lon)[0]): raise ValueError('Nonperiodic longitude grid')

    def _column(self,k,j,i):
        key=(k,j,i)
        if key in self.cache:
            self.cache.move_to_end(key); return self.cache[key]
        _,path,record=self.records[k]; out=[]
        with Dataset(path) as n:
            n.set_auto_mask(False)
            for name,scale in [('ZG',.01),('DEN',1000.)]:
                v=n[name]; raw=np.asarray(v[record,:,j,i]); bad=~np.isfinite(raw)|(np.abs(raw)>1e30)
                for marker in ['_FillValue','missing_value']:
                    if hasattr(v,marker): bad |= raw==np.asarray(getattr(v,marker),dtype=raw.dtype)
                x=raw.astype(float)*scale; x[bad]=np.nan; x.flags.writeable=False; out.append(x)
        self.reads+=1
        if self.limit:
            self.cache[key]=tuple(out)
            while len(self.cache)>self.limit:self.cache.popitem(last=False)
        return tuple(out)

    def query_native(self, utc, latitude_deg, longitude_deg, height_m, *, datum, vertical='log'):
        if self.closed: raise RuntimeError('Provider closed')
        meta={'source':self.source,'datum':datum,'algorithm':'vertical log; horizontal density bilinear; time density linear', 'quality':'hindcast; spin-up not demonstrated converged', 'manifests':[{'path':m['path'],'sha256':m['sha256'],'hashes_are_manifest_claims':True} for m in self.manifests.values()]}
        def fail(reason):return DensityResult(False,reason=reason,metadata=meta)
        if datum!=DATUM:return fail('DATUM_UNVERIFIED')
        if vertical not in ('log','linear'):raise ValueError('Unknown vertical interpolation')
        t=utc if isinstance(utc,Time) else Time(utc,scale='utc')
        if not t.isscalar:raise ValueError('Scalar UTC required')
        x=float((t.utc-self.epoch).sec); lat,lon,h=map(float,(latitude_deg,longitude_deg,height_m))
        if not np.isfinite([x,lat,lon,h]).all():return fail('NONFINITE_QUERY')
        if x<self.seconds[0] or x>self.seconds[-1]:return fail('TIME_OUTSIDE')
        if lat<self.lat[0] or lat>self.lat[-1]:return fail('POLAR_CAP_UNSUPPORTED')
        k=int(np.clip(np.searchsorted(self.seconds,x,side='right')-1,0,len(self.seconds)-2))
        j=int(np.clip(np.searchsorted(self.lat,lat,side='right')-1,0,len(self.lat)-2))
        lon=(lon-self.lon[0])%360+self.lon[0]
        i=int(np.searchsorted(self.lon,lon,side='right')-1); ii=(i+1)%len(self.lon)
        l1=self.lon[ii]+(360 if ii==0 else 0)
        wt=(x-self.seconds[k])/(self.seconds[k+1]-self.seconds[k]); wy=(lat-self.lat[j])/(self.lat[j+1]-self.lat[j]); wx=(lon-self.lon[i])/(l1-self.lon[i])
        keys=[(kk,jj,iii) for kk in [k,k+1] for jj in [j,j+1] for iii in [i,ii]]
        cols=[self._column(*key) for key in keys]; z=np.array([c[0] for c in cols]); rho=np.array([c[1] for c in cols])
        gate=stencil_coverage([h],z[None],rho[None],[True])
        meta.update(time_utc=[self.records[kk][0].utc.isot for kk in [k,k+1]], weights={'time':wt,'latitude':wy,'longitude':wx}, columns=[{'file':self.records[kk][1].name,'record':self.records[kk][2],'lat_index':jj,'lon_index':iii} for kk,jj,iii in keys])
        if gate['bad_columns']:
            meta['invalid_column_indices']=[i for i,(zz,rr) in enumerate(cols) if not (np.isfinite(zz).all() and np.isfinite(rr).all() and (rr>0).all() and (np.diff(zz)>0).all())]
            return fail('INVALID_COLUMN')
        meta['top_margin_m']=float(np.min(z[:,-1]-h))
        if not gate['valid'][0]:return fail('VERTICAL_OUTSIDE')
        brackets=[int(np.clip(np.searchsorted(zz,h,side='right')-1,0,len(zz)-2)) for zz in z]
        vals=np.array([np.exp(np.interp(h,zz,np.log(rr))) if vertical=='log' else np.interp(h,zz,rr) for zz,rr in cols]).reshape(2,2,2)
        weights=np.array([1-wt,wt])[:,None,None]*np.array([1-wy,wy])[None,:,None]*np.array([1-wx,wx])[None,None,:]
        meta.update(vertical_brackets=[{'lower_index':b,'height_m':[float(zz[b]),float(zz[b+1])],'weight':float((h-zz[b])/(zz[b+1]-zz[b]))} for b,zz in zip(brackets,z)],vertical=vertical,all_log_alternative_kg_m3=float(np.exp(np.sum(weights*np.log(vals)))))
        return DensityResult(True,float(np.sum(weights*vals)),metadata=meta)

    def query_external(self,query):
        return DensityResult(False,reason='EXTERNAL_DATUM_UNVERIFIED',metadata={'source':self.source,'input':'ITRS/WGS84','required':DATUM})

    def density_kg_m3(self,query):
        raise ValueError('EXTERNAL_DATUM_UNVERIFIED: use explicitly native coordinates')

    def close(self):self.cache.clear(); self.closed=True
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
