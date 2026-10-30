"""New configuration tests only; no repetition of prior seven budget CPU tests."""
import sys,unittest,re,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import run_tiegcm_runtime_restart_audit as m
class QualificationConfigTests(unittest.TestCase):
 def test_reference_is_twenty_minutes(self):
  t=m.config('continuous');self.assertIn('START = 82 0 0',t);self.assertIn('STOP = 82 0 20',t);self.assertIn('STEP  = 60',t)
 def test_first_segment_uses_identical_source(self):
  a=m.config('continuous');b=m.config('segment')
  for key in ['SOURCE','SOURCE_START','GPI_NCFILE']:
   self.assertEqual(re.findall(r'^\s*'+key+r'\s*=.*$',a,re.M),re.findall(r'^\s*'+key+r'\s*=.*$',b,re.M))
 def test_restored_branch_is_native_continuation(self):
  t=m.config('resumed');self.assertNotRegex(t,r'(?m)^\s*SOURCE');self.assertIn('START = 82 0 10',t);self.assertIn("OUTPUT = 'primary.nc'",t)
 def test_no_fixed_driver_overrides(self):
  for g in ['continuous','segment','resumed']:self.assertNotRegex(m.config(g),r'(?m)^\s*(F107|F107A|KP|POWER|CTPOTEN)\s*=')
 def test_limits_are_short_only(self):
  p=json.loads((m.SUITE/'protocol.json').read_text());self.assertEqual(sum(p['stage_model_steps'].values()),40);self.assertEqual(p['max_launches'],3);self.assertTrue(p['no_remote_sync']);self.assertLessEqual(p['model_wall_total_s'],180)
 def test_existing_frozen_mmr_rule_not_relaxed(self):
  x=json.loads((m.SUITE/'frozen_comparison_rules.json').read_text());self.assertEqual(x['O1']['rtol'],1e-10);self.assertEqual(x['O1']['atol_SI'],1e-12)
if __name__=='__main__':unittest.main()
