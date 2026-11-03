"""New DOP853 event adapter contracts on analytic non-orbit ODEs only."""
from pathlib import Path
import sys,unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.dop853_events import propagate_dop853_events
from orbit import event_segments
class AdapterTests(unittest.TestCase):
    def test_analytic_acceleration_jump_and_original_unchanged(self):
        original=event_segments.propagate;seen=[[],[]]
        def factory(i):
            def rhs(t,y):seen[i].append(t);return np.r_[y[3:],[1.+i,0,0]]
            return rhs
        sol=propagate_dop853_events(factory,[0,0,0],[0,0,0],(0,2),[0,.5,1,1.5,2],[1],rtol=2.5e-13,atol=[1e-6]*3+[1e-9]*3,max_step=.1)
        self.assertIs(event_segments.propagate,original);np.testing.assert_allclose(sol.states[-1],[2.5,0,0,3,0,0],rtol=0,atol=1e-12);np.testing.assert_array_equal(sol.segments[0].states[-1],sol.segments[1].states[0]);self.assertEqual(sol.segments[0].statistics['method'],'DOP853');self.assertLessEqual(max(seen[0]),1);self.assertGreaterEqual(min(seen[1]),1)
    def test_failure_is_not_filled(self):
        def factory(i):
            def rhs(t,y):raise ValueError('invalid density sentinel')
            return rhs
        with self.assertRaisesRegex(ValueError,'invalid density'):propagate_dop853_events(factory,[0]*3,[0]*3,(0,2),[0,1,2],[1],rtol=2.5e-13,atol=[1e-6]*3+[1e-9]*3,max_step=.1)
    def test_bad_event_rejected_before_rhs(self):
        with self.assertRaises(ValueError):propagate_dop853_events(lambda i:None,[0]*3,[0]*3,(0,2),[0,1,2],[0],rtol=2.5e-13,atol=[1e-6]*3+[1e-9]*3,max_step=.1)
if __name__=='__main__':unittest.main()
