"""Observation comparison rules; no fitting, model adjustment or datum release."""
import numpy as np


def quality_mask(density, flags, fill_value=9.99e32):
    """0301: exactly 0 nominal, 1 anomalous; unknown codes quarantined.

    Finite positive density alone is insufficient. No density uncertainty or
    quality inference is made from agreement with any atmospheric model.
    """
    rho=np.asarray(density,float);flag=np.asarray(flags)
    if rho.shape!=flag.shape:raise ValueError('Aligned density and flags required')
    nominal=flag==0;known=(flag==0)|(flag==1)
    physical=np.isfinite(rho)&(rho>0)&(rho!=fill_value)&(rho<1e30)
    return nominal&physical,dict(anomalous=flag==1,unknown=~known,invalid_density=~physical)


def compare_density(predicted, observed):
    p,r=np.asarray(predicted,float),np.asarray(observed,float)
    if p.ndim!=1 or p.shape!=r.shape:raise ValueError('Aligned 1D paired observations required')
    if not len(p):return dict(n=0,MAE=None,RMSE=None,relative_RMS=None,relative_P95=None,bias=None,log_RMS=None,max_abs=None)
    if not np.isfinite(p).all() or not np.isfinite(r).all() or np.any(p<=0) or np.any(r<=0):
        raise ValueError('Do not silently drop invalid samples')
    e=p-r;rel=e/r
    return dict(n=len(p),MAE=float(np.mean(abs(e))),RMSE=float(np.sqrt(np.mean(e*e))),
        relative_RMS=float(np.sqrt(np.mean(rel*rel))),relative_P95=float(np.percentile(abs(rel),95)),
        bias=float(np.mean(e)),log_RMS=float(np.sqrt(np.mean(np.log(p/r)**2))),max_abs=float(abs(e).max()))


def periods(hours):
    x=np.asarray(hours,float)
    return {'pre':(x>=1)&(x<7),'event':x==7,'transition':(x>7)&(x<8),'post':(x>=8)&(x<=13),
            'all_forecast':(x>=1)&(x<=13)&(x!=7)}


def paired_valid_mask(quality, *predictions):
    mask=np.asarray(quality,bool).copy()
    for x in predictions:
        a=np.asarray(x,float)
        if a.shape!=mask.shape:raise ValueError('Paired sample identities required')
        mask &= np.isfinite(a)&(a>0)
    return mask
