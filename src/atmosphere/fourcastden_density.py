"""Hourly AI density on an explicitly declared model-native height datum.

No WGS84 registration is implied; no future reference ZG enters reconstruction.
"""
from pathlib import Path
import hashlib
import numpy as np
from astropy.time import Time
from .tiegcm_density_provider import DensityResult, DATUM
from fourcastden.logden import decode_physical

ROOT = Path(__file__).resolve().parents[2]
HEIGHT_SOURCE = 'AI_RECONSTRUCTED_NATIVE_ZG'


def reconstruct_native_zg(tn, den, z, tlbc, lat, ilev):
    """Invert dt.F interface molecular mass, then apply addiag.F:calczg.

    Inputs retain author units (K, g/cm3, cm); output is metres. This enforces
    a diagnostic thermodynamic consistency assumption on the independently
    predicted fields; it is not a proof of future height accuracy.
    Invalid inferred masses are masked, never clipped or substituted.
    """
    tn, den, z, tlbc = [np.asarray(v, dtype=np.float64) for v in (tn, den, z, tlbc)]
    lat, ilev = np.asarray(lat, float), np.asarray(ilev, float)
    if z.ndim != 4 or z.shape != den.shape or z.shape[1] != 29:
        raise ValueError('Expected (time,29,lat,lon) native Z/DEN')
    if tn.shape != (z.shape[0], 28, *z.shape[2:]) or tlbc.shape != (z.shape[0], 1, *z.shape[2:]):
        raise ValueError('Expected 28 TN and one TLBC channel')
    if lat.shape != (z.shape[2],) or ilev.shape != (29,) or not np.allclose(np.diff(ilev), .5, atol=1e-12, rtol=0):
        raise ValueError('Verified 5-degree/half-scale-height vertical contract required')
    if not all(np.isfinite(a).all() for a in (tn, den, z, tlbc, lat, ilev)) or np.any(den <= 0) or np.any(tn <= 0) or np.any(tlbc <= 0):
        raise ValueError('Nonphysical input; no correction permitted')
    t_interface = np.concatenate((tlbc, .5*(tn[:, :-1]+tn[:, 1:]), tn[:, -1:]), axis=1)
    pressure = 5e-4*np.exp(-ilev)  # dyn/cm²; dt.F deliberately repeats top pressure
    pressure[-1] = pressure[-2]
    mu_interface = den*8.314e7*t_interface/pressure[None, :, None, None]
    mu_mid = np.empty_like(mu_interface)
    mu_mid[:, 0] = .5*(mu_interface[:, 0]+mu_interface[:, 1])
    for k in range(1, 29):
        mu_mid[:, k] = 2*mu_interface[:, k]-mu_mid[:, k-1]
    # Source uses O/O2/N2/He masses 16/32/28/4; no fitting to test errors.
    valid = ((mu_mid >= 4) & (mu_mid <= 32)).all(axis=1) & (np.diff(z, axis=1) > 0).all(axis=1)
    c2 = np.cos(2*1.74533e-2*lat)[None, :, None]
    g0 = 980.616*(1-.0026373*c2)
    radius = 2*g0/(3.085462e-6+2.27e-9*c2)
    gravity = g0*(radius/(radius+.5*(z[:, 0]+z[:, 1])))**2
    zg = np.empty_like(z); zg[:, 0] = z[:, 0]
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        for k in range(1, 28):
            zg[:, k] = zg[:, k-1] + 1.38e-16*.5*tn[:, k-1]*6.023e23/(mu_mid[:, k-1]*gravity)
            gravity = g0*(radius/(radius+.5*(zg[:, k]+z[:, k+1])))**2
        zg[:, -1] = 2*zg[:, -2]-zg[:, -3]
    valid &= np.isfinite(zg).all(axis=1) & (np.diff(zg, axis=1)>0).all(axis=1)
    return zg*.01, valid, mu_mid


