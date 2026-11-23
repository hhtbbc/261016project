"""Stream the V24 release volumes independently of NetCDF parsing."""
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import time

ROOT = Path(__file__).resolve().parents[1]
V24 = ROOT / 'experiments/thermosphere_autumn_2021_formal_run_v24'
BASE = ROOT / 'experiments/thermosphere_autumn_mareqx_config_v23/2021'
RUN = BASE / 'actual_run'
OUT = ROOT / 'experiments/thermosphere_autumn_2021_postrun_closure_v26'
MANIFEST = V24 / 'model_output_manifest.csv'
MANIFEST_SHA = '8b44a39cc94962a99caee875451f7a4597ca9052864b6f92d11261b9e725a056'
TOTAL = 3371588992


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write_once(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def stream_sha(path):
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size


def manifest_rows(path=MANIFEST):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def scan(run, entries, total):
    start = time.monotonic()
    expected = {row['file'] for row in entries}
    require(len(expected) == len(entries) and all(
        re.fullmatch(r'(primary|secondary)_\d{3}\.nc', name) for name in expected
    ), 'Malformed or duplicate manifest file name')
    actual = {file.name for file in run.glob('*.nc')}
    rows = []
    for entry in entries:
        path = run / entry['file']
        row = dict(file=path.name, expected_SHA256=entry['SHA256'],
                   expected_bytes=int(entry['bytes']), read_bytes=0, match=False)
        try:
            require(path.resolve(strict=True) == path, f'Symlink rejected: {path.name}')
            before = path.stat()
            digest, size = stream_sha(path)
            after = path.stat()
            row.update(actual_SHA256=digest, read_bytes=size,
                       actual_bytes=after.st_size, inode=after.st_ino,
                       device=after.st_dev, mtime_ns=after.st_mtime_ns,
                       ctime_ns=after.st_ctime_ns)
            row['match'] = (digest == row['expected_SHA256']
                            and size == row['expected_bytes'] == after.st_size
                            and (before.st_dev, before.st_ino, before.st_size,
                                 before.st_mtime_ns, before.st_ctime_ns)
                            == (after.st_dev, after.st_ino, after.st_size,
                                after.st_mtime_ns, after.st_ctime_ns))
        except (OSError, ValueError) as error:
            row['error'] = str(error)
        rows.append(row)
    read_bytes = sum(row['read_bytes'] for row in rows)
    return dict(files=rows, read_bytes=read_bytes, file_count=len(actual),
                missing=sorted(expected - actual), extra=sorted(actual - expected),
                expected_bytes=total,
                V24_33_NETCDF_SHA_VERIFIED=(expected == actual and read_bytes == total
                                           and all(row['match'] for row in rows)),
                wall_s=time.monotonic() - start, CPU_s=time.process_time(),
                peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def main():
    require(OUT.resolve() == OUT and RUN.resolve() == RUN, 'Unexpected project path')
    require(stream_sha(MANIFEST)[0] == MANIFEST_SHA, 'Published V24 manifest changed')
    entries = manifest_rows()
    require(len(entries) == 33 and sum(int(row['bytes']) for row in entries) == TOTAL,
            'Wrong published inventory')
    OUT.mkdir(exist_ok=False)
    result = scan(RUN, entries, TOTAL)
    write_once(OUT / 'sha_verification.json', result)
    print({key: value for key, value in result.items() if key != 'files'})
    return 0 if result['V24_33_NETCDF_SHA_VERIFIED'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
