"""CPU-only execution overlay for the frozen 2022 autumn experiment."""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import uuid

from audit_tiegcm_autumn_v26 import (
    BASE as BASE_2021, OLD_FAIL, ROOT, RUN as RUN_2021, RUN_ID as V26_ID, V24,
    binding, historical_evidence, load, manifest_rows, require, sha, write_once,
)
from runtime import tiegcm_autumn_execution as old
from runtime.supervisor import Limits, supervise

FOLDER = old.PACKAGE / '2022'
RUN = FOLDER / 'actual_run'
OUT = ROOT / 'experiments/thermosphere_autumn_2022_execution_preparation_v27'
CLAIM_FILE = FOLDER / 'execution_claim_local.json'
AUDIT_DIR = OUT / 'postrun_v27_local'
RELEASE = OUT / 'execution_release.json'
V26 = ROOT / 'experiments/thermosphere_autumn_2021_postrun_closure_v26'
V23_RELEASE = old.PACKAGE / 'execution_release.json'
V24_RESOURCES = V24 / 'preflight.json'
V24_RESOURCES_SHA = '07af5063cc6d2ec2082b920990b37aac31ec4526bf6a4cd8595330434171e703'
FIXED_PINS = {
    V26 / 'closure_release.json': '8ffddfbe4da3ae4dc33947b94d082d4e7796adde2532114df9b59cb755308774',
    ROOT / 'reports/THERMOSPHERE_AUTUMN_2021_POSTRUN_CLOSURE_V26.md': 'a9ecbf027bbc850c11bc732ed9d3c2d7976e6d50f4eb0773db81ec0284a79c7b',
    V24 / 'result_final.json': 'db7861d1efc6a27d3a34851af18fe4007ef442d755fe530f5274ed142d32376e',
    V24 / 'model_output_manifest.csv': '8b44a39cc94962a99caee875451f7a4597ca9052864b6f92d11261b9e725a056',
    OLD_FAIL: '3859b363b92f6f5cfb3d10a125db8d83356cfe91d557f72f6b64ad285b998271',
}
ASSET_SHA = {
    'input': 'f01f3913f9f15b79132fe8f824c7ce9f5ce7c4c1b6591c9622be184ee7b0fa49',
    'GPI': '7d43db220fe7fbaded6b2182db8db32ee09cedf99dc5760815824ccf8298ebb2',
    'source': 'a710e39b9b992cab55b839e1ab11298305e02d0205135efa5a93254cb30fd4e7',
    'executable': 'f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776',
    'mpirun': '7b6c839e5d90310bf741efe3f9cbba68460083c74721513d5f3697b158119639',
}
AUDIT_SCRIPT = ROOT / 'scripts/audit_tiegcm_autumn_2022_v27.py'


def v26_bindings():
    for path, digest in FIXED_PINS.items():
        binding(path, digest)
    closure = load(V26 / 'closure_release.json')
    for name, digest in closure['SHA256'].items():
        path = ROOT / name
        require(path.is_relative_to(V26), 'Evidence outside V26 package')
        binding(path, digest)
    return closure


def verify_v26_fields(closure, final, primary, independent, receipt, history, original, manifest):
    require(closure['V26_POSTRUN_VERIFICATION'] == final['V26_POSTRUN_VERIFICATION']
            == 'ENGINEERING_PASS' and primary['overall'] == 'PASS'
            and independent['independent_raw_checks'] == 'PASS'
            and final['V24_33_NETCDF_SHA_VERIFIED'] is True
            and final['main_attempts'] == closure['main_attempts'] == 1,
            'Incomplete V26 engineering closure')
    identity = independent['identity']
    require(closure['run_id'] == primary['run_id'] == identity['run_id']
            == history['run_id'] == original['run_id'] == V26_ID,
            'V26 run_id mismatch')
    require(original['overall'] == 'FAIL' and history['overall'] == 'ENGINEERING_FAIL'
            and final['V24_ORIGINAL_ENGINEERING_STATUS'] == 'FAIL',
            'Historical V24 verdict mismatch')
    checks = primary['checks']
    require(identity['actual_steps'] == history['steps'] == 23040
            and identity['actual_final_UTC'] == '2021-09-25T00:00:00Z'
            and identity['parent_returncode'] == checks['supervision']['returncode'] == 0
            and identity['direct_wait_journal_verified'] is True
            and [row['rank'] for row in identity['ranks']] == list(range(4))
            and [row['returncode'] for row in identity['ranks']] == [0]*4
            and [row['returncode'] for row in checks['MPI_rank_exits']['ranks']] == [0]*4
            and [row['final_step'] for row in checks['step_logs']] == [23040]*4,
            'Incomplete V26 direct-wait or step evidence')
    expected = {row['file']: (row['SHA256'], int(row['bytes'])) for row in manifest}
    require(len(expected) == len(manifest) == 33
            and sum(size for _,size in expected.values()) == 3371588992
            and receipt['V24_33_NETCDF_SHA_VERIFIED'] is True
            and receipt['file_count'] == len(receipt['files']) == 33
            and receipt['read_bytes'] == 3371588992
            and all(row['match'] for row in receipt['files'])
            and {row['file']: (row['actual_SHA256'], row['actual_bytes'])
                 for row in receipt['files']} == expected,
            'Incomplete V26 volume SHA evidence')
    for evidence in (checks['output_files'], independent['outputs']):
        require((evidence['primary_records'], evidence['secondary_records']) == (17,384)
                and len(evidence['files']) == 33
                and {row['file']: (row['SHA256'], row['bytes']) for row in evidence['files']} == expected,
                'V26 reviewed output identity mismatch')
    require(checks['target_observation_queries']['success'] ==
            independent['independent_queries']['success'] == 2880,
            'V26 coverage evidence mismatch')


