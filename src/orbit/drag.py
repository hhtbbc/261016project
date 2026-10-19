"""Modular physical drag acceleration; SI, explicit frame and atmosphere APIs."""
from dataclasses import dataclass
import numpy as np
from astropy.time import TimeDelta
from astropy.utils import iers
import astropy.units as u
import erfa
from orbit.frames import check_eop, transform_state
from atmosphere.density_interface import DensityQuery, CorotatingAtmosphere


def drag_acceleration(rho_kg_m3, cd, area_m2, mass_kg, relative_velocity_m_s):
    values=np.asarray([rho_kg_m3,cd,area_m2,mass_kg],dtype=float)
    v=np.asarray(relative_velocity_m_s,dtype=float)
    if not np.isfinite(values).all() or np.any(values[:3]<0) or mass_kg<=0:
        raise ValueError('Require rho/Cd/area >= 0 and mass > 0, all finite')
    if v.shape!=(3,) or not np.isfinite(v).all():
        raise ValueError('Finite Cartesian relative velocity required')
    return -.5*rho_kg_m3*cd*area_m2/mass_kg*np.linalg.norm(v)*v


@dataclass(frozen=True)
class DragProperties:
    mass_kg: float
    area_m2: float
    cd: float
    provenance: str
    def __post_init__(self):
        drag_acceleration(0,self.cd,self.area_m2,self.mass_kg,np.zeros(3))
        if not self.provenance.strip():raise ValueError('Parameter provenance required')


class EarthFixedFrame:
    """Full GCRS -> ITRS state; physical acceleration only rotates back.

    Caller must configure frozen time/EOP with orbit.frames.configure_time_data.
    Astropy includes the derivative of frame orientation in velocity conversion.
    IAU2006/2000A (no observed dX/dY), consistent with J2 and current frames.
    """
    def __init__(self, epoch):
        if not epoch.isscalar:raise ValueError('Scalar initial epoch required')
        self.epoch=epoch
    def state_to_itrs(self, seconds, position, velocity):
        times=self.epoch+TimeDelta([float(seconds)],format='sec')
        check_eop(times)
        r,v=transform_state(np.asarray(position)[None,:],np.asarray(velocity)[None,:],times,'GCRS','ITRS')
        xp,yp=iers.earth_orientation_table.get().pm_xy(times)
        Q=erfa.c2t06a(times.tt.jd1,times.tt.jd2,times.ut1.jd1,times.ut1.jd2,
                     xp.to_value(u.rad),yp.to_value(u.rad))[0]
        return times[0],r[0],v[0],Q


class DragForce:
    """Composable (t,r,v) acceleration with replaceable density, wind and area.

    An optional properties_provider(query, v_rel_itrs) returns DragProperties,
    allowing future attitude/geometry-based Cd*A without modifying the solver.
    No default Swarm parameters or empirical density are supplied.
    """
    def __init__(self, frame, density, properties, wind=None, properties_provider=None):
        self.frame=frame;self.density=density;self.properties=properties
        self.wind=wind if wind is not None else CorotatingAtmosphere()
        self.properties_provider=properties_provider
    def evaluate(self, seconds, position, velocity):
        utc,r,v,Q=self.frame.state_to_itrs(seconds,position,velocity)
        Q=np.asarray(Q)
        if Q.shape!=(3,3) or not np.isfinite(Q).all() or not np.allclose(Q@Q.T,np.eye(3),atol=1e-12,rtol=0) or np.linalg.det(Q)<0:
            raise ValueError('Invalid Cartesian rotation')
        query=DensityQuery.from_itrs(utc,r)
        wind=np.asarray(self.wind.wind_itrs_m_s(query),dtype=float)
        if wind.shape!=(3,) or not np.isfinite(wind).all():raise ValueError('Invalid ITRS neutral wind')
        relative=v-wind
        rho=float(self.density.density_kg_m3(query))
        properties=self.properties_provider(query,relative) if self.properties_provider else self.properties
        if not isinstance(properties,DragProperties):raise TypeError('Expected DragProperties')
        acceleration_itrs=drag_acceleration(rho,properties.cd,properties.area_m2,properties.mass_kg,relative)
        acceleration_gcrs=Q.T@acceleration_itrs
        return {'acceleration_gcrs_m_s2':acceleration_gcrs,'acceleration_itrs_m_s2':acceleration_itrs,
                'relative_velocity_itrs_m_s':relative,'density_kg_m3':rho,'query':query,'properties':properties}
    def __call__(self, seconds, position, velocity):
        return self.evaluate(seconds,position,velocity)['acceleration_gcrs_m_s2']
