from pathlib import Path
import sys,unittest,tempfile,json
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
import numpy as np
from evaluation.causal_density_latitude import latitude_band,fit_history,apply_global,apply_latitude,assess_joint,exclusive_json,fit_global_history,supported_metric
from evaluation.late_day_correction import RollingOrigin
class LatitudeTests(unittest.TestCase):
 def data(self,n=30):
  t=np.arange(np.datetime64('2021-03-23T15'),np.datetime64('2021-03-23T18'),np.timedelta64(30,'s'));lat=np.tile([0.,30.,60.],120);o=np.full(360,2.);p=np.ones(360);q=np.ones(360,bool);return t,lat,o,p,q
 def test_boundaries_and_negative_latitudes(self):np.testing.assert_array_equal(latitude_band([-90,-60,-30,-29.99,0,29.99,30,59.99,60,90]),[2,2,1,0,0,0,1,1,2,2])
 def test_29_unsupported_no_borrow(self):
  t,lat,o,p,q=self.data();q[lat==0]=False;q[np.flatnonzero(lat==0)[:29]]=True;c,_=fit_history(t,lat,o,p,q,day='2021-03-23');self.assertEqual(c['latitude']['low']['N'],29);self.assertIsNone(c['latitude']['low']['b']);pred,s=apply_latitude([1.,1.],[0.,30.],c['latitude']);self.assertTrue(np.isnan(pred[0]));self.assertFalse(s[0]);self.assertEqual(pred[1],2.)
 def test_30_supported(self):
  t,lat,o,p,q=self.data();q[lat==0]=False;q[np.flatnonzero(lat==0)[:30]]=True;c,_=fit_history(t,lat,o,p,q,day='2021-03-23');self.assertEqual(c['latitude']['low']['N'],30);self.assertEqual(c['latitude']['low']['status'],'SUPPORTED')
 def test_invalid_density_rejected(self):
  for val in [np.nan,np.inf,0.,-1.]:
   for which in ['obs','model']:
    t,lat,o,p,q=self.data();(o if which=='obs' else p)[0]=val
    with self.assertRaises(ValueError):fit_history(t,lat,o,p,q,day='2021-03-23')
 def test_invalid_application_rejected(self):
  c,_=fit_history(*self.data(),day='2021-03-23')
  for x in [np.nan,np.inf,0.,-1.]:
   with self.assertRaises(ValueError):apply_latitude([x],[0.],c['latitude'])
 def test_future_poison_global_local_and_Stale(self):
  for hour in [6,18]:
   t,lat,o,p,q=self.data();t=t+np.timedelta64(hour-18,'h');t=np.r_[t,t[-1]+np.timedelta64(30,'s')];lat=np.r_[lat,0];o=np.r_[o,1];p=np.r_[p,1];q=np.r_[q,True];a,_=fit_history(t,lat,o,p,q,day='2021-03-23',hour=hour);o[-1]*=1e20;b,_=fit_history(t,lat,o,p,q,day='2021-03-23',hour=hour);self.assertEqual(a,b)
 def test_matches_global_baseline(self):
  t,lat,o,p,q=self.data();a,_=fit_history(t,lat,o,p,q,day='2021-03-23');b,_,_=RollingOrigin('2021-03-23').fit(t,o,p,q,satellite='A');self.assertEqual(a['global_fit']['b'],b.log_bias)
 def test_future_own_region_used(self):
  t,lat,o,p,q=self.data();o[lat==0]=2;o[lat==30]=3;o[lat==60]=4;c,_=fit_history(t,lat,o,p,q,day='2021-03-23');pred,s=apply_latitude([1,1,1],[-60,-30,0],c['latitude']);np.testing.assert_allclose(pred,[4,3,2],rtol=1e-15);self.assertTrue(s.all())
 def test_global_only_stale_and_unsupported_full_score(self):
  t,lat,o,p,q=self.data();t=t-np.timedelta64(12,'h');g,m=fit_global_history(t,lat,o,p,q,day='2021-03-23');self.assertEqual(g['N'],360);self.assertEqual(g['b'],float(np.log(2.)))
  pred=np.r_[np.full(39,2.),np.nan];score=supported_metric(pred,np.ones(40),np.ones(40,bool),np.ones(40,bool),np.ones(40,bool),np.r_[np.ones(39,bool),False]);self.assertTrue(score['status'].startswith('N/A'));self.assertIsNone(score['RMSE']);self.assertEqual(score['n'],40);self.assertEqual(score['n_supported'],39)
 def test_nonA_rejected(self):
  for s in ['B','C']:
   with self.assertRaises(ValueError):fit_history(*self.data(),day='2021-03-23',satellite=s)
 def test_nonfinite_latitude_rejected(self):
  for x in [np.nan,np.inf,91.]:
   with self.assertRaises(ValueError):latitude_band([x])
 def test_no_overwrite(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'.tmp') as td:
   p=Path(td)/'record.json';exclusive_json(p,{'one':1})
   with self.assertRaises(FileExistsError):exclusive_json(p,{'two':2})
   self.assertEqual(json.loads(p.read_text()),{'one':1})
 def test_future_region_NA_cannot_pass(self):
  ok=dict(status='OK',RMSE=2.,relative_RMS=.2,relative_P95=.3,relative_bias=.1);bad=dict(status='N/A_INSUFFICIENT_SAMPLES');raw={k:ok for k in ['low','mid','high']};new=dict(raw,high=bad);self.assertEqual(assess_joint(ok,ok,raw,new)['JOINT_NO_REGRET'],'N/A_INSUFFICIENT_SAMPLES')
 def test_missing_support_cannot_pass(self):
  ok=dict(status='OK',RMSE=2.,relative_RMS=.2,relative_P95=.3,relative_bias=.1);rr={k:ok for k in ['low','mid','high']};self.assertEqual(assess_joint(ok,ok,rr,rr,False)['JOINT_NO_REGRET'],'N/A_INSUFFICIENT_SAMPLES')
if __name__=='__main__':unittest.main()
