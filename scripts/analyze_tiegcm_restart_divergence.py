"""Read-only first-divergence bounds; never compile, launch, or repair a model."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import csv
import hashlib
import json
import re
import resource
import sys
import time

import numpy as np
from netCDF4 import Dataset, num2date

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from atmosphere.restart_validation import REQUIRED
from atmosphere.tiegcm_drivers import GpiDriver

SUITE = ROOT / 'experiments/tiegcm_runtime_restart_audit_v1'
OUT = ROOT / 'results/tiegcm_restart_divergence_v2'


def sha(path):
    path = Path(path).resolve()
    path.relative_to(ROOT)
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 * 1024**2), b''):
            h.update(block)
    return h.hexdigest()


def utc_record(n, i):
    """Require independent CF-time and year/DOY/hour/minute agreement."""
    year = int(n['year'][i])
    day, hour, minute = map(int, n['mtime'][i])
    expected = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(
        days=day - 1, hours=hour, minutes=minute)
    cf = num2date(n['time'][i], n['time'].units,
                 calendar=getattr(n['time'], 'calendar', 'standard'))
    if (cf.year, cf.month, cf.day, cf.hour, cf.minute, cf.second) != (
            expected.year, expected.month, expected.day, hour, minute, 0):
        raise ValueError('CF/calendar clock mismatch')
    return expected.isoformat()


def read_valid(v, i):
    v.set_auto_mask(False)
    a = np.asarray(v[i], dtype=np.float64)
    mask = np.abs(a) > 1e30
    for key in ('_FillValue', 'missing_value'):
        if key in v.ncattrs():
            mask |= a == v.getncattr(key)
    if not np.isfinite(a).all():
        raise ValueError('Nonfinite stored values')
    return a, mask


def metrics(a, b, ma, mb, rule):
    if a.shape != b.shape or ma.shape != a.shape or mb.shape != b.shape:
        raise ValueError('Array/mask shape mismatch')
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('Nonfinite input')
    valid = ~(ma | mb)
    if not valid.any():
        raise ValueError('No valid values')
    x, y = a[valid] * rule['scale_to_SI'], b[valid] * rule['scale_to_SI']
    d = y - x
    tol = rule['atol_SI'] + rule['rtol'] * np.maximum(abs(x), abs(y))
    ratios = np.divide(abs(d), tol, out=np.where(d == 0, 0., np.inf), where=tol > 0)
    nonzero = x != 0
    return dict(max_abs_SI=float(abs(d).max()), rms_SI=float(np.sqrt(np.mean(d*d))),
                max_relative=float(np.max(abs(d[nonzero] / x[nonzero]))) if nonzero.any() else None,
                max_normalized=float(ratios.max()),
                valid_points=int(valid.sum()), mask_mismatch=int((ma != mb).sum()),
                exact=bool(np.array_equal(a, b) and np.array_equal(ma, mb)),
                passed=bool((ratios <= 1).all() and np.array_equal(ma, mb)))


def compare(paths, ia, ib, variables, rules, tag):
    rows = []
    with Dataset(paths[0]) as a, Dataset(paths[1]) as b:
        epoch = utc_record(a, ia)
        if epoch != utc_record(b, ib):
            raise ValueError('Cannot compare different UTC epochs')
        for coord in ('lat', 'lon', 'lev', 'ilev', 'mlat', 'mlon', 'mlev', 'imlev'):
            np.testing.assert_array_equal(a[coord][:], b[coord][:])
        for k in variables:
            va, vb = a[k], b[k]
            if va.dimensions != vb.dimensions or va.dtype != vb.dtype or va.units != vb.units:
                raise ValueError(f'Schema mismatch: {k}')
            x, ma = read_valid(va, ia)
            y, mb = read_valid(vb, ib)
            rule = dict(rules[k])
            # Existing frozen policy: float32 output uses rtol=1e-6.
            if va.dtype == np.dtype('float32'):
                rule['rtol'] = 1e-6
            rows.append(dict(comparison=tag, UTC=epoch, variable=k,
                             SI_unit=rule['SI_unit'], **metrics(x, y, ma, mb, rule)))
    return rows


def write_json(path, value):
    path.resolve().relative_to(ROOT)
    with path.open('x') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')


def main():
    started = time.monotonic()
    OUT.resolve().relative_to(ROOT)
    if OUT.exists():
        raise FileExistsError('Independent result tag already exists; never overwrite')
    OUT.mkdir()
    protected = json.loads((SUITE / 'protected_files.json').read_text())
    changed = [p for p, h in protected.items() if sha(ROOT / p) != h]
    if changed:
        raise ValueError(f'Historical integrity failed: {changed}')
    rules = json.loads((SUITE / 'frozen_comparison_rules.json').read_text())
    # Frozen JSON enumerates PRIMARY only. Inherit the existing qualified
    # analyzer's secondary unit policy, without loosening any tolerance.
    rules['N2'] = dict(rules['O1'])
    rules['ZG'] = dict(rules['Z'])
    rules['DEN'] = dict(native_unit='g/cm3', scale_to_SI=1000.,
                        atol_SI=1e-25, rtol=1e-6, SI_unit='kg/m3')
    driver = GpiDriver(ROOT / 'data/processed/tiegcm_2021_spinup_14day_v1/gpi_2021_14day.nc')
    records, logs, ledger = [], [], {}
    for stage in ('continuous', 'segment', 'resumed'):
        logpath = ROOT / f'logs/tiegcm_runtime_restart_audit_v1_{stage}.log'
        text = logpath.read_text()
        ledger[str(logpath.relative_to(ROOT))] = sha(logpath)
        logged = re.findall(r'GPI run: mtime=\s*(\d+)\s+(\d+)\s+(\d+)\s+power=\s*([\d.]+)\s+ctpoten=\s*([\d.]+)\s+f107=\s*([\d.]+)\s+f107a=\s*([\d.]+)', text)
        for day, hour, minute, power, potential, f107, f107a in logged:
            t = tuple(map(int, (day, hour, minute)))
            expected = driver.at(2021000 + t[0], t[1]*3600 + t[2]*60)
            error = max(abs(float(v) - expected[k]) for k, v in zip(
                ('hpower', 'ctpoten', 'f107d', 'f107a'), (power, potential, f107, f107a)))
            if error > .0005000001:
                raise ValueError('Rounded minute driver log disagrees')
            logs.append(dict(stage=stage, day=t[0], hour=t[1], minute=t[2], max_print_error=error))
        if not logged:
            raise ValueError('No driver log')
        for kind in ('primary', 'secondary'):
            path = SUITE / stage / f'{kind}.nc'
            ledger[str(path.relative_to(ROOT))] = sha(path)
            with Dataset(path) as n:
                for i in range(len(n.dimensions['time'])):
                    epoch = utc_record(n, i)
                    t = tuple(map(int, n['mtime'][i]))
                    expected = driver.at(2021000 + t[0], t[1]*3600 + t[2]*60)
                    err = max(abs(float(n[k][i]) - v) for k, v in expected.items())
                    if err > 1e-10:
                        raise ValueError('Full precision driver mismatch')
                    records.append(dict(stage=stage, kind=kind, record=i, UTC=epoch,
                                        iter=int(n['iter'][i]) if 'iter' in n.variables else None,
                                        driver_max_error=err))
    pairs = [
        ('prefix_at_0010', 'continuous', 'segment', 'primary', 1, 1, REQUIRED),
        ('saved_checkpoint_preserved_not_RAM', 'segment', 'resumed', 'primary', 1, 1, REQUIRED),
        ('endpoint_primary', 'continuous', 'resumed', 'primary', 2, 2, REQUIRED),
        ('endpoint_secondary', 'continuous', 'resumed', 'secondary', 1, 0,
         ('DEN', 'ZG', 'TN', 'UN', 'VN', 'O1', 'O2', 'N2', 'HE'))]
    rows = []
    for tag, a, b, kind, ia, ib, names in pairs:
        rows.extend(compare([SUITE/a/f'{kind}.nc', SUITE/b/f'{kind}.nc'], ia, ib, names, rules, tag))
    # Verify agreement with prior independently retained statistics; do not edit them.
    previous = json.loads((ROOT/'results/tiegcm_runtime_restart_audit_v1/comparison.json').read_text())
    for row in rows:
        if row['comparison'].startswith('endpoint_'):
            kind = row['comparison'].removeprefix('endpoint_')
            old = next(v for v in previous['rows'] if v['type'] == kind and v['variable'] == row['variable'])
            np.testing.assert_allclose(row['max_abs_SI'], old['max_absolute_error'], rtol=1e-14, atol=0)
            assert row['passed'] == old['passed']
    for name, data in (('field_comparison.csv', rows), ('clock_records.csv', records), ('minute_drivers.csv', logs)):
        with (OUT/name).open('x', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator='\n')
            w.writeheader(); w.writerows(data)
    src = ROOT/'third_party/TIEGCM2.0/src'
    source_names = ('tgcm.F','rdsource.F','advance.F','pdynamo.F','fields.F','esmf.F','gswm.F','lbc.F','gpi.F','comp.F','dynamics.F','ionvel.F')
    for name in source_names:
        p = src/name
        ledger[str(p.relative_to(ROOT))] = sha(p)
    source_index = []
    for name in source_names:
        for line, value in enumerate((src/name).read_text().splitlines(), 1):
            if re.search(r'istep\s*==\s*1|call (readsource|define_phim3d|prepare_phig3d|pefield|pdynamo|dynamics|init_lbc)|istep = 0|phim3d = 0\.|ephi3d = 0\.|elam3d = 0\.|emz3d = 0\.', value):
                source_index.append(dict(file=name, line=line, text=value.strip()))
    with (OUT/'source_control_flow.csv').open('x', newline='') as f:
        w=csv.DictWriter(f, fieldnames=['file','line','text'], lineterminator='\n');w.writeheader();w.writerows(source_index)
    summary = dict(tag=OUT.name, new_model_launches=0, new_model_steps=0,
                   protected_verified=len(protected), changed=changed,
                   recomputed_rows=len(rows), clock_records=len(records), minute_log_records=len(logs),
                   prefix_numeric_pass=all(r['passed'] for r in rows if r['comparison']=='prefix_at_0010'),
                   saved_34_exact=all(r['exact'] for r in rows if r['comparison']=='saved_checkpoint_preserved_not_RAM'),
                   endpoint_primary_failed=sum(not r['passed'] for r in rows if r['comparison']=='endpoint_primary'),
                   endpoint_secondary_failed=sum(not r['passed'] for r in rows if r['comparison']=='endpoint_secondary'),
                   first_restart_specific_divergence='UNOBSERVED: after disk checkpoint at 00:10, by endpoint 00:20; RAM read/init/first-step unresolved',
                   decision='B: continuous integrations; restart remains isolated engineering gate',
                   wall_s=time.monotonic()-started, peak_process_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                   no_physical_patch=True, no_remote_sync=True)
    write_json(OUT/'audit.json', summary)
    write_json(OUT/'inputs_sha256.json', ledger)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
