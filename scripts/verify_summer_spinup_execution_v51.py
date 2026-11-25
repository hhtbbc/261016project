"""Independent 23-day engineering inspection before admitting the next role."""
import argparse
from datetime import timedelta, timezone
import math

import numpy as np
from netCDF4 import Dataset

import prepare_summer_gpi_extended_v50 as gpi
from check_summer_spinup_add7_v50 import replay_input
from run_summer_seed_sensitivity_v46 import (
    REQUIRED, checks, load, metadata, model_argv, require, sha, v45, write_once,
)

ROOT = gpi.ROOT
START = gpi.START.replace(tzinfo=None)


def validate(run, p, run_id):
    status = load(run/'status.json')
    require(status['returncode'] == 0 and status['qualification'] == 'PASS'
            and status['cleanup_verified'] and not status['gaps']
            and status['wait_source'] == 'direct subprocess.Popen.wait', 'Bad MPI supervisor receipt')
    require(load(run/'launch_once.json')['argv'] == model_argv(p, run_id), 'Launch identity mismatch')
    require(sha(run/'input.inp') == p['input']['SHA256'], 'Input changed')
    require(status['elapsed_s'] <= 4800 and status['stop_reason'] is None
            and 0 < status['peak_sampled_tree_rss_bytes'] <= 16*2**30, 'Wall time or RSS budget exceeded')
    total_bytes = sum(path.stat().st_size for path in run.rglob('*') if path.is_file())
    require(total_bytes <= 5*2**30, 'Total output exceeded frozen budget')
    ranks = checks.validate_exits(run, run_id, p)
    steps = [checks.parse_progress((run/f'rank_{i:03d}.log').read_text(), steps=33120, start=START) for i in range(4)]
    require('output_hist: copied source history structure sh to' in (run/'rank_000.log').read_text(),
            'Missing cold source log')
    for key in ('executable', 'source', 'GPI'):
        v45.verify_hash(p[key]['path'], p[key]['SHA256'])
    with Dataset(ROOT/p['source']['path']) as n:
        seed_iter = int(n['iter'][0])
        grid = {k: np.asarray(n[k][:]) for k in ('lev','ilev','lat','lon')}
        schema = {k:(n[k].dimensions,n[k].units) for k in REQUIRED}
    driver = v45.GpiDriver(ROOT/p['GPI']['path'])
    solar, kp, _ = replay_input()
    means = {t: math.fsum(solar[t+timedelta(days=d)] for d in range(-40,41))/81
             for t in gpi.TIMES}
    names = {f'{kind}_{i:03d}.nc' for kind, count in [('primary',24),('secondary',23)]
             for i in range(1,count+1)}
    require({f.name for f in run.glob('*.nc')} == names, 'Wrong output inventory')
    files = []
    worst = 0.
    for name in sorted(names):
        kind, volume = name[:-3].split('_')
        volume = int(volume)
        count = 1 if kind == 'primary' else 24
        path = run/name
        stat = path.stat()
        require(path.resolve() == path and stat.st_size <= 256*2**20, 'Unexpected volume')
        with Dataset(path) as n:
            require(n.data_model == 'NETCDF3_CLASSIC' and len(n.dimensions['time']) == count
                    and int(np.asarray(n['timestep'][:]).item()) == 60
                    and np.all(n['calendar_advance'][:] == 1), 'Wrong format, STEP, calendar or record count')
            for k,v in grid.items():
                require(np.array_equal(v, n[k][:]), f'Grid drift {k}')
            checks.prognostics(n)
            if kind == 'primary':
                for k, wanted in schema.items():
                    require((n[k].dimensions,n[k].units) == wanted, f'Primary schema mismatch {k}')
            else:
                for k in ('TN','UN','VN','O1','O2','N2','HE'):
                    require(n[k].dimensions == ('time','lev','lat','lon') and n[k].units ==
                            ('mmr' if k == 'N2' else schema[k][1]), f'Secondary schema mismatch {k}')
                read_drivers = {k: checks.field(n[k]) for k in driver.at(2022151,0)}
            times = []
            for i in range(count):
                hours = 24*(volume-1) + (i+1 if kind == 'secondary' else 0)
                t = START + timedelta(hours=hours)
                m = metadata(n,i)
                yd = t.timetuple().tm_yday
                require(m['utc'] == t and m['history_type'] == kind
                        and (m['initial_year'],m['initial_day'],m['initial_mtime']) == (2022,151,[151,0,0])
                        and (m['year'],m['day'],m['mtime']) == (2022,yd,[yd,t.hour,0]), 'Wrong output UTC/native identity')
                if hours == 0:
                    require(name == 'primary_001.nc' and list(n.source_mtime) == p['source_start']
                            and m['run_type'] in ('','initial') and m['iter'] == seed_iter, 'Invalid cold echo')
                else:
                    require(m['run_type'] == 'initial' and m['iter'] == 151*1440+hours*60, 'Wrong warm iter')
                if kind == 'secondary':
                    checks.inspect_density_record(n,i)
                    wanted = gpi.independent_at(t.replace(tzinfo=timezone.utc), solar, means, kp)
                    gpi.compare_vectors(driver.at(2022000+yd,t.hour*3600), wanted, 'Native reader mismatch')
                    worst = max(worst, *(checks.driver_difference(read_drivers[k][i],v) for k,v in wanted.items()))
                    require(worst < 1e-10, 'GPI driver discrepancy')
                times.append(t.isoformat()+'Z')
        digest = sha(path)
        after = path.stat()
        require((stat.st_size,stat.st_mtime_ns,stat.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino),
                'Volume changed during audit')
        files.append(dict(file=name, SHA256=digest, bytes=stat.st_size, records=count,
                          first_UTC=times[0],last_UTC=times[-1]))
    return dict(engineering='PASS', role=p['role'], plan_sha256=p['plan_sha256'],
                run_id=run_id, parent_exit=status['returncode'], rank_exit=[r['returncode'] for r in ranks['ranks']],
                steps=33120, secondary_hours=sum(f['records'] for f in files if f['file'].startswith('secondary')),
                final_model_UTC=gpi.STOP.isoformat(), model_sha256=p['executable']['SHA256'],
                gpi_sha256=p['GPI']['SHA256'], input_sha256=p['input']['SHA256'],
                source_sha256=p['source']['SHA256'], outputs_sha256={f['file']: f['SHA256'] for f in files},
                files=files, progress=steps, ranks=ranks, max_GPI_abs=worst,
                elapsed_s=status['elapsed_s'], peak_RSS_bytes=status['peak_sampled_tree_rss_bytes'],
                NetCDF_bytes=sum(f['bytes'] for f in files), total_output_bytes=total_bytes,
                parent_identity=status['identity'], status_sha256=sha(run/'status.json'),
                rank_log_sha256={f'rank_{i:03d}.log':sha(run/f'rank_{i:03d}.log') for i in range(4)},
                CPU_user_seconds=status['children_cpu_user_s'],
                CPU_system_seconds=status['children_cpu_system_s'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('role', choices=('A', 'B'))
    args = parser.parse_args()
    from execute_summer_spinup_add7_v51 import protocol, OUT, run_path
    run = run_path(args.role)
    claim = load(OUT/f'claim_{args.role}.json')
    p = protocol(args.role)
    require(claim['plan_sha256'] == p['plan_sha256'], 'Claim plan mismatch')
    receipt = validate(run, p, claim['run_id'])
    write_once(run/'engineering_receipt.json', receipt)


if __name__ == '__main__':
    main()
