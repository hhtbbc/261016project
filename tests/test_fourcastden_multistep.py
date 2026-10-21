import unittest,sys,copy
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'third_party/FourCastDEN_linux'))
from fourcastden.validation import channel_metrics,feedback_check

class FourCastdenMultiTests(unittest.TestCase):
    def test_weighted_hand_calculation(self):
        p=np.array([[[1.,3.],[2.,4.]]]);r=np.zeros_like(p);clim=np.ones_like(p)
        rmse,_,_=channel_metrics(p,r,clim,[0.,60.]);w=np.array([1.,.5])/0.75
        self.assertAlmostEqual(rmse[0],np.sqrt((10*w[0]+20*w[1])/4))
    def test_acc_zero_denominator_is_NA(self):
        _,acc,valid=channel_metrics(np.ones((1,2,2)),np.ones((1,2,2)),np.ones((1,2,2)),[-45,45]);self.assertFalse(valid[0]);self.assertTrue(np.isnan(acc[0]))
    def test_acc_identity(self):
        x=np.arange(8.).reshape(2,2,2);_,a,v=channel_metrics(x,x,np.zeros_like(x),[-45,45]);np.testing.assert_allclose(a,1);self.assertTrue(v.all())
    def test_feedback_gate_detects_teacher_forcing(self):
        real=np.zeros((3,177,2,2));sw=np.zeros((3,4));outputs=[np.ones((1,171,2,2)),np.ones((1,171,2,2))*2];ins=[(real[:1].copy(),sw[1].copy()),(real[1:2].copy(),sw[2].copy())]
        with self.assertRaises(AssertionError):feedback_check(ins,outputs,real,sw)
    def test_author_loop_rejects_future_state_leakage(self):
        # Synthetic CPU-only dependency test of original inference loop; NOT scientific predictions.
        import torch
        from inference.inference import TGCMForecast
        class Stub:
            def __init__(self,data):self.data=data
            def get_data(self,indices,inference=False):return self.data,torch.arange(12,dtype=torch.float32).reshape(3,4),None,None,None
        class Net(torch.nn.Module):
            def __init__(self):super().__init__();self.inputs=[]
            def forward(self,x,s):self.inputs.append((x.clone(),s.clone()));return x[:,:171]*.5+.2
        data=torch.ones((3,177,36,72));data[1:,171:]=2.
        def run(d):
            f=object.__new__(TGCMForecast);f.dt=1;f.n_prediction=2;f.n_history=0;f.img_shape_x=36;f.img_shape_y=72;f.n_in_channels=177;f.n_out_channels=171;f.device=torch.device('cpu');f.means=torch.zeros((174,1,1));f.stds=torch.ones((174,1,1));f.time_means=torch.zeros((174,36,72));f.wgt=torch.ones(36);f.log_to_screen=False;f.perturb=False;f.flow=False;f.log_DEN=False;f.model=Net();f.dataset=Stub(d);r=f.inference(0);return r[1],f.model.inputs
        baseline,inp=run(data);changed=data.clone();changed[1:,:171]=999.;poisoned,inp2=run(changed)
        np.testing.assert_array_equal(baseline,poisoned)
        for a,b in zip(inp,inp2):torch.testing.assert_close(a[0],b[0],rtol=0,atol=0)
        changed_aux=data.clone();changed_aux[1:,171:]=3.;_,inp3=run(changed_aux);self.assertFalse(torch.equal(inp[1][0],inp3[1][0]))
if __name__=='__main__':unittest.main()
