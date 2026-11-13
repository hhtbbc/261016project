import sys,unittest,tempfile,json,copy
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from training.den_engineering import (DenTrainer,DEN_INDICES,stats_policy,density_metrics,
                                     evaluate_fields,LABEL,restore_den,F)
from training.pipeline import EpochPairs,validate_disjoint,seed_all
class Tiny(torch.nn.Module):
 def __init__(self):super().__init__();self.bias=torch.nn.Parameter(torch.zeros(171))
 def forward(self,x,d):return self.bias[None,:,None,None].expand(x.shape[0],171,36,72)+x[:,:171]*.1
def cfg():return dict(optimizer=dict(name='SGD',lr=.01,momentum=0),scheduler=dict(step_size=1,gamma=1),gradient_clip_norm=1.,latitude_deg=np.linspace(-87.5,87.5,36).tolist())
class DenTests(unittest.TestCase):
 def test_den_slice(self):np.testing.assert_array_equal(DEN_INDICES,np.arange(142,171))
 def test_loss_only_den_and_real_gradient(self):
  t=DenTrainer(Tiny(),cfg());x=torch.zeros(1,177,36,72);d=torch.zeros(1,1,4);y=torch.ones(1,171,36,72);before=copy.deepcopy(t.model.state_dict());r=t.train_step((x,d,y));self.assertGreater(r['gradient_l2_before_clip'],0)
  self.assertTrue(torch.equal(before['bias'][:142],t.model.bias[:142]));self.assertFalse(torch.equal(before['bias'][142:],t.model.bias[142:]))
  poisoned=y.clone();poisoned[:,:142]=1000;torch.testing.assert_close(t.loss((x,d,y)),t.loss((x,d,poisoned)))
 def test_validation_no_gradient_or_update(self):
  t=DenTrainer(Tiny(),cfg());batch=(torch.zeros(1,177,36,72),torch.zeros(1,1,4),torch.ones(1,171,36,72));before=t.model.bias.detach().clone();t.validation_step(batch)
  self.assertTrue(torch.equal(before,t.model.bias));self.assertIsNone(t.model.bias.grad)
 def test_tiny_and_zero_variance_policy(self):
  mean=np.array([1e-15,2.,0.]);std=np.array([1e-16,0.,0.]);eff,mask=stats_policy(mean,std,abs(mean)*2)
  np.testing.assert_array_equal(mask,[False,True,True]);np.testing.assert_array_equal(eff,[1e-16,2.,1.])
 def test_physical_metrics_and_negative_prediction_retained(self):
  t=np.ones((1,2,2))*1e-12;p=t*2;r=density_metrics(p,t,[-45,45]);self.assertAlmostEqual(r['relative_RMS'],1)
  p[0,0,0]=-t[0,0,0];r=density_metrics(p,t,[-45,45]);self.assertEqual(r['n'],4);self.assertEqual(r['positive_fraction'],.75);self.assertGreater(r['relative_RMS'],1)
 def test_zero_target_rejected(self):
  with self.assertRaises(ValueError):density_metrics(np.zeros((1,2,2)),np.zeros((1,2,2)),[-5,5])
 def test_v3_checkpoint_restore_not_synthetic_label(self):
  import hashlib
  seed_all(4);a=DenTrainer(Tiny(),cfg());batch=(torch.zeros(1,177,36,72),torch.zeros(1,1,4),torch.ones(1,171,36,72));a.train_step(batch)
  with tempfile.TemporaryDirectory(dir=F) as folder:
   p=Path(folder)/'test.pt';a.save(p,dict(label=LABEL));b=DenTrainer(Tiny(),cfg());restore_den(b,p,hashlib.sha256(p.read_bytes()).hexdigest());self.assertEqual(b.step,1);self.assertTrue(torch.equal(a.model.bias,b.model.bias))
   with self.assertRaises(ValueError):restore_den(b,p,'0'*64)
 def test_statistics_fit_only_training_hashes(self):
  from training.den_engineering import DATA
  s=json.loads((F/'statistics.json').read_text());m=json.loads((F/'dataset_manifest.json').read_text())['frames']
  self.assertEqual(s['fit_frame_SHA256'],[r['SHA256'] for r in m['2021']])
  self.assertFalse(set(s['fit_frame_SHA256']) & {r['SHA256'] for r in m['2022']})
  self.assertTrue(s['validation_not_used'])
 def test_actual_dataset_contract_and_year_separation(self):
  from training.den_engineering import pairs,load_statistics
  a,b=pairs(2021),pairs(2022);validate_disjoint(a,b);self.assertEqual((len(a),len(b)),(72,48));x,d,y=a[0];self.assertEqual(tuple(x.shape),(177,36,72));self.assertEqual(tuple(y[DEN_INDICES.tolist()].shape),(29,36,72))
  with self.assertRaises(ValueError):pairs(2023)
if __name__=='__main__':unittest.main()
