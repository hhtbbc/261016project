"""CPU safeguards for v7 eval-mode resume and independent520-update v8 budget."""
from pathlib import Path
import sys,json,unittest,copy
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import torch
from training.den_multisample_continuation import additional_order,validate_plan,SOURCE_SHA256
from training.den_continuation import ContinuationBudget,rng_snapshot,rng_fingerprint
from training.den_engineering import DenTrainer
class Tiny(torch.nn.Module):
 def __init__(self):super().__init__();self.p=torch.nn.Parameter(torch.zeros(171));self.forward_modes=[]
 def forward(self,x,d):self.forward_modes.append(self.training);return self.p[None,:,None,None].expand(x.shape[0],171,36,72)
class ResumeTests(unittest.TestCase):
 def plan(self):
  p7=json.loads((ROOT/'experiments/fourcastden_den_multisample_v7/plan.json').read_text())
  return dict(training_config=p7['training_config'],start_step=200,additional_updates=520,end_step=720,train_order=additional_order(),cumulative_exposure_counts=[10]*72,source_checkpoint='experiments/fourcastden_den_multisample_v7/step200.pt',source_checkpoint_SHA256=SOURCE_SHA256,forward_budget=dict(initial_restore=1,training=520,train_evaluation=72,validation=48,checkpoint_restore=1),evaluation_after_step=720,validation_after_step=720,train_evaluation_indices=list(range(72)),validation_indices=list(range(48)),source_model_training=False,restore_array_rtol=0,restore_array_atol=0)
 def test_schedule_resumes_pair56_and_ten_visits(self):
  a=additional_order();self.assertEqual(a[:16],list(range(56,72)));self.assertEqual(a[-72:],list(range(72)));self.assertEqual(len(a),520);allorder=[i%72 for i in range(200)]+a;self.assertEqual([allorder.count(i) for i in range(72)],[10]*72)
 def test_original_config_exact(self):
  p=self.plan();self.assertTrue(validate_plan(p,p['training_config']));q=copy.deepcopy(p);q['training_config']['max_train_steps']=720
  with self.assertRaises(ValueError):validate_plan(q,p['training_config'])
 def test_reject_v6_or_source_SHA(self):
  for key,value in [('source_checkpoint','experiments/fourcastden_den_overfit_continuation_v6/step200.pt'),('source_checkpoint_SHA256','0'*64)]:
   q=self.plan();q[key]=value
   with self.assertRaises(ValueError):validate_plan(q)
 def test_reject_budget_or_intermediate_validation(self):
  for key,value in [('additional_updates',521),('validation_after_step',500),('source_model_training',True),('restore_array_rtol',1e-6)]:
   q=self.plan();q[key]=value
   with self.assertRaises(ValueError):validate_plan(q)
 def test_exact642_forward_budget(self):
  p=self.plan();self.assertEqual(sum(p['forward_budget'].values()),642);p['forward_budget']['initial_restore']=2
  with self.assertRaises(ValueError):validate_plan(p)
 def test_optimizer_budget_rejects721(self):
  b=ContinuationBudget(200,520)
  for i in range(200,720):b.before_step(i);b.after_step(i+1)
  b.assert_finished(720)
  with self.assertRaises(RuntimeError):b.before_step(720)
 def test_eval_probe_preserves_state_and_RNG(self):
  m=Tiny().eval();before=m.p.detach().clone();rng=rng_fingerprint(rng_snapshot())
  with torch.no_grad():m(torch.zeros(1,177,36,72),torch.zeros(1,1,4))
  self.assertFalse(m.training);self.assertTrue(torch.equal(before,m.p));self.assertEqual(rng,rng_fingerprint(rng_snapshot()));self.assertIsNone(m.p.grad)
 def test_train_step_switches_restored_eval_to_train(self):
  t=DenTrainer(Tiny().eval(),self.plan()['training_config']);t.step=200;before=t.model.p.detach().clone();r=t.train_step((torch.zeros(1,177,36,72),torch.zeros(1,1,4),torch.ones(1,171,36,72)));self.assertTrue(t.model.training);self.assertEqual(t.model.forward_modes,[True]);self.assertEqual(r['step'],201);self.assertFalse(torch.equal(before,t.model.p));self.assertEqual(t.config['max_train_steps'],200)
if __name__=='__main__':unittest.main()
