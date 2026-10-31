"""Opt-in experimental force bridge; never changes the formal datum gate."""
import time
from .provisional_coordinate_adapter import ProvisionalCoordinateAdapter,A_WGS84
from .tiegcm_density_provider import DATUM

LABEL='PROVISIONAL_COORDINATE_A'


class ProvisionalEventBridge:
    def __init__(self, provider, *, authorization_label, branch_label, records):
        if authorization_label!=LABEL:
            raise ValueError('Explicit PROVISIONAL_COORDINATE_A required')
        self.provider=provider;self.branch_label=branch_label;self.records=records
        self.adapter=ProvisionalCoordinateAdapter(assumption=A_WGS84)

    def density_kg_m3(self,query):
        tick=time.perf_counter();c=self.adapter.adapt(query)
        result=self.provider.query_native(query.utc,c.model_latitude_deg,c.model_longitude_deg,c.model_zg_m,datum=DATUM)
        coverage=result.metadata.get('height_coverage_m',[None,None])
        self.records.append(dict(UTC=query.utc.isot,branch=self.branch_label,label=LABEL,lat=c.model_latitude_deg,
            lon=c.model_longitude_deg,assumed_native_ZG_m=c.model_zg_m,valid=result.valid,reason=result.reason,
            rho_kg_m3=result.rho_kg_m3,height_lower_m=coverage[0],height_upper_m=coverage[1],
            time_bracket=';'.join(result.metadata.get('time_utc',[])),query_s=time.perf_counter()-tick))
        if not result.valid:raise ValueError('PROVISIONAL density rejected: '+result.reason)
        return result.rho_kg_m3
