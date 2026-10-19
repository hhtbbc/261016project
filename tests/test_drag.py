"""Synthetic parameters only; no Swarm drag accuracy claim."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from astropy.time import Time
from orbit.drag import drag_acceleration,DragProperties,DragForce,EarthFixedFrame
from orbit.frames import configure_time_data,transform_state
from atmosphere.density_interface import ConstantDensityDemo,DensityQuery

class DragTests(unittest.TestCase):
    def test_synthetic_orbit_energy_and_work(self):
        from orbit.two_body import EARTH_MU,central_gravity,make_state_derivative,invariants
        from orbit.rk45_propagator import propagate
        from scipy.integrate import simpson
        radius=6778137.;speed=np.sqrt(EARTH_MU/radius)
        omega=np.array([0,0,7.292115e-5])
        def force(t,r,v):
            return drag_acceleration(1e-12,2.2,1.,100.,v-np.cross(omega,r))
        times=np.linspace(0,600,301)
        run=propagate(make_state_derivative([central_gravity,force]),[radius,0,0],
                      [0,speed,0],(0,600),times,rtol=1e-12,
                      atol=[1e-5]*3+[1e-8]*3,max_step=10.)
        energy,_=invariants(run.states)
        power=np.array([np.dot(y[3:],force(t,y[:3],y[3:])) for t,y in zip(times,run.states)])
        work=simpson(power,x=times)
        self.assertTrue(np.all(power<0))
        self.assertLess(energy[-1]-energy[0],0)
        self.assertLess(abs((energy[-1]-energy[0]-work)/work),1e-4)

    def test_zero_and_direction(self):
        v=np.array([7500.,20.,-10.])
        np.testing.assert_array_equal(drag_acceleration(0,2.2,1,100,v),np.zeros(3))
        np.testing.assert_array_equal(drag_acceleration(1e-12,2.2,1,100,np.zeros(3)),np.zeros(3))
        a=drag_acceleration(1e-12,2.2,1,100,v)
        self.assertLess(np.dot(a,v),0);np.testing.assert_allclose(np.cross(a,v),0,atol=1e-16)
    def test_scalings_and_si_value(self):
        v=np.array([7500.,0,0]);a=drag_acceleration(1e-12,2.2,1,100,v)
        np.testing.assert_allclose(a,[-6.1875e-7,0,0],atol=1e-20)
        np.testing.assert_allclose(drag_acceleration(2e-12,2.2,1,100,v),2*a)
        np.testing.assert_allclose(drag_acceleration(1e-12,2.2,2,100,v),2*a)
        np.testing.assert_allclose(drag_acceleration(1e-12,2.2,1,200,v),a/2)
    def test_invalid_inputs(self):
        for rho,cd,area,mass in [(-1,2,1,100),(1,-2,1,100),(1,2,-1,100),(1,2,1,0),(np.nan,2,1,100)]:
            with self.assertRaises(ValueError):drag_acceleration(rho,cd,area,mass,[1,0,0])
        with self.assertRaises(ValueError):ConstantDensityDemo(-1)
        with self.assertRaises(ValueError):DragProperties(100,1,2.2,'')
    def test_full_frame_corotation_and_wind(self):
        configure_time_data();times=Time(['2023-03-21T00:00:02'],scale='utc')
        r_e=np.array([[6778137.,0,0]]);v_e=np.zeros((1,3))
        r,v=transform_state(r_e,v_e,times,'ITRS','GCRS')
        self.assertGreater(np.linalg.norm(v),400.)
        force=DragForce(EarthFixedFrame(times[0]),ConstantDensityDemo(1e-12),DragProperties(100,1,2.2,'SYNTHETIC'))
        result=force.evaluate(0,r[0],v[0]);self.assertLess(np.linalg.norm(result['relative_velocity_itrs_m_s']),1e-7)
        self.assertLess(np.linalg.norm(result['acceleration_gcrs_m_s2']),1e-24)
        class Wind:
            def wind_itrs_m_s(self,q):return np.array([0,100.,0])
        windy=DragForce(force.frame,force.density,force.properties,wind=Wind())
        value=windy.evaluate(0,r[0],v[0])
        np.testing.assert_allclose(value['relative_velocity_itrs_m_s'],[0,-100,0],atol=1e-7)
        self.assertGreater(value['acceleration_itrs_m_s2'][1],0)
        class Area:
            def __call__(self,q,rel):return DragProperties(100,2,2.2,'SYNTHETIC area callback')
        doubled=DragForce(force.frame,force.density,force.properties,wind=Wind(),properties_provider=Area())
        np.testing.assert_allclose(doubled(0,r[0],v[0]),2*windy(0,r[0],v[0]),rtol=1e-14)
    def test_query_and_provider_validation(self):
        query=DensityQuery.from_itrs(Time('2023-03-21'),np.array([6778137.,0,0]))
        self.assertAlmostEqual(query.height_wgs84_m,400000.,places=6)
        self.assertEqual(ConstantDensityDemo(1e-12).density_kg_m3(query),1e-12)
        class BadDensity:
            def density_kg_m3(self,q):return -1
        configure_time_data();force=DragForce(EarthFixedFrame(Time('2023-03-21')),BadDensity(),DragProperties(100,1,2.2,'SYNTHETIC'))
        with self.assertRaises(ValueError):force(0,[6778137.,0,0],[0,7500.,0])

if __name__=='__main__':unittest.main()
