"""Actual official six-step CPU loop with synthetic network and poison tests."""
import sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'third_party/FourCastDEN_linux'))
from fourcastden.autoregression import check_autoregression
from fourcastden.logden import load_overlay,MetricTrace
class SixHourTests(unittest.TestCase):
 def stub(self,history=0,flow=False,log=False,poison=False,length=6):
  import torch
  if log:module=load_overlay(ROOT/'experiments/fourcastden_logden_multidate_v1/inference_overlay.py')
  else:import inference.inference as module
  data=torch.empty((length+history+1,177,36,72))
  for k in range(len(data)):data[k,:171]=1+k*.1;data[k,171:]=.1*k
  if poison:data[history+1:,:171]=9.
  sw=torch.arange(len(data)*4,dtype=torch.float32).reshape(-1,4)
  class Dataset:
   def get_data(self,indices,**kwargs):
    assert indices==list(range(len(data)));return data,sw,None,None,None
  class Network(torch.nn.Module):
   def __init__(self):super().__init__();self.inputs=[];self.raw=[]
   def forward(self,x,d):
    self.inputs.append((x.clone().numpy(),d.clone().numpy()))
    y=(torch.full_like(x[:,:171],.01) if flow else .2*x[:,:171]+.4*x[:,177:348] if history else .5*x[:,:171]+.01)
    self.raw.append(y.clone().numpy());return y
  f=object.__new__(module.TGCMForecast)
  for k,v in dict(dt=1,n_prediction=length,n_history=history,img_shape_x=36,img_shape_y=72,n_in_channels=177,n_out_channels=171,device=torch.device('cpu'),means=torch.zeros((174,1,1)),stds=torch.ones((174,1,1)),time_means=torch.zeros((174,36,72)),wgt=torch.ones(36),log_to_screen=False,perturb=False,flow=flow,log_DEN=log,index={'DEN':np.arange(142,171)},model=Network(),dataset=Dataset()).items():setattr(f,k,v)
  if log:f.means[142:171]=-12.;f.stds[142:171]=.1;f.time_means[142:171]=-12.
  with MetricTrace(module):r=f.inference(0)
  states=[r[1][0,k+1:k+2].copy() for k in range(length)]
  check_autoregression(f.model.inputs,states,data.numpy(),sw.numpy(),history,f.model.raw,flow)
  return r,f.model.inputs,states,data.numpy(),sw.numpy(),f.model.raw
 def test_all_four_official_update_modes_six_steps_and_poison(self):
  for h,flow,log in [(0,False,False),(0,True,False),(0,False,True),(1,False,False)]:
   with self.subTest(history=h,flow=flow,log=log):
    a,*_=self.stub(h,flow,log);b,*_=self.stub(h,flow,log,True);np.testing.assert_array_equal(a[1],b[1]);self.assertFalse(np.array_equal(a[0],b[0]))
 def test_history_third_step_has_two_predictions(self):
  _,ins,states,data,sw,raw=self.stub(1);np.testing.assert_array_equal(ins[2][0][0,:171],states[0][0]);np.testing.assert_array_equal(ins[2][0][0,177:348],states[1][0])
 def test_later_teacher_forcing_rejected(self):
  _,ins,out,data,sw,raw=self.stub(1);ins[4][0][0,177:348]=data[5,:171]
  with self.assertRaises(AssertionError):check_autoregression(ins,out,data,sw,1)
 def test_later_auxiliary_and_scalar_shift_rejected(self):
  _,ins,out,data,sw,raw=self.stub();ins[5][1][:]+=1
  with self.assertRaises(AssertionError):check_autoregression(ins,out,data,sw)
  _,ins,out,data,sw,raw=self.stub();ins[3][0][0,171:]+=1
  with self.assertRaises(AssertionError):check_autoregression(ins,out,data,sw)
 def test_flow_delta_is_not_absolute_state(self):
  _,ins,out,data,sw,raw=self.stub(flow=True)
  with self.assertRaises(AssertionError):check_autoregression(ins,raw,data,sw,raw_outputs=raw,flow=True)
 def test_arbitrary_positive_length_and_wrong_shapes(self):
  for length in [1,3,7]:self.stub(1,length=length)
  _,ins,out,data,sw,raw=self.stub();
  with self.assertRaises(ValueError):check_autoregression(ins,out,data[:-1],sw)
  ins[0]=(ins[0][0][:,:170],ins[0][1])
  with self.assertRaises(ValueError):check_autoregression(ins,out,data,sw)
if __name__=='__main__':unittest.main()
