"""Independent verification for V56 frozen history, UTC, truth and isolation."""
from collections import Counter
import csv
from datetime import datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import unittest

from cdflib import CDF
import numpy as np
from netCDF4 import Dataset, num2date

import build_non_target_horizon_index_v56 as idx
import admit_swarm_summer_v53 as seal
import verify_external_evidence_handoff_v55 as v55
import test_future_access_isolation_v56 as isolation
from runtime.tiegcm_rank_exit import write_once

V55=idx.ROOT/'experiments/thermosphere_external_evidence_handoff_v55'


def read(name):
    with (idx.OUT/name).open(newline='') as f:
        return list(csv.DictReader(f))


def fold(s):
    return datetime.strptime(s,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)


def history():
    manifest=idx.pin(V55/'publication_SHA256.json')
    for source,digest in manifest.items():
        assert idx.sha(idx.ROOT/source)==digest,source
    historic=v55.verify_history()
    dates=('2021-05-09','2021-06-16')
    for day in dates:
        old=idx.ROOT/f'data/raw/thermosphere_summer_data_acquisition_v38/Fobs_{day}_{day}.json'
        latest=idx.ROOT/f'experiments/thermosphere_swarm_external_datum_v54/public_evidence/{day}_Fobs.json'
        assert latest.read_bytes()==old.read_bytes() and json.loads(old.read_bytes())['Fobs']==[-1.0]
    return dict(V55=len(manifest),GFZ_missing=list(dates),**historic)


def independent_controls():
    hourly=json.loads((idx.OUT/'hourly_results.json').read_text())
    sources={r['source']:r for r in hourly['sources']}
    for entry in sources.values():
        path=idx.OUT/entry['file']
        assert idx.sha(path)==entry['sha256']
        with Dataset(path) as n:
            assert n.synthetic_marker=='V56_FROZEN_SYNTHETIC_ONLY'
            t=n['time']
            native=num2date(t[:],t.units)
            expected=fold(entry['start'])
            assert len(native)==49 and all(x.isoformat()==(expected+timedelta(hours=k)).replace(
                tzinfo=None).isoformat() for k,x in enumerate(native))
    cases=read('horizon_index.csv')
    mapping={r['sample_id']:r for r in cases}
    assert len(mapping)==36
    for r in cases:
        cutoff=fold(r['cutoff_UTC'])
        expected=fold(r['target_UTC'])
        h=int(r['horizon_hours'])
        assert cutoff.hour in (6,18) and h in (1,3,6) and (expected-cutoff).total_seconds()==h*3600
        assert (cutoff-fold(r['input_window_start_UTC'])).total_seconds()==10800
        assert (cutoff-fold(r['last_allowed_hourly_record_UTC'])).total_seconds()==3600
        assert r['input_window_end_UTC']==r['allowed_history_end_UTC']==r['cutoff_UTC']
        assert r['source_SHA']==sources[r['source_identity']]['sha256']
        expr=('V56_SYNTHETIC_ENDPOINT',r['source_SHA'],r['source_identity'],r['split_identity'],
              r['cutoff_UTC'],h,r['target_UTC'])
        expected_id=hashlib.sha256(json.dumps(expr,separators=(',',':')).encode()).hexdigest()
        assert expected_id==r['sample_id']
    midnight={r['source_identity'] for r in cases if r['cutoff_UTC'][:10]!=r['target_UTC'][:10]}
    assert midnight=={'MONTH','LEAP','YEAR'}
    assert any(r['cutoff_UTC']=='2020-02-29T18:00:00Z' and r['target_UTC']=='2020-03-01T00:00:00Z' for r in cases)
    assert any(r['cutoff_UTC']=='2020-12-31T18:00:00Z' and r['target_UTC']=='2021-01-01T00:00:00Z' for r in cases)
    controls=read('synthetic_query_controls.csv')
    err=[]
    # Independent monomial tensor evaluation, with no provider or main truth-function call.
    coefficients=np.zeros((2,2,2))
    for (i,j,k),v in [((0,0,0),1.6),((1,0,0),.15),((0,1,0),.08),((0,0,1),.12),
                      ((0,1,1),.04),((1,1,0),.03),((1,0,1),.07),((1,1,1),.02)]:
        coefficients[i,j,k]=v
    for r in controls:
        row=mapping[r['sample_id']]
        assert row['cutoff_UTC']==r['cutoff_UTC'] and row['source_identity']==r['source']
        instant=fold(r['UTC'])
        start=fold(sources[r['source']]['start'])
        x=(float(r['lon'])+185)%360/5
        y=float(r['lat'])/90
        t=(instant-start).total_seconds()/172800
        h=float(r['altitude_m'])
        polynomial=np.polynomial.polynomial.polyval3d(t,y,x,coefficients)
        expected=polynomial*np.exp(-1.55e-5*(h-350000))*1e-12
        assert expected>0
        actual=float(r['actual_kg_m3'])
        err.append(abs(actual/expected-1))
    assert max(err)<1e-11 and len(controls)==hourly['controls']
    assert len({r['control_id'] for r in controls})==len(controls)
    return dict(n=len(controls),max_relative=max(err),P95_relative=float(np.percentile(err,95)),endpoint_rows=len(cases))


