import sys,unittest
from pathlib import Path
import numpy as np
import astropy.units as u
from astropy.time import Time
from sgp4.api import Satrec,WGS72
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data,gps_calendar_to_time,transform_state,check_eop
from orbit.sgp4_baseline import read_archive,select_before,propagate,parse_tle
from evaluation.orbit_data import load_sp3_reference
from evaluation.orbit_metrics import rac_errors,summarize_errors

class OrbitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table,_=configure_time_data()
        cls.t=Time(['2023-03-21T00:00:02','2023-03-23T00:00:02'],scale='utc')
        cls.ref=load_sp3_reference((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))
        cls.records=read_archive(ROOT/'data/raw/orbits/tle/swarm_a_20230320_23_eth_archive.json')
    def test_gps_epoch_and_hdr_independent_anchor(self):
        self.assertLess(abs((gps_calendar_to_time(['1980-01-06T00:00:00'])[0]-Time('1980-01-06',scale='utc')).sec),1e-9)
        # Expected UTC comes from independent ESA .HDR, not a fixed-offset implementation.
        self.assertEqual(self.ref.times[0].utc.isot,'2023-03-20T23:59:42.000')
        self.assertTrue(all(x['hdr_time_difference_s']<1e-6 for x in self.ref.metadata['sources']))
    def test_exact_window_and_units(self):
        a=self.ref.take_exact(self.t)
        self.assertEqual(a.positions_m.shape,(2,3))
        self.assertTrue(np.all((np.linalg.norm(a.positions_m,axis=1)>6e6)&(np.linalg.norm(a.positions_m,axis=1)<8e6)))
        with self.assertRaises(ValueError):self.ref.take_exact(Time(['2023-03-20T00:00:00'],scale='utc'))
        with self.assertRaises(ValueError):self.ref.take_exact(Time(['2023-03-21T00:00:03'],scale='utc'))
    def test_definitive_eop_only(self):
        self.assertTrue(check_eop(self.t)['all_status_iers_b'])
        with self.assertRaises(ValueError):check_eop(Time(['2100-01-01'],scale='utc'))
    def test_tle_policy_and_checksum(self):
        self.assertEqual(len(self.records),8)
        with self.assertRaises(ValueError):select_before(self.records,self.t[0])
        selected=select_before(self.records,self.t[0],True)
        self.assertEqual(selected.epoch.utc.isot,'2023-03-20T20:30:00.330')
        with self.assertRaises(ValueError):parse_tle(selected.line1[:-1]+'0',selected.line2)
    def test_sgp4_vallado_reference_vector(self):
        a='1 00005U 58002B   00179.78495062  .00000023  00000-0  28098-4 0  4753'
        b='2 00005  34.2682 348.7242 1859667 331.7664  19.3264 10.82419157413667'
        record=parse_tle(a,b,expected_norad=5);r,v,e=propagate(record,Time([record.epoch]))
        # Vallado verification file tcppver.out distributed with python-sgp4.
        np.testing.assert_allclose(r[0],[7022465.29266,-1400082.96755,39.95155],atol=1e-5,rtol=0)
        np.testing.assert_allclose(v[0],[1893.841015,6405.893759,4534.807250],atol=1e-6,rtol=0)
        self.assertEqual(int(e[0]),0)
    def test_real_state_roundtrips(self):
        ref=self.ref.take_exact(self.t)
        for target in ['TEME','GCRS']:
            p,v=transform_state(ref.positions_m,ref.velocities_m_s,self.t,'ITRS',target)
            pr,vr=transform_state(p,v,self.t,target,'ITRS')
            self.assertLess(np.max(np.linalg.norm(pr-ref.positions_m,axis=1)),1e-3)
            self.assertLess(np.max(np.linalg.norm(vr-ref.velocities_m_s,axis=1)),1e-4)
    def test_earth_rotation_velocity(self):
        p,v=transform_state(np.array([[6378137.,0,0]]),np.zeros((1,3)),self.t[:1],'ITRS','GCRS')
        self.assertTrue(464<np.linalg.norm(v)<466)
    def test_rac_sign_norm_and_statistics(self):
        r=np.array([[1.,0,0],[1.,0,0]]);v=np.array([[0.,1,0],[0.,1,0]])
        d=np.array([[3.,4,12],[-3.,-4,-12]])
        rac=rac_errors(d,r,v);np.testing.assert_allclose(rac,d)
        np.testing.assert_allclose(np.linalg.norm(rac,axis=1),[13,13])
        s=summarize_errors(d,rac)
        self.assertEqual(s['mean_norm_m'],13);self.assertEqual(s['rmse_3d_m'],13)
        with self.assertRaises(ValueError):rac_errors(d,r,np.zeros_like(v))
if __name__=='__main__':unittest.main()
