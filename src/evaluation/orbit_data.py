"""Standard SI orbit data with explicit Astropy time and frame metadata."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,xml.etree.ElementTree as ET
import numpy as np
import astropy.units as u
from astropy.time import Time
from evaluation.sp3_reader import read_sp3
from orbit.frames import gps_calendar_to_time

@dataclass
class OrbitSeries:
    times:Time
    positions_m:np.ndarray
    velocities_m_s:np.ndarray
    frame:str
    metadata:dict

    def __post_init__(self):
        if self.positions_m.shape!=self.velocities_m_s.shape or self.positions_m.shape!=(self.times.size,3):raise ValueError('Invalid orbit shape')
        if not np.isfinite(self.positions_m).all() or not np.isfinite(self.velocities_m_s).all():raise ValueError('Nonfinite state')
        if np.any(np.diff(self.times.tai.jd)<=0):raise ValueError('Non-increasing time')

    def take_exact(self,times,tolerance_s=1e-6):
        # No SP3 interpolation: locate only exact existing reference samples.
        seconds=(self.times-self.times[0]).to_value(u.s)
        query=(times-self.times[0]).to_value(u.s)
        i=np.searchsorted(seconds,query)
        i=np.clip(i,0,len(seconds)-1)
        left=np.maximum(0,i-1)
        i=np.where(abs(seconds[left]-query)<abs(seconds[i]-query),left,i)
        mismatch=np.abs((self.times[i]-times).to_value(u.s))
        if np.any(mismatch>tolerance_s):raise ValueError('Requested time outside exact SP3 grid')
        return OrbitSeries(self.times[i],self.positions_m[i],self.velocities_m_s[i],self.frame,{**self.metadata,'time_match_max_s':float(mismatch.max())})

def load_sp3_reference(paths):
    all_times=[];p=[];v=[];sources=[];frame=None
    for path in sorted(map(Path,paths)):
        raw=read_sp3(path)
        if raw.time_system!='GPS':raise ValueError('Current standardizer requires explicitly verified GPS products')
        if raw.satellite_id!='L47':raise ValueError('Expected Swarm-A product identity L47')
        if frame is not None and frame!=raw.frame:raise ValueError('Mixed frame realizations')
        frame=raw.frame;times=gps_calendar_to_time(raw.epochs)
        header=ET.parse(path.with_suffix('.HDR')).getroot()
        validity_start=header.findtext('.//Validity_Start').removeprefix('UTC=')
        difference=abs((times[0]-Time(validity_start,scale='utc')).to_value(u.s))
        if difference>1e-6:raise ValueError('SP3 GPS conversion does not match independent HDR UTC start')
        source={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'version':raw.version,'frame':raw.frame,'native_time_system':raw.time_system,'satellite_id':raw.satellite_id,'epochs':len(raw.epochs),'hdr_time_difference_s':float(difference),'hdr_quality_indicator':header.findtext('.//Quality_Indicator'),'hdr_creation_date':header.findtext('.//Creation_Date'),'formal_accuracy_exponents':sorted(set(line[3:].strip() for line in path.read_text().splitlines() if line.startswith('++'))),'maneuver_flag_available':any(x['maneuver'] is not None for x in raw.orbit_flags)}
        sources.append(source);all_times.append(times);p.append(raw.positions_m);v.append(raw.velocities_m_s)
    if not all_times:raise ValueError('No SP3 files')
    times=Time(np.concatenate([x.tai.jd1 for x in all_times]),np.concatenate([x.tai.jd2 for x in all_times]),format='jd',scale='tai').utc
    if np.max(abs(np.diff((times-times[0]).to_value(u.s))-10))>1e-6:raise ValueError('Missing or overlapping SP3 epochs')
    return OrbitSeries(times,np.concatenate(p),np.concatenate(v),frame,{'sources':sources,'reference_kind':'reduced-dynamic postprocessed orbit','reference_uncertainty_quantified':False,'itrs_realization_assumption':'IGS20 aligned with ITRF2020; used as ITRS, no estimated Helmert correction'})

def save_standardized(series,path):
    import json
    np.savez_compressed(path,utc_jd1=series.times.utc.jd1,utc_jd2=series.times.utc.jd2,utc_isot=series.times.utc.to_value('isot'),position_m=series.positions_m,velocity_m_s=series.velocities_m_s,frame=series.frame,metadata_json=json.dumps(series.metadata))
