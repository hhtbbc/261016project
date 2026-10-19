"""Explicit time scales and geocentric state transforms using frozen IERS data."""
from pathlib import Path
import hashlib,json
import numpy as np
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import TEME,ITRS,GCRS,CartesianRepresentation,CartesianDifferential
from astropy.utils import iers
ROOT=Path(__file__).resolve().parents[2]

def configure_time_data(manifest=None):
    manifest=Path(manifest or ROOT/'logs/20261020_frozen_time_data.json')
    meta=json.loads(manifest.read_text())
    for key in ['iers_b','leap_seconds']:
        p=ROOT/meta[key]['path']
        if not p.resolve().is_relative_to(ROOT) or hashlib.sha256(p.read_bytes()).hexdigest()!=meta[key]['sha256']:
            raise ValueError('Frozen time-data integrity failure')
    iers.conf.auto_download=False
    iers.conf.iers_degraded_accuracy='error'
    leap=iers.LeapSeconds.open(str(ROOT/meta['leap_seconds']['path']))
    # Retain ERFA pre-1972 drift entries; clearing them breaks historical DAT lookup.
    leap.update_erfa_leap_seconds(initialize_erfa=True)
    table=iers.IERS_B.open(str(ROOT/meta['iers_b']['path']))
    iers.earth_orientation_table.set(table)
    return table,meta

def gps_calendar_to_time(labels):
    """Interpret GPS calendar labels via GPS elapsed seconds, never as UTC.

    TAI is used ONLY as a uniform calendar arithmetic ruler here. Physical
    GPS epoch and TAI/GPS relation are supplied by Astropy's TimeGPS format.
    No hardcoded GPS-UTC offset enters this conversion.
    """
    labels=[x.isoformat() if hasattr(x,'isoformat') else str(x) for x in labels]
    uniform=Time(labels,format='isot',scale='tai')
    elapsed=(uniform-Time('1980-01-06T00:00:00',format='isot',scale='tai')).to_value(u.s)
    return Time(elapsed,format='gps').utc

def check_eop(times,table=None):
    table=table if table is not None else iers.earth_orientation_table.get()
    ut1,status=table.ut1_utc(times,return_status=True)
    xp,yp,pm_status=table.pm_xy(times,return_status=True)
    if np.any(status!=iers.FROM_IERS_B) or np.any(pm_status!=iers.FROM_IERS_B):
        raise ValueError('Definitive IERS-B coverage required; extrapolation forbidden')
    if not all(np.isfinite(x.value).all() for x in [ut1,xp,yp]):raise ValueError('Nonfinite EOP')
    return {'ut1_utc_s_min':float(np.min(ut1.to_value(u.s))),'ut1_utc_s_max':float(np.max(ut1.to_value(u.s))),
            'xp_arcsec_min':float(np.min(xp.to_value(u.arcsec))),'xp_arcsec_max':float(np.max(xp.to_value(u.arcsec))),
            'yp_arcsec_min':float(np.min(yp.to_value(u.arcsec))),'yp_arcsec_max':float(np.max(yp.to_value(u.arcsec))),
            'all_status_iers_b':True}

def transform_state(position_m,velocity_m_s,times,source,target):
    """Transform complete positions AND velocities at identical obstime."""
    classes={'TEME':TEME,'ITRS':ITRS,'GCRS':GCRS}
    p=np.asarray(position_m,dtype=float);v=np.asarray(velocity_m_s,dtype=float)
    if p.shape!=v.shape or p.shape[-1]!=3 or p.shape[0]!=times.size:raise ValueError('State/time shape mismatch')
    if not np.isfinite(p).all() or not np.isfinite(v).all():raise ValueError('Nonfinite state')
    check_eop(times)
    representation=CartesianRepresentation(p.T*u.m,differentials=CartesianDifferential(v.T*u.m/u.s))
    transformed=classes[source](representation,obstime=times).transform_to(classes[target](obstime=times))
    return transformed.cartesian.xyz.to_value(u.m).T,transformed.cartesian.differentials['s'].d_xyz.to_value(u.m/u.s).T
