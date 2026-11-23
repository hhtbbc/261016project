"""Read-only post-run adapter for the reserved V27 2022 cold start."""
import argparse
import datetime as dt
import json
import re

import numpy as np
from netCDF4 import Dataset

from audit_tiegcm_autumn_v26 import (
    FIRST, ROOT, binding, frozen, load, metadata, require, sha, source_identity,
    validate_input, write_once,
)
from runtime.readonly_audit_warning_channel import WarningChannel
from execute_tiegcm_autumn_2022_v27 import (
    AUDIT_DIR, CLAIM_FILE, RUN, V26_ID, model_argv, verify_plan,
)

START, STOP = frozen.dates(2022)


def validate_record(m, kind, name, index, expected_utc, seed_iter, source_start):
    t = m['utc']
    day = t.timetuple().tm_yday
    require(t == expected_utc, 'Unexpected UTC (duplicate, gap or wrong order)')
    require(m['history_type'] == kind, 'Native history mismatch')
    require((m['initial_year'], m['initial_day'], m['initial_mtime'])
            == (2022, 252, [252, 0, 0]), 'Native initial calendar identity mismatch')
    require((m['year'], m['day'], m['mtime']) == (2022, day, [day, t.hour, t.minute]),
            'CF/native year/day/mtime disagree')
    if name == FIRST and kind == 'primary' and index == 0 and t == START:
        require(source_start == [80, 0, 0] and m['run_type'] in ('', 'initial')
                and m['iter'] == seed_iter,
                'Illegal cold-echo run_type or inherited iter')
        return True
    require(t > START and m['run_type'] == 'initial', 'Warm run_type missing or invalid')
    require(m['iter'] == 252 * 1440 + int((t - START).total_seconds() / 60),
            'Warm iter/time mismatch')
    return False


