"""Frozen pure evaluation kernel. This module has no file or target loader."""
import numpy as np


def score(target, forecast, weight, domain, common=None):
    """Inputs broadcast over [sample,ilev,lat,lon]. Quantiles use cosine-weighted empirical CDF."""
    target_ok = np.isfinite(target) & (target > 0) & domain
    finite = np.isfinite(forecast)
    own = target_ok & finite & (forecast > 0)
    valid = own if common is None else own & common
    result = dict(target_count=int(target_ok.sum()), valid_count=int(valid.sum()),
                  nonpositive_count=int((target_ok & finite & (forecast <= 0)).sum()),
                  nonfinite_count=int((target_ok & ~finite).sum()))
    result['coverage'] = result['valid_count']/result['target_count'] if result['target_count'] else None
    if not valid.any():
        return result | dict.fromkeys(('rmse','log_rmse','relative_rmse','mae','bias','log_bias',
                                      'absolute_p95','relative_p95','log_error_p05','log_error_p50',
                                      'log_error_p95','weight_sum','sse','log_sse'))
    w=np.broadcast_to(weight,target.shape)[valid]
    y,p=target[valid],forecast[valid]
    e=p-y
    le=np.log(p)-np.log(y)
    re=e/y
    def quantile(values, fraction):
        order=np.argsort(values,kind='stable')
        mass=np.cumsum(w[order])
        return float(values[order[np.searchsorted(mass,fraction*mass[-1])]])
    avg=lambda x: float(np.average(x,weights=w))
    return result | dict(rmse=avg(e**2)**.5,log_rmse=avg(le**2)**.5,relative_rmse=avg(re**2)**.5,
                         mae=avg(abs(e)),bias=avg(e),log_bias=avg(le),weight_sum=float(w.sum()),
                         sse=float(w @ (e**2)),log_sse=float(w @ (le**2)),
                         absolute_p95=quantile(abs(e),.95),
                         relative_p95=quantile(abs(re),.95),
                         **dict(zip(('log_error_p05','log_error_p50','log_error_p95'),
                                    [quantile(le,q) for q in (.05,.50,.95)])))


def evaluate(target, forecast, samples, methods, lat, thresholds):
    """Yield pooled event/lead and individual cutoff/lead rows, including strata."""
    if target.shape!=(21,29,36,72) or forecast.shape!=(len(methods),*target.shape):
        raise ValueError('Unexpected native evaluation grid')
    if len(samples)!=21 or len({(r['cutoff_id'],r['lead_hours']) for r in samples})!=21:
        raise ValueError('Invalid sample identity')
    weights=np.cos(np.deg2rad(lat))[None,None,:,None]
    for group_key in ('event_id','cutoff_id'):
        for group in sorted({r[group_key] for r in samples}):
            for lead in (1,3,6):
                index=[i for i,r in enumerate(samples) if r[group_key]==group and int(r['lead_hours'])==lead]
                y,p=target[index],forecast[:,index]
                common=np.all(np.isfinite(p)&(p>0),axis=0)
                domains={'global':True,'south_polar':lat[None,None,:,None]<=-60,
                         'north_polar':lat[None,None,:,None]>=60,
                         'low_density':y<=thresholds[None,:,None,None]}
                domains.update({f'ilev_{i:02}':np.arange(29)[None,:,None,None]==i for i in range(29)})
                for region,domain in domains.items():
                    for name,values in zip(methods,p):
                        for mask,valid in [('own',None),('common',common)]:
                            yield dict(group_key=group_key,group=group,lead_hours=lead,
                                       method=name,region=region,mask=mask,**score(y,values,weights,domain,valid))


def self_test():
    y=np.array([1.,4.,2.])
    p=np.array([2.,-1.,2.])
    r=score(y,p,np.array([1.,2.,3.]),True)
    assert r['coverage']==2/3 and r['nonpositive_count']==1 and r['rmse']==.5
    assert np.isclose(r['log_rmse'],np.log(2)/2) and r['absolute_p95']==1
    assert score(y,p,np.ones(3),True,np.array([False,False,True]))['rmse']==0


if __name__=='__main__':
    self_test()
