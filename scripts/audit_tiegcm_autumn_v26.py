"""Versioned post-run audit of the single completed V24 run."""
import datetime as dt
import json
from pathlib import Path
import resource
import sys
import time

from tiegcm_autumn_v26_sha import (
    BASE, OUT, ROOT, RUN, TOTAL, V24, manifest_rows, require, stream_sha, write_once,
)

sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
import numpy as np
from netCDF4 import Dataset, num2date

from atmosphere import tiegcm_autumn_acceptance as frozen
from runtime.readonly_audit_warning_channel import WarningChannel
from runtime.tiegcm_autumn_execution import validate_input, verify_package

RUN_ID = '18726974f5d3450ba61f82c23c8da3a0'
START, STOP = frozen.dates(2021)
FIRST = 'primary_001.nc'
OLD_FAIL = BASE / 'postrun_audit_local/acceptance.json'
FAIL_SHA = '3859b363b92f6f5cfb3d10a125db8d83356cfe91d557f72f6b64ad285b998271'
V25 = ROOT / 'experiments/thermosphere_workspace_recovery_audit_v25'


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return stream_sha(path)[0]


def binding(path, expected):
    require(path.resolve(strict=True) == path and sha(path) == expected,
            f'Changed original asset: {path.name}')


def metadata(n, i):
    tv = n['time']
    missing = {'initial_year', 'initial_day', 'initial_mtime', 'units'} - set(tv.ncattrs())
    require(not missing, f'Missing time-variable attributes: {sorted(missing)}')
    missing = {'history_type', 'run_type'} - set(n.ncattrs())
    require(not missing, f'Missing history global attributes: {sorted(missing)}')
    for key in ('year', 'day', 'mtime', 'iter'):
        require(key in n.variables, f'Missing native variable: {key}')
    t = num2date(tv[i], tv.units)
    return dict(history_type=n.history_type, run_type=n.run_type,
                initial_year=int(tv.initial_year), initial_day=int(tv.initial_day),
                initial_mtime=list(map(int, tv.initial_mtime)), units=tv.units,
                year=int(n['year'][i]), day=int(n['day'][i]),
                mtime=list(map(int, n['mtime'][i])), iter=int(n['iter'][i]),
                utc=dt.datetime(t.year, t.month, t.day, t.hour, t.minute, t.second, t.microsecond))


def validate_record(m, kind, name, index, expected_utc, seed_iter):
    t = m['utc']
    day = t.timetuple().tm_yday
    require(t == expected_utc, 'Unexpected UTC (duplicate, gap or wrong order)')
    require(m['history_type'] == kind, 'Native history mismatch')
    require((m['initial_year'], m['initial_day'], m['initial_mtime'])
            == (2021, 252, [252, 0, 0]), 'Native initial calendar identity mismatch')
    require((m['year'], m['day'], m['mtime']) == (2021, day, [day, t.hour, t.minute]),
            'CF/native year/day/mtime disagree')
    if name == FIRST and kind == 'primary' and index == 0 and t == START:
        require(m['run_type'] in ('', 'initial') and m['iter'] == seed_iter,
                'Illegal cold-echo run_type or inherited iter')
        return True
    require(t > START and m['run_type'] == 'initial', 'Warm run_type missing or invalid')
    require(m['iter'] == 252 * 1440 + int((t - START).total_seconds() / 60),
            'Warm iter/time mismatch')
    return False


def source_identity(n, config, seed_path):
    require(config['SOURCE'] == f"'$PROJECTROOT/{seed_path}'"
            and config['SOURCE_START'].split() == ['80', '0', '0'],
            'Explicit SOURCE / SOURCE_START mismatch')
    require(n.history_type == 'primary' and len(n.dimensions['time']) == 1,
            'Invalid mareqx source structure')
    require((int(n['year'][0]), int(n['day'][0]), list(n['mtime'][0]))
            == (2002, 80, [80, 0, 0]), 'Wrong mareqx source record')
    require(int(n['iter'][0]) == 115200, 'Wrong mareqx source iter')
    return int(n['iter'][0])


