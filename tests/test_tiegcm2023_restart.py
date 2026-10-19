"""No model launches: reject invalid starts and test explicit difference metrics."""
from pathlib import Path
import unittest
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from atmosphere.restart_validation import check_source_clock,inspect_restart,compare_arrays

class RestartTests(unittest.TestCase):
    def test_clock_mismatch_rejected(self):
        with self.assertRaises(ValueError):check_source_clock([77,23,50],[80,0,0])
    def test_day_can_differ_if_clock_matches(self):
        check_source_clock([78,0,0],[81,0,0])
    def test_original_is_complete_but_lacks_target_clock(self):
        path=ROOT/'data/raw/tiegcm2_support/tiegcm_res5.0_mareqx_smin_prim.nc'
        a=inspect_restart(path,[80,0,0]);b=inspect_restart(path,[80,23,50])
        self.assertTrue(a['structure_complete']);self.assertTrue(a['record_available'])
        self.assertFalse(b['record_available']);self.assertFalse(a['validated_continuation'])
    def test_known_error_metrics_and_units(self):
        r=compare_arrays([100.,200.],[103.,204.],atol=.05,rtol=0.,scale=.01)
        self.assertAlmostEqual(r['max_absolute_error'],.04)
        self.assertAlmostEqual(r['rmse'],np.sqrt((.03**2+.04**2)/2))
        self.assertAlmostEqual(r['max_relative_error'],.03);self.assertTrue(r['passed'])
    def test_nonfinite_and_mask_difference_fail(self):
        r=compare_arrays([1.,np.nan],[1.,2.],atol=1e-8,rtol=0.)
        self.assertFalse(r['passed']);self.assertEqual(r['reference_nonfinite'],1)
        r=compare_arrays([1.,2.],[1.,2.],[False,True],[False,False],atol=0.,rtol=0.)
        self.assertFalse(r['passed']);self.assertEqual(r['mask_mismatch_count'],1)
    def test_shape_and_zero_reference(self):
        with self.assertRaises(ValueError):compare_arrays([1.],[1.,2.],atol=0.,rtol=0.)
        r=compare_arrays([0.,1.],[0.,1.],atol=0.,rtol=0.)
        self.assertTrue(r['passed']);self.assertEqual(r['relative_zero_reference_count'],1)
    def test_large_physical_difference_not_hidden(self):
        self.assertFalse(compare_arrays([800.],[800.01],atol=1e-8,rtol=1e-10)['passed'])
if __name__=='__main__':unittest.main()
