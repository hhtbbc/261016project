"""Trusted preparation. No generic CDF density reads and no real evaluation."""
import csv
from datetime import datetime, timezone
import io
import json
import math
from pathlib import Path
import struct
import subprocess

from cdflib import CDF, cdfepoch
import numpy as np

from build_non_target_horizon_index_v56 import ROOT, V37, HOUR, identity, iso, pin, sha, utc

OUT = ROOT / 'experiments/thermosphere_real_development_v57'
LOCAL = OUT / 'inputs_local'
FOLDERS = {
    '2021-03-23': 'causal_density_latitude_v1',
    '2022-03-23': 'causal_density_latitude_v1',
    '2021-03-24': 'swarm_tiegcm_2021_spinup_observation_v1',
    '2022-03-24': 'swarm_tiegcm_2022_observation_v1',
    '2021-03-25': 'causal_density_new_date_validation_v1',
    '2022-03-25': 'tiegcm_2022_mar25_preparation_v1',
    '2021-09-23': 'thermosphere_autumn_data_acquisition_v21',
    '2022-09-23': 'thermosphere_autumn_data_acquisition_v21',
}
BASE = '5c010ee32ebc8bad1e9d79669ef27ec7dece4780'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def source(day):
    compact = day.replace('-', '')
    path = ROOT / 'data/raw' / FOLDERS[day] / f'SW_OPER_DNSAPOD_2__{compact}T000000_{compact}T235930_0301.cdf'
    require(path.resolve() == path and path.is_file(), 'Unsafe or missing CDF')
    return path


def bounded_density(cdf, fd, first, stop, allowed):
    """Only direct reads of selected uncompressed CDF3 scalar VVR records."""
    require((first, stop) == allowed and 0 <= first < stop <= 2880, 'Outside authorized history window')
    info = cdf.cdf_info()
    vdr = cdf.vdr_info('density')
    require(cdf.cdfversion == 3 and not info.Compressed and info.Encoding == 6 and
            vdr.data_type == 45 and vdr.num_elements == 1 and vdr.num_dims == vdr.sparse == 0 and
            vdr.record_vary and vdr.max_rec == 2879 and not vdr.compression_bool and
            cdf.varattsget('density').get('UNITS') == 'kg/m3', 'Unsupported CDF density layout')
    offsets, starts, ends = cdf._read_vxrs(vdr.head_vxr, [], [], [])
    payload = bytearray()
    next_record = first
    reads = []
    for offset, begin, end in zip(offsets, starts, ends):
        lo, hi = max(first, begin), min(stop, end + 1)
        if lo >= hi:
            continue
        fd.seek(offset)
        size, kind = struct.unpack('>QI', fd.read(12))
        require(kind == 7 and size == 12 + 8 * (end - begin + 1) and lo == next_record,
                'Unexpected VVR header or noncontiguous record coverage')
        byte_offset = offset + 12 + 8 * (lo - begin)
        fd.seek(byte_offset)
        content = fd.read(8 * (hi - lo))
        require(len(content) == 8 * (hi - lo), 'Truncated density records')
        payload.extend(content)
        reads.append(dict(first_record=lo, exclusive_end_record=hi, byte_offset=byte_offset, bytes=len(content)))
        next_record = hi
    require(next_record == stop, 'Incomplete history')
    return np.frombuffer(payload, dtype='<f8'), reads


def table(path, rows):
    with path.open('x', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def jsonout(path, obj):
    with path.open('x') as out:
        json.dump(obj, out, indent=2, allow_nan=False)
        out.write('\n')


def worker(jail, marker=None):
    args = [str(LOCAL / 'worker'), str(jail)]
    if marker:
        args.append(str(marker))
    audit = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           env={'LC_ALL': 'C'}, close_fds=True, timeout=10, check=True)
    lines = audit.stdout.splitlines()
    forecasts = [x.split(',') for x in lines[-3:]]
    require([int(x[0]) for x in forecasts] == [1, 3, 6], 'Unexpected worker result')
    return forecasts, lines[:-3]