def validate_sha_receipt(receipt):
    rows = receipt['files']
    manifest = manifest_rows()
    require(receipt['V24_33_NETCDF_SHA_VERIFIED'] is True
            and receipt['file_count'] == len(rows) == len(manifest) == 33
            and receipt['read_bytes'] == sum(row['read_bytes'] for row in rows) == TOTAL
            and {p.name for p in RUN.glob('*.nc')} == {row['file'] for row in manifest},
            'Incomplete SHA receipt')
    for row, reference in zip(rows, manifest):
        require(row['match'] is True and row['file'] == reference['file']
                and row['actual_SHA256'] == row['expected_SHA256'] == reference['SHA256']
                and row['actual_bytes'] == row['read_bytes'] == int(reference['bytes']),
                'SHA receipt differs from release manifest')
        volume_unchanged(row)
    return {row['file']: row for row in rows}


def volume_unchanged(row):
    path = RUN / row['file']
    require(path.resolve(strict=True) == path, 'Output path no longer canonical')
    s = path.stat()
    require((s.st_size, s.st_ino, s.st_dev, s.st_mtime_ns, s.st_ctime_ns)
            == tuple(row[k] for k in ('actual_bytes', 'inode', 'device', 'mtime_ns', 'ctime_ns')),
            f'Output changed since SHA scan: {path.name}')


def historical_evidence(p):
    binding(OLD_FAIL, FAIL_SHA)
    binding(V24 / 'main_acceptance_snapshot.json', FAIL_SHA)
    snapshot = load(OLD_FAIL)
    require(snapshot['overall'] == 'FAIL' and snapshot['run_id'] == RUN_ID,
            'Wrong historical acceptance identity')
    references = snapshot['checks']
    binding(RUN / 'status.json', references['supervision']['evidence']['status_SHA256'])
    for rank in references['MPI_rank_exits']['evidence']['ranks']:
        binding(RUN / f"rank_{rank['rank']:03d}_exit.json", rank['receipt_SHA256'])
    status = load(RUN / 'status.json')
    require(status['returncode'] == 0 and status['qualification'] == 'PASS'
            and not status['gaps'] and status['cleanup_verified']
            and status['wait_source'] == 'direct subprocess.Popen.wait'
            and status['stop_reason'] is None and status['elapsed_s'] <= 4800,
            'MPI parent wait/monitoring failed')
    journal = [json.loads(line) for line in (RUN / 'events.jsonl').read_text().splitlines()]
    started = [event for event in journal if event['event'] == 'launched']
    waited = [event for event in journal if event['event'] == 'child_wait_final']
    require(len(started) == len(waited) == 1 and started[0]['identity'] == status['identity']
            and waited[0]['returncode'] == 0 and waited[0]['cleanup_verified'],
            'Original supervision journal does not match direct wait')
    claim = load(BASE / 'execution_claim_local.json')
    launch = load(RUN / 'launch_once.json')
    argv = launch['argv']
    require(claim['run_id'] == RUN_ID and claim['year'] == 2021 and claim['attempts'] == 1
            and claim['automatic_retry'] is False and launch['launch_count'] == 1
            and argv[argv.index('--run-id') + 1] == RUN_ID,
            'Original launch reservation mismatch')
    binding(RUN / 'input.inp', p['input']['SHA256'])
    return dict(run_id=RUN_ID, returncode=0, direct_wait=True, launch_count=1)


