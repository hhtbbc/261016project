"""Conservative native-ZG coverage gate; no height datum conversion implied."""
import numpy as np

def stencil_coverage(query_height_m, heights_m, density_kg_m3, time_valid):
    """Arrays: query (N,), stencil heights/density (N, corners, levels).

    Caller supplies both temporal endpoints and all horizontal corners, expressed
    in a verified common vertical datum. This checks coverage, not interpolation.
    """
    q=np.asarray(query_height_m,dtype=float)
    z=np.asarray(heights_m,dtype=float);rho=np.asarray(density_kg_m3,dtype=float)
    tv=np.asarray(time_valid,dtype=bool)
    if q.ndim!=1 or z.ndim!=3 or rho.shape!=z.shape or z.shape[0]!=len(q) or tv.shape!=q.shape or z.shape[1]<1 or z.shape[2]<2:
        raise ValueError('Invalid query/stencil shapes')
    good=np.isfinite(z)&np.isfinite(rho)&(abs(z)<1e30)&(rho>0)&(rho<1e30)
    column_good=good.all(axis=2)&(np.diff(z,axis=2)>0).all(axis=2)
    vertical=((q[:,None]>=z[:,:,0])&(q[:,None]<=z[:,:,-1])).all(axis=1)
    valid=tv&np.isfinite(q)&column_good.all(axis=1)&vertical
    return {'valid':valid,'valid_fraction':float(valid.mean()) if len(q) else None,
            'total':len(q),'valid_count':int(valid.sum()),
            'time_invalid':int((~tv).sum()),'bad_columns':int((~column_good.all(axis=1)).sum()),
            'vertical_outside':int((~vertical).sum())}
