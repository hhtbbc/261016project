import sys,unittest,json
from pathlib import Path
import numpy as np
from scipy.special import eval_legendre
from scipy.spatial.transform import Rotation
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.higher_order_gravity import *
from orbit.j2 import j2_acceleration,j2_potential,J2_COEFFICIENT,EarthFigureAxis,terrestrial_z_in_gcrs
from orbit.two_body import central_gravity,make_state_derivative,EARTH_MU
from orbit.rk45_propagator import propagate
from orbit.frames import configure_time_data
from astropy.time import Time,TimeDelta


def spherical_reference(r,degree,cbar):
    # Independent GFZ positive W expansion in spherical coordinates, no production helper.
    radius=np.linalg.norm(r);phi=np.arcsin(r[2]/radius);lon=np.arctan2(r[1],r[0]);s=np.sin(phi)
    p=eval_legendre(degree,s)
    dp=degree*(s*p-eval_legendre(degree-1,s))/(s*s-1)
    amplitude=SOURCE_MU*SOURCE_RADIUS_M**degree*cbar*np.sqrt(2*degree+1)/radius**(degree+2)
    radial=-(degree+1)*amplitude*p;latitudinal=amplitude*dp*np.cos(phi)
    e_r=np.array([np.cos(phi)*np.cos(lon),np.cos(phi)*np.sin(lon),s]);e_phi=np.array([-s*np.cos(lon),-s*np.sin(lon),np.cos(phi)])
    return radial*e_r+latitudinal*e_phi