def inspect_outputs(p, verified):
    drv = frozen.GpiDriver(ROOT / p['GPI']['path'])
    with Dataset(ROOT / p['source']['path'], 'r') as seed:
        seed_iter = source_identity(seed, validate_input((RUN / 'input.inp').read_text(), 2021),
                                    p['source']['path'])
        grid = {key: np.asarray(seed[key][:]) for key in ('lat', 'lon', 'lev', 'ilev')}
        schema = {name: (seed[name].dimensions, seed[name].units) for name in frozen.REQUIRED}

    inventory = []
    primary, secondary = [], []
    worst = 0.0
    cold = None
    for kind, volumes, records in [('primary', 17, 1), ('secondary', 16, 24)]:
        for volume in range(1, volumes + 1):
            name = f'{kind}_{volume:03d}.nc'
            row = verified[name]
            volume_unchanged(row)
            require(row['actual_bytes'] <= 256 * 2**20, 'Volume budget exceeded')
            with Dataset(RUN / name, 'r') as n:
                require(n.history_type == kind and n.data_model == 'NETCDF3_CLASSIC',
                        'Native format/history mismatch')
                require(len(n.dimensions['time']) == records, 'Wrong records per volume')
                require(int(np.asarray(n['timestep'][:]).item()) == 60
                        and np.all(n['calendar_advance'][:] == 1), 'Step/calendar mismatch')
                for key, coordinate in grid.items():
                    require(np.array_equal(n[key][:], coordinate), f'Grid mismatch: {key}')
                frozen.prognostics(n)
                if kind == 'primary':
                    for field, wanted in schema.items():
                        require((n[field].dimensions, n[field].units) == wanted,
                                f'Primary source schema mismatch: {field}')
                else:
                    for field in ('TN', 'UN', 'VN', 'O1', 'O2', 'N2', 'HE'):
                        unit = 'mmr' if field == 'N2' else schema[field][1]
                        require(n[field].dimensions == ('time', 'lev', 'lat', 'lon')
                                and n[field].dtype.kind == 'f' and n[field].units == unit,
                                f'Secondary schema mismatch: {field}')
                times = []
                for index in range(records):
                    m = metadata(n, index)
                    elapsed_h = (volume - 1) * 24 + (index + 1 if kind == 'secondary' else 0)
                    t = START + dt.timedelta(hours=elapsed_h)
                    if validate_record(m, kind, name, index, t, seed_iter):
                        require(list(n.source_mtime) == [80, 0, 0], 'Echo source_mtime mismatch')
                        cold = dict(m, utc=t.isoformat() + 'Z', source_iter=seed_iter,
                                    source_SHA256=p['source']['SHA256'], primary_states=len(schema))
                    times.append(t)
                    if kind == 'secondary':
                        frozen.inspect_density_record(n, index)
                        expected = drv.at(2021000 + t.timetuple().tm_yday,
                                          t.hour * 3600 + t.minute * 60)
                        for field, value in expected.items():
                            worst = max(worst, frozen.driver_difference(frozen.field(n[field])[index], value))
                        require(worst < 1e-10, 'Actual GPI driver mismatch')
                (primary if kind == 'primary' else secondary).extend(times)
            volume_unchanged(row)
            inventory.append(dict(file=name, SHA256=row['actual_SHA256'],
                                  bytes=row['actual_bytes'], records=records,
                                  first_UTC=times[0].isoformat() + 'Z',
                                  last_UTC=times[-1].isoformat() + 'Z'))
    return dict(**frozen.validate_timelines(primary, secondary, 2021, int(cold is not None)),
                files=inventory, cold_echo=cold, DEN_ZG_warm_records=len(secondary),
                primary_required_states=len(schema), actual_GPI_max_abs_difference=worst)


def protect():
    v25_paths = [V25 / 'audit.json', V25 / 'assets.csv',
                 ROOT / 'reports/THERMOSPHERE_WORKSPACE_RECOVERY_AUDIT_V25.md']
    paths = v25_paths + [OLD_FAIL, BASE / 'execution_claim_local.json']
    paths += sorted(path for path in RUN.iterdir() if path.is_file() and path.suffix != '.nc')
    paths += [V24 / name for name in ('result_final.json', 'cold_echo_failure_diagnosis.json',
                                      'model_output_manifest.csv', 'independent_verification.json')]
    return {str(path.relative_to(ROOT)): sha(path) for path in paths}


def audit_directory(path):
    require(path.resolve() == path and path.parent == OUT, 'Wrong audit destination')
    path.mkdir(exist_ok=False)


def expected_inventory(rows):
    return {row['file']: (row['SHA256'], int(row['bytes']), int(row['records']),
                          row['first_UTC'], row['last_UTC']) for row in rows}


def finish(destination, checks, verified, old_hashes, wall, cpu, independent_attempts):
    # The original verifier runs its raw checks before reading any new V26 verdict.
    # Its historical overall field refers to V24 and remains visible in this evidence.
    from scripts.verify_tiegcm_autumn_2021_v24 import review
    independent = review()
    write_once(destination / 'independent_review.json', independent)
    observed = {row['file']: (row['SHA256'], row['bytes'], row['records'],
                              row['first_UTC'], row['last_UTC'])
                for row in independent['outputs']['files']}
    expected = expected_inventory(manifest_rows())
    require(observed == expected and len(observed) == 33
            and independent['outputs']['NetCDF_bytes'] == TOTAL,
            'Independent current SHA/size/calendar does not match published release')
    require(independent['independent_raw_checks'] == 'PASS'
            and independent['identity']['run_id'] == RUN_ID
            and independent['identity']['actual_steps'] == 23040
            and independent['identity']['actual_final_UTC'] == STOP.isoformat() + 'Z'
            and independent['outputs']['primary_records'] == 17
            and independent['outputs']['secondary_records'] == 384
            and independent['outputs']['all_warm_DEN_ZG_records'] == 384
            and independent['independent_queries']['success'] == checks['target_observation_queries']['success'] == 2880,
            'Independent raw result disagrees with V26 primary audit')
    for row in verified.values():
        volume_unchanged(row)
    require(protect() == old_hashes, 'Original run, V24 evidence or V25 records changed')
    require(not (BASE.parent / '2022/actual_run').exists()
            and not (BASE.parent / '2022/execution_claim_local.json').exists(),
            'Unexpected 2022 run evidence')
    write_once(destination / 'result.json', dict(
        V26_POSTRUN_VERIFICATION='ENGINEERING_PASS', V24_ORIGINAL_ENGINEERING_STATUS='FAIL',
        V24_33_NETCDF_SHA_VERIFIED=True, main_attempts=1, independent_attempts=independent_attempts, model_launches=0, GPU_calls=0,
        autumn_2022='NOT_RUN', historical_files_unchanged=len(old_hashes),
        wall_s=time.monotonic() - wall, CPU_s=time.process_time() - cpu,
        peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))