def verify_v26():
    closure = v26_bindings()
    verify_v26_fields(
        closure, load(V26 / 'independent_recovery_once/result.json'),
        load(V26 / 'formal_once/main_acceptance.json'),
        load(V26 / 'independent_recovery_once/independent_review.json'),
        load(V26 / 'sha_verification.json'), load(V24 / 'result_final.json'),
        load(OLD_FAIL), manifest_rows(),
    )
    p = load(BASE_2021 / 'launch_protocol.json')
    historical_evidence(p)
    return closure


def verify_physics(p):
    require(p['year'] == 2022 and ROOT / p['cwd'] == RUN and RUN != RUN_2021
            and FOLDER.resolve(strict=True) == FOLDER, 'Wrong year or output directory')
    require(p['limits'] == dict(model_wall_s=4800, stop_trigger_s=4770, cleanup_reserve_s=30,
                               RSS_bytes=16*2**30, output_bytes=5*2**30,
                               start_free_bytes=25*2**30, run_free_floor_bytes=20*2**30,
                               postrun_wall_s=600, postrun_RSS_bytes=4*2**30, launches=1, retries=0),
            'Unexpected frozen run limits')
    require(p['step_s'] == 60 and p['target_date'] == '2022-09-23'
            and '20220923T000000' in Path(p['observation']['path']).name,
            'Wrong calendar or observation binding')
    for name, expected in ASSET_SHA.items():
        item = p[name]
        require(item['SHA256'] == expected, f'Wrong frozen {name} SHA')
        binding(ROOT / item['path'], expected)


def preflight():
    binding(V23_RELEASE, '3e6db19a1ff954e3df2b2c4d6b1050a527e5ac269b9597b87ea2b5200133860f')
    verify_v26()
    p = old.verify_package(2022)
    verify_physics(p)
    return p


def evidence_pins():
    return {**{str(path.relative_to(ROOT)): digest for path, digest in FIXED_PINS.items()},
            **load(V26 / 'closure_release.json')['SHA256']}


def check_pin_set(release):
    expected = {'scripts/execute_tiegcm_autumn_2022_v27.py',
                'scripts/audit_tiegcm_autumn_2022_v27.py',
                'scripts/audit_tiegcm_autumn_v26.py', 'scripts/tiegcm_autumn_v26_sha.py',
                'src/runtime/supervisor.py', 'src/runtime/tiegcm_rank_exit.py',
                'src/runtime/readonly_audit_warning_channel.py',
                'src/atmosphere/tiegcm_mar25_acceptance.py'}
    require(release['year'] == 2022 and set(release['code_SHA256']) == expected,
            'Incomplete V27 code release')
    for name, digest in release['code_SHA256'].items():
        binding(ROOT / name, digest)


def verify_plan():
    require(RELEASE.resolve(strict=True) == RELEASE, 'V27 release path changed')
    release = load(RELEASE)
    check_pin_set(release)
    require(release['V26_SHA256'] == evidence_pins()
            and release['physical_SHA256'] == ASSET_SHA
            and release['model_libraries_SHA256'] == load(V24_RESOURCES)['resource']['library_SHA256'],
            'V27 release provenance mismatch')
    return preflight()


