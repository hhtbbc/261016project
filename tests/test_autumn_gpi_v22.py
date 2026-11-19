"""Synthetic/contract tests only; no real model or candidate observation density."""
import unittest,sys,math,json
from pathlib import Path
from datetime import timedelta
import numpy as np
from netCDF4 import Dataset
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R/'scripts')]
import prepare_tiegcm_training_drivers as old
from atmosphere.autumn_gpi_validation import *
from observations.autumn_validation import inspect_initial,source_clock
from atmosphere.restart_validation import REQUIRED,LOWER
F=R/'experiments/thermosphere_autumn_gpi_v22_tests_local'
class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        F.mkdir(exist_ok=False)
        cls.s={t:100.+i/10 for i,t in enumerate(span(stamp(2022,7,29),stamp(2022,11,6)))}
        cls.k={t:float(i%7) for i,t in enumerate(span(stamp(2022,9,7),stamp(2022,9,27)+timedelta(hours=21),3))}
        cls.template=R/'experiments/tiegcm_2022_mar25_preparation_v1/gpi_2022_extended.nc'
    def make(self,name):
        p=F/(name+'.nc');d,f,a,k=old.arrays(self.s,self.k,stamp(2022,9,7).date(),stamp(2022,9,27).date());old.write_gpi(p,d,f,a,k,stamp(2022,9,9).date(),stamp(2022,9,25).date());return p
    def test_good_full_runtime(self):
        p=self.make('good');means,err=check_file(p,self.s,self.k,2022,self.template)
        a=compare_driver(old.GpiDriver(p),self.s,means,self.k,2022);self.assertEqual(a['minute_nodes'],23041)
    def test_missing_day(self):
        s=self.s.copy();s.pop(next(iter(s)))
        with self.assertRaises(ValueError):check_records(s,self.k,2022)
    def test_bad_values(self):
        for x in [-1,float('nan'),float('inf')]:
            s=self.s.copy();s[next(iter(s))]=x
            with self.assertRaises(ValueError):check_records(s,self.k,2022)
    def test_bad_Kp(self):
        k=self.k.copy();k[next(iter(k))]=10
        with self.assertRaises(ValueError):check_records(self.s,k,2022)
    def test_wrong_units(self):
        p=self.make('unit')
        with Dataset(p,'a') as n:n['f107d'].units='Fadj'
        with self.assertRaises(ValueError):check_file(p,self.s,self.k,2022,self.template)
    def test_time_shift(self):
        p=self.make('time')
        with Dataset(p,'a') as n:n['year_day'][0]+=1
        with self.assertRaises(ValueError):check_file(p,self.s,self.k,2022,self.template)
    def test_mean_corruption(self):
        p=self.make('mean')
        with Dataset(p,'a') as n:n['f107a'][0]+=1e-8
        with self.assertRaises(ValueError):check_file(p,self.s,self.k,2022,self.template)
    def test_endpoint_corruption(self):
        p=self.make('endpoint');means,_=check_file(p,self.s,self.k,2022,self.template);driver=old.GpiDriver(p);driver.f107d[0]+=1
        with self.assertRaises(ValueError):compare_driver(driver,self.s,means,self.k,2022)
    def test_Kp_center_corruption(self):
        p=self.make('kpcenter');means,_=check_file(p,self.s,self.k,2022,self.template);driver=old.GpiDriver(p);driver.kp[1,7]+=1
        with self.assertRaises(ValueError):compare_driver(driver,self.s,means,self.k,2022)
    def test_no_overwrite(self):
        self.make('exclusive')
        with self.assertRaises(FileExistsError):self.make('exclusive')
    def test_nondef_and_duplicate(self):
        for p in [dict(datetime=['2022-09-07T00:00:00Z'],Kp=[1],status=['pre']),dict(datetime=['2022-09-07T00:00:00Z']*2,Kp=[1,1],status=['def']*2)]:
            with self.assertRaises(ValueError):old.decode(p,'Kp')
    def test_clock(self):
        with self.assertRaises(ValueError):source_clock([[266,6,0]])
        self.assertEqual(source_clock([[266,0,0]]),[266,0,0])
    def initial(self,name,omit=None):
        p=F/(name+'.nc')
        with Dataset(p,'w',format='NETCDF3_CLASSIC') as n:
            for k,l in [('time',1),('mtimedim',3),('lat',2),('lon',2),('lev',2),('ilev',2)]:n.createDimension(k,l)
            n.history_type='primary'
            for k in ['lat','lon','lev','ilev']:v=n.createVariable(k,'f8',(k,));v[:]=[0,1]
            v=n.createVariable('mtime','i4',('time','mtimedim'));v[:]=[[266,0,0]]
            v=n.createVariable('year','i4',('time',));v[:]=2002
            for k in REQUIRED:
                if k==omit:continue
                dims=('time','lat','lon') if k in LOWER or k=='POTEN' else ('time','lev','lat','lon')
                v=n.createVariable(k,'f8',dims,fill_value=1e36)
                v.units='K' if k.startswith(('TN','TLBC')) or k in ['TI','TE'] else ('mmr' if k.startswith(('O1','O2','N4S','HE','AR','NO')) else '1')
                x=np.full(v.shape,300. if v.units=='K' else .1)
                if k=='Z':x[:,1]=.2
                if k in ['TN','TN_NM','UN','UN_NM','VN','VN_NM','TI','TE']:x[:,-1]=1e36
                v[:]=x
        return p
    def test_initial_synthetic_complete(self):
        p=self.initial('initial_good');a=inspect_initial(p,p);self.assertEqual(a['required_complete_states'],34)
    def test_initial_missing_state(self):
        p=self.initial('initial_missing','HE')
        with self.assertRaises(ValueError):inspect_initial(p,p)
    def test_initial_nonfinite(self):
        p=self.initial('initial_nan')
        with Dataset(p,'a') as n:n['O1'][0,0,0,0]=np.nan
        with self.assertRaises(ValueError):inspect_initial(p,p)
    def test_initial_wrong_grid(self):
        a=self.initial('initial_ref');b=self.initial('initial_grid')
        with Dataset(b,'a') as n:n['lat'][0]=10
        with self.assertRaises(ValueError):inspect_initial(b,a)
    def test_initial_wrong_units(self):
        a=self.initial('initial_refunits');b=self.initial('initial_units')
        with Dataset(b,'a') as n:n['TN'].units='degC'
        with self.assertRaises(ValueError):inspect_initial(b,a)
if __name__=='__main__':unittest.main()
