"""Independently reconstruct assigned record subsets, clocks and worker results."""
from collections import defaultdict
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess

from cdflib import CDF, cdfepoch
from netCDF4 import Dataset, num2date

import run_real_development_v57 as run
from build_non_target_horizon_index_v56 import check_split, OUT as V56
from check_external_evidence_v55 import check
from verify_non_target_prediction_protocol_v56 import history


def read_table(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def model_inventory():
    runs = {
        '2021-03': 'tiegcm_2021_spinup_14day_v1/A14',
        '2022-03': 'tiegcm_2022_spinup_14day_v1/A14',
        '2022-03-25': 'tiegcm_2022_mar25_execution_review_v1/actual_run',
        '2021-09': 'thermosphere_autumn_mareqx_config_v23/2021/actual_run',
        '2022-09': 'thermosphere_autumn_mareqx_config_v23/2022/actual_run',
    }
    result = {}
    for key, directory in runs.items():
        times, paths = set(), []
        for path in sorted((run.ROOT/'experiments'/directory).glob('secondary_*.nc')):
            with Dataset(path) as nc:
                if tuple(nc['DEN'].dimensions) != tuple(nc['ZG'].dimensions):
                    raise ValueError('Unexpected DEN/ZG grid')
                axis = nc['time']
                times.update(dt.isoformat(timespec='seconds')[:19]+'Z' for dt in num2date(axis[:], axis.units))
            paths.append(str(path.relative_to(run.ROOT)))
        result[key] = (times, paths)
    rows = []
    for day in sorted(run.FOLDERS):
        key = day if day in runs else day[:7]
        times, paths = result[key]
        needed = [f'{day}T{h:02d}:00:00Z' for h in (3,4,5,15,16,17)]
        rows.append(dict(day=day, folder=runs[key], examined_secondary_volumes=len(paths),
            history_frames_present=sum(x in times for x in needed), missing_history_times=[x for x in needed if x not in times],
            DEN_ZG_metadata_only=True, future_target_observation_read=False))
    return rows


def test_negatives():
    checks = {}
    day = '2021-03-23'
    cdf = CDF(run.source(day))
    for name, action in {
        'cutoff_record': lambda: run.bounded_density(cdf,None,360,721,(360,720)),
        'full_day_normalization_input': lambda: run.bounded_density(cdf,None,0,2880,(360,720)),
        'invalid_record_order': lambda: run.bounded_density(cdf,None,720,360,(720,360)),
        'unseen_source_date': lambda: run.source('2021-06-21'),
        'train_validation_overlap': lambda: check_split([
            ('train', '2021-03-23T03:00:00Z','2021-03-23T06:00:00Z'),
            ('validation', '2021-03-23T05:00:00Z','2021-03-23T08:00:00Z')]),
    }.items():
        try:
            action()
        except (ValueError,KeyError) as exc:
            checks[name] = str(exc)
        else:
            raise ValueError(f'Negative test accepted: {name}')
    return checks


def main():
    byte_manifest = V56/'publication_SHA256.json'
    assert byte_manifest.read_bytes() == subprocess.check_output(
        ['git','show',f'{run.BASE}:{byte_manifest.relative_to(run.ROOT)}'],cwd=run.ROOT)
    manifest = json.loads(byte_manifest.read_text())
    assert all(run.sha(run.ROOT/name)==digest for name,digest in manifest.items())
    historical = history()
    availability = {r['day']: r for r in read_table(run.OUT/'availability.csv')}
    assert set(availability)==set(run.FOLDERS)
    forecast = read_table(run.OUT/'predictions.csv')
    keyed = {(r['cutoff_UTC'],int(r['horizon_hours']),r['method']): r for r in forecast}
    assert len(keyed) == len(forecast) == 96
    samples = defaultdict(set)
    windows = json.loads((run.OUT/'windows.json').read_text())
    input_records = 0
    for row in windows:
        cut = datetime.strptime(row['stop_exclusive'],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        day = cut.date().isoformat()
        info = availability[day]
        path = run.ROOT/info['CDF']
        digest = run.sha(path)
        assert digest == row['source_SHA256'] == info['source_SHA256']
        cdf = CDF(path)
        first = (cut.hour-3)*120
        stop = cut.hour*120
        vdr = cdf.vdr_info('density')
        vvr = cdf._read_vxrs(vdr.head_vxr,[],[],[])
        ledger = dict(zip(zip(vvr[1],vvr[2]),vvr[0]))
        chunks = []
        actual_reads = []
        with path.open('rb',buffering=0) as raw:
            for record in range(first,stop):
                start,end = next(key for key in ledger if key[0]<=record<=key[1])
                offset = ledger[start,end] + 12 + (record-start)*8
                chunks.append(struct.unpack('<d',os.pread(raw.fileno(),8,offset))[0])
                if not actual_reads or offset != actual_reads[-1]['byte_offset']+actual_reads[-1]['bytes']:
                    actual_reads.append(dict(first_record=record,exclusive_end_record=record,byte_offset=offset,bytes=0))
                actual_reads[-1]['exclusive_end_record'] += 1
                actual_reads[-1]['bytes'] += 8
        assert actual_reads == row['reads']
        datafile = run.LOCAL / (row['name']+'_history.csv')
        assert run.sha(datafile)==row['history_SHA256']
        records = read_table(datafile)
        flags = cdf.varget('validity_flag',startrec=first,endrec=stop-1)
        frozen_time = cdfepoch.to_datetime(cdf.varget('time',startrec=first,endrec=stop-1))
        for k,(record,value,flag,dt) in enumerate(zip(records,chunks,flags,frozen_time)):
            assert record['UTC'] == str(dt)[:19]+'Z'
            assert datetime.fromisoformat(record['UTC'][:-1]+'+00:00') == cut-timedelta(hours=3)+timedelta(seconds=30*k)
            assert float(record['density_kg_m3']) == value and int(record['validity_flag'])==flag
            assert int(record['valid']) == int(flag==0 and math.isfinite(value) and
                   0<value<float(cdf.varattsget('density')['FILLVAL']))
        assert len(records)==len(chunks)==len(flags)==360
        assert sum(int(r['valid']) for r in records)==row['valid_n']
        assert row['start']==(cut-timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ')
        input_records+=len(records)
        first_rho,last_rho = chunks[120],chunks[240]
        worker_input = run.LOCAL / row['name'] / 'anchors.txt'
        assert list(map(float,worker_input.read_text().split()))==[first_rho,last_rho]
        assert run.sha(worker_input)==row['input_SHA256']
        assert worker_input.stat().st_mode & 0o777 == datafile.stat().st_mode & 0o777 == 0o444
        for h in (1,3,6):
            target = (cut+timedelta(hours=h)).strftime('%Y-%m-%dT%H:%M:%SZ')
            parts = ['V57_SWARM_HISTORY_ONLY',digest,row['stop_exclusive'],h,target]
            sample = hashlib.sha256(json.dumps(parts,separators=(',',':')).encode()).hexdigest()
            for method,expected in (('Persistence',last_rho),('TwoFrameLinear',last_rho+(h+1)*(last_rho-first_rho))):
                answer = keyed[row['stop_exclusive'],h,method]
                assert answer['sample_id']==sample and answer['target_UTC']==target
                assert float(answer['density_kg_m3'])==expected and (answer['valid']=='True')==(expected>0)
                assert answer['input_SHA256']==row['input_SHA256'] and answer['source_SHA256']==digest
                samples[sample].add(method)
    assert len(windows)==16 and len(samples)==48 and all(len(s)==2 for s in samples.values())
    isolation = json.loads((run.OUT/'isolation.json').read_text())
    assert len(isolation['probes'])==10 and isolation['poison_predictions_identical']
    synthetic = read_table(run.OUT/'synthetic_metrics.csv')
    for row in synthetic:
        h = int(row['horizon_hours'])
        truth = {1:1.3e-12,3:1.5e-12,6:1.8e-12}[h]
        expected = 1.1e-12 if row['method']=='Persistence' else 1.1e-12+(h+1)*(1.1e-12-1e-12)
        assert float(row['Bias'])==expected-truth and float(row['MAE'])==float(row['RMSE'])==abs(expected-truth)
        assert float(row['relative_RMSE'])==abs(expected-truth)/truth and row['role']=='SYNTHETIC_ONLY'
    assert all(r['target_status']=='SEALED' for r in forecast)
    external = check()
    run.jsonout(run.OUT/'handoff.json',external)
    run.jsonout(run.OUT/'model_inventory.json',model_inventory())
    negatives = test_negatives()
    run.jsonout(run.OUT/'independent.json',dict(V56_entries=len(manifest),historical=historical,
        independently_checked_history_records=input_records,cutoffs=len(windows),sample_ids=len(samples),
        predictions=len(forecast),synthetic_metric_rows=len(synthetic),access_probe_assertions=len(isolation['probes']),
        negative_cases=negatives,max_prediction_abs_difference_kg_m3=0,
        valid_predictions={method:sum(r['valid']=='True' for r in forecast if r['method']==method)
                           for method in ('Persistence','TwoFrameLinear')},
        nominal_observations=sum(r['valid_n'] for r in windows),disk_free_bytes=shutil.disk_usage(run.ROOT).free,
        CPU_affinity=len(os.sched_getaffinity(0)),target_density_reads=0,formal_scores=0,AI_training=0,
        GPU=0,new_TIEGCM_integrations=0))


if __name__=='__main__':
    main()
