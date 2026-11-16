"""Fixed latitude-band medians; explicit unsupported regions, no fallback or tuning."""
from pathlib import Path
import hashlib,json
import numpy as np
from .late_day_correction import RollingOrigin,joint_flags
from atmosphere.causal_density_correction import LogMedianCorrection
ROOT=Path(__file__).resolve().parents[2]
BANDS=('low','mid','high')
def latitude_band(latitude):
    lat=np.asarray(latitude,float)
    if not np.isfinite(lat).all() or np.any(abs(lat)>90):raise ValueError('Finite GRS80 latitude in [-90,90] required')
    a=abs(lat);return np.where(a<30,0,np.where(a<60,1,2))

def sample_sha(utc,latitude,observed,model):
    h=hashlib.sha256()
    for x,dtype in [(np.asarray(utc,dtype='datetime64[ns]').astype('int64'),'<i8'),(latitude,'<f8'),(observed,'<f8'),(model,'<f8')]:h.update(np.asarray(x,dtype=dtype).tobytes())
    return h.hexdigest()

def _coefficient(t,lat,o,p,mask,min_samples=30):
    n=int(mask.sum());base=dict(N=n,first_UTC=str(t[mask][0])+'Z' if n else None,last_UTC=str(t[mask][-1])+'Z' if n else None,sample_SHA256=sample_sha(t[mask],lat[mask],o[mask],p[mask]))
    if n<min_samples:return dict(**base,status='UNSUPPORTED_INSUFFICIENT_HISTORY',b=None,multiplier=None)
    residual=np.log(o[mask])-np.log(p[mask]);b=float(np.median(residual));return dict(**base,status='SUPPORTED',b=b,multiplier=float(np.exp(b)))

def _historical_inputs(utc,latitude,observed,background,quality,*,day,hour=18,satellite='A'):
    if satellite!='A':raise ValueError('Only Swarm A may fit')
    t=np.asarray(utc,dtype='datetime64[ns]');lat=np.asarray(latitude,float);o=np.asarray(observed,float);p=np.asarray(background,float);q=np.asarray(quality,bool)
    if any(x.shape!=t.shape for x in [lat,o,p,q]) or t.ndim!=1:raise ValueError('Aligned 1D inputs required')
    bands=latitude_band(lat);m=RollingOrigin(day,hour).masks(t)['analysis']&q
    if not np.isfinite(o[m]).all() or not np.isfinite(p[m]).all() or np.any(o[m]<=0) or np.any(p[m]<=0):raise ValueError('Invalid eligible historical density rejected, never silently filled')
    return t,lat,o,p,bands,m

def fit_global_history(utc,latitude,observed,background,quality,*,day,hour=6,satellite='A'):
    t,lat,o,p,bands,m=_historical_inputs(utc,latitude,observed,background,quality,day=day,hour=hour,satellite=satellite)
    return _coefficient(t,lat,o,p,m),m

def fit_history(utc,latitude,observed,background,quality,*,day,hour=18,satellite='A'):
    t,lat,o,p,bands,m=_historical_inputs(utc,latitude,observed,background,quality,day=day,hour=hour,satellite=satellite)
    global_fit=_coefficient(t,lat,o,p,m)
    local={name:_coefficient(t,lat,o,p,m&(bands==i)) for i,name in enumerate(BANDS)}
    return dict(global_fit=global_fit,latitude=local,day=day,cutoff=RollingOrigin(day,hour).cutoff,satellite='A'),m

def apply_global(background,fit):
    if fit['status']!='SUPPORTED':raise ValueError('Unsupported global coefficient')
    return LogMedianCorrection(fit['b'],fit['N']).apply(background)

def apply_latitude(background,latitude,coefficients):
    p=np.asarray(background,float);bands=latitude_band(latitude)
    if p.shape!=bands.shape or not np.isfinite(p).all() or np.any(p<=0):raise ValueError('Positive aligned background required')
    out=np.full(p.shape,np.nan);support=np.zeros(p.shape,bool)
    for i,name in enumerate(BANDS):
        fit=coefficients[name];m=bands==i
        if fit['status']=='SUPPORTED':out[m]=LogMedianCorrection(fit['b'],fit['N']).apply(p[m]);support[m]=True
    return out,support

def assess_joint(raw,corrected,raw_regions,corrected_regions,complete_support=True):
    adequate=complete_support and all(raw_regions[k].get('status')=='OK' and corrected_regions[k].get('status')=='OK' for k in BANDS)
    if not adequate:return dict(RMSE_BENEFIT=None,RELATIVE_RMS_BENEFIT=None,TAIL_NONWORSENED=None,LOW_LATITUDE_BIAS_NONWORSENED=None,JOINT_NO_REGRET='N/A_INSUFFICIENT_SAMPLES',status='N/A_INSUFFICIENT_SAMPLES')
    flags=joint_flags(raw,corrected,raw_regions['low'],corrected_regions['low']);flags['JOINT_NO_REGRET']='PASS' if flags['JOINT_NO_REGRET'] else 'FAIL';return flags

def exclusive_json(path,obj):
    p=Path(path);p.resolve().relative_to(ROOT)
    with p.open('x') as out:json.dump(obj,out,indent=2,allow_nan=False)

def supported_metric(predicted,observed,quality,common,region,support):
    """Preserve requested IDs; an unsupported point makes the full score N/A."""
    from .swarm_crossyear import metric_row
    from .swarm_density_comparison import compare_density
    p,o=np.asarray(predicted,float),np.asarray(observed,float);q,c,r,s=map(lambda x:np.asarray(x,bool),(quality,common,region,support));selected=c&r;n=int(selected.sum());ns=int((selected&s).sum())
    if np.any(selected&~s):
        empty=compare_density([],[]);empty['n']=n;eligible=int((q&r).sum());own=int((q&r&s&np.isfinite(p)&(p>0)).sum())
        return dict(status='N/A_UNSUPPORTED_INSUFFICIENT_HISTORY',eligible=eligible,own_valid=own,coverage=own/eligible if eligible else None,common_coverage=ns/eligible if eligible else None,**empty,Pearson=None,relative_bias=None,bias_over_mean_observed=None,observed_mean=float(np.mean(o[selected])) if n else None,simulated_mean=None,n_supported=ns,n_scored=0)
    out=metric_row(p,o,q,c,r);return dict(**out,n_supported=ns,n_scored=n if out['status']=='OK' else 0)
