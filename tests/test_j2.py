"""Independent physical checks before real-orbit experiments."""
from pathlib import Path
import sys, unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from astropy.time import Time, TimeDelta
from orbit.two_body import EARTH_MU, central_gravity, make_state_derivative
from orbit.j2 import (J2_COEFFICIENT, J2_REFERENCE_RADIUS_M, j2_acceleration,
                      j2_potential, fixed_axis_invariants, terrestrial_z_in_gcrs, EarthFigureAxis)
from orbit.rk45_propagator import propagate
from orbit.frames import configure_time_data, transform_state


def fixed_axis_experiment():
    a=7e6;e=.01;i=np.deg2rad(55.)
    initial=np.array([a*(1-e),0,0,0,*([0,0])],float)
    speed=np.sqrt(EARTH_MU*(1+e)/(a*(1-e)))
    initial[3:]=[0,speed*np.cos(i),speed*np.sin(i)]
    rhs=make_state_derivative([central_gravity,lambda t,r,v:j2_acceleration(r)])
    times=np.arange(0,172801,60,dtype=float)
    run=propagate(rhs,initial[:3],initial[3:],(0,times[-1]),times,rtol=1e-11,
                  atol=[1e-4]*3+[1e-7]*3,max_step=30.)
    energy,hz=fixed_axis_invariants(run.states)
    h=np.cross(run.states[:,:3],run.states[:,3:])
    node=np.cross(np.array([0,0,1.]),h)
    raan=np.unwrap(np.arctan2(node[:,1],node[:,0]))
    fit=np.polyfit(times,raan,1)
    theoretical=-1.5*np.sqrt(EARTH_MU/a**3)*J2_COEFFICIENT*(J2_REFERENCE_RADIUS_M/(a*(1-e*e)))**2*np.cos(i)
    result={'a_m':a,'e':e,'inclination_deg':55.,'duration_s':172800,
        'max_relative_total_energy_drift':float(np.max(abs((energy-energy[0])/energy[0]))),
        'max_relative_axial_h_drift':float(np.max(abs((hz-hz[0])/hz[0]))),
        'raan_theory_deg_day':float(np.rad2deg(theoretical)*86400),
        'raan_measured_deg_day':float(np.rad2deg(fit[0])*86400),
        'raan_rate_relative_difference':float(abs(fit[0]/theoretical-1)),
        'raan_fit_method':'OLS unwrapped osculating node, 48 h, no reference orbit',
        'integration':run.statistics}
    return run, result, energy, hz, raan


class J2Tests(unittest.TestCase):
    def test_directions_scaling_magnitude(self):
        r=6778137.;k=1.5*EARTH_MU*J2_COEFFICIENT*J2_REFERENCE_RADIUS_M**2/r**4
        np.testing.assert_allclose(j2_acceleration([r,0,0]),[-k,0,0],atol=1e-16)
        np.testing.assert_allclose(j2_acceleration([0,0,r]),[0,0,2*k],atol=1e-16)
        np.testing.assert_allclose(j2_acceleration([2*r,0,0]),j2_acceleration([r,0,0])/16,atol=1e-16)
        ratio=k/(EARTH_MU/r**2);self.assertTrue(.001<ratio<.002)
        with self.assertRaises(ValueError):j2_acceleration([0,0,0])
        with self.assertRaises(ValueError):j2_acceleration([r,0,0],axis=[0,0,2])
    def test_independent_potential_gradient(self):
        # Fourth-order finite difference of scalar potential, tilted figure axis.
        k=np.array([.2,.3,.9]);k/=np.linalg.norm(k)
        for r in [np.array([6e6,2e6,3e6]),np.array([-3e6,5e6,-4e6])]:
            gradient=[];h=100.
            for unit in np.eye(3):
                gradient.append((j2_potential(r-2*h*unit,k)-8*j2_potential(r-h*unit,k)+8*j2_potential(r+h*unit,k)-j2_potential(r+2*h*unit,k))/(12*h))
            np.testing.assert_allclose(j2_acceleration(r,k),-np.array(gradient),rtol=1e-9,atol=1e-12)
    def test_component_formula_reference(self):
        # Independent Cartesian expression checked against Orekit 13.0.3 source,
        # computeAccelerationInJ2Frame; no Orekit installation or execution claim.
        r=np.array([3e6,-4e6,5e6]);x,y,z=r;rr=np.dot(r,r)
        f=3*J2_COEFFICIENT*EARTH_MU*J2_REFERENCE_RADIUS_M**2/(2*rr**2.5)
        expected=f*np.array([x*(5*z*z/rr-1),y*(5*z*z/rr-1),z*(5*z*z/rr-3)])
        np.testing.assert_allclose(j2_acceleration(r),expected,rtol=1e-14,atol=1e-16)
        # Rotational covariance for a non-coordinate-aligned symmetry axis.
        angle=.4;Q=np.array([[np.cos(angle),0,np.sin(angle)],[0,1,0],[-np.sin(angle),0,np.cos(angle)]])
        np.testing.assert_allclose(j2_acceleration(Q@r,Q@np.array([0,0,1.])),Q@expected,atol=1e-16)
    def test_fixed_axis_energy_hz_and_secular_node(self):
        _,result,*_=fixed_axis_experiment()
        self.assertLess(result['max_relative_total_energy_drift'],1e-7)
        self.assertLess(result['max_relative_axial_h_drift'],1e-7)
        # First-order averaged theory applied to osculating initial elements;
        # allow higher-order and mean/osculating differences, not numerical fitting.
        self.assertLess(result['raan_rate_relative_difference'],.01)
        self.assertLess(result['raan_measured_deg_day'],0)
    def test_axis_frame_and_interpolation(self):
        configure_time_data();epoch=Time('2023-03-21T00:00:02',scale='utc')
        seconds=np.array([0.,30.,86430.,172800.]);times=epoch+TimeDelta(seconds,format='sec')
        directions=terrestrial_z_in_gcrs(times)
        expected,_=transform_state(np.tile([0,0,1.],(len(times),1)),np.zeros((len(times),3)),times,'ITRS','GCRS')
        np.testing.assert_allclose(directions,expected,atol=1e-14,rtol=0)
        self.assertGreater(np.linalg.norm(directions[0]-[0,0,1]),1e-3)
        axis=EarthFigureAxis(epoch,172800.)
        np.testing.assert_allclose([axis(t) for t in seconds],directions,atol=1e-11,rtol=0)
        with self.assertRaises(ValueError):axis(-1)
        with self.assertRaises(ValueError):axis(172801)

if __name__=='__main__':unittest.main()
