"""CPU representation and compatibility tests; never runs a real checkpoint."""
import sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'third_party/FourCastDEN_linux'))
from fourcastden.logden import load_log_time_means,decode_physical,checked_tensor_pow10,load_overlay,MetricTrace
class LogDenTests(unittest.TestCase):
 def test_base10_known_units(self):
  import torch
  x=torch.tensor([-15.,-12.,-9.]);y=checked_tensor_pow10(x)
  np.testing.assert_allclose(y.numpy()*1000,[1e-12,1e-9,1e-6],rtol=2e-7)
 def test_dtype_device_and_numpy_reference(self):
  import torch
  for dtype in [torch.float32,torch.float64]:
   x=torch.tensor([-15.2,-12.4,-9.3],dtype=dtype);y=checked_tensor_pow10(x)
   self.assertEqual(y.dtype,dtype);self.assertEqual(y.device,x.device)
   np.testing.assert_allclose(y.numpy(),np.power(10.,x.numpy().astype(float)),rtol=3e-7)
 def test_overflow_and_underflow_are_rejected(self):
  import torch
  for value in [100.,-100.]:
   with self.assertRaises(ValueError):checked_tensor_pow10(torch.tensor([value]))
 def test_inverse_standardization_and_non_DEN_unchanged(self):
  x=np.zeros((171,2,2));means=np.ones((171,1,1))*2;stds=np.ones_like(means)*.5;means[142:]=-12.;x[142:]=2.
  y=decode_physical(x,means,stds,True)
  np.testing.assert_array_equal(y[:142],2.);np.testing.assert_allclose(y[142:],1e-11)
 def test_log_mean_is_not_physical_arithmetic_mean(self):
  a=np.array([1e-10,1e-12]);self.assertNotAlmostEqual(float(np.log10(a.mean())),float(np.log10(a).mean()),places=3)
 def test_official_climatology_singleton_removal_is_exact(self):
  p=ROOT/'data/processed/static_log/time_means.npz';out=load_log_time_means(p)
  with np.load(p) as q:
   for k,n in dict(TN=28,UN=28,VN=28,WN=29,Z=29,ZG=29,DEN=29,NE=29,TLBC=1,ULBC=1,VLBC=1).items():
    self.assertEqual(out[k].shape,(n,36,72));np.testing.assert_array_equal(out[k].reshape(-1),q[k].reshape(-1))
 def test_channelwise_broadcast_preserves_formula(self):
  import torch
  p=torch.arange(29*2*3,dtype=torch.float32).reshape(29,2,3)/100
  s=torch.linspace(.01,.1,29);m=torch.linspace(-16,-9,29)
  with self.assertRaises(RuntimeError):p*s+m
  actual=p*s[:,None,None]+m[:,None,None]
  expected=np.stack([p[k].numpy()*s[k].item()+m[k].item() for k in range(29)])
  np.testing.assert_array_equal(actual.numpy(),expected)
 def test_metric_trace_rejects_invalid_density(self):
  import torch
  from types import SimpleNamespace
  module=SimpleNamespace(weighted_rmse_channels=lambda p,t,w:torch.ones(1))
  with MetricTrace(module):
   with self.assertRaises(ValueError):module.weighted_rmse_channels(-torch.ones((1,29,2,2)),torch.ones((1,29,2,2)),torch.ones(2))
 def test_logspace_two_step_feedback_without_future_truth(self):
  import torch
  module=load_overlay(ROOT/'experiments/fourcastden_logden_multidate_v1/inference_overlay.py')
  TGCMForecast=module.TGCMForecast
  data=torch.ones((3,177,36,72));sw=torch.zeros((3,4))
  class Data:
   def __init__(self,d):self.d=d
   def get_data(self,*a,**k):return self.d,sw,None,None,None
  class Net(torch.nn.Module):
   def __init__(self):super().__init__();self.inputs=[]
   def forward(self,x,s):self.inputs.append(x.clone());return x[:,:171]*.5
  def run(d):
   f=object.__new__(TGCMForecast)
   for k,v in dict(dt=1,n_prediction=2,n_history=0,img_shape_x=36,img_shape_y=72,n_in_channels=177,n_out_channels=171,device=torch.device('cpu'),means=torch.zeros((174,1,1)),stds=torch.ones((174,1,1)),time_means=torch.zeros((174,36,72)),wgt=torch.ones(36),log_to_screen=False,perturb=False,flow=False,log_DEN=True,index={'DEN':np.arange(142,171)},model=Net(),dataset=Data(d)).items():setattr(f,k,v)
   f.means[142:171]=-12.;f.stds[142:171]=.1;f.time_means[142:171]=-12.
   with MetricTrace(module) as trace:r=f.inference(0)
   self.assertEqual(len(trace.normalized_rmse),2);self.assertEqual(len(trace.physical_pred),2)
   for h in range(2):
    actual=np.sqrt(np.mean((trace.physical_pred[h].astype(float)-trace.physical_target[h].astype(float))**2,axis=(-1,-2)))[0]
    np.testing.assert_allclose(actual,r[2][0,h,142:171],rtol=2e-5,atol=1e-25)
   return r,f.model.inputs
  a,ins=run(data);poison=data.clone();poison[1:,:171]=9.;b,_=run(poison)
  np.testing.assert_array_equal(a[1],b[1]);torch.testing.assert_close(ins[1][0,:171],torch.full((171,36,72),.5),rtol=0,atol=0)
if __name__=='__main__':unittest.main()
