"""Date-explicit replication of v10's scalar log-median output correction."""
from dataclasses import dataclass
import numpy as np
from atmosphere.causal_density_correction import LogMedianCorrection
from evaluation.swarm_density_comparison import paired_valid_mask

@dataclass(frozen=True)
class CausalDay:
    day: str
    def __post_init__(self):
        t=np.datetime64(self.day,'D')
        if str(t)!=self.day:raise ValueError('Explicit YYYY-MM-DD required')
    @property
    def cutoff(self):return self.day+'T06:00:00Z'
    def masks(self,utc):
        t=np.asarray(utc,dtype='datetime64[ns]');cut=np.datetime64(self.day+'T06:00:00','ns')
        if np.isnat(t).any():raise ValueError('Finite UTC required')
        return {'analysis':(t>=cut-np.timedelta64(3,'h'))&(t<cut),**{f'future_{h}h':(t>=cut)&(t<cut+np.timedelta64(h,'h')) for h in [1,3,6]},'incremental_1_3h':(t>=cut+np.timedelta64(1,'h'))&(t<cut+np.timedelta64(3,'h')),'incremental_3_6h':(t>=cut+np.timedelta64(3,'h'))&(t<cut+np.timedelta64(6,'h'))}
    def fit(self,utc,observed,background,quality,*,satellite):
        if satellite!='A':raise ValueError('Only historical Swarm A may fit')
        t=np.asarray(utc,dtype='datetime64[ns]');o=np.asarray(observed,float);p=np.asarray(background,float);q=np.asarray(quality,bool)
        if any(a.shape!=t.shape for a in [o,p,q]):raise ValueError('Aligned arrays required')
        m=self.masks(t)['analysis']&paired_valid_mask(q,p,o)
        if not m.any():raise ValueError('No eligible past observations')
        e=np.log(o[m])-np.log(p[m]);return LogMedianCorrection(float(np.median(e)),int(m.sum()),cutoff_UTC=self.cutoff),m,e

def frozen_transfer(case,coefficient):
    if case!='B14':raise ValueError('2022 B14 transfer is only registered for B14')
    if coefficient!=0.1261252775057784:raise ValueError('Frozen v10 coefficient changed')
    return LogMedianCorrection(coefficient,360,cutoff_UTC='2022-03-24T06:00:00Z')
