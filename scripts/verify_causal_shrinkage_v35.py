"""V35 CPU-only history and fixture verification. No future scoring or real future values."""
from dataclasses import replace
from datetime import datetime, timezone
import inspect
import io
import math
import resource
import time
import unittest
from unittest.mock import patch
import zipfile

import numpy as np

import stability_zg_v32 as frozen
from evaluation import causal_shrinkage_v35 as v35
from evaluation.causal_density_latitude import (
    apply_global, apply_latitude, assess_joint, fit_global_history, sample_sha,
)

ROOT = frozen.ROOT
OUT = frozen.E / 'thermosphere_causal_shrinkage_design_v35'
RTOL = 1e-13
BASE = '344e54787a50b016128b470f464d20f9ceddc896'


def parameter_path(day):
    if day == '2021-03-25':
        return frozen.SPRING21 / 'correction_parameters.json'
    if day == '2022-03-25':
        return frozen.V18 / 'correction_parameters.json'
    return frozen.V30 / f'{day[:4]}_parameters.json'


def bind(path, digest, day, hour, a):
    return v35.load_frozen_global(
        path, expected_sha256=digest, day=day, hour=hour, utc=a['utc'],
        latitude=a['latitude'], observed=a['density'], background=a['raw'], quality=a['quality'])


def fixture(hour=6, sign=1):
    day = '2021-03-25'
    cut = np.datetime64(f'{day}T{hour:02}:00', 'ns')
    utc = cut - np.timedelta64(3, 'h') + np.arange(360) * np.timedelta64(30, 's')
    model = np.linspace(1e-13, 8e-13, 360)
    latitude = np.linspace(-80, 80, 360)
    obs = model * np.exp(sign * 0.4)
    quality = np.ones(360, dtype=bool)
    fit, _ = fit_global_history(utc, latitude, obs, model, quality, day=day, hour=hour)
    identity = v35.FrozenGlobal(day, hour, fit['b'], fit['N'], '1'*64,
                                fit['sample_SHA256'], v35.utc_sha(utc))
    return identity, dict(utc=utc, raw=model, density=obs, latitude=latitude, quality=quality), fit


