"""Execute the frozen V50 CPU pair at most once per role."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import uuid

import preflight_summer_spinup_add7_v50 as offline
from run_summer_seed_sensitivity_v46 import (
    Limits, env, execution_lock, load, model_argv, now, require, resource_review, sha,
    supervise, write_once,
)

gpi = offline.gpi
ROOT = offline.ROOT
OUT = ROOT/'experiments/thermosphere_summer_spinup_add7_execution_v51'
AUTH = OUT/'authorization_local.json'
BASE = '2c8ad3e41ce7ccf1be89009230f0964c1acacb98'
GIB = 2**30
MIB = 2**20


def run_path(role):
    return offline.OUT/offline.RUNS[('A', 'B').index(role)]


def available(role):
    return not any(os.path.lexists(path) for path in (run_path(role), OUT/f'claim_{role}.json'))


def protocol(role):
    i = ('A', 'B').index(role)
    config = load(offline.OUT/'configuration.json')
    source = config['seeds'][i]
    name = offline.RUNS[i]+'.namelist'
    copy = offline.safe_source(run_path(role), '../'+offline.SEEDS[i])
    gpi.verify_sha(ROOT/source['source'], source['SHA256'])
    p = dict(role=role, executable=config['model'], mpirun=config['MPI'], GPI=config['GPI'],
             source=dict(path=str(copy.relative_to(ROOT)), SHA256=source['SHA256']),
             source_start=source['SOURCE_START'], plan_sha256=sha(offline.PLAN),
             input=dict(path=str((offline.OUT/name).relative_to(ROOT)), SHA256=config['config_sha'][name]))
    for key in ('executable', 'mpirun', 'GPI', 'source', 'input'):
        asset = p[key]
        require(sha(ROOT/asset['path']) == asset['SHA256'], f'Frozen {key} SHA changed')
    return p


def frozen():
    manifest = offline.OUT/'publication_SHA256.json'
    pinned = subprocess.check_output(['git', 'show', f'{BASE}:{manifest.relative_to(ROOT)}'], cwd=ROOT)
    require(manifest.read_bytes() == pinned, 'V50 publication manifest changed')
    entries = load(manifest)
    for path, digest in entries.items():
        require(sha(ROOT/path) == digest, f'Frozen V50 SHA changed: {path}')
    freeze = load(offline.OUT/'input_freeze.json')
    for path, digest in freeze['sources'].items():
        require(sha(ROOT/path) == digest, f'GFZ source changed: {path}')
    historical = gpi.protection()
    require(historical == freeze['old_inventory'], 'Historical V48/V49 evidence changed')
    diff = offline.validate(
        [(offline.OUT/(name+'.namelist')).read_text() for name in offline.RUNS],
        offline.expected_pair(offline.v47.INPUT.read_text()))
    return dict(V50_files=len(entries)+1, history=historical, differences=diff,
                plan_sha256=sha(offline.PLAN))


def budget(resources, plan):
    require(resources['resource_ready'] and resources['disk_free_bytes'] >= 25*GIB,
            'CPU affinity, memory, disk, or exclusive model resource gate failed')
    require(plan['budget_estimate']['estimated_NetCDF_bytes_per_run'] < 5*GIB
            and plan['budget_estimate']['estimated_minutes_per_run']*60 < 4770,
            'V50 expected outputs or duration exceed frozen budgets')


def check():
    offline.check_gpu(os.environ)
    require(Path(sys.executable) == ROOT/'.venv310/bin/python', 'Use frozen CPU Python entry')
    review = frozen()
    p = protocol('A')
    protocol('B')
    resources = resource_review(p)
    budget(resources, load(offline.PLAN))
    return review | {'resources': {k:v for k,v in resources.items() if k != 'library_SHA256'}}


def execute():
    require(OUT.resolve() == OUT and AUTH.resolve() == AUTH and AUTH.is_file(),
            'Explicit V51 authorization receipt required')
    authorization = load(AUTH)
    offline.next_admission(sha(offline.PLAN), 'A', authorization, available('A'))
    with execution_lock(env.PACKAGE/'autumn_execution_lock_local'):
        prior = None
        require(available('B'), 'B directory or claim already present')
        write_once(OUT/'startup_review.json', check())
        for role in ('A', 'B'):
            offline.next_admission(sha(offline.PLAN), role, authorization, available(role), prior)
            p = protocol(role)
            resources = resource_review(p)
            budget(resources, load(offline.PLAN))
            workdir = run_path(role)
            run_id = uuid.uuid4().hex
            write_once(OUT/f'claim_{role}.json', dict(
                role=role, run_id=run_id, created_UTC=now(), plan_sha256=p['plan_sha256'],
                input_sha256=p['input']['SHA256'], authorization_sha256=sha(AUTH),
                attempts_allowed=1, automatic_retry=False, unresolved_state='UNKNOWN'))
            try:
                workdir.mkdir()
                offline.safe_source(workdir, '../'+offline.SEEDS[('A','B').index(role)])
                print(f'{role} reserved {run_id}', flush=True)
                status = supervise(model_argv(p, run_id), workdir,
                    Limits(4770,16*GIB,20*GIB,5*GIB,256*MIB,total_output_bytes=5*GIB),
                    env=env.runtime_environment(), total_dir=workdir,
                    input_files={'input.inp':(ROOT/p['input']['path']).read_bytes()})
                require(status['qualification']=='PASS' and status['returncode']==0,
                        'MPI supervisor rejected run; preserve one-time claim')
                subprocess.run([sys.executable, '-B', str(ROOT/'scripts/verify_summer_spinup_execution_v51.py'), role],
                               cwd=ROOT, env=env.runtime_environment(), check=True)
                prior = load(workdir/'engineering_receipt.json')
                require(prior['engineering']=='PASS' and prior['run_id']==run_id, 'Engineering receipt mismatch')
                write_once(OUT/f'engineering_{role}.json', prior)
                print(f'{role} ENGINEERING_PASS {run_id}', flush=True)
            except BaseException as failure:
                write_once(OUT/f'failure_{role}.json', dict(run_id=run_id, UTC=now(),
                           failure=repr(failure), retry=False))
                raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-only', action='store_true')
    mode.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.execute:
        execute()
    else:
        import json
        print(json.dumps(check(), indent=2))


if __name__ == '__main__':
    main()
