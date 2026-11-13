"""Bounded policy and real fixed-pair CPU contracts, without a GPU/model run."""
import sys,unittest,json,copy,os,subprocess
from pathlib import Path
import numpy as np,torch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from training.den_overfit import validate_overfit_plan,array_sha
from training.den_engineering import pairs,DEN_INDICES,load_statistics
from training.pipeline import EpochPairs
class OverfitPolicy(unittest.TestCase):
 def plan(self):
  cfg=json.loads((ROOT/'experiments/fourcastden_den_gpu_smoke_v4/plan.json').read_text())['training_config'];cfg['max_train_steps']=100
  return dict(train_pair_index=0,updates=100,evaluation_steps=[0,10,50,100],validation_after_step=100,validation_indices=list(range(48)),training_config=cfg,forward_budget=dict(training=100,fixed_evaluation=4,checkpoint_restore=1,validation=48))
 def test_fixed_plan_rejects_adaptive_changes(self):
  p=self.plan();self.assertTrue(validate_overfit_plan(p))
  for k,v in [('train_pair_index',1),('updates',101),('validation_after_step',50),('evaluation_steps',[0,10,100]),('validation_indices',[0])]:
   q=copy.deepcopy(p);q[k]=v
   with self.assertRaises(ValueError):validate_overfit_plan(q)
 def test_optimizer_and_forward_budget_frozen(self):
  p=self.plan();p['training_config']['optimizer']['lr']=2e-4
  with self.assertRaises(ValueError):validate_overfit_plan(p)
  p=self.plan();p['forward_budget']['training']=101
  with self.assertRaises(ValueError):validate_overfit_plan(p)
 def test_actual_fixed_pair_repeat_exact(self):
  ds=pairs(2021);a=ds[0];b=ds[0];self.assertEqual(ds.epochs[0].isoformat(),'2021-03-23T00:00:00+00:00');self.assertEqual(ds.epochs[1].isoformat(),'2021-03-23T01:00:00+00:00')
  self.assertEqual([array_sha(x) for x in a],[array_sha(x) for x in b]);self.assertEqual(tuple(a[0].shape),(177,36,72));self.assertEqual(tuple(a[2][DEN_INDICES.tolist()].shape),(29,36,72))
 def test_fixed_future_truth_poison(self):
  ds=pairs(2021);a=ds[0];target=ds.epochs[1]
  def poison(t):
   s,d,e=ds.source(t);return s+1234 if t==target else s,d,e
  b=EpochPairs(ds.epochs,poison,'train')[0];torch.testing.assert_close(a[0],b[0],rtol=0,atol=0);torch.testing.assert_close(a[1],b[1],rtol=0,atol=0);self.assertFalse(torch.equal(a[2],b[2]))
 def test_entry_import_device_visibility_unchanged(self):
  subprocess.run([sys.executable,'-c',"import sys,os;sys.path[:0]=['src','scripts'];os.environ['CUDA_VISIBLE_DEVICES']='7';import train_den_overfit_v5;assert os.environ['CUDA_VISIBLE_DEVICES']=='7'"],cwd=ROOT,env=dict(os.environ),check=True,timeout=20)
if __name__=='__main__':unittest.main()
