import unittest,importlib.util
from pathlib import Path
from math import sqrt
import numpy as np
from orbit.spherical_harmonics_gravity import SphericalHarmonicsGravity,GM,RADIUS_M
from orbit.j2 import j2_acceleration
from orbit.higher_order_gravity import j3_acceleration,j4_acceleration

def external_reference(model,p):
    so=next(Path(__file__).resolve().parents[1].glob('.local/reference/pyshtools_4_14_1/pyshtools/_SHTOOLS*.so'))
    spec=importlib.util.spec_from_file_location('_SHTOOLS',so);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    c=np.zeros((2,model.degree+1,model.degree+1))
    for (n,m),v in model.coefficients.items():c[:,n,m]=v
    r=np.linalg.norm(p);lat=np.arcsin(p[2]/r);lon=np.arctan2(p[1],p[0]);cl,sl=np.cos(lat),np.sin(lat);co,si=np.cos(lon),np.sin(lon)
    result=module.MakeGravGridPoint(c,model.gm,model.radius_m,r,np.rad2deg(lat),np.rad2deg(lon),lmax=model.degree,omega=0.)
    # f2py wrapper may return status followed by vector.
    if isinstance(result,tuple):
        if np.isscalar(result[0]):assert result[0]==0
        result=next(x for x in result if np.shape(x)==(3,))
    return np.asarray(result)@np.array([[cl*co,cl*si,sl],[sl*co,sl*si,-cl],[-si,co,0.]])

class TestSphericalGravity(unittest.TestCase):
    def test_central(self):
        p=np.array([4e6,-3e6,5e6]);m=SphericalHarmonicsGravity(0,0)
        np.testing.assert_allclose(m.acceleration_itrs(p),-GM*p/np.linalg.norm(p)**3,rtol=2e-15)
    def test_j2_and_zonals(self):
        allm=SphericalHarmonicsGravity(4,0);p=np.array([4e6,-3e6,5e6]);expected=-GM*p/np.linalg.norm(p)**3
        for n,fn in [(2,j2_acceleration),(3,j3_acceleration),(4,j4_acceleration)]:
            j=-sqrt(2*n+1)*allm.coefficients[n,0][0]
            kw={'mu':GM,'radius_m':RADIUS_M,('j2' if n==2 else 'j'+str(n)):j}
            expected+=fn(p,**kw)
        np.testing.assert_allclose(allm.acceleration_itrs(p),expected,rtol=3e-15,atol=3e-15)
    def test_external_random_and_poles(self):
        m=SphericalHarmonicsGravity();rng=np.random.default_rng(20261021)
        points=[np.array([6850000.,0.,0.])]+[6850000*np.array([np.cos(np.deg2rad(89.9)),0.,s*np.sin(np.deg2rad(89.9))]) for s in [-1,1]]
        for _ in range(100):
            v=rng.normal(size=3);points.append(v/np.linalg.norm(v)*rng.uniform(6800000,7400000))
        for p in points:np.testing.assert_allclose(m.acceleration_itrs(p),external_reference(m,p),rtol=2e-12,atol=2e-12)
    def test_gradient_convergence(self):
        m=SphericalHarmonicsGravity();p=np.array([4e6,-3e6,5e6]);a=m.acceleration_itrs(p);err=[]
        for h in [10000.,1000.,100.]:
            g=np.array([-(m.potential_itrs(p+np.eye(3)[j]*h)-m.potential_itrs(p-np.eye(3)[j]*h))/(2*h) for j in range(3)])
            err.append(np.linalg.norm(g-a)/np.linalg.norm(a))
        self.assertLess(err[1],err[0]/50);self.assertLess(err[2],err[1]/30);self.assertLess(err[2],2e-8)
    def test_longitude_and_poles(self):
        m=SphericalHarmonicsGravity();a=m.acceleration_itrs([6850000.,0,0]);b=m.acceleration_itrs([0,6850000.,0])
        self.assertGreater(abs(a[0]-b[1]),1e-6)
        for s in [-1,1]:
            a=m.acceleration_itrs([0.,0.,s*6850000.]);b=m.acceleration_itrs([1e-5,0,s*6850000.]);self.assertLess(np.linalg.norm(a-b),1e-9)
    def test_order_and_invalid(self):
        for d,o in [(9,8),(8,9),(-1,0)]:
            with self.assertRaises(ValueError):SphericalHarmonicsGravity(d,o)
        m=SphericalHarmonicsGravity()
        for p in [[0,0,0],[float('nan'),0,0]]:
            with self.assertRaises(ValueError):m.acceleration_itrs(p)
    def test_potential_independent_legendre(self):
        from scipy.special import lpmv
        from math import factorial
        model=SphericalHarmonicsGravity();p=np.array([4e6,3e6,-5e6]);r=np.linalg.norm(p);lon=np.arctan2(p[1],p[0]);v=0.
        for (n,m),(c,s) in model.coefficients.items():
            norm=sqrt((2 if m else 1)*(2*n+1)*factorial(n-m)/factorial(n+m))
            v+=(RADIUS_M/r)**n*norm*(-1)**m*lpmv(m,n,p[2]/r)*(c*np.cos(m*lon)+s*np.sin(m*lon))
        self.assertAlmostEqual(model.potential_itrs(p)/(-GM/r*v),1.,places=14)
    def test_frame_force_rotation(self):
        from orbit.frames import configure_time_data,transform_state
        from orbit.spherical_harmonics_gravity import GcrsSphericalHarmonicsForce
        from astropy.time import Time
        configure_time_data();epoch=Time('2023-03-21T00:00:02',scale='utc');f=GcrsSphericalHarmonicsForce(epoch)
        r=np.array([4e6,3e6,-5e6]);v=np.array([2000.,5000.,4000.]);utc,rt,vt,Q=f.frame.state_to_itrs(0,r,v)
        np.testing.assert_allclose(rt,Q@r,rtol=0,atol=1e-7)
        ag=f(0,r,v);at=f.model.acceleration_itrs(rt)
        np.testing.assert_allclose(Q@ag,at,rtol=1e-14,atol=1e-14)
        self.assertAlmostEqual(np.linalg.norm(ag),np.linalg.norm(at),places=12)
    def test_j2_only_and_order_cutoff(self):
        p=np.array([4e6,-3e6,5e6]);m=SphericalHarmonicsGravity();c20=m.coefficients[2,0][0]
        only=SphericalHarmonicsGravity(2,0,{(0,0):(1.,0.),(2,0):(c20,0.)})
        a=-GM*p/np.linalg.norm(p)**3+j2_acceleration(p,mu=GM,radius_m=RADIUS_M,j2=-sqrt(5)*c20)
        np.testing.assert_allclose(only.acceleration_itrs(p),a,rtol=2e-15,atol=2e-15)
        zonal=SphericalHarmonicsGravity(8,0)
        np.testing.assert_allclose(zonal.acceleration_itrs(p),external_reference(zonal,p),rtol=2e-12,atol=2e-12)
