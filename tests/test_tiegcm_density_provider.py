import sys, unittest,tempfile
from pathlib import Path
import numpy as np
from netCDF4 import Dataset
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from atmosphere.tiegcm_density_provider import TiegcmDensityProvider,DATUM
class DensityTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'.tmp');self.path=Path(self.tmp.name)/'test.nc'
  with Dataset(self.path,'w') as n:
   for d,s in [('time',2),('ilev',3),('lat',2),('lon',4),('clock',3)]:n.createDimension(d,s)
   n.createVariable('lat','f8',('lat',))[:]=[-87.5,87.5];n.createVariable('lon','f8',('lon',))[:]=[-180,-90,0,90]
   n.createVariable('year','i4',('time',))[:]=2023;n.createVariable('mtime','i4',('time','clock'))[:]=[[80,0,0],[80,0,10]]
   for name,unit in [('ZG','cm'),('DEN','g/cm3')]:
    v=n.createVariable(name,'f8',('time','ilev','lat','lon'));v.units=unit
    for t in range(2):
     for j in range(2):
      for i in range(4):v[t,:,j,i]=np.array([100,200,300])*100 if name=='ZG' else (1+t)*np.exp(-np.array([100,200,300])/100)/1000
  self.p=TiegcmDensityProvider([self.path],'SYNTHETIC')
 def tearDown(self):self.p.close();self.tmp.cleanup()
 def q(self,t='2023-03-21T00:05:00',lat=0,lon=0,h=150,datum=DATUM,**kw):return self.p.query_native(t,lat,lon,h,datum=datum,**kw)
 def test_hand_calculation(self):self.assertAlmostEqual(self.q().rho_kg_m3,1.5*np.exp(-1.5),14)
 def test_grid_units(self):self.assertAlmostEqual(self.q(t='2023-03-21T00:00:00',lat=-87.5,h=100).rho_kg_m3,np.exp(-1),14)
 def test_periodic(self):self.assertEqual(self.q(lon=179).rho_kg_m3,self.q(lon=-181).rho_kg_m3)
 def test_poles(self):

  for lat in [-87.4,87.4]:self.assertTrue(self.q(lat=lat).valid)
  for lat in [-90,90]:self.assertEqual(self.q(lat=lat).reason,'POLAR_CAP_UNSUPPORTED')
 def test_boundaries(self):
  for h in [99,301]:self.assertEqual(self.q(h=h).reason,'VERTICAL_OUTSIDE')
 def test_time(self):
  for t in ['2023-03-20T23:59:59','2023-03-21T00:10:01']:self.assertEqual(self.q(t=t).reason,'TIME_OUTSIDE')
 def test_datum(self):self.assertEqual(self.q(datum='WGS84').reason,'DATUM_UNVERIFIED');self.assertFalse(self.p.query_external(None).valid)
 def corrupt(self,name,value):
  self.p.cache.clear()
  with Dataset(self.path,'a') as n:n[name][1,1,1,3]=value
 def test_nan_corner(self):self.corrupt('DEN',float('nan'));self.assertEqual(self.q().reason,'INVALID_COLUMN')
 def test_fill_corner(self):self.corrupt('DEN',1e36);self.assertEqual(self.q().reason,'INVALID_COLUMN')
 def test_order_corner(self):self.corrupt('ZG',1);self.assertEqual(self.q().reason,'INVALID_COLUMN')
 def test_linear_alternative(self):
  self.assertAlmostEqual(self.q(vertical='linear').rho_kg_m3,1.5*(np.exp(-1)+np.exp(-2))/2,14)
  self.assertAlmostEqual(self.q().metadata['all_log_alternative_kg_m3'],np.sqrt(2)*np.exp(-1.5),14)
 def test_cache_repeat_close(self):
  a=self.q();self.assertEqual(a,self.q());self.assertLessEqual(len(self.p.cache),256);self.p.close()
  with self.assertRaises(RuntimeError):self.q()
 def test_source(self):
  with TiegcmDensityProvider([self.path],'S7') as p:self.assertEqual(p.query_native('2023-03-21',0,0,150,datum=DATUM).metadata['source'],'S7')

 def test_cf_mismatch_rejected(self):
  with Dataset(self.path,'a') as n:
   v=n.createVariable('time','f8',('time',));v.units='minutes since 2023-03-21 00:00:00';v[:]=[0,11]
  with self.assertRaisesRegex(ValueError,'calendar mismatch'):TiegcmDensityProvider([self.path],'BAD')
 def test_duplicate_rejected(self):
  with self.assertRaisesRegex(ValueError,'Duplicate'):TiegcmDensityProvider([self.path,self.path],'BAD')
 def test_zero_weight_bad_neighbor_rejected(self):
  self.corrupt('DEN',float('nan'))
  self.assertEqual(self.q(t='2023-03-21T00:00:00',lat=-87.5,h=100).reason,'INVALID_COLUMN')
 def test_no_handle_leak(self):
  fds=Path('/proc/self/fd');before=len(list(fds.iterdir()))
  for _ in range(20):self.p.cache.clear();self.q()
  self.assertEqual(len(list(fds.iterdir())),before)

 def test_nonuniform_horizontal_and_seam(self):
  self.p.cache.clear()
  with Dataset(self.path,'a') as n:
   for j in range(2):
    for i in range(4):n['DEN'][:,:,j,i]=n['DEN'][:,:,j,i]*(1+.2*j+.1*i)
  self.assertAlmostEqual(self.q(lon=45).rho_kg_m3,1.5*1.35*np.exp(-1.5),14)
  self.assertAlmostEqual(self.q(lon=135).rho_kg_m3,1.5*1.25*np.exp(-1.5),14)
  self.assertEqual(self.q(lon=135),self.q(lon=-225))

if __name__=='__main__':unittest.main()
