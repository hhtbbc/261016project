from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
import numpy as np
from evaluation.cross_year_correction import CausalDay,frozen_transfer
from atmosphere.causal_density_correction import fit_past_A
class CrossYearTests(unittest.TestCase):
 def arrays(self,year):
  t=np.arange(np.datetime64(f'{year}-03-24T03:00'),np.datetime64(f'{year}-03-24T12:00'),np.timedelta64(30,'s')).astype('datetime64[ns]');return t,np.ones(len(t))*2,np.ones(len(t)),np.ones(len(t),bool)
 def test_2021_counts(self):
  t,*_=self.arrays(2021);m=CausalDay('2021-03-24').masks(t);self.assertEqual([m[k].sum() for k in ['analysis','future_1h','future_3h','future_6h']],[360,120,360,720])
 def test_half_open(self):
  t=np.array(['2021-03-24T03','2021-03-24T06','2021-03-24T07','2021-03-24T09','2021-03-24T12'],dtype='datetime64[ns]');m=CausalDay('2021-03-24').masks(t);self.assertEqual(m['analysis'].tolist(),[1,0,0,0,0]);self.assertEqual(m['future_6h'].tolist(),[0,1,1,1,0])
 def test_future_poison_invariant(self):
  t,o,p,q=self.arrays(2021);d=CausalDay('2021-03-24');a,_,_=d.fit(t,o,p,q,satellite='A');future=~d.masks(t)['analysis'];o[future]=1e-100;p[future]=1e100;b,_,_=d.fit(t,o,p,q,satellite='A');self.assertEqual(a,b)
 def test_matches_v10_same_year(self):
  t,o,p,q=self.arrays(2022);a,m,e=CausalDay('2022-03-24').fit(t,o,p,q,satellite='A');b,n,f=fit_past_A(t,o,p,q,satellite='A');self.assertEqual(a,b);np.testing.assert_array_equal(m,n);np.testing.assert_array_equal(e,f)
 def test_cross_year_input_not_selected(self):
  t,o,p,q=self.arrays(2022)
  with self.assertRaises(ValueError):CausalDay('2021-03-24').fit(t,o,p,q,satellite='A')
 def test_nonA_rejected(self):
  for s in ['B','C']:
   with self.assertRaises(ValueError):CausalDay('2021-03-24').fit(*self.arrays(2021),satellite=s)
 def test_transfer_unchanged(self):self.assertEqual(frozen_transfer('B14',.1261252775057784).multiplier,1.1344242772252575)
 def test_other_background_transfer_rejected(self):
  for c in ['A7','B7','A14']:
   with self.assertRaises(ValueError):frozen_transfer(c,.1261252775057784)
 def test_no_tuned_coefficient(self):
  with self.assertRaises(ValueError):frozen_transfer('B14',.12)
 def test_disjoint_incremental_windows(self):
  t,*_=self.arrays(2021);m=CausalDay('2021-03-24').masks(t);s=m['future_1h'].astype(int)+m['incremental_1_3h']+m['incremental_3_6h'];np.testing.assert_array_equal(s,m['future_6h'].astype(int))
if __name__=='__main__':unittest.main()
