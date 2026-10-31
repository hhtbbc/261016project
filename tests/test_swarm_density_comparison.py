from pathlib import Path
import sys,unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from evaluation.swarm_density_comparison import quality_mask,compare_density,periods,paired_valid_mask


class ObservationTests(unittest.TestCase):
    def test_nominal_anomalous_unknown_distinct(self):
        valid,reasons=quality_mask([1.,1.,1.,np.nan,9.99e32,0.],[0,1,2,0,0,0])
        np.testing.assert_array_equal(valid,[True,False,False,False,False,False])
        self.assertEqual(reasons['anomalous'].sum(),1);self.assertEqual(reasons['unknown'].sum(),1)
    def test_metric_independent_values(self):
        a=compare_density([2.,1.],[1.,2.]);self.assertEqual(a['RMSE'],1);self.assertEqual(a['MAE'],1)
        self.assertEqual(a['bias'],0);self.assertAlmostEqual(a['relative_RMS'],np.sqrt(.625))
        self.assertAlmostEqual(a['log_RMS'],np.log(2))
    def test_invalid_metric_not_silently_removed(self):
        for a in ([0.,1.],[np.nan,1.],[-1.,1.]):
            with self.assertRaises(ValueError):compare_density(a,[1.,1.])
    def test_relative_denominator_has_no_floor(self):
        a=compare_density([2e-30],[1e-30]);self.assertEqual(a['relative_RMS'],1)
    def test_no_samples_explicit(self):self.assertEqual(compare_density([],[])['n'],0)
    def test_pairing_intersection_all_models(self):
        a=np.array([1,np.nan,1]);b=np.array([1,1,np.nan]);m=paired_valid_mask([True]*3,a,b)
        np.testing.assert_array_equal(m,[True,False,False])
    def test_event_excluded_and_boundaries(self):
        p=periods([1,6.999,7,7.001,8,13,13.001])
        np.testing.assert_array_equal(p['pre'],[1,1,0,0,0,0,0]);np.testing.assert_array_equal(p['post'],[0,0,0,0,1,1,0])
        self.assertFalse(p['all_forecast'][2]);self.assertTrue(p['event'][2])
    def test_units_scaling_preserves_relative_error(self):
        a=compare_density([1,2],[2,1]);b=compare_density(np.array([1,2])*1e-12,np.array([2,1])*1e-12)
        self.assertEqual(a['relative_RMS'],b['relative_RMS']);self.assertAlmostEqual(b['RMSE']/a['RMSE'],1e-12)


if __name__=='__main__':unittest.main()
