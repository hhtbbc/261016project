"""Evidence-preserving Swarm0601 snapshots, deliberately not a complete force model.

No demo mass/area/Cd fallback. Product quaternion convention, platform-code
semantics and actual thrust calibration are not certified by this module.
"""
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import hashlib
import numpy as np
import cdflib

ROOT=Path(__file__).resolve().parents[2]
class Mode(str,Enum):
    RESEARCH_PROVISIONAL='RESEARCH_PROVISIONAL'
    FORMAL_VALIDATED='FORMAL_VALIDATED'
class ForceInputError(ValueError):pass
@dataclass(frozen=True)
class Parameter:
    value:object
    unit:str
    status:str
    source:str
    reason:str
@dataclass(frozen=True)
class ForceInputs:
    UTC:str
    mass:Parameter
    attitude:Parameter
    effective_area:Parameter
    Cd:Parameter
    thrust:Parameter
    quality:dict
    provenance:dict
    formal_ready:bool=False

def file_sha(path):
    p=Path(path).resolve();p.relative_to(ROOT)
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024**2),b''):h.update(b)
    return h.hexdigest()

def cdf_epoch_utc64(epoch_ms):
    """Keep fractional milliseconds serialized in CDF_EPOCH float64.

    cdflib's datetime conversion drops the fraction of a millisecond here.
    An ns output grid does not imply ns measurement accuracy:2023 epoch ULP
    is about7.8125us. We preserve the stored value, not invent extra precision.
    """
    a=np.asarray(epoch_ms,dtype=np.float64)
    if a.ndim!=1 or not np.isfinite(a).all():raise ForceInputError('Invalid CDF_EPOCH array')
    whole=np.floor(a)
    return cdflib.cdfepoch.to_datetime(whole).astype('datetime64[ns]')+np.rint((a-whole)*1e6).astype('timedelta64[ns]')

def utc64(value):
    # Only explicitly UTC-labelled inputs; GPS/TAI offsets must not be guessed.
    if isinstance(value,np.datetime64):t=value.astype('datetime64[ns]')
    elif isinstance(value,str) and value.endswith('Z'):t=np.datetime64(value[:-1],'ns')
    else:raise ForceInputError('Explicit ISO UTC suffix Z or numpy UTC datetime64 required')
    if np.isnat(t):raise ForceInputError('Invalid UTC')
    return t

def synthetic_quaternion_matrix_xyzw(q):
    """Hamilton active xyzw mathematical utility; NOT certified for Swarm q."""
    q=np.asarray(q,dtype=float)
    if q.shape!=(4,) or not np.isfinite(q).all() or abs(np.dot(q,q)-1)>1e-8:raise ForceInputError('Finite unit xyzw quaternion required; no silent normalization')
    x,y,z,w=q
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def synthetic_convex_projected_area(outward_area_vectors,spacecraft_velocity_relative_air):
    """Convex closed one-sided facets, no occlusion/articulation; synthetic only.

Vectors must be outward normals times facet area in m2, same frame as relative
velocity. The four SC_ADYN area vectors are NOT a certified input to this model.
"""
    a=np.asarray(outward_area_vectors,dtype=float);v=np.asarray(spacecraft_velocity_relative_air,dtype=float)
    if a.ndim!=2 or a.shape[1]!=3 or len(a)<4 or v.shape!=(3,) or not np.isfinite(a).all() or not np.isfinite(v).all() or np.linalg.norm(v)==0:raise ForceInputError('Invalid closed-facet geometry or relative velocity')
    if np.linalg.norm(a.sum(axis=0))>1e-10*max(1,float(np.linalg.norm(a,axis=1).sum())):raise ForceInputError('Area vectors do not close; cannot assume convex complete geometry')
    return float(np.maximum(a@(v/np.linalg.norm(v)),0).sum())

