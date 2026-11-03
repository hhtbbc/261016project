"""DOP853 adapter using the existing event-sequencing function unmodified.

An isolated globals binding substitutes only its segment solver. The original
module/function/global dictionary are never mutated; H6 and density stay intact.
"""
import types,time
import numpy as np
from scipy.integrate import solve_ivp
from .rk45_propagator import Propagation
from . import event_segments

def dop853_segment(rhs,position_m,velocity_m_s,t_span,output_times_s,*,rtol,atol,max_step):
    initial=np.r_[position_m,velocity_m_s].astype(float);times=np.asarray(output_times_s,float);lo,hi=map(float,t_span)
    if initial.shape!=(6,) or not np.isfinite(initial).all() or not lo<hi:raise ValueError('Finite6D forward span required')
    if times.ndim!=1 or not times.size or np.any(np.diff(times)<=0) or times[0]<lo or times[-1]>hi:raise ValueError('Output times outside ordered span')
    tolerance=np.asarray(atol,float)
    if tolerance.shape!=(6,) or not np.isfinite(tolerance).all() or np.any(tolerance<=0) or not 0<rtol or not 0<max_step:raise ValueError('Invalid solver controls')
    begin=time.perf_counter();sol=solve_ivp(rhs,(lo,hi),initial,method='DOP853',rtol=rtol,atol=tolerance,max_step=max_step,dense_output=True)
    if not sol.success or sol.status!=0 or sol.t[-1]!=hi:raise RuntimeError('DOP853 did not reach endpoint: '+sol.message)
    states=sol.sol(times).T
    if not np.isfinite(states).all():raise RuntimeError('Nonfinite state')
    return Propagation(times,states,sol.t,dict(method='DOP853',rtol=rtol,atol=tolerance.tolist(),max_step_s=max_step,nfev=sol.nfev,accepted_steps=len(sol.t)-1,min_accepted_step_s=float(np.diff(sol.t).min()),max_accepted_step_s=float(np.diff(sol.t).max()),elapsed_s=time.perf_counter()-begin,success=True),sol.sol)

def propagate_dop853_events(*args,**kwargs):
    original=event_segments.propagate_event_segments
    namespace=dict(original.__globals__);namespace['propagate']=dop853_segment
    isolated=types.FunctionType(original.__code__,namespace,original.__name__,original.__defaults__,original.__closure__)
    return isolated(*args,**kwargs)
