import unittest
import numpy as np
from orbit.gravity_degree40 import Degree40EarthGravity
from orbit.gravity_truncation import ExtendedEarthGravity
from test_spherical_harmonics_gravity import external_reference
class Gravity40Tests(unittest.TestCase):
 def test_complete_and_backward(self):
  new=Degree40EarthGravity();self.assertEqual(len(new.coefficients),861)
  for n in [8,12,20]:
   small=Degree40EarthGravity(n);old=ExtendedEarthGravity(n);self.assertEqual(small.coefficients,old.coefficients)
   for p in [[4e6,3e6,5e6],[0.,0.,6850000.]]:np.testing.assert_array_equal(small.acceleration_itrs(p),old.acceleration_itrs(p))
 def test_external_random(self):
  rng=np.random.default_rng(400021);m=Degree40EarthGravity()
  for i in range(100):
   p=rng.normal(size=3);p*=rng.uniform(6578136.3,12000000)/np.linalg.norm(p);a=m.acceleration_itrs(p)
   self.assertTrue(np.isfinite(a).all());np.testing.assert_allclose(a,external_reference(m,p),rtol=2e-12,atol=2e-12)
 def test_equator_and_poles(self):
  m=Degree40EarthGravity()
  for lat in [-89.9,0,89.9]:
   for lon in [-179.99,0,90]:
    la,lo=np.deg2rad([lat,lon]);p=6850000*np.array([np.cos(la)*np.cos(lo),np.cos(la)*np.sin(lo),np.sin(la)]);np.testing.assert_allclose(m.acceleration_itrs(p),external_reference(m,p),rtol=2e-12,atol=2e-12)
  for s in [-1,1]:self.assertLess(np.linalg.norm(m.acceleration_itrs([0.,0.,s*6850000.])-m.acceleration_itrs([1e-5,0.,s*6850000.])),1e-9)
 def test_gradient(self):
  m=Degree40EarthGravity();p=np.array([4e6,-3e6,5e6]);a=m.acceleration_itrs(p);err=[]
  for h in [10000.,1000.,100.]:
   g=np.array([-(m.potential_itrs(p+np.eye(3)[j]*h)-m.potential_itrs(p-np.eye(3)[j]*h))/(2*h) for j in range(3)]);err.append(np.linalg.norm(a-g)/np.linalg.norm(a))
  self.assertLess(err[1],err[0]/50);self.assertLess(err[2],err[1]/30);self.assertLess(err[-1],2e-8)
 def test_invalid_degree(self):
  for d,o in [(41,40),(40,41),(-1,0)]:
   with self.assertRaises(ValueError):Degree40EarthGravity(d,o)
