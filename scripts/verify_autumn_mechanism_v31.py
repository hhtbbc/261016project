"""Independent scalar checks of V31 outputs and frozen V30 cache identity."""
import collections
import math
import time

import numpy as np

from diagnose_autumn_v31 import (
    ROOT, OUT, V30, SPRING, YEARS, BANDS, METHODS, TOL, load, rows, sha, require,
    resource_log, write_once,
)

BOUNDS={'history':(-3,0),'future_1h':(0,1),'future_3h':(0,3),'future_6h':(0,6),
        'block_0_1h':(0,1),'block_1_3h':(1,3),'block_3_6h':(3,6)}
TERMS=('raw_abs','corrected_abs','delta_abs','linear_abs','penalty_abs',
       'raw_rel','corrected_rel','delta_rel','linear_rel','penalty_rel',
       'raw_relative_bias','corrected_relative_bias')


def quantile(x,q):
    s=sorted(x)
    i=(len(s)-1)*q
    k=math.floor(i)
    return s[k]+(s[math.ceil(i)]-s[k])*(i-k)


def mask(t,year,h,name):
    lo,hi=BOUNDS[name] if name in BOUNDS else (int(name.split('_')[1]),int(name.split('_')[1])+1)
    center=np.datetime64(f'{year}-09-23T{h:02d}:00')
    return (t>=center+np.timedelta64(lo,'h'))&(t<center+np.timedelta64(hi,'h'))


