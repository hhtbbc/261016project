"""Time-explicit scalar baseline and descriptive diagnostics; no optimization."""
from dataclasses import dataclass
import numpy as np
from atmosphere.causal_density_correction import LogMedianCorrection
from evaluation.swarm_density_comparison import paired_valid_mask

@dataclass(frozen=True)
class RollingOrigin:
    day: str
    hour: int=18
    def __post_init__(self):
        if str(np.datetime64(self.day,'D'))!=self.day or self.hour not in [6,18]:raise ValueError('Registered day/cutoff required')
    @property
    def cutoff(self):return f'{self.day}T{self.hour:02d}:00:00Z'
    def masks(self,utc):
        t=np.asarray(utc,dtype='datetime64[ns]');cut=np.datetime64(self.cutoff[:-1],'ns')
        if np.isnat(t).any():raise ValueError('Finite UTC required')
        return {'analysis':(t>=cut-np.timedelta64(3,'h'))&(t<cut),**{f'future_{h}h':(t>=cut)&(t<cut+np.timedelta64(h,'h')) for h in [1,3,6]},'block_1_3h':(t>=cut+np.timedelta64(1,'h'))&(t<cut+np.timedelta64(3,'h')),'block_3_6h':(t>=cut+np.timedelta64(3,'h'))&(t<cut+np.timedelta64(6,'h'))}
    def fit(self,utc,observed,background,quality,*,satellite):
        if satellite!='A':raise ValueError('A history only')
        t=np.asarray(utc,dtype='datetime64[ns]');o=np.asarray(observed,float);p=np.asarray(background,float);q=np.asarray(quality,bool)
        if any(x.shape!=t.shape for x in [o,p,q]):raise ValueError('Aligned arrays required')
        m=self.masks(t)['analysis']&paired_valid_mask(q,p,o)
        if not m.any():raise ValueError('No eligible history')
        e=np.log(o[m])-np.log(p[m]);return LogMedianCorrection(float(np.median(e)),int(m.sum()),cutoff_UTC=self.cutoff),m,e

def diagnostic_quintiles(observed):
    x=np.asarray(observed,float)
    if x.ndim!=1 or not len(x) or not np.isfinite(x).all() or np.any(x<=0):raise ValueError('Positive aligned observations required')
    edges=np.quantile(x,[0,.2,.4,.6,.8,1.]);idx=np.searchsorted(edges[1:-1],x,side='right')
    return idx,edges  # ties stay together; no density perturbation to force equal N

def joint_flags(raw,corrected,raw_low,corrected_low):
    adequate=all(x.get('status')=='OK' for x in [raw,corrected,raw_low,corrected_low])
    if not adequate:return dict(RMSE_BENEFIT=None,RELATIVE_RMS_BENEFIT=None,TAIL_NONWORSENED=None,LOW_LATITUDE_BIAS_NONWORSENED=None,JOINT_NO_REGRET=False,status='N/A_INSUFFICIENT_SAMPLES')
    flags=dict(RMSE_BENEFIT=corrected['RMSE']<raw['RMSE'],RELATIVE_RMS_BENEFIT=corrected['relative_RMS']<raw['relative_RMS'],TAIL_NONWORSENED=corrected['relative_P95']<=raw['relative_P95'],LOW_LATITUDE_BIAS_NONWORSENED=abs(corrected_low['relative_bias'])<=abs(raw_low['relative_bias']))
    return dict(**flags,JOINT_NO_REGRET=all(flags.values()),status='OK')
