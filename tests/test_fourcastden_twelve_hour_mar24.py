"""Mar24-specific data selection; generic twelve-step poison tests are reused."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import run_fourcastden_twelve_hour_mar24 as run
class Mar24Tests(unittest.TestCase):
 def test_isolated_paths_and_fixed_date(self):
  self.assertEqual(run.DATES,('2023-03-24',))
  for p in (run.F,run.D,run.RAW):
   self.assertTrue(p.is_relative_to(ROOT));self.assertIn('mar24',p.name)
 def test_code_preserves_exact_six_hour_gate_and_twelve_updates(self):
  import inspect
  code=inspect.getsource(run.execute)
  self.assertIn('assert len(inputs)==12',code)
  self.assertIn("np.testing.assert_array_equal(state,old['pred'][0,lead:lead+1])",code)
  self.assertIn('check_autoregression',code)
if __name__=='__main__':unittest.main()
