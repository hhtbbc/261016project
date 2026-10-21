"""Offline force-scale helpers ONLY: no RHS/propagator integration adapter."""
import numpy as np

def third_body_differential(position_m, body_geocentric_m, body_mu):
    """Stable geocentric differential attraction, including Earth reference term."""
    r=np.asarray(position_m,float);R=np.asarray(body_geocentric_m,float)
    if r.shape!=(3,) or R.shape!=(3,) or not np.isfinite([*r,*R,body_mu]).all() or body_mu<=0:raise ValueError('Finite SI vectors/positive GM required')
    R2=np.dot(R,R);dist=np.linalg.norm(R-r)
    if R2==0 or dist==0:raise ValueError('Singular geometry')
    q=np.dot(r,r-2*R)/R2
    if q<=-1:raise ValueError('Singular differential geometry')
    f=q*(3+3*q+q*q)/(1+(1+q)**1.5)
    return -body_mu/dist**3*(r+f*R)

def spherical_shadow_class(position_m, sun_geocentric_m, earth_radius_m=6378136.3, sun_radius_m=695700000.):
    """Finite-disk occultation classification, not production illumination model.

    Returns an illumination interval: penumbra is [0,1], never filled/interpolated.
    Earth is spherical here; no atmospheric refraction/ellipsoid/attitude.
    """
    r=np.asarray(position_m,float);S=np.asarray(sun_geocentric_m,float);q=S-r;rn=np.linalg.norm(r);sn=np.linalg.norm(q)
    if not np.isfinite([*r,*S]).all() or rn<=earth_radius_m or sn<=sun_radius_m:raise ValueError('Invalid shadow geometry')
    ae=np.arcsin(earth_radius_m/rn);asun=np.arcsin(sun_radius_m/sn);sep=np.arccos(np.clip(np.dot(-r,q)/(rn*sn),-1,1))
    if sep<ae-asun:return 'umbra',0.,0.
    if sep>ae+asun:return 'sunlit',1.,1.
    return 'penumbra',0.,1.

def schwarzschild_monopole(position_m,velocity_m_s,mu,c=299792458.):
    """Leading Earth monopole GR acceleration; only a budget, not full IERS model."""
    r=np.asarray(position_m,float);v=np.asarray(velocity_m_s,float);rn=np.linalg.norm(r)
    if r.shape!=(3,) or v.shape!=(3,) or not np.isfinite([*r,*v,mu,c]).all() or rn==0 or mu<=0 or c<=0:raise ValueError('Invalid SI state')
    return mu/(c*c*rn**3)*((4*mu/rn-np.dot(v,v))*r+4*np.dot(r,v)*v)
