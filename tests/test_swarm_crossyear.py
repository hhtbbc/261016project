import unittest
import numpy as np
from evaluation.swarm_crossyear import strata,metric_row
from evaluation.swarm_density_comparison import paired_valid_mask
class TestCrossyear(unittest.TestCase):
    def test_latitude_partition(self):
        la=np.array([-90,-60,-30,0,30,60,90]);s=strata(la,np.full(7,440000),np.full(7,np.datetime64('2022-03-24')))
        np.testing.assert_array_equal(s['low'].astype(int)+s['mid']+s['high'],1)
        self.assertEqual(s['high'].sum(),4)
    def test_height_half_open(self):
        s=strata([0,0],[440000,450000],['2022-03-24','2022-03-24']);np.testing.assert_array_equal(s['height_440_450km'],[1,0])
    def test_three_hour_blocks(self):
        s=strata([0,0],[440000]*2,['2022-03-24T02:59:59','2022-03-24T03:00:00']);np.testing.assert_array_equal(s['UTC_00_03'],[1,0])
    def test_signed_relative_bias(self):
        y=np.tile([1.,2.],30);x=y*1.1;r=metric_row(x,y,np.ones(60,bool),np.ones(60,bool),np.ones(60,bool));self.assertAlmostEqual(r['relative_bias'],.1);self.assertAlmostEqual(r['relative_RMS'],.1)
    def test_no_sample_invention(self):
        r=metric_row([1],[1],[1],[1],[1]);self.assertEqual(r['n'],1);self.assertIsNone(r['RMSE'])
    def test_common_rejection(self):
        with self.assertRaises(ValueError):metric_row([np.nan],[1],[1],[1],[1])
    def test_cross_mapping_common(self):
        np.testing.assert_array_equal(paired_valid_mask([1,1,1],[1,np.nan,3],[2,3,np.nan]),[1,0,0])
if __name__=='__main__':unittest.main()
