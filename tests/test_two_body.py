"""Analytical central-gravity and propagation contract checks (SI)."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import unittest
import numpy as np
from orbit.two_body import EARTH_MU, central_gravity, two_body_rhs, make_state_derivative, invariants
from orbit.rk45_propagator import propagate

class TwoBodyTests(unittest.TestCase):
    def test_force_and_composition(self):
        r=np.array([7e6,0,0]);v=np.array([0,7500,0])
        np.testing.assert_allclose(central_gravity(0,r,v),[-EARTH_MU/7e6**2,0,0])
        rhs=make_state_derivative([central_gravity,lambda t,r,v: np.array([1.,2.,3.])])
        np.testing.assert_allclose(rhs(0,np.r_[r,v]),np.r_[v,central_gravity(0,r,v)+[1,2,3]])
        with self.assertRaises(ValueError):central_gravity(0,np.zeros(3),v)
    def test_analytic_circular_orbit(self):
        radius=6778137.;speed=np.sqrt(EARTH_MU/radius);T=2*np.pi*np.sqrt(radius**3/EARTH_MU)
        y=np.array([radius,0,0,0,speed,0])
        run=propagate(two_body_rhs,y[:3],y[3:],(0,T),np.linspace(0,T,101))
        phase=run.times_s*2*np.pi/T
        true=np.column_stack([radius*np.cos(phase),radius*np.sin(phase),np.zeros(len(phase))])
        self.assertLess(np.linalg.norm(run.states[:,:3]-true,axis=1).max(),.1)
        self.assertLess(np.linalg.norm(run.states[-1,3:]-y[3:]),1e-4)
        E,h=invariants(run.states)
        self.assertLess(np.max(abs((E-E[0])/E[0])),1e-8)
        self.assertLess(np.max(np.linalg.norm(h-h[0],axis=1)/np.linalg.norm(h[0])),1e-8)
        self.assertGreater(run.statistics['accepted_steps'],100)
    def test_nonzero_start_and_output_grid(self):
        run=propagate(lambda t,y:np.r_[y[3:],np.zeros(3)],[1,2,3],[4,5,6],(10,20),[10,13,20])
        np.testing.assert_allclose(run.states[-1],[41,52,63,4,5,6],atol=1e-10)
        self.assertEqual(run.statistics['output_samples'],3)
        with self.assertRaises(ValueError):propagate(two_body_rhs,[1,0,0],[0,1,0],(0,10),[0,11])
        with self.assertRaises(ValueError):propagate(two_body_rhs,[1,0,0],[0,1,0],(0,10),[0,0])
    def test_failure_is_not_silently_returned(self):
        def invalid(t,y):raise RuntimeError('deliberate force failure')
        with self.assertRaises(RuntimeError):propagate(invalid,[7e6,0,0],[0,7500,0],(0,10),[0,10])

if __name__=='__main__':unittest.main()
