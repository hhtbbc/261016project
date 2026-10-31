"""Small CPU causality/timeline/metric checks, no official network forward."""
from pathlib import Path
import sys,unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from fourcastden.ideal_update import update_indices,splice_at_seven,physical_stats,improvement_percent
from fourcastden.autoregression import check_autoregression


class IdealUpdateTests(unittest.TestCase):
    def test_indices(self):
        self.assertEqual(update_indices(0,0),list(range(7,14)))
        self.assertEqual(update_indices(14,1),list(range(20,28)))

    def test_splice_preserves_prefix_and_reset(self):
        a=np.arange(13)[:,None];b=np.arange(100,107)[:,None]
        s=splice_at_seven(a,b);np.testing.assert_array_equal(s[:6],a[:6]);self.assertEqual(s[6,0],100);self.assertEqual(s[-1,0],106)

    def test_metrics_hand_calculation(self):
        p=np.array([[[2.,4.],[6.,8.]]]);t=np.ones_like(p)*2
        a=physical_stats(p,t,[-30,30],relative=True)
        self.assertAlmostEqual(a['RMSE'],np.sqrt(14));self.assertAlmostEqual(a['MAE'],3)
        self.assertAlmostEqual(a['relative_RMS'],np.sqrt(3.5))
        self.assertEqual(improvement_percent(2,3),-50);self.assertIsNone(improvement_percent(0,1))

    def test_tiny_density_not_floored(self):
        t=np.ones((1,2,2))*1e-30;p=2*t
        self.assertAlmostEqual(physical_stats(p,t,[-30,30],relative=True)['relative_RMS'],1.)

    def test_invalid_domain_counted(self):
        t=np.ones((1,2,2));p=t.copy();p[0,0,0]=np.nan
        a=physical_stats(p,t,[-30,30],relative=True)
        self.assertEqual(a['invalid_pressure_points'],1)
        a=physical_stats(t,t,[-30,30],common_columns=np.array([[0,1],[1,1]],bool),relative=True)
        self.assertEqual(a['common_domain_excluded_points'],1)

    def exercise_feedback(self,history,flow):
        L=6;r=np.zeros((L+history+1,177,36,72),np.float32);sw=np.arange(len(r)*4,dtype=np.float32).reshape(-1,4)
        for k in range(len(r)):r[k,:171]=10+k;r[k,171:]=100+k
        states=[];raw=[];inputs=[]
        for i in range(L):
            blocks=[]
            for j in range(history+1):
                k=i+j;state=r[k,:171] if k<=history else states[k-history-1][0]
                blocks.append(np.concatenate((state,r[k+1,171:]),axis=0))
            x=np.concatenate(blocks,axis=0)[None];z=np.ones((1,171,36,72),np.float32)*(i+1)
            y=z+x[:,:171] if flow else z.copy();inputs.append((x,sw[i+history+1][None,None]));raw.append(z);states.append(y)
        check_autoregression(inputs,states,r,sw,history,raw,flow)
        poison=r.copy();poison[history+1:,:171]=987654
        check_autoregression(inputs,states,poison,sw,history,raw,flow)
        leaked=[(x.copy(),s.copy()) for x,s in inputs];leaked[1][0][0,-177:-6]=poison[history+1,:171]
        with self.assertRaises(AssertionError):check_autoregression(leaked,states,r,sw,history,raw,flow)

    def test_direct_six_step_future_poison(self):self.exercise_feedback(0,False)
    def test_flow_six_step_future_poison(self):self.exercise_feedback(0,True)
    def test_history_six_step_future_poison(self):self.exercise_feedback(1,False)


if __name__=='__main__':unittest.main()
