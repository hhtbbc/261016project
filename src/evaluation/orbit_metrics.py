"""Position-error statistics and right-handed radial/along-track/cross-track basis."""
import numpy as np

def rac_errors(delta_position,reference_position,reference_velocity):
    d=np.asarray(delta_position);r=np.asarray(reference_position);v=np.asarray(reference_velocity)
    if d.shape!=r.shape or r.shape!=v.shape or r.ndim!=2 or r.shape[1]!=3:raise ValueError('Shape mismatch')
    if not all(np.isfinite(x).all() for x in [d,r,v]):raise ValueError('Nonfinite metrics input')
    rr=np.linalg.norm(r,axis=1);h=np.cross(r,v);hh=np.linalg.norm(h,axis=1)
    if np.any(rr==0) or np.any(hh==0):raise ValueError('Degenerate RAC basis')
    R=r/rr[:,None];C=h/hh[:,None];A=np.cross(C,R)
    basis=np.stack([R,A,C],axis=1)
    if np.max(abs(basis@basis.transpose(0,2,1)-np.eye(3)))>1e-10:raise ValueError('RAC not orthonormal')
    return np.einsum('nij,nj->ni',basis,d)

def summarize_errors(delta,rac):
    error=np.linalg.norm(delta,axis=1)
    if not len(error) or not np.isfinite(error).all():raise ValueError('Invalid errors')
    return {'samples':len(error),'initial_m':float(error[0]),'mean_norm_m':float(error.mean()),'rmse_3d_m':float(np.sqrt(np.mean(error**2))),'median_norm_m':float(np.median(error)),'p95_norm_m':float(np.percentile(error,95)),'max_norm_m':float(error.max()),'max_index':int(np.argmax(error)),'terminal_m':float(error[-1]),'xyz_bias_m':np.mean(delta,axis=0).tolist(),'rac_bias_m':np.mean(rac,axis=0).tolist(),'rac_rmse_m':np.sqrt(np.mean(rac**2,axis=0)).tolist()}