def main():
    start=time.perf_counter()
    pins=load(OUT/'input_identity.json')['sha256']
    for n,h in pins.items():
        p=ROOT/n
        require(p.resolve()==p and sha(p)==h,'Changed input '+n)
    summary=load(OUT/'diagnostic_receipt.json')
    require(summary['formal_scores']==summary['new_prediction_arrays']==0,'Improper execution scope')
    arrays={}
    for y in YEARS:
        with np.load(V30/f'{y}_matched_local.npz') as f:
            a={k:f[k] for k in f.files}
        lat=a['latitude'].astype(float)
        a['latband']=np.where(abs(lat)<30,'low',np.where(abs(lat)<60,'mid','high'))
        a['residual']=np.log(a['density'].astype(float))-np.log(a['raw'].astype(float))
        arrays[y]=a
    failures=[]
    comparisons=0
    max_scaled=0.0
    def check(key,label,a,b,scale=None):
        nonlocal comparisons,max_scaled
        comparisons+=1
        if b is None:
            if a not in ('',None):failures.append(dict(key=repr(key),field=label,main=a,independent=None))
            return
        x=float(a)
        limit=max(abs(b),scale or 0)
        delta=abs(x-b)
        ratio=delta/limit if limit else (0.0 if delta==0 else math.inf)
        max_scaled=max(max_scaled,ratio)
        if ratio>TOL:
            failures.append(dict(key=repr(key),field=label,main=x,independent=b,scale=limit,
                                 difference=delta))
    hist_edges=np.r_[-np.inf,np.linspace(-4,4,81),np.inf]
    for r in rows(OUT/'autumn_residual_drift.csv'):
        y,h,name,reg=key=(int(r['year']),int(r['cutoff']),r['window'],r['region'])
        a=arrays[y];t=a['utc']
        region=np.ones(len(t),bool) if reg=='all' else a['latband']==reg
        g=mask(t,y,h,name)&region
        now=list(map(float,a['residual'][g]))
        past=list(map(float,a['residual'][mask(t,y,h,'history')&region]))
        check(key,'N',r['N'],len(now))
        good=len(now)>=30
        require(r['status']==('OK' if good else 'N/A_INSUFFICIENT_SAMPLES'),'Residual support changed')
        b_h=quantile(past,.5) if len(past)>=30 else None
        b_f=quantile(now,.5) if good else None
        expected=dict(b_H=b_h,b_F_descriptive=b_f if name!='history' else None,
                      delta_b=b_f-b_h if good and b_h is not None and name!='history' else None)
        if good:
            avg=math.fsum(now)/len(now)
            expected.update(mean=avg,median=b_f,P50=b_f,MAD=quantile([abs(x-b_f) for x in now],.5),
                std=math.sqrt(math.fsum((x-avg)**2 for x in now)/len(now)),
                positive_fraction=sum(x>0 for x in now)/len(now),negative_fraction=sum(x<0 for x in now)/len(now),
                **{label:quantile(now,q) for label,q in (('P05',.05),('P25',.25),('P75',.75),('P95',.95))})
        else:
            expected.update({name:None for name in ('mean','median','P50','MAD','std','positive_fraction','negative_fraction','P05','P25','P75','P95')})
        if good and b_h is not None:
            hist=lambda vals:collections.Counter(int(np.searchsorted(hist_edges,x,side='right')-1) for x in vals)
            hp,hn=hist(past),hist(now)
            expected['overlap']=math.fsum(min(hp[i]/len(past),hn[i]/len(now)) for i in set(hp)|set(hn))
        else:
            expected['overlap']=None
        expected.update(observed_mean=math.fsum(map(float,a['density'][g]))/len(now) if now else None,
                        height_mean_m=math.fsum(map(float,a['altitude'][g]))/len(now) if now else None,
                        north_fraction=int((a['latitude'][g]>=0).sum())/len(now) if now else None)
        for key2,v in expected.items():check(key,key2,r[key2],v,1 if key2!='observed_mean' else None)
    breakdown=collections.defaultdict(list)
    for r in rows(OUT/'stratified_contributions.csv'):
        key=(int(r['year']),int(r['cutoff']),r['window'],r['method'])
        breakdown[key].append(r)
    totals={}
    for r in rows(OUT/'window_decomposition.csv'):
        y,h,name,method=key=(int(r['year']),int(r['cutoff']),r['window'],r['method'])
        a=arrays[y]
        wm=mask(a['utc'],y,h,name)
        v=list(map(float,a['density'][wm]));p=list(map(float,a['raw'][wm]))
        c=list(map(float,a[method][wm]));n=len(v)
        b=list(a['latband'][wm])
        center=np.datetime64(f'{y}-09-23T{h:02d}:00')
        hr=list((a['utc'][wm]-center)/np.timedelta64(1,'h'))
        terms={k:[] for k in TERMS}
        for yy,pp,cc in zip(v,p,c):
            re=pp-yy;ce=cc-yy;step=cc-pp
            # This scalar path uses the stored step directly, independent of NumPy (a-1)*p.
            row=[re*re,ce*ce,(ce+re)*(ce-re),2*step*re,step*step,
                 (re/yy)**2,(ce/yy)**2,(ce/yy+re/yy)*(ce/yy-re/yy),
                 2*(step/yy)*(re/yy),(step/yy)**2,re/yy,ce/yy]
            for k,z in zip(TERMS,row):terms[k].append(z)
        means={k:math.fsum(seq)/n for k,seq in terms.items()}
        scale={k:math.fsum(abs(z) for z in seq)/n for k,seq in terms.items()}
        totals[key]=means,n,scale
        check(key,'N',r['N'],n)
        for k,val in means.items():
            extra=max(scale['raw_abs'],scale['corrected_abs']) if k.endswith('_abs') else max(scale['raw_rel'],scale['corrected_rel']) if k.endswith('_rel') else 1
            check(key,k,r[k],val,extra)
        left=[abs((pp-yy)/yy) for pp,yy in zip(p,v)]
        right=[abs((cc-yy)/yy) for cc,yy in zip(c,v)]
        base,cor=quantile(left,.95),quantile(right,.95)
        # Use the verified NumPy threshold for exact tie membership.
        base_threshold=float(r['raw_P95']);cor_threshold=float(r['corrected_P95'])
        for k,m in [('raw_P95',base),('corrected_P95',cor),('abs_raw_RMSE',math.sqrt(means['raw_abs'])),
                    ('abs_corrected_RMSE',math.sqrt(means['corrected_abs']))]:
            check(key,k,r[k],m)
        edges=[quantile(v,i/5) for i in range(1,5)]
        # Validate independent linear edges, then use table values for exact tied points.
        edge=[float(breakdown[key][0][f'q{i}']) for i in (20,40,60,80)]
        for i in range(4):check(key,'quintile_edges',edge[i],edges[i])
        bins=[sum(d>=t for t in edge)+1 for d in v]
        for q in breakdown[key]:
            axis,label=q['axis'],q['level']
            if axis=='all':idx=list(range(n))
            elif axis=='density':idx=[i for i,z in enumerate(bins) if z==int(label[1])]
            elif axis=='latitude':idx=[i for i,z in enumerate(b) if z==label]
            elif axis=='density_latitude':
                qbin,rb=label.split('_')
                idx=[i for i,z in enumerate(bins) if z==int(qbin[1]) and b[i]==rb]
            else:
                lo,hi=map(int,label[:-1].split('_'))
                idx=[i for i,x in enumerate(hr) if lo<=x<hi]
            for k,wanted in [('N',len(idx)),('N_window',n),('raw_tail_N',sum(left[i]>=base_threshold for i in idx)),
                ('corrected_tail_N',sum(right[i]>=cor_threshold for i in idx)),
                ('corrected_above_raw_P95_N',sum(right[i]>=base_threshold for i in idx)),
                ('observed_mean',math.fsum(v[i] for i in idx)/len(idx) if idx else None)]:
                check((key,axis,label),k,q[k],wanted)
            for k,seq in terms.items():
                check((key,axis,label),k,q[k],math.fsum(seq[i] for i in idx)/n,
                      max(scale[k],scale['raw_abs'],scale['corrected_abs']) if k.endswith('_abs')
                      else max(scale[k],scale['raw_rel'],scale['corrected_rel']) if k.endswith('_rel') else 1)
        for axis in ('density','latitude','time','density_latitude'):
            group=[x for x in breakdown[key] if x['axis']==axis]
            check(key,'partition_N_'+axis,sum(int(x['N']) for x in group),n)
            for k,z in means.items():
                check((key,axis),k,math.fsum(float(x[k]) for x in group),z,
                      max(scale[k],scale['raw_abs'],scale['corrected_abs']) if k.endswith('_abs')
                      else max(scale[k],scale['raw_rel'],scale['corrected_rel']) if k.endswith('_rel') else 1)
    for (year,h,name,method),(total,n,scale) in totals.items():
        parts={'future_1h':('block_0_1h',),'future_3h':('block_0_1h','block_1_3h'),
               'future_6h':('block_0_1h','block_1_3h','block_3_6h')}.get(name)
        if not parts:continue
        pp=[totals[year,h,p,method] for p in parts]
        key=(year,h,name,method)
        check(key,'disjoint_N',sum(row[1] for row in pp),n)
        for k,z in total.items():
            check(key,'disjoint_'+k,math.fsum(row[0][k]*row[1] for row in pp)/n,z,
                  max(row[2][k] for row in pp))
    identity=rows(OUT/'four_date_identity.csv')
    copied=rows(OUT/'frozen_joint_readonly.csv')
    raw=rows(OUT/'four_date_raw_frozen.csv')
    for record in identity:
        date,season=record['date'],record['season']
        y=int(date[:4])
        old=rows(SPRING[y]/'joint_assessment.csv') if season=='spring' else rows(V30/f'{y}_joint.csv')
        expected=[r for r in old if r.get('case','B14')=='B14' and r['window'].startswith('future_')]
        copied_date=[r for r in copied if r['date']==date]
        require(len(copied_date)==len(expected)==12 and all(
            all(x[k]==v for k,v in src.items()) for x,src in zip(copied_date,expected)),
            'Joint rows not exact frozen copies')
        require(sum(r['JOINT_NO_REGRET']=='PASS' for r in copied_date)==int(record['PASS']),
                'Frozen PASS tally differs')
        mr=(rows(SPRING[y]/'metrics.csv')+rows(SPRING[y]/'region_metrics.csv') if season=='spring'
            else rows(V30/f'{y}_metrics.csv'))
        expected=[r for r in mr if r.get('case','B14')=='B14' and r['method']=='Raw']
        actual=[r for r in raw if r['date']==date]
        require(len(expected)==len(actual) and all(
            all(row[k]==v for k,v in old.items()) for old,row in zip(expected,actual)),
            'Raw frozen copies changed')
    result=dict(PASS=not failures,status='MECHANISM_DIAGNOSTIC_COMPLETE_VERIFIED' if not failures else
                'MECHANISM_DIAGNOSTIC_INCONCLUSIVE',numeric_checks=comparisons,failures=failures,
                max_scale_normalized_difference=max_scaled,
                bounds='1e-12 times magnitude or decomposed term scale; residual fractions scale 1',
                frozen_input_sha_rechecked=len(pins),native_volumes_rehashed=66,
                joint_evaluations_recomputed=0,resources=resource_log(start))
    write_once(OUT/'independent_verification.json',result)
    require(not failures,'Independent diagnostics did not close')


if __name__=='__main__':
    main()
