from pathlib import Path
import sys,tempfile,json,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
from observations.density_catalog import enforce_value_access,ReservedObservationError,read_swarm_pod,calibration_time_mask
from atmosphere.dart_density_audit import three_species_density,helium_eos_density_ratio
from atmosphere.restart_validation import inspect_restart,check_source_clock,REQUIRED
from evaluation.swarm_density_comparison import quality_mask
class FeasibilityTests(unittest.TestCase):
 def test_reserved_B_rejected_before_file_access(self):
  with self.assertRaises(ReservedObservationError):read_swarm_pod(ROOT/'not_present','not_present','0'*64,satellite='B')
 def test_unknown_satellite_rejected(self):
  with self.assertRaises(ValueError):enforce_value_access('D')
 def test_unknown_version_not_silently_reused(self):
  with self.assertRaises(ValueError):read_swarm_pod('SW_OPER_DNSCPOD_2__20220324T000000_20220324T235930_0401.cdf','missing','0'*64,satellite='C')
 def test_corrupted_file_SHA_rejected(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'experiments') as td:
   p=Path(td)/'SW_OPER_DNSCPOD_2__20220324T000000_20220324T235930_0301.cdf';p.write_bytes(b'not a valid CDF')
   with self.assertRaisesRegex(ValueError,'SHA'):read_swarm_pod(p,'missing','0'*64,satellite='C')
 def test_quality_not_all_finite_or_all_nonzero_bad(self):
  mask,why=quality_mask([1e-12,2e-12,3e-12,-1,9.99e32],[0,1,127,0,0]);self.assertEqual(mask.tolist(),[True,False,False,False,False]);self.assertTrue(why['unknown'][2])
 def test_causal_window_excludes_current_and_future(self):
  t=np.array(['2022-03-24T02:00','2022-03-24T05:59','2022-03-24T06:00','2022-03-24T06:01'],dtype='datetime64[ns]');self.assertEqual(calibration_time_mask(t,'2022-03-24T06:00:00Z').tolist(),[False,True,False,False])
 def test_calibration_C_or_reserved_B_not_allowed(self):
  for sat in ['B','C']:
   with self.assertRaises(ValueError):calibration_time_mask([], '2022-03-24T06:00:00Z',satellite=sat)
 def test_cutoff_requires_explicit_UTC(self):
  with self.assertRaises(ValueError):calibration_time_mask([],'2022-03-24T06:00:00')
 def test_EOS_SI_N2_analytic(self):self.assertAlmostEqual(float(three_species_density(1.,1000.,0.,0.)),28/8314/1000,places=15)
 def test_EOS_no_helium_equals_one(self):np.testing.assert_array_equal(helium_eos_density_ratio([0,.2],[0,.3],[0,0]),[1.,1.])
 def test_EOS_helium_reduces_same_PT_density(self):self.assertLess(float(helium_eos_density_ratio(.2,.3,.1)),1.)
 def test_EOS_invalid_states_rejected(self):
  with self.assertRaises(ValueError):helium_eos_density_ratio(.9,.3,.1)
  with self.assertRaises(ValueError):three_species_density(1.,0.,.2,.3)
 def test_secondary_never_qualified_as_complete_restart(self):
  from netCDF4 import Dataset
  with tempfile.TemporaryDirectory(dir=ROOT/'experiments') as td:
   p=Path(td)/'secondary.nc'
   with Dataset(p,'w') as n:n.createDimension('time',1);n.createDimension('mtimedim',3);n.createVariable('mtime','i4',('time','mtimedim'))[:]=[[83,0,0]];n.history_type='secondary'
   a=inspect_restart(p,[83,0,0]);self.assertFalse(a['structure_complete']);self.assertFalse(a['validated_continuation']);self.assertEqual(len(a['missing_required']),34)
 def test_source_clock_original_rule(self):
  check_source_clock([68,0,0],[80,0,0])
  with self.assertRaises(ValueError):check_source_clock([68,23,50],[80,0,0])
if __name__=='__main__':unittest.main()
