import importlib.util, unittest
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=load('prepare_tiegcm_training_drivers');r=load('run_tiegcm_training_year_diagnostic')
class TrainingDrivers(unittest.TestCase):
 def test_missing_flux_rejected(self):
  with self.assertRaises(ValueError):p.decode({'datetime':['2021-05-09T00:00:00Z'],'Fobs':[-1]},'Fobs')
 def test_duplicates(self):
  with self.assertRaises(ValueError):p.decode({'datetime':['2021-01-01T00:00:00Z']*2,'Fobs':[80,80]},'Fobs')
 def test_kp_status(self):
  with self.assertRaises(ValueError):p.decode({'datetime':['2021-01-01T00:00:00Z'],'Kp':[2],'status':['now']},'Kp')
 def test_centered_average(self):
  t=datetime(2022,4,5,tzinfo=timezone.utc);solar={t+timedelta(days=i):100+i for i in range(-40,41)};kp={t+timedelta(hours=h):2 for h in range(0,24,3)}
  _,f,a,k=p.arrays(solar,kp,t.date(),t.date());np.testing.assert_array_equal(a,[100]);np.testing.assert_array_equal(f,[100]);self.assertEqual(k.shape,(1,8))
 def test_missing_day(self):
  with self.assertRaises(KeyError):p.arrays({}, {}, date(2021,4,5),date(2021,4,5))
 def test_config(self):
  for y in [2021,2022]:
   r.YEAR=y;r.GPI=ROOT/f'data/processed/tiegcm_training_years_v1/gpi_{y}_training_candidate.nc';s=r.configuration();r.validate_config(s);self.assertIn('SOURCE_START = 80 0 0',s);self.assertIn(f'START_YEAR = {y}',s)
 def test_override(self):
  with self.assertRaises(ValueError):r.validate_config(r.configuration().replace('\n/', '\n KP = 2\n/'))
 def test_independent_driver(self):
  r.YEAR=2022;r.GPI=ROOT/'data/processed/tiegcm_training_years_v1/gpi_2022_training_candidate.nc'
  d=p.GpiDriver(r.GPI)
  for sec in range(0,601,60):
   a=d.at(2022095,sec);b=r.expected_drivers(sec);b['Kp']=b.pop('kp')
   for key in a:self.assertAlmostEqual(a[key],b[key],places=10)
