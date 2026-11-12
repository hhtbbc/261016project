"""Frozen descriptive strata and paired metrics; no fitting or uncertainty claims."""
import numpy as np
from .swarm_density_comparison import compare_density,paired_valid_mask

MIN_SAMPLES=30
HEIGHT_EDGES_KM=(400,430,440,450,460,470,500)

def strata(latitude, height_m, utc):
    lat=np.asarray(latitude,float);height=np.asarray(height_m,float)/1000
    t=np.asarray(utc,dtype='datetime64[ns]');hour=(t-t.astype('datetime64[D]'))/np.timedelta64(1,'h')
    if lat.shape!=height.shape or t.shape!=lat.shape:raise ValueError('Aligned sample IDs required')
    a=np.abs(lat)
    out={'all':np.ones(lat.shape,bool),'low':a<30,'mid':(a>=30)&(a<60),'high':a>=60,
         'north':lat>=60,'south':lat<=-60,'midlow':a<60,
         'north_hemisphere':lat>=0,'south_hemisphere':lat<0}
    for x,y in zip(HEIGHT_EDGES_KM[:-1],HEIGHT_EDGES_KM[1:]):out[f'height_{x}_{y}km']=(height>=x)&(height<y)
    out['height_outside_bins']=(height<HEIGHT_EDGES_KM[0])|(height>=HEIGHT_EDGES_KM[-1])
    for x in range(0,24,3):out[f'UTC_{x:02d}_{x+3:02d}']=(hour>=x)&(hour<x+3)
    return out

def metric_row(predicted,observed,quality,common,region):
    p,o=np.asarray(predicted,float),np.asarray(observed,float)
    q,c,r=map(lambda v:np.asarray(v,bool),(quality,common,region))
    if any(x.shape!=o.shape for x in (p,q,c,r)):raise ValueError('Aligned arrays required')
    own=paired_valid_mask(q,p);selected=c&r
    if np.any(selected&~own):raise ValueError('Common domain includes invalid sample')
    eligible=int((q&r).sum());n=int(selected.sum());status='OK' if n>=MIN_SAMPLES else 'N/A_INSUFFICIENT_SAMPLES'
    result=compare_density(p[selected],o[selected]) if n>=MIN_SAMPLES else compare_density([],[])
    result['n']=n
    x,y=p[selected],o[selected]
    pearson=float(np.corrcoef(x,y)[0,1]) if n>=MIN_SAMPLES and np.std(x)>0 and np.std(y)>0 else None
    return dict(status=status,eligible=eligible,own_valid=int((own&r).sum()),
                coverage=float((own&r).sum()/eligible) if eligible else None,
                common_coverage=n/eligible if eligible else None,**result,Pearson=pearson,
                relative_bias=float(np.mean((x-y)/y)) if n>=MIN_SAMPLES else None,
                bias_over_mean_observed=float(np.mean(x-y)/np.mean(y)) if n>=MIN_SAMPLES else None,
                observed_mean=float(np.mean(y)) if n else None,
                simulated_mean=float(np.mean(x)) if n else None)
