"""New read-only audit guards; no repetition of model qualification tests."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np
from netCDF4 import Dataset

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('divergence', ROOT/'scripts/analyze_tiegcm_restart_divergence.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ClockAndValidityTests(unittest.TestCase):
    def make_clock(self, directory, name, units, value):
        path = Path(directory)/name
        with Dataset(path, 'w') as n:
            n.createDimension('time', 1); n.createDimension('three', 3)
            n.createVariable('year', 'i4', ('time',))[:] = [2021]
            n.createVariable('mtime', 'i4', ('time', 'three'))[:] = [[82, 0, 10]]
            t = n.createVariable('time', 'f8', ('time',)); t.units = units; t[:] = [value]
        return path

    def test_equivalent_different_cf_origins(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.tmp') as d:
            a = self.make_clock(d, 'a.nc', 'minutes since 2021-03-23 00:00:00', 10)
            b = self.make_clock(d, 'b.nc', 'minutes since 2021-03-22 00:00:00', 1450)
            with Dataset(a) as x, Dataset(b) as y:
                self.assertEqual(audit.utc_record(x, 0), audit.utc_record(y, 0))

    def test_false_calendar_label_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.tmp') as d:
            p = self.make_clock(d, 'bad.nc', 'minutes since 2002-03-23 00:00:00', 10)
            with Dataset(p) as n, self.assertRaisesRegex(ValueError, 'clock mismatch'):
                audit.utc_record(n, 0)

    def test_mask_difference_cannot_hide_as_exact(self):
        x = np.array([1., 2.]); m = np.array([False, False]); other = np.array([False, True])
        r = audit.metrics(x, x, m, other, dict(scale_to_SI=1., atol_SI=1e-8, rtol=1e-10))
        self.assertFalse(r['passed']); self.assertFalse(r['exact']); self.assertEqual(r['mask_mismatch'], 1)

    def test_nonfinite_not_hidden_by_mask(self):
        x = np.array([1., np.nan]); m = np.array([False, True])
        with self.assertRaisesRegex(ValueError, 'Nonfinite'):
            audit.metrics(x, x, m, m, dict(scale_to_SI=1., atol_SI=1e-8, rtol=1e-10))


if __name__ == '__main__':
    unittest.main()
