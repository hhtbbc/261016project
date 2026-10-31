"""CPU interpolation and independent source-equation reconstruction tests."""
from pathlib import Path
import sys
import unittest
import tempfile,hashlib
import numpy as np
from astropy.time import Time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from atmosphere.fourcastden_density import FourCastDENDensity,reconstruct_native_zg
from atmosphere.tiegcm_density_provider import DATUM


class DensityTests(unittest.TestCase):
    def setUp(self):
        self.lat=np.array([-5.,5.]);self.lon=np.array([-180.,-90.,0.,90.])
        self.epochs=['2023-03-24T01:00:00','2023-03-24T02:00:00']
        # Separable amplitude makes horizontal/time expectations independent.
        amp=np.array([1.,3.])[:,None,None,None]*np.array([1.,2.])[None,None,:,None]*np.array([1.,2.,3.,4.])[None,None,None,:]
        self.den=amp*np.exp(-np.array([0.,1.,2.]))[None,:,None,None]*1e-15
        self.height=np.broadcast_to(np.array([100e3,200e3,300e3])[None,:,None,None],self.den.shape).copy()
        self.p=FourCastDENDensity(self.epochs,self.lat,self.lon,self.den,self.height,source='SYNTHETIC',height_source='SYNTHETIC')

    def test_grid_point_units(self):
        q=self.p(self.epochs[0],-5,-90,200000,datum=DATUM)
        self.assertTrue(q.valid);self.assertAlmostEqual(q.rho_kg_m3/self.den[0,1,0,1],1000.)

    def test_vertical_log_midpoint(self):
        q=self.p(self.epochs[0],-5,-180,150000,datum=DATUM)
        self.assertAlmostEqual(q.rho_kg_m3/(1e-12*np.exp(-.5)),1.)

    def test_horizontal_time_interpolation(self):
        q=self.p('2023-03-24T01:30:00',0,-135,100000,datum=DATUM)
        self.assertAlmostEqual(q.rho_kg_m3/(2*1.5*1.5e-12),1.)

    def test_periodic_seam(self):
        a=self.p(self.epochs[0],0,135,100000,datum=DATUM)
        b=self.p(self.epochs[0],0,-225,100000,datum=DATUM)
        self.assertEqual(a.rho_kg_m3,b.rho_kg_m3)
        self.assertAlmostEqual(a.rho_kg_m3/(1.5*2.5e-12),1.)

    def test_pressure_lookup_no_height_claim(self):
        q=self.p.query_pressure(self.epochs[0],-5,-90,1)
        self.assertEqual(q.rho_kg_m3,self.p.rho[0,1,0,1])
        self.assertTrue(q.metadata['no_geometric_height_claim'])

    def test_time_and_altitude_no_extrapolation(self):
        self.assertFalse(self.p('2023-03-24T00:59:59',0,0,200000,datum=DATUM).valid)
        self.assertFalse(self.p(self.epochs[-1],0,0,300001,datum=DATUM).valid)
        self.assertTrue(self.p(self.epochs[-1],5,90,300000,datum=DATUM).valid)

    def test_polar_and_external_rejected(self):
        self.assertFalse(self.p(self.epochs[0],6,0,200000,datum=DATUM).valid)
        self.assertFalse(self.p(self.epochs[0],0,0,200000,datum='WGS84').valid)
        with self.assertRaisesRegex(ValueError,'EXTERNAL_DATUM'):self.p.density_kg_m3(None)

    def test_zero_weight_corner_still_required(self):
        mask=np.ones((2,2,4),bool);mask[1,1,1]=False
        p=FourCastDENDensity(self.epochs,self.lat,self.lon,self.den,self.height,source='TEST',height_source='TEST',valid_columns=mask)
        self.assertFalse(p(self.epochs[0],-5,-180,100000,datum=DATUM).valid)

    def test_nonpositive_nonfinite_and_missing_time(self):
        for value in (0.,np.nan,np.inf):
            d=self.den.copy();d[0,0,0,0]=value
            with self.assertRaises(ValueError):FourCastDENDensity(self.epochs,self.lat,self.lon,d,self.height,source='X',height_source='X')
        with self.assertRaises(ValueError):FourCastDENDensity(['2023-03-24T01:00:00','2023-03-24T03:00:00'],self.lat,self.lon,self.den,self.height,source='X',height_source='X')

    def test_future_reference_ZG_poison_does_not_change_AI_provider(self):
        iv=np.arange(-7,7.01,.5);tn=np.full((2,28,2,4),700.);tl=np.full((2,1,2,4),180.)
        ti=np.concatenate((tl,tn[:,:27],tn[:,-1:]),axis=1)
        pressure=5e-4*np.exp(-iv);pressure[-1]=pressure[-2]
        rho=pressure[None,:,None,None]*20/(8.314e7*ti)
        ph=np.zeros((1,2,171,2,4));ph[0,:,:28]=tn
        ph[0,:,113:142]=np.broadcast_to((9600000+np.arange(29)*200000)[None,:,None,None],rho.shape)
        ph[0,:,142:171]=rho
        with tempfile.TemporaryDirectory(dir=ROOT/'.tmp') as d:
            providers=[]
            for tag,poison in [('original',1.),('poisoned',np.nan)]:
                path=Path(d)/(tag+'.npz')
                np.savez(path,pred=ph,means=np.zeros((171,1,1)),stds=np.ones((171,1,1)),ZG=np.full((2,29,2,4),poison))
                h=hashlib.sha256(path.read_bytes()).hexdigest()
                providers.append(FourCastDENDensity.from_saved(path,expected_sha256=h,model='Direct',epochs=self.epochs,lat=self.lat,lon=self.lon,ilev=iv,tlbc=tl))
            np.testing.assert_array_equal(providers[0].height,providers[1].height)
            np.testing.assert_array_equal(providers[0].rho,providers[1].rho)

    def test_independent_calczg_equations(self):
        # Independent forward construction with known ORIGINAL midpoint mass.
        lat=np.array([-45.,45.]);iv=np.arange(-7,7.01,.5)
        mass=np.broadcast_to(np.linspace(28,12,29)[None,:,None,None],(2,29,2,4)).copy()
        interface=np.empty_like(mass);interface[:,0]=1.5*mass[:,0]-.5*mass[:,1]
        interface[:,1:]=.5*(mass[:,:-1]+mass[:,1:])
        tn=np.full((2,28,2,4),700.);lb=np.full((2,1,2,4),180.)
        ti=np.concatenate((lb,.5*(tn[:,:-1]+tn[:,1:]),tn[:,-1:]),axis=1)
        pressure=5e-4*np.exp(-iv);pressure[-1]=pressure[-2]
        den=pressure[None,:,None,None]*interface/(8.314e7*ti)
        z=np.empty_like(mass);z[:,0]=9600000.
        for k in range(28):z[:,k+1]=z[:,k]+.5*8.314e7*tn[:,k]/(.5*(interface[:,k]+interface[:,k+1])*870.)
        expected=np.empty_like(z)
        for it in range(2):
            for j,phi in enumerate(lat):
                c=np.cos(2*1.74533e-2*phi);g0=980.616*(1-.0026373*c);r=2*g0/(3.085462e-6+2.27e-9*c)
                for i in range(4):
                    expected[it,0,j,i]=z[it,0,j,i]
                    g=g0*(r/(r+.5*(z[it,0,j,i]+z[it,1,j,i])))**2
                    for k in range(1,28):
                        particle_mass=mass[it,k-1,j,i]/6.023e23
                        expected[it,k,j,i]=expected[it,k-1,j,i]+1.38e-16*.5*tn[it,k-1,j,i]/(particle_mass*g)
                        g=g0*(r/(r+.5*(expected[it,k,j,i]+z[it,k+1,j,i])))**2
                    expected[it,-1,j,i]=2*expected[it,-2,j,i]-expected[it,-3,j,i]
        reconstructed,valid,inferred=reconstruct_native_zg(tn,den,z,lb,lat,iv)
        np.testing.assert_allclose(inferred,mass,rtol=1e-13,atol=1e-12)
        np.testing.assert_allclose(reconstructed,expected*.01,rtol=1e-13,atol=1e-8)
        self.assertTrue(valid.all())
        _,bad,_=reconstruct_native_zg(tn,den*3,z,lb,lat,iv)
        self.assertFalse(bad.any())  # impossible mass is rejected, not clipped


if __name__=='__main__':unittest.main()