def jail_at(path, anchors):
    path.mkdir(mode=0o755)
    file = path / 'anchors.txt'
    with file.open('x') as out:
        out.write(' '.join(format(float(x), '.17g') for x in anchors) + '\n')
    file.chmod(0o444)
    path.chmod(0o555)
    return file


def synthetic():
    folder = LOCAL / 'synthetic'
    folder.mkdir()
    outside = folder / 'future.csv'
    synthetic_jail = folder / 'jail'
    anchors = [1e-12, 1.1e-12]
    jail_at(synthetic_jail, anchors)
    synthetic_jail.chmod(0o755)
    (synthetic_jail / 'escape').symlink_to(outside)
    synthetic_jail.chmod(0o555)
    outside.write_text('1.3e-12\n1.5e-12\n1.8e-12\n')
    original_sha = sha(outside)
    before, log = worker(synthetic_jail, outside)
    truth = [float(x) for x in outside.read_text().splitlines()]
    outside.write_text('99\n-40\n300\n')
    after, new_log = worker(synthetic_jail, outside)
    require(before == after and log == new_log and sha(outside) != original_sha, 'Poison isolation failed')
    scores = []
    for forecast, expected in zip(before, truth):
        for method, value in zip(('Persistence','TwoFrameLinear'), forecast[1:]):
            error = float(value) - expected
            scores.append(dict(role='SYNTHETIC_ONLY', horizon_hours=int(forecast[0]), method=method,
                n=1, unit='kg/m3', MAE=abs(error), RMSE=abs(error), Bias=error,
                relative_RMSE=abs(error)/expected))
    table(OUT / 'synthetic_metrics.csv', scores)
    jsonout(OUT / 'isolation.json', dict(probes=log, poison_predictions_identical=True,
        before_label_SHA256=original_sha, after_label_SHA256=sha(outside),
        isolation='chroot + uid/gid 65534 + no_new_privs + seccomp syscall allowlist',
        outside_open_probe_names=['absolute future','parent future','parent traversal future','absolute symlink',
                                  'inherited fd proc path','other process proc root']))


