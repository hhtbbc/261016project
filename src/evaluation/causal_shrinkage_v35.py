"""Fixed scalar mechanism contrast for development-only, provisional Map-A hindcasts."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from types import MappingProxyType

import numpy as np

from .causal_density_latitude import sample_sha
from .late_day_correction import RollingOrigin
from .swarm_crossyear import MIN_SAMPLES
from atmosphere.causal_density_correction import LogMedianCorrection


CANDIDATES = MappingProxyType({'Raw': 0.0, 'ShrinkageHalf': 0.5, 'Global': 1.0})
DEVELOPMENT_DATES = frozenset(
    f'{year}-{day}' for year in (2021, 2022) for day in ('03-23', '03-24', '03-25', '09-23')
)
HINDCAST = 'HINDCAST_HISTORY_AVAILABLE'
REALTIME = 'REALTIME_ASOF_UNVERIFIED'


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def _origin(day, hour):
    if day not in DEVELOPMENT_DATES or type(hour) is not int or hour not in (6, 18):
        raise ValueError('Unregistered development date or cutoff')
    return RollingOrigin(day, hour)


def _utc(ids):
    t = np.asarray(ids)
    if t.dtype != np.dtype('datetime64[ns]') or t.ndim != 1 or not len(t):
        raise ValueError('Nonempty decoded UTC nanosecond IDs required')
    if np.isnat(t).any() or np.any(t[1:] <= t[:-1]):
        raise ValueError('UTC IDs must be finite, unique and strictly sorted')
    return t


def utc_sha(ids):
    return _digest(_utc(ids).astype('<i8').tobytes())


@dataclass(frozen=True)
class FrozenGlobal:
    day: str
    hour: int
    b: float
    n: int
    source_sha256: str
    sample_sha256: str
    utc_sha256: str


def load_frozen_global(path, *, expected_sha256, day, hour, utc,
                       latitude, observed, background, quality):
    """Bind a trusted file pin to a supported original Global and its exact historical inputs."""
    origin = _origin(day, hour)
    t = _utc(utc)
    if not origin.masks(t)['analysis'].all():
        raise ValueError('History crosses its three-hour, left-closed right-open window')
    q = np.asarray(quality)
    if q.dtype != np.dtype(bool) or q.shape != t.shape:
        raise ValueError('Aligned frozen quality mask required')
    if np.count_nonzero(q) < MIN_SAMPLES:
        raise ValueError('Insufficient history')
    lat, o, p = (np.asarray(x, dtype=float) for x in (latitude, observed, background))
    if any(x.shape != t.shape or not np.isfinite(x[q]).all() for x in (lat, o, p)):
        raise ValueError('Invalid historical inputs')
    if np.any(abs(lat[q]) > 90) or np.any(o[q] <= 0) or np.any(p[q] <= 0):
        raise ValueError('Invalid historical coordinate or density')
    contents = Path(path).read_bytes()
    if _digest(contents) != expected_sha256:
        raise ValueError('Original Global parameter SHA mismatch')
    params = json.loads(contents)
    if params.get('date') != day:
        raise ValueError('Original Global date mismatch')
    methods = params.get('parameters', {})
    fit = methods.get('B14', methods).get(f'GlobalAdaptive{hour:02d}', {})
    if fit.get('status') != 'SUPPORTED':
        raise ValueError('Supported original Global history required')
    n = fit.get('N')
    b = fit.get('b')
    if type(n) is not int or n != np.count_nonzero(q) or type(b) not in (float, int) or not np.isfinite(b):
        raise ValueError('Invalid Global support or coefficient')
    samples = sample_sha(t[q], lat[q], o[q], p[q])
    if (samples != fit.get('sample_SHA256')
            or str(t[q][0]) + 'Z' != fit.get('first_UTC')
            or str(t[q][-1]) + 'Z' != fit.get('last_UTC')):
        raise ValueError('Original Global history identity mismatch')
    if LogMedianCorrection(b, n).multiplier != fit.get('multiplier'):
        raise ValueError('Original Global multiplier mismatch')
    return FrozenGlobal(day, hour, b, n, expected_sha256, samples, utc_sha(t[q]))


def coefficient(global_fit, shrinkage):
    """Produce only preregistered contrasts. No outcome-dependent selection interface."""
    if type(shrinkage) not in (int, float) or shrinkage not in CANDIDATES.values():
        raise ValueError('Unregistered lambda')
    if type(global_fit) is not FrozenGlobal:
        raise ValueError('Frozen Global receipt required')
    origin = _origin(global_fit.day, global_fit.hour)
    if (type(global_fit.n) is not int or global_fit.n < MIN_SAMPLES
            or type(global_fit.b) not in (float, int) or not np.isfinite(global_fit.b)
            or any(not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value)
                   for value in (global_fit.source_sha256, global_fit.sample_sha256,
                                 global_fit.utc_sha256))):
        raise ValueError('Invalid frozen Global identity')
    return LogMedianCorrection(shrinkage * global_fit.b, global_fit.n, cutoff_UTC=origin.cutoff)


def apply_panel(global_fit, background, ids, *, expected_ids_sha256):
    """Use one ordered shared ID/background array. Observed outcomes are absent from this API."""
    ids = _utc(ids)
    first = coefficient(global_fit, 0)
    if not _origin(global_fit.day, global_fit.hour).masks(ids)['future_6h'].all():
        raise ValueError('Panel outside registered six-hour development window')
    p = np.asarray(background, dtype=float)
    if p.shape != ids.shape or utc_sha(ids) != expected_ids_sha256:
        raise ValueError('Shared sample identity mismatch')
    predictions = {}
    parameters = {}
    for name, shrinkage in CANDIDATES.items():
        fit = coefficient(global_fit, shrinkage)
        predictions[name] = fit.apply(p)
        parameters[name] = {'lambda': shrinkage, 'b_shrink': fit.log_bias,
                            'multiplier': fit.multiplier}
    return dict(ids=ids.copy(), predictions=predictions, parameters=parameters,
                day=global_fit.day, cutoff_UTC=first.cutoff_UTC,
                data_role='DEVELOPMENT_SOURCE', history_availability=HINDCAST,
                realtime_availability=REALTIME, geometry='PROVISIONAL Map-A',
                global_parameter_SHA256=global_fit.source_sha256,
                history_sample_SHA256=global_fit.sample_sha256,
                history_UTC_SHA256=global_fit.utc_sha256,
                parameter_code_SHA256=_digest(Path(__file__).read_bytes()))
