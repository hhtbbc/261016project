from pathlib import Path
import sys,unittest
import numpy as np
from astropy.time import Time,TimeDelta
from astropy.coordinates import EarthLocation
import astropy.units as u
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from evaluation.orbit_data import OrbitSeries
from evaluation.orbit_interpolation import HermiteOrbit,signed_density_budget,contiguous_lag_correlation
from orbit.frames import gps_calendar_to_time


class CoordinateTests(unittest.TestCase):
    def setUp(self):
        self.t0=Time('2023-01-04T01:00:00',scale='utc');self.t=np.array([0.,10.,20.])
        self.p=lambda t:np.column_stack([t**3+2*t,3*t**2+4*t,np.ones(len(t))*100])
        self.v=lambda t:np.column_stack([3*t**2+2,6*t+4,np.zeros(len(t))])
        self.s=OrbitSeries(self.t0+TimeDelta(self.t,format='sec'),self.p(self.t),self.v(self.t),'ITRS',{})
    def test_exact_cubic_positions_and_derivative(self):
        q=np.array([0.,2.,9.,10.,18.,20.]);r=HermiteOrbit(self.s).evaluate(self.t0+TimeDelta(q,format='sec'))
        np.testing.assert_allclose(r.positions_m,self.p(q),rtol=2e-11,atol=2e-7)
        np.testing.assert_allclose(r.velocities_m_s,self.v(q),rtol=2e-11,atol=2e-8)
    def test_native_endpoints_preserved(self):
        r=HermiteOrbit(self.s).evaluate(self.s.times)
        np.testing.assert_array_equal(r.positions_m,self.s.positions_m);np.testing.assert_array_equal(r.velocities_m_s,self.s.velocities_m_s)
    def test_no_extrapolation(self):
        for q in ([-1.,2.],[2.,21.]):
            with self.assertRaises(ValueError):HermiteOrbit(self.s).evaluate(self.t0+TimeDelta(q,format='sec'))
    def test_missing_native_epoch_rejected(self):
        s=OrbitSeries(self.s.times[[0,2]],self.s.positions_m[[0,2]],self.s.velocities_m_s[[0,2]],'ITRS',{})
        with self.assertRaises(ValueError):HermiteOrbit(s)
    def test_retrospective_initialization_disclosed(self):
        r=HermiteOrbit(self.s).evaluate(self.t0+TimeDelta([2.,8.],format='sec'))
        self.assertAlmostEqual(r.metadata['future_bracket_max_s'],8.,places=7)
    def test_GPS_UTC_anchor(self):
        t=gps_calendar_to_time(['2023-01-04T01:00:18','2023-03-24T01:00:18'])
        np.testing.assert_allclose((t-Time(['2023-01-04T01:00:00','2023-03-24T01:00:00'],scale='utc')).sec,0,atol=1e-6)
    def test_GRS80_cartesian_roundtrip(self):
        e=EarthLocation.from_geodetic([0,90,-179]*u.deg,[-80,0,60]*u.deg,[470000]*3*u.m,ellipsoid='GRS80');geo=e.to_geodetic('GRS80')
        np.testing.assert_allclose(geo.height.to_value(u.m),470000,atol=1e-8)
        w=e.to_geodetic('WGS84');other=EarthLocation.from_geodetic(w.lon,w.lat,w.height,ellipsoid='WGS84')
        np.testing.assert_allclose(np.array([x.to_value(u.m) for x in e.geocentric]),np.array([x.to_value(u.m) for x in other.geocentric]),atol=1e-8)
    def test_signed_and_MSE_budget(self):
        r=signed_density_budget([1.,3.],[2.,2.],[1.,1.]);self.assertEqual(r['signed_identity_max_abs'],0)
        self.assertAlmostEqual(r['MSE_closure'],0);self.assertAlmostEqual(r['MSE_AI_Swarm'],r['MSE_AI_TIE']+r['MSE_TIE_Swarm']+r['cross_term'])
    def test_acf_does_not_compress_gaps(self):
        r=contiguous_lag_correlation(np.arange(8.),[0,1,2,3,5,6,7,8],max_lag=2)
        self.assertEqual(r[0]['pairs'],6);self.assertEqual(r[1]['pairs'],4)
    def test_common_denominator_relative_identity(self):
        r=signed_density_budget([2.,3.],[1.,4.],[1.,2.]);self.assertAlmostEqual(r['relative_MSE_AI_Swarm'],r['relative_MSE_AI_TIE']+r['relative_MSE_TIE_Swarm']+r['relative_cross_term'])


if __name__=='__main__':unittest.main()
