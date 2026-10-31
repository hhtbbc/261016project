"""Stop RK45 at known discontinuities and carry the identical six-state.

No force equations or existing RK45 implementation are changed. rhs_factory(i)
must bind the atmosphere for segment i, including BOTH endpoint evaluations.
The caller must not use a globally right-continuous density inside a left
segment endpoint. A failed query/RHS aborts; there is no restart/retry policy.
"""
from dataclasses import dataclass
import numpy as np
from .rk45_propagator import propagate


@dataclass
class EventPropagation:
    times_s: np.ndarray
    states: np.ndarray
    segments: list
    event_records: list


def propagate_event_segments(rhs_factory, position_m, velocity_m_s, t_span,
                             output_times_s, event_times_s, **kwargs):
    start, stop = map(float, t_span)
    events = np.asarray(event_times_s, float)
    times = np.asarray(output_times_s, float)
    if (events.ndim != 1 or not np.isfinite(events).all()
            or np.any(np.diff(events) <= 0)
            or np.any(events <= start) or np.any(events >= stop)):
        raise ValueError('Events must be strictly internal and increasing')
    if (not times.size or times.ndim != 1 or not np.isfinite(times).all()
            or np.any(np.diff(times) <= 0) or times[0] < start or times[-1] > stop):
        raise ValueError('Output times must be ordered within integration span')
    bounds = np.r_[start, events, stop]
    state = np.r_[position_m, velocity_m_s].astype(float)
    segments = []; records = []; output = np.empty((len(times), 6))
    for i, (a, b) in enumerate(zip(bounds[:-1], bounds[1:])):
        rhs = rhs_factory(i)
        def bounded_rhs(t, y):
            if t < a or t > b:
                raise ValueError('RHS evaluated outside bound segment')
            return rhs(t, y)
        initial = state.copy()
        seg = propagate(bounded_rhs, state[:3], state[3:], (a, b), [a, b], **kwargs)
        np.testing.assert_array_equal(seg.states[0], initial)
        if i:
            records.append(dict(time_s=float(a), position_jump_m=float(np.linalg.norm(
                seg.states[0,:3]-segments[-1].states[-1,:3])),
                velocity_jump_m_s=float(np.linalg.norm(seg.states[0,3:]-segments[-1].states[-1,3:])),
                acceleration_left=np.asarray(rhs_factory(i-1)(a, initial),float)[3:].tolist(),
                acceleration_right=np.asarray(rhs(a, initial),float)[3:].tolist()))
        selected = (times >= a) & ((times < b) if i < len(bounds)-2 else (times <= b))
        output[selected] = seg.dense_solution(times[selected]).T
        state = seg.states[-1].copy(); segments.append(seg)
    return EventPropagation(times, output, segments, records)