def inspect_outputs(run, p):
    drv = frozen.GpiDriver(ROOT / p['GPI']['path'])
    with Dataset(ROOT / p['source']['path'], 'r') as seed:
        seed_iter = source_identity(seed, validate_input((run / 'input.inp').read_text(), 2022),
                                    p['source']['path'])
        grid = {key: np.asarray(seed[key][:]) for key in ('lat', 'lon', 'lev', 'ilev')}
        schema = {name: (seed[name].dimensions, seed[name].units) for name in frozen.REQUIRED}

    expected = {f'primary_{i:03d}.nc' for i in range(1, 18)}
    expected.update(f'secondary_{i:03d}.nc' for i in range(1, 17))
    require({path.name for path in run.glob('*.nc')} == expected, 'Unexpected output set')
    inventory = []
    primary, secondary = [], []
    worst = 0.0
    cold = None
    for kind, volumes, records in [('primary', 17, 1), ('secondary', 16, 24)]:
        for volume in range(1, volumes + 1):
            name = f'{kind}_{volume:03d}.nc'
            path = run / name
            require(path.resolve(strict=True) == path, 'Unexpected output path')
            before = path.stat()
            require(before.st_size <= 256 * 2**20, 'Volume budget exceeded')
            with Dataset(path, 'r') as n:
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
                    if validate_record(m, kind, name, index, t, seed_iter, list(n.source_mtime)
                                       if name == FIRST else None):
                        cold = dict(m, utc=t.isoformat() + 'Z', source_iter=seed_iter,
                                    source_SHA256=p['source']['SHA256'], primary_states=len(schema))
                    times.append(t)
                    if kind == 'secondary':
                        frozen.inspect_density_record(n, index)
                        expected = drv.at(2022000 + t.timetuple().tm_yday,
                                          t.hour * 3600 + t.minute * 60)
                        for field, value in expected.items():
                            worst = max(worst, frozen.driver_difference(frozen.field(n[field])[index], value))
                        require(worst < 1e-10, 'Actual GPI driver mismatch')
                (primary if kind == 'primary' else secondary).extend(times)
            signature = sha(path)
            after = path.stat()
            require((before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                    == (after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                    'Output changed during audit')
            inventory.append(dict(file=name, SHA256=signature,
                                  bytes=after.st_size, records=records,
                                  first_UTC=times[0].isoformat() + 'Z',
                                  last_UTC=times[-1].isoformat() + 'Z'))
    return dict(**frozen.validate_timelines(primary, secondary, 2022, int(cold is not None)),
                files=inventory, cold_echo=cold, DEN_ZG_warm_records=len(secondary),
                primary_required_states=len(schema), actual_GPI_max_abs_difference=worst)


def check_identity(p, run_id):
    require(RUN.resolve(strict=True) == RUN and CLAIM_FILE.resolve(strict=True) == CLAIM_FILE,
            'Unexpected 2022 run or claim path')
    require(re.fullmatch(r'[0-9a-f]{32}', run_id) and run_id != V26_ID,
            'Invalid 2022 run identity')
    claim = load(CLAIM_FILE)
    require(claim == dict(year=2022, run_id=run_id, attempts=1, automatic_retry=False,
                          release_SHA256=sha(AUDIT_DIR.parent / 'execution_release.json')),
            'Missing or different V27 once-only claim')
    status = load(RUN / 'status.json')
    require(status['returncode'] == 0 and status['qualification'] == 'PASS'
            and not status['gaps'] and status['cleanup_verified']
            and status['wait_source'] == 'direct subprocess.Popen.wait'
            and status['stop_reason'] is None and status['elapsed_s'] <= 4800,
            'MPI parent wait/monitoring failed')
    events = list(map(json.loads, (RUN / 'events.jsonl').read_text().splitlines()))
    started = [event for event in events if event['event'] == 'launched']
    waited = [event for event in events if event['event'] == 'child_wait_final']
    require(len(started) == len(waited) == 1 and started[0]['identity'] == status['identity']
            and waited[0]['returncode'] == 0 and waited[0]['cleanup_verified'],
            'Direct wait journal does not match parent')
    once = load(RUN / 'launch_once.json')
    require(once['launch_count'] == 1 and once['argv'] == model_argv(p, run_id),
            'One-time launch identity mismatch')
    binding(RUN / 'input.inp', p['input']['SHA256'])
    ranks = frozen.validate_exits(RUN, run_id, p)
    progress = []
    for rank in range(4):
        log = (RUN / f'rank_{rank:03d}.log').read_text()
        progress.append(frozen.parse_progress(log, steps=23040, start=START))
    require('output_hist: copied source history structure sh to' in (RUN / 'rank_000.log').read_text(),
            'Missing native cold echo execution evidence')
    return dict(parent_returncode=0, ranks=ranks, progress=progress,
                status_SHA256=sha(RUN / 'status.json'))


def audit(run_id):
    require(AUDIT_DIR.resolve() == AUDIT_DIR and AUDIT_DIR.is_dir()
            and not (AUDIT_DIR / 'acceptance.json').exists(), 'Invalid or used audit directory')
    p = verify_plan()
    identity = check_identity(p, run_id)
    reader = ROOT / 'src/atmosphere/hourly_tiegcm_observation.py'
    with WarningChannel(AUDIT_DIR, {reader: sha(reader)}) as warning:
        outputs = inspect_outputs(RUN, p)
        coverage = frozen.query_coverage(RUN, p, outputs)
    return dict(overall='PASS', year=2022, run_id=run_id, run=identity, outputs=outputs,
                Map_A=coverage, warning_count=warning.count, model_launches_this_audit=0,
                independent_review='PENDING')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    try:
        result = audit(args.run_id)
    except Exception as error:
        if AUDIT_DIR.resolve() == AUDIT_DIR and AUDIT_DIR.is_dir():
            write_once(AUDIT_DIR / 'failure.json', dict(overall='FAIL', error=str(error)))
        raise
    write_once(AUDIT_DIR / 'acceptance.json', result)


if __name__ == '__main__':
    main()
