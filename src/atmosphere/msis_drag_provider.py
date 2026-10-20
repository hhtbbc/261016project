"""Explicit synthetic-aerodynamics MSIS research force; original DragForce reused."""
from dataclasses import asdict
import time
import numpy as np
from orbit.drag import DragForce, DragProperties
from atmosphere.msis_density_provider import MsisDensityProvider
from atmosphere.provisional_drag_provider import LABELS


class _AuditedDensity:
    def __init__(self, provider):
        self.provider=provider;self.last=None;self.calls=0;self.failures=0;self.latency_s=[]
    def density_kg_m3(self, query):
        self.calls+=1;tick=time.perf_counter()
        try:
            self.last=self.provider.query(query.utc,query.longitude_deg,query.latitude_deg,query.height_wgs84_m)
            if not self.last.valid or not np.isfinite(self.last.rho_kg_m3) or self.last.rho_kg_m3<=0:
                raise ValueError('Invalid MSIS density; no fallback')
            return self.last.rho_kg_m3
        except Exception:
            self.failures+=1;raise
        finally:self.latency_s.append(time.perf_counter()-tick)


class MsisResearchDrag:
    labels=LABELS
    def __init__(self, *, frame, provider, properties, acknowledge_provisional, audit_sink=None):
        if acknowledge_provisional is not True or not isinstance(provider,MsisDensityProvider):
            raise ValueError('Explicit MSIS provider and research acknowledgment required')
        if not isinstance(properties,DragProperties) or LABELS[1] not in properties.provenance:
            raise ValueError('Explicit synthetic aerodynamic parameters required')
        self.bridge=_AuditedDensity(provider)
        self.force=DragForce(frame,self.bridge,properties)
        self.audit_sink=audit_sink;self.phase_calls={'rhs':0,'output':0,'test':0};self.elapsed_s=0.
    def evaluate(self,seconds,position,velocity,*,phase='rhs'):
        if phase not in self.phase_calls:raise ValueError('Invalid phase')
        self.phase_calls[phase]+=1;tick=time.perf_counter()
        try:value=self.force.evaluate(seconds,position,velocity)
        except Exception as error:
            if self.audit_sink:self.audit_sink({'labels':LABELS,'phase':phase,'seconds':seconds,'failure':str(error)})
            raise
        finally:self.elapsed_s+=time.perf_counter()-tick
        q=value['query'];d=self.bridge.last
        record={'labels':LABELS,'phase':phase,'seconds':float(seconds),'utc':q.utc.to_value('isot',subfmt='date_hms'),
            'utc_jd1':float(q.utc.jd1),'utc_jd2':float(q.utc.jd2),'source':d.model,'coordinate_mapping':'WGS84_NATIVE_MSIS',
            'position_gcrs_m':np.asarray(position).tolist(),'velocity_gcrs_m_s':np.asarray(velocity).tolist(),
            'position_itrs_m':q.position_itrs_m.tolist(),'latitude_wgs84_deg':q.latitude_deg,
            'longitude_wgs84_deg':q.longitude_deg,'height_wgs84_m':q.height_wgs84_m,
            'relative_velocity_itrs_m_s':value['relative_velocity_itrs_m_s'].tolist(),
            'acceleration_gcrs_m_s2':value['acceleration_gcrs_m_s2'].tolist(),
            'acceleration_itrs_m_s2':value['acceleration_itrs_m_s2'].tolist(),
            'rho_kg_m3':d.rho_kg_m3,'density_valid':d.valid,'density_status':d.status,
            'drivers':asdict(d.drivers),'properties':asdict(value['properties']),
            'density_query_seconds':self.bridge.latency_s[-1]}
        if self.audit_sink:self.audit_sink(record)
        value.update(labels=LABELS,msis_record=record)
        return value
    def __call__(self,seconds,position,velocity):
        return self.evaluate(seconds,position,velocity)['acceleration_gcrs_m_s2']
    def statistics(self):
        a=np.asarray(self.bridge.latency_s)
        return {'labels':LABELS,'density_queries':self.bridge.calls,'failures':self.bridge.failures,
            'density_query_seconds':float(a.sum()),'query_mean_ms':float(a.mean()*1000),
            'query_p95_ms':float(np.percentile(a,95)*1000),'phase_calls':self.phase_calls,
            'frame_and_drag_evaluate_seconds':self.elapsed_s,'cache':'No density cache; explicit frozen drivers; Fortran backend internal state reused'}
