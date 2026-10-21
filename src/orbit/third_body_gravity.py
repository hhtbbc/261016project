"""Explicit time-varying solar/lunar Newtonian geocentric differential gravity.

PROVISIONAL_EPHEMERIS: frozen ERFA epv00 Sun, moon98 Moon; no online access.
Moon is native GCRS; Sun geometric BCRS/ICRS axes aligned to GCRS at leading
Newtonian order. No apparent light-time/stellar-aberration coordinates are used.
Full relativistic spatial/time/GM scaling is NOT claimed. See validation report.
"""
import json,hashlib,re
import numpy as np
import erfa
from astropy.time import TimeDelta
from astropy.constants import au
from orbit.spherical_harmonics_gravity import ROOT
from orbit.force_budget_estimates import third_body_differential

class ThirdBodyGravity:
 def __init__(self,epoch,duration_s,*,sun=True,moon=True):
  if not epoch.isscalar or not np.isfinite(duration_s) or duration_s<=0 or not isinstance(sun,bool) or not isinstance(moon,bool):raise ValueError('Scalar epoch, positive span, boolean body switches required')
  self.epoch=epoch;self.duration_s=float(duration_s);self.enabled={'sun':sun,'moon':moon}
  meta=json.loads((ROOT/'configs/missing_force_sources.json').read_text());p=ROOT/'data/raw/gravity_sources/gm_de440.tpc';data=p.read_bytes()
  if hashlib.sha256(data).hexdigest()!=meta['sha256']:raise ValueError('GM source SHA mismatch')
  txt=data.decode();self.mu={b:float(re.search(r'BODY'+str(n)+r'_GM\s*=\s*\(\s*([^\s)]+)',txt).group(1).replace('D','E'))*1e9 for b,n in [('sun',10),('moon',301)]}
  self.metadata={'status':'PROVISIONAL_EPHEMERIS','position_source':'ERFA epv00 geometric heliocentric Earth (negative) for Sun; ERFA moon98 TT native GCRS Moon','erfa_version':erfa.__version__,'GM_source_sha256':meta['sha256'],'GM_time_scale':'DE440 TDB-compatible SI values; full TT rescaling/spatial mapping omitted at leading Newtonian order','no_runtime_download':True,'full_relativistic_mapping':False}
 def positions(self,seconds):
  seconds=float(seconds)
  if not np.isfinite(seconds) or not 0<=seconds<=self.duration_s:raise ValueError('Ephemeris query outside frozen experiment span')
  t=self.epoch+TimeDelta(seconds,format='sec');helio,bary=erfa.epv00(t.tdb.jd1,t.tdb.jd2);moon=erfa.moon98(t.tt.jd1,t.tt.jd2)
  positions={'sun':-np.array(helio['p'])*au.value,'moon':np.array(moon['p'])*au.value}
  if not all(np.isfinite(p).all() for p in positions.values()):raise ValueError('Invalid ephemeris position')
  return positions
 def components(self,seconds,position_m):
  r=np.asarray(position_m,float)
  if r.shape!=(3,) or not np.isfinite(r).all():raise ValueError('Finite geocentric Cartesian state required')
  positions=self.positions(seconds)
  return {b:third_body_differential(r,positions[b],self.mu[b]) if self.enabled[b] else np.zeros(3) for b in self.enabled}
 def __call__(self,seconds,position,velocity):
  values=self.components(seconds,position);return values['sun']+values['moon']
