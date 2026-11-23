"""V32 history-only descriptive features and provenance-labeled read-only joins."""
import csv
import hashlib
import json
import math
from pathlib import Path
import resource
import subprocess
import sys
import time
import zipfile

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from evaluation.swarm_density_comparison import quality_mask
from evaluation.causal_density_latitude import sample_sha
from runtime.tiegcm_rank_exit import digest as sha, write_once

E=ROOT/'experiments'
OUT=E/'thermosphere_coefficient_stability_zg_audit_v32'
V30=E/'thermosphere_autumn_density_validation_v30'
V31=E/'thermosphere_spring_autumn_failure_mechanism_v31'
V1=E/'thermosphere_residual_representativeness_v1'
V18=E/'tiegcm_2022_mar25_density_validation_v18'
SPRING21=E/'causal_density_new_date_validation_v1'
PROTOCOL=E/'thermosphere_independent_date_validation_plan_v20/preregistered_protocol.json'
HEAD='7c4a47bf7ba725202fd07bf652aa4593a56249a7'
MAIN_DAYS=('2021-03-25','2022-03-25','2021-09-23','2022-09-23')
V1_DAYS=('2021-03-23','2021-03-24','2022-03-23','2022-03-24')
UNSEEN=('2021-06-21','2022-06-21','2021-12-21','2022-12-21')
FIELDS=('utc','density','latitude','longitude','altitude','quality','validity_flag','raw')
BANDS=('low','mid','high')


def require(ok,message):
    if not ok:raise ValueError(message)


def load(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def table(path,data):
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for row in data for k in row)),lineterminator='\n')
        w.writeheader();w.writerows(data)


def baseline(path):
    expected=hashlib.sha256(subprocess.check_output(['git','show',f'{HEAD}:{path.relative_to(ROOT)}'])).hexdigest()
    require(path.resolve()==path and sha(path)==expected,'Frozen Git file changed: '+path.name)
    return expected


