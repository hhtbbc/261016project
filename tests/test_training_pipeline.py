"""Synthetic CPU training contracts; no official weights or real data."""
import unittest,sys,random,copy,tempfile
from pathlib import Path
from datetime import datetime,timedelta,timezone
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from training.pipeline import DirectTrainer,EpochPairs,validate_disjoint,AffineNormalizer,seed_all,synthetic_batch,LABEL
class Tiny(torch.nn.Module):
 def __init__(self):super().__init__();self.scale=torch.nn.Parameter(torch.tensor(.2));self.bias=torch.nn.Parameter(torch.zeros(171))
 def forward(self,x,s):return self.scale*x[:,:171]+self.bias[None,:,None,None]+s[:,:,:1].reshape(-1,1,1,1)*.01

def cfg():return dict(optimizer=dict(name='SGD',lr=.01,momentum=.9),scheduler=dict(step_size=1,gamma=.99),gradient_clip_norm=1.)
def times(year,n=3):return [datetime(year,1,4,tzinfo=timezone.utc)+timedelta(hours=h) for h in range(n)]
def source(t):
 return torch.full((171,36,72),float(t.hour)),torch.full((6,36,72),float(t.hour+100)),torch.arange(4,dtype=torch.float32)
class TrainingTests(unittest.TestCase):
 def test_shapes_backward_updates_and_validation_no_update(self):
  seed_all(12);t=DirectTrainer(Tiny(),cfg());batch=synthetic_batch(1);before=t.model.scale.clone();r=t.train_step(batch);self.assertGreater(r['gradient_l2_before_clip'],0);self.assertNotEqual(before.item(),t.model.scale.item());state=copy.deepcopy(t.model.state_dict());self.assertTrue(np.isfinite(t.validation_step(batch)));self.assertEqual(t.step,1)
  for k in state:torch.testing.assert_close(state[k],t.model.state_dict()[k],rtol=0,atol=0)
 def test_resume_exact_optimizer_scheduler_rng_and_continuation(self):
  seed_all(4);a=DirectTrainer(Tiny(),cfg());batch=synthetic_batch(5);a.train_step(batch)
  with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as folder:
   p=Path(folder)/'cpu.pt';a.save(p,dict(label=LABEL));expected=(random.random(),np.random.rand(),torch.rand(3));a.train_step(batch);end=copy.deepcopy(a.model.state_dict());optimizer=copy.deepcopy(a.optimizer.state_dict())
   b=DirectTrainer(Tiny(),cfg());b.restore(p,trusted_local=True);self.assertEqual(b.step,1);got=(random.random(),np.random.rand(),torch.rand(3));self.assertEqual(expected[0],got[0]);self.assertEqual(expected[1],got[1]);torch.testing.assert_close(expected[2],got[2],rtol=0,atol=0);b.train_step(batch)
   for k in end:torch.testing.assert_close(end[k],b.model.state_dict()[k],rtol=0,atol=0)
   torch.testing.assert_close(optimizer['state'][0]['momentum_buffer'],b.optimizer.state_dict()['state'][0]['momentum_buffer'],rtol=0,atol=0);self.assertEqual(a.scheduler.state_dict(),b.scheduler.state_dict())
 def test_repeat_seed_reproduces_updates(self):
  results=[]
  for _ in range(2):seed_all(9);t=DirectTrainer(Tiny(),cfg());results.append(t.train_step(synthetic_batch(9)))
  self.assertEqual(results[0],results[1])
 def test_future_physical_truth_not_input(self):
  d=EpochPairs(times(2021),source,'train');x,s,y=d[0]
  def poison(t):
   state,aux,scalar=source(t);return (state+99 if t.hour==1 else state),aux,scalar
  xp,sp,yp=EpochPairs(times(2021),poison,'train')[0];torch.testing.assert_close(x,xp);torch.testing.assert_close(s,sp);self.assertFalse(torch.equal(y,yp));self.assertEqual(x[171,0,0],101)
 def test_test_year_cross_year_missing_duplicates_and_timezone_rejected(self):
  for epoch,split in [(times(2023),'train'),(times(2023),'validation'),(times(2022),'train'),([times(2021)[0],times(2021)[2]],'train'),([times(2021)[0]]*2,'train'),([datetime(2021,12,31,23,tzinfo=timezone.utc),datetime(2022,1,1,tzinfo=timezone.utc)],'train'),([datetime(2021,1,4),datetime(2021,1,4,1)],'train')]:
   with self.subTest(epoch=epoch,split=split),self.assertRaises(ValueError):EpochPairs(epoch,source,split)
 def test_disjoint_splits(self):
  a=EpochPairs(times(2021),source,'train');b=EpochPairs(times(2022),source,'validation');validate_disjoint(a,b)
  with self.assertRaises(ValueError):validate_disjoint(a,a)
 def test_affine_roundtrip_and_bad_stats(self):
  norm=AffineNormalizer(np.ones((174,1,1)),np.full((174,1,1),2));raw=np.full((174,36,72),5.);np.testing.assert_array_equal(norm.decode(norm.encode(raw)),raw)
  with self.assertRaises(ValueError):AffineNormalizer(norm.means,np.zeros_like(norm.stds))
 def test_bad_batch_and_untrusted_checkpoint_fail(self):
  t=DirectTrainer(Tiny(),cfg());x,s,y=synthetic_batch(1)
  with self.assertRaises(ValueError):t.train_step((x[:,:170],s,y))
  x[0,0,0,0]=float('nan')
  with self.assertRaises(ValueError):t.train_step((x,s,y))
  with self.assertRaises(ValueError):t.restore(ROOT/'models/checkpoints/author/Direct_ckpt.tar')
if __name__=='__main__':unittest.main()