def main():
    require(OUT.resolve() == OUT and not LOCAL.exists() and not LOCAL.is_symlink(), 'Unclean output')
    protocol = pin(V37)
    core = protocol['V20_core']
    require((core['cutoffs'],core['history_hours'],core['future_hours']) == ([6,18],3,[1,3,6]), 'V37 clock changed')
    roles = {r['date']: r for r in protocol['roles']['dates'] if r['role'] == 'DEVELOPMENT_SOURCE'}
    require(set(roles) == set(FOLDERS) and all(r['cutoff_history_density_access'] and
                  not r['future_density_access'] for r in roles.values()), 'V37 role changed')
    LOCAL.mkdir(mode=0o755)
    temp = LOCAL / 'compiler_tmp'
    temp.mkdir()
    worker_src = ROOT/'scripts/swarm_history_worker_v57.c'
    subprocess.run(['/usr/bin/gcc','-O2','-Wall','-Wextra','-Werror','-static',str(worker_src),
                    '-o',str(LOCAL/'worker')], check=True, env={'TMPDIR':str(temp),'PATH':'/usr/bin:/bin'})
    synthetic()
    receipt = subprocess.check_output(['git','grep','-h','-E','[a-f0-9]{64}',BASE,'--','experiments'],
                                      cwd=ROOT)
    availability, windows, predictions = [], [], []
    for day in sorted(FOLDERS):
        path = source(day)
        digest = sha(path)
        require(digest.encode() in receipt, 'CDF SHA absent from prior Git receipts: '+day)
        cdf = CDF(path)
        require(cdf.globalattsget()['TITLE'] == [path.stem], 'CDF product identity mismatch')
        elapsed = cdfepoch.to_datetime(cdf.varget('time')).astype('datetime64[ns]')
        beginning = np.datetime64(day,'ns')
        require(np.array_equal(elapsed, beginning + np.arange(2880)*np.timedelta64(30,'s')), 'UTC grid mismatch')
        flags = cdf.varget('validity_flag')
        require(flags.shape == (2880,) and set(flags).issubset({0,1}), 'Unexpected quality flags')
        availability.append(dict(day=day, CDF=path.relative_to(ROOT), source_SHA256=digest,
            bytes=path.stat().st_size, UTC_first=day+'T00:00:00Z', UTC_last=day+'T23:59:30Z',
            role='DEVELOPMENT_SOURCE', history_density='AUTHORIZED', future_density='SEALED',
            model_density_used=False, existing_aggregate_allowed=roles[day]['already_scored_future_aggregate_join']))
        intervals = []
        fill = float(cdf.varattsget('density')['FILLVAL'])
        for hour in core['cutoffs']:
            cutoff = utc(f'{day}T{hour:02d}:00:00Z')
            start = cutoff - 3*HOUR
            intervals.append((start, cutoff))
            first, stop = int((start.hour)*120), hour*120
            with path.open('rb', buffering=0) as raw:
                values, reads = bounded_density(cdf, raw, first, stop, (first, stop))
            good = (flags[first:stop]==0) & np.isfinite(values) & (values>0) & (values<fill)
            name = f'{day}_{hour:02d}Z'
            history_file = LOCAL / f'{name}_history.csv'
            payload = io.StringIO(newline='')
            writer = csv.writer(payload)
            writer.writerow(['UTC','density_kg_m3','validity_flag','valid'])
            for dt,value,flag,valid in zip(elapsed[first:stop],values,flags[first:stop],good):
                writer.writerow([np.datetime_as_string(dt,unit='s')+'Z', value,int(flag),int(valid)])
            with history_file.open('x') as out:
                out.write(payload.getvalue())
            history_file.chmod(0o444)
            history_sha = sha(history_file)
            anchor_indices = [120,240]  # exactly cutoff minus two and one hour
            require(all(good[i] for i in anchor_indices), 'Missing valid hourly anchors: '+name)
            anchor_file = jail_at(LOCAL / name, values[anchor_indices])
            forecast, log = worker(anchor_file.parent)
            require(not log, 'Unexpected real worker output')
            windows.append(dict(name=name, source_SHA256=digest, history_SHA256=history_sha,
                input_SHA256=sha(anchor_file), start=iso(start), stop_exclusive=iso(cutoff), n=len(values),
                valid_n=int(good.sum()), reads=reads, allowed_density_field='density',
                forbidden_fields=['density_orbitmean','future_density','global_statistics']))
            generated = iso(datetime.now(timezone.utc))
            for lead, persistence, linear in forecast:
                target = iso(cutoff+int(lead)*HOUR)
                sample = identity(('V57_SWARM_HISTORY_ONLY',digest,iso(cutoff),int(lead),target))
                for method, raw_prediction in [('Persistence',persistence),('TwoFrameLinear',linear)]:
                    pred = float(raw_prediction)
                    predictions.append(dict(sample_id=sample,dataset_role='DEVELOPMENT_SOURCE',
                        split_identity='DEVELOPMENT_DIAGNOSTIC_NO_TRAIN_VALIDATION_ASSIGNMENT',
                        source_SHA256=digest,input_SHA256=sha(anchor_file),history_SHA256=history_sha,
                        history_start_UTC=iso(start),cutoff_UTC=iso(cutoff),target_UTC=target,
                        horizon_hours=int(lead),method=method,density_kg_m3=pred,generated_UTC=generated,
                        valid=math.isfinite(pred) and pred>0,target_status='SEALED'))
        require(intervals[0][1] <= intervals[1][0], 'Overlapping histories')
        require(sha(path) == digest, 'Source changed during preparation')
    table(OUT/'availability.csv', availability)
    table(OUT/'predictions.csv', predictions)
    jsonout(OUT/'windows.json', windows)


if __name__ == '__main__':
    main()
