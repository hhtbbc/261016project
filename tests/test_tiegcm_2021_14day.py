import sys,unittest,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R/'scripts')]
import run_tiegcm_2021_14day as m
import prepare_tiegcm_2021_14day_drivers as d
class Extended(unittest.TestCase):
 def test_support(self):self.assertEqual([str(x) for x in d.support()],['2021-03-09','2021-03-26','2021-03-07','2021-03-28','2021-01-26','2021-05-07'])
 def test_records(self):
  p,q=m.schedules();self.assertEqual(len(p),18);self.assertEqual(len(q),17);self.assertEqual(len(sum(q,[])),408);self.assertEqual(sum(q,[])[0],68*86400+3600);self.assertEqual(sum(q,[])[-1],85*86400)
 def test_pair_only_source(self):
  m.GROUP='A14';a=m.configuration();m.GROUP='B14';b=m.configuration();self.assertEqual(a,b.replace(str(m.B_SOURCE),str(m.s.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc')));m.GROUP='A14'
 def test_exact_frozen_thresholds(self):
  self.assertEqual((m.CASE/'frozen_comparison_rules.json').read_bytes(),(R/'experiments/tiegcm_2021_spinup_initial_condition_v1/frozen_comparison_rules.json').read_bytes())
 def test_configuration(self):m.GROUP='A14';m.validate(m.configuration())
 def test_reject_override(self):
  with self.assertRaises(ValueError):m.validate(m.configuration().replace('\n/','\n KP=2\n/'))
 def test_common_drivers_and_quality(self):
  x=json.loads((m.CASE/'driver_audit.json').read_text());self.assertEqual(x['status'],'PASS');self.assertEqual(x['Fobs_count'],102);self.assertEqual(x['Kp_count'],176);self.assertEqual(x['common_14401_minute_nodes_max_difference'],0)
 def test_calendar_physics_and_source_clock(self):
  m.GROUP='A14';text=m.configuration()
  for entry in ['START_YEAR = 2021','START_DAY = 68','SOURCE_START = 80 0 0','START = 68 0 0','STOP = 85 0 0','STEP  = 60',"POTENTIAL_MODEL = 'HEELIS'",'CALC_HELIUM = 1','gswm_diurn_5.0d_99km.nc','gpi_2021_14day.nc']:self.assertIn(entry,text)
 def test_native_initial_identity_preserved(self):
  from atmosphere.restart_validation import inspect_restart
  for p in [m.s.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc',m.B_SOURCE]:
   x=inspect_restart(p,[80,0,0]);self.assertTrue(x['structure_complete']);self.assertTrue(x['record_available']);self.assertFalse(x['validated_continuation'])
 def test_extended_GPI_native_format(self):
  from netCDF4 import Dataset
  import numpy as np
  with Dataset(R/'data/processed/tiegcm_2021_spinup_14day_v1/gpi_2021_14day.nc') as n:
   self.assertEqual(n.data_model,'NETCDF3_CLASSIC');self.assertEqual(n['kp'].shape,(22,8));self.assertEqual(n['year_day'].dtype,np.dtype('int32'))
   for k in ['f107d','f107a','kp']:self.assertEqual(n[k].dtype,np.dtype('float64'))
 def test_cross_epoch_absolute_calendar(self):
  from netCDF4 import Dataset,num2date
  old=R/'experiments/tiegcm_training_mar23_v2_2021_longrun/secondary_007.nc';new=m.CASE/'A14/secondary_014.nc'
  with Dataset(old) as a,Dataset(new) as b:
   self.assertNotEqual(a['time'].units,b['time'].units)
   ta=num2date(a['time'][-1],a['time'].units);tb=num2date(b['time'][-1],b['time'].units);self.assertEqual(str(ta),str(tb));self.assertEqual(str(ta),'2021-03-23 00:00:00')
   self.assertEqual(a['DEN'].units,b['DEN'].units)
