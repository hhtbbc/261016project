from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
import numpy as np
from evaluation.late_day_correction import RollingOrigin,diagnostic_quintiles,joint_flags
from evaluation.cross_year_correction import CausalDay
class LateTests(unittest.TestCase):
 def data(self,year=2021,hour=18):
  start=np.datetime64(f'{year}-03-24T{hour-3:02d}');t=np.arange(start,start+np.timedelta64(9,'h'),np.timedelta64(30,'s')).astype('datetime64[ns]');return t,np.full(len(t),2.),np.ones(len(t)),np.ones(len(t),bool)
 def test_counts_and_midnight(self):
  for y in [2021,2022]:
   t,*_=self.data(y);m=RollingOrigin(f'{y}-03-24').masks(t);self.assertEqual([m[k].sum() for k in ['analysis','future_1h','future_3h','future_6h']],[360,120,360,720]);self.assertEqual(str(t[-1]),f'{y}-03-24T23:59:30.000000000')
 def test_cutoff_and_nextday_excluded(self):
  t=np.array(['2021-03-24T15','2021-03-24T18','2021-03-25T00'],dtype='datetime64[ns]');m=RollingOrigin('2021-03-24').masks(t);self.assertEqual(m['analysis'].tolist(),[1,0,0]);self.assertEqual(m['future_6h'].tolist(),[0,1,0])
 def test_future_poison(self):
  t,o,p,q=self.data();w=RollingOrigin('2021-03-24');a,_,_=w.fit(t,o,p,q,satellite='A');o[360:]=1e30;p[360:]=1e-30;b,_,_=w.fit(t,o,p,q,satellite='A');self.assertEqual(a,b)
 def test_no_B_C_fit(self):
  for s in ['B','C']:
   with self.assertRaises(ValueError):RollingOrigin('2021-03-24').fit(*self.data(),satellite=s)
 def test_06_compatibility(self):
  t,o,p,q=self.data(hour=6);a,m,e=RollingOrigin('2021-03-24',6).fit(t,o,p,q,satellite='A');b,n,f=CausalDay('2021-03-24').fit(t,o,p,q,satellite='A');self.assertEqual(a,b);np.testing.assert_array_equal(m,n)
 def test_quintile_contributions(self):
  y=np.arange(1,101,dtype=float);p=y*1.1;i,e=diagnostic_quintiles(y);self.assertEqual(np.bincount(i).tolist(),[20]*5);self.assertAlmostEqual(sum(np.sum((p[i==k]-y[i==k])**2) for k in range(5)),np.sum((p-y)**2),10)
 def test_weight_identity(self):
  y=np.array([1.,2.,100.]);p=np.array([2.,1.,99.]);rel=p/y-1;np.testing.assert_allclose(np.mean((p-y)**2),np.mean(y*y*rel*rel),rtol=1e-14,atol=0)
 def test_ties_not_jittered(self):
  i,e=diagnostic_quintiles(np.ones(30));self.assertEqual(len(np.unique(i)),1)
 def test_joint_no_regret(self):
  raw=dict(status='OK',RMSE=2.,relative_RMS=.2,relative_P95=.4,relative_bias=-.1);corr=dict(status='OK',RMSE=1.,relative_RMS=.1,relative_P95=.4,relative_bias=.05);self.assertTrue(joint_flags(raw,corr,raw,corr)['JOINT_NO_REGRET']);corr['relative_RMS']=.3;self.assertFalse(joint_flags(raw,corr,raw,corr)['JOINT_NO_REGRET'])
 def test_low_bias_uses_absolute_value(self):
  a=dict(status='OK',RMSE=2.,relative_RMS=.2,relative_P95=.4,relative_bias=-.01);b=dict(status='OK',RMSE=1.,relative_RMS=.1,relative_P95=.3,relative_bias=.02);self.assertFalse(joint_flags(a,b,a,b)['LOW_LATITUDE_BIAS_NONWORSENED'])
 def test_insufficient_not_pass(self):
  a=dict(status='N/A_INSUFFICIENT_SAMPLES');self.assertFalse(joint_flags(a,a,a,a)['JOINT_NO_REGRET'])
if __name__=='__main__':unittest.main()
