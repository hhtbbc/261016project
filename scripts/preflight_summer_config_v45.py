"""Offline summer candidate materialization and fail-closed preflight. No launcher."""
import argparse
import ctypes as C
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from netCDF4 import Dataset, num2date
from import_summer_handoff_v39 import inspect_seed
from atmosphere.restart_validation import check_source_clock, inspect_restart
from atmosphere.tiegcm_drivers import GpiDriver
from evaluation.shrinkage_unseen_gate_v37 import admit, REQUIREMENTS, StageReceipt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'experiments/thermosphere_summer_seed_policy_config_v45'
BASE = '6e5c574fcabd8a3a355a4db980dda7ea9604191e'
V27 = 'experiments/thermosphere_autumn_2022_execution_preparation_v27/execution_release.json'
V23 = 'experiments/thermosphere_autumn_mareqx_config_v23/execution_release.json'
V37 = 'experiments/thermosphere_shrinkage_unseen_prereg_v37/preregistered_protocol.json'
SEED = ('data/raw/thermosphere_summer_data_handoff_v39/accepted/'
        'tiegcm_res5.0_junsol_smax_prim.nc/tiegcm_res5.0_junsol_smax_prim.nc')
JUNSOL = 'baed93b59dee7f8e6355c8d0224bd2335cf355bd0d632c9d2327aa7d0227475e'
GPI = 'experiments/thermosphere_summer_gpi_candidate_v43/gpi_2022_summer_candidate_v43.nc'
DRIVER = 'd1e5cd2211a0ec6dd7e2c882341e3a2756626aa9ec4df74b8461ab4cc5d1a860'
RUN = 'experiments/thermosphere_summer_engineering_2022_future/actual_run'
SOURCE_CLOCK = [172, 0, 0]
START = datetime(2022, 6, 7, tzinfo=timezone.utc)
STOP = datetime(2022, 6, 23, tzinfo=timezone.utc)
SETTINGS = {'mpi': 4, 'omp': 1, 'gpu': 0, 'step': 60, 'steps': 23040,
            'output_directory': RUN, 'runtime': 'UNVERIFIED', 'policy': 'PENDING',
            'run_ready': False, 'wall_s': 4800, 'rss_gib': 16, 'output_gib': 5,
            'startup_free_gib': 25, 'running_free_gib': 20, 'retry': False}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    with Path(path).open('rb') as f:
        h = hashlib.sha256()
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
        return h.hexdigest()


def verify_hash(path, expected):
    need(digest(ROOT / path) == expected, f'SHA mismatch: {path}')


def pinned(path):
    data = (ROOT / path).read_bytes()
    need(data == subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT), path)
    return data


def history():
    counts = {}
    for v in range(37, 45):
        path, = ROOT.glob(f'experiments/thermosphere_*_v{v}/publication_SHA256.json')
        data = json.loads(pinned(path.relative_to(ROOT)))
        entries = data.get('published', data) | data.get('original_local_only', {})
        for name, sha in entries.items():
            verify_hash(name, sha)
        counts[f'V{v}'] = len(entries)
    return counts


def draft(template):
    replacements = {'LABEL': "'SUMMER JUNSOL 2022 OFFLINE CANDIDATE'",
                    'START_DAY': '158', 'SOURCE_START': '172 0 0', 'START': '158 0 0',
                    'STOP': '174 0 0', 'SECSTART': '158 1 0', 'SECSTOP': '174 0 0',
                    'SOURCE': f"'$PROJECTROOT/{SEED}'", 'GPI_NCFILE': f"'$PROJECTROOT/{GPI}'"}
    for key, value in replacements.items():
        template, count = re.subn(rf'(?m)^( +{key}\s*=).*$', rf'\g<1> {value}', template)
        need(count == 1, f'missing or duplicate template key {key}')
    return "\n".join(line.rstrip() for line in template.splitlines()) + "\n"


