"""Critical batch-time isolation checks; real forwards are not unit tests."""
import sys,unittest
from pathlib import Path
from datetime import datetime,timedelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from fourcastden.four_model_windows import window_indices,summarize_windows
from fourcastden.multidate import DATES
class FourModelWindowsTests(unittest.TestCase):
 def setUp(self):self.epochs=[datetime.fromisoformat(d)+timedelta(hours=h) for d in DATES for h in range(4)]
 def test_history_and_nonhistory_align_to_same_targets(self):
  for i,d in enumerate(DATES):
   h=window_indices(self.epochs,d,1);s=window_indices(self.epochs,d,0)
   self.assertEqual(h,[4*i+j for j in range(4)]);self.assertEqual(h[1:],s);self.assertEqual(self.epochs[h[-2]],datetime.fromisoformat(d)+timedelta(hours=2))
 def test_january_and_unregistered_dates_never_scheduled(self):
  for d in ['2023-01-04','2023-03-24']:
   with self.assertRaises(ValueError):window_indices(self.epochs,d,1)
 def test_missing_duplicate_or_misordered_hour_rejected(self):
  for epochs in [self.epochs[1:],self.epochs+[self.epochs[0]],[self.epochs[1],self.epochs[0]]+self.epochs[2:]]:
   with self.assertRaises(ValueError):window_indices(epochs,DATES[0],1)
 def test_invalid_history_does_not_silently_change_inputs(self):
  for h in [2,-1,True,None]:
   with self.assertRaises(ValueError):window_indices(self.epochs,DATES[0],h)
 def test_summary_uses_equal_windows_not_cell_count(self):
  r=summarize_windows([1,2,3,4,20]);self.assertEqual(r['mean'],6);self.assertEqual(r['median'],3)
  for x in [[1,2], [1,2,3,4,float('nan')], [[1,2,3,4,5]]]:
   with self.assertRaises(ValueError):summarize_windows(x)
if __name__=='__main__':unittest.main()
