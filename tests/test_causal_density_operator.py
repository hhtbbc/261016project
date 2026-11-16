"""Analytical numerical tests, not real-atmosphere validation."""
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import numpy as np
from astropy.time import Time
import test_hourly_tiegcm_observation as hourly_fixture
from atmosphere.tiegcm_density_provider import DATUM
from atmosphere.causal_observation_operator import map_a_queries,observe_map_a,split_masks

class TestCausalOperator(unittest.TestCase):
 def test_affine_horizontal_time_exponential_vertical(self):
  p=hourly_fixture.TestHourly().provider()
  for k in range(2):
   for j in range(2):
    for i in range(72):p.arrays[k][1][:,j,i]=(1+k+.1*j+.01*i)*np.exp(-np.array([100.,200.])/100)*1e-12
  q=p.query_native('2021-03-24T00:30',0,2.5,150,datum=DATUM)
  self.assertTrue(q.valid);self.assertAlmostEqual(q.rho_kg_m3/(np.exp(-1.5)*1e-12),1.555,13)
 def test_half_open_causal_windows(self):
  t=np.array(['2022-03-24T03','2022-03-24T05:59:30','2022-03-24T06','2022-03-24T07','2022-03-24T09','2022-03-24T12'],dtype='datetime64[ns]');m=split_masks(t)
  np.testing.assert_array_equal(m['calibration'],[1,1,0,0,0,0]);np.testing.assert_array_equal(m['future_1h'],[0,0,1,0,0,0]);np.testing.assert_array_equal(m['future_6h'],[0,0,1,1,1,0])
 def test_map_a_trace_and_formal_gate(self):
  p=hourly_fixture.TestHourly().provider();q=map_a_queries(np.array(['2021-03-24'],dtype='datetime64[ns]'),[0],[0],[150])[0];a,c=observe_map_a(p,q)
  self.assertTrue(a.valid);self.assertEqual(c['status'],'PROVISIONAL');self.assertAlmostEqual(c['model_zg_m'],150,6);self.assertEqual(p.query_external(q).reason,'EXTERNAL_DATUM_UNVERIFIED')
 def test_periodic_longitude(self):
  p=hourly_fixture.TestHourly().provider();self.assertEqual(p.query_native('2021-03-24',0,-1,150,datum=DATUM).rho_kg_m3,p.query_native('2021-03-24',0,359,150,datum=DATUM).rho_kg_m3)
 def test_no_fallback_at_invalid_zero_weight_column(self):
  p=hourly_fixture.TestHourly().provider();p.arrays[1][1][0,0,0]=np.nan;q=p.query_native('2021-03-24',-5,0,150,datum=DATUM);self.assertFalse(q.valid);self.assertIsNone(q.rho_kg_m3)
 def test_time_height_and_polar_rejection(self):
  p=hourly_fixture.TestHourly().provider()
  for t,lat,h,reason in [('2021-03-23',0,150,'TIME_OUTSIDE'),('2021-03-24',0,201,'VERTICAL_OUTSIDE'),('2021-03-24',6,150,'POLAR_CAP_UNSUPPORTED')]:self.assertEqual(p.query_native(t,lat,0,h,datum=DATUM).reason,reason)
if __name__=='__main__':unittest.main()
