import unittest,importlib.util
from pathlib import Path
R=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('longrun',R/'scripts/run_tiegcm_mar23_2021_longrun.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class LongRun(unittest.TestCase):
 def test_primary(self):
  p,_=m.schedules();self.assertEqual(len(p),11);self.assertEqual([x[0] for x in p],list(range(75*86400,85*86400+1,86400)))
 def test_secondary(self):
  _,q=m.schedules();t=sum(q,[]);self.assertEqual(len(q),10);self.assertEqual(t,list(range(75*86400+3600,85*86400+1,3600)))
 def test_candidates(self):
  t=[t for t in sum(m.schedules()[1],[]) if t>=82*86400];self.assertEqual(len(t),73);self.assertEqual(t[0],82*86400)
 def test_fixed_config(self):m.validate(m.configuration())
 def test_overrides(self):
  with self.assertRaises(ValueError):m.validate(m.configuration().replace('\n/','\n KP=2\n/'))
 def test_no_restart_stitch(self):
  s=m.configuration();self.assertIn('SOURCE_START = 80 0 0',s);self.assertIn('START = 75 0 0',s);self.assertIn('STOP = 85 0 0',s);self.assertNotIn('restart_',s)

class AuditMath(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  import sys
  sys.path.insert(0,str(R/'scripts'))
  import audit_tiegcm_mar23_longrun
  cls.audit=audit_tiegcm_mar23_longrun
 def test_native_log_height_and_SI(self):
  import numpy as np
  den=np.array([2e-15,.5e-15])[:,None,None];zg=np.array([400e5,500e5])[:,None,None]
  self.assertAlmostEqual(float(self.audit.native450(den,zg)[0,0])/1e-12,1.,places=12)
 def test_no_height_extrapolation(self):
  import numpy as np
  den=np.array([2e-15,.5e-15])[:,None,None];zg=np.array([100e5,200e5])[:,None,None]
  self.assertTrue(np.isnan(self.audit.native450(den,zg)).all())
 def test_weighted_mean(self):
  import numpy as np
  self.assertAlmostEqual(self.audit.mean(np.array([[2.,2.],[4.,4.]]),np.array([[1.],[.5]])),8/3)

class ActualArtifacts(unittest.TestCase):
 def test_actual_times_and_counts(self):
  import json
  a=json.loads((R/'experiments/tiegcm_training_mar23_v2_2021_longrun/data_audit.json').read_text());self.assertEqual(a['primary_records'],11);self.assertEqual(a['secondary_records'],240);self.assertEqual(a['model_steps'],14400);self.assertEqual(a['actual_driver_log_interval_seconds'],600)
 def test_readonly_candidates_and_leakage(self):
  import json
  a=json.loads((R/'experiments/tiegcm_training_mar23_v2_2021_longrun/candidate_audit.json').read_text());self.assertEqual(a['count'],73);self.assertEqual(a['continuous_pairs'],72);self.assertEqual(a['future_target_poison_checks'],72);self.assertFalse(a['training_approved']);self.assertFalse(a['model_forwards']);self.assertFalse(a['backward']);self.assertFalse(a['optimizer_steps']);self.assertFalse(a['training_statistics_fitted'])
