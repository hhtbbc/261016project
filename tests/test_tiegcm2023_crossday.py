"""Static tests only; never starts MPI or the model."""
from pathlib import Path
import importlib.util,unittest,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from atmosphere.tiegcm_drivers import GpiDriver
spec=importlib.util.spec_from_file_location('crossday',ROOT/'scripts/run_tiegcm2023_crossday.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class CrossdayTests(unittest.TestCase):
    def test_native_checkpoint_schedule(self):
        expected=[(77,0,0),(77,23,50),(78,0,0),(78,0,10)]
        self.assertEqual(c.schedule(),[c.seconds(t) for t in expected])
        self.assertEqual((c.schedule()[-1]-c.schedule()[0])//60,1450)
    def test_clock_and_no_overrides(self):
        text=c.configuration();c.validate_config(text)
        self.assertIn('SOURCE_START = 80 0 0',text);self.assertIn('MXHIST_PRIM = 1',text)
        self.assertNotIn(' POWER ',text)
    def test_configuration_mutation_rejected(self):
        with self.assertRaises(ValueError):c.validate_config(c.configuration().replace('STEP  = 60','STEP  = 120'))
    def test_single_frame_file_count(self):
        text=c.configuration()
        for i in range(1,5):self.assertIn(f"'primary_{i:03d}.nc'",text)

class DriverTests(unittest.TestCase):
    def setUp(self):
        self.d=GpiDriver(ROOT/'data/processed/tiegcm2023/gpi_20230312_20230325.nc')
    def test_midnight_reference(self):
        v=self.d.at(2023078,0)
        self.assertAlmostEqual(v['f107d'],141.04375)
        self.assertAlmostEqual(v['f107a'],161.75501543209876)
        self.assertEqual(v['Kp'],1.5);self.assertEqual(v['ctpoten'],39.3)
    def test_noon_exact_daily(self):
        i=list(self.d.days).index(2023077)
        v=self.d.at(2023077,43200)
        self.assertEqual(v['f107d'],self.d.f107d[i]);self.assertEqual(v['f107a'],self.d.f107a[i])
    def test_midnight_continuity(self):
        a=self.d.at(2023077,86399);b=self.d.at(2023078,0)
        for k in ['f107d','f107a','Kp']:self.assertLess(abs(a[k]-b[k]),.001)
    def test_time_overflow_and_missing_date_rejected(self):
        with self.assertRaises(ValueError):self.d.at(2023077,86400)
        with self.assertRaises(ValueError):self.d.at(2023060,0)
if __name__=='__main__':unittest.main()
