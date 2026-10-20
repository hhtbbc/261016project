"""Explicit-driver NRLMSIS 2.1, WGS84/SI. No implicit weather retrieval."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import json
import numpy as np
from astropy.time import Time
import pymsis
from atmosphere.density_interface import DensityQuery


def _dt(value):
    t = value if isinstance(value, Time) else Time(value, scale='utc')
    if not t.isscalar or not np.isfinite(t.jd):
        raise ValueError('Finite scalar UTC required')
    return t.utc.to_datetime(timezone=timezone.utc)


@dataclass(frozen=True)
class MsisDrivers:
    f107_previous_day: float
    f107a_centered81: float
    ap: tuple
    provenance: str

    def __post_init__(self):
        values = np.asarray([self.f107_previous_day, self.f107a_centered81, *self.ap], float)
        if len(self.ap) != 7 or not np.isfinite(values).all() or np.any(values < 0) or np.any(values[:2] <= 0) or not self.provenance:
            raise ValueError('Positive solar flux and seven nonnegative finite Ap values with provenance required')
        object.__setattr__(self, 'ap', tuple(float(x) for x in self.ap))


class FrozenGfzDrivers:
    """Immutable-in-practice daily/binned GFZ lookup; explicit missing-data failure."""
    def __init__(self, path):
        self.path = Path(path)
        raw = self.path.read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        d = json.loads(raw)
        self._solar = d['solar_observed_sfu']
        self._ap = d['ap_3hour']
        self._daily = d['Ap_daily']
        self.provenance = f'GFZ / HINDCAST / {self.sha256}'

    def at(self, utc):
        t = _dt(utc)
        day = t.date()
        solar_days = [(day + timedelta(days=i)).isoformat() for i in range(-40,41)]
        b = t.replace(hour=(t.hour//3)*3, minute=0, second=0, microsecond=0)
        def ap(lag):
            return float(self._ap[(b-timedelta(hours=lag)).strftime('%Y-%m-%dT%H:00:00Z')])
        try:
            a = (float(self._daily[day.isoformat()]), ap(0), ap(3), ap(6), ap(9),
                 float(np.mean([ap(i) for i in range(12,34,3)])),
                 float(np.mean([ap(i) for i in range(36,58,3)])))
            return MsisDrivers(float(self._solar[(day-timedelta(days=1)).isoformat()]),
                               float(np.mean([self._solar[x] for x in solar_days])), a, self.provenance)
        except KeyError as e:
            raise ValueError(f'Missing frozen GFZ input: {e}') from e


@dataclass(frozen=True)
class MsisResult:
    rho_kg_m3: float
    model: str
    drivers: MsisDrivers
    valid: bool = True
    status: str = 'HINDCAST / MODEL_DENSITY'


class MsisDensityProvider:
    def __init__(self, drivers, *, version):
        if str(version) != '2.1':
            raise ValueError('This validated provider requires explicit NRLMSIS 2.1')
        if drivers is None or not callable(getattr(drivers, 'at', None)):
            raise ValueError('Frozen explicit driver provider required')
        self.drivers = drivers
        self.version = '2.1'

    def query_batch(self, times, longitude_deg, latitude_deg, height_wgs84_m):
        times = Time(times).utc
        if times.isscalar:
            times = Time([times])
        arrays = [np.asarray(x, dtype=float).reshape(-1) for x in (longitude_deg, latitude_deg, height_wgs84_m)]
        n = len(times)
        if n == 0 or any(x.size != n or not np.isfinite(x).all() for x in arrays) or not np.isfinite(times.jd).all():
            raise ValueError('Aligned finite nonempty flythrough arrays required')
        lon, lat, height = arrays
        # Conservative declared software domain, not a claim about model accuracy.
        if np.any(abs(lat)>90) or np.any((height<0)|(height>1000000)):
            raise ValueError('Require WGS84 latitude [-90,90], altitude [0,1000] km')
        d = [self.drivers.at(t) for t in times]
        if any(not isinstance(x, MsisDrivers) for x in d):
            raise ValueError('Validated explicit MsisDrivers required')
        out = pymsis.calculate(times.to_value('datetime64'), (lon+180)%360-180,
            lat, height/1000, np.array([x.f107_previous_day for x in d]),
            np.array([x.f107a_centered81 for x in d]), np.array([x.ap for x in d]),
            version=self.version, geomagnetic_activity=-1)
        rho = np.asarray(out[:,pymsis.Variable.MASS_DENSITY], dtype=float)
        if rho.shape != (n,) or not np.isfinite(rho).all() or np.any(rho<=0):
            raise ValueError('NRLMSIS returned invalid density')
        return [MsisResult(float(r), 'NRLMSIS 2.1 / pymsis '+pymsis.__version__, x) for r,x in zip(rho,d)]

    def query(self, utc, longitude_deg, latitude_deg, height_wgs84_m):
        return self.query_batch(Time([Time(utc)]), [longitude_deg], [latitude_deg], [height_wgs84_m])[0]

    def density_kg_m3(self, query: DensityQuery):
        # Reconstruct from ITRS rather than trusting inconsistent duplicated coordinates.
        q = DensityQuery.from_itrs(query.utc, query.position_itrs_m)
        return self.query(q.utc, q.longitude_deg, q.latitude_deg, q.height_wgs84_m).rho_kg_m3