class HigherGravityTests(unittest.TestCase):
    def test_coefficients_rescaling_and_J2_convention(self):
        c=json.loads((ROOT/'configs/higher_order_gravity.json').read_text())
        for n,j,cb in [(3,J3,CBAR30),(4,J4,CBAR40)]:
            self.assertEqual(j,c['terms'][str(n)]['Jn_project'])
            self.assertAlmostEqual((EARTH_MU*J2_REFERENCE_RADIUS_M**n*j)/(-SOURCE_MU*SOURCE_RADIUS_M**n*np.sqrt(2*n+1)*cb),1,places=14)
        r=np.array([4e6,-2e6,5e6]);self.assertAlmostEqual(zonal_potential(r,2,J2_COEFFICIENT),j2_potential(r),places=11)
    def test_equator_and_poles(self):
        radius=6850000.;scale3=EARTH_MU*J3*J2_REFERENCE_RADIUS_M**3/radius**5;scale4=EARTH_MU*J4*J2_REFERENCE_RADIUS_M**4/radius**6
        np.testing.assert_allclose(j3_acceleration([radius,0,0]),[0,0,1.5*scale3],rtol=2e-14,atol=1e-20)
        np.testing.assert_allclose(j4_acceleration([radius,0,0]),[15/8*scale4,0,0],rtol=2e-14,atol=1e-20)
        for sign in [-1,1]:
            np.testing.assert_allclose(j3_acceleration([0,0,sign*radius]),[0,0,4*scale3],rtol=2e-14,atol=1e-20)
            np.testing.assert_allclose(j4_acceleration([0,0,sign*radius]),[0,0,sign*5*scale4],rtol=2e-14,atol=1e-20)
    def test_parity_and_decay(self):
        r=np.array([4e6,3e6,4e6])
        for n,j,fn in [(3,J3,j3_acceleration),(4,J4,j4_acceleration)]:
            np.testing.assert_allclose(fn(-r),(-1)**(n+1)*fn(r),rtol=2e-14)
            np.testing.assert_allclose(fn(2*r),fn(r)/2**(n+2),rtol=2e-14)
            self.assertAlmostEqual(zonal_potential(-r,n,j)/zonal_potential(r,n,j),(-1)**n,places=13)
    def test_independent_spherical_reference(self):
        rng=np.random.default_rng(20261020)
        for _ in range(50):
            r=rng.normal(size=3);r=r/np.linalg.norm(r)*rng.uniform(6.8e6,7e6)
            for n,cb,fn in [(3,CBAR30,j3_acceleration),(4,CBAR40,j4_acceleration)]:
                np.testing.assert_allclose(fn(r),spherical_reference(r,n,cb),rtol=2e-12,atol=1e-18)
    def test_negative_potential_gradient_and_convergence(self):
        r=np.array([4e6,-2e6,5e6])
        for n,j,fn in [(3,J3,j3_acceleration),(4,J4,j4_acceleration)]:
            analytic=fn(r);cs=[]
            for i in range(3):
                z=r.astype(complex);z[i]+=1e-10j;cs.append(-np.imag(zonal_potential(z,n,j))/1e-10)
            np.testing.assert_allclose(analytic,cs,rtol=2e-12,atol=1e-18)
            err=[]
            for h in [10000.,1000.,100.]:
                grad=np.array([-(zonal_potential(r+np.eye(3)[i]*h,n,j)-zonal_potential(r-np.eye(3)[i]*h,n,j))/(2*h) for i in range(3)])
                err.append(np.linalg.norm(grad-analytic)/np.linalg.norm(analytic))
            self.assertLess(err[1],err[0]/50);self.assertLess(err[2],err[1]/50);self.assertLess(err[-1],2e-7)
    def test_axis_rotation_and_frame_consistency(self):
        r=np.array([4e6,3e6,4e6]);k=np.array([0.,0.,1.]);Q=Rotation.from_rotvec([.3,-.4,.7]).as_matrix()
        for fn in [j3_acceleration,j4_acceleration]:np.testing.assert_allclose(fn(Q@r,Q@k),Q@fn(r,k),rtol=2e-12,atol=1e-18)
        configure_time_data();t=Time('2023-03-21T00:00:02',scale='utc');axis=EarthFigureAxis(t,21600,60)
        np.testing.assert_allclose(axis(0),terrestrial_z_in_gcrs(Time([t]))[0],rtol=0,atol=1e-15)
        self.assertGreater(np.linalg.norm(axis(0)-k),1e-4)
    def test_switch_off_and_superposition(self):
        r=np.array([6.85e6,0,0]);v=np.array([0,7600,100.]);k=lambda t:np.array([0.,0.,1.]);j2=lambda t,r,v:j2_acceleration(r)
        old=make_state_derivative([central_gravity,j2]);off=HigherOrderZonalForce(k,include_j3=False,include_j4=False)
        np.testing.assert_array_equal(old(0,np.r_[r,v]),make_state_derivative([central_gravity,j2,off])(0,np.r_[r,v]))
        a=propagate(old,r,v,(0,60),[0,60]);b=propagate(make_state_derivative([central_gravity,j2,off]),r,v,(0,60),[0,60]);np.testing.assert_array_equal(a.states,b.states)
        on=HigherOrderZonalForce(k,include_j3=True,include_j4=True)
        np.testing.assert_array_equal(on(0,r,v),j3_acceleration(r)+j4_acceleration(r))
    def test_invalid(self):
        for r,k in [([0,0,0],[0,0,1]),([np.nan,0,1],[0,0,1]),([1,0,0],[0,0,2])]:
            with self.assertRaises(ValueError):j3_acceleration(r,k)
    def test_fixed_axis_conservative_invariants(self):
        r=[6850000.,0,0];v=[0,5400.,5400.];k=np.array([0.,0.,1.]);t=np.arange(0,6001,60.)
        rhs=make_state_derivative([central_gravity,lambda t,r,v:j2_acceleration(r,k),HigherOrderZonalForce(lambda t:k,include_j3=True,include_j4=True)])
        a=propagate(rhs,r,v,(0,6000),t,rtol=1e-11,atol=[1e-4]*3+[1e-7]*3,max_step=20)
        b=propagate(rhs,r,v,(0,6000),t,rtol=1e-12,atol=[1e-5]*3+[1e-8]*3,max_step=10)
        def invariant(states):
            energy=np.sum(states[:,3:]**2,axis=1)/2-EARTH_MU/np.linalg.norm(states[:,:3],axis=1)
            energy+=np.array([j2_potential(r)+zonal_potential(r,3,J3)+zonal_potential(r,4,J4) for r in states[:,:3]])
            axial=np.cross(states[:,:3],states[:,3:])@k
            return max(abs(energy/energy[0]-1)),max(abs(axial/axial[0]-1))
        ea,ha=invariant(a.states);eb,hb=invariant(b.states)
        self.assertLess(ea,1e-8);self.assertLess(ha,1e-8);self.assertLess(eb,ea);self.assertLess(hb,ha)
        self.assertLess(np.max(np.linalg.norm(a.states[:,:3]-b.states[:,:3],axis=1)),.05)
if __name__=='__main__':unittest.main()
