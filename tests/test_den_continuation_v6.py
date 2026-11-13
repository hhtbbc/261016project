"""CPU fixtures for budget and strict checkpoint recovery; no real GPU task."""
from pathlib import Path
import sys,unittest,tempfile,copy,json,hashlib,random
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import torch,numpy as np
from training.den_continuation import ContinuationBudget,validate_continuation_plan,checkpoint_summary,audited_restore,rng_snapshot,rng_fingerprint
from training.den_engineering import DenTrainer,LABEL
from training.pipeline import seed_all
class Tiny(torch.nn.Module):
 def __init__(self):super().__init__();self.value=torch.nn.Parameter(torch.zeros(171))
 def forward(self,x,d):return self.value[None,:,None,None].expand(x.shape[0],171,36,72)
def cfg():return dict(max_train_steps=100,optimizer=dict(name='SGD',lr=.01,momentum=0),scheduler=dict(step_size=1,gamma=1),gradient_clip_norm=1.,latitude_deg=np.linspace(-87.5,87.5,36).tolist())
class ContinuationTests(unittest.TestCase):
 def test_budget_counts_only_new_updates(self):
  b=ContinuationBudget(100,100)
  for s in range(100,200):b.before_step(s);b.after_step(s+1)
  b.assert_finished(200);self.assertEqual(b.completed,100)
  with self.assertRaises(RuntimeError):b.before_step(200)
 def test_wrong_cumulative_step_and_incomplete_rejected(self):
  b=ContinuationBudget(100,100)
  with self.assertRaises(RuntimeError):b.before_step(0)
  with self.assertRaises(RuntimeError):b.after_step(102)
  with self.assertRaises(RuntimeError):b.assert_finished(200)
 def test_old_config_and_schedule_immutable(self):
  old=json.loads((ROOT/'experiments/fourcastden_den_overfit_v5/plan.json').read_text())['training_config'];p=dict(start_step=100,additional_updates=100,end_step=200,evaluation_steps=[100,150,200],validation_after_step=200,validation_indices=list(range(48)),train_pair_index=0,training_config=copy.deepcopy(old),forward_budget=dict(training=100,fixed_evaluation=3,checkpoint_restore=1,validation=48))
  self.assertTrue(validate_continuation_plan(p,old));p['training_config']['max_train_steps']=200
  with self.assertRaises(ValueError):validate_continuation_plan(p,old)
 def fixture(self,folder):
  seed_all(17);a=DenTrainer(Tiny(),cfg());batch=(torch.zeros(1,177,36,72),torch.zeros(1,1,4),torch.ones(1,171,36,72));a.train_step(batch);a.save(Path(folder)/'cpu_fixture.pt',dict(label=LABEL,tag='CPU_TEST_ONLY'));p=Path(folder)/'cpu_fixture.pt';return a,p,hashlib.sha256(p.read_bytes()).hexdigest()
 def test_exact_cpu_state_and_rng_restore(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'experiments') as folder:
   a,p,h=self.fixture(folder);expected=rng_fingerprint(rng_snapshot());b=DenTrainer(Tiny(),cfg());random.random();np.random.random();torch.rand(3);result=audited_restore(b,p,h,root=folder,expected_step=1,expected_metadata=dict(tag='CPU_TEST_ONLY'));self.assertTrue(result['PASS']);self.assertEqual(expected,rng_fingerprint(rng_snapshot()));self.assertEqual(b.config['max_train_steps'],100);self.assertTrue(torch.equal(a.model.value,b.model.value))
 def test_sha_failure_before_pickle_load(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'experiments') as folder:
   a,p,h=self.fixture(folder)
   with patch('torch.load') as load:
    with self.assertRaises(ValueError):checkpoint_summary(p,'0'*64,folder,1,dict(tag='CPU_TEST_ONLY'),cfg())
    load.assert_not_called()
 def test_metadata_and_config_mismatch_rejected(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'experiments') as folder:
   a,p,h=self.fixture(folder)
   with self.assertRaises(ValueError):checkpoint_summary(p,h,folder,1,dict(tag='WRONG'),cfg())
   changed=cfg();changed['max_train_steps']=200
   with self.assertRaises(ValueError):checkpoint_summary(p,h,folder,1,dict(tag='CPU_TEST_ONLY'),changed)
if __name__=='__main__':unittest.main()
