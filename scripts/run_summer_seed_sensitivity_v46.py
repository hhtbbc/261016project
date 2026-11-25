"""Once-only CPU summer engineering pair. No observation access."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

import numpy as np
from netCDF4 import Dataset
import preflight_summer_config_v45 as v45
from audit_tiegcm_autumn_v26 import metadata
from execute_tiegcm_autumn_2022_v27 import execution_lock, model_argv, resource_review
from atmosphere import tiegcm_autumn_acceptance as checks
from atmosphere.restart_validation import REQUIRED, inspect_restart
from runtime import tiegcm_autumn_execution as env
from runtime.supervisor import Limits, supervise
from runtime.tiegcm_rank_exit import write_once

ROOT = v45.ROOT
OUT = ROOT / 'experiments/thermosphere_summer_seed_sensitivity_v46'
START = v45.START.replace(tzinfo=None)
STOP = v45.STOP.replace(tzinfo=None)
A = 'run_A_mareqx'
B = 'run_B_junsol'
TEMPLATE = v45.OUT / '2022_summer_offline.namelist.draft'
V45 = 'dd1d33d1ee9b165e1ce5bef51dbe6ed71cb00043'
require = v45.need
sha = v45.digest


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(path.read_text())


def entry(path, expected):
    return {'path': str(path), 'SHA256': expected}


def plan():
    receipt = json.loads(subprocess.check_output([
        sys.executable, '-B', str(ROOT / 'scripts/preflight_summer_config_v45.py'), '--check-only'
    ], cwd=ROOT, env=env.runtime_environment(), text=True))
    manifest_path = v45.OUT / 'publication_SHA256.json'
    manifest = subprocess.check_output(['git', 'show', f'{V45}:{manifest_path.relative_to(ROOT)}'])
    require(manifest_path.read_bytes() == manifest, 'V45 manifest changed')
    for path, digest in json.loads(manifest).items():
        v45.verify_hash(path, digest)
    base = json.loads(v45.pinned(v45.V27))
    mareqx = base['physical_paths']['source']
    v45.verify_hash(mareqx, base['physical_SHA256']['source'])
    first = inspect_restart(ROOT / mareqx, [80, 0, 0])
    require(first['structure_complete'] and first['record_available'], 'Invalid mareqx state')
    with Dataset(ROOT / mareqx) as n:
        require(int(n['year'][0]) == 2002 and int(n['day'][0]) == 80 and
                n.label == 'tiegcm_res5.0_mareqx_smax', 'Not native mareqx smax')
    b = TEMPLATE.read_text()
    a = b.replace(f'$PROJECTROOT/{v45.SEED}', f'$PROJECTROOT/{mareqx}').replace(
        'SOURCE_START = 172 0 0', 'SOURCE_START = 80 0 0')
    differences = [line.split('=')[0].strip() for line, other in zip(a.splitlines(), b.splitlines(), strict=True)
                   if line != other]
    require(differences == ['SOURCE', 'SOURCE_START'], 'Pair differs outside source')
    protocols = {}
    for name, source, digest, clock, text in (
        (A, mareqx, base['physical_SHA256']['source'], [80, 0, 0], a),
        (B, v45.SEED, v45.JUNSOL, [172, 0, 0], b)):
        import hashlib
        require(len(str(OUT / name)) < 120 and (OUT/name).resolve() == OUT/name, 'Invalid output directory')
        asset = {k: entry(base['physical_paths'][k], base['physical_SHA256'][k]) for k in ('executable', 'mpirun')}
        protocols[name] = dict(**asset, input=entry(str((OUT/f'{name}.namelist').relative_to(ROOT)),
                    hashlib.sha256(text.encode()).hexdigest()), source=entry(source, digest),
                    source_start=clock, GPI=entry(v45.GPI, v45.DRIVER), input_text=text)
    current = resource_review(protocols[A])
    require(current['resource_ready'], 'CPU resources or an active model blocks start')
    return dict(base=V45, protocols=protocols, differences=differences, preflight=receipt,
                resource=current, scope='2022 summer internal field engineering pair; no observations',
                approval='User V46 explicit 2022 pair only', V37_qualified=False, order=[A, B],
                auto_retry=False, elapsed_days=[1, 3, 7, 14], final_window_hours=[360,384],
                criteria='experiments/tiegcm_2021_spinup_14day_v1/frozen_comparison_rules.json')


def validate(run, p, run_id):
    status = load(run/'status.json')
    require(status['returncode'] == 0 and status['qualification'] == 'PASS'
            and status['cleanup_verified'] and not status['gaps']
            and status['wait_source'] == 'direct subprocess.Popen.wait', 'Bad MPI supervisor receipt')
    require(load(run/'launch_once.json')['argv'] == model_argv(p, run_id), 'Launch identity mismatch')
    require(sha(run/'input.inp') == p['input']['SHA256'], 'Input changed')
    ranks = checks.validate_exits(run, run_id, p)
    steps = [checks.parse_progress((run/f'rank_{i:03d}.log').read_text(), steps=23040, start=START) for i in range(4)]
    require('output_hist: copied source history structure sh to' in (run/'rank_000.log').read_text(),
            'Missing cold source log')
    for key in ('executable', 'source', 'GPI'):
        v45.verify_hash(p[key]['path'], p[key]['SHA256'])
    with Dataset(ROOT/p['source']['path']) as n:
        seed_iter = int(n['iter'][0])
        grid = {k: np.asarray(n[k][:]) for k in ('lev','ilev','lat','lon')}
        schema = {k:(n[k].dimensions,n[k].units) for k in REQUIRED}
    driver = v45.GpiDriver(ROOT/p['GPI']['path'])
    names = {f'{kind}_{i:03d}.nc' for kind, count in [('primary',17),('secondary',16)]
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
                read_drivers = {k: checks.field(n[k]) for k in driver.at(2022158,0)}
            times = []
            for i in range(count):
                hours = 24*(volume-1) + (i+1 if kind == 'secondary' else 0)
                t = START + timedelta(hours=hours)
                m = metadata(n,i)
                yd = t.timetuple().tm_yday
                require(m['utc'] == t and m['history_type'] == kind
                        and (m['initial_year'],m['initial_day'],m['initial_mtime']) == (2022,158,[158,0,0])
                        and (m['year'],m['day'],m['mtime']) == (2022,yd,[yd,t.hour,0]), 'Wrong output UTC/native identity')
                if hours == 0:
                    require(name == 'primary_001.nc' and list(n.source_mtime) == p['source_start']
                            and m['run_type'] in ('','initial') and m['iter'] == seed_iter, 'Invalid cold echo')
                else:
                    require(m['run_type'] == 'initial' and m['iter'] == 158*1440+hours*60, 'Wrong warm iter')
                if kind == 'secondary':
                    checks.inspect_density_record(n,i)
                    wanted = driver.at(2022000+yd,t.hour*3600)
                    worst = max(worst, *(checks.driver_difference(read_drivers[k][i],v) for k,v in wanted.items()))
                    require(worst < 1e-10, 'GPI driver discrepancy')
                times.append(t.isoformat()+'Z')
        digest = sha(path)
        after = path.stat()
        require((stat.st_size,stat.st_mtime_ns,stat.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino),
                'Volume changed during audit')
        files.append(dict(file=name, SHA256=digest, bytes=stat.st_size, records=count,
                          first_UTC=times[0],last_UTC=times[-1]))
    return dict(overall='PASS', run_id=run_id, parent_exit=status['returncode'], ranks=ranks, progress=steps,
                final_UTC=STOP.isoformat()+'Z', files=files, max_GPI_abs=worst, supervision=status)


def execute(bundle):
    with execution_lock(env.PACKAGE / 'autumn_execution_lock_local'):
        require(not (OUT/'pair_claim.json').exists(), 'V46 already attempted')
        for name in (A,B):
            require(not os.path.lexists(OUT/name), 'V46 run directory already exists')
        write_once(OUT/'pair_claim.json',dict(UTC=now(),scope=bundle['scope'],order=bundle['order'],attempts=1))
        for name in (A,B):
            p = bundle['protocols'][name]
            require(resource_review(p)['resource_ready'], 'CPU capacity no longer available')
            require(name == A or load(OUT/f'{A}_acceptance.json')['overall'] == 'PASS', 'A did not qualify')
            for key in ('GPI','source','input','executable','mpirun'):
                v45.verify_hash(p[key]['path'],p[key]['SHA256'])
            run = OUT/name
            run.mkdir()
            run_id = uuid.uuid4().hex
            write_once(OUT/f'{name}_claim.json',dict(run_id=run_id,UTC=now(),input_sha256=p['input']['SHA256']))
            result = supervise(model_argv(p,run_id),run,
                Limits(4770,16*2**30,20*2**30,5*2**30,256*2**20,total_output_bytes=5*2**30),
                env=env.runtime_environment(), total_dir=run,
                input_files={'input.inp':(ROOT/p['input']['path']).read_bytes()})
            require(result['qualification']=='PASS' and result['returncode']==0,'Supervisor stopped model')
            write_once(OUT/f'{name}_acceptance.json',validate(run,p,run_id))
            print(name,'ENGINEERING_PASS',flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--authorized-v46-pair',action='store_true')
    args = p.parse_args()
    require(OUT.resolve()==OUT and OUT.is_dir(),'Unexpected V46 directory')
    if args.authorized_v46_pair:
        require(not (OUT/'pair_claim.json').exists(), 'No repeat attempt')
    bundle = plan()
    if not args.authorized_v46_pair:
        print(json.dumps(bundle,indent=2))
        return
    for name, proto in bundle['protocols'].items():
        with (ROOT/proto['input']['path']).open('x') as f:
            f.write(proto['input_text'])
    write_once(OUT/'frozen_pair.json',bundle)
    try:
        execute(bundle)
    except BaseException as exc:
        write_once(OUT/'failure.json',dict(UTC=now(),failure=repr(exc)))
        raise


if __name__ == '__main__':
    main()
