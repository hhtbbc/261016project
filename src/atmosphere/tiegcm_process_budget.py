"""Fail-closed prerequisites and arithmetic for native-mmr process budgets.

No model launcher. Missing process measurements never imply a zero contribution.
The proposed closure thresholds require solver/instrumentation qualification.
"""
import numpy as np

TERMS=('chemistry_production','chemistry_loss','horizontal_advection',
       'vertical_transport','molecular_diffusion','vertical_eddy_diffusion',
       'horizontal_diffusion','boundary','time_level_memory_bridge',
       'previous_state_spatial_filter','spatial_filter','time_filter','clipping_normalization')
CLOSURE_ATOL_MMR=1e-12
CLOSURE_RTOL=1e-10

def require_ready(*,structure_complete,runtime_restore_verified,process_capture_verified,closure_protocol_qualified):
    reasons=[name for name,value in locals().copy().items() if not value]
    if reasons:raise ValueError('PROCESS_BUDGET_BLOCKED: '+', '.join(reasons))

def n2_contribution(o1,o2,he):
    """Derived bookkeeping only, not an independent nitrogen chemistry equation."""
    return -(np.asarray(o1)+np.asarray(o2)+np.asarray(he))

def check_closure(delta,contributions,valid=None):
    missing=[k for k in TERMS if k not in contributions or contributions[k] is None]
    if missing:return {'status':'NOT_EVALUABLE','missing_terms':missing,'residual':None,'passed':False}
    delta=np.asarray(delta,dtype=np.float64)
    arrays=[np.asarray(contributions[k],dtype=np.float64) for k in TERMS]
    if any(a.shape!=delta.shape for a in arrays):raise ValueError('Shape mismatch')
    mask=np.ones(delta.shape,bool) if valid is None else np.asarray(valid,dtype=bool)
    if mask.shape!=delta.shape or not mask.any():raise ValueError('Invalid mask')
    if any(not np.isfinite(a[mask]).all() for a in [delta]+arrays):raise ValueError('Nonfinite budget')
    total=np.sum(arrays,axis=0);residual=delta-total
    scale=np.maximum(abs(delta),np.sum([abs(a) for a in arrays],axis=0))
    limit=CLOSURE_ATOL_MMR+CLOSURE_RTOL*scale
    return {'status':'SYNTHETIC_OR_QUALIFIED_INPUT_ARITHMETIC_ONLY',
            'residual':residual,'passed':bool(np.all(abs(residual[mask])<=limit[mask])),
            'max_absolute_residual':float(abs(residual[mask]).max())}
