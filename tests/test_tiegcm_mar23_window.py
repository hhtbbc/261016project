import unittest,importlib.util,json,hashlib
from pathlib import Path
from datetime import date,timedelta
import numpy as np
R=Path(__file__).resolve().parents[1];F=R/'experiments/training_window_mar23_v2'
def load(name):
 s=importlib.util.spec_from_file_location(name,R/'scripts'/f'{name}.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
b=load('prepare_tiegcm_mar23_drivers');r=load('run_tiegcm_mar23_diagnostic')
class MarchWindow(unittest.TestCase):
 def test_registered_split(self):
  p=json.loads((R/'configs/training_windows/training_window_mar23_v2.json').read_text())
  for year,n in [('2021',73),('2022',49)]:
   x=p['years'][year];self.assertEqual(x['hourly_frames'],n);self.assertEqual((date.fromisoformat(x['sample_start'])-date.fromisoformat(x['model_start'])).days,7)
 def test_exact_boundaries(self):
  for y in [2021,2022]:
   p,solar,kp,_=b.inputs(y);self.assertEqual(len(solar),95 if y==2021 else 94);self.assertEqual(len(kp),120 if y==2021 else 112);self.assertNotIn(b.utc(date(y,5,9)),solar)
 def test_both_source_gates(self):
  a=json.loads((F/'completeness.json').read_text());self.assertEqual([a[str(y)]['status'] for y in [2021,2022]],['PASS','PASS'])
 def test_config_year_and_source(self):
  for y in [2021,2022]:
   r.YEAR=y;r.GPI=R/f'data/processed/training_window_mar23_v2/gpi_{y}_mar23_v2.nc';s=r.configuration();r.validate_config(s);self.assertIn(f'START_YEAR = {y}',s);self.assertIn('SOURCE_START = 80 0 0',s);self.assertIn('START = 82 0 0',s)
 def test_override_rejected(self):
  with self.assertRaises(ValueError):r.validate_config(r.configuration().replace('\n/','\n KP = 2\n/'))
 def test_driver_full_valid_domain(self):
  for y in [2021,2022]:
   p=R/f'data/processed/training_window_mar23_v2/gpi_{y}_mar23_v2.nc';d=b.old.GpiDriver(p);protocol=b.inputs(y)[0]
   for day in b.old.dates(date.fromisoformat(protocol['model_start']),date.fromisoformat(protocol['model_end'])):
    for t in [0,5399,5400,43199,43200,86399]:
     a=d.at(int(day.strftime('%Y%j')),t);c=b.independent(p,int(day.strftime('%Y%j')),t)
     for key in a:self.assertAlmostEqual(a[key],c[key],places=9)
 def test_domain_rejection(self):
  d=b.old.GpiDriver(R/'data/processed/training_window_mar23_v2/gpi_2021_mar23_v2.nc')
  with self.assertRaises(ValueError):d.at(2021074,0)
 def test_gpi_old_not_changed(self):
  for name,want in json.loads((F/'protected.json').read_text()).items():self.assertEqual(hashlib.sha256((R/name).read_bytes()).hexdigest(),want,name)
 def test_dtype(self):
  from netCDF4 import Dataset
  for y in [2021,2022]:
   with Dataset(R/f'data/processed/training_window_mar23_v2/gpi_{y}_mar23_v2.nc') as n:
    self.assertEqual(n.data_model,'NETCDF3_CLASSIC');self.assertEqual(n['year_day'].dtype,np.dtype('int32'));self.assertEqual(n['kp'].dtype,np.dtype('float64'))

 def test_output_fields_and_grid(self):
  for y in [2021,2022]:
   a=json.loads((F/f'fields_{y}.json').read_text());self.assertEqual(len(a['fields']),14);self.assertTrue(all(c['author_exact'] for c in a['coordinates'].values()));self.assertFalse(a['training_samples_generated'])
 def test_actual_calendar_and_drivers(self):
  for y in [2021,2022]:
   p=R/f'experiments/tiegcm_mar23_d{y}_v2';a=json.loads((p/'diagnostic_audit.json').read_text());self.assertTrue(a['calendar_pass']);self.assertTrue(a['drivers_pass']);self.assertEqual(a['log_unique_verified_seconds'],list(range(60,601,60)))
