"""Twelve actual author CPU updates with synthetic network, never trained weights."""
import unittest
import numpy as np
import test_fourcastden_six_hour as six
from fourcastden.autoregression import check_autoregression
class TwelveHourTests(unittest.TestCase):
 def run_stub(self,**kw):return six.SixHourTests().stub(length=12,**kw)
 def test_four_modes_twelve_steps_future_truth_poison(self):
  for history,flow,log in [(0,False,False),(0,True,False),(0,False,True),(1,False,False)]:
   with self.subTest(history=history,flow=flow,log=log):
    a,*_=self.run_stub(history=history,flow=flow,log=log);b,*_=self.run_stub(history=history,flow=flow,log=log,poison=True)
    np.testing.assert_array_equal(a[1],b[1]);self.assertEqual(a[1].shape[1],13)
 def test_history_last_step_two_predictions(self):
  _,ins,out,data,sw,raw=self.run_stub(history=1)
  np.testing.assert_array_equal(ins[11][0][0,:171],out[9][0]);np.testing.assert_array_equal(ins[11][0][0,177:348],out[10][0])
 def test_last_step_teacher_forcing_rejected(self):
  _,ins,out,data,sw,raw=self.run_stub(history=1);ins[11][0][0,177:348]=data[12,:171]
  with self.assertRaises(AssertionError):check_autoregression(ins,out,data,sw,1)
 def test_last_step_condition_shift_rejected(self):
  _,ins,out,data,sw,raw=self.run_stub();ins[11][1][:]+=1
  with self.assertRaises(AssertionError):check_autoregression(ins,out,data,sw)
 def test_first_six_prefix_independent_of_horizon(self):
  for h,flow,log in [(0,False,False),(0,True,False),(0,False,True),(1,False,False)]:
   short,*_=six.SixHourTests().stub(history=h,flow=flow,log=log,length=6);long,*_=self.run_stub(history=h,flow=flow,log=log)
   np.testing.assert_array_equal(short[1],long[1][:,:7])
if __name__=='__main__':unittest.main()
