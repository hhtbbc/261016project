"""Read-only independent V36 audit using original CDF and scalar statistics."""
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import resource
import struct
import subprocess
from time import monotonic, process_time
import zipfile

from cdflib import CDF, cdfepoch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASE = '3004cfeff7232c5edd48916897ceb6d685e6eb2e'
EXPERIMENT = ROOT/'experiments'
DESIGN = EXPERIMENT/'thermosphere_causal_shrinkage_design_v35/v36_development_release.json'
OUT = EXPERIMENT/'thermosphere_causal_shrinkage_development_v36'
ADMITTED = {'2021-03-25','2022-03-25','2021-09-23','2022-09-23'}
BOUNDS = {'future_1h':(0,1),'future_3h':(0,3),'future_6h':(0,6),
          'block_0_1h':(0,1),'block_1_3h':(1,3),'block_3_6h':(3,6)}
METHODS = {'Raw':0.0,'Global':1.0,'ShrinkageHalf':0.5}
REGIONS = ('all','low','mid','high')
TESTS = Counter()
ERRORS = {}
MAX_DIFF = {}


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))


def check(kind, status, detail):
    TESTS[kind] += 1
    if not status:
        ERRORS.setdefault(kind, []).append(detail)


def same(label, name, actual, expected):
    if expected is None:
        check('metric_NA', actual=='', dict(key=label, field=name, published=actual))
        return
    got = float(actual)
    difference = abs(got-expected)
    rel = difference/abs(expected) if expected else None
    highest = MAX_DIFF.setdefault(name, {'absolute':0.0,'relative':0.0})
    highest['absolute'] = max(highest['absolute'],difference)
    if rel is not None:
        highest['relative'] = max(highest['relative'],rel)
    check('numeric', difference <= 1e-13*abs(expected),
          dict(key=label, field=name, published=got, independent=expected,
               absolute_difference=difference, relative_difference=rel))


def id_hash(ts):
    return hashlib.sha256(b''.join(struct.pack('<q', int(t)) for t in ts.astype('int64'))).hexdigest()


def packed_member(archive, name, offset, count):
    with archive.open(name+'.npy') as stream:
        version=np.lib.format.read_magic(stream)
        assert version in ((1,0),(2,0))
        read_header={ (1,0):np.lib.format.read_array_header_1_0,
                      (2,0):np.lib.format.read_array_header_2_0 }[version]
        dims,fort,dt=read_header(stream)
        assert not fort and len(dims)==1 and not dt.hasobject and offset+count<=dims[0]
        stream.seek(stream.tell()+offset*dt.itemsize)
        raw=stream.read(count*dt.itemsize)
        assert len(raw)==count*dt.itemsize
        return np.frombuffer(raw, dtype=dt)


def quantify(pred, obs):
    n=len(obs)
    result=dict.fromkeys(('MAE','RMSE','bias','relative_RMS','relative_P95','relative_bias',
                          'log_RMS','Pearson','max_abs','bias_over_mean_observed',
                          'observed_mean','simulated_mean'))
    if n<30:
        result['observed_mean']=math.fsum(obs)/n if n else None
        result['simulated_mean']=math.fsum(pred)/n if n else None
        return result
    err=pred-obs
    rel=err/obs
    sorted_rel=sorted(abs(rel))
    rank=0.95*(n-1)
    i=int(rank)
    p95=sorted_rel[i]+(rank-i)*(sorted_rel[i+1]-sorted_rel[i])
    xp,yo=math.fsum(pred)/n,math.fsum(obs)/n
    u,v=pred-xp,obs-yo
    norm=math.sqrt(math.fsum(u*u)*math.fsum(v*v))
    # Preserve NumPy summation for the signed, cancellation-sensitive baseline contract.
    bias,rel_bias=float(np.add.reduce(err)/n),float(np.add.reduce(rel)/n)
    return dict(MAE=math.fsum(abs(err))/n,RMSE=math.sqrt(math.fsum(err*err)/n),
                bias=bias,relative_RMS=math.sqrt(math.fsum(rel*rel)/n),
                relative_P95=p95,relative_bias=rel_bias,
                log_RMS=math.sqrt(math.fsum(math.log(float(x/y))**2 for x,y in zip(pred,obs))/n),
                Pearson=math.fsum(u*v)/norm if norm else None,max_abs=float(max(abs(err))),
                bias_over_mean_observed=bias/float(np.add.reduce(obs)/n),
                observed_mean=yo,simulated_mean=xp)


