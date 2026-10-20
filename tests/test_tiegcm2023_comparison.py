import unittest,importlib.util
from pathlib import Path
import numpy as np
spec=importlib.util.spec_from_file_location('comparison',Path(__file__).resolve().parents[1]/'scripts/compare_tiegcm2023_s3_s7.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ComparisonTests(unittest.TestCase):
    def test_identical(self):
        x=np.array([[1.,2.],[3.,4.]])
        r=m.metrics(x,x,np.ones_like(x),.05,True,True)
        self.assertEqual(r['RMSE'],0);self.assertEqual(r['pass_fraction'],1);self.assertEqual(r['log_RMSE'],0)
    def test_density_relative_sign(self):
        x=np.full((2,2),1.1);y=np.ones((2,2));r=m.metrics(x,y,np.ones((2,2)),.05,True,True)
        self.assertAlmostEqual(r['bias'],.1);self.assertAlmostEqual(r['log_RMSE'],np.log(1.1));self.assertFalse(r['passed'])
    def test_trace_only_relative_exclusion(self):
        x=np.array([[1e-9,1.],[2.,3.]]);y=np.array([[1e-10,1.],[2.,3.]])
        r=m.metrics(x,y,np.ones_like(x),.05,True,False,1e-8);self.assertEqual(r['n'],4);self.assertEqual(r['relative_n'],3)
    def test_masks_and_weights(self):
        x=np.array([[np.nan,2.],[4.,4.]]);y=np.ones_like(x)
        r=m.metrics(x,y,np.array([[1.,1.],[2.,2.]]),10)
        self.assertEqual(r['valid_fraction'],.75);self.assertAlmostEqual(r['bias'],13/5)
