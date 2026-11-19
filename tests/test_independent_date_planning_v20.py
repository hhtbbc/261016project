import unittest,sys,math
from datetime import date,timedelta
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from evaluation.independent_date_planning import *
class Planning(unittest.TestCase):
 def test_order_and_no_march_relaunch(self):
  self.assertEqual([x[2] for x in CANDIDATES],['2021-06-21','2022-06-21','2021-09-23','2022-09-23','2021-12-21','2022-12-21']);self.assertFalse(any('03-25' in x[2] for x in CANDIDATES))
 def test_summer_support(self):
  a=support('2021-06-21');self.assertEqual((a['start'],a['stop'],a['solar_start'],a['solar_stop']),('2021-06-07','2021-06-23','2021-04-26','2021-08-04'));self.assertEqual((a['steps'],a['GPI_days'],a['Fobs_days'],a['Kp_buckets']),(23040,21,101,168))
 def test_winter_crossyear(self):self.assertEqual(support('2022-12-21')['solar_stop'],'2023-02-03')
 def test_kp_boundary(self):
  self.assertEqual(kp_class([2]*8,['def']*8),'QUIET');self.assertEqual(kp_class([2.333]*8,['def']*8),'INTERMEDIATE');self.assertEqual(kp_class([5]+[0]*7,['def']*8),'ENHANCED')
 def test_incomplete_or_not_def_unknown(self):
  self.assertEqual(kp_class([0]*7,['def']*7),'UNKNOWN');self.assertEqual(kp_class([0]*8,['pre']*8),'UNKNOWN');self.assertEqual(kp_class([0]*7+[float('nan')],['def']*8),'UNKNOWN')
 def test_missing_flux_not_filled(self):
  d=date(2021,6,21);s={d+timedelta(days=j):80. for j in range(-40,41)};s[date(2021,6,16)]=-1;v,bad=centered(s,d);self.assertIsNone(v);self.assertEqual(bad,[date(2021,6,16)])
 def test_full_center(self):
  d=date(2021,9,23);v,bad=centered({d+timedelta(days=j):90. for j in range(-40,41)},d);self.assertEqual(v,90);self.assertFalse(bad)
 def test_resource_linear_and_sequential_RAM(self):
  e=[dict(wall_s=2400,steps=23040,days=16,output_bytes=3*2**30,CPU_s=9600)];x=estimate(e,16,2);self.assertEqual(x['total_steps'],46080);self.assertEqual(x['total_wall_s_max'],4800);self.assertEqual(x['sequential_peak_RSS_budget_GiB'],16);self.assertEqual(x['disk_available_if_reserving_all_output_caps_GiB'],30)
 def test_seed_is_not_scientific_pass(self):
  self.assertEqual(seed_status(True,True,True,False),'LEGAL_STRUCTURE_SEASON_ADAPTATION_UNVERIFIED');self.assertEqual(seed_status(False,False,False,False),'NOT_ACQUIRED')
 def test_days_inclusive(self):self.assertEqual(len(days(date(2021,6,5),date(2021,6,25))),21)
 def test_seed_clock_rejected(self):self.assertEqual(seed_status(True,True,False,True),'BLOCKED_IDENTITY_OR_CLOCK')
 def test_planner_datetime_namespace(self):
  sys.path.insert(0,str(R/'scripts'));import plan_independent_dates_v20 as planner;self.assertEqual(planner.datetime.datetime(2021,6,21).year,2021)
if __name__=='__main__':unittest.main()