def resume_independent():
    """Recover the lost independent evidence without invoking primary acceptance."""
    wall, cpu = time.monotonic(), time.process_time()
    original = OUT / 'formal_once'
    failure = load(original / 'failure.json')
    require(failure['error'] == 'Independent current SHA/size/calendar does not match published release',
            'Unrecognized failed stage')
    main_result = load(original / 'main_acceptance.json')
    require(main_result['overall'] == 'PASS' and main_result['run_id'] == RUN_ID
            and main_result['model_launches_this_audit'] == 0, 'Missing original V26 primary PASS')
    previous = load(OUT / 'supervision_local/status.json')
    require(previous['returncode'] == 1 and previous['elapsed_s'] < 300,
            'Original attempt supervision or remaining budget is invalid')
    verified = validate_sha_receipt(load(OUT / 'sha_verification.json'))
    p = verify_package(2021)
    historical_evidence(p)
    for name, expected in load(V24 / 'code_version_manifest.json').items():
        binding(ROOT / name, expected)
    old_hashes = protect()
    destination = OUT / 'independent_recovery_once'
    audit_directory(destination)
    try:
        finish(destination, main_result['checks'], verified, old_hashes, wall, cpu, 2)
    except Exception as error:
        write_once(destination / 'failure.json', dict(overall='FAIL',
                                                      error_type=type(error).__name__, error=str(error)))
        raise


def main():
    wall = time.monotonic()
    cpu = time.process_time()
    destination = OUT / 'formal_once'
    audit_directory(destination)
    checks = {}
    try:
        verified = validate_sha_receipt(load(OUT / 'sha_verification.json'))
        p = verify_package(2021)
        old_hashes = protect()
        checks['supervision'] = historical_evidence(p)
        checks['MPI_rank_exits'] = frozen.validate_exits(RUN, RUN_ID, p)
        checks['step_logs'] = [
            frozen.parse_progress((RUN / f'rank_{i:03d}.log').read_text(), steps=23040, start=START)
            for i in range(4)
        ]
        reader = ROOT / 'src/atmosphere/hourly_tiegcm_observation.py'
        release = load(BASE.parent / 'execution_release.json')
        binding(BASE.parent / 'execution_release.json',
                '3e6db19a1ff954e3df2b2c4d6b1050a527e5ac269b9597b87ea2b5200133860f')
        binding(reader, release['scientific_asset_SHA256'][str(reader.relative_to(ROOT))])
        for name, expected in load(V24 / 'code_version_manifest.json').items():
            binding(ROOT / name, expected)
        with WarningChannel(destination, {reader: sha(reader)}) as channel:
            checks['output_files'] = inspect_outputs(p, verified)
            checks['target_observation_queries'] = frozen.query_coverage(RUN, p, checks['output_files'])
        main_result = dict(overall='PASS', run_id=RUN_ID, checks=checks,
                           warning_count=channel.count, model_launches_this_audit=0,
                           wall_s=time.monotonic() - wall, CPU_s=time.process_time() - cpu)
        write_once(destination / 'main_acceptance.json', main_result)

        finish(destination, checks, verified, old_hashes, wall, cpu, 1)
    except Exception as error:
        write_once(destination / 'failure.json', dict(overall='FAIL', completed_checks=list(checks),
                                                      error_type=type(error).__name__, error=str(error)))
        raise


if __name__ == '__main__':
    if sys.argv[1:] == ['--resume-independent']:
        resume_independent()
    else:
        require(not sys.argv[1:], 'Unexpected arguments')
        main()