def settings_check(settings, environment, occupied):
    need(settings == SETTINGS, 'Configuration or authorization changed')
    need(environment.get('CUDA_VISIBLE_DEVICES') == '' and environment.get('OMP_NUM_THREADS') == '1',
         'Need CPU-only and OMP=1')
    path = ROOT / RUN
    need(path.resolve() == path and not occupied, 'Output path occupied or aliased')


def validate_namelist(text, expected):
    need(text == expected, 'Namelist differs from pinned seasonal transform')
    fields = dict(re.findall(r'(?m)^ +([A-Z_]+)\s*=\s*(.*)$', text))
    clock = lambda name: list(map(int, fields[name].split()))
    need(clock('SOURCE_START') == SOURCE_CLOCK, 'Incorrect native SOURCE_START')
    check_source_clock(clock('START'), clock('SOURCE_START'))
    need(int(fields['START_YEAR']) == START.year and int(fields['START_DAY']) == START.timetuple().tm_yday
         and clock('START') == [START.timetuple().tm_yday, 0, 0]
         and clock('STOP') == [STOP.timetuple().tm_yday, 0, 0]
         and clock('SECSTART') == [158, 1, 0] and clock('SECSTOP') == clock('STOP')
         and int(fields['STEP']) == 60 and (STOP - START).total_seconds() / 60 == 23040,
         'Calendar or step mismatch')
    need(len(re.findall(r"'primary_\d+\.nc'", fields['OUTPUT'])) == 17
         and len(re.findall(r"'secondary_\d+\.nc'", fields['SECOUT'])) == 16
         and fields['MXHIST_PRIM'] == '1' and fields['MXHIST_SECH'] == '24',
         'Incorrect output schedule')


def native_check(structure):
    need(structure['structure_complete'] and structure['record_available']
         and structure['available_mtime'] == [SOURCE_CLOCK], 'Required native state or clock absent')


def fortran_clock(library, path):
    """Use the legacy NetCDF-Fortran ABI also used by the model, without MPI."""
    lib = C.CDLL(str(library))
    name = os.fsencode(path)
    mode, ncid = C.c_int(0), C.c_int()
    need(lib.nf_open_(name, C.byref(mode), C.byref(ncid), C.c_size_t(len(name))) == 0,
         'NetCDF-Fortran open failed')
    values = {}
    try:
        for key, size in ((b'year', 1), (b'day', 1), (b'mtime', 3)):
            ident = C.c_int()
            result = (C.c_int * size)()
            need(lib.nf_inq_varid_(C.byref(ncid), key, C.byref(ident), C.c_size_t(len(key))) == 0
                 and lib.nf_get_var_int_(C.byref(ncid), C.byref(ident), result) == 0,
                 'NetCDF-Fortran integer read failed')
            values[key.decode()] = list(result)
    finally:
        need(lib.nf_close_(C.byref(ncid)) == 0, 'NetCDF-Fortran close failed')
    need(values == {'year': [2002], 'day': [172], 'mtime': SOURCE_CLOCK}, 'Fortran clock mismatch')
    return values


def resources():
    cg = Path('/sys/fs/cgroup')
    if (cg / 'cpu.max').is_file():
        q, p = (cg / 'cpu.max').read_text().split()
        limit = (cg / 'memory.max').read_text().strip()
        usage = int((cg / 'memory.current').read_text())
    else:
        q = (cg / 'cpu/cpu.cfs_quota_us').read_text().strip()
        p = (cg / 'cpu/cpu.cfs_period_us').read_text().strip()
        limit = (cg / 'memory/memory.limit_in_bytes').read_text().strip()
        usage = int((cg / 'memory/memory.usage_in_bytes').read_text())
    affinity = len(os.sched_getaffinity(0))
    available = int(re.search(r'^MemAvailable:\s+(\d+)', Path('/proc/meminfo').read_text(), re.M)[1]) * 1024
    cpus = affinity if q in ('max', '-1') else min(affinity, int(q) / int(p))
    memory = available if limit == 'max' else min(available, int(limit) - usage)
    disk = shutil.disk_usage(ROOT).free
    return {'cpu_equivalent': cpus, 'memory_available_bytes': memory, 'disk_free_bytes': disk,
            'snapshot_meets_capacity': cpus >= 4 and memory >= 16*2**30 and disk >= 25*2**30}


