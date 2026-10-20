"""Research-only force bridge; no change to the formal external density gate."""
from dataclasses import asdict
import time
import numpy as np
from orbit.drag import DragForce, DragProperties
from .provisional_coordinate_adapter import ProvisionalCoordinateAdapter

LABELS = ('PROVISIONAL', 'SYNTHETIC_AERODYNAMIC_PARAMETERS', 'HINDCAST')

class ProvisionalDensityError(RuntimeError):
    pass

class _ExplicitResearchDensity:
    """Private bridge instantiated only by an acknowledged research force."""
    def __init__(self, provider, adapter):
        self.provider=provider; self.adapter=adapter; self.last=None
        self.calls=0; self.failures=0; self.elapsed_s=0.
    def density_kg_m3(self, query):
        self.calls+=1; started=time.perf_counter()
        try:
            self.last=self.adapter.query_provisional(self.provider,query)
            result=self.last.native_result
            if not result.valid:
                raise ProvisionalDensityError(result.reason)
            rho=float(result.rho_kg_m3)
            if not np.isfinite(rho) or rho<0:
                raise ProvisionalDensityError('NONFINITE_OR_NEGATIVE_DENSITY')
            # Real native columns require strictly positive rho; zero is possible
            # only in explicitly synthetic test providers, not a missing fallback.
            return rho
        except Exception:
            self.failures+=1
            raise
        finally:
            self.elapsed_s+=time.perf_counter()-started

class ProvisionalDragForce:
    """Explicit (t,r_GCRS,v_GCRS) research force with zero ITRS wind.

    Reuses the validated DragForce/EarthFixedFrame, provisional mapping and native
    interpolator. This object itself has no operational density_kg_m3 method.
    """
    labels=LABELS
    def __init__(self, *, frame, provider, adapter, properties,
                 acknowledge_provisional, audit_sink=None):
        if acknowledge_provisional is not True:
            raise ValueError('Explicit PROVISIONAL acknowledgment required')
        if not isinstance(adapter,ProvisionalCoordinateAdapter):
            raise TypeError('Explicit provisional coordinate adapter required')
        if not isinstance(properties,DragProperties) or LABELS[1] not in properties.provenance:
            raise ValueError('Explicit synthetic aerodynamic parameter provenance required')
        self.bridge=_ExplicitResearchDensity(provider,adapter)
        self.force=DragForce(frame,self.bridge,properties)  # zero ground-relative wind
        self.audit_sink=audit_sink
        self.phase_calls={'rhs':0,'output':0,'test':0};self.total_elapsed_s=0.
    def evaluate(self, seconds, position, velocity, *, phase='rhs'):
        if phase not in self.phase_calls:raise ValueError('Unknown audit phase')
        self.phase_calls[phase]+=1;started=time.perf_counter()
        try:
            value=self.force.evaluate(seconds,position,velocity)
        except Exception as error:
            if self.audit_sink is not None:
                self.audit_sink({'labels':LABELS,'phase':phase,'seconds':float(seconds),
                                 'source':getattr(self.bridge.provider,'source','unknown'),
                                 'assumption':self.bridge.adapter.assumption,
                                 'failure':str(error)})
            raise
        finally:
            self.total_elapsed_s+=time.perf_counter()-started
        record={'labels':LABELS,'phase':phase,'seconds':float(seconds),
                'source':self.bridge.provider.source,
                'mapping':asdict(self.bridge.last.coordinates),
                'native_query':asdict(self.bridge.last.native_result),
                'properties':asdict(value['properties']),
                'position_gcrs_m':np.asarray(position).tolist(),
                'velocity_gcrs_m_s':np.asarray(velocity).tolist(),
                'relative_velocity_itrs_m_s':value['relative_velocity_itrs_m_s'].tolist(),
                'acceleration_itrs_m_s2':value['acceleration_itrs_m_s2'].tolist(),
                'acceleration_gcrs_m_s2':value['acceleration_gcrs_m_s2'].tolist()}
        if self.audit_sink is not None:self.audit_sink(record)
        value.update(labels=LABELS,provisional_query=self.bridge.last)
        return value
    def __call__(self,seconds,position,velocity):
        return self.evaluate(seconds,position,velocity)['acceleration_gcrs_m_s2']
    def statistics(self):
        p=self.bridge.provider
        cache=getattr(p,'cache',{})
        return {'labels':LABELS,'density_queries':self.bridge.calls,
                'failures':self.bridge.failures,'density_query_seconds':self.bridge.elapsed_s,
                'frame_and_drag_evaluate_seconds':self.total_elapsed_s,
                'phase_calls':self.phase_calls.copy(),'column_reads':getattr(p,'reads',None),
                'cached_columns':len(cache),
                'cached_array_bytes':sum(z.nbytes+rho.nbytes for z,rho in cache.values())}
