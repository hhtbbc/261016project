"""Force-independent RK45 propagation with separate internal and output grids."""
from dataclasses import dataclass
import time
import numpy as np
from scipy.integrate import solve_ivp

@dataclass
class Propagation:
    times_s: np.ndarray
    states: np.ndarray
    internal_times_s: np.ndarray
    statistics: dict
    dense_solution: object


def propagate(rhs, position_m, velocity_m_s, t_span, output_times_s,
              rtol=1e-10, atol=(1e-3, 1e-3, 1e-3, 1e-6, 1e-6, 1e-6), max_step=30.):
    y0 = np.concatenate((np.asarray(position_m, float), np.asarray(velocity_m_s, float)))
    times = np.asarray(output_times_s, float)
    span = np.asarray(t_span, float)
    tolerance = np.asarray(atol, float)
    if y0.shape != (6,) or not np.isfinite(y0).all():
        raise ValueError('Invalid initial state')
    if span.shape != (2,) or not np.isfinite(span).all() or span[1] <= span[0]:
        raise ValueError('Forward finite time span required')
    if times.ndim != 1 or not times.size or not np.isfinite(times).all() or np.any(np.diff(times) <= 0) or times[0] < span[0] or times[-1] > span[1]:
        raise ValueError('Output grid outside span or not increasing')
    if tolerance.shape != (6,) or not np.isfinite(tolerance).all() or np.any(tolerance <= 0) or not np.isfinite(rtol) or rtol <= 0 or not np.isfinite(max_step) or max_step <= 0:
        raise ValueError('Invalid integration tolerances or maximum step')
    started = time.perf_counter()
    solution = solve_ivp(rhs, span, y0, method='RK45', rtol=rtol, atol=tolerance,
                         max_step=max_step, dense_output=True)
    elapsed = time.perf_counter()-started
    if not solution.success or solution.status != 0 or solution.t[-1] != span[1]:
        raise RuntimeError(f'Integration did not reach end: {solution.message}')
    states = solution.sol(times).T
    if not np.isfinite(states).all():
        raise RuntimeError('Nonfinite integrated state')
    return Propagation(times, states, solution.t, {
        'method':'RK45', 'rtol':rtol, 'atol_si':tolerance.tolist(), 'max_step_s':max_step,
        'accepted_steps':len(solution.t)-1, 'nfev':solution.nfev, 'elapsed_s':elapsed,
        'output_samples':len(times), 'success':solution.success, 'message':solution.message,
        'min_accepted_step_s':float(np.diff(solution.t).min()),
        'max_accepted_step_s':float(np.diff(solution.t).max())}, solution.sol)
