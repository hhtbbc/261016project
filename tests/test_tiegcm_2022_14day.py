import unittest,sys,ast
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_tiegcm_2022_14day as r
import prepare_tiegcm_2022_14day_drivers as d
class TestFourteen(unittest.TestCase):
 def test_support(self):
  a,b,lo,hi,sl,sh=d.support();self.assertEqual(((sh-sl).days+1,((hi-lo).days+1)*8),(101,168));self.assertEqual(str(sl),'2022-01-26');self.assertEqual(str(sh),'2022-05-06')
 def test_output_schedule(self):
  p,q=r.schedules();self.assertEqual((len(p),len(q),len(sum(q,[]))),(17,16,384));self.assertEqual(sum(v>=82*86400 for v in sum(q,[])),49)
 def test_only_initial_difference(self):
  a,b=r.configuration('A14'),r.configuration('B14');self.assertEqual(b.replace(str(r.initial.SOURCE),str(r.m.s.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc')),a)
 def test_configs(self):
  r.validate(r.configuration());self.assertIn('START_YEAR = 2022',r.configuration())
  with self.assertRaises(ValueError):r.validate(r.configuration().replace('STEP  = 60','STEP  = 30'))
 def test_engineering_adapter(self):
  import audit_tiegcm_2022_14day as a
  s=a.adapted();ast.parse(s);self.assertIn("('primary',17),('secondary',16)",s);self.assertIn('range(1,385)',s);self.assertNotIn('range(1,409)',s)

class TestSupervisionAndStatistics(unittest.TestCase):
 def test_proc_disappearance_is_not_monitor_crash(self):
  from unittest.mock import patch
  import tiegcm_2022_runtime_guardian as g
  with patch.object(g.os,'listdir',return_value=['999999999','notpid']):self.assertEqual(g.process_table(),{})
 def test_safe_rss_descendants_and_group(self):
  from unittest.mock import patch
  import tiegcm_2022_runtime_guardian as g
  table={10:dict(parent=1,group=10,rss=2),11:dict(parent=10,group=10,rss=3),12:dict(parent=11,group=11,rss=4),13:dict(parent=1,group=13,rss=100)}
  with patch.object(g,'process_table',return_value=table):self.assertEqual(g.safe_rss(10),9)
 def test_shared_domain_excludes_either_invalid(self):
  import numpy as np
  from evaluation.swarm_density_comparison import paired_valid_mask
  m=paired_valid_mask(np.array([True,True,True]),np.array([1.,2.,np.nan]),np.array([1.,np.nan,3.]))
  np.testing.assert_array_equal(m,[True,False,False])
 def test_relative_threshold_unchanged(self):
  import numpy as np
  import compare_tiegcm_2021_initial_conditions as h
  a=np.ones((2,2));b=a*1.06
  q=h.metrics(b,a,np.ones((2,2),float),.05,True,0,True)
  self.assertAlmostEqual(q['relative_P95'],.06);self.assertFalse(q['passed'])

if __name__=='__main__':unittest.main()
