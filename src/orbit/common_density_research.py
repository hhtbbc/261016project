"""Isolated H6/density experiment wiring. No operational TIE datum adaptation."""
import time
import numpy as np
from pathlib import Path
from orbit.drag import EarthFixedFrame,DragProperties
from atmosphere.msis_density_provider import FrozenGfzDrivers,MsisDensityProvider
from atmosphere.msis_drag_provider import MsisResearchDrag
from atmosphere.tiegcm_density_provider import TiegcmDensityProvider
from atmosphere.provisional_coordinate_adapter import ProvisionalCoordinateAdapter,A_WGS84,B_SPHERE
from atmosphere.provisional_drag_provider import ProvisionalDragForce
ROOT=Path(__file__).resolve().parents[2]
LABELS=('PROVISIONAL','SYNTHETIC_AERODYNAMIC_PARAMETERS','HINDCAST','FORCE_MODEL_INCOMPLETE','PROVISIONAL_EPHEMERIS')

def demonstration_properties():
    return DragProperties(400.,1.,2.2,'SYNTHETIC_AERODYNAMIC_PARAMETERS; not actual Swarm-A aero')

class TimedDensity:
    def __init__(self,bridge):self.bridge=bridge;self.latencies=[]
    def density_kg_m3(self,query):
        tick=time.perf_counter()
        try:
            rho=self.bridge.density_kg_m3(query)
            if not np.isfinite(rho) or rho<=0:raise ValueError('Invalid research density; no fallback')
            return rho
        finally:self.latencies.append(time.perf_counter()-tick)

class DensityResearchForce:
    def __init__(self, model, epoch, audit_sink=None):
        if model not in ('C1','C2','C3'):raise ValueError('Explicit supported density model required')
        self.model=model;self.last_record=None
        def sink(record):
            record=dict(record);record['labels']=LABELS;record['experiment_model']=model
            record['density_query_seconds']=self.timer.latencies[-1] if self.timer.latencies else None
            self.last_record=record
            if audit_sink is not None:audit_sink(record)
        frame=EarthFixedFrame(epoch);properties=demonstration_properties()
        if model=='C1':
            self.provider=MsisDensityProvider(FrozenGfzDrivers(ROOT/'configs/nrlmsis2023_gfz_frozen.json'),version='2.1')
            self.inner=MsisResearchDrag(frame=frame,provider=self.provider,properties=properties,acknowledge_provisional=True,audit_sink=sink)
        else:
            self.provider=TiegcmDensityProvider((ROOT/'experiments/tiegcm2023_s7_continuous_v1').glob('secondary_*.nc'),'S7',cache_columns=4096)
            assumption=A_WGS84 if model=='C2' else B_SPHERE
            adapter=ProvisionalCoordinateAdapter(assumption=assumption,**({'sphere_radius_m':6371000.} if model=='C3' else {}))
            self.inner=ProvisionalDragForce(frame=frame,provider=self.provider,adapter=adapter,properties=properties,acknowledge_provisional=True,audit_sink=sink)
        self.timer=TimedDensity(self.inner.bridge);self.inner.force.density=self.timer
    def evaluate(self,t,r,v,*,phase='rhs'):
        value=self.inner.evaluate(t,r,v,phase=phase)
        if np.dot(value['relative_velocity_itrs_m_s'],value['acceleration_itrs_m_s2'])>0:raise ValueError('Drag sign violation')
        value['labels']=LABELS;return value
    def __call__(self,t,r,v):return self.evaluate(t,r,v)['acceleration_gcrs_m_s2']
    def statistics(self):
        a=np.asarray(self.timer.latencies);s=self.inner.statistics();s.update(labels=LABELS,query_mean_ms=float(a.mean()*1000),query_p95_ms=float(np.percentile(a,95)*1000),instrumented_density_seconds=float(a.sum()))
        if self.model!='C1':
            s['column_cache_hits']=8*self.inner.bridge.calls-self.provider.reads;s['cache_capacity_columns']=self.provider.limit
        return s
    def close(self):
        if hasattr(self.provider,'close'):self.provider.close()
