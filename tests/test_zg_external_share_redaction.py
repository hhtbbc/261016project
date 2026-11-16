"""In-memory redaction fixtures only; no private files or network access."""
import unittest,importlib.util
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts/verify_zg_registration_v2_1.py';s=importlib.util.spec_from_file_location('sharecheck',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class RedactionTests(unittest.TestCase):
 def test_official_URL(self):self.assertFalse(m.scan_text('https://github.com/NCAR/tiegcm/tree/commit/src/addiag.F','test'))
 def test_unix_paths(self):
  for p in ['/workspace/data/private','/root/private','/home/person/x','/tmp/x','/opt/private/x']:self.assertTrue(m.scan_text(p,'test'))
 def test_windows(self):self.assertTrue(m.scan_text('C:\\private\\file','test'))
 def test_project_relative(self):self.assertTrue(m.scan_text('experiments/private/file','test'))
 def test_private_email(self):self.assertTrue(m.scan_text('person@example.org','test'))
 def test_official_email(self):self.assertFalse(m.scan_text('tgcmgroup@mailman.ucar.edu','test'))
 def test_credential_assignment(self):self.assertTrue(m.scan_text('password=synthetic_test_value','test'))
 def test_known_token(self):self.assertTrue(m.scan_text('github'+'_pat_'+'X'*30,'test'))
 def test_nested_keys(self):self.assertTrue(m.scan_json({'a':[{'logname':'synthetic'}]}))
 def test_decoded_escaped_path(self):
  import json
  self.assertTrue(m.scan_json(json.loads('{"x":"\\u002fhome\\u002fperson\\u002ffile"}')))
 def test_original_attribute_keys(self):
  for k in ['source_file','initial_file','host','username']:self.assertTrue(m.scan_json({k:'synthetic'}))
 def test_raw_file(self):self.assertTrue(m.scan_text('secondary_015.nc','test'))
 def test_actual_host(self):self.assertTrue(m.scan_text('machine-example','test',['machine-example']))
 def test_no_full_logs_or_extra_data(self):self.assertFalse(m.validate_names(m.ALLOWED|{'stdout.log'}))
 def test_whitelist(self):self.assertTrue(m.validate_names(m.ALLOWED))
if __name__=='__main__':unittest.main()
