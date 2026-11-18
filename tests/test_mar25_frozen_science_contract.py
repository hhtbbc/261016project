"""Synthetic-only exercise of unchanged frozen operators; no real date fit or scores."""
from pathlib import Path
import sys,unittest,json,hashlib,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
import numpy as np
from evaluation.causal_density_latitude import fit_history,fit_global_history,apply_global,apply_latitude,supported_metric,assess_joint,exclusive_json
from evaluation.late_day_correction import RollingOrigin
from evaluation.swarm_crossyear import metric_row
BASE=ROOT/'experiments/tiegcm_2022_mar25_execution_review_v1/tests_local'
class FrozenScience(unittest.TestCase):
 def data(self):
  t=np.arange(np.datetime64('2022-03-25T00'),np.datetime64('2022-03-26T00'),np.timedelta64(30,'s'));lat=np.tile([0.,30.,60.],960);p=np.full(2880,1e-12);obs=p*(1.1+.01*np.sin(np.arange(2880)));q=np.ones(2880,bool);return t,lat,obs,p,q
 def test_protocol_fixed(self):
  f=ROOT/'experiments/tiegcm_2022_mar25_preparation_v1';m=json.loads((f/'sha256_manifest.json').read_text());p=f/'frozen_evaluation_protocol.json';self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),m[str(p.relative_to(ROOT))]);x=json.loads(p.read_text());self.assertEqual(x['cutoffs'],[6,18]);self.assertEqual(x['history_hours'],3);self.assertEqual(x['future_hours'],[1,3,6]);self.assertEqual(x['min_history_and_future_region_N'],30);self.assertTrue(x['no_fallback'])
 def test_half_open_and_nonoverlap(self):
  t,*_=self.data()
  for hour in [6,18]:
   m=RollingOrigin('2022-03-25',hour).masks(t);self.assertEqual(m['analysis'].sum(),360)
   for h in [1,3,6]:self.assertEqual(m[f'future_{h}h'].sum(),h*120);self.assertFalse((m['analysis']&m[f'future_{h}h']).any())
   self.assertFalse((m['future_1h']&m['block_1_3h']).any());self.assertFalse((m['block_1_3h']&m['block_3_6h']).any())
 def test_freeze_poison_then_shared_domain_scoring(self):
  t,lat,o,p,q=self.data();g06,_=fit_global_history(t,lat,o,p,q,day='2022-03-25',hour=6);g18,_=fit_history(t,lat,o,p,q,day='2022-03-25',hour=18)
  with tempfile.TemporaryDirectory(dir=BASE) as td:
   path=Path(td)/'synthetic_params.json';exclusive_json(path,dict(identity='SIMULATED_TEST_ONLY',g06=g06,g18=g18));frozen=path.read_bytes()
   for hour in [6,18]:
    z=o.copy();z[t>=np.datetime64(f'2022-03-25T{hour:02d}')]*=1e20
    if hour==6:new,_=fit_global_history(t,lat,z,p,q,day='2022-03-25',hour=hour);self.assertEqual(new,g06)
    else:new,_=fit_history(t,lat,z,p,q,day='2022-03-25',hour=hour);self.assertEqual(new,g18)
   self.assertEqual(path.read_bytes(),frozen)
   # All methods receive the exact same predeclared sample IDs, never separate masks.
   common=RollingOrigin('2022-03-25',18).masks(t)['future_6h']&q;local,support=apply_latitude(p,lat,g18['latitude']);preds=[p,apply_global(p,g18['global_fit']),local,apply_global(p,g06)]
   ns=[supported_metric(pred,o,q,common,np.ones(2880,bool),support)['n'] for pred in preds];self.assertEqual(ns,[720]*4)
 def test_invalid_selected_sample_never_silently_dropped(self):
  for val in [np.nan,np.inf,0.,-1.]:
   p=np.ones(40);p[0]=val
   with self.assertRaises(ValueError):metric_row(p,np.ones(40),np.ones(40,bool),np.ones(40,bool),np.ones(40,bool))
 def test_NA_cannot_pass_joint(self):
  o=dict(status='OK',RMSE=1.,relative_RMS=.1,relative_P95=.1,relative_bias=0.);r={k:o for k in ['low','mid','high']};z=dict(r,low=dict(status='N/A_INSUFFICIENT_SAMPLES'));self.assertNotEqual(assess_joint(o,o,r,z)['JOINT_NO_REGRET'],'PASS')
if __name__=='__main__':unittest.main()
