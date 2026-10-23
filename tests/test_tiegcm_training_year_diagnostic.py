import unittest
from test_tiegcm_training_drivers import r
class YearDiagnostic(unittest.TestCase):
 def test_initial_guess_not_calendar(self):
  for year in [2021,2022]:
   r.YEAR=year;s=r.configuration();self.assertIn('SOURCE_START = 80 0 0',s);self.assertIn('START = 95 0 0',s);self.assertIn('STOP = 95 0 10',s)
 def test_no_overrides(self):
  for name in ['F107','F107A','KP','POWER','CTPOTEN']:
   with self.assertRaises(ValueError):r.validate_config(r.configuration().replace('\n/',f'\n {name}_TIME = 0\n/'))
 def test_calendar_tamper(self):
  with self.assertRaises(ValueError):r.validate_config(r.configuration().replace('CALENDAR_ADVANCE = 1','CALENDAR_ADVANCE = 0'))
