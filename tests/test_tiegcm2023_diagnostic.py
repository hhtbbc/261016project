"""Static gates only. These tests must never launch an MPI model."""
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('diagnostic_runner',ROOT/'scripts/run_tiegcm2023_diagnostic.py')
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)

class DiagnosticTests(unittest.TestCase):
    def test_date_separation_and_duration(self):
        text=d.configuration();d.validate_config(text)
        self.assertIn('SOURCE_START = 80 0 0',text)
        self.assertIn('STOP = 77 0 10',text)
    def test_constant_driver_override_rejected(self):
        for key in ['F107','F107A','KP','POWER','CTPOTEN','POWER_TIME','F107_TIME']:
            with self.subTest(key=key),self.assertRaises(ValueError):
                d.validate_config(d.configuration().replace('\n/',f'\n {key} = 70\n/'))
    def test_longer_run_rejected(self):
        with self.assertRaises(ValueError):d.validate_config(d.configuration().replace('STOP = 77 0 10','STOP = 77 1 0'))
    def test_outside_workspace_rejected(self):
        with self.assertRaises(ValueError):d.inside(Path('/tmp'))
if __name__=='__main__':unittest.main()
