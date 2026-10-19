"""Strict TIE-GCM restart preconditions and SI comparison primitives."""
from pathlib import Path
import numpy as np
from netCDF4 import Dataset

CURRENT=('TN','UN','VN','O2','O1','N4S','NO','HE','AR','OP','N2D','TI','TE','NE','O2P','OMEGA','Z','POTEN')
PREVIOUS=tuple(x+'_NM' for x in ('TN','UN','VN','O2','O1','N4S','NO','OP','HE','AR'))
LOWER=('TLBC','ULBC','VLBC','TLBC_NM','ULBC_NM','VLBC_NM')
REQUIRED=CURRENT+PREVIOUS+LOWER

def check_source_clock(start,source_start):
    """Original input.F requires matching hour/minute, independent of day."""
    if len(start)!=3 or len(source_start)!=3:raise ValueError('Need day/hour/minute')
    if tuple(start[1:])!=tuple(source_start[1:]):
        raise ValueError('START hour/minute must equal SOURCE_START (input.F:948-960)')

def inspect_restart(path,source_start):
    path=Path(path)
    with Dataset(path) as n:
        missing=[v for v in REQUIRED if v not in n.variables]
        records=np.asarray(n['mtime'][:]).astype(int) if 'mtime' in n.variables else np.empty((0,3),int)
        hits=np.flatnonzero((records==source_start).all(axis=1))
        result={'file':str(path),'history_type':getattr(n,'history_type',None),
                'missing_required':missing,'selected_record_count':len(hits),
                'available_mtime':records.tolist(),
                'all_required_double':not missing and all(n[v].dtype==np.dtype('float64') for v in REQUIRED)}
        result['structure_complete']=not missing and result['all_required_double'] and result['history_type']=='primary'
        result['record_available']=len(hits)==1
        # Structure alone is not proof of valid state or numerical continuation.
        result['validated_continuation']=False
        return result

def compare_arrays(reference,candidate,reference_mask=None,candidate_mask=None,*,atol,rtol,scale=1.):
    """Same-time arrays only; caller must separately prove epoch/grid/unit match.

    No nonfinite value is silently accepted. Reference zeroes are excluded from
    relative maxima and counted; absolute/allclose metrics still include them.
    """
    a=np.asarray(reference,dtype=float)*scale;b=np.asarray(candidate,dtype=float)*scale
    if a.shape!=b.shape:raise ValueError('Shape mismatch')
    ma=np.zeros(a.shape,bool) if reference_mask is None else np.asarray(reference_mask,bool)
    mb=np.zeros(a.shape,bool) if candidate_mask is None else np.asarray(candidate_mask,bool)
    if ma.shape!=a.shape or mb.shape!=b.shape:raise ValueError('Mask shape mismatch')
    nf_a=~np.isfinite(a);nf_b=~np.isfinite(b)
    valid=~(ma|mb|nf_a|nf_b)
    if not valid.any():raise ValueError('No common valid values')
    aa=a[valid];bb=b[valid];delta=bb-aa;nonzero=aa!=0
    limit=atol+rtol*np.maximum(abs(aa),abs(bb))
    normalized=np.divide(abs(delta),limit,out=np.where(delta==0,0.,np.inf),where=limit>0)
    return {'shape':list(a.shape),'total':a.size,'common_valid':int(valid.sum()),
            'valid_fraction':float(valid.mean()),'mask_mismatch_count':int((ma!=mb).sum()),
            'reference_nonfinite':int(nf_a.sum()),'candidate_nonfinite':int(nf_b.sum()),
            'relative_zero_reference_count':int((~nonzero).sum()),
            'max_absolute_error':float(abs(delta).max()),'rmse':float(np.sqrt(np.mean(delta**2))),
            'max_relative_error':float(np.max(abs(delta[nonzero]/aa[nonzero]))) if nonzero.any() else None,
            'max_normalized_error':float(normalized.max()),
            'passed':bool((normalized<=1).all() and not (ma!=mb).any() and not nf_a.any() and not nf_b.any())}
