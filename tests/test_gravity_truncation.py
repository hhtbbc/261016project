import unittest
import numpy as np
from pathlib import Path
from orbit.gravity_truncation import ExtendedEarthGravity
from orbit.spherical_harmonics_gravity import SphericalHarmonicsGravity
from test_spherical_harmonics_gravity import external_reference

class GravityTruncationTests(unittest.TestCase):
 def test_complete_common_coefficients(self):
  m=ExtendedEarthGravity(20);self.assertEqual(len(m.coefficients),231)
  for d in [8,12]:
   small=ExtendedEarthGravity(d)
   for k,v in small.coefficients.items():self.assertEqual(v,m.coefficients[k])
 def test_external_all_degrees(self):
  rng=np.random.default_rng(20261021)
  for d in [8,12,20]:
   m=ExtendedEarthGravity(d)
   for _ in range(100):
    p=rng.normal(size=3);p*=rng.uniform(6578136.3,12000000)/np.linalg.norm(p)
    np.testing.assert_allclose(m.acceleration_itrs(p),external_reference(m,p),rtol=2e-12,atol=2e-12)
 def test_equator_near_poles(self):
  for d in [8,12,20]:
   m=ExtendedEarthGravity(d)
   for lat in [-89.9,-45,0,45,89.9]:
    for lon in [-179.99,0,90,179.99]:
     la,lo=np.deg2rad([lat,lon]);p=6850000*np.array([np.cos(la)*np.cos(lo),np.cos(la)*np.sin(lo),np.sin(la)])
     np.testing.assert_allclose(m.acceleration_itrs(p),external_reference(m,p),rtol=2e-12,atol=2e-12)
 def test_exact_poles(self):
  for d in [8,12,20]:
   m=ExtendedEarthGravity(d)
   for s in [-1,1]:
    a=m.acceleration_itrs([0.,0.,s*6850000]);b=m.acceleration_itrs([1e-5,0.,s*6850000]);self.assertTrue(np.isfinite(a).all());self.assertLess(np.linalg.norm(a-b),1e-9)
 def test_gradient_convergence(self):
  p=np.array([4e6,-3e6,5e6])
  for d in [8,12,20]:
   m=ExtendedEarthGravity(d);a=m.acceleration_itrs(p);err=[]
   for h in [10000.,1000.,100.]:
    g=np.array([-(m.potential_itrs(p+np.eye(3)[j]*h)-m.potential_itrs(p-np.eye(3)[j]*h))/(2*h) for j in range(3)])
    err.append(np.linalg.norm(a-g)/np.linalg.norm(a))
   self.assertLess(err[1],err[0]/50);self.assertLess(err[2],err[1]/30);self.assertLess(err[-1],2e-8)
 def test_8_bitwise_historical_states(self):
  old=SphericalHarmonicsGravity();new=ExtendedEarthGravity(8)
  self.assertEqual(old.coefficients,new.coefficients)
  root=Path(__file__).resolve().parents[1]
  with np.load(root/'data/processed/spherical_harmonics_v1/H1_states.npz') as z:states=z['states']
  for y in states:
   self.assertEqual(old.potential_itrs(y[:3]),new.potential_itrs(y[:3]))
   np.testing.assert_array_equal(old.acceleration_itrs(y[:3]),new.acceleration_itrs(y[:3]))
 def test_order_restriction(self):
  for n,m in [(21,20),(12,13),(-1,0),(8,-1)]:
   with self.assertRaises(ValueError):ExtendedEarthGravity(n,m)
 def test_order_zero_external(self):
  p=np.array([3e6,4e6,-5e6])
  for d in [8,12,20]:
   m=ExtendedEarthGravity(d,0);np.testing.assert_allclose(m.acceleration_itrs(p),external_reference(m,p),rtol=2e-12,atol=2e-12)