def resource_log(start):
    return dict(wall_s=time.perf_counter()-start,CPU_s=time.process_time(),
                peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def freeze_roles():
    require(ROOT==Path.cwd().resolve() and OUT.resolve()==OUT,'Unexpected V32 path')
    OUT.mkdir()
    baseline(PROTOCOL)
    candidates=load(PROTOCOL)['fixed_dates']
    require(set(UNSEEN).issubset(candidates),'Unseen panel not registered')
    parts=[]
    for d in (*MAIN_DAYS,*V1_DAYS,*UNSEEN):
        held=d in UNSEEN
        parts.append(dict(date=d,role='UNSEEN_TEST_METADATA_ONLY' if held else 'DEVELOPMENT_SOURCE',
            historical_identity=('V30 preregistered held-out historical evaluation preserved' if d[5:]=='09-23'
                                else 'V20 candidate' if held else 'spring historical development/validation'),
            cutoff_history_density_access=not held,already_scored_future_aggregate_join=not held,
            future_density_access=False))
    write_once(OUT/'data_roles.json',dict(scope='HINDCAST / DEVELOPMENT_DIAGNOSTIC',
        dates=parts,method_validation_dates_in_current_round=[],new_test_evaluations=0,
        design_requires_frozen_formula_input_availability_hyperparameter_policy_roles_metrics_exclusions_gates=True,
        protocol_SHA256=sha(PROTOCOL),feature_code_SHA256=sha(Path(__file__))))


def specification(date,h):
    require(date in (*MAIN_DAYS,*V1_DAYS) and h in (6,18),'Date/cutoff outside history allowlist')
    y=int(date[:4])
    if date in V1_DAYS:
        prefix='D'+date.replace('-','')+f'H{h:02d}_'
        path=V1/'matched_diagnostics_local.npz'
        return path,{k:prefix+('B14_Raw' if k=='raw' else k) for k in FIELDS}
    if date=='2021-03-25':
        return SPRING21/'matched_local.npz',{k:f'B14_{h}_Raw' if k=='raw' else k for k in FIELDS}
    path=V18/f'history{h}_local.npz' if date=='2022-03-25' else V30/f'{y}_{h}_history_local.npz'
    return path,{k:k for k in FIELDS}


def read_member(archive,key,interval):
    # Numeric members are never decoded beyond the explicit authorized record slice.
    with archive.open(key+'.npy') as f:
        version=np.lib.format.read_magic(f)
        require(version in ((1,0),(2,0)),'Unexpected array header')
        header=np.lib.format.read_array_header_1_0 if version==(1,0) else np.lib.format.read_array_header_2_0
        shape,fortran,dtype=header(f)
        require(len(shape)==1 and not fortran and not dtype.hasobject,'Unsupported cached layout')
        if interval is None:
            require(key=='utc' or key.endswith('_utc'),'Only UTC index metadata can be read unbounded')
            start,stop=0,shape[0]
        else:
            start,stop=interval
        require(0<=start<stop<=shape[0],'Bad history record slice')
        # Zip decompression may pass preceding bytes; no out-of-range values are parsed.
        if start:
            require(len(f.read(start*dtype.itemsize))==start*dtype.itemsize,'Truncated prefix')
        buf=f.read((stop-start)*dtype.itemsize)
        require(len(buf)==(stop-start)*dtype.itemsize,'Truncated history')
        return np.frombuffer(buf,dtype=dtype)


def record_range(t,date,h):
    require(date in (*MAIN_DAYS,*V1_DAYS) and h in (6,18),'Unregistered window')
    cut=np.datetime64(date+f'T{h:02d}:00','ns')
    start=cut-np.timedelta64(3,'h')
    expected=start+np.arange(360)*np.timedelta64(30,'s')
    require(np.all(np.diff(t)>np.timedelta64(0,'ns')),'Duplicate or disordered UTC index')
    lo,hi=np.searchsorted(t,[start,cut])
    require(np.array_equal(t[lo:hi],expected),'Missing or irregular historical UTC')
    return int(lo),int(hi)


def read_history(date,h):
    path,keys=specification(date,h)
    require(path.resolve(strict=True)==path,'Unexpected cache path')
    with zipfile.ZipFile(path) as z:
        utc=read_member(z,keys['utc'],None).astype('datetime64[ns]')
        indices=record_range(utc,date,h)
        a={k:read_member(z,key,indices) for k,key in keys.items() if k!='utc'}
        a['utc']=utc[slice(*indices)]
    q,_=quality_mask(a['density'],a['validity_flag'])
    coordinates=np.isfinite(a['latitude'])&(abs(a['latitude'])<=90)&np.isfinite(a['longitude'])&(
        abs(a['longitude'])<=180)&np.isfinite(a['altitude'])&(a['altitude']>0)
    require((q&coordinates&a['quality']).all() and np.isfinite(a['raw']).all()
            and (a['raw']>0).all(),'Invalid historical CDF/model sample')
    return path,a


def stats(e):
    if len(e)<30:
        return {k:None for k in ('median','std','MAD','P05','P25','P75','P95','positive','negative')}
    mid=float(np.median(e))
    return dict(median=mid,std=float(np.std(e)),MAD=float(np.median(abs(e-mid))),
        **{f'P{q:02}':float(np.quantile(e,q/100)) for q in (5,25,75,95)},
        positive=float((e>0).mean()),negative=float((e<0).mean()))


def coefficient_reference(date,h):
    if date in V1_DAYS:return None
    y=int(date[:4])
    p=(SPRING21/'correction_parameters.json' if y==2021 else V18/'correction_parameters.json') if date[5:]=='03-25' else V30/f'{y}_parameters.json'
    baseline(p)
    params=load(p)['parameters'];params=params.get('B14',params)
    return params[f'GlobalAdaptive{h:02d}']


def history():
    start=time.perf_counter()
    roles=load(OUT/'data_roles.json')
    require(roles['feature_code_SHA256']==sha(Path(__file__)),'Code changed since role freeze')
    pins={name:baseline(ROOT/name) for name in (
        'reports/THERMOSPHERE_SPRING_AUTUMN_FAILURE_MECHANISM_V31.md',
        'docs/THERMOSPHERE_MECHANISM_NEXT_STAGE_PLAN_V31.md',
        'reports/THERMOSPHERE_AUTUMN_DENSITY_VALIDATION_V30.md',
        'reports/THERMOSPHERE_RESIDUAL_REPRESENTATIVENESS_V1.md',
    )}
    for directory in (V30,V31):
        index=directory/'publication_SHA256.json'
        pins[str(index.relative_to(ROOT))]=baseline(index)
        for name,d in load(index).items():
            require(sha(ROOT/name)==d,'Changed protected V30/V31 output')
            pins[name]=d
    v1manifest=V1/'sha256_manifest.json'
    pins[str(v1manifest.relative_to(ROOT))]=baseline(v1manifest)
    identity=load(v1manifest)
    v1_expected=next(v['matched_diagnostics_local.npz'] for v in identity.values()
                     if isinstance(v,dict) and 'matched_diagnostics_local.npz' in v)
    require(sha(V1/'matched_diagnostics_local.npz')==v1_expected,'V1 cache SHA drift')
    for year in (2021,2022):
        score=load(V30/f'{year}_score_receipt.json')
        for name,d in score['outputs_SHA256'].items():
            require(sha(V30/name)==d,'Changed V30 score output')
            pins[str((V30/name).relative_to(ROOT))]=d
    summaries=[];bygroup=[];cache=[]
    for date in (*MAIN_DAYS,*V1_DAYS):
        for h in (6,18):
            path,a=read_history(date,h)
            o=a['density'].astype(float);p=a['raw'].astype(float)
            e=np.log(o)-np.log(p)
            medians=[]
            for k in range(3):
                s=slice(k*120,(k+1)*120)
                medians.append(float(np.median(e[s])))
                bygroup.append(dict(date=date,cutoff=h,group=f'hour_{k+1}',N=120,
                    first_UTC=str(a['utc'][s][0]),last_UTC=str(a['utc'][s][-1]),
                    utc_SHA256=hashlib.sha256(a['utc'][s].astype('<i8').tobytes()).hexdigest(),**stats(e[s])))
            b=np.digitize(abs(a['latitude']),[30,60])
            counts=[int((b==j).sum()) for j in range(3)]
            for j,name in enumerate(BANDS):
                m=b==j
                bygroup.append(dict(date=date,cutoff=h,group=name,N=counts[j],sample_fraction=counts[j]/360,
                    observed_mean_kg_m3=float(o[m].mean()) if counts[j] else None,**stats(e[m])))
            ref=coefficient_reference(date,h)
            hist_sha=sample_sha(a['utc'],a['latitude'],o,p)
            if ref:
                require(ref['N']==360 and ref['sample_SHA256']==hist_sha and ref['b']==float(np.median(e)),
                        'Existing coefficient/sample identity did not match exact history')
            summaries.append(dict(date=date,cutoff=h,N=360,history_start=str(a['utc'][0]),
                last_UTC=str(a['utc'][-1]),cutoff_UTC=f'{date}T{h:02d}:00:00Z',
                hourly_b1=medians[0],hourly_b2=medians[1],hourly_b3=medians[2],
                hourly_range=max(medians)-min(medians),hour2_minus_1=medians[1]-medians[0],
                hour3_minus_2=medians[2]-medians[1],low_N=counts[0],mid_N=counts[1],high_N=counts[2],
                low_fraction=counts[0]/360,mid_fraction=counts[1]/360,high_fraction=counts[2]/360,
                observed_mean_kg_m3=float(o.mean()),observed_median_kg_m3=float(np.median(o)),
                model_mean_kg_m3=float(p.mean()),latitude_min_deg=float(a['latitude'].min()),
                latitude_max_deg=float(a['latitude'].max()),north_fraction=float((a['latitude']>=0).mean()),
                altitude_mean_m=float(a['altitude'].mean()),altitude_min_m=float(a['altitude'].min()),
                altitude_max_m=float(a['altitude'].max()),
                circular_longitude_span_deg=float(360-np.max(np.diff(np.r_[np.sort(a['longitude']),np.sort(a['longitude'])[0]+360]))),
                last_completed_Kp_bucket_end_UTC=f'{date}T{h:02d}:00:00Z',
                realtime_GFZ_value='UNVERIFIED_NOT_USED',**stats(e)))
            cache.append(dict(date=date,cutoff=h,path=str(path.relative_to(ROOT)),SHA256=sha(path),
                sample_SHA256=hist_sha,identity=('exact_frozen_coefficient_sample_hash' if ref else 'V1_manifest_cache_hash')))
    table(OUT/'history_stability.csv',summaries)
    table(OUT/'history_groups.csv',bygroup)
    write_once(OUT/'history_freeze.json',dict(history_SHA256=sha(OUT/'history_stability.csv'),
        groups_SHA256=sha(OUT/'history_groups.csv'),feature_code_SHA256=sha(Path(__file__)),
        role_SHA256=sha(OUT/'data_roles.json'),assets=pins,history_caches=cache,windows=len(summaries),
        future_density_parsed=False,formal_prediction_count=0,resource=resource_log(start)))


def associate():
    receipt=load(OUT/'history_freeze.json')
    for name,k in [('history_stability.csv','history_SHA256'),('history_groups.csv','groups_SHA256'),('data_roles.json','role_SHA256')]:
        require(sha(OUT/name)==receipt[k],'Changed history receipt')
    require(receipt['feature_code_SHA256']==sha(Path(__file__)),'Changed feature implementation')
    hrows={(r['date'],int(r['cutoff'])):r for r in rows(OUT/'history_stability.csv')}
    drift=[]
    for r in rows(V31/'autumn_residual_drift.csv'):
        if r['region']=='all' and r['window'] in ('future_6h','block_3_6h'):
            drift.append((f"{r['year']}-09-23",r['cutoff'],r['window'],r['delta_b'],'V31'))
    for p,name in [(V1/'history_future_median_gap.csv','V1'),(V18/'history_future_residual_gap.csv','V18')]:
        baseline(p)
        for r in rows(p):
            if r.get('case','B14')=='B14' and r['region']=='all' and r['window'] in ('future_6h','block_3_6h'):
                drift.append((r.get('date','2022-03-25'),r['cutoff'],r['window'],r['delta_b'],name))
    assoc=[]
    for date,h,w,d,src in drift:
        if (date,int(h)) in hrows:
            a=hrows[date,int(h)]
            assoc.append(dict(date=date,cutoff=h,window=w,label='abs_or_signed_median_drift',
                source=src,delta_b=float(d),historical_hourly_range=float(a['hourly_range']),
                historical_MAD=float(a['MAD'])))
    table(OUT/'drift_descriptive_join.csv',assoc)
    frozen=V31/'frozen_joint_readonly.csv'
    baseline(frozen)
    gains=[]
    for r in rows(frozen):
        if r['window']!='future_6h' or r['method']=='LatitudeAdaptive18':continue
        date=r['date'];h=int(r['cutoff']);a=hrows[date,h]
        used=hrows[date,6] if r['method']=='Stale06' else a
        gains.append(dict(date=date,cutoff=h,method=r['method'],
            input_hourly_range=float(used['hourly_range']),input_MAD=float(used['MAD']),
            input_P95_minus_P05=float(used['P95'])-float(used['P05']),
            input_negative_fraction=float(used['negative']),input_observed_mean=float(used['observed_mean_kg_m3']),
            cutoff_band_count_range=max(int(a[k+'_N']) for k in BANDS)-min(int(a[k+'_N']) for k in BANDS),
            historical_18_minus_06_b=(float(a['median'])-float(hrows[date,6]['median']) if h==18 else None),
            frozen_RMSE_gain_pct=r['RMSE_gain_pct'],frozen_relative_RMS_gain_pct=r['relative_RMS_gain_pct'],
            frozen_tail_nonworsened=r['TAIL_NONWORSENED'],frozen_low_bias_nonworsened=r['LOW_LATITUDE_BIAS_NONWORSENED'],
            frozen_joint=r['JOINT_NO_REGRET']))
    table(OUT/'frozen_outcome_descriptive_join.csv',gains)
    # Small-sample descriptive ranges only; no fitted model, thresholds or p-values.
    fresh=[r for r in gains if r['method']!='Stale06']
    same=[r for r in assoc if r['window']=='future_6h']
    def corr(x,y):return float(np.corrcoef(x,y)[0,1])
    write_once(OUT/'association_summary.json',dict(
        arithmetic_only=True,association_not_predictive=True,fresh_rows=len(fresh),fresh_distinct_dates=4,
        drift_rows=len(same),drift_distinct_dates=len({r['date'] for r in same}),
        unavailable_drift_cells=['2021-03-25 06Z','2021-03-25 18Z'],
        pearson_hourly_range_vs_abs_drift=corr([r['historical_hourly_range'] for r in same],[abs(r['delta_b']) for r in same]),
        pearson_MAD_vs_relative_RMS_gain=corr([r['input_MAD'] for r in fresh],[float(r['frozen_relative_RMS_gain_pct']) for r in fresh]),
        predictors_used_for_new_forecasts=0,selected_thresholds=0))


if __name__=='__main__':
    {'roles':freeze_roles,'history':history,'associate':associate}[sys.argv[1]]()
