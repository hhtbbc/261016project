import unittest,importlib.util,tempfile
from pathlib import Path
import numpy as np
from netCDF4 import Dataset
spec=importlib.util.spec_from_file_location('s7',Path(__file__).resolve().parents[1]/'scripts/run_tiegcm2023_s7.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class S7Tests(unittest.TestCase):
    def test_schedule(self):
        p,q=m.schedules();self.assertEqual(len(p),11);self.assertEqual(len(q),14);self.assertEqual([len(v) for v in q],[8]+[24]*12+[1]);self.assertEqual(len(sum(q,[])),297);self.assertEqual(len(set(sum(q,[]))),297);self.assertEqual(sum(t>=80*86400 for t in sum(q,[])),290)
    def test_fixed_config(self):
        t=m.configuration();m.validate(t);self.assertIn('START_DAY = 73',t);self.assertIn('SOURCE_START = 80 0 0',t)
        for change in [t.replace('STEP  = 60','STEP  = 30'),t.replace('\n/','\n KP = 2\n/')]:
            with self.assertRaises(ValueError):m.validate(change)
    def fixture(self,d,cold=True,bad=None):
        path=Path(d)/'secondary_001.nc';fill=np.float32(1e36)
        with Dataset(path,'w') as n:
            n.history_type='secondary';n.run_type='initial';n.createDimension('time',2 if cold else 1);n.createDimension('clock',3);n.createDimension('lev',3);n.createDimension('ilev',3);n.createDimension('lat',1);n.createDimension('lon',1)
            tv=n.createVariable('time','f8',('time',));tv.initial_year=2023;tv.initial_day=73;tv.initial_mtime=[73,0,0]
            n.createVariable('year','i4',('time',))[:]=2023
            n.createVariable('mtime','i4',('time','clock'))[:]=[[73,0,0],[74,0,0]] if cold else [[74,0,0]]
            for name in ['DEN','ZG','TN','UN','VN','O1','O2','N2','HE']:
                v=n.createVariable(name,'f4',('time','ilev' if name in ['DEN','ZG'] else 'lev','lat','lon'),fill_value=fill)
                v[:]= {'DEN':1e-12,'TN':1000,'UN':1,'VN':2,'O1':.5,'O2':.2,'N2':.25,'HE':.05}.get(name,0)
                if name=='ZG':v[:]=np.array([100,200,300])[None,:,None,None]
                if name in ['TN','UN','VN']:v[:,-1]=fill
                if cold and name in ['DEN','ZG','N2']:v[0]=fill
            if bad:
                name,index,value=bad;n[name][index]=value
        return path
    def test_cold_missing_and_warm_good(self):
        with tempfile.TemporaryDirectory(dir=m.ROOT/'.tmp') as d:m.basic_file(self.fixture(d))
    def test_warm_missing_rejected(self):
        for name in ['DEN','ZG','N2','O1']:
            with self.subTest(name=name),tempfile.TemporaryDirectory(dir=m.ROOT/'.tmp') as d:
                with self.assertRaises((AssertionError,ValueError)):m.basic_file(self.fixture(d,bad=(name,1,1e36)))
    def test_cold_prognostic_missing_rejected(self):
        with tempfile.TemporaryDirectory(dir=m.ROOT/'.tmp') as d:
            with self.assertRaises(ValueError):m.basic_file(self.fixture(d,bad=('TN',0,1e36)))
    def test_nan_and_negative_density_rejected(self):
        for value in [float('nan'),-1.]:
            with tempfile.TemporaryDirectory(dir=m.ROOT/'.tmp') as d:
                with self.assertRaises(ValueError):m.basic_file(self.fixture(d,bad=('DEN',1,value)))
    def test_wrong_cold_identity_rejected(self):
        with tempfile.TemporaryDirectory(dir=m.ROOT/'.tmp') as d:
            p=self.fixture(d)
            with Dataset(p,'a') as n:n.run_type='continuation'
            with self.assertRaises(AssertionError):m.basic_file(p)
    def test_existing_directory_refused(self):
        with tempfile.TemporaryDirectory(dir=m.ROOT/'.tmp') as d:
            with self.assertRaises(FileExistsError):m.prepare(Path(d))
    def test_launch_once_guard_precedes_model(self):
        # The exclusive marker itself rejects a second acquisition without MPI.
        with tempfile.TemporaryDirectory(dir=m.ROOT/'.tmp') as d:
            p=Path(d)/'launch_once.json'
            with p.open('x') as f:f.write('{}')
            with self.assertRaises(FileExistsError):p.open('x')
