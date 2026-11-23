"""CPU-only V27 tests. Any model launch during these tests is a failure."""
import ast
from contextlib import nullcontext
from copy import deepcopy
import datetime as dt
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import execute_tiegcm_autumn_2022_v27 as launch
import audit_tiegcm_autumn_2022_v27 as audit
from netCDF4 import Dataset
from tests.test_tiegcm_autumn_v26 import AcceptanceTests as V26Tests


class V27Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = launch.preflight()
        cls.evidence = [
            launch.load(launch.V26 / item) for item in (
                'closure_release.json', 'independent_recovery_once/result.json',
                'formal_once/main_acceptance.json', 'independent_recovery_once/independent_review.json',
                'sha_verification.json',
            )
        ] + [launch.load(launch.V24 / 'result_final.json'), launch.load(launch.OLD_FAIL),
             launch.manifest_rows()]

    def scratch(self):
        work = tempfile.TemporaryDirectory(dir=ROOT / '.tmp')
        self.addCleanup(work.cleanup)
        return Path(work.name)

    def test_unauthorized_does_not_validate_reserve_or_spawn(self):
        with patch.object(launch, 'execution_lock') as lock, patch.object(launch, 'verify_plan') as plan, patch.object(launch, 'supervise') as start:
            with self.assertRaisesRegex(ValueError, 'authorization'):
                launch.execute(2022)
            for tool in (lock, plan, start):
                tool.assert_not_called()

    def test_unconfirmed_cpu_session(self):
        with self.assertRaisesRegex(ValueError, 'sustained supervision'):
            launch.execute(2022, True)

    def test_wrong_year(self):
        with self.assertRaisesRegex(ValueError, 'Only 2022'):
            launch.execute(2021, True, True)

    def test_v26_complete(self):
        launch.verify_v26_fields(*self.evidence)

    def test_v26_sha_changed(self):
        pins = {launch.V26 / 'formal_once/main_acceptance.json': '0'*64}
        with patch.object(launch, 'FIXED_PINS', pins), self.assertRaisesRegex(ValueError, 'Changed original asset'):
            launch.verify_v26()

    def test_missing_closure_and_only_v24_fail(self):
        with patch.object(launch, 'V26', self.scratch()), self.assertRaises(FileNotFoundError):
            launch.verify_v26()
        self.assertEqual(launch.load(launch.OLD_FAIL)['overall'], 'FAIL')

    def test_forged_pass_field(self):
        e = deepcopy(self.evidence)
        e[2] = {'overall': 'PASS'}
        with self.assertRaises(KeyError):
            launch.verify_v26_fields(*e)

    def test_run_id_mismatch(self):
        e = deepcopy(self.evidence)
        e[3]['identity']['run_id'] = '0'*32
        with self.assertRaisesRegex(ValueError, 'run_id mismatch'):
            launch.verify_v26_fields(*e)

    def test_evidence_protection_and_matching_sha(self):
        before = {path: launch.sha(path) for path in launch.FIXED_PINS}
        launch.verify_v26()
        self.assertEqual(before, {path: launch.sha(path) for path in launch.FIXED_PINS})
        for path in (launch.OLD_FAIL, launch.V26 / 'closure_release.json'):
            digest = launch.sha(path)
            with self.assertRaises(FileExistsError):
                launch.write_once(path, {'overall': 'PASS'})
            self.assertEqual(digest, launch.sha(path))

    def test_frozen_asset_sha_drifts(self):
        for asset in ('input', 'GPI', 'source', 'executable', 'mpirun'):
            with self.subTest(asset=asset):
                altered = deepcopy(self.plan)
                altered[asset]['SHA256'] = '0'*64
                with self.assertRaisesRegex(ValueError, f'Wrong frozen {asset} SHA'):
                    launch.verify_physics(altered)

    def test_dependency_mismatch(self):
        result = {'library_SHA256': {}}
        with patch.object(launch.old, 'environment_review', return_value=result):
            with self.assertRaisesRegex(ValueError, 'dynamic library SHA drift'):
                launch.resource_review(self.plan)

    def test_output_directory_and_observation_mismatch(self):
        for asset, value in [('cwd', str(launch.RUN_2021)),
                             ('observation', {'path': 'SW_OPER_20210923T000000.cdf'})]:
            with self.subTest(asset=asset):
                with self.assertRaises(ValueError):
                    launch.verify_physics(dict(self.plan, **{asset: value}))

    def test_unreserved_checks_each_marker(self):
        folder = self.scratch()
        paths = [folder / name for name in ('actual_run','claim','audit')]
        launch.ensure_unreserved(*paths)
        for path in paths:
            with self.subTest(path=path.name):
                path.touch()
                with self.assertRaisesRegex(ValueError, 'already reserved'):
                    launch.ensure_unreserved(*paths)
                path.unlink()

    def test_concurrent_lock_rejected(self):
        lock = self.scratch() / 'lock'
        lock.touch()
        with launch.execution_lock(lock):
            with self.assertRaisesRegex(ValueError, 'owns the lock'):
                with launch.execution_lock(lock):
                    self.fail('Entered contended lock')

    def test_unknown_model_result_preserves_reservation_no_retry(self):
        folder = self.scratch()
        run, claim, output, release = [folder / name for name in ('run','claim','audit','release')]
        release.write_text('{}')
        with patch.multiple(launch, RUN=run, CLAIM_FILE=claim, AUDIT_DIR=output, RELEASE=release), \
                patch.object(launch, 'execution_lock', return_value=nullcontext()), \
                patch.object(launch, 'verify_plan', return_value=self.plan), \
                patch.object(launch, 'resource_review', return_value={'resource_ready': True}), \
                patch.object(launch, 'supervise', return_value={'qualification': 'UNKNOWN', 'returncode': None}) as start:
            with self.assertRaisesRegex(ValueError, 'failed or unknown'):
                launch.execute(2022, True, True)
            with self.assertRaisesRegex(ValueError, 'already reserved'):
                launch.execute(2022, True, True)
            self.assertTrue(run.is_dir())
            self.assertFalse(output.exists())
            self.assertFalse(launch.load(claim)['automatic_retry'])
            start.assert_called_once()
            self.assertEqual(start.call_args.kwargs['env']['CUDA_VISIBLE_DEVICES'], '')
            self.assertEqual(start.call_args.kwargs['env']['OMP_NUM_THREADS'], '1')
            self.assertEqual(start.call_args.args[0][1:3], ['-np','4'])

    def echo_fixture(self):
        path = self.scratch() / 'echo.nc'
        with Dataset(path, 'w', format='NETCDF3_CLASSIC') as n:
            n.history_type = 'primary'
            n.run_type = ''
            n.createDimension('time', 1)
            n.createDimension('three', 3)
            tv = n.createVariable('time', 'i4', ('time',))
            tv.units = 'minutes since 2022-09-09 00:00:00'
            tv.initial_year = 2022
            tv.initial_day = 252
            tv.initial_mtime = [252,0,0]
            tv[0] = 0
            for key, value in [('year', 2022), ('day', 252), ('iter', 115200)]:
                n.createVariable(key, 'i4', ('time',))[0] = value
            n.createVariable('mtime','i4',('time','three'))[0] = [252,0,0]
        with Dataset(path, 'r') as n:
            metadata = audit.metadata(n, 0)
        return metadata

    def test_legal_2022_first_echo(self):
        self.assertTrue(audit.validate_record(self.echo_fixture(), 'primary', audit.FIRST,
                                             0, audit.START, 115200, [80,0,0]))

    def test_illegal_2022_cold_echo(self):
        m = self.echo_fixture()
        for override, source in [({'iter': 385920}, [80,0,0]), ({'year': 2021}, [80,0,0]),
                                 ({'initial_year': 2021}, [80,0,0]), ({}, [81,0,0])]:
            with self.subTest(override=override, source=source), self.assertRaises(ValueError):
                audit.validate_record(dict(m, **override), 'primary', audit.FIRST,
                                      0, audit.START, 115200, source)

    def test_warm_empty_and_wrong_iter(self):
        t = audit.START + dt.timedelta(hours=1)
        m = dict(self.echo_fixture(), history_type='secondary', mtime=[252,1,0], utc=t)
        for state, iteration in [('',362940), ('initial',115200)]:
            with self.subTest(state=state), self.assertRaises(ValueError):
                audit.validate_record(dict(m, run_type=state, iter=iteration), 'secondary',
                                      'secondary_001.nc', 0, t, 115200, None)
        self.assertFalse(audit.validate_record(dict(m, run_type='initial', iter=362940),
                                               'secondary','secondary_001.nc',0,t,115200,None))

    def test_duplicate_or_missing_timeline(self):
        m = self.echo_fixture()
        for delta in (0,2):
            with self.subTest(delta=delta), self.assertRaisesRegex(ValueError, 'Unexpected UTC'):
                audit.validate_record(dict(m, utc=audit.START+dt.timedelta(hours=delta)),
                                      'secondary','secondary_001.nc',0,
                                      audit.START+dt.timedelta(hours=1),115200,None)

    def test_gpu_entry_points_absent(self):
        for module in (launch,audit):
            tree = ast.parse(Path(module.__file__).read_text())
            names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            self.assertFalse(names & {'torch','cupy','cuda','nvidia_smi'})


class FrozenScientificRegression(V26Tests):
    def new_directory(self):
        folder = tempfile.TemporaryDirectory(dir=ROOT / '.tmp')
        self.addCleanup(folder.cleanup)
        return Path(folder.name)


if __name__ == '__main__':
    # Reuse the relevant V26 real NetCDF and direct-wait negatives against the same
    # frozen functions called by the 2022 adapter.
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(V27Tests)
    for name in ('test_real_netcdf_nan','test_real_netcdf_inf','test_illegal_fill',
                 'test_nonpositive_density','test_nonmonotonic_zg','test_rank_exit_nonzero',
                 'test_rank_missing','test_missing_primary_state'):
        suite.addTest(FrozenScientificRegression(name))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
