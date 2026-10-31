"""Read-only physical metrics and timeline contracts for ideal updates."""
import numpy as np


def update_indices(day_offset, history):
    if history not in (0,1):raise ValueError('Official history 0/1 only')
    return list(range(day_offset+7-history,day_offset+14))


def splice_at_seven(open_loop,updated):
    a,b=np.asarray(open_loop),np.asarray(updated)
    if a.shape[0]!=13 or b.shape[0]!=7 or a.shape[1:]!=b.shape[1:]:
        raise ValueError('01-13 open / 07-13 updated states required')
    # 07 pre-reset remains in the jump audit; this array stores post-reset 07.
    return np.concatenate((a[:6],b),axis=0)


def improvement_percent(before,after):
    if before is None or after is None or before==0:return None
    return 100*(before-after)/before


def physical_stats(pred,truth,lat,region=None,common_columns=None,*,relative=False):
    """Float64, cos(latitude) weights; no relative-error denominator floor.

    RMSE_all_points and mean_layer_RMSE are intentionally distinct. Relative
    P95 is unweighted as in the existing protocol. Missing values are counted.
    """
    p,t=np.asarray(pred,float),np.asarray(truth,float)
    if p.shape!=t.shape or p.ndim!=3:raise ValueError('Aligned layer/lat/lon arrays required')
    lat=np.asarray(lat,float)
    if lat.shape!=(p.shape[1],):raise ValueError('Latitude size mismatch')
    r=np.ones(p.shape[1:],bool) if region is None else np.asarray(region,bool)
    if r.shape!=p.shape[1:]:raise ValueError('Region shape')
    good=np.isfinite(p)&np.isfinite(t)&(np.abs(p)<1e30)&(np.abs(t)<1e30)
    if relative:good&=(p>0)&(t>0)
    original=good & r[None]
    if common_columns is not None:
        cc=np.asarray(common_columns,bool)
        if cc.shape!=r.shape:raise ValueError('Column mask shape')
        good &= cc[None]
    good &= r[None]
    w=np.broadcast_to(np.cos(np.deg2rad(lat))[None,:,None],p.shape)
    weight=np.where(good,w,0.);den=weight.sum(axis=(1,2));total=float(weight.sum())
    count=int(good.sum());requested=int(np.broadcast_to(r,p.shape).sum())
    base=dict(requested_points=requested,valid_points=count,invalid_pressure_points=int((~original&r[None]).sum()),
              common_domain_excluded_points=int(original.sum())-count,valid_fraction=count/requested if requested else 0.)
    if not count:return dict(**base,RMSE=None,mean_layer_RMSE=None,MAE=None,bias=None,max_abs=None,
                             relative_RMS=None,mean_layer_relative_RMS=None,relative_P95=None,log_RMS=None)
    d=np.where(good,p-t,0.)
    layer_mse=np.divide((weight*d*d).sum(axis=(1,2)),den,out=np.full(len(p),np.nan),where=den>0)
    result=dict(**base,RMSE=float(np.sqrt((weight*d*d).sum()/total)),mean_layer_RMSE=float(np.nanmean(np.sqrt(layer_mse))),
        MAE=float((weight*abs(d)).sum()/total),bias=float((weight*d).sum()/total),max_abs=float(abs(d[good]).max()),
        relative_RMS=None,mean_layer_relative_RMS=None,relative_P95=None,log_RMS=None)
    if relative:
        e=np.zeros_like(p);np.divide(d,t,out=e,where=good)
        lg=np.zeros_like(p);lg[good]=np.log(p[good]/t[good])
        layer=np.divide((weight*e*e).sum(axis=(1,2)),den,out=np.full(len(p),np.nan),where=den>0)
        result.update(relative_RMS=float(np.sqrt((weight*e*e).sum()/total)),mean_layer_relative_RMS=float(np.nanmean(np.sqrt(layer))),
            relative_P95=float(np.percentile(abs(e[good]),95)),log_RMS=float(np.sqrt((weight*lg*lg).sum()/total)))
    return result


def layer_rmse(pred,truth,lat):
    p,t=np.asarray(pred,float),np.asarray(truth,float)
    w=np.cos(np.deg2rad(lat))[:,None]
    return np.sqrt(np.einsum('cij,ij->c',(p-t)**2,np.broadcast_to(w,p.shape[1:]))/(w.sum()*p.shape[2]))
