import unittest,importlib.util
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def load(name):
 s=importlib.util.spec_from_file_location(name,R/'scripts'/f'{name}.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('run_tiegcm_mar23_2022_longrun');old=load('run_tiegcm_mar23_2021_longrun')
class ValidationRun(unittest.TestCase):
 def test_primary(self):self.assertEqual([a[0] for a in m.schedules()[0]],list(range(75*86400,84*86400+1,86400)))
 def test_secondary(self):self.assertEqual(sum(m.schedules()[1],[]),list(range(75*86400+3600,84*86400+1,3600)))
 def test_candidate_window(self):self.assertEqual(len([x for x in sum(m.schedules()[1],[]) if x>=82*86400]),49)
 def test_validate(self):m.validate(m.configuration())
 def test_no_cross_year_initialization(self):
  s=m.configuration();self.assertIn('START_YEAR = 2022',s);self.assertIn('SOURCE_START = 80 0 0',s);self.assertIn('tiegcm_res5.0_mareqx_smin_prim.nc',s);self.assertNotIn('primary_011.nc',s)
 def test_physics_parity(self):
  for line in old.configuration().splitlines():
   if any(k in line for k in ['SECFLDS','GSWM_','POTENTIAL_MODEL','CALC_HELIUM','STEP ','SOURCE_START','CALENDAR_ADVANCE']):self.assertIn(line,m.configuration())
 def test_override(self):
  with self.assertRaises(ValueError):m.validate(m.configuration().replace('\n/','\n KP=1\n/'))

class ActualDataset(unittest.TestCase):
 def test_actual_time_counts(self):
  import json
  a=json.loads((R/'experiments/tiegcm_training_mar23_v2_2022_longrun/data_audit.json').read_text());self.assertEqual((a['model_steps'],a['primary_records'],a['secondary_records'],a['candidate_records']),(12960,10,216,49))
 def test_actual_readonly_interface(self):
  import json
  a=json.loads((R/'experiments/tiegcm_training_mar23_v2_2022_longrun/candidate_audit.json').read_text());self.assertEqual(a['continuous_pairs'],48);self.assertEqual(a['future_target_poison_checks'],48);self.assertTrue(a['official_input_exact']);self.assertIn('VALIDATION_CANDIDATE_ONLY',a['labels']);self.assertFalse(any(a[k] for k in ['training_statistics_fitted','model_forwards','backward','optimizer_steps','training_approved']))
 def test_joint_dataset_split(self):
  import json
  a=json.loads((R/'experiments/tiegcm_training_mar23_v2_2022_longrun/joint_dataset_audit.json').read_text());self.assertEqual(a['total_frames'],122);self.assertEqual(a['total_continuous_pairs'],120);self.assertTrue(a['epochs_disjoint']);self.assertTrue(a['identical_grid_units_padding_and_model'])
 def test_scientific_gate_not_bypassed(self):
  import json
  a=json.loads((R/'experiments/tiegcm_training_mar23_v2_2022_longrun/joint_dataset_audit.json').read_text());self.assertFalse(a['scientific_training_READY']);self.assertFalse(a['training_statistics_fitted']);self.assertEqual(a['spinup_status'],'SPINUP_SUFFICIENCY_UNVERIFIED')
