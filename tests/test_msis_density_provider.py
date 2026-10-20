import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u
import pymsis
from atmosphere.msis_density_provider import FrozenGfzDrivers,MsisDrivers,MsisDensityProvider
from atmosphere.density_interface import DensityQuery
ROOT=Path(__file__).resolve().parents[1]

class TestMsis(unittest.TestCase):
    def setUp(self):
        self.d=FrozenGfzDrivers(ROOT/'configs/nrlmsis2023_gfz_frozen.json')
        self.p=MsisDensityProvider(self.d,version='2.1')
        self.t=Time('2023-03-21T00:00:02',scale='utc')
    def rho(self,h=475000,lon=0,lat=0):return self.p.query(self.t,lon,lat,h).rho_kg_m3
    def test_explicit_no_download_and_si(self):
        with patch('pymsis.msis.get_f107_ap',side_effect=AssertionError('Implicit weather forbidden')):
            r=self.rho();self.assertTrue(1e-14<r<1e-10)
        d=self.d.at(self.t)
        direct=pymsis.calculate([self.t.isot],[0],[0],[475],[d.f107_previous_day],[d.f107a_centered81],[d.ap],version='2.1',geomagnetic_activity=-1)
        self.assertEqual(r,float(direct[0,0]))
    def test_height_repeat(self):
        self.assertGreater(self.rho(400000),self.rho(500000));self.assertEqual(self.rho(),self.rho())
    def test_longitude_poles(self):
        self.assertEqual(self.rho(lon=180),self.rho(lon=-180))
        for lat in [-90,90]:self.assertGreater(self.rho(lat=lat),0)
    def test_invalid(self):
        for kw in [{'h':-1},{'h':np.nan},{'lat':91},{'lon':np.inf}]:
            with self.assertRaises(ValueError):self.rho(**kw)
        with self.assertRaises(ValueError):MsisDensityProvider(self.d,version='2.0')
        with self.assertRaises(ValueError):MsisDensityProvider(None,version='2.1')
        for ap in [(1,)*6,(1,)*8,(np.nan,)*7]:
            with self.assertRaises(ValueError):MsisDrivers(150,150,ap,'synthetic')
        with self.assertRaises(ValueError):self.d.at(Time('2022-01-01'))
    def test_contract_wgs84(self):
        for lon,lat in [(0,0),(179.99,45),(-179.99,-89.99)]:
            loc=EarthLocation.from_geodetic(lon*u.deg,lat*u.deg,475000*u.m)
            q=DensityQuery.from_itrs(self.t,np.array([x.to_value(u.m) for x in loc.geocentric]))
            self.assertAlmostEqual(q.height_wgs84_m,475000,places=6)
            self.assertAlmostEqual(q.latitude_deg,lat,places=10)
            self.assertAlmostEqual(self.p.density_kg_m3(q)/self.rho(lon=lon,lat=lat),1,places=6)
    def test_boundary_history_independent(self):
        from datetime import datetime,timedelta,timezone
        for iso in ['2023-03-20T23:59:59','2023-03-21T00:00:00','2023-03-21T02:59:59','2023-03-21T03:00:00','2023-03-23T00:00:00']:
            t=Time(iso);a=self.d.at(t);day=iso[:10]
            import json
            raw=json.loads((ROOT/'data/raw/tiegcm2023_sources/gfz_ap_support.json').read_text())
            stamp=np.array([v.removesuffix('Z') for v in raw['datetime']],dtype='datetime64[s]');k=int(np.searchsorted(stamp,np.datetime64(iso),side='right')-1)
            expected=[self.d._daily[day],*raw['ap'][k-3:k+1][::-1],np.mean(raw['ap'][k-11:k-3]),np.mean(raw['ap'][k-19:k-11])]
            np.testing.assert_array_equal(a.ap,expected)
    def test_solar_conventions_and_missing_history(self):
        import json
        from datetime import date,timedelta
        raw=json.loads((ROOT/'data/raw/meeting_sources/gfz_Fobs_spinup_support.txt').read_text())
        days=[x[:10] for x in raw['datetime']];values=raw['Fobs']
        for day in ['2023-03-20','2023-03-21','2023-03-22','2023-03-23']:
            i=days.index(day);d=self.d.at(Time(day))
            self.assertEqual(d.f107_previous_day,values[i-1])
            self.assertAlmostEqual(d.f107a_centered81,sum(values[i-40:i+41])/81,places=10)
        key='2023-03-20T21:00:00Z';del self.d._ap[key]
        with self.assertRaises(ValueError):self.d.at(self.t)

    def test_backend_invalid_rejected(self):
        with patch('pymsis.calculate',return_value=np.full((1,11),np.nan)):
            with self.assertRaises(ValueError):self.rho()

    def test_batch(self):
        r=self.p.query_batch(Time([self.t,self.t]),[0,10],[0,50],[475000,480000]);self.assertEqual(len(r),2)
        self.assertEqual(r[0].rho_kg_m3,self.rho())
        with self.assertRaises(ValueError):self.p.query_batch(Time([self.t,self.t]),[0],[0],[475000])
    def test_driving_response(self):
        class Fixed:
            def __init__(self,f,ap):self.f=f;self.ap=ap
            def at(self,t):return MsisDrivers(self.f,self.f,(self.ap,)*7,'SYNTHETIC TEST INPUT')
        def r(f,ap):return MsisDensityProvider(Fixed(f,ap),version='2.1').query(self.t,0,0,475000).rho_kg_m3
        self.assertGreater(r(200,4),r(80,4));self.assertGreater(r(150,100),r(150,4))
    def test_published_fortran_regression(self):
        # Pre-existing upstream double-precision Fortran reference, not generated here.
        ref=Path(pymsis.__file__).parent/'tests/msis2.1_test_ref_dp.txt'
        errors=[]
        for line in ref.read_text().splitlines()[1:]:
            s=line.split();year=int(s[0][:-3]);year+=1900 if year>60 else 2000
            date=np.datetime64(str(year))+np.timedelta64(int(s[0][-3:])-1,'D')+np.timedelta64(int(float(s[1])),'s')
            sec,alt,lat,lon,stl,fa,f,ap=map(float,s[1:9])
            out=pymsis.calculate([date],[lon],[lat],[alt],[f],[fa],[[ap]*7],version='2.1')[0]
            # Reference rho is g/cm3, pymsis rho SI; reference table rounded.
            expected=float(s[14])*1000
            errors.append(abs(float(out[0])/expected-1))
        self.assertLess(max(errors),.002)
    def test_formal_gate_retained(self):
        text=(ROOT/'src/atmosphere/tiegcm_density_provider.py').read_text()
        self.assertIn('EXTERNAL_DATUM_UNVERIFIED',text)
