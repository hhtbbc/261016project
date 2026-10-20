"""Static zonal J3/J4 increments; SI, arbitrary explicit unit figure axis.

Defined project potential, not full EGM2008: preserve legacy nominal J2, re-express
EGM2008 static fully-normalized C30/C40 into the existing mu/R convention.
Source/derivation: configs/higher_order_gravity.json and HIGH_ORDER_GRAVITY_DESIGN.
"""
import numpy as np
from orbit.two_body import EARTH_MU
from orbit.j2 import J2_REFERENCE_RADIUS_M

SOURCE_MU = 3.986004415e14
SOURCE_RADIUS_M = 6378136.3
CBAR30 = 0.957161207093473e-6
CBAR40 = 0.539965866638991e-6
J3 = -np.sqrt(7)*CBAR30*(SOURCE_MU/EARTH_MU)*(SOURCE_RADIUS_M/J2_REFERENCE_RADIUS_M)**3
J4 = -3*CBAR40*(SOURCE_MU/EARTH_MU)*(SOURCE_RADIUS_M/J2_REFERENCE_RADIUS_M)**4


def _geometry(position, axis, mu, radius, coefficient, *, complex_potential=False):
    r=np.asarray(position)
    k=np.asarray(axis,dtype=float)
    if r.shape!=(3,) or not np.isfinite(r).all() or (np.iscomplexobj(r) and not complex_potential):
        raise ValueError('Finite real Cartesian position required for acceleration')
    if k.shape!=(3,) or not np.isfinite(k).all() or abs(np.linalg.norm(k)-1)>1e-12:
        raise ValueError('Explicit unit symmetry axis required')
    if not np.isfinite([mu,radius,coefficient]).all() or mu<=0 or radius<=0:
        raise ValueError('Invalid potential parameters')
    r=np.asarray(r,dtype=complex if np.iscomplexobj(r) else float)
    length=np.sqrt(np.dot(r,r))
    if length==0:raise ValueError('Central singularity')
    return r,k,length,np.dot(k,r)/length


def _polynomials(degree,s):
    if degree==2:return (3*s*s-1)/2,3*s
    if degree==3:return (5*s**3-3*s)/2,(15*s*s-3)/2
    if degree==4:return (35*s**4-30*s*s+3)/8,(140*s**3-60*s)/8
    raise ValueError('Validated zonal degrees are 2,3,4')


def zonal_potential(position_m, degree, coefficient, axis=(0.,0.,1.),
                    mu=EARTH_MU, radius_m=J2_REFERENCE_RADIUS_M):
    """Single contribution to mechanical potential U (J/kg); a=-grad(U).

    Analytic complex extension is solely for complex-step validation. No central
    potential or other degrees are added implicitly.
    """
    r,k,length,s=_geometry(position_m,axis,mu,radius_m,coefficient,complex_potential=True)
    p,_=_polynomials(degree,s)
    return mu*coefficient*radius_m**degree/length**(degree+1)*p


def _acceleration(position,degree,coefficient,axis,mu,radius):
    r,k,length,s=_geometry(position,axis,mu,radius,coefficient)
    p,dp=_polynomials(degree,s)
    return mu*coefficient*radius**degree/length**(degree+2)*(((degree+1)*p+s*dp)*r/length-dp*k)


def j3_acceleration(position_m,axis=(0.,0.,1.),mu=EARTH_MU,
                    radius_m=J2_REFERENCE_RADIUS_M,j3=J3):
    return _acceleration(position_m,3,j3,axis,mu,radius_m)


def j4_acceleration(position_m,axis=(0.,0.,1.),mu=EARTH_MU,
                    radius_m=J2_REFERENCE_RADIUS_M,j4=J4):
    return _acceleration(position_m,4,j4,axis,mu,radius_m)


class HigherOrderZonalForce:
    """Composable J3/J4 ONLY; caller supplies the existing EarthFigureAxis."""
    def __init__(self,axis_provider,*,include_j3,include_j4):
        if not callable(axis_provider):raise TypeError('Time-dependent axis provider required')
        self.axis_provider=axis_provider;self.include_j3=bool(include_j3);self.include_j4=bool(include_j4)
    def __call__(self,seconds,position,velocity):
        axis=self.axis_provider(seconds);a=np.zeros(3)
        if self.include_j3:a+=j3_acceleration(position,axis)
        if self.include_j4:a+=j4_acceleration(position,axis)
        return a
