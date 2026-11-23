"""One-time V36 evaluation from V35's eight frozen development windows."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import resource
import subprocess
from time import monotonic, process_time
import zipfile

from cdflib import CDF, cdfepoch
import numpy as np

import stability_zg_v32 as old
import verify_causal_shrinkage_v35 as regression
from evaluation import causal_shrinkage_v35 as v35
from evaluation.causal_density_latitude import assess_joint, latitude_band
from evaluation.late_day_correction import RollingOrigin
from evaluation.swarm_crossyear import metric_row
from evaluation.swarm_density_comparison import quality_mask

ROOT = old.ROOT
BASE = '3004cfeff7232c5edd48916897ceb6d685e6eb2e'
OUT = old.E / 'thermosphere_causal_shrinkage_development_v36'
DESIGN = regression.OUT / 'v36_development_release.json'
DAYS = ('2021-03-25', '2022-03-25', '2021-09-23', '2022-09-23')
METHODS = tuple(v35.CANDIDATES)
REGIONS = ('all', 'low', 'mid', 'high')
BOUNDS = {'future_1h': (0, 1), 'future_3h': (0, 3), 'future_6h': (0, 6),
          'block_0_1h': (0, 1), 'block_1_3h': (1, 3), 'block_3_6h': (3, 6)}
METRICS = ('MAE', 'RMSE', 'bias', 'relative_RMS', 'relative_P95', 'relative_bias',
           'log_RMS', 'Pearson', 'max_abs')
FLAGS = ('RMSE_BENEFIT', 'RELATIVE_RMS_BENEFIT', 'TAIL_NONWORSENED',
         'LOW_LATITUDE_BIAS_NONWORSENED', 'JOINT_NO_REGRET')
RTOL = 1e-13


def require(ok, detail):
    if not ok:
        raise ValueError(detail)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def resources(wall, cpu):
    return dict(wall_seconds=monotonic()-wall, cpu_seconds=process_time()-cpu,
                peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def trusted_path(name):
    path = ROOT / name
    require(path.resolve(strict=True) == path and path.is_relative_to(ROOT), name)
    return path


def pin(name, digest):
    path = trusted_path(name)
    require(old.sha(path) == digest, f'SHA mismatch: {name}')
    return path


def release():
    blob = subprocess.check_output(['git', 'show', f'{BASE}:{DESIGN.relative_to(ROOT)}'], cwd=ROOT)
    require(blob == DESIGN.read_bytes(), 'V35 publication differs from V35 commit')
    return json.loads(blob)


def review_sources(plan):
    require(plan['state'] == 'SHRINKAGE_DESIGN_FROZEN_READY'
            and plan['methods'] == dict(v35.CANDIDATES), 'Candidate state')
    pins = plan['frozen_sources'] | plan['V35_SHA256']
    for name, digest in pins.items():
        pin(name, digest)
    require(old.load(old.PROTOCOL)['fixed_scientific_core'] == plan['V20_core'], 'V20 core')
    guards = (*[p for p in ('experiments/thermosphere_autumn_2021_formal_run_v24',
                            'experiments/thermosphere_autumn_2021_postrun_closure_v26',
                            'experiments/thermosphere_autumn_2022_formal_run_v29')],
              str(DESIGN.parent.relative_to(ROOT)), 'experiments/thermosphere_zg_external_datum_v34')
    subprocess.run(['git', 'diff', '--quiet', BASE, '--', *guards], cwd=ROOT, check=True)
    entries = plan['eligible_windows']
    require(len(entries) == 8 and {(x['date'], x['cutoff']) for x in entries}
            == {(d, h) for d in DAYS for h in (6, 18)}, 'Development scope changed')
    role = {row['date']:row['role'] for row in plan['roles']['dates']}
    require(all(role[d] == 'DEVELOPMENT_SOURCE' for d in DAYS)
            and all(role[d] == 'UNSEEN_TEST_METADATA_ONLY' for d in old.UNSEEN), 'Role mismatch')
    return len(pins)


def cdf_source(entry):
    manifest = old.load(trusted_path(entry['background_provenance_manifest']))
    day = entry['date']
    if day == '2021-03-25':
        source = manifest['observation']['CDF']
    elif day == '2022-03-25':
        source = manifest['CDF']
    else:
        source = manifest['years'][day[:4]]['CDF']
    require(day.replace('-', '') in Path(source['path']).name
            and Path(source['path']).stem.endswith('_0301')
            and 'DNSAPOD_2__' in Path(source['path']).name, 'CDF product identity')
    return source


def masks(day, hour, utc):
    found = RollingOrigin(day, hour).masks(utc)
    found['block_0_1h'] = found['future_1h']
    return {k: found[k] for k in BOUNDS}


def archive_members(entry, members):
    path = pin(entry['future_cache_path'], entry['future_cache_SHA256'])
    day, hour = entry['date'], entry['cutoff']
    cut = np.datetime64(f'{day}T{hour:02}:00', 'ns')
    with zipfile.ZipFile(path) as z:
        clock = old.read_member(z, 'utc', None)
        records = np.r_[360:1440, 1800:2880] if day == '2021-03-25' else np.arange(2880)
        require(np.array_equal(clock, np.datetime64(day, 'ns') + records*np.timedelta64(30, 's')),
                'Cache UTC grid mismatch')
        lo, hi = np.searchsorted(clock, (cut, cut+np.timedelta64(6, 'h')))
        require(hi-lo == 720, 'Missing future records')
        return dict(utc=clock[lo:hi], **{k: old.read_member(z, k, (lo,hi)) for k in members})


def cdf_slice(source, ids, *, density):
    path = pin(source['path'], source['SHA256'])
    cdf = CDF(path)
    g = cdf.globalattsget()
    require(g['TITLE'] == [path.stem] and g['TIME SYSTEM'] == ['UTC']
            and cdf.varinq('time').Data_Type == 31, 'CDF metadata')
    fields = {'latitude':'deg', 'longitude':'deg','altitude':'m','density':'kg/m3'}
    require(all(cdf.varattsget(k)['UNITS'] == unit for k, unit in fields.items()), 'CDF units')
    clock = cdfepoch.to_datetime(cdf.varget('time')).astype('datetime64[ns]')
    require(np.array_equal(clock, ids[0].astype('datetime64[D]')+np.arange(2880)*np.timedelta64(30,'s')),
            'CDF cadence')
    lo = int(np.searchsorted(clock, ids[0]))
    require(np.array_equal(clock[lo:lo+len(ids)], ids), 'CDF ordered sample IDs')
    keys = ['latitude','longitude','altitude','validity_flag'] + (['density'] if density else [])
    return {key: cdf.varget(key, startrec=lo, endrec=lo+len(ids)-1) for key in keys}


def table(name, rows):
    old.table(OUT/name, rows)


def freeze():
    wall, cpu = monotonic(), process_time()
    plan = release()
    count = review_sources(plan)
    tests = old.load(regression.OUT/'verification.json')
    require(tests['fixture_tests']==25 and not tests['failures'] and not tests['errors']
            and tests['independent_rtol']==RTOL and tests['independent_atol']==0
            and all(x['bitwise_same_history_and_multipliers'] for x in tests['poison']), 'V35 verification')
    test_result = regression.unittest.TextTestRunner(verbosity=1).run(
        regression.unittest.defaultTestLoader.loadTestsFromTestCase(regression.Checks))
    require(test_result.wasSuccessful() and test_result.testsRun==25, 'V36 regression')
    poison = regression.poison()
    require({p['cutoff'] for p in poison}=={6,18}, 'Poison windows')
    verified = {x['key']:x for x in tests['windows']}
    fits = []
    for entry in plan['eligible_windows']:
        day, hour = entry['date'], entry['cutoff']
        path = pin(entry['history_path'], entry['history_cache_SHA256'])
        pin(entry['original_global_path'], entry['original_global_SHA256'])
        actual, data = old.read_history(day, hour)
        require(actual == path, 'Unexpected history cache')
        fit = regression.bind(ROOT/entry['original_global_path'], entry['original_global_SHA256'],
                              day, hour, data)
        ref = verified[f'{day}/{hour:02}']
        require(fit.b==ref['original_b'] and fit.n==entry['history_quality_N']==360
                and fit.sample_sha256==entry['history_sample_SHA256']
                and fit.utc_sha256==entry['history_UTC_SHA256'], 'V35 original coefficient identity')
        methods = {}
        for name, value in v35.CANDIDATES.items():
            c = v35.coefficient(fit, value)
            methods[name] = dict(lambda_=value, b_shrink=c.log_bias, multiplier=c.multiplier)
        fits.append(dict(date=day, cutoff=hour, original=vars(fit), methods=methods))
    param_path = OUT/'parameter_freeze.json'
    if param_path.exists():
        prior = old.load(param_path)
        require(prior['windows']==fits and prior['source_SHA256']==old.sha(DESIGN)
                and prior['method_SHA256']==old.sha(Path(v35.__file__)), 'Existing freeze changed')
    else:
        old.write_once(param_path, dict(UTC=utc_now(), source_SHA256=old.sha(DESIGN),
                       source_pins=count, method_SHA256=old.sha(Path(v35.__file__)), fixture_tests=25,
                       poison=poison, temporal_identity=plan['temporal_identity'],
                       future_density_read=False, windows=fits, resources=resources(wall,cpu)))

    evidence, backgrounds, predictions = [], [], []
    for entry, row in zip(plan['eligible_windows'], fits, strict=True):
        day,hour = entry['date'],entry['cutoff']
        runner = v35.FrozenGlobal(**row['original'])
        raw = entry['future_background_field']
        global_key = ({'2021-03-25': f'B14_{hour}_', '2022-03-25': f'{hour}_'}.get(day, '')
                      + f'GlobalAdaptive{hour:02}')
        fields = (raw, global_key, 'latitude', 'longitude', 'altitude', 'validity_flag', 'quality')
        cache = archive_members(entry, fields)
        source = cdf_source(entry)
        coord = cdf_slice(source, cache['utc'], density=False)
        for key, values in coord.items():
            np.testing.assert_array_equal(values, cache[key], err_msg=f'{day}/{hour} {key}')
        require(cache['quality'].all() and (coord['validity_flag']==0).all(), 'Nominal flags')
        by_window = masks(day,hour,cache['utc'])
        for name, selection in by_window.items():
            target = entry['future_windows'][name]
            require(int(selection.sum())==target['N']
                    and v35.utc_sha(cache['utc'][selection])==target['original_ID_SHA256'], name)
        panel = v35.apply_panel(runner, cache[raw], cache['utc'],
                    expected_ids_sha256=entry['future_windows']['future_6h']['original_ID_SHA256'])
        for method, series in [('Raw',cache[raw]), ('Global',cache[global_key])]:
            np.testing.assert_array_equal(panel['predictions'][method], series, err_msg=f'{day}/{hour} {method}')
        require(all(panel['parameters'][k]['multiplier']==v['multiplier']
                    for k,v in row['methods'].items()), 'Frozen multipliers changed')
        for i, t in enumerate(cache['utc']):
            identity = dict(date=day, cutoff=hour, utc=str(t)+'Z', observation_ID=f'Swarm/A/0301/{t}Z')
            backgrounds.append(dict(identity, background_kg_m3=float(cache[raw][i]),
                    **{k:float(cache[k][i]) for k in ('latitude','longitude','altitude')},
                    flag=int(cache['validity_flag'][i])))
            predictions.append(dict(identity, **{k:float(panel['predictions'][k][i]) for k in METHODS}))
        evidence.append(dict(date=day, cutoff=hour, CDF=source, cache=entry['future_cache_path'],
                             cache_SHA256=entry['future_cache_SHA256'], N=720,
                             Raw_bitwise=True, Global_bitwise=True,
                             max_absolute_difference=0, max_relative_difference=0,
                             unit='kg/m3', query_identity='Frozen provisional Map-A',
                             windows=entry['future_windows']))
    table('common_background.csv', backgrounds)
    table('predictions.csv', predictions)
    old.write_once(OUT/'background_freeze.json', dict(UTC=utc_now(), future_density_read=False,
          windows=evidence, SHA256={name:old.sha(OUT/name) for name in
              ('parameter_freeze.json','common_background.csv','predictions.csv')},
          runner_SHA256=old.sha(Path(__file__)), resources=resources(wall,cpu)))


def previous_scores(day):
    if day == '2021-03-25':
        paths = (old.SPRING21/'metrics.csv', old.SPRING21/'region_metrics.csv')
    elif day == '2022-03-25':
        paths = (old.V18/'metrics.csv', old.V18/'region_metrics.csv')
    else:
        paths = (old.V30/f'{day[:4]}_metrics.csv',)
    out = {}
    for path in paths:
        expected = subprocess.check_output(['git','show',f'{BASE}:{path.relative_to(ROOT)}'],cwd=ROOT)
        require(path.read_bytes()==expected, 'Legacy metrics SHA changed')
        for r in old.rows(path):
            if r.get('case','B14')=='B14':
                out[int(r['cutoff']),r['window'],r['region'],r['method']] = r
    return out


def validate_legacy(rows):
    grouped = {d: previous_scores(d) for d in DAYS}
    max_abs = max_rel = 0.0
    count = 0
    for row in rows:
        day, hour, method = row['date'],row['cutoff'],row['method']
        r = grouped[day][hour,row['window'],row['region'],
                         'Raw' if method=='Raw' else f'GlobalAdaptive{hour:02}']
        require(row['n']==int(r['n']) and row['status']==r['status'], 'Baseline support mismatch')
        for metric in METRICS:
            x, y = row[metric], r[metric]
            if x is None:
                require(y=='', 'Unexpected legacy metric')
                continue
            y = float(y)
            require(np.isclose(x,y,rtol=RTOL,atol=0),
                    f'Legacy metric mismatch: {day}/{hour}/{row["window"]}/{row["region"]}/{method}/{metric}: {x!r} vs {y!r}')
            max_abs = max(max_abs,abs(x-y))
            if y:
                max_rel = max(max_rel,abs((x-y)/y))
            count += 1
    return dict(checked_finite_metrics=count, max_absolute_difference=max_abs,
                max_relative_difference=max_rel, rtol=RTOL, atol=0)


def evaluation_rows(panels, methods):
    for day,hour,utc,observed,lat,series in panels:
        q = np.ones(len(utc),bool)
        band = latitude_band(lat)
        for window, mask in masks(day,hour,utc).items():
            for method in methods:
                for idx, region in enumerate(REGIONS):
                    select = mask if idx==0 else mask&(band==idx-1)
                    yield dict(date=day,cutoff=hour,window=window,method=method,region=region,
                               **metric_row(series[method],observed,q,q,select))


def comparisons(metrics):
    index = {(r['date'],r['cutoff'],r['window'],r['method'],r['region']):r for r in metrics}
    joint,delta = [],[]
    scopes = sorted({(r['date'],r['cutoff'],r['window']) for r in metrics})
    for scope in scopes:
        day,hour,window = scope
        header=dict(date=day,cutoff=hour,window=window)
        def group(method):
            return {region:index[(*scope,method,region)] for region in REGIONS}
        raw = group('Raw')
        for method in ('Global','ShrinkageHalf'):
            test = group(method)
            joint.append(dict(header,method=method,**assess_joint(raw['all'],test['all'],raw,test)))
        for label, reference, selected in [('Global_vs_Raw','Raw','Global'),
                                            ('ShrinkageHalf_vs_Raw','Raw','ShrinkageHalf'),
                                            ('ShrinkageHalf_vs_Global','Global','ShrinkageHalf')]:
            a,b=group(reference),group(selected)
            for region in REGIONS:
                x,y=a[region],b[region]
                if x['status']!= 'OK' or y['status']!='OK':
                    vals = dict(RMSE_change_pct=None,relative_RMS_change_pct=None,
                                relative_P95_change=None,abs_relative_bias_change=None)
                else:
                    vals = dict(RMSE_change_pct=100*(y['RMSE']/x['RMSE']-1) if x['RMSE'] else None,
                       relative_RMS_change_pct=100*(y['relative_RMS']/x['relative_RMS']-1) if x['relative_RMS'] else None,
                       relative_P95_change=y['relative_P95']-x['relative_P95'],
                       abs_relative_bias_change=abs(y['relative_bias'])-abs(x['relative_bias']))
                delta.append(dict(header,comparison=label,region=region,**vals))
    return joint,delta


def score():
    wall,cpu=monotonic(),process_time()
    plan=release()
    review_sources(plan)
    receipt=old.load(OUT/'background_freeze.json')
    for name, sha in receipt['SHA256'].items():
        require(old.sha(OUT/name)==sha, name)
    require(old.sha(Path(__file__))==receipt['runner_SHA256'], 'Scorer changed after freeze')
    old.write_once(OUT/'score_once.json', dict(UTC=utc_now(), attempts=1,
                       background_freeze_SHA256=old.sha(OUT/'background_freeze.json')))
    try:
        bg=old.rows(OUT/'common_background.csv')
        pred=old.rows(OUT/'predictions.csv')
        panels=[]
        for entry,evidence in zip(plan['eligible_windows'],receipt['windows'],strict=True):
            day,hour=entry['date'],entry['cutoff']
            a=[x for x in bg if x['date']==day and int(x['cutoff'])==hour]
            b=[x for x in pred if x['date']==day and int(x['cutoff'])==hour]
            ids=np.array([x['utc'][:-1] for x in a],dtype='datetime64[ns]')
            require(len(a)==len(b)==720 and [x['observation_ID'] for x in a]
                    ==[x['observation_ID'] for x in b], 'Frozen pointwise identity')
            require(v35.utc_sha(ids)==entry['future_windows']['future_6h']['original_ID_SHA256'], 'Frozen ID hash')
            observed=cdf_slice(evidence['CDF'],ids,density=True)
            cache=archive_members(entry,('density',))['density']
            np.testing.assert_array_equal(observed['density'],cache,err_msg=f'{day}/{hour} observed density')
            for field in ('latitude','longitude','altitude'):
                np.testing.assert_array_equal(observed[field], [float(x[field]) for x in a])
            require(quality_mask(observed['density'], observed['validity_flag'])[0].all()
                    and np.array_equal(observed['validity_flag'],[int(x['flag']) for x in a]), 'Quality changed')
            series={m:np.array([float(x[m]) for x in b]) for m in METHODS}
            panels.append((day,hour,ids,observed['density'],observed['latitude'],series))
        baseline=list(evaluation_rows(panels,('Raw','Global')))
        validation=validate_legacy(baseline)
        old.write_once(OUT/'baseline_verification.json',validation)
        metrics=baseline+list(evaluation_rows(panels,('ShrinkageHalf',)))
        joint,delta=comparisons(metrics)
        table('metrics.csv',metrics)
        table('joint.csv',joint)
        table('comparisons.csv',delta)
        old.write_once(OUT/'score_completed.json',dict(UTC=utc_now(), metric_rows=len(metrics),
             joint_rows=len(joint), comparison_rows=len(delta), complete=True, resources=resources(wall,cpu),
             SHA256={name:old.sha(OUT/name) for name in ('metrics.csv','joint.csv','comparisons.csv','baseline_verification.json')}))
    except Exception as exc:
        old.write_once(OUT/'score_failure.json',dict(UTC=utc_now(), reason=str(exc), resources=resources(wall,cpu)))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=('freeze','score'))
    {'freeze':freeze,'score':score}[parser.parse_args().phase]()
