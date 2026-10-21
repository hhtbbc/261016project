import unittest,sys,json
from pathlib import Path
from unittest.mock import patch
import numpy as np
from astropy.time import Time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data
from orbit.common_force_model import CommonForceModel
from orbit.common_density_research import DensityResearchForce,demonstration_properties,LABELS,TimedDensity
from orbit.drag import DragForce,EarthFixedFrame,DragProperties
from orbit.two_body import make_state_derivative
from atmosphere.density_interface import ConstantDensityDemo

class CommonDensityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_time_data();c=json.loads((ROOT/'configs/provisional_common_force_model.json').read_text());cls.y=np.array(c['initial_state_GCRS_SI']);cls.t=Time(c['t0_utc'],scale='utc')
    def test_zero_drag_restores_H6(self):
        h=CommonForceModel(self.t,21600);base=make_state_derivative([h])
        for rho,cd,area in [(0.,2.2,1.),(1e-12,0.,1.),(1e-12,2.2,0.)]:
            drag=DragForce(EarthFixedFrame(self.t),ConstantDensityDemo(rho),DragProperties(400,area,cd,'synthetic'))
            np.testing.assert_array_equal(make_state_derivative([h,drag])(0,self.y),base(0,self.y))
    def test_all_models_actual_query_and_same_parameters(self):
        properties=[]
        with patch('pymsis.msis.get_f107_ap',side_effect=AssertionError('no network')):
            for name in ['C1','C2','C3']:
                f=DensityResearchForce(name,self.t)
                try:
                    z=f.evaluate(123.456789,self.y[:3],self.y[3:],phase='test');properties.append(z['properties'])
                    self.assertGreater(z['density_kg_m3'],0);self.assertEqual(tuple(f.last_record['labels']),LABELS)
                    self.assertLess(np.dot(z['relative_velocity_itrs_m_s'],z['acceleration_itrs_m_s2']),0)
                    if name!='C1':self.assertEqual(f.provider.query_external(None).reason,'EXTERNAL_DATUM_UNVERIFIED')
                finally:f.close()
        self.assertTrue(all(p==demonstration_properties() for p in properties))
    def test_failure_propagates_without_zero(self):
        f=DensityResearchForce('C1',self.t);f.provider.drivers._ap={}
        with self.assertRaises(ValueError):f(0,self.y[:3],self.y[3:])
        f.close()
    def test_ap_boundary_unchanged(self):
        f=DensityResearchForce('C1',self.t)
        self.assertEqual(f.provider.drivers.at(Time('2023-03-21T02:59:59.9999')).ap[1],9.)
        self.assertEqual(f.provider.drivers.at(Time('2023-03-21T03:00:00.0001')).ap[1],4.)
        f.close()
    def test_no_implicit_models(self):
        with self.assertRaises(ValueError):DensityResearchForce('C0',self.t)
    def test_timing_rejects_invalid_positive_density(self):
        class Bad:
            def density_kg_m3(self,q):return float('nan')
        with self.assertRaises(ValueError):TimedDensity(Bad()).density_kg_m3(None)
