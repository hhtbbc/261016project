import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_tiegcm_2022_dual_initial as r
class TestDual(unittest.TestCase):
 def test_config_only_source(self):
  a=(r.A/'input.inp').read_text();b=r.configuration();self.assertEqual(b.replace(str(r.SOURCE),str(r.m.s.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc')),a);r.validate(b)
 def test_reject_physical_change(self):
  with self.assertRaises(ValueError):r.validate(r.configuration().replace('STEP  = 60','STEP  = 30'))
 def test_schedules(self):
  p,q=r.m.schedules();self.assertEqual((len(p),len(q),len(sum(q,[]))),(10,9,216));self.assertEqual(sum(x>=82*86400 for x in sum(q,[])),49)
 def test_smax_actual_contract(self):
  a=r.source_audit();self.assertEqual(a['required_count'],34);self.assertTrue(a['record_available']);self.assertEqual(a['actual_run_year'],2022)

class TestFrozenAnalysis(unittest.TestCase):
 def test_metrics_unchanged_AST(self):
  import compare_tiegcm_2022_dual_initial as a
  self.assertIn("'last24h':t>=83*86400",a.adapted_source())
 def test_composition_floor_preserved(self):
  import compare_tiegcm_2021_initial_conditions as c
  import numpy as np
  m=c.metrics(np.array([2e-6]),np.array([1e-6]),np.array([1.]),.05,True,1e-8)
  self.assertEqual(m['relative_P95'],1.);self.assertFalse(m['passed']);self.assertAlmostEqual(m['max_abs'],1e-6)
 def test_cell_95_percent_rule(self):
  import compare_tiegcm_2021_initial_conditions as c
  import numpy as np
  y=np.ones((1,1,1,20));x=y.copy();x[0,0,0,0]=1.1
  a=c.gate_cells(x,y,np.array([True]),{'global':np.array([True])},.05,True,0)
  self.assertTrue(a['passed']);x[0,0,0,1]=1.1
  a=c.gate_cells(x,y,np.array([True]),{'global':np.array([True])},.05,True,0);self.assertFalse(a['passed'])

if __name__=='__main__':unittest.main()
