"""Frozen scalar output correction. No model-state update, fallback or tuning."""
from dataclasses import dataclass,asdict
import numpy as np
from .causal_observation_operator import split_masks
from evaluation.swarm_density_comparison import paired_valid_mask

@dataclass(frozen=True)
class LogMedianCorrection:
    log_bias: float
    sample_count: int
    cutoff_UTC: str='2022-03-24T06:00:00Z'
    source_satellite: str='A'
    def __post_init__(self):
        if not np.isfinite(self.log_bias) or self.sample_count<1 or self.source_satellite!='A':raise ValueError('Finite A-history estimate required')
    @property
    def multiplier(self):return float(np.exp(self.log_bias))
    def apply(self,background):
        x=np.asarray(background,float)
        if not np.isfinite(x).all() or np.any(x<=0):raise ValueError('Invalid background is never filled')
        y=x*self.multiplier
        if not np.isfinite(y).all() or np.any(y<=0):raise ValueError('Invalid correction')
        return y

def fit_past_A(utc,observed,background,quality,*,satellite):
    if satellite!='A':raise ValueError('Only past Swarm A may estimate this correction')
    t=np.asarray(utc,dtype='datetime64[ns]');o=np.asarray(observed,float);p=np.asarray(background,float);q=np.asarray(quality,bool)
    if any(a.shape!=t.shape for a in [o,p,q]) or np.isnat(t).any():raise ValueError('Aligned explicit UTC required')
    m=split_masks(t)['calibration']&paired_valid_mask(q,p,o)
    if not m.any():raise ValueError('No valid past calibration samples')
    residual=np.log(o[m])-np.log(p[m]);return LogMedianCorrection(float(np.median(residual)),int(m.sum())),m,residual
