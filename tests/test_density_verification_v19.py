"""Synthetic verification mechanics, never accesses V18 metric tables."""
import sys,unittest,math,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from evaluation.density_verification import *
F=ROOT/'experiments/tiegcm_2022_mar25_independent_verification_v19/tests_local'

def coeff(x):return dict(status='SUPPORTED',N=30,b=999.,multiplier=x)
def params():return dict(GlobalAdaptive06=coeff(.9),GlobalAdaptive18=coeff(1.2),LatitudeAdaptive18=dict(low=coeff(1.1),mid=coeff(1.2),high=coeff(1.3)))
class Verification(unittest.TestCase):
 def test_frozen_multiplier_not_exp(self):
  p,s=prediction([1,2,3],[0,30,60],params(),18,'LatitudeAdaptive18');np.testing.assert_array_equal(p,np.array([1.,2.,3.])*[1.1,1.2,1.3]);self.assertTrue(s.all())
 def test_exp_one_ulp(self):
  b=.13412716979060235;x=math.exp(b);y=float(np.exp(b));self.assertEqual(abs(x-y),np.spacing(y));self.assertNotEqual(x,y)
 def test_near_zero_bias(self):
  o=np.ones(30)*1e-12;p=o.copy();p[:15]+=1e-15;p[15:]-=1e-15;v=statistics(p,o)['bias'];self.assertTrue(numeric(v,v)['PASS'])
 def test_very_small_bias_difference_rejected(self):self.assertFalse(numeric(5.453772204284436e-16,5.453772204285187e-16)['PASS'])
 def test_zero_rule(self):
  self.assertTrue(numeric(0,0)['PASS']);self.assertFalse(numeric(1e-300,0)['PASS']);self.assertIsNone(numeric(1e-300,0)['relative_difference'])
 def test_ids(self):
  with self.assertRaises(ValueError):require_ids(['a','b'],['a','c'])
 def test_corrupted_metric(self):self.assertFalse(numeric(1.,1.01)['PASS'])
 def test_sha_mismatch(self):
  p=F/'sha.json';write_json(F,'sha.json',{'x':1})
  with self.assertRaises(ValueError):check_sha(p,'0'*64)
 def test_missing_metric(self):
  with self.assertRaises(ValueError):check_metric_fields(dict(status='OK'))
 def test_nonfinite(self):
  for v in [np.nan,np.inf,-np.inf]:
   with self.assertRaises(ValueError):numeric(v,1)
 def test_density_invalid(self):
  for v in [0,-1,np.nan,np.inf]:
   with self.assertRaises(ValueError):statistics(np.full(30,v),np.ones(30))
 def test_joint_wrong(self):
  r=dict(RMSE=2,relative_RMS=2,relative_P95=2,relative_bias=.2);c=dict(RMSE=1,relative_RMS=3,relative_P95=1,relative_bias=.1);self.assertEqual(joint(r,c,r,c)['JOINT_NO_REGRET'],'FAIL')
 def test_history_write_rejected(self):
  with self.assertRaises(ValueError):write_json(ROOT/'experiments/tiegcm_2022_mar25_density_validation_v18','must_not_exist.json',{})
 def test_no_overwrite(self):
  write_json(F,'once.json',{})
  with self.assertRaises(FileExistsError):write_json(F,'once.json',{})
 def test_reservation_once(self):
  reserve(F/'reserved')
  with self.assertRaises(FileExistsError):reserve(F/'reserved')
 def test_bands(self):np.testing.assert_array_equal(band([-60,-30,-29,30,60]),[2,1,0,1,2])
 def test_support_threshold_no_fallback(self):
  c=params();c['LatitudeAdaptive18']['low']['N']=29;out,s=prediction([1,2],[0,30],c,18,'LatitudeAdaptive18');self.assertFalse(s[0]);self.assertTrue(np.isnan(out[0]));self.assertTrue(s[1])
 def test_half_open_poison(self):
  t=np.array(['2022-03-25T05:59:30','2022-03-25T06:00:00'],dtype='datetime64[ns]');np.testing.assert_array_equal(window(t,6,'analysis'),[True,False]);np.testing.assert_array_equal(window(t,6,'future_1h'),[False,True])
 def test_stale_same_day(self):
  p,_=prediction([1],[0],params(),18,'Stale06');self.assertEqual(p[0],.9)
if __name__=='__main__':unittest.main()
