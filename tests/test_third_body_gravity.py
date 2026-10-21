import unittest,json,csv
from pathlib import Path
import numpy as np
from astropy.time import Time
from orbit.third_body_gravity import ThirdBodyGravity
from orbit.frames import configure_time_data
from orbit.gravity_truncation import ExtendedEarthGravity
from orbit.spherical_harmonics_gravity import GcrsSphericalHarmonicsForce
from orbit.two_body import make_state_derivative
ROOT=Path(__file__).resolve().parents[1]
class ThirdBodyTests(unittest.TestCase):
 def setUp(self):self.epoch=Time('2023-03-21T00:00:02',scale='utc');self.m=ThirdBodyGravity(self.epoch,21600)
 def test_units_source_and_positions(self):
  self.assertAlmostEqual(self.m.mu['sun']/1e20,1.3271244004127942);self.assertAlmostEqual(self.m.mu['moon']/1e12,4.90280011845755)
  p=self.m.positions(0);self.assertTrue(1.4e11<np.linalg.norm(p['sun'])<1.6e11);self.assertTrue(3e8<np.linalg.norm(p['moon'])<5e8)
 def test_independent_horizons_positions(self):
  for body,limit in [('sun',20000),('moon',40000)]:
   reference=json.loads((ROOT/'configs/third_body_horizons_reference.json').read_text())[body]
   self.assertEqual(reference['query']['VEC_CORR'],"'NONE'");self.assertEqual(reference['query']['CENTER'],"'500@399'")
   self.assertEqual(len(reference['records']),3)
   for row in reference['records']:
    p=np.asarray(row['geocentric_ICRF_m']);self.assertLess(np.linalg.norm(p-self.m.positions(row['elapsed_s'])[body]),limit)
 def test_geocenter_and_formula(self):
  r=np.array([3e6,4e6,5e6]);parts=self.m.components(300,r);positions=self.m.positions(300)
  for b in parts:
   R=positions[b];expected=self.m.mu[b]*((R-r)/np.linalg.norm(R-r)**3-R/np.linalg.norm(R)**3);np.testing.assert_allclose(parts[b],expected,rtol=2e-9,atol=1e-17)
  np.testing.assert_array_equal(self.m(0,[0,0,0],[0,0,0]),[0,0,0])
 def test_switches_and_backward_rhs(self):
  configure_time_data();r=np.array([3e6,4e6,5e6]);v=np.array([1000.,3000.,5000.]);y=np.r_[r,v]
  onlymoon=ThirdBodyGravity(self.epoch,21600,sun=False);np.testing.assert_array_equal(onlymoon(0,r,v),self.m.components(0,r)['moon'])
  off=ThirdBodyGravity(self.epoch,21600,sun=False,moon=False);np.testing.assert_array_equal(off(0,r,v),np.zeros(3));earth=GcrsSphericalHarmonicsForce(self.epoch,ExtendedEarthGravity(20));np.testing.assert_array_equal(make_state_derivative([earth,off])(0,y),make_state_derivative([earth])(0,y))
 def test_time_continuity(self):
  for t in [0.,10800.,21599.]:
   a=self.m.positions(t);b=self.m.positions(t+.01)
   self.assertLess(np.linalg.norm(b['sun']-a['sun']),400);self.assertLess(np.linalg.norm(b['moon']-a['moon']),20)
 def test_extreme_geometry_and_limit(self):
  R=self.m.positions(0)['moon'];k=R/np.linalg.norm(R)
  for r in [k*6850000,-k*6850000,[0.,0.,6850000.]]:self.assertTrue(np.isfinite(self.m(0,r,[0,0,0])).all())
  for t in [-1,21601,float('nan')]:
   with self.assertRaises(ValueError):self.m.positions(t)
 def test_repeatability_and_magnitude(self):
  r=np.array([3e6,4e6,5e6]);a=self.m(123.456,r,[0,0,0]);np.testing.assert_array_equal(a,self.m(123.456,r,[0,0,0]));self.assertTrue(1e-8<np.linalg.norm(a)<1e-5)
 def test_tends_to_geocenter(self):
  k=np.array([.3,-.4,.5]);norms=[]
  for scale in [1e5,1e3,1.]:norms.append(np.linalg.norm(self.m(10,scale*k,[0,0,0])))
  self.assertAlmostEqual(norms[1]/norms[0],.01,delta=1e-5);self.assertAlmostEqual(norms[2]/norms[1],.001,delta=1e-7)
