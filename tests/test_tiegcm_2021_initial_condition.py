import unittest,importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('initial',R/'scripts/run_tiegcm_2021_initial_condition.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class InitialState(unittest.TestCase):
 def test_only_source_changed(self):
  a=(m.A_DIR/'input.inp').read_text();b=m.configuration();self.assertEqual(b.replace(str(m.B_SOURCE),str(m.s.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc')),a)
 def test_complete_native_state(self):
  a=json.loads((m.CASE/'initial_state_audit.json').read_text());self.assertEqual(a['status'],'STATIC_COMPATIBLE');self.assertEqual(a['complete_required_variables'],34);self.assertTrue(a['B']['all_required_double'])
 def test_same_output_schedule(self):
  p,q=m.schedules();self.assertEqual(len(p),11);self.assertEqual(len(q),10);self.assertEqual(sum(q,[]),list(range(75*86400+3600,85*86400+1,3600)))
 def test_validate(self):m.validate(m.configuration())
 def test_forbidden_override(self):
  with self.assertRaises(ValueError):m.validate(m.configuration().replace('\n/','\n KP=2\n/'))
 def test_frozen_thresholds(self):
  a=json.loads((m.CASE/'frozen_comparison_rules.json').read_text());self.assertEqual(a['density_relative_limit'],.05);self.assertEqual(a['TN_absolute_limit_K'],10);self.assertEqual(a['horizontal_wind_vector_limit_m_s'],20);self.assertEqual(a['trace_reference_floor_mmr'],1e-8)


class PairedMetrics(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  spec=importlib.util.spec_from_file_location('comparison',R/'scripts/compare_tiegcm_2021_initial_conditions.py');cls.c=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.c)
 def test_signed_reference_and_relative(self):
  import numpy as np
  x=np.array([[[1.04,1.06]]]);y=np.ones_like(x);a=self.c.metrics(x,y,np.ones_like(x),.05,True,0,True)
  self.assertAlmostEqual(a['bias'],.05);self.assertAlmostEqual(a['pass_fraction'],.5);self.assertFalse(a['passed'])
 def test_padding_and_trace_floor(self):
  import numpy as np
  x=np.array([[[np.nan,2e-9,1.02]]]);y=np.array([[[np.nan,1e-9,1.]]]);a=self.c.metrics(x,y,np.ones_like(x),.05,True,1e-8)
  self.assertEqual(a['relative_n'],1);self.assertEqual(a['n'],2);self.assertTrue(a['passed']);self.assertAlmostEqual(a['coverage'],2/3)
 def test_regional_gate_cannot_hide_bad_layer(self):
  import numpy as np
  x=np.ones((2,2,2,10));y=x.copy();x[1,1,0,:]=1.1
  a=self.c.gate_cells(x,y,np.array([True,True]),{'north':np.array([True,False])},.05,True)
  self.assertFalse(a['passed']);self.assertEqual(a['failed_cells'],1)
 def test_native_ZG_no_extrapolation(self):
  import numpy as np
  z=np.array([[[100.]],[[200.]],[[300.]]]);d=np.exp(-z/100)
  v=self.c.legacy.a3.at_height(z,d,150);self.assertAlmostEqual(float(v[0,0]),float(np.exp(-1.5)))
  self.assertTrue(np.isnan(self.c.legacy.a3.at_height(z,d,400)).all())
