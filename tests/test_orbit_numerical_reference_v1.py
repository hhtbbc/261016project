"""Installed solver contract checks only; no H6 trajectory or old event replay."""
import unittest
import numpy as np
from scipy.integrate import solve_ivp,RK45,DOP853
class SolverContracts(unittest.TestCase):
    def test_dop853_six_state_component_atol_and_dense(self):
        def f(t,y):return np.r_[y[3:],-y[:3]]
        x=np.array([1.,2.,3.]);v=np.array([.1,.2,.3]);t=np.array([0.,.3,1.])
        s=solve_ivp(f,(0,1),np.r_[x,v],method='DOP853',rtol=2.5e-13,atol=[1e-6]*3+[1e-9]*3,max_step=.03,dense_output=True)
        self.assertTrue(s.success);expected=np.concatenate([np.cos(t)[:,None]*x+np.sin(t)[:,None]*v,-np.sin(t)[:,None]*x+np.cos(t)[:,None]*v],axis=1)
        np.testing.assert_allclose(s.sol(t).T,expected,rtol=0,atol=2e-12)
    def test_rk45_nfev_trial_accounting(self):
        s=solve_ivp(lambda t,y:y,(0,1),[1.],rtol=1e-10,atol=1e-12,max_step=.001)
        self.assertEqual((s.nfev-2)//RK45.n_stages,len(s.t)-1);self.assertEqual((s.nfev-2)%RK45.n_stages,0)
    def test_high_order_stage_cost_contract(self):
        self.assertEqual(DOP853.n_stages,12);self.assertEqual(len(DOP853.A_EXTRA),3)
if __name__=='__main__':unittest.main()
