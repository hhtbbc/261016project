"""Synthetic time and diagnostic-only pairing tests; never train or instantiate a model."""
import unittest,sys
from pathlib import Path
from datetime import datetime,timedelta,timezone
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from training.readonly_interface import inspect_pair
from training.pipeline import EpochPairs,validate_disjoint

def source(t):return torch.full((171,36,72),float(t.hour)),torch.full((6,36,72),float(100+t.hour)),torch.arange(4,dtype=torch.float32)
def epochs(y):return [datetime(y,4,5,h,tzinfo=timezone.utc) for h in [0,1]]
def run_pair(a,b,source_fn=source,**kw):
 st,_,_=source_fn(a);tar,aux,sc=source_fn(b);return inspect_pair(source_fn,a,b,torch.cat((st,aux))[None],sc.reshape(1,1,4),tar[None],current_split=kw.get('current_split','test_readonly'),target_split=kw.get('target_split','test_readonly'))
class ReadOnlyTests(unittest.TestCase):
 def test_real_year_allowed_only_diagnostic_and_no_tensors_returned(self):
  r=run_pair(*epochs(2023));self.assertTrue(r['exact']);self.assertEqual(r['input_shape'],[1,177,36,72]);self.assertFalse(any(torch.is_tensor(x) for x in r.values()))
 def test_future_state_poison_changes_target_only(self):
  a,b=epochs(2023);r=run_pair(a,b)
  def poison(t):
   state,aux,s=source(t);return (state+9 if t==b else state),aux,s
  q=run_pair(a,b,poison);self.assertEqual(r['input_SHA256'],q['input_SHA256']);self.assertNotEqual(r['target_SHA256'],q['target_SHA256'])
 def test_gap_duplicate_cross_year_reject(self):
  a,b=epochs(2021)
  for t,u in [(a,a),(a,b+timedelta(hours=1)),(datetime(2021,12,31,23,tzinfo=timezone.utc),datetime(2022,1,1,tzinfo=timezone.utc))]:
   with self.assertRaises(ValueError):run_pair(t,u)
 def test_split_boundary_reject(self):
  with self.assertRaises(ValueError):run_pair(*epochs(2021),current_split='train',target_split='validation')
 def test_nonUTC_and_naive_reject(self):
  a,b=epochs(2021)
  for ts in [(a.replace(tzinfo=None),b.replace(tzinfo=None)),(a.astimezone(timezone(timedelta(hours=2))),b.astimezone(timezone(timedelta(hours=2))))]:
   with self.assertRaises(ValueError):run_pair(*ts)
 def test_every_training_year_and_validation_year(self):
  for year in range(2000,2022):self.assertEqual(len(EpochPairs(epochs(year),source,'train')),1)
  validate_disjoint(EpochPairs(epochs(2021),source,'train'),EpochPairs(epochs(2022),source,'validation'))
 def test_2023_training_validation_guard_unchanged(self):
  for split in ['train','validation']:
   with self.assertRaises(ValueError):EpochPairs(epochs(2023),source,split)
 def test_nan_and_wrong_channel_reject(self):
  a,b=epochs(2023)
  def invalid(t):
   st,aux,s=source(t);st[0,0,0]=float('nan');return st,aux,s
  with self.assertRaises(ValueError):run_pair(a,b,invalid)
  st,aux,s=source(b)
  with self.assertRaises(AssertionError):inspect_pair(source,a,b,torch.zeros(1,170,36,72),s,st,current_split='x',target_split='x')
if __name__=='__main__':unittest.main()
