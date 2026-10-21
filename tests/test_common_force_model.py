import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import numpy as np
from astropy.time import Time
from orbit.frames import configure_time_data
from orbit.common_force_model import CommonForceModel
from orbit.spherical_harmonics_gravity import GcrsSphericalHarmonicsForce
from orbit.gravity_degree40 import Degree40EarthGravity
from orbit.gravity_truncation import ExtendedEarthGravity
from orbit.third_body_gravity import ThirdBodyGravity

class CommonForceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_time_data(); cls.epoch=Time('2023-03-21T00:00:02',scale='utc')
    def test_disabled_is_H4(self):
        c=CommonForceModel(self.epoch,21600,third_bodies=False)
        f=GcrsSphericalHarmonicsForce(self.epoch,Degree40EarthGravity(40))
        for r in ([6800000.,0,0],[0,0,6900000.],[4000000.,4000000.,4000000.]):
            np.testing.assert_array_equal(c(300,r,[0,0,0]),f(300,r,[0,0,0]))
    def test_degree20_is_H5(self):
        c=CommonForceModel(self.epoch,21600,degree=20)
        e=GcrsSphericalHarmonicsForce(self.epoch,ExtendedEarthGravity(20));t=ThirdBodyGravity(self.epoch,21600)
        r=np.array([6800000.,100000.,200000.]);v=np.array([0.,7500.,0.])
        np.testing.assert_array_equal(c(180,r,v),e(180,r,v)+t(180,r,v))
    def test_components_once_and_continuous(self):
        c=CommonForceModel(self.epoch,21600);r=np.array([6800000.,0,0]);v=np.zeros(3)
        np.testing.assert_allclose(c(10,r,v),c.earth(10,r,v)+sum(c.third.components(10,r).values()),rtol=0,atol=0)
        self.assertLess(np.linalg.norm(c(10.001,r,v)-c(10,r,v)),1e-6)
    def test_metadata(self):
        c=CommonForceModel(self.epoch,21600)
        self.assertEqual(c.metadata['earth_component_count'],1)
        self.assertFalse(c.metadata['truncation_convergence_proven'])
        self.assertEqual(c.metadata['ephemeris']['status'],'PROVISIONAL_EPHEMERIS')
    def test_time_bounds(self):
        c=CommonForceModel(self.epoch,21600)
        for t in [-1,21601]:
            with self.assertRaises(ValueError): c(t,np.array([6800000.,0,0]),np.zeros(3))
