"""Offline SI audit of DART's retrieved three-species EOS, not a density provider."""
import numpy as np

def _fractions(o,o2,he=0.):
    a,b,c=np.broadcast_arrays(np.asarray(o,float),np.asarray(o2,float),np.asarray(he,float))
    if not all(np.isfinite(x).all() for x in [a,b,c]) or any((x<0).any() for x in [a,b,c]) or ((a+b+c)>1).any():raise ValueError('Invalid mass fractions, no clipping')
    return a,b,c

def three_species_density(pressure_Pa,temperature_K,O1_mmr,O2_mmr):
    a,b,_=_fractions(O1_mmr,O2_mmr);p,t=np.broadcast_arrays(np.asarray(pressure_Pa,float),np.asarray(temperature_K,float))
    if not np.isfinite(p).all() or not np.isfinite(t).all() or (p<=0).any() or (t<=0).any():raise ValueError('Finite positive SI pressure/temperature required')
    return p/(a/16.+b/32.+(1-a-b)/28.)/t/8314.

def helium_eos_density_ratio(O1_mmr,O2_mmr,HE_mmr):
    """rho(O,O2,N2,He)/rho(O,O2,remainder-as-N2), sameP/T; not native DEN error."""
    a,b,c=_fractions(O1_mmr,O2_mmr,HE_mmr)
    return (a/16.+b/32.+(1-a-b)/28.)/(a/16.+b/32.+c/4.+(1-a-b-c)/28.)
