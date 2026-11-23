"""Independent sorted statistics, cutoff/quality negatives and ZG header verification."""
from collections import Counter
import json
import math
from pathlib import Path
import time
from unittest.mock import patch
import zipfile

from netCDF4 import Dataset
import numpy as np

import stability_zg_v32 as v
from review_zg_v32 import trusted_source


def equal(a,b):
    if b is None:
        return a in ('',None)
    return math.isclose(float(a),float(b),rel_tol=1e-13,abs_tol=0)


def percentile(values,f):
    s=sorted(map(float,values))
    x=(len(s)-1)*f
    lo=int(x)
    return s[lo]+(s[math.ceil(x)]-s[lo])*(x-lo)


def independently_read_window(date,h):
    # Parse UTC index and authorized bytes with a separate reader; never read full density members.
    path,keys=v.specification(date,h)
    low=np.datetime64(date)+np.timedelta64(h-3,'h')
    high=low+np.timedelta64(3,'h')
    with zipfile.ZipFile(path) as z:
        with z.open(keys['utc']+'.npy') as f:
            utc=np.load(f,allow_pickle=False)
        ix=[i for i,t in enumerate(utc) if low<=t<high]
        assert len(ix)==360 and ix[-1]-ix[0]==359
        a={'utc':utc[ix]}
        for key,member in keys.items():
            if key=='utc':continue
            with z.open(member+'.npy') as f:
                version=np.lib.format.read_magic(f)
                reader=np.lib.format.read_array_header_1_0 if version==(1,0) else np.lib.format.read_array_header_2_0
                _,_,dtype=reader(f)
                f.seek(ix[0]*dtype.itemsize,1)
                a[key]=np.frombuffer(f.read(360*dtype.itemsize),dtype=dtype)
    return a


def fail_if_accepted(fun):
    try:
        fun()
    except (ValueError,FileNotFoundError):
        return True
    raise AssertionError('Negative case was accepted')


