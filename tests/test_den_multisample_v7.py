"""CPU-only v7 schedule, safety, and validation contract tests."""
from pathlib import Path
import sys,json,copy,unittest,tempfile
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import torch,numpy as np
from training.den_multisample import cyclic_indices,exposure_counts,require_initial_hash,require_gpu_budget,validate_multisample_plan,INITIAL_MODEL_SHA256
from training.den_continuation import ContinuationBudget
from training.den_engineering import DenTrainer
from training.pipeline import EpochPairs
from runtime.supervisor import Limits,limit_reason
from train_den_gpu_smoke_v4 import dump
class Tiny(torch.nn.Module):
 def __init__(self):super().__init__();self.p=torch.nn.Parameter(torch.zeros(171))
 def forward(self,x,d):return self.p[None,:,None,None].expand(x.shape[0],171,36,72)
class MultiTests(unittest.TestCase):
 def plan(self):
  cfg=json.loads((ROOT/'experiments/fourcastden_den_overfit_v5/plan.json').read_text())['training_config'];cfg['max_train_steps']=200
  return dict(training_config=cfg,updates=200,train_order=cyclic_indices(),exposure_counts=exposure_counts(cyclic_indices()),forward_budget=dict(training=200,train_evaluation=72,validation=48,checkpoint_restore=1),validation_after_step=200,validation_indices=list(range(48)),train_evaluation_indices=list(range(72)),initial_model_SHA256=INITIAL_MODEL_SHA256,loss_trend=dict(type='trailing_arithmetic_mean',window=24,min_periods=24,descriptive_only=True))
 def test_exact_frozen_schedule(self):
  a=cyclic_indices();self.assertEqual(a[:72],list(range(72)));self.assertEqual(a[72:144],list(range(72)));self.assertEqual(a[144:],list(range(56)))
 def test_exposures_and_no216_update_extension(self):self.assertEqual(exposure_counts(cyclic_indices()),[3]*56+[2]*16);self.assertEqual(len(cyclic_indices()),200)
 def test_plan_rejects_modified_order_or_budget(self):
  p=self.plan();self.assertTrue(validate_multisample_plan(p))
  for k,v in [('updates',216),('train_order',list(reversed(p['train_order']))),('validation_after_step',100),('train_evaluation_indices',[0])]:
   q=copy.deepcopy(p);q[k]=v
   with self.assertRaises(ValueError):validate_multisample_plan(q)
 def test_initial_hash_guard(self):
  require_initial_hash(INITIAL_MODEL_SHA256)
  with self.assertRaises(RuntimeError):require_initial_hash('0'*64)
 def test_maximum_200_updates(self):
  b=ContinuationBudget(0,200)
  for i in range(200):b.before_step(i);b.after_step(i+1)
  b.assert_finished(200)
  with self.assertRaises(RuntimeError):b.before_step(200)
 def test_2022_not_a_training_split(self):
  times=[datetime(2022,3,23,tzinfo=timezone.utc)+timedelta(hours=i) for i in range(2)]
  with self.assertRaises(ValueError):EpochPairs(times,lambda _:None,'train')
 def test_validation_cannot_backward_or_update(self):
  cfg=self.plan()['training_config'];t=DenTrainer(Tiny(),cfg);b=(torch.zeros(1,177,36,72),torch.zeros(1,1,4),torch.ones(1,171,36,72));before=t.model.p.detach().clone()
  with patch.object(torch.Tensor,'backward',side_effect=AssertionError('No validation backward')),patch.object(t.optimizer,'step',side_effect=AssertionError('No validation optimizer')):value=t.validation_step(b)
  self.assertTrue(np.isfinite(value));self.assertTrue(torch.equal(before,t.model.p));self.assertIsNone(t.model.p.grad);self.assertEqual(t.step,0)
 def test_exclusive_launch_marker(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'experiments') as folder:
   p=Path(folder)/'launch.json';dump(p,dict(tasks=1))
   with self.assertRaises(FileExistsError):dump(p,dict(tasks=2))
 def test_mock_memory_disk_output_limits(self):
  limits=Limits(300,8*2**30,20*2**30,2*2**30,2*2**30);snap=dict(rss_bytes=1,free_disk_bytes=30*2**30,output_bytes=1,largest_volume_bytes=0,total_output_bytes=None);self.assertIsNone(limit_reason(snap,limits))
  for key,value in [('rss_bytes',9*2**30),('free_disk_bytes',19*2**30),('output_bytes',3*2**30)]:
   q=dict(snap);q[key]=value;self.assertIsNotNone(limit_reason(q,limits))
  require_gpu_budget(20*2**30)
  with self.assertRaises(MemoryError):require_gpu_budget(20*2**30+1)
if __name__=='__main__':unittest.main()
