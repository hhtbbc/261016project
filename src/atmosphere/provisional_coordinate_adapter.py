"""Explicit experimental mappings only; intentionally not a DensityProvider.

No WGS84-to-ZG equivalence or uncertainty bound is asserted. Formal external
queries retain EXTERNAL_DATUM_UNVERIFIED in the unmodified native provider.
"""
from dataclasses import dataclass, field
import numpy as np
from .density_interface import DensityQuery
from .tiegcm_density_provider import DATUM, DensityResult

A_WGS84 = 'A_WGS84_AS_NATIVE_ZG'
B_SPHERE = 'B_GEOCENTRIC_SPHERE'
LIMITATIONS = ('PROVISIONAL conditional coordinate hypothesis; not a validated ZG '
               'datum conversion, confidence interval, or physical accuracy result; '
               'must not be used automatically by the operational drag interface')

@dataclass(frozen=True)
class ProvisionalCoordinates:
    assumption: str
    utc: str
    itrs_m: tuple
    wgs84_longitude_deg: float
    wgs84_latitude_deg: float
    wgs84_height_m: float
    geocentric_latitude_deg: float
    model_longitude_deg: float
    model_latitude_deg: float
    model_zg_m: float
    height_offset_m: float
    sphere_radius_m: float | None
    status: str = field(default='PROVISIONAL', init=False)
    limitations: str = field(default=LIMITATIONS, init=False)

@dataclass(frozen=True)
class ProvisionalDensityResult:
    coordinates: ProvisionalCoordinates
    native_result: DensityResult
    status: str = field(default='PROVISIONAL', init=False)

@dataclass(frozen=True, kw_only=True)
class ProvisionalCoordinateAdapter:
    assumption: str
    height_offset_m: float = 0.0
    sphere_radius_m: float | None = None

    def __post_init__(self):
        if self.assumption not in (A_WGS84, B_SPHERE):
            raise ValueError('Explicit supported PROVISIONAL assumption required')
        if not np.isfinite(self.height_offset_m):
            raise ValueError('Finite explicit perturbation required')
        if self.assumption == B_SPHERE:
            if self.sphere_radius_m is None or not np.isfinite(self.sphere_radius_m) or self.sphere_radius_m <= 0:
                raise ValueError('B requires an explicit positive sphere radius')
        elif self.sphere_radius_m is not None:
            raise ValueError('Sphere radius is inapplicable to A')

    def adapt(self, query: DensityQuery) -> ProvisionalCoordinates:
        r = np.asarray(query.position_itrs_m, dtype=float)
        if r.shape != (3,) or not np.isfinite(r).all() or np.linalg.norm(r) == 0:
            raise ValueError('Finite nonzero ITRS position required')
        lat_gc = float(np.degrees(np.arctan2(r[2], np.hypot(r[0], r[1]))))
        if self.assumption == A_WGS84:
            lat, height = query.latitude_deg, query.height_wgs84_m
        else:
            lat, height = lat_gc, float(np.linalg.norm(r) - self.sphere_radius_m)
        return ProvisionalCoordinates(
            assumption=self.assumption, utc=query.utc.utc.isot,
            itrs_m=tuple(map(float, r)),
            wgs84_longitude_deg=query.longitude_deg,
            wgs84_latitude_deg=query.latitude_deg,
            wgs84_height_m=query.height_wgs84_m,
            geocentric_latitude_deg=lat_gc,
            model_longitude_deg=query.longitude_deg,
            model_latitude_deg=float(lat), model_zg_m=float(height + self.height_offset_m),
            height_offset_m=float(self.height_offset_m), sphere_radius_m=self.sphere_radius_m)

    def query_provisional(self, provider, query: DensityQuery, *, vertical='log'):
        coordinates = self.adapt(query)
        result = provider.query_native(query.utc, coordinates.model_latitude_deg,
                                      coordinates.model_longitude_deg, coordinates.model_zg_m,
                                      datum=DATUM, vertical=vertical)
        return ProvisionalDensityResult(coordinates, result)


def diagnose_provisional_interpolation(provider, result: ProvisionalDensityResult):
    """Offline diagnostics using the exact eight native columns, never a force API.

    Reads the existing provider's bounded column cache. Each alternative changes
    one interpolation dimension while holding the other operations fixed.
    Coarsening is a sensitivity test, not an independent high-resolution truth.
    """
    if result.status != 'PROVISIONAL':
        raise ValueError('PROVISIONAL result required')
    native = result.native_result
    if not native.valid:
        return {'status': 'PROVISIONAL', 'reason': native.reason}
    lookup = {(p.name, record): k for k, (_, p, record) in enumerate(provider.records)}
    columns = [provider._column(lookup[(m['file'], m['record'])], m['lat_index'], m['lon_index'])
               for m in native.metadata['columns']]
    h = result.coordinates.model_zg_m
    w = native.metadata['weights']
    wt = np.array([1-w['time'], w['time']])
    spatial = np.outer([1-w['latitude'], w['latitude']], [1-w['longitude'], w['longitude']])
    values=[]; linear=[]; coarse=[]; slopes=[]; spacing=[]
    for (z,rho), bracket in zip(columns,native.metadata['vertical_brackets']):
        b=bracket['lower_index']; log_rho=np.log(rho)
        values.append(np.exp(np.interp(h,z,log_rho)))
        linear.append(np.interp(h,z,rho))
        keep=np.unique(np.r_[np.arange(0,len(z),2),len(z)-1])
        coarse.append(np.exp(np.interp(h,z[keep],log_rho[keep])))
        slopes.append((log_rho[b+1]-log_rho[b])/(z[b+1]-z[b]))
        spacing.append(z[b+1]-z[b])
    values=np.array(values).reshape(2,2,2)
    frame_rho=np.sum(values*spatial[None],axis=(1,2))
    combined=wt[:,None,None]*spatial[None]
    baseline=float(np.sum(combined*values))
    if not np.isclose(baseline,native.rho_kg_m3,rtol=1e-13,atol=0):
        raise ValueError('Native diagnostic reconstruction mismatch')
    slope=float(np.sum(combined*values*np.array(slopes).reshape(2,2,2))/baseline)
    return {'status':'PROVISIONAL', 'top_margin_m':min(z[-1]-h for z,_ in columns),
            'bottom_margin_m':min(h-z[0] for z,_ in columns),
            'dlnrho_dh_per_m':slope, 'scale_height_m':-1/slope if slope<0 else None,
            'vertical_spacing_min_m':float(min(spacing)), 'vertical_spacing_max_m':float(max(spacing)),
            'vertical_linear_relative':float(np.sum(combined*np.array(linear).reshape(2,2,2))/baseline-1),
            'horizontal_log_relative':float(np.dot(wt,np.exp(np.sum(np.log(values)*spatial[None],axis=(1,2))))/baseline-1),
            'time_log_relative':float(np.exp(np.dot(wt,np.log(frame_rho)))/baseline-1),
            'horizontal_and_time_log_relative':float(np.exp(np.sum(combined*np.log(values)))/baseline-1),
            'vertical_coarsened_log_relative':float(np.sum(combined*np.array(coarse).reshape(2,2,2))/baseline-1)}