def main():
    start=time.perf_counter()
    out=v.OUT
    assert out.resolve()==out
    roles=v.load(out/'data_roles.json')
    rec=v.load(out/'history_freeze.json')
    z=v.load(out/'zg_review_receipt.json')
    nr=0
    def compare(r,expected):
        nonlocal nr
        for k,x in expected.items():
            nr+=1
            assert equal(r[k],x),(r.get('date'),r.get('cutoff'),r.get('group'),k,r[k],x)
    def scalar_stats(x):
        k=('median','std','MAD','P05','P25','P75','P95','positive','negative')
        if len(x)<30:return dict.fromkeys(k)
        mid=percentile(x,.5);mean=math.fsum(x)/len(x)
        std=math.sqrt(math.fsum((v-mean)**2 for v in x)/len(x))
        return dict(median=mid,std=std,MAD=percentile([abs(v-mid) for v in x],.5),
                    **{f'P{j:02}':percentile(x,j/100) for j in (5,25,75,95)},
                    positive=sum(v>0 for v in x)/len(x),negative=sum(v<0 for v in x)/len(x))
    for name,digest in {**rec['assets'],**z['files_rechecked']}.items():
        assert v.sha(v.ROOT/name)==digest,name
    assert v.sha(v.PROTOCOL)==roles['protocol_SHA256']
    assert v.sha(out/'history_stability.csv')==rec['history_SHA256']
    assert v.sha(out/'history_groups.csv')==rec['groups_SHA256']
    assert v.sha(out/'data_roles.json')==rec['role_SHA256']
    assert all(v.sha(v.ROOT/r['path'])==r['SHA256'] for r in rec['history_caches'])
    group={(r['date'],r['cutoff'],r['group']):r for r in v.rows(out/'history_groups.csv')}
    proof={}
    for row in v.rows(out/'history_stability.csv'):
        date,h=row['date'],int(row['cutoff'])
        a=independently_read_window(date,h)
        t=a['utc'];lat=list(map(float,a['latitude']));lon=sorted(map(float,a['longitude']))
        y=list(map(float,a['density']));p=list(map(float,a['raw']));height=list(map(float,a['altitude']))
        assert all(int(x)==0 for x in a['validity_flag']) and a['quality'].all()
        assert all(0<q<1e30 for q in y) and all(q>0 for q in p)
        assert all(abs(x)<=90 for x in lat) and all(abs(x)<=180 for x in lon) and all(x>0 for x in height)
        # The separate scalar path preserves the originally specified log(obs)-log(raw).
        e=list(np.log(y)-np.log(p))
        bins=[0 if abs(x)<30 else 1 if abs(x)<60 else 2 for x in lat]
        med=[]
        for j in range(3):
            k=slice(j*120,(j+1)*120)
            r=group[date,str(h),f'hour_{j+1}']
            s=scalar_stats(e[k]);med.append(s['median'])
            compare(r,dict(N=120,**s))
            assert r['first_UTC']==str(t[k][0]) and r['last_UTC']==str(t[k][-1])
            assert r['utc_SHA256']==__import__('hashlib').sha256(t[k].astype('<i8').tobytes()).hexdigest()
        counts=[bins.count(j) for j in range(3)]
        for j,k in enumerate(v.BANDS):
            r=group[date,str(h),k]
            compare(r,dict(N=counts[j],sample_fraction=counts[j]/360,
                observed_mean_kg_m3=math.fsum(yy for i,yy in enumerate(y) if bins[i]==j)/counts[j],
                **scalar_stats([e[i] for i,b in enumerate(bins) if b==j])))
        compare(row,dict(N=360,observed_mean_kg_m3=math.fsum(y)/360,observed_median_kg_m3=percentile(y,.5),
            model_mean_kg_m3=math.fsum(p)/360,hourly_b1=med[0],hourly_b2=med[1],hourly_b3=med[2],
            hourly_range=max(med)-min(med),hour2_minus_1=med[1]-med[0],hour3_minus_2=med[2]-med[1],
            altitude_mean_m=math.fsum(height)/360,altitude_min_m=min(height),altitude_max_m=max(height),
            latitude_min_deg=min(lat),latitude_max_deg=max(lat),north_fraction=sum(x>=0 for x in lat)/360,
            circular_longitude_span_deg=360-max(b-a for a,b in zip(lon,lon[1:]+[lon[0]+360])),
            **{k+'_N':counts[j] for j,k in enumerate(v.BANDS)},
            **{k+'_fraction':counts[j]/360 for j,k in enumerate(v.BANDS)},**scalar_stats(e)))
        assert str(t[0])==row['history_start'] and str(t[-1])==row['last_UTC']
        proof[date,h]=e
    sample=np.datetime64('2022-09-23T00:00','ns')+np.arange(2880)*np.timedelta64(30,'s')
    tests={}
    for h in (6,18):
        lo,hi=v.record_range(sample,'2022-09-23',h)
        tests[f'cutoff_{h}_exclusive']=(hi-lo==360 and sample[hi]==np.datetime64(f'2022-09-23T{h:02d}:00'))
        tests[f'missing_{h}_rejected']=fail_if_accepted(lambda h=h,lo=lo:v.record_range(np.delete(sample,lo),'2022-09-23',h))
        tests[f'duplicate_{h}_rejected']=fail_if_accepted(lambda h=h,lo=lo:v.record_range(np.insert(sample,lo,sample[lo]),'2022-09-23',h))
    tests['unseen_date_rejected']=fail_if_accepted(lambda:v.read_history('2022-06-21',6))
    tests['unknown_cutoff_rejected']=fail_if_accepted(lambda:v.read_history('2022-09-23',12))
    tests['no_small_N_substitute']=all(x is None for x in v.stats(np.arange(29)).values())
    path,keys=v.specification('2021-03-25',6)
    with zipfile.ZipFile(path) as zf:
        tests['future_density_unbounded_rejected']=fail_if_accepted(lambda:v.read_member(zf,keys['density'],None))
    original=v.read_member
    def fake_invalid(zf,key,interval):
        x=original(zf,key,interval)
        if key=='validity_flag':
            x=x.copy();x[0]=1
        return x
    with patch.object(v,'read_member',side_effect=fake_invalid):
        tests['old_quality_filter_rejects_flag1']=fail_if_accepted(lambda:v.read_history('2022-09-23',6))
    tests['data_role_separation']=all(r['role']=='UNSEEN_TEST_METADATA_ONLY' and not r['cutoff_history_density_access']
                                     for r in roles['dates'] if r['date'] in v.UNSEEN)
    tests['existing_joint_unchanged']=v.load(v.V30/'result.json')['per_date_joint']['2021_autumn']['PASS']==8
    tests['no_model_or_candidate_execution']=rec['formal_prediction_count']==0 and v.load(
        out/'association_summary.json')['predictors_used_for_new_forecasts']==0 and z['model_queries']==0
    matrix={r['field']:r for r in v.rows(out/'zg_evidence_matrix.csv')}
    tests['height_datum_never_promoted']=matrix['external_zero']['evidence_level']=='EXTERNAL_UNVERIFIED' and         matrix['Map_A']['evidence_level']=='INTERNAL_NUMERIC_CONFIRMED' and z['external_datum']=='EXTERNAL_DATUM_UNVERIFIED'
    tests['bad_ZG_source_sha_rejected']=fail_if_accepted(lambda:trusted_source(matrix['ZG_definition']['source_path'],'0'*64,'calczg'))
    tests['ZG_source_wrong_definition_rejected']=fail_if_accepted(lambda:trusted_source(
        matrix['ZG_definition']['source_path'],matrix['ZG_definition']['source_SHA256'],'V32_NONEXISTENT'))
    headers=v.load(out/'zg_native_headers.json')
    for label,item in headers.items():
        with Dataset(v.ROOT/item['path']) as ds:
            assert np.allclose(np.asarray(ds['lev'][:])-np.asarray(ds['ilev'][:]),.25,atol=0,rtol=0)
            p0=float(ds['p0'][...])*100  # millibar to Pa
            assert math.isclose(p0,5e-5,rel_tol=1e-12)
            for key,row in item['variables'].items():
                v1=ds.variables[key]
                assert list(v1.dimensions)==row['dimensions'] and v1.units==row['unit']
            assert ('ZG' in ds.variables)==label.endswith('warm')
    tests['source_headers_match']=True
    tests['v2_v21_previous_artifacts_sha_match']=all(v.sha(v.ROOT/name)==h for name,h in z['files_rechecked'].items())
    assert all(tests.values()),tests
    # Independently recalculate aggregate correlations from recorded, frozen post-hoc labels.
    def cross(x,y):
        a=math.fsum(x)/len(x);b=math.fsum(y)/len(y)
        return math.fsum((u-a)*(vv-b) for u,vv in zip(x,y))/math.sqrt(
            math.fsum((u-a)**2 for u in x)*math.fsum((vv-b)**2 for vv in y))
    assoc=v.load(out/'association_summary.json')
    drift=[r for r in v.rows(out/'drift_descriptive_join.csv') if r['window']=='future_6h']
    fresh=[r for r in v.rows(out/'frozen_outcome_descriptive_join.csv') if r['method']!='Stale06']
    assert len(drift)==assoc['drift_rows'] and len(fresh)==assoc['fresh_rows']
    compare(assoc,dict(pearson_hourly_range_vs_abs_drift=cross(
        [float(r['historical_hourly_range']) for r in drift],[abs(float(r['delta_b'])) for r in drift]),
        pearson_MAD_vs_relative_RMS_gain=cross(
        [float(r['input_MAD']) for r in fresh],[float(r['frozen_relative_RMS_gain_pct']) for r in fresh])))
    v.write_once(out/'independent_verification.json',dict(PASS=True,numeric_fields=nr,
        independent_windows=len(proof),tests={key:bool(value) for key,value in tests.items()},protected_file_SHA_count=len(set(rec['assets'])|set(z['files_rechecked'])),
        future_density_parsed=False,external_datum='EXTERNAL_DATUM_UNVERIFIED',
        resource=v.resource_log(start)))


if __name__=='__main__':
    main()
