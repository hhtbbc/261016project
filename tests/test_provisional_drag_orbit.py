import sys,unittest,json
from pathlib import Path
import numpy as np
from astropy.time import Time,TimeDelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from atmosphere.provisional_drag_provider import ProvisionalDragForce,ProvisionalDensityError,LABELS
from atmosphere.provisional_coordinate_adapter import ProvisionalCoordinateAdapter,A_WGS84
from atmosphere.tiegcm_density_provider import DensityResult,TiegcmDensityProvider
from orbit.drag import DragProperties,EarthFixedFrame,drag_acceleration
from orbit.two_body import central_gravity,make_state_derivative
from orbit.rk45_propagator import propagate
from orbit.frames import configure_time_data,transform_state

class SyntheticProvider:
    source='SYNTHETIC_TEST_ONLY'
    def __init__(self,rho=1e-12,valid=True):self.rho=rho;self.valid=valid
    def query_native(self,*args,**kwargs):return DensityResult(self.valid,self.rho,'TEST_INVALID' if not self.valid else '',{'source':self.source})
class IdentitySyntheticFrame:
    def state_to_itrs(self,t,r,v):return Time('2023-03-21')+TimeDelta(t,format='sec'),np.asarray(r),np.asarray(v),np.eye(3)
class ProvisionalDragTests(unittest.TestCase):
    def force(self,rho=1e-12,cd=2.2,area=1.,valid=True,frame=None,sink=None,provider=None):
        return ProvisionalDragForce(frame=frame or IdentitySyntheticFrame(),provider=provider or SyntheticProvider(rho,valid),adapter=ProvisionalCoordinateAdapter(assumption=A_WGS84),properties=DragProperties(400.,area,cd,LABELS[1]),acknowledge_provisional=True,audit_sink=sink)
    def test_explicit_parameters_and_labels(self):
        with self.assertRaises(TypeError):ProvisionalDragForce()
        with self.assertRaises(ValueError):ProvisionalDragForce(frame=IdentitySyntheticFrame(),provider=SyntheticProvider(),adapter=ProvisionalCoordinateAdapter(assumption=A_WGS84),properties=DragProperties(400,1,2.2,'SYNTHETIC'),acknowledge_provisional=True)
        records=[];result=self.force(sink=records.append).evaluate(0,[6800000,0,0],[0,7500,0],phase='test')
        self.assertEqual(result['labels'],LABELS);self.assertEqual(tuple(records[0]['labels']),LABELS)
        self.assertEqual(records[0]['mapping']['status'],'PROVISIONAL')
    def test_zero_integrations_identical(self):
        r=[6800000.,0,0];v=[0,7656.,0];times=np.arange(0,61,10.)
        base=propagate(make_state_derivative([central_gravity]),r,v,(0,60),times)
        for f in [self.force(rho=0),self.force(cd=0),self.force(area=0)]:
            run=propagate(make_state_derivative([central_gravity,f]),r,v,(0,60),times)
            np.testing.assert_array_equal(base.states,run.states)
            self.assertEqual(f.phase_calls['rhs'],run.statistics['nfev'])
    def test_direction_scaling_si(self):
        r=[6800000.,0,0];v=np.array([0,7500.,0]);a=self.force()(0,r,v)
        np.testing.assert_allclose(a,[0,-1.546875e-7,0],atol=1e-20)
        self.assertLess(np.dot(a,v),0);np.testing.assert_allclose(self.force(rho=2e-12)(0,r,v),2*a,rtol=1e-14)
    def test_invalid_stops_integration(self):
        for f in [self.force(valid=False),self.force(rho=np.nan),self.force(rho=-1)]:
            with self.assertRaises(ProvisionalDensityError):propagate(make_state_derivative([central_gravity,f]),[6800000.,0,0],[0,7500,0],(0,60),[0,60])
            self.assertEqual(f.bridge.failures,1)
    def test_full_frame_state_force_rotation(self):
        configure_time_data();epoch=Time('2023-03-21T00:00:02',scale='utc')
        re=np.array([[6800000.,0,0]]);ve=np.array([[0,7300.,10.]])
        r,v=transform_state(re,ve,Time([epoch]),'ITRS','GCRS');frame=EarthFixedFrame(epoch)
        result=self.force(frame=frame).evaluate(0,r[0],v[0],phase='test')
        np.testing.assert_allclose(result['relative_velocity_itrs_m_s'],ve[0],atol=1e-7,rtol=0)
        Q=frame.state_to_itrs(0,r[0],v[0])[3]
        np.testing.assert_allclose(result['acceleration_gcrs_m_s2'],Q.T@drag_acceleration(1e-12,2.2,1,400,ve[0]),atol=1e-17,rtol=1e-10)
        self.assertAlmostEqual(np.linalg.norm(result['acceleration_gcrs_m_s2']),np.linalg.norm(result['acceleration_itrs_m_s2']),20)
    def test_real_sources_same_state_drag_ratio_and_formal_gate(self):
        configure_time_data();epoch=Time('2023-03-21T00:00:02',scale='utc')
        meta=json.loads((ROOT/'experiments/rk45_j2_v1/summary.json').read_text());r=meta['initial_gcrs_position_m'];v=meta['initial_gcrs_velocity_m_s'];values=[]
        for source in ['S3','S7']:
            with TiegcmDensityProvider((ROOT/f'experiments/tiegcm2023_{source.lower()}_continuous_v1').glob('secondary_*.nc'),source) as p:
                self.assertEqual(p.query_external(None).reason,'EXTERNAL_DATUM_UNVERIFIED')
                values.append(self.force(frame=EarthFixedFrame(epoch),provider=p).evaluate(0,r,v,phase='test'))
        ratio=values[0]['density_kg_m3']/values[1]['density_kg_m3']
        np.testing.assert_allclose(values[0]['acceleration_gcrs_m_s2'],values[1]['acceleration_gcrs_m_s2']*ratio,rtol=1e-14,atol=1e-23)
if __name__=='__main__':unittest.main()
