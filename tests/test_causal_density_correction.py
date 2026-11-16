"""Synthetic causal estimator and real nine-probe evidence checks."""
import unittest,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
import numpy as np
from atmosphere.causal_density_correction import fit_past_A,LogMedianCorrection
class TestCorrection(unittest.TestCase):
 def data(self):return np.array(['2022-03-24T03','2022-03-24T04','2022-03-24T05','2022-03-24T06','2022-03-24T07'],dtype='datetime64[ns]'),np.array([2.,2.,200.,100.,100.]),np.ones(5),np.ones(5,bool)
 def test_median_and_future_poison(self):
  t,o,p,q=self.data();a,m,_=fit_past_A(t,o,p,q,satellite='A');self.assertAlmostEqual(a.multiplier,2);o[3:]=1e100;p[3:]=1e-100;b,_,_=fit_past_A(t,o,p,q,satellite='A');self.assertEqual(a,b);self.assertEqual(m.tolist(),[1,1,1,0,0])
 def test_C_and_B_cannot_fit(self):
  for s in ['B','C']:
   with self.assertRaises(ValueError):fit_past_A(*self.data(),satellite=s)
 def test_empty_past_rejected(self):
  t,o,p,q=self.data();q[:3]=False
  with self.assertRaises(ValueError):fit_past_A(t,o,p,q,satellite='A')
 def test_invalid_never_filled(self):
  for p in [[0],[-1],[np.nan],[np.inf]]:
   with self.assertRaises(ValueError):LogMedianCorrection(.1,1).apply(p)
 def test_no_mutation(self):
  p=np.array([1.,2.]);before=p.copy();np.testing.assert_array_equal(LogMedianCorrection(np.log(2),3).apply(p),[2,4]);np.testing.assert_array_equal(p,before)
 def test_existing_nine_CDF_checks(self):
  d=json.loads((ROOT/'experiments/causal_density_correction_v1/operator_independent_probes.json').read_text());self.assertEqual(len(d['CDF_checks']),9);self.assertTrue(all(x['PASS'] for x in d['CDF_checks']));self.assertEqual(len(d['interpolation_reconstructions']),24)
if __name__=='__main__':unittest.main()
