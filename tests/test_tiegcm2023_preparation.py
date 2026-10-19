import unittest
from pathlib import Path
import numpy as np
from netCDF4 import Dataset
from atmosphere.coverage import stencil_coverage
ROOT=Path(__file__).resolve().parents[1]
class PreparationTests(unittest.TestCase):
    def test_conservative_coverage(self):
        z=np.tile([100e3,500e3],(3,8,1));r=np.ones_like(z)*1e-12
        d=stencil_coverage([470e3,510e3,470e3],z,r,[True,True,False])
        np.testing.assert_array_equal(d['valid'],[True,False,False])
        self.assertEqual(d['valid_fraction'],1/3)
        z[0,7,-1]=460e3
        self.assertEqual(stencil_coverage([470e3]*3,z,r,[True]*3)['valid_count'],2)
    def test_driver_structure_and_padding(self):
        with Dataset(ROOT/'data/processed/tiegcm2023/gpi_20230312_20230325.nc') as n:
            self.assertEqual(n['kp'].shape,(14,8));self.assertEqual(n['kp'].dimensions,('ndays','nkp'))
            self.assertEqual(n.yearday_beg,2023073);self.assertEqual(n.yearday_end,2023082)
            self.assertTrue(np.all(np.diff(n['year_day'][:])==1))
            self.assertTrue(np.all((n['kp'][:]>=0)&(n['kp'][:]<=9)))
    def test_missing_density_rejected(self):
        z=np.tile([100e3,500e3],(1,8,1));r=np.ones_like(z)*1e-12;r[0,0,0]=np.nan
        self.assertEqual(stencil_coverage([470e3],z,r,[True])['valid_count'],0)
if __name__=='__main__':unittest.main()