def verify_isolation():
    manifest=json.loads((idx.OUT/'isolation_results.json').read_text())
    for i,row in enumerate(manifest['evidence']):
        path=isolation.STORE/f'cutoff_{i:02d}'
        history_path=path/'history.json'
        a=path/'baseline_future.json'
        b=path/'future.json'
        assert [idx.sha(p) for p in (history_path,a,b)]==[row[x] for x in (
            'history_SHA','future_original_SHA','future_poisoned_SHA')]
        full,bad=[json.loads(p.read_text())['rows'] for p in (a,b)]
        assert len(full)==len(bad)==7
        assert all(x['UTC']==y['UTC'] and y['density_kg_m3']==1e20*x['density_kg_m3'] for x,y in zip(full,bad))
        t=fold(row['cutoff_UTC'])
        assert all(fold(x['UTC'])>=t for x in full+bad)
        seen=0
        for call in row['predictor']['access_log']:
            assert call['allowed']
            for q in call['UTC']:
                assert t-timedelta(hours=3)<=fold(q)<t
                seen+=1
        assert seen==6 and row['causal_input_and_output_bitwise_equal']
        assert len(row['negative_cases'])==13 and all(x['error'] for x in row['negative_cases'])
        u,v,w=[x['density_kg_m3'] for x in json.loads(history_path.read_text())['rows']]
        actual=row['predictor']
        assert actual['normalization']['mean']==(u+v+w)/3
        for a in actual['predictions']:
            assert a['Persistence']==w and a['TwoFrameLinear']==w+(a['lead']+1)*(w-v)
    predictions=read('synthetic_baseline_pairs.csv')
    metrics=read('synthetic_baseline_metrics.csv')
    for s in metrics:
        rows=[r for r in predictions if r['method']==s['method'] and r['horizon_hours']==s['horizon_hours']
               and int(r['cutoff_UTC'][11:13])==int(s['cutoff_UTC_hour'])]
        expected=np.array([float(r['truth_kg_m3']) for r in rows])
        out=np.array([float(r['prediction_kg_m3']) for r in rows])
        d=out-expected
        for k,val in dict(MAE_kg_m3=np.mean(abs(d)),RMSE_kg_m3=np.sqrt(np.mean(d*d)),
                          Bias_kg_m3=np.mean(d),relative_RMSE=np.sqrt(np.mean((d/expected)**2))).items():
            assert np.isclose(float(s[k]),val,rtol=1e-14,atol=1e-27)
        assert len(rows)==int(s['n'])==6
    return dict(poison_cutoffs=len(manifest['evidence']),metric_groups=len(metrics),prediction_rows=len(predictions),
                audited_training_calls=sum(len(p['predictor']['access_log']) for p in manifest['evidence']),
                actual_rejections=manifest['negative_rejections'])


def verify_metadata():
    rows=read('swarm_metadata_time_index.csv')
    assert len(rows)==4800 and len({r['sample_id'] for r in rows})==2880
    counts=Counter()
    for r in rows:
        t=fold(r['observation_UTC'])
        cut=fold(r['cutoff_UTC'])
        lo=fold(r['lower_hour_UTC'])
        hi=fold(r['upper_hour_UTC'])
        end=fold(r['endpoint_UTC'])
        assert cut<=t<end and lo<=t<hi and (hi-lo).total_seconds()==3600
        assert (t-cut).total_seconds()%30==0 and float(r['hour_weight'])==(t-lo).total_seconds()/3600
        assert end-cut==timedelta(hours=int(r['horizon_hours']))
        assert r['target_status']=='TARGET_DENSITY_SEALED'
        counts[cut.date().isoformat(),cut.hour,int(r['horizon_hours'])]+=1
    assert len(counts)==12 and all(n==120*h for (_,_,h),n in counts.items())
    return dict(records=len(rows),unique_samples=2880,window_groups=len(counts))


def negative_tests():
    protocol=idx.pin(idx.V37)['V20_core']
    date=fold('2020-12-31T00:00:00Z')
    good=[idx.iso(date+timedelta(hours=k)) for k in range(49)]
    cut='2020-12-31T18:00:00Z'
    def build(values,cutoffs):
        return idx.build(values,cutoffs,'synthetic','test','f'*64,protocol)
    class Reject(unittest.TestCase):
        def test_missing(self):
            with self.assertRaises(ValueError): build(good[:8]+good[9:],[cut])
        def test_duplicate(self):
            with self.assertRaises(ValueError): build(good[:8]+[good[7]]+good[8:],[cut])
        def test_nonhour(self):
            with self.assertRaises(ValueError): build(good[:8]+[good[8].replace(':00:00',':00:30')]+good[9:],[cut])
        def test_bad_cut(self):
            with self.assertRaises(ValueError): build(good,['2020-12-31T18:30:00Z'])
        def test_wrong_utc(self):
            with self.assertRaises(ValueError): build(good,[cut.removesuffix('Z')])
        def test_target_outside(self):
            with self.assertRaisesRegex(ValueError,'Target outside'): build(good[:24],[cut])
        def test_history_outside(self):
            with self.assertRaisesRegex(ValueError,'cutoff history'): build(good[17:],[cut])
        def test_repeated_cutoff(self):
            with self.assertRaises(ValueError): build(good,[cut,cut])
        def test_split_overlap(self):
            with self.assertRaises(ValueError): idx.check_split([('a',good[0],good[24]),('b',good[24],good[-1])])
        def test_sealed_reader(self):
            log=[]
            with seal.sealed_access(log):
                for name in ('density','density_orbitmean'):
                    with self.assertRaises(ValueError): CDF.varget(object(),name)
            self.assertEqual(log,[dict(variable='density',allowed=False),dict(variable='density_orbitmean',allowed=False)])
    test=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Reject))
    assert test.wasSuccessful()
    return test.testsRun


def main():
    digest=history()
    numeric=independent_controls()
    access=verify_isolation()
    meta=verify_metadata()
    tests=negative_tests()
    write_once(idx.OUT/'independent.json',dict(historical=digest,numeric=numeric,access=access,metadata=meta,
        targeted_CPU_tests=tests,actual_density_decodes=0,new_TIEGCM_runs=0,GPU=0,formal_scores=0))


if __name__=='__main__':
    main()
