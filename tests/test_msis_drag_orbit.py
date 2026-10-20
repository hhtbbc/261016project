import sys,json,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from astropy.time import Time,TimeDelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from atmosphere.msis_density_provider import FrozenGfzDrivers,MsisDensityProvider,MsisResult
from atmosphere.msis_drag_provider import MsisResearchDrag
from atmosphere.density_interface import ConstantDensityDemo,DensityQuery
from atmosphere.provisional_drag_provider import LABELS
from orbit.drag import EarthFixedFrame,DragForce,DragProperties,drag_acceleration
from orbit.frames import configure_time_data,transform_state
from orbit.two_body import central_gravity,make_state_derivative
from orbit.rk45_propagator import propagate

class MsisDragTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_time_data();cls.t0=Time('2023-03-21T00:00:02',scale='utc')
        m=json.loads((ROOT/'experiments/provisional_drag_orbit_v1/D0.json').read_text())
        cls.state=np.asarray(m['initial_state'])
    def provider(self):return MsisDensityProvider(FrozenGfzDrivers(ROOT/'configs/nrlmsis2023_gfz_frozen.json'),version='2.1')
    def force(self,p=None,sink=None):return MsisResearchDrag(frame=EarthFixedFrame(self.t0),provider=p or self.provider(),properties=DragProperties(400,1,2.2,LABELS[1]),acknowledge_provisional=True,audit_sink=sink)
    def test_irregular_rhs_and_provenance(self):
        records=[];f=self.force(sink=records.append)
        with patch('pymsis.msis.get_f107_ap',side_effect=AssertionError('No automatic retrieval')):
            v=f.evaluate(123.456789,self.state[:3],self.state[3:],phase='test')
        q=v['query'];self.assertEqual(tuple(records[0]['labels']),LABELS)
        self.assertIn('2.1',records[0]['source']);self.assertEqual(len(records[0]['drivers']['ap']),7)
        self.assertAlmostEqual((q.utc-self.t0).to_value('s'),123.456789,places=7)
        self.assertEqual(records[0]['position_itrs_m'],q.position_itrs_m.tolist())
        self.assertGreater(v['density_kg_m3'],0)
    def test_submillisecond_time_and_ap_boundary(self):
        p=self.provider();a=Time('2023-03-21T02:59:59.9999');b=Time('2023-03-21T03:00:00.0001')
        self.assertEqual(p.drivers.at(a).ap[1],9);self.assertEqual(p.drivers.at(b).ap[1],4)
        import pymsis
        original=pymsis.calculate;seen=[]
        def capture(*args,**kwargs):seen.append(args[0].copy());return original(*args,**kwargs)
        with patch('pymsis.calculate',side_effect=capture):
            p.query(a,0,0,475000);p.query(b,0,0,475000)
        self.assertLess(seen[0][0],np.datetime64('2023-03-21T03:00:00'))
        self.assertGreater(seen[1][0],np.datetime64('2023-03-21T03:00:00'))
    def test_full_velocity_formula_and_si(self):
        r=np.array([[6800000.,0,0]]);v=np.array([[0,7300.,10.]])
        rg,vg=transform_state(r,v,Time([self.t0]),'ITRS','GCRS')
        f=self.force();value=f.evaluate(0,rg[0],vg[0],phase='test')
        np.testing.assert_allclose(value['relative_velocity_itrs_m_s'],v[0],atol=1e-7,rtol=0)
        _,_,_,Q=f.force.frame.state_to_itrs(0,rg[0],vg[0])
        expected=drag_acceleration(value['density_kg_m3'],2.2,1,400,v[0])
        np.testing.assert_allclose(value['acceleration_gcrs_m_s2'],Q.T@expected,rtol=1e-10,atol=1e-20)
        self.assertLess(np.dot(value['acceleration_itrs_m_s2'],v[0]),0)
    def test_zero_terms_restore_original_rhs(self):
        # Independent existing drag supports synthetic zero density; real MSIS rejects invalid zero.
        r=[6800000.,0,0];v=[0,7650.,0];base=make_state_derivative([central_gravity])
        for rho,cd,area in [(0,2.2,1),(1e-12,0,1),(1e-12,2.2,0)]:
            f=DragForce(EarthFixedFrame(self.t0),ConstantDensityDemo(rho),DragProperties(400,area,cd,'SYNTHETIC TEST'))
            np.testing.assert_array_equal(make_state_derivative([central_gravity,f])(0,np.r_[r,v]),base(0,np.r_[r,v]))
    def test_missing_driver_immediate_failure(self):
        p=self.provider();p.drivers._ap={};f=self.force(p)
        with self.assertRaises(ValueError):f(0,self.state[:3],self.state[3:])
        self.assertEqual(f.bridge.failures,1)
    def test_invalid_density_and_labels_rejected(self):
        p=self.provider()
        with patch.object(p,'query',return_value=MsisResult(np.nan,'TEST',p.drivers.at(self.t0))):
            with self.assertRaises(ValueError):self.force(p)(0,self.state[:3],self.state[3:])
        with self.assertRaises(ValueError):MsisResearchDrag(frame=EarthFixedFrame(self.t0),provider=p,properties=DragProperties(400,1,2.2,'real'),acknowledge_provisional=True)
    def test_original_formal_gate(self):
        from atmosphere.tiegcm_density_provider import TiegcmDensityProvider
        with TiegcmDensityProvider((ROOT/'experiments/tiegcm2023_s3_continuous_v1').glob('secondary_*.nc'),'S3') as p:
            self.assertEqual(p.query_external(None).reason,'EXTERNAL_DATUM_UNVERIFIED')
if __name__=='__main__':unittest.main()
