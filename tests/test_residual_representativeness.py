import unittest
import numpy as np
from evaluation.residual_representativeness import *
from evaluation.causal_density_latitude import latitude_band
from evaluation.late_day_correction import RollingOrigin,diagnostic_quintiles
class DiagnosticTests(unittest.TestCase):
 def test_residual(self):np.testing.assert_allclose(residual([2,4],[1,2]),np.log(2))
 def test_invalid(self):
  for v in [0,-1,np.nan,np.inf]:
   with self.assertRaises(ValueError):residual([v],[1])
 def test_threshold(self):self.assertEqual(statistics(np.ones(29))['status'],'N/A_INSUFFICIENT_SAMPLES');self.assertEqual(statistics(np.ones(30))['median'],1)
 def test_MAD_unscaled(self):self.assertEqual(statistics(np.tile([0.,1.,2.],10))['MAD'],1)
 def test_latitude_boundaries(self):np.testing.assert_array_equal(latitude_band([-60,-30,0,30,60]),[2,1,0,1,2])
 def test_half_open(self):
  for hour in [6,18]:
   t=np.array([f'2021-03-23T{hour:02d}:00:00'],dtype='datetime64[ns]');m=RollingOrigin('2021-03-23',hour).masks(t);self.assertFalse(m['analysis'][0]);self.assertTrue(m['future_1h'][0])
 def test_overlap(self):self.assertEqual(overlap(np.ones(30),np.ones(30)),1);self.assertEqual(overlap(np.ones(30),-np.ones(30)),0)
 def test_overflow_preserved(self):self.assertEqual(overlap(np.full(30,10),np.full(30,10)),1)
 def test_quintile_ties(self):i,_=diagnostic_quintiles(np.ones(120));self.assertEqual(len(np.unique(i)),1)
 def test_contribution_identity(self):
  p=np.linspace(1,2,120);o=p+.2;rows=[contribution(p,o,np.arange(120)%3==i) for i in range(3)];self.assertAlmostEqual(sum(r['absolute_MSE_contribution'] for r in rows),np.mean((p-o)**2));self.assertAlmostEqual(sum(r['relative_MSE_contribution'] for r in rows),np.mean(((p-o)/o)**2))
 def test_coordinates(self):
  for ell in ELLIPSOIDS:
   for lat in [0,45,-45,89.999,90,-90]:
    xyz=forward(180,lat,450000,ell);lo,la,h=inverse(xyz,ell);self.assertLess(np.linalg.norm(forward(lo,la,h,ell)-xyz),1e-5);self.assertLess(abs(h-450000),1e-5)
 def test_longitude_periodicity(self):np.testing.assert_allclose(forward(540,30,400000,'GRS80'),forward(180,30,400000,'GRS80'),atol=1e-8)
if __name__=='__main__':unittest.main()
