import unittest,importlib.util,json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];F=R/'experiments/f107_2021_recovery_v1'
s=importlib.util.spec_from_file_location('recovery',R/'scripts/investigate_f107_2021.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Recovery(unittest.TestCase):
 def test_interpolated_not_observed(self):self.assertFalse(m.candidate_gate(76.2,'INT',True,True))
 def test_adjusted_not_observed(self):self.assertFalse(m.candidate_gate(77.7,'ADJ',True,True))
 def test_unexplained_overlap_blocks(self):self.assertFalse(m.candidate_gate(76,'OBS',False,True))
 def test_missing_rejected(self):self.assertFalse(m.candidate_gate(-1,'OBS',True,True))
 def test_nan_rejected(self):self.assertFalse(m.candidate_gate(float('nan'),'OBS',True,True))
 def test_definition_required(self):self.assertFalse(m.candidate_gate(76,'OBS',True,False))
 def test_sensitivity(self):self.assertAlmostEqual(m.sensitivity(.2),.2/81,places=15)
 def test_original_and_2022_unchanged(self):
  for name,want in json.loads((F/'protected.json').read_text()).items():self.assertEqual(hashlib.sha256((R/name).read_bytes()).hexdigest(),want,name)
 def test_actual_decision(self):
  a=json.loads((F/'recovery_audit.json').read_text());self.assertEqual(a['status'],'DATA_GAP_UNRESOLVED');self.assertEqual(a['model_launches'],0);self.assertFalse(a['GPI_generated']);self.assertEqual(a['NOAA_failed_days'],23)
 def test_complete_kp(self):
  a=json.loads((F/'kp_window_audit.json').read_text());self.assertEqual(a['bucket_count'],120);self.assertTrue(a['Kp_is_definitive'])
