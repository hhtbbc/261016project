"""V37-aligned UTC indexing. Development endpoints are not scoring windows."""
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'experiments/thermosphere_non_target_protocol_v56'
V53=ROOT/'experiments/thermosphere_swarm_summer_metadata_v53'
V37=ROOT/'experiments/thermosphere_shrinkage_unseen_prereg_v37/preregistered_protocol.json'
BASE='d526f4ca3dcc7b1a2f35f9a1d203d23fc5487fd1'
HOUR=timedelta(hours=1)


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):
            h.update(chunk)
    return h.hexdigest()


def pin(path):
    if path.read_bytes()!=subprocess.check_output(['git','show',f'{BASE}:{path.relative_to(ROOT)}'],cwd=ROOT):
        raise ValueError(f'Frozen file differs: {path}')
    return json.loads(path.read_text())


def utc(value):
    if not isinstance(value,str) or not value.endswith('Z'):
        raise ValueError('Require explicit UTC Z')
    t=datetime.fromisoformat(value[:-1]+'+00:00')
    if t.tzinfo!=timezone.utc:
        raise ValueError('Require UTC')
    return t


def iso(t):
    return t.isoformat(timespec='seconds').replace('+00:00','Z')


def identity(parts):
    return hashlib.sha256(json.dumps(list(parts),separators=(',',':')).encode()).hexdigest()


def grid(frames):
    parsed=[utc(x) for x in frames]
    if len(parsed)<2 or any(x.minute or x.second or x.microsecond for x in parsed):
        raise ValueError('Hourly UTC frames required')
    if any(b-a!=HOUR for a,b in zip(parsed,parsed[1:])):
        raise ValueError('Missing, repeated or unordered hour')
    return set(parsed)


def cutoff_check(t,core):
    if t.hour not in core['cutoffs'] or t.minute or t.second or t.microsecond:
        raise ValueError('Wrong V37 cutoff')


def build(frames,cutoffs,source,split,digest,core):
    timing=grid(frames)
    rows=[]
    if len(cutoffs)!=len(set(cutoffs)):
        raise ValueError('Repeated cutoff')
    for value in cutoffs:
        t=utc(value)
        cutoff_check(t,core)
        start=t-core['history_hours']*HOUR
        end=t
        history=[start+i*HOUR for i in range(core['history_hours'])]
        if not set(history)<=timing:
            raise ValueError('Incomplete cutoff history')
        for h in core['future_hours']:
            target=t+h*HOUR
            if target not in timing:
                raise ValueError('Target outside model time extent')
            rows.append(dict(sample_id=identity(('V56_SYNTHETIC_ENDPOINT',digest,source,split,value,h,iso(target))),
               dataset_role='SYNTHETIC_DEVELOPMENT_DIAGNOSTIC',source_identity=source,cutoff_UTC=value,
               horizon_hours=h,target_UTC=iso(target),allowed_history_end_UTC=iso(end),
               input_window_start_UTC=iso(start),input_window_end_UTC=iso(end),
               last_allowed_hourly_record_UTC=iso(history[-1]),target_status='SYNTHETIC_EVALUATOR_ONLY',
               access_policy='HISTORY_HALF_OPEN_NO_CUTOFF_OR_FUTURE_LABELS',
               source_SHA=digest,split_identity=split))
    return rows


def check_split(intervals):
    """Additional synthetic-only guard. Intervals are inclusive data supports."""
    values=list(intervals)
    for i,(split,first,last) in enumerate(values):
        if utc(last)<utc(first):
            raise ValueError('Invalid dataset support')
        for other,lo,hi in values[:i]:
            if other!=split and max(utc(first),utc(lo))<=min(utc(last),utc(hi)):
                raise ValueError('Cross-split temporal support collision')


def output(name,rows):
    path=OUT/name
    if path.resolve()!=path:
        raise ValueError('Unsafe output')
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def metadata_index(protocol):
    manifest=pin(V53/'publication_SHA256.json')
    draws=[]
    counts=[]
    for day in protocol['first_pair']:
        path=V53/f'metadata_{day[:4]}.csv'
        if sha(path)!=manifest[str(path.relative_to(ROOT))]:
            raise ValueError('V53 metadata hash changed')
        with path.open(newline='') as f:
            source=list(csv.DictReader(f))
        core=protocol['V20_core']
        base=utc(day+'T00:00:00Z')
        by_time={utc(r['UTC']):r for r in source}
        if sorted(by_time)!=[base+timedelta(seconds=30*i) for i in range(2880)] or len(source)!=2880:
            raise ValueError('V53 cadence changed')
        for h in core['cutoffs']:
            t=base+h*HOUR
            for lead in core['future_hours']:
                end=t+lead*HOUR
                expected=[t+timedelta(seconds=30*i) for i in range(120*lead)]
                for key in expected:
                    r=by_time[key]
                    start=key.replace(minute=0,second=0,microsecond=0)
                    draws.append(dict(sample_id=identity(('V37_META',r['product_sha256'],r['UTC'])),
                        V53_sample_id=r['sample_id'],source_SHA=r['product_sha256'],observation_UTC=r['UTC'],
                        cutoff_UTC=iso(t),horizon_hours=lead,endpoint_UTC=iso(end),
                        lower_hour_UTC=iso(start),upper_hour_UTC=iso(start+HOUR),
                        hour_weight=(key-start).total_seconds()/3600,
                        validity_flag=r['validity_flag'],access_policy='METADATA_ONLY',
                        target_status='TARGET_DENSITY_SEALED'))
                counts.append(dict(day=day,cutoff=h,horizon=lead,rows=len(expected),end_excluded=iso(end)))
    return draws,counts
