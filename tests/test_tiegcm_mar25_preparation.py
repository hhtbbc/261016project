"""CPU-only static controls: never invokes the physical model."""
import unittest,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'scripts'),str(R/'src'),str(R)]
from prepare_tiegcm_2022_mar25_v1 import extended_text,namelist
import prepare_tiegcm_training_drivers as old
class Preparation(unittest.TestCase):
 def setUp(self):self.original=(R/'experiments/tiegcm_2022_b14_exploratory_pair_v2/B14/input.inp').read_text()
 def test_minimal_changes(self):
  a=namelist(self.original);b=namelist(extended_text(self.original,R/'experiments/tiegcm_2022_mar25_preparation_v1/gpi_2022_extended.nc'));self.assertEqual({k for k in a if a[k]!=b[k]},{'STOP','SECSTOP','OUTPUT','SECOUT','GPI_NCFILE'})
 def test_counts(self):
  b=namelist(extended_text(self.original,R/'new.nc'));self.assertEqual(b['OUTPUT'].count('.nc'),18);self.assertEqual(b['SECOUT'].count('.nc'),17);self.assertEqual(b['STOP'],'85 0 0')
 def test_no_restart(self):
  b=namelist(extended_text(self.original,R/'new.nc'));self.assertEqual(b['SOURCE_START'],'80 0 0');self.assertIn('smax',b['SOURCE']);self.assertEqual(b['START'],'68 0 0')
 def test_override_rejected(self):
  with self.assertRaises(AssertionError):extended_text(self.original.replace('\n/','\n KP = 2\n/'),R/'new.nc')
 def test_duplicate_rejected(self):
  with self.assertRaises(ValueError):old.decode({'datetime':['2022-03-28T00:00:00Z']*2,'Fobs':[100,100]},'Fobs')
 def test_nondef_rejected(self):
  with self.assertRaises(ValueError):old.decode({'datetime':['2022-03-28T00:00:00Z'],'Kp':[1],'status':['now']},'Kp')
 def test_bad_flux_rejected(self):
  for x in [-1,0,float('inf'),float('nan')]:
   with self.assertRaises(ValueError):old.decode({'datetime':['2022-03-28T00:00:00Z'],'Fobs':[x]},'Fobs')
if __name__=='__main__':unittest.main()