def audit():
    wall,cpu=monotonic(),process_time()
    start_blob=subprocess.check_output(['git','show',f'{BASE}:{DESIGN.relative_to(ROOT)}'],cwd=ROOT)
    assert start_blob==DESIGN.read_bytes()
    design=json.loads(start_blob)
    for path,expected in (design['frozen_sources']|design['V35_SHA256']).items():
        check('frozen_source_SHA256', digest(ROOT/path)==expected,path)
    score, bg_receipt, params=(load(OUT/p) for p in ('score_completed.json','background_freeze.json','parameter_freeze.json'))
    assert score['complete'] and load(OUT/'score_once.json')['attempts']==1
    for path,expected in (score['SHA256']|bg_receipt['SHA256']).items():
        check('outcome_artifact_SHA256',digest(OUT/path)==expected,path)
    pred=rows(OUT/'predictions.csv')
    bg=rows(OUT/'common_background.csv')
    metrics=rows(OUT/'metrics.csv')
    joint=rows(OUT/'joint.csv')
    delta=rows(OUT/'comparisons.csv')
    mi={(r['date'],int(r['cutoff']),r['window'],r['method'],r['region']):r for r in metrics}
    ji={(r['date'],int(r['cutoff']),r['window'],r['method']):r for r in joint}
    di={(r['date'],int(r['cutoff']),r['window'],r['comparison'],r['region']):r for r in delta}
    assert len(mi)==len(metrics)==576 and len(ji)==len(joint)==96 and len(di)==len(delta)==576
    assert len(pred)==len(bg)==5760
    assert {(x['date'],x['cutoff']) for x in design['eligible_windows']}=={(d,h) for d in ADMITTED for h in (6,18)}
    assert design['methods']==METHODS
    results={}
    for e,par,r in zip(design['eligible_windows'],params['windows'],bg_receipt['windows'],strict=True):
        day,h=e['date'],e['cutoff']
        assert day in ADMITTED and (day,h)==(par['date'],par['cutoff'])==(r['date'],r['cutoff'])
        key=(day,h)
        path=ROOT/e['original_global_path']
        check('global_parameter_SHA256',digest(path)==e['original_global_SHA256'],key)
        raw_doc=load(path)
        group=raw_doc['parameters']
        original=group.get('B14',group)[f'GlobalAdaptive{h:02d}']
        check('original_coefficient_identity',raw_doc['date']==day and original['N']==360
              and original['status']=='SUPPORTED' and original['b']==par['original']['b']
              and original['sample_SHA256']==par['original']['sample_sha256']==e['history_sample_SHA256'],key)
        cut=np.datetime64(f'{day}T{h:02d}:00','ns')
        ids=cut+np.arange(720)*np.timedelta64(30,'s')
        parts=[x for x in bg if (x['date'],int(x['cutoff']))==key]
        predicted=[x for x in pred if (x['date'],int(x['cutoff']))==key]
        for t,bb,pp in zip(ids,parts,predicted,strict=True):
            check('ordered_observation_ID',bb['utc']==pp['utc']==str(t)+'Z'
                  and bb['observation_ID']==pp['observation_ID']==f'Swarm/A/0301/{t}Z',str(t))
        cpath=ROOT/r['CDF']['path']
        check('CDF_SHA256',digest(cpath)==r['CDF']['SHA256'],key)
        c=CDF(cpath)
        assert c.varattsget('density')['UNITS']=='kg/m3' and c.globalattsget()['TIME SYSTEM']==['UTC']
        first=h*120
        last=first+719
        times=cdfepoch.to_datetime(c.varget('time',startrec=first,endrec=last)).astype('datetime64[ns]')
        check('CDF_UTC',np.array_equal(ids,times),key)
        obs=c.varget('density',startrec=first,endrec=last)
        lat=c.varget('latitude',startrec=first,endrec=last)
        flags=c.varget('validity_flag',startrec=first,endrec=last)
        check('quality_domain',np.all((flags==0)&np.isfinite(obs)&(obs>0)&(obs<1e30))
              and np.array_equal(lat,[float(x['latitude']) for x in parts]),key)
        assert all(int(x['flag'])==0 for x in parts)
        raw=np.array([float(x['background_kg_m3']) for x in parts])
        cached=ROOT/e['future_cache_path']
        check('cache_SHA256',digest(cached)==e['future_cache_SHA256'],key)
        cache_pos=360 if day=='2021-03-25' and h==6 else 1440 if day=='2021-03-25' else first
        old_key = ('B14_'+str(h)+'_' if day=='2021-03-25' else str(h)+'_' if day=='2022-03-25' else '')+f'GlobalAdaptive{h:02d}'
        with zipfile.ZipFile(cached) as z:
            original_p=packed_member(z,e['future_background_field'],cache_pos,720)
            original_global=packed_member(z,old_key,cache_pos,720)
            cache_observed=packed_member(z,'density',cache_pos,720)
        check('old_Raw_and_observation_exact',np.array_equal(original_p,raw)
              and np.array_equal(cache_observed,obs),key)
        series={}
        bands=np.abs(lat)
        elapsed=(times-cut).astype('timedelta64[s]').astype('int64')
        for method,value in METHODS.items():
            coefficients=par['methods'][method]
            b=value*original['b']
            mul=float(np.exp(b))
            check('lambda_and_multiplier',coefficients=={'lambda_':value,'b_shrink':b,'multiplier':mul}
                  and (method!='Global' or mul==original['multiplier']),(*key,method))
            estimate=np.array([float(x)*mul for x in original_p])
            trial=np.array([float(x[method]) for x in predicted])
            if method=='Global':
                check('old_Global_exact',np.array_equal(estimate,original_global),key)
            for index,(x,y) in enumerate(zip(trial,estimate)):
                check('exact_prediction_values',x==y,(*key,method,index,float(x),float(y)))
            series[method]=estimate
        for name,(a,b) in BOUNDS.items():
            membership=(elapsed>=3600*a)&(elapsed<3600*b)
            check('six_common_ID_hashes',id_hash(times[membership])==e['future_windows'][name]['original_ID_SHA256']
                  and int(membership.sum())==e['future_windows'][name]['N'],(*key,name))
            for region,subset in {'all':np.ones(720,bool),'low':bands<30,
                                   'mid':(bands>=30)&(bands<60),'high':bands>=60}.items():
                use=membership&subset
                n=int(use.sum())
                for method,p in series.items():
                    token=(*key,name,method,region)
                    row=mi[token]
                    status='OK' if n>=30 else 'N/A_INSUFFICIENT_SAMPLES'
                    check('sample_and_support',int(row['n'])==int(row['eligible'])==int(row['own_valid'])==n
                          and row['status']==status and (not n or (float(row['coverage'])==1
                          and float(row['common_coverage'])==1)),token)
                    computed=quantify(p[use],obs[use])
                    results[token]=(status,computed)
                    for field,value in computed.items():
                        same(token,field,row[field],value)

    for token,row in ji.items():
        day,h,window,method=token
        old,raw=results[day,h,window,'Raw','all']
        new,value=results[day,h,window,method,'all']
        all_ok=all(results[day,h,window,m,r][0]=='OK' for m in ('Raw',method) for r in REGIONS)
        if not all_ok:
            check('joint_flags',row['JOINT_NO_REGRET']=='N/A_INSUFFICIENT_SAMPLES'
                  and row['status']=='N/A_INSUFFICIENT_SAMPLES'
                  and all(row[x]=='' for x in ('RMSE_BENEFIT','RELATIVE_RMS_BENEFIT',
                                          'TAIL_NONWORSENED','LOW_LATITUDE_BIAS_NONWORSENED')),token)
            continue
        r0=results[day,h,window,'Raw','low'][1]['relative_bias']
        r1=results[day,h,window,method,'low'][1]['relative_bias']
        cases=dict(RMSE_BENEFIT=value['RMSE']<raw['RMSE'],
            RELATIVE_RMS_BENEFIT=value['relative_RMS']<raw['relative_RMS'],
            TAIL_NONWORSENED=value['relative_P95']<=raw['relative_P95'],
            LOW_LATITUDE_BIAS_NONWORSENED=abs(r1)<=abs(r0))
        expected='PASS' if all(cases.values()) else 'FAIL'
        check('joint_flags',row['status']=='OK' and row['JOINT_NO_REGRET']==expected
              and all(row[name]==str(flag) for name,flag in cases.items()),token)
    for token,row in di.items():
        day,h,window,cmp,region=token
        target,base=cmp.split('_vs_')
        # Recheck algebra from independently validated published metrics to avoid
        # cancellation in percent-change arithmetic from an alternative sum order.
        prior=mi[day,h,window,base,region]
        now=mi[day,h,window,target,region]
        expected=dict.fromkeys(('RMSE_change_pct','relative_RMS_change_pct',
                               'relative_P95_change','abs_relative_bias_change'))
        if prior['status']==now['status']=='OK':
            x,y={k:float(prior[k]) for k in ('RMSE','relative_RMS','relative_P95','relative_bias')},{
                 k:float(now[k]) for k in ('RMSE','relative_RMS','relative_P95','relative_bias')}
            expected=dict(RMSE_change_pct=100*(y['RMSE']/x['RMSE']-1),
                          relative_RMS_change_pct=100*(y['relative_RMS']/x['relative_RMS']-1),
                          relative_P95_change=y['relative_P95']-x['relative_P95'],
                          abs_relative_bias_change=abs(y['relative_bias'])-abs(x['relative_bias']))
        for column,v in expected.items():
            same(token,column,row[column],v)
    out=dict(verified=not ERRORS,checks=dict(TESTS),total_checks=sum(TESTS.values()),errors=ERRORS,
             maximum_metric_differences=MAX_DIFF,rtol=1e-13,atol=0,
             scored_dates=sorted(ADMITTED),unseen_densities_read=0,method='original CDF plus independent scalar predictions, order statistics and reductions',
             UTC=datetime.now(timezone.utc).isoformat(),
             resources=dict(wall_seconds=monotonic()-wall,cpu_seconds=process_time()-cpu,
                 peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
    result_name='independent_verification.json' if not ERRORS else 'independent_discrepancies.json'
    with (OUT/result_name).open('x') as f:
        json.dump(out,f,indent=2)
        f.write('\n')
    print(result_name,out['total_checks'],sum(len(items) for items in ERRORS.values()))
    if ERRORS:
        raise SystemExit(1)


if __name__=='__main__':
    audit()
