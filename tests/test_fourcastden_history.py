"""Actual author H=1 CPU loop with synthetic network, never a checkpoint run."""
import sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'third_party/FourCastDEN_linux'))
from fourcastden.history import history_feedback_check

class HistoryTests(unittest.TestCase):
 def run_stub(self,poison=False):
  import torch
  from inference.inference import TGCMForecast
  data=torch.empty((4,177,36,72))
  for h in range(4):data[h,:171]=h+1.;data[h,171:]=10.+h
  if poison:data[2:,:171]=9.
  sw=torch.arange(16,dtype=torch.float32).reshape(4,4)
  class Data:
   def get_data(self,indices,**kw):
    assert indices==[0,1,2,3]
    return data,sw,None,None,None
  class Net(torch.nn.Module):
   def __init__(self):super().__init__();self.ins=[];self.out=[]
   def forward(self,x,s):
    self.ins.append((x.clone().numpy(),s.clone().numpy()));y=.25*x[:,:171]+.5*x[:,177:348];self.out.append(y.clone().numpy());return y
  f=object.__new__(TGCMForecast)
  for k,v in dict(dt=1,n_prediction=2,n_history=1,img_shape_x=36,img_shape_y=72,n_in_channels=177,n_out_channels=171,device=torch.device('cpu'),means=torch.zeros((174,1,1)),stds=torch.ones((174,1,1)),time_means=torch.zeros((174,36,72)),wgt=torch.ones(36),log_to_screen=False,perturb=False,flow=False,log_DEN=False,model=Net(),dataset=Data()).items():setattr(f,k,v)
  result=f.inference(0);return result,f.model.ins,f.model.out,data.numpy(),sw.numpy()
 def test_actual_loop_input_order_and_feedback(self):
  result,ins,out,data,sw=self.run_stub();check=history_feedback_check(ins,out,data,sw);self.assertTrue(check['passed']);self.assertEqual(result[1].shape,(1,3,171,36,72))
  np.testing.assert_array_equal(out[0],1.25);np.testing.assert_array_equal(out[1],1.125)
 def test_future_truth_poison_no_prediction_change(self):
  a,*_=self.run_stub();b,*_=self.run_stub(True);np.testing.assert_array_equal(a[1],b[1]);self.assertFalse(np.array_equal(a[0],b[0]))
 def test_reversed_history_rejected(self):
  _,ins,out,data,sw=self.run_stub();bad=[(x.copy(),s.copy()) for x,s in ins];bad[0][0][:]=bad[0][0].reshape(2,177,36,72)[::-1].copy().reshape(1,354,36,72)
  with self.assertRaises(AssertionError):history_feedback_check(bad,out,data,sw)
 def test_future_auxiliary_or_scalar_shift_rejected(self):
  _,ins,out,data,sw=self.run_stub();bad=[(x.copy(),s.copy()) for x,s in ins];bad[1][0][0,171:177]+=1
  with self.assertRaises(AssertionError):history_feedback_check(bad,out,data,sw)
  bad=[(x.copy(),s.copy()) for x,s in ins];bad[1][1][:]+=1
  with self.assertRaises(AssertionError):history_feedback_check(bad,out,data,sw)
 def test_teacher_forcing_rejected(self):
  _,ins,out,data,sw=self.run_stub();bad=[(x.copy(),s.copy()) for x,s in ins];bad[1][0][0,177:348]=data[2,:171]
  with self.assertRaises(AssertionError):history_feedback_check(bad,out,data,sw)
 def test_wrong_channels_rejected(self):
  _,ins,out,data,sw=self.run_stub();ins[0]=(ins[0][0][:,:177],ins[0][1])
  with self.assertRaises(ValueError):history_feedback_check(ins,out,data,sw)
if __name__=='__main__':unittest.main()