def refuse_run():
    raise ValueError('V45 offline candidate: policy pending, execution unauthorized')


def tests(template, expected, good_structure, environment):
    results = []
    def reject(name, fn):
        try:
            fn()
        except ValueError:
            results.append(name)
            return
        raise AssertionError(f'Unexpected acceptance: {name}')
    reject('junsol SHA drift', lambda: verify_hash(SEED, '0'*64))
    reject('GPI SHA drift', lambda: verify_hash(GPI, '0'*64))
    reject('SOURCE_START drift', lambda: native_check(good_structure | {'available_mtime': [[80, 0, 0]]}))
    reject('missing native state', lambda: native_check(good_structure | {'structure_complete': False}))
    reject('wrong 2022 calendar', lambda: validate_namelist(expected.replace('STOP = 174', 'STOP = 175'), expected))
    reject('old autumn input', lambda: validate_namelist(template, expected))
    for name, values in [('MPI', {'mpi': 8}), ('OMP', {'omp': 2}),
                         ('GPU', {'gpu': 1}), ('authorization', {'run_ready': True})]:
        reject(name, lambda: settings_check(SETTINGS | values, environment, False))
    reject('visible GPU', lambda: settings_check(SETTINGS, environment | {'CUDA_VISIBLE_DEVICES': '0'}, False))
    reject('output occupied', lambda: settings_check(SETTINGS, environment, True))
    reject('launch with pending policy', refuse_run)
    ev = dict.fromkeys(REQUIREMENTS['integration'], True)
    ev.update(same_season_2021_integration_verified=False)
    reject('2022 before 2021', lambda: admit('2022-06-21', 'integration',
        approved={('2022-06-21','integration')}, operation='CPU_SINGLE_MODEL', evidence=ev,
        predecessors=[StageReceipt('2022-06-21','identity','0'*64,'PASS')]))
    reject('2021 missing Fobs', lambda: admit('2021-06-21', 'integration',
        approved={('2021-06-21','integration')}, operation='CPU_SINGLE_MODEL',
        evidence=ev | {'GFZ_complete': False},
        predecessors=[StageReceipt('2021-06-21','identity','0'*64,'PASS')]))
    reject('unseen density decoding stage', lambda: admit('2022-06-21', 'score',
        approved=set(), operation='FUTURE_ONCE'))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write-candidate', action='store_true')
    mode.add_argument('--check-only', action='store_true')
    mode.add_argument('--request-run', action='store_true')
    args = parser.parse_args()
    if args.request_run:
        refuse_run()
    need(OUT.resolve() == OUT, 'Unsafe candidate location')
    histories = history()
    policy = json.loads(pinned(V37))
    need(policy['candidates'] == {'Raw': 0, 'Global': 1, 'ShrinkageHalf': .5}
         and policy['first_pair'] == ['2021-06-21', '2022-06-21'], 'V37 drift')
    v44 = json.loads(pinned('experiments/thermosphere_ncar_junsol_real_acceptance_v44/admission.json'))
    need(v44['state'] == 'V44_JUNSOL_ACCEPTED_VERIFIED' and not v44['official_publication_checksum_verified'],
         'Wrong seed provenance')
    v44_review = json.loads(pinned('experiments/thermosphere_ncar_junsol_real_acceptance_v44/v40_independent.json'))
    need(v44_review['real_junsol_native']['member_SHA256'] == JUNSOL, 'V44 independent receipt mismatch')
    v43 = json.loads(pinned('experiments/thermosphere_summer_gpi_candidate_v43/verification.json'))
    need(v43['numeric'] == 'GPI_NUMERIC_VERIFIED' and v43['sha256'] == DRIVER, 'V43 validation receipt mismatch')
    for p, sha in v43_sources().items():
        verify_hash(p, sha)
    verify_hash(SEED, JUNSOL)
    verify_hash(GPI, DRIVER)
    need((ROOT / SEED).resolve() == ROOT / SEED and (ROOT / SEED).stat().st_mode & 0o222 == 0,
         'Seed is not a read-only original')
    structure = inspect_restart(ROOT / SEED, SOURCE_CLOCK)
    native_check(structure)
    seed = inspect_seed(ROOT / SEED)
    need(seed['required_complete_states'] == 34 and seed['source_scalars']['f107d'] == [200.]
         and seed['source_scalars']['f107a'] == [200.], 'Native state contract')
    with Dataset(ROOT / SEED) as n:
        t = num2date(n['time'][0], n['time'].units)
        need(t.isoformat() == '2002-06-21T00:00:00', 'Native UTC mismatch')
    release = json.loads(pinned(V27))
    scientific = json.loads(pinned(V23))['scientific_asset_SHA256']
    elf = release['physical_paths']['executable']
    mpi = release['physical_paths']['mpirun']
    for key in ('executable', 'mpirun'):
        verify_hash(release['physical_paths'][key], release['physical_SHA256'][key])
    critical = {p: sha for p, sha in scientific.items() if p.startswith(('third_party/', 'configs/patches/', 'experiments/tiegcm2_apex2023_v1/', 'data/raw/tiegcm2_support/'))}
    for p, sha in critical.items():
        verify_hash(p, sha)
    dynamic = subprocess.check_output(['ldd', str(ROOT / elf)], text=True)
    need('not found' not in dynamic, 'Unresolved model library')
    libs = dict(re.findall(r'^\s*(\S+)\s+=>\s+(\/\S+)\s+', dynamic, re.M))
    for lib, sha in release['model_libraries_SHA256'].items():
        need(lib in libs and digest(libs[lib]) == sha, f'Library mismatch: {lib}')
    clock = fortran_clock(Path(libs['libnetcdff.so.7']), ROOT / SEED)
    mpi_version = subprocess.check_output([str(ROOT / mpi), '--version'], text=True).splitlines()[0]
    driver = GpiDriver(ROOT / GPI)
    need((driver.begin, driver.end) == (2022158, 2022174) and len(driver.days) == 21, 'GPI coverage')
    boundaries = {str(yd): driver.at(yd, 0) for yd in (2022158, 2022174)}
    template = pinned(release['physical_paths']['input']).decode()
    expected = draft(template)
    path = OUT / '2022_summer_offline.namelist.draft'
    occupied = any(os.path.lexists(p) for p in ((ROOT / RUN), (ROOT / RUN).parent / 'execution_claim.json'))
    settings_check(SETTINGS, os.environ, occupied)
    if args.write_candidate:
        with path.open('x') as f:
            f.write(expected)
    need(path.resolve() == path, 'Unsafe candidate file')
    validate_namelist(path.read_text(), expected)
    negatives = tests(template, expected, structure, dict(os.environ))
    print(json.dumps({'state': '2022_SUMMER_CONFIG_CANDIDATE_VERIFIED', 'settings': SETTINGS,
          'candidate_sha256': digest(path), 'checker_sha256': digest(__file__), 'historical': histories,
          'seed_sha256': JUNSOL, 'gpi_sha256': DRIVER, 'native_fortran_clock': clock, 'model_sha256': digest(ROOT / elf),
          'mpirun_sha256': digest(ROOT / mpi), 'mpi_version': mpi_version, 'library_count': len(release['model_libraries_SHA256']),
          'netcdff_sha256': digest(libs['libnetcdff.so.7']), 'critical_assets': critical,
          'resources': resources(), 'boundaries': boundaries, 'negative_tests': negatives,
          'model_executed': False, 'unseen_density_reads': 0}, indent=2, allow_nan=False))


def v43_sources():
    return json.loads(pinned('experiments/thermosphere_summer_gpi_candidate_v43/input_freeze.json'))['sources']


if __name__ == '__main__':
    main()