def resource_review(p):
    result = old.environment_review(p)
    binding(V24_RESOURCES, V24_RESOURCES_SHA)
    expected = load(V24_RESOURCES)['resource']['library_SHA256']
    require(result['library_SHA256'] == expected, 'V24 dynamic library SHA drift')
    require(result['MPI_version'] == 'mpirun (Open MPI) 5.0.8', 'MPI version drift')
    v1 = Path('/sys/fs/cgroup')
    if (v1 / 'cpu.max').exists():
        quota, period = (v1 / 'cpu.max').read_text().split()
        quota = -1 if quota == 'max' else int(quota)
        limit = (v1 / 'memory.max').read_text().strip()
        limit = None if limit == 'max' else int(limit)
        usage = int((v1 / 'memory.current').read_text())
    else:
        quota = int((v1 / 'cpu/cpu.cfs_quota_us').read_text())
        period = (v1 / 'cpu/cpu.cfs_period_us').read_text()
        limit = int((v1 / 'memory/memory.limit_in_bytes').read_text())
        usage = int((v1 / 'memory/memory.usage_in_bytes').read_text())
    cpus = min(result['CPU_affinity_count'], quota / int(period)) if quota >= 0 else result['CPU_affinity_count']
    memory = min(result['MemAvailable_bytes'], limit - usage) if limit is not None else result['MemAvailable_bytes']
    writable = os.access(FOLDER, os.W_OK | os.X_OK)
    result.update(cpu_equivalent=cpus, cgroup_memory_limit=limit, cgroup_memory_usage=usage,
                  effective_memory_available=memory, load_average=os.getloadavg(), writable=writable,
                  queue_clients=[tool for tool in ('sbatch','srun','qsub','bsub') if shutil.which(tool)],
                  resource_ready=result['resource_ready'] and cpus >= 4 and memory >= 16*2**30 and writable)
    return result


def ensure_unreserved(run, claim, audit_dir):
    require(not any(os.path.lexists(path) for path in (run, claim, audit_dir)),
            'V27 run already reserved or attempted; preserve evidence')


@contextlib.contextmanager
def execution_lock(path):
    # Share the existing V23 lock inode and never truncate or replace it.
    require(path.resolve(strict=True) == path, 'Unexpected autumn lock path')
    with path.open('r') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError('Another autumn execution owns the lock') from error
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def model_argv(p, run_id):
    return [str(ROOT / p['mpirun']['path']), '-np', '4', sys.executable,
            str(ROOT / 'src/runtime/tiegcm_rank_exit.py'), '--model',
            str(ROOT / p['executable']['path']), '--run-id', run_id,
            '--model-sha', p['executable']['SHA256'], '--input-sha', p['input']['SHA256']]


def execute(year, authorized=False, cpu_session_confirmed=False):
    require(year == 2022, 'Only 2022 is admitted')
    require(authorized is True, 'Explicit 2022 single-run authorization required')
    require(cpu_session_confirmed is True, 'Confirm approved CPU queue and sustained supervision')
    with execution_lock(old.PACKAGE / 'autumn_execution_lock_local'):
        ensure_unreserved(RUN, CLAIM_FILE, AUDIT_DIR)
        p = verify_plan()
        require(resource_review(p)['resource_ready'], 'Insufficient CPU-only resources')
        require(Path(sys.executable) == ROOT / '.venv310/bin/python', 'Use frozen Python entry')
        run_id = uuid.uuid4().hex
        require(run_id != V26_ID, 'Repeated historical run identity')
        env = old.runtime_environment()
        input_bytes = (ROOT / p['input']['path']).read_bytes()
        require(hashlib.sha256(input_bytes).hexdigest() == ASSET_SHA['input'], 'Staged input SHA drift')
        RUN.mkdir(exist_ok=False)
        write_once(CLAIM_FILE, dict(year=2022, run_id=run_id, attempts=1, automatic_retry=False,
                                    release_SHA256=sha(RELEASE)))
        model = supervise(model_argv(p, run_id), RUN,
                          Limits(4770, 16*2**30, 20*2**30, 5*2**30, 256*2**20,
                                 total_output_bytes=5*2**30),
                          env=env, total_dir=RUN, input_files={'input.inp': input_bytes})
        require(model['qualification'] == 'PASS' and model['returncode'] == 0,
                'Model exit failed or unknown; reservation retained')
        AUDIT_DIR.mkdir(exist_ok=False)
        audit = supervise([sys.executable, '-B', str(AUDIT_SCRIPT), '--run-id', run_id], AUDIT_DIR,
                          Limits(600, 4*2**30, 20*2**30, 150*2**20, 20*2**20,
                                 total_output_bytes=150*2**20),
                          env=env, total_dir=AUDIT_DIR)
        require(audit['qualification'] == 'PASS' and audit['returncode'] == 0,
                'Post-run audit failed or unknown; reservation retained')
        result = load(AUDIT_DIR / 'acceptance.json')
        require(result['overall'] == 'PASS' and result['run_id'] == run_id,
                'V27 primary acceptance failed')
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', required=True, type=int, choices=[2022])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--authorize-2022-single-16day-run', action='store_true')
    mode.add_argument('--check-only', action='store_true')
    parser.add_argument('--confirm-cpu-session', action='store_true')
    args = parser.parse_args()
    if args.check_only:
        ensure_unreserved(RUN, CLAIM_FILE, AUDIT_DIR)
        resources = resource_review(verify_plan())
        require(resources['resource_ready'], 'Insufficient CPU-only resources')
        print(json.dumps({key: value for key, value in resources.items() if key != 'library_SHA256'}))
        return
    result = execute(args.year, args.authorize_2022_single_16day_run, args.confirm_cpu_session)
    print(json.dumps(dict(overall=result['overall'], independent_review=result['independent_review'])))


if __name__ == '__main__':
    main()
