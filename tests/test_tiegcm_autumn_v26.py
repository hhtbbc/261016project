"""CPU-only acceptance tests, using temporary fixtures and read-only original headers."""
import ast
import datetime as dt
import importlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_tiegcm_autumn_v26 import (
    BASE, FIRST, OLD_FAIL, OUT, RUN, RUN_ID, START, audit_directory, binding,
    expected_inventory, frozen, load, metadata, source_identity, validate_record, write_once,
)
from tiegcm_autumn_v26_sha import scan, stream_sha
from netCDF4 import Dataset
import numpy as np


class AcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = load(BASE / 'launch_protocol.json')
        with Dataset(RUN / FIRST, 'r') as cold:
            cls.cold = metadata(cold, 0)
        with Dataset(RUN / 'primary_002.nc', 'r') as warm:
            cls.warm = metadata(warm, 0)

    def new_directory(self):
        folder = tempfile.TemporaryDirectory(dir=OUT)
        self.addCleanup(folder.cleanup)
        return Path(folder.name)

    def cold_check(self, **changed):
        return validate_record(dict(self.cold, **changed), 'primary', FIRST, 0, START, 115200)

    def warm_check(self, **changed):
        return validate_record(dict(self.warm, **changed), 'primary', 'primary_002.nc',
                               0, START + dt.timedelta(days=1), 115200)

    def test_real_cold_echo(self):
        self.assertEqual(self.cold['run_type'], '')
        self.assertTrue(self.cold_check())

    def test_warm_empty(self):
        with self.assertRaisesRegex(ValueError, 'Warm run_type'):
            self.warm_check(run_type='')

    def test_wrong_position(self):
        with self.assertRaisesRegex(ValueError, 'Warm run_type'):
            validate_record(self.cold, 'primary', 'primary_002.nc', 0, START, 115200)

    def test_forged_source(self):
        with Dataset(ROOT / self.protocol['source']['path'], 'r') as seed:
            with self.assertRaisesRegex(ValueError, 'SOURCE'):
                source_identity(seed, {'SOURCE': "'fake'", 'SOURCE_START': '80 0 0'},
                                self.protocol['source']['path'])
        with self.assertRaisesRegex(ValueError, 'Changed original asset'):
            binding(ROOT / self.protocol['source']['path'], '0' * 64)

    def test_wrong_source_start(self):
        path = self.protocol['source']['path']
        with Dataset(ROOT / path, 'r') as seed:
            with self.assertRaisesRegex(ValueError, 'SOURCE_START'):
                source_identity(seed, {'SOURCE': f"'$PROJECTROOT/{path}'",
                                       'SOURCE_START': '80 0 1'}, path)

    def test_wrong_initial_utc(self):
        with self.assertRaisesRegex(ValueError, 'Unexpected UTC'):
            self.cold_check(utc=START + dt.timedelta(minutes=1))

    def test_wrong_cold_iter(self):
        with self.assertRaisesRegex(ValueError, 'inherited iter'):
            self.cold_check(iter=362880)

    def test_wrong_warm_iter(self):
        with self.assertRaisesRegex(ValueError, 'Warm iter'):
            self.warm_check(iter=115200)

    def test_rank_exit_nonzero(self):
        folder = self.new_directory()
        for original in sorted(RUN.glob('rank_*.json')) + [RUN / 'status.json']:
            data = load(original)
            if original.name == 'rank_002_exit.json':
                data['returncode'] = 1
            write_once(folder / original.name, data)
        with self.assertRaisesRegex(ValueError, 'did not exit normally'):
            frozen.validate_exits(folder, RUN_ID, self.protocol)

    def test_rank_missing(self):
        with self.assertRaisesRegex(ValueError, 'Four rank'):
            frozen.validate_exits(self.new_directory(), RUN_ID, self.protocol)

    def test_missing_primary_state(self):
        with self.assertRaisesRegex(RuntimeError, 'Missing/non-double primary state'):
            frozen.prognostics(type('Missing', (), {'history_type': 'primary', 'variables': {}})())

    def test_wrong_native_calendar(self):
        for changed in ({'year': 2002}, {'day': 80}, {'mtime': [252, 1, 0]}):
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, 'CF/native'):
                self.cold_check(**changed)

    def test_missing_time_attribute_even_with_global_decoy(self):
        path = self.new_directory() / 'metadata.nc'
        with Dataset(path, 'w', format='NETCDF3_CLASSIC') as n:
            n.createDimension('time', 1)
            v = n.createVariable('time', 'i4', ('time',))
            v.initial_day = 252
            v.initial_mtime = [252, 0, 0]
            v.units = self.cold['units']
            n.initial_year = 2021
        with Dataset(path, 'r') as n:
            with self.assertRaisesRegex(ValueError, 'time-variable attributes.*initial_year'):
                metadata(n, 0)

    def assert_invalid_field(self, density, height, reason):
        path = self.new_directory() / 'native.nc'
        with Dataset(path, 'w', format='NETCDF3_CLASSIC') as n:
            dims = ('time', 'ilev', 'lat', 'lon')
            for k, size in zip(dims, (1, 2, 1, 1)):
                n.createDimension(k, size)
            for name, values, unit in [('DEN', density, 'g/cm3'), ('ZG', height, 'cm')]:
                variable = n.createVariable(name, 'f8', dims, fill_value=1e35)
                variable.units = unit
                variable[0, :, 0, 0] = values
        with Dataset(path, 'r') as n:
            with self.assertRaisesRegex(ValueError, reason):
                frozen.inspect_density_record(n, 0)

    def test_real_netcdf_nan(self):
        self.assert_invalid_field([np.nan, 1], [1, 2], 'Invalid warm DEN')

    def test_real_netcdf_inf(self):
        self.assert_invalid_field([1, 2], [1, np.inf], 'Invalid warm ZG')

    def test_nonpositive_density(self):
        self.assert_invalid_field([0, 1], [1, 2], 'Nonpositive DEN')

    def test_illegal_fill(self):
        self.assert_invalid_field([1e35, 1], [1, 2], 'Invalid warm DEN')

    def test_nonmonotonic_zg(self):
        self.assert_invalid_field([1, 2], [2, 1], 'ZG nonmonotonic')

    def test_gpi_sha(self):
        item = self.protocol['GPI']
        binding(ROOT / item['path'], item['SHA256'])
        with self.assertRaisesRegex(ValueError, 'Changed original asset'):
            binding(ROOT / item['path'], '0' * 64)

    def test_missing_volume(self):
        entry = dict(file=FIRST, SHA256='0' * 64, bytes='1')
        result = scan(self.new_directory(), [entry], 1)
        self.assertFalse(result['V24_33_NETCDF_SHA_VERIFIED'])
        self.assertEqual(result['missing'], [FIRST])

    def test_changed_volume(self):
        folder = self.new_directory()
        (folder / FIRST).write_bytes(b'x')
        entry = dict(file=FIRST, SHA256='0' * 64, bytes='1')
        self.assertFalse(scan(folder, [entry], 1)['V24_33_NETCDF_SHA_VERIFIED'])

    def test_duplicate_time(self):
        with self.assertRaisesRegex(ValueError, 'Unexpected UTC'):
            self.warm_check(utc=START)

    def test_time_gap(self):
        with self.assertRaisesRegex(ValueError, 'Unexpected UTC'):
            self.warm_check(utc=START + dt.timedelta(days=2))

    def test_csv_inventory_numbers_are_integers(self):
        row = dict(file=FIRST, SHA256='f' * 64, bytes='17', records='1',
                   first_UTC='2021-09-09T00:00:00Z', last_UTC='2021-09-09T00:00:00Z')
        self.assertEqual(expected_inventory([row])[FIRST],
                         ('f' * 64, 17, 1, row['first_UTC'], row['last_UTC']))

    def test_no_launch_api(self):
        script = ROOT / 'scripts/audit_tiegcm_autumn_v26.py'
        tree = ast.parse(script.read_text())
        identifiers = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        self.assertFalse((identifiers | attributes) & {'execute', 'supervise', 'Popen', 'system', 'mpirun'})
        with patch('subprocess.Popen', side_effect=AssertionError('Process creation prohibited')):
            importlib.reload(sys.modules['audit_tiegcm_autumn_v26'])
            binding(RUN / 'input.inp', self.protocol['input']['SHA256'])

    def test_old_fail_cannot_be_audit_destination(self):
        before = stream_sha(OLD_FAIL)
        with self.assertRaisesRegex(ValueError, 'Wrong audit destination'):
            audit_directory(OLD_FAIL.parent)
        self.assertEqual(stream_sha(OLD_FAIL), before)

    def test_concurrent_directory_claim(self):
        path = OUT / '__test_exclusive_claim'
        def claim(_):
            try:
                audit_directory(path)
                return True
            except FileExistsError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(claim, range(2))), [False, True])
        path.rmdir()


if __name__ == '__main__':
    unittest.main()