class Checks(unittest.TestCase):
    def setUp(self):
        self.fit, self.history, self.old = fixture()
        self.ids = np.datetime64('2021-03-25T06:00', 'ns') + np.arange(2)*np.timedelta64(30, 's')
        self.raw = np.array([1e-13, 2e-13])

    def panel(self, values=None, expected=None):
        return v35.apply_panel(self.fit, self.raw if values is None else values, self.ids,
                               expected_ids_sha256=expected or v35.utc_sha(self.ids))

    def test_raw(self):
        np.testing.assert_array_equal(self.panel()['predictions']['Raw'], self.raw)

    def test_global(self):
        np.testing.assert_array_equal(self.panel()['predictions']['Global'],
                                      apply_global(self.raw, self.old))

    def test_half_formula(self):
        self.assertEqual(self.panel()['parameters']['ShrinkageHalf']['multiplier'],
                         np.exp(self.old['b'] * 0.5))

    def test_positive_shrink(self):
        self.assertTrue(1 < v35.coefficient(self.fit, .5).multiplier < self.old['multiplier'])

    def test_negative_shrink(self):
        identity, _, old = fixture(sign=-1)
        self.assertTrue(old['multiplier'] < v35.coefficient(identity, .5).multiplier < 1)

    def test_invalid_lambda(self):
        for value in (-1, .25, 1.1, True, np.nan, np.inf, '0.5', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                v35.coefficient(self.fit, value)

    def test_nan_or_inf_history(self):
        for value in (np.nan, np.inf, -np.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                v35.coefficient(replace(self.fit, b=value), .5)

    def test_nonpositive_or_nonfinite_background(self):
        for value in (0, -1, np.nan, np.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.panel(np.array([value, 1e-13]))

    def test_unsupported_history_type(self):
        with self.assertRaises(ValueError):
            v35.coefficient(self.old, .5)

    def test_unsupported_parameter_receipt(self):
        import hashlib
        import json
        fake = json.dumps({'date': self.fit.day, 'parameters': {
            'GlobalAdaptive06': {'status': 'UNSUPPORTED_INSUFFICIENT_HISTORY'}}}).encode()
        with patch.object(v35.Path, 'read_bytes', return_value=fake):
            with self.assertRaisesRegex(ValueError, 'Supported original'):
                bind('unused', hashlib.sha256(fake).hexdigest(), self.fit.day, 6, self.history)

    def test_insufficient_N(self):
        with self.assertRaises(ValueError):
            v35.coefficient(replace(self.fit, n=29), .5)

    def test_parameter_SHA_changed(self):
        with patch.object(v35.Path, 'read_bytes', return_value=b'tampered'):
            with self.assertRaisesRegex(ValueError, 'SHA mismatch'):
                bind('unused', '0'*64, self.fit.day, 6, self.history)

    def reject_cutoff(self, hour):
        identity, data, _ = fixture(hour)
        data['utc'][-1] = np.datetime64(f'{identity.day}T{hour:02d}:00', 'ns')
        with patch.object(v35.Path, 'read_bytes', side_effect=AssertionError('premature read')):
            with self.assertRaisesRegex(ValueError, 'History crosses'):
                bind('unused', '0'*64, identity.day, hour, data)

    def test_06Z_right_edge(self):
        self.reject_cutoff(6)

    def test_18Z_right_edge(self):
        self.reject_cutoff(18)

    def test_06Z_rejects_18Z_history(self):
        _, afternoon, _ = fixture(18)
        with self.assertRaisesRegex(ValueError, 'History crosses'):
            bind('unused', '0'*64, self.fit.day, 6, afternoon)

    def test_invalid_quality(self):
        a = dict(self.history, quality=np.zeros(360, bool))
        with self.assertRaisesRegex(ValueError, 'Insufficient history'):
            bind('unused', '0'*64, self.fit.day, 6, a)

    def test_invalid_historical_density(self):
        a = dict(self.history, density=np.zeros(360))
        with self.assertRaisesRegex(ValueError, 'Invalid historical'):
            bind('unused', '0'*64, self.fit.day, 6, a)

    def test_fair_shared_ids(self):
        np.testing.assert_array_equal(self.ids, self.panel()['ids'])
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            self.panel(expected='0'*64)

    def test_duplicate_utc_rejected(self):
        self.ids[1] = self.ids[0]
        with self.assertRaisesRegex(ValueError, 'unique'):
            self.panel()

    def test_panel_outside_own_window(self):
        self.ids += np.timedelta64(6, 'h')
        with self.assertRaisesRegex(ValueError, 'outside'):
            self.panel()

    def test_future_labels_absent(self):
        signature = inspect.signature(v35.apply_panel)
        self.assertEqual(tuple(signature.parameters),
                         ('global_fit', 'background', 'ids', 'expected_ids_sha256'))
        with self.assertRaises(TypeError):
            v35.apply_panel(self.fit, self.raw, self.ids, expected_ids_sha256=v35.utc_sha(self.ids),
                            observed_future=self.raw)

    def test_candidates_cannot_be_tuned(self):
        with self.assertRaises(TypeError):
            v35.CANDIDATES['ShrinkageHalf'] = 0.75
        self.assertEqual(dict(v35.CANDIDATES), {'Raw': 0, 'ShrinkageHalf': 0.5, 'Global': 1})

    def test_holdout_rejected_before_io(self):
        for date in frozen.UNSEEN:
            with self.subTest(date=date), patch.object(v35.Path, 'read_bytes',
                                                       side_effect=AssertionError('unexpected read')):
                with self.assertRaisesRegex(ValueError, 'Unregistered'):
                    bind('unused', '0'*64, date, 6, self.history)
                with self.assertRaises(ValueError):
                    frozen.specification(date, 6)

    def test_unsupported_region_has_no_fallback(self):
        regions = {name: dict(self.old, status='UNSUPPORTED_INSUFFICIENT_HISTORY')
                   for name in ('low', 'mid', 'high')}
        adjusted, support = apply_latitude(self.raw, [10, 50], regions)
        self.assertTrue(np.isnan(adjusted).all())
        self.assertFalse(support.any())
        self.assertEqual(assess_joint({}, {}, regions, regions)['JOINT_NO_REGRET'],
                         'N/A_INSUFFICIENT_SAMPLES')

    def test_realtime_unverified(self):
        self.assertEqual(self.panel()['realtime_availability'], 'REALTIME_ASOF_UNVERIFIED')


def poison():
    checks = []
    for hour in (6, 18):
        identity, a, _ = fixture(hour)
        cut = np.datetime64(f'{identity.day}T{hour:02}:00', 'ns')
        utc = np.r_[a['utc'], cut, cut + np.timedelta64(30, 's')]
        model = np.r_[a['raw'], 5e-13, 8e-13]
        source = np.r_[a['density'], 1e-12, 2e-12]
        fits = []
        for factor in (1.0, 1e20):
            altered = source.copy()
            altered[utc >= cut] *= factor
            archive = io.BytesIO()
            np.savez_compressed(archive, utc=utc, density=altered)
            with zipfile.ZipFile(archive) as z:
                clock = frozen.read_member(z, 'utc', None)
                span = frozen.record_range(clock, identity.day, hour)
                observed = frozen.read_member(z, 'density', span)
            assert span == (0, 360)
            fitted, _ = fit_global_history(clock[slice(*span)], a['latitude'], observed,
                                            model[slice(*span)], a['quality'], day=identity.day, hour=hour)
            fit = replace(identity, b=fitted['b'], sample_sha256=fitted['sample_SHA256'])
            fits.append((fitted, [v35.coefficient(fit, x).multiplier for x in v35.CANDIDATES.values()]))
        assert fits[0] == fits[1]
        checks.append(dict(cutoff=hour, factor=1e20, bitwise_same_history_and_multipliers=True,
                           future_records_decoded=0, history_sample_SHA256=identity.sample_sha256))
    return checks


def verify_history(entry, parameter_sha):
    day, hour = entry['date'], entry['cutoff']
    path, a = frozen.read_history(day, hour)
    assert path == ROOT / entry['path']
    q = a['quality']
    t, lat, o, p = (a[k][q] for k in ('utc', 'latitude', 'density', 'raw'))
    sample = sample_sha(t, lat, o, p)
    assert sample == entry['sample_SHA256']
    key = f'{day}/{hour:02}'
    result = dict(key=key, source=entry['path'], source_SHA256=entry['SHA256'], N=len(t),
                  history_sample_SHA256=sample, history_UTC_SHA256=v35.utc_sha(t),
                  start=str(t[0])+'Z', last=str(t[-1])+'Z', original_global=parameter_sha is not None)
    if parameter_sha is None:
        return result
    identity = bind(parameter_path(day), parameter_sha, day, hour, a)
    # Freeze the original log primitive; use independent order statistics and scalar exp.
    residual = sorted((np.log(o) - np.log(p)).tolist())
    middle = len(residual)//2
    b = (residual[middle-1] + residual[middle])*0.5
    exploratory = sorted(math.log(float(y)) - math.log(float(x)) for y, x in zip(o, p, strict=True))
    alternate = (exploratory[middle-1] + exploratory[middle])*0.5
    np.testing.assert_allclose(identity.b, b, rtol=RTOL, atol=0)
    probe = np.array([1e-13, 3e-13, 8e-13])
    candidates = []
    for shrinkage in (0, .5, 1):
        trial = v35.coefficient(identity, shrinkage)
        scalar = b*shrinkage
        multiplier = math.exp(scalar)
        np.testing.assert_allclose([trial.log_bias, trial.multiplier], [scalar, multiplier],
                                   rtol=RTOL, atol=0)
        assert trial.multiplier == float(np.exp(shrinkage*identity.b))
        np.testing.assert_allclose(trial.apply(probe), [x*multiplier for x in probe], rtol=RTOL, atol=0)
        if shrinkage == 1:
            np.testing.assert_array_equal(trial.apply(probe),
                                          apply_global(probe, frozen.coefficient_reference(day, hour)))
        elif shrinkage == 0:
            np.testing.assert_array_equal(trial.apply(probe), probe)
        candidates.append(dict(lambda_=shrinkage, b_shrink=trial.log_bias,
                               multiplier=trial.multiplier, scalar_multiplier=multiplier))
    return dict(result, original_b=identity.b, independently_reconstructed_b=b,
                alternate_scalar_log_b=alternate, alternate_absolute_difference=abs(alternate-b),
                global_parameter_path=str(parameter_path(day).relative_to(ROOT)),
                global_parameter_SHA256=parameter_sha, candidate_math=candidates)


def main():
    wall = time.perf_counter()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Checks)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    poison_checks = poison()
    receipt = frozen.load(frozen.OUT/'history_freeze.json')
    roles = frozen.load(frozen.OUT/'data_roles.json')
    assert {r['date'] for r in roles['dates'] if r['role'] == 'DEVELOPMENT_SOURCE'} == v35.DEVELOPMENT_DATES
    pins = {}
    windows = []
    for entry in receipt['history_caches']:
        path = ROOT / entry['path']
        if entry['path'] not in pins:
            pins[entry['path']] = frozen.sha(path)
        assert pins[entry['path']] == entry['SHA256']
        day = entry['date']
        if day in frozen.MAIN_DAYS:
            param = parameter_path(day)
            param_sha = frozen.baseline(param)
        else:
            param_sha = None
        windows.append(verify_history(entry, param_sha))
    assert len(windows) == 16 and sum(w['original_global'] for w in windows) == 8
    frozen.write_once(OUT/'verification.json', dict(
        UTC=datetime.now(timezone.utc).isoformat(), numpy=np.__version__,
        fixture_tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        poison=poison_checks, independent_rtol=RTOL, independent_atol=0, windows=windows,
        real_future_values_decoded=0, scores=0, wall_seconds=time.perf_counter()-wall,
        peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))


if __name__ == '__main__':
    main()
