"""CPU synthetic tests of original Flow loop; not scientific model outputs."""
import sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'third_party/FourCastDEN_linux'))
from fourcastden.flow_validation import flow_feedback_check
class FlowTests(unittest.TestCase):
 def run_author(self,poison=False,aux=2.,delta=.25):
  import torch
  from inference.inference import TGCMForecast
  data=torch.ones((3,177,36,72));data[1:,171:]=aux
  if poison:data[1:,:171]=999.
  sw=torch.arange(12,dtype=torch.float32).reshape(3,4)
  class Dataset:
   def get_data(self,indices,inference=False):return data,sw,None,None,None
  class Net(torch.nn.Module):
   def __init__(self):super().__init__();self.inputs=[];self.increments=[]
   def forward(self,x,s):
    self.inputs.append((x.detach().numpy().copy(),s.detach().numpy().copy()))
    y=torch.full_like(x[:,:171],delta);self.increments.append(y.numpy().copy());return y
  f=object.__new__(TGCMForecast)
  for k,v in dict(dt=1,n_prediction=2,n_history=0,img_shape_x=36,img_shape_y=72,n_in_channels=177,n_out_channels=171,device=torch.device('cpu'),means=torch.zeros((174,1,1)),stds=torch.ones((174,1,1)),time_means=torch.zeros((174,36,72)),wgt=torch.ones(36),log_to_screen=False,perturb=False,flow=True,log_DEN=False,model=Net(),dataset=Dataset()).items():setattr(f,k,v)
  result=f.inference(0)
  return result,f.model.inputs,f.model.increments,sw.numpy()
 def test_actual_author_normalized_increment_feedback(self):
  r,i,d,s=self.run_author();flow_feedback_check(i,d,r[0][0],r[1][0],s)
  np.testing.assert_array_equal(r[1][0,1],1.25);np.testing.assert_array_equal(r[1][0,2],1.5)
 def test_future_truth_poison_does_not_change_predictions(self):
  r,i,_,_=self.run_author();r2,i2,_,_=self.run_author(poison=True)
  np.testing.assert_array_equal(r[1],r2[1])
  for a,b in zip(i,i2):np.testing.assert_array_equal(a[0],b[0])
 def test_future_auxiliary_is_prescribed(self):
  _,i,_,_=self.run_author();_,j,_,_=self.run_author(aux=3.)
  self.assertFalse(np.array_equal(i[1][0][:,171:],j[1][0][:,171:]))
 def test_zero_increment_preserves_initial_state(self):
  r,_,_,_=self.run_author(delta=0.)
  np.testing.assert_array_equal(r[1][0,1],r[1][0,0]);np.testing.assert_array_equal(r[1][0,2],r[1][0,0])
 def test_wrong_absolute_feedback_is_rejected(self):
  r,i,d,s=self.run_author();p=r[1][0].copy();p[1]=d[0][0]
  with self.assertRaises(AssertionError):flow_feedback_check(i,d,r[0][0],p,s)
 def test_denormalization_adds_std_times_increment_not_mean(self):
  state=np.array([1.25]);delta=np.array([.25]);mean=np.array([100.]);std=np.array([10.])
  np.testing.assert_allclose((state+delta)*std+mean,(state*std+mean)+delta*std)
  self.assertFalse(np.allclose((state+delta)*std+mean,(state*std+mean)+(delta*std+mean)))
if __name__=='__main__':unittest.main()
