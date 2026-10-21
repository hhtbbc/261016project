import unittest
import numpy as np
from orbit.force_budget_estimates import third_body_differential,spherical_shadow_class,schwarzschild_monopole
class ForceBudgetTests(unittest.TestCase):
 def test_geocenter_zero(self):np.testing.assert_array_equal(third_body_differential([0,0,0],[1.5e11,0,0],1.327e20),[0,0,0])
 def test_reference_term_and_linear_tide(self):
  r=np.array([4e6,3e6,-5e6]);R=np.array([1.5e11,2e10,-1e10]);mu=1.327e20
  a=third_body_differential(r,R,mu);direct=mu*((R-r)/np.linalg.norm(R-r)**3-R/np.linalg.norm(R)**3)
  np.testing.assert_allclose(a,direct,rtol=2e-10,atol=1e-17)
  k=R/np.linalg.norm(R);linear=mu/np.linalg.norm(R)**3*(3*np.dot(r,k)*k-r)
  self.assertLess(np.linalg.norm(a-linear)/np.linalg.norm(a),2e-4)
  self.assertLess(np.linalg.norm(a),1e-6)
 def test_shadow_and_bounds(self):
  self.assertEqual(spherical_shadow_class([-7e6,0,0],[1.5e11,0,0]),('umbra',0.,0.))
  self.assertEqual(spherical_shadow_class([7e6,0,0],[1.5e11,0,0]),('sunlit',1.,1.))
  with self.assertRaises(ValueError):spherical_shadow_class([0,0,0],[1.5e11,0,0])
 def test_relativistic_scale(self):
  a=schwarzschild_monopole([7e6,0,0],[0,7500,0],3.986004415e14)
  self.assertGreater(a[0],0);self.assertTrue(1e-9<np.linalg.norm(a)<1e-7)