class SwarmForceInputProvider:
    """Read traced source records only. Zero-order snapshots are not interpolants.

Each field reports its own source UTC/age. No interpolation crosses quality
changes, gaps or thrust candidates; indeed no temporal interpolation is used.
FORMAL_VALIDATED always refuses while required independent evidence is absent.
"""
    def __init__(self,dynamics_cdf,attitude_cdf,*,source_sha256):
        self.paths={'SC_ADYN':Path(dynamics_cdf).resolve(),'STRAATT':Path(attitude_cdf).resolve()};self.sha=dict(source_sha256);self.data={};self.meta={}
        self.verify_sources()
        for kind,path in self.paths.items():
            with cdflib.CDF(path) as c:
                g=c.globalattsget()
                if g.get('File_Version')!=['0601'] or g.get('File_Type')!=[kind+'_1B']:raise ForceInputError('Unsupported product version/type')
                if c.varinq('Timestamp').Data_Type_Description!='CDF_EPOCH' or not g['Sensing_Start'][0].startswith('UTC='):raise ForceInputError('Unverified product time convention')
                t=cdf_epoch_utc64(c.varget('Timestamp'))
                if np.isnat(t).any() or (np.diff(t)<=np.timedelta64(0,'ms')).any():raise ForceInputError('Non-monotone or missing time')
                if abs((t[0]-np.datetime64(g['Sensing_Start'][0][4:]))/np.timedelta64(1,'s'))>.002:raise ForceInputError('UTC header/CDF mismatch')
                keys=['m_SC','Flags_Platform','dt_thr','f_thr','thr_set','Flags_q','SyncStatus'] if kind=='SC_ADYN' else ['q','Flags_q','SyncStatus','Maneuver_Id']
                d={k:c.varget(k) for k in keys};d['Timestamp']=t
                units={k:c.varattsget(k).get('UNITS') for k in keys}
                if kind=='SC_ADYN' and any(units[k]!=u for k,u in [('m_SC','kg'),('dt_thr','s'),('f_thr','mN')]):raise ForceInputError('Unexpected physical units')
                if kind=='STRAATT' and c.varattsget('q').get('DESCRIPTION')!='Quaternion, transformation: ITRF <- S/C':raise ForceInputError('Unexpected quaternion direction metadata')
                if any(len(d[k])!=len(t) for k in keys):raise ForceInputError('Record dimension mismatch')
                expected={'m_SC':(), 'dt_thr':(12,), 'f_thr':(3,), 'q':(4,)}
                for key,shape in expected.items():
                    if key in d and d[key].shape!=(len(t),)+shape:raise ForceInputError('State dimensions do not match0601: '+key)
                self.data[kind]=d;self.meta[kind]=dict(path=str(path.relative_to(ROOT)),SHA256=self.sha[kind],version='0601',processor=g.get('Software_Version'),processed_UTC=g.get('Proc_Time'),q_convention='UNVERIFIED',units=units)
        self.meta['STRAATT']['quaternion_declared_frames']={'from':'S/C','to':'ITRF','component_order':None,'active_or_passive_matrix_convention':None,'formal_rotation_enabled':False}
        self.start=max(d['Timestamp'][0] for d in self.data.values());self.stop=min(d['Timestamp'][-1] for d in self.data.values())
    def verify_sources(self):
        for k,p in self.paths.items():
            if k not in self.sha or file_sha(p)!=self.sha[k]:raise ForceInputError('Source SHA mismatch: '+k)
    def rotation_to_itrs(self,utc):raise ForceInputError('UNVERIFIED_QUATERNION_CONVENTION: actual Swarm q is not converted')
    def at(self,utc_time,*,mode=Mode.RESEARCH_PROVISIONAL):
        if not isinstance(mode,Mode):raise ForceInputError('Use an explicit Mode enum; boolean/string gate bypass refused')
        if mode is Mode.FORMAL_VALIDATED:raise ForceInputError('FORMAL_VALIDATED BLOCKED: version-specific quality, quaternion convention, geometry/Cd and actual thrust unverified')
        self.verify_sources();t=utc64(utc_time)
        if t<self.start or t>self.stop:raise ForceInputError('Outside common product coverage; no extrapolation')
        rows={};provenance={};quality={}
        for k,d in self.data.items():
            i=int(np.searchsorted(d['Timestamp'],t,side='right')-1);age=float((t-d['Timestamp'][i])/np.timedelta64(1,'s'))
            if age>1.1:raise ForceInputError('Gap/stale snapshot; no bridging')
            rows[k]=(d,i);provenance[k]={**self.meta[k], 'record_index':i,'source_UTC':str(d['Timestamp'][i])+'Z','age_s':age,'time_method':'latest_observed_record_snapshot_NOT_interpolation'}
            quality[k]={key:int(d[key][i]) for key in ['Flags_q','SyncStatus']}
        d,i=rows['SC_ADYN'];s,j=rows['STRAATT'];m=float(d['m_SC'][i]);q=np.array(s['q'][j],copy=True);quality['SC_ADYN']['Flags_Platform']=int(d['Flags_Platform'][i]);quality['STRAATT']['Maneuver_Id']=int(s['Maneuver_Id'][j]);on=np.asarray(d['dt_thr'][i]);nominal=np.asarray(d['f_thr'][i])*1e-3
        mass=Parameter(m if np.isfinite(m) and m>0 else None,'kg','PARTIAL' if np.isfinite(m) and m>0 else 'INVALID','SC_ADYN.m_SC','Record and units verified; version-specific quality and uncertainty unverified')
        q_numeric_ok=bool(np.isfinite(q).all() and abs(np.dot(q,q)-1)<=1e-8)
        attitude=Parameter(q.tolist() if q_numeric_ok else None,'dimensionless','UNVERIFIED' if q_numeric_ok else 'INVALID','STRAATT.q','ITRF <- S/C reported; xyzw/wxyz and active/passive matrix convention unverified')
        thrust=Parameter(dict(on_time_s=on.tolist(),nominal_force_N=nominal.tolist(),active_branch_raw=int(d['thr_set'][i]),candidate_on_time=bool(np.any(on>0)),actual_force_N=None),'N','UNVERIFIED','SC_ADYN.dt_thr/f_thr/thr_set','f_thr is nominal mN converted to N; zero does not prove no thrust; Maneuver_Id is undecoded')
        return ForceInputs(str(t)+'Z',mass,attitude,Parameter(None,'m2','UNVERIFIED','SC_ADYN.A_*','Orbit-frame cross-section vectors are not verified complete facets; no norm shortcut'),Parameter(None,'dimensionless','UNVERIFIED','No paired geometry/GSI model acquired','Cd2.2 is a demonstration constant and is not used'),thrust,quality,provenance)
