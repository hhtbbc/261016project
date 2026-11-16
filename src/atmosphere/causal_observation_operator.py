"""Explicit Map-A research operator; never a formal external density provider."""
from dataclasses import asdict
import numpy as np
from astropy.coordinates import EarthLocation
from astropy.time import Time
import astropy.units as u
from .density_interface import DensityQuery
from .provisional_coordinate_adapter import ProvisionalCoordinateAdapter,A_WGS84

def map_a_queries(utc,latitude,longitude,height):
    loc=EarthLocation.from_geodetic(np.asarray(longitude)*u.deg,np.asarray(latitude)*u.deg,np.asarray(height)*u.m,ellipsoid='GRS80')
    xyz=np.column_stack([x.to_value(u.m) for x in loc.geocentric])
    return [DensityQuery.from_itrs(t,r) for t,r in zip(Time(utc),xyz)]

def observe_map_a(provider,query):
    result=ProvisionalCoordinateAdapter(assumption=A_WGS84).query_provisional(provider,query)
    return result.native_result,asdict(result.coordinates)

def split_masks(utc):
    t=np.asarray(utc,dtype='datetime64[ns]');cut=np.datetime64('2022-03-24T06:00:00','ns')
    return {'calibration':(t>=cut-np.timedelta64(3,'h'))&(t<cut),**{f'future_{h}h':(t>=cut)&(t<cut+np.timedelta64(h,'h')) for h in [1,3,6]}}
