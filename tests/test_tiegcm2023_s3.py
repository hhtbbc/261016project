import unittest,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('s3',Path(__file__).resolve().parents[1]/'scripts/run_tiegcm2023_s3.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class S3Tests(unittest.TestCase):
    def test_exact_schedule(self):
        p,q=m.schedules();self.assertEqual(len(p),7);self.assertEqual(len(q),14)
        self.assertEqual([len(v) for v in q],[4]+[24]*12+[1])
        self.assertEqual(len(sum(q,[])),293);self.assertEqual(sum(t>=80*86400 for t in sum(q,[])),290)
        self.assertEqual(sum(q,[])[-1],82*86400+600)
    def test_no_duplicate_boundary(self):
        for v in m.schedules():self.assertEqual(len(sum(v,[])),len(set(sum(v,[]))))
    def test_reviewed_config_and_overrides(self):
        t=m.configuration();m.validate(t)
        for old,new in [('STEP  = 60','STEP  = 30'),('START_YEAR = 2023','START_YEAR = 2002')]:
            with self.assertRaises(ValueError):m.validate(t.replace(old,new))
        with self.assertRaises(ValueError):m.validate(t.replace('\n/', '\n KP = 2\n/'))
    def test_continuous_source(self):
        t=m.configuration();self.assertIn('SOURCE_START = 80 0 0',t);self.assertIn('START = 77 0 0, 82 0 0',t);self.assertIn('SOURCE =',t)

class S3AuditInterpolationTests(unittest.TestCase):
    def test_exponential_density_at_native_height(self):
        import numpy as np
        spec=importlib.util.spec_from_file_location('audit_s3',Path(__file__).resolve().parents[1]/'scripts/audit_tiegcm2023_s3.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
        z=np.array([100.,200.,300.])[:,None,None];rho=np.exp(-z/50)
        np.testing.assert_allclose(a.at_height(z,rho,150),np.exp(-3),rtol=1e-14)
        self.assertTrue(np.isnan(a.at_height(z,rho,99)).all())
        self.assertTrue(np.isnan(a.at_height(z,rho,301)).all())

class S3ColdEchoTests(unittest.TestCase):
    def make_file(self,root,clock):
        import numpy as np
        from netCDF4 import Dataset
        p=root/'echo.nc'
        with Dataset(p,'w') as n:
            n.history_type='secondary';n.createDimension('time',1);n.createDimension('clock',3);n.createDimension('ilev',2);n.createDimension('lat',1);n.createDimension('lon',1)
            n.createVariable('mtime','i4',('time','clock'))[:]=[clock]
            for name in ['DEN','ZG']:n.createVariable(name,'f4',('time','ilev','lat','lon'),fill_value=np.float32(1e36))
        return p
    def test_native_uncomputed_cold_echo_excluded(self):
        import tempfile
        with tempfile.TemporaryDirectory(dir=m.ROOT/'.tmp') as d:m.basic_file(self.make_file(Path(d),[77,0,0]))
    def test_missing_warm_diagnostics_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory(dir=m.ROOT/'.tmp') as d:
            with self.assertRaises(AssertionError):m.basic_file(self.make_file(Path(d),[78,0,0]))
