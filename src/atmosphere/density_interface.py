"""Replaceable SI neutral density / wind query contracts (no real model assumed)."""
from dataclasses import dataclass
from typing import Protocol
import numpy as np
from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u


@dataclass(frozen=True)
class DensityQuery:
    utc: Time
    position_itrs_m: np.ndarray
    longitude_deg: float
    latitude_deg: float
    height_wgs84_m: float

    @classmethod
    def from_itrs(cls, epoch, position_m):
        r=np.asarray(position_m,dtype=float)
        if not epoch.isscalar or r.shape!=(3,) or not np.isfinite(r).all():
            raise ValueError('Scalar epoch and finite ITRS position required')
        lon,lat,height=EarthLocation.from_geocentric(*r,unit=u.m).to_geodetic('WGS84')
        r=r.copy();r.setflags(write=False)
        return cls(epoch.utc,r,float(lon.to_value(u.deg)),float(lat.to_value(u.deg)),float(height.to_value(u.m)))


class DensityProvider(Protocol):
    def density_kg_m3(self, query: DensityQuery) -> float:
        """Neutral mass density in kg/m³; reject unsupported dates/heights."""
        ...


class WindProvider(Protocol):
    def wind_itrs_m_s(self, query: DensityQuery) -> np.ndarray:
        """Neutral wind relative to rotating Earth, Cartesian ITRS m/s.

        Local east/north/up model wind must be rotated into Cartesian first.
        Plasma drift is not a neutral atmospheric wind measurement.
        """
        ...


@dataclass(frozen=True)
class ConstantDensityDemo:
    """SYNTHETIC test density; not Swarm, MSIS or TIE-GCM."""
    value_kg_m3: float
    def __post_init__(self):
        if not np.isfinite(self.value_kg_m3) or self.value_kg_m3<0:
            raise ValueError('Nonnegative finite density required')
    def density_kg_m3(self, query):
        return self.value_kg_m3


class CorotatingAtmosphere:
    """Zero neutral wind in ITRS; atmospheric rotation is handled by frame state."""
    def wind_itrs_m_s(self, query):
        return np.zeros(3)
