"""Synthetic tests only: frozen floor, signed closure, coordinate meaning."""
import importlib.util
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parents[1]/'scripts/analyze_tiegcm_composition_root_cause_20261030.py'
s=importlib.util.spec_from_file_location('composition_audit',P);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def test_floor_is_not_model_small():
 a=np.array([1e-9,1e-8,1e-6,0.2]);b=a+1e-7;r=m.relative(a,b)
 assert np.isnan(r[:2]).all();np.testing.assert_allclose(r[2:], [.1,5e-7])
def test_closure_transfer():
 x=np.array([.2,.3,.01]);y=np.array([.21,.28,.01]);n2a=1-x.sum();n2b=1-y.sum()
 np.testing.assert_allclose(n2b-n2a,-(y-x).sum(),atol=1e-15)
def test_midpoint_is_between_interfaces():
 z=np.array([100.,110.,130.]);ilev=np.array([-7.,-6.5,-6.]);lev=np.array([-6.75,-6.25,-5.75])
 np.testing.assert_allclose(np.interp(lev[:2],ilev,z),[105,120]);assert lev[-1]>ilev[-1]
def test_frozen_regions_cover_both_poles():
 assert m.REGIONS['south_polar']==(-90,-60);assert m.REGIONS['north_polar']==(60,90)