class FourCastDENDensity:
    """Log-density vertically, density bilinear horizontally, density linear in UTC.

    Every one of the eight columns must be valid, including zero-weight corners.
    Formal Earth-fixed DensityProvider calls deliberately remain blocked.
    """
    def __init__(self, epochs, lat, lon, density_native, height_m, *, source,
                 height_source, valid_columns=None, provenance=None):
        self.epochs = Time(epochs, scale='utc')
        self.lat, self.lon = np.asarray(lat, float), np.asarray(lon, float)
        self.rho = np.asarray(density_native, float)*1000.
        self.height = np.asarray(height_m, float)
        self.source, self.height_source = source, height_source
        self.provenance = provenance or {}
        if self.epochs.isscalar or len(self.epochs)<2:
            raise ValueError('At least two UTC frames required')
        self.seconds = (self.epochs-self.epochs[0]).sec
        if not np.isfinite(self.seconds).all() or not np.allclose(np.diff(self.seconds), 3600, atol=1e-6, rtol=0):
            raise ValueError('Consecutive hourly frames required')
        if self.lat.ndim != 1 or self.lon.ndim != 1 or min(len(self.lat),len(self.lon))<2 or not np.isfinite(self.lat).all() or not np.isfinite(self.lon).all():
            raise ValueError('Finite grid required')
        if np.any(np.diff(self.lat)<=0) or np.any(np.diff(self.lon)<=0) or not np.allclose(np.diff(np.r_[self.lon,self.lon[0]+360]),np.diff(self.lon)[0]):
            raise ValueError('Monotone latitude and periodic longitude required')
        if self.rho.ndim != 4 or self.rho.shape != self.height.shape or self.rho.shape[0] != len(self.epochs) or self.rho.shape[2:] != (len(self.lat),len(self.lon)):
            raise ValueError('Aligned (time,level,latitude,longitude) arrays required')
        if not np.isfinite(self.rho).all() or np.any(self.rho<=0):
            raise ValueError('Invalid density, no clipping or repair')
        self.valid = np.isfinite(self.height).all(axis=1) & (np.diff(self.height,axis=1)>0).all(axis=1)
        if valid_columns is not None:
            mask=np.asarray(valid_columns,bool)
            if mask.shape != self.valid.shape:raise ValueError('Column mask shape')
            self.valid &= mask
        for a in (self.rho,self.height,self.lat,self.lon,self.valid):a.flags.writeable=False

    @classmethod
    def from_saved(cls, path, *, expected_sha256, model, epochs, lat, lon, ilev, tlbc):
        path=Path(path).resolve();path.relative_to(ROOT)
        h=hashlib.sha256()
        with path.open('rb') as f:
            for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
        if h.hexdigest()!=expected_sha256:raise ValueError('Prediction SHA mismatch')
        if model not in ('Direct','Flow','LogDEN','History'):raise ValueError('Unknown official variant')
        with np.load(path,allow_pickle=False) as f:
            physical=decode_physical(f['pred'][0,:len(epochs)],f['means'][:171],f['stds'][:171],model=='LogDEN')
        zg,valid,mass=reconstruct_native_zg(physical[:,:28],physical[:,142:171],physical[:,113:142],tlbc,lat,ilev)
        obj=cls(epochs,lat,lon,physical[:,142:171],zg,source=model,height_source=HEIGHT_SOURCE,valid_columns=valid,
                provenance={'prediction_SHA256':expected_sha256,'future_reference_ZG_used':False,'known_TLBC_auxiliary_used':True})
        obj.reconstruction_summary={'invalid_columns':int((~valid).sum()),'inferred_mass_min':float(mass.min()),'inferred_mass_max':float(mass.max())}
        return obj

    def _stencil(self, utc, latitude_deg, longitude_deg):
        t=utc if isinstance(utc,Time) else Time(utc,scale='utc')
        if not t.isscalar:raise ValueError('Scalar UTC required')
        x=float((t-self.epochs[0]).sec);lat,lon=map(float,(latitude_deg,longitude_deg))
        if not np.isfinite([x,lat,lon]).all():raise ValueError('NONFINITE_QUERY')
        # Only absorb sub-microsecond representation noise at the time endpoints.
        if x < -1e-7 or x > self.seconds[-1]+1e-7:raise ValueError('TIME_OUTSIDE')
        x=min(max(x,0.),self.seconds[-1])
        if lat<self.lat[0] or lat>self.lat[-1]:raise ValueError('POLAR_CAP_UNSUPPORTED')
        k=int(np.clip(np.searchsorted(self.seconds,x,side='right')-1,0,len(self.seconds)-2))
        j=int(np.clip(np.searchsorted(self.lat,lat,side='right')-1,0,len(self.lat)-2))
        lon=(lon-self.lon[0])%360+self.lon[0]
        i=int(np.searchsorted(self.lon,lon,side='right')-1);ii=(i+1)%len(self.lon)
        wx=(lon-self.lon[i])/(self.lon[ii]+(360 if ii==0 else 0)-self.lon[i])
        wy=(lat-self.lat[j])/(self.lat[j+1]-self.lat[j]);wt=(x-self.seconds[k])/(self.seconds[k+1]-self.seconds[k])
        keys=[(kk,jj,iii) for kk in (k,k+1) for jj in (j,j+1) for iii in (i,ii)]
        weights=(np.array([1-wt,wt])[:,None,None]*np.array([1-wy,wy])[None,:,None]*np.array([1-wx,wx])[None,None,:]).reshape(-1)
        return k,keys,weights

    def query_native(self, utc, latitude_deg, longitude_deg, altitude_m, *, datum, vertical='log'):
        meta={'source':self.source,'height_source':self.height_source,'datum':datum,
              'units':'kg/m3','algorithm':'vertical log-density; horizontal/time linear density',
              'labels':'HINDCAST / TIEGCM_REFERENCE_ONLY / NATIVE_DATUM_ONLY',**self.provenance}
        def fail(reason):return DensityResult(False,reason=reason,metadata=meta)
        if datum!=DATUM:return fail('DATUM_UNVERIFIED')
        if vertical!='log':raise ValueError('Only qualified log vertical interpolation')
        h=float(altitude_m)
        if not np.isfinite(h):return fail('NONFINITE_QUERY')
        try:k,keys,weights=self._stencil(utc,latitude_deg,longitude_deg)
        except ValueError as exc:return fail(str(exc))
        meta.update(time_utc=[self.epochs[k].isot,self.epochs[k+1].isot],columns=keys)
        if not all(self.valid[key] for key in keys):return fail('INVALID_HEIGHT_RECONSTRUCTION_COLUMN')
        heights=[self.height[kk,:,j,i] for kk,j,i in keys]
        lower=max(z[0] for z in heights);upper=min(z[-1] for z in heights)
        meta.update(height_coverage_m=[float(lower),float(upper)],top_margin_m=float(upper-h))
        if not lower<=h<=upper:return fail('VERTICAL_OUTSIDE')
        values=[np.exp(np.interp(h,z,np.log(self.rho[kk,:,j,i]))) for z,(kk,j,i) in zip(heights,keys)]
        return DensityResult(True,float(np.dot(weights,values)),metadata=meta)

    def query_pressure(self, utc, latitude_deg, longitude_deg, ilev_index):
        if not isinstance(ilev_index,(int,np.integer)) or not 0<=ilev_index<self.rho.shape[1]:
            raise ValueError('Explicit native interface index required')
        k,keys,w=self._stencil(utc,latitude_deg,longitude_deg)
        return DensityResult(True,float(np.dot(w,[self.rho[kk,ilev_index,j,i] for kk,j,i in keys])),
                             metadata={'source':self.source,'coordinate':'NATIVE_ILEV_INDEX','index':ilev_index,'units':'kg/m3','no_geometric_height_claim':True})

    def __call__(self,utc_time,latitude_deg,longitude_deg,altitude_m,*,datum):
        return self.query_native(utc_time,latitude_deg,longitude_deg,altitude_m,datum=datum)

    def density_kg_m3(self,query):
        raise ValueError('EXTERNAL_DATUM_UNVERIFIED: explicit controlled virtual mapping required')
