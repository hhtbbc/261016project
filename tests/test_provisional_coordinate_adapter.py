import sys, unittest, importlib.util
from pathlib import Path
import numpy as np
from astropy.time import Time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from atmosphere.density_interface import DensityQuery
from atmosphere.provisional_coordinate_adapter import ProvisionalCoordinateAdapter,A_WGS84,B_SPHERE,diagnose_provisional_interpolation
from atmosphere.tiegcm_density_provider import TiegcmDensityProvider
spec=importlib.util.spec_from_file_location('native_fixture',ROOT/'tests/test_tiegcm_density_provider.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)

class GeometryTests(unittest.TestCase):
    def point(self,latitude,longitude,height=470000):
        # Independent forward WGS84 ellipsoid formula, not Astropy's inverse.
        a=6378137.; f=1/298.257223563; e2=f*(2-f)
        phi,lam=np.deg2rad([latitude,longitude]);N=a/np.sqrt(1-e2*np.sin(phi)**2)
        r=[(N+height)*np.cos(phi)*np.cos(lam),(N+height)*np.cos(phi)*np.sin(lam),(N*(1-e2)+height)*np.sin(phi)]
        return DensityQuery.from_itrs(Time('2023-03-21T00:05:00',scale='utc'),r)
    def test_equator(self):
        c=ProvisionalCoordinateAdapter(assumption=A_WGS84).adapt(self.point(0,0))
        self.assertAlmostEqual(c.model_zg_m,470000,6);self.assertAlmostEqual(c.model_latitude_deg,0,10)
    def test_midlatitude(self):
        q=self.point(45,30);c=ProvisionalCoordinateAdapter(assumption=A_WGS84).adapt(q)
        self.assertAlmostEqual(c.model_latitude_deg,45,9);self.assertAlmostEqual(c.model_zg_m,470000,5)
        self.assertGreater(c.model_latitude_deg-c.geocentric_latitude_deg,.1)
    def test_both_poles(self):
        for lat in [-87.4,87.4]:
            c=ProvisionalCoordinateAdapter(assumption=A_WGS84).adapt(self.point(lat,80))
            self.assertAlmostEqual(c.model_latitude_deg,lat,9)
    def test_dateline(self):
        for lon in [-179.999,179.999]:
            c=ProvisionalCoordinateAdapter(assumption=A_WGS84).adapt(self.point(20,lon))
            self.assertAlmostEqual(c.model_longitude_deg,lon,9)
    def test_spherical_geometry(self):
        q=DensityQuery.from_itrs(Time('2023-03-21'),[3e6,0,4e6])
        c=ProvisionalCoordinateAdapter(assumption=B_SPHERE,sphere_radius_m=4e6).adapt(q)
        self.assertAlmostEqual(c.model_zg_m,1e6,8);self.assertAlmostEqual(c.model_latitude_deg,53.13010235415598,10)
    def test_offsets(self):
        q=self.point(30,20)
        for offset in [-10000,-5000,-2000,0,2000,5000,10000]:
            c=ProvisionalCoordinateAdapter(assumption=A_WGS84,height_offset_m=offset).adapt(q)
            self.assertAlmostEqual(c.model_zg_m-q.height_wgs84_m,offset,8)
    def test_explicit_assumptions(self):
        with self.assertRaises(TypeError):ProvisionalCoordinateAdapter()
        with self.assertRaises(ValueError):ProvisionalCoordinateAdapter(assumption=B_SPHERE)
        with self.assertRaises(ValueError):ProvisionalCoordinateAdapter(assumption='VERIFIED')
    def test_no_drag_protocol(self):
        a=ProvisionalCoordinateAdapter(assumption=A_WGS84)
        self.assertFalse(hasattr(a,'density_kg_m3'))
        c=a.adapt(self.point(45,20));self.assertEqual(c.status,'PROVISIONAL');self.assertIn('not a validated',c.limitations)

class QueryTests(unittest.TestCase):
    # Reuse only fixture setup; do not duplicate the existing test cases.
    def setUp(self):
        self.fixture=fixture.DensityTests();self.fixture.setUp();self.p=self.fixture.p
    def tearDown(self):self.fixture.tearDown()
    def q(self,height=150,t='2023-03-21T00:05:00'):
        return DensityQuery.from_itrs(Time(t,scale='utc'),[6378137+height,0,0])
    def test_source_switch_and_provisional(self):
        for source in ['S3','S7']:
            with TiegcmDensityProvider([self.fixture.path],source) as p:
                result=ProvisionalCoordinateAdapter(assumption=A_WGS84).query_provisional(p,self.q())
                self.assertTrue(result.native_result.valid);self.assertEqual(result.status,'PROVISIONAL')
                self.assertEqual(result.native_result.metadata['source'],source)
    def test_top_failure(self):
        r=ProvisionalCoordinateAdapter(assumption=A_WGS84).query_provisional(self.p,self.q(301))
        self.assertFalse(r.native_result.valid);self.assertEqual(r.native_result.reason,'VERTICAL_OUTSIDE');self.assertEqual(r.status,'PROVISIONAL')
    def test_bottom_failure(self):
        r=ProvisionalCoordinateAdapter(assumption=A_WGS84).query_provisional(self.p,self.q(99))
        self.assertEqual(r.native_result.reason,'VERTICAL_OUTSIDE')
    def test_time_failure(self):
        r=ProvisionalCoordinateAdapter(assumption=A_WGS84).query_provisional(self.p,self.q(t='2023-03-20'))
        self.assertEqual(r.native_result.reason,'TIME_OUTSIDE')
    def test_formal_gate_unchanged(self):
        self.assertEqual(self.p.query_external(self.q()).reason,'EXTERNAL_DATUM_UNVERIFIED')
        with self.assertRaises(ValueError):self.p.density_kg_m3(self.q())
    def test_derivative_and_dimension_separation(self):
        result=ProvisionalCoordinateAdapter(assumption=A_WGS84).query_provisional(self.p,self.q())
        d=diagnose_provisional_interpolation(self.p,result)
        self.assertAlmostEqual(d['dlnrho_dh_per_m'],-.01,14)
        self.assertAlmostEqual(d['vertical_spacing_min_m'],100,8)
        self.assertAlmostEqual(d['horizontal_log_relative'],0,14)
        self.assertAlmostEqual(d['time_log_relative'],np.sqrt(2)/1.5-1,14)
        self.assertAlmostEqual(d['vertical_coarsened_log_relative'],0,14)
        self.assertAlmostEqual(d['bottom_margin_m'],50,6)

if __name__=='__main__':unittest.main()
