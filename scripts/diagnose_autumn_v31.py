"""Exploratory diagnostics on immutable V30 predictions; no prediction or scoring entry."""
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import resource
import subprocess
import sys
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from evaluation.late_day_correction import diagnostic_quintiles
from evaluation.residual_representativeness import statistics, overlap, OVERLAP_EDGES
from runtime.tiegcm_rank_exit import digest as sha,write_once

EXP=ROOT/'experiments'
V30=EXP/'thermosphere_autumn_density_validation_v30'
OUT=EXP/'thermosphere_spring_autumn_failure_mechanism_v31'
HEAD='54a3d65278e0be3f8db461fb0258e37693e235e2'
YEARS=(2021,2022)
BANDS=('low','mid','high')
WINDOWS={'history':(-3,0),'future_1h':(0,1),'future_3h':(0,3),'future_6h':(0,6),
         'block_0_1h':(0,1),'block_1_3h':(1,3),'block_3_6h':(3,6)}
METHODS={6:('GlobalAdaptive06',),18:('GlobalAdaptive18','LatitudeAdaptive18','Stale06')}
SPRING={2021:EXP/'causal_density_new_date_validation_v1',2022:EXP/'tiegcm_2022_mar25_density_validation_v18'}
IDENTITY='EXPLORATORY / POST_HOC / HINDCAST / PROVISIONAL Map-A / EXTERNAL_DATUM_UNVERIFIED'
# Stable cancellation-aware double precision bounds, fixed before reading diagnostic outputs.
TOL=1e-12


def require(ok,message):
    if not ok:raise ValueError(message)


def load(p):
    return json.loads(p.read_text())


def rows(p):
    with p.open(newline='') as f:
        return list(csv.DictReader(f))


def table(name,data):
    with (OUT/name).open('x',newline='') as f:
        keys=list(dict.fromkeys(k for row in data for k in row))
        w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');w.writeheader();w.writerows(data)


def git_digest(p):
    return hashlib.sha256(subprocess.check_output(
        ['git','show',f'{HEAD}:{p.relative_to(ROOT)}'],cwd=ROOT)).hexdigest()


def bind(p,wanted,pins):
    require(p.resolve(strict=True)==p and sha(p)==wanted,f'File identity mismatch: {p.name}')
    pins[str(p.relative_to(ROOT))]=wanted


def protect():
    pins={}
    manifest=V30/'publication_SHA256.json'
    bind(manifest,git_digest(manifest),pins)
    for name,wanted in load(manifest).items():
        bind(ROOT/name,wanted,pins)
    source=load(V30/'source_manifest.json')
    for name,wanted in source['previous_SHA256'].items():
        bind(ROOT/name,wanted,pins)
    for item in source['science_sources'].values():
        bind(ROOT/item['path'],item['SHA256'],pins)
    for name in ('experiments/thermosphere_independent_date_validation_plan_v20/preregistered_protocol.json',
                 'reports/THERMOSPHERE_RESIDUAL_REPRESENTATIVENESS_V1.md',
                 'reports/THERMOSPHERE_AUTUMN_DENSITY_VALIDATION_V30.md',
                 'reports/TIEGCM_2022_MAR25_DENSITY_VALIDATION_V18.md',
                 'reports/TIEGCM_2022_MAR25_INDEPENDENT_VERIFICATION_V19.md'):
        p=ROOT/name;bind(p,git_digest(p),pins)
    for year in YEARS:
        info=source['years'][str(year)]
        for item in [*info['full_model'],info['CDF'],*map(info['frozen_inputs'].get,('input','source','GPI','hapi','executable'))]:
            bind(ROOT/item['path'],item['SHA256'],pins)
        score=load(V30/f'{year}_score_receipt.json')
        require(score['PASS'] and score['attempts']==1,'Expected one frozen V30 score')
        for name,wanted in score['outputs_SHA256'].items():
            bind(V30/name,wanted,pins)
        bind(V30/f'{year}_parameters.json',score['parameter_SHA256'],pins)
    for name in ('input_sources_2021.json','input_sources_2022.json'):
        path=EXP/'thermosphere_autumn_gpi_seed_policy_v22'/name
        bind(path,git_digest(path),pins)
        for source,wanted in load(path)['files'].items():
            bind(ROOT/source,wanted,pins)
    return pins


def read_pair(year):
    with np.load(V30/f'{year}_matched_local.npz') as f:
        data={k:f[k] for k in f.files}
    utc=data['utc'].astype('datetime64[ns]')
    begin=np.datetime64(f'{year}-09-23','ns')
    require(np.array_equal(utc,begin+np.arange(2880)*np.timedelta64(30,'s'))
            and data['quality'].all(),'Bad cached observation ID or quality')
    lat=data['latitude'].astype(float)
    band=np.digitize(abs(lat),[30,60])
    o=data['density'].astype(float);p=data['raw'].astype(float)
    require(np.isfinite(o).all() and np.isfinite(p).all() and (o>0).all() and (p>0).all(),'Bad frozen densities')
    return data,o,p,band


def window(h,name):
    lo,hi=WINDOWS[name] if name in WINDOWS else (int(name.split('_')[1]),int(name.split('_')[1])+1)
    ix=np.arange(2880)
    return (ix>=(h+lo)*120)&(ix<(h+hi)*120)


def factor(year,method,band):
    par=load(V30/f'{year}_parameters.json')['parameters']
    if method=='LatitudeAdaptive18':
        return np.array([par[method][BANDS[int(i)]]['multiplier'] for i in band])
    return np.full(len(band),par['GlobalAdaptive06' if method=='Stale06' else method]['multiplier'])


def decomposition(p,y,c,a):
    raw=p-y;corrected=c-y
    require(np.array_equal(c,a*p),'Frozen multiplier does not match cached prediction')
    abs_direct=corrected**2-raw**2
    linear=2*(a-1)*p*raw
    penalty=(a-1)**2*p**2
    gross=corrected**2+raw**2+abs(linear)+penalty
    require(np.all(abs(abs_direct-linear-penalty)<=TOL*gross),'Pointwise squared error identity')
    return dict(raw_abs=raw**2,corrected_abs=corrected**2,delta_abs=abs_direct,
                linear_abs=linear,penalty_abs=penalty,raw_rel=(raw/y)**2,
                corrected_rel=(corrected/y)**2,delta_rel=abs_direct/y**2,
                linear_rel=linear/y**2,penalty_rel=penalty/y**2,
                raw_relative_bias=raw/y,corrected_relative_bias=corrected/y)


def tail_masks(p,y,c):
    base=abs(p/y-1);corr=abs(c/y-1)
    # The frozen percentile uses (p-y)/y; preserve the same expression here.
    base=abs((p-y)/y);corr=abs((c-y)/y)
    q0,q1=np.quantile(base,.95),np.quantile(corr,.95)
    return q0,q1,base>=q0,corr>=q1,corr>=q0


def partition(o,band,h,name):
    bins,edges=diagnostic_quintiles(o)
    ix=np.flatnonzero(window(h,name))-h*120
    groups=[('all','all',np.ones(len(o),bool))]
    groups.extend(('density',f'Q{i+1}',bins==i) for i in range(5))
    groups.extend(('latitude',n,band==i) for i,n in enumerate(BANDS))
    groups.extend(('density_latitude',f'Q{i+1}_{n}',(bins==i)&(band==j))
                  for i in range(5) for j,n in enumerate(BANDS))
    groups.extend(('time',f'{lo}_{hi}h',(ix>=lo*120)&(ix<hi*120)) for lo,hi in ((0,1),(1,3),(3,6)))
    return groups,edges


def resource_log(start):
    return dict(wall_s=time.perf_counter()-start,CPU_s=time.process_time(),
                peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def main():
    start=time.perf_counter()
    require(ROOT==Path.cwd().resolve() and OUT.resolve()==OUT,'Bad output path')
    OUT.mkdir()
    pins=protect()
    status=load(V30/'result.json')
    require(status['status']=='SCIENTIFIC_EVALUATION_COMPLETE_VERIFIED','V30 not complete')
    identity=[];raw_rows=[];frozen_rows=[]
    for y in YEARS:
        for season in ('spring','autumn'):
            key=f'{y}_{season}'
            if season=='spring':
                data=rows(SPRING[y]/'metrics.csv')+rows(SPRING[y]/'region_metrics.csv')
                js=rows(SPRING[y]/'joint_assessment.csv')
            else:
                data=rows(V30/f'{y}_metrics.csv');js=rows(V30/f'{y}_joint.csv')
            selected=[r for r in js if r.get('case','B14')=='B14' and r['window'].startswith('future_')]
            counts=dict(collections.Counter(r['JOINT_NO_REGRET'] for r in selected))
            require(counts==status['per_date_joint'][key] and len(selected)==12,'Historical verdict changed')
            date=f'{y}-'+('03-25' if season=='spring' else '09-23')
            identity.append(dict(date=date,season=season,PASS=counts.get('PASS',0),FAIL=counts.get('FAIL',0),
                N_A=12-sum(counts.get(x,0) for x in ('PASS','FAIL')),case='B14',
                status='frozen_copy',role='historical_development_reference' if season=='spring'
                        else 'previously_scored_test_used_for_exploratory_diagnosis'))
            frozen_rows.extend(dict(date=date,season=season,**r) for r in selected)
            raw_rows.extend(dict(date=date,season=season,**r) for r in data
                            if r.get('case','B14')=='B14' and r['method']=='Raw')
    require([r['PASS'] for r in identity]==[1,8,0,6],'Unexpected frozen counts')
    write_once(OUT/'input_identity.json',dict(identity=IDENTITY,sha256=pins,formal_scores=0,
               corrected_arrays_reused=True,fit_new_coefficients=False))
    table('four_date_identity.csv',identity)
    table('four_date_raw_frozen.csv',raw_rows)
    table('frozen_joint_readonly.csv',frozen_rows)
    residual_rows=[];contrib=[];decomp_rows=[]
    for year in YEARS:
        a,o,p,band=read_pair(year)
        e=np.log(o)-np.log(p)
        regions={'all':np.ones(2880,bool),**{k:band==i for i,k in enumerate(BANDS)}}
        for h in (6,18):
            history=window(h,'history')
            for name in (*WINDOWS,*(f'hour_{i}' for i in range(-3,6))):
                wm=window(h,name)
                for region,rm in regions.items():
                    eh=e[history&rm];ef=e[wm&rm]
                    hs,fs=statistics(eh),statistics(ef)
                    good=fs['status']=='OK'
                    delta=fs['median']-hs['median'] if good and hs['median'] is not None else None
                    residual_rows.append(dict(year=year,cutoff=h,window=name,region=region,
                        b_H=hs['median'],b_F_descriptive=fs['median'] if name!='history' else None,
                        delta_b=delta if name!='history' else None,overlap=overlap(eh,ef),
                        P50=fs['median'],negative_fraction=float((ef<0).mean()) if good else None,
                        observed_mean=float(o[wm&rm].mean()) if (wm&rm).any() else None,
                        north_fraction=float((a['latitude'][wm&rm]>=0).mean()) if (wm&rm).any() else None,
                        height_mean_m=float(a['altitude'][wm&rm].mean()) if (wm&rm).any() else None,
                        **fs))
                if name=='history' or name.startswith('hour_'):continue
                obs=o[wm];raw=p[wm];groups,edges=partition(obs,band[wm],h,name)
                for method in METHODS[h]:
                    cor=a[method][wm];z=decomposition(raw,obs,cor,factor(year,method,band[wm]))
                    q0,q1,t0,t1,tx=tail_masks(raw,obs,cor)
                    key=dict(year=year,cutoff=h,window=name,method=method)
                    decomp_rows.append(dict(**key,N=len(obs),abs_raw_RMSE=float(np.sqrt(z['raw_abs'].mean())),
                        abs_corrected_RMSE=float(np.sqrt(z['corrected_abs'].mean())),
                        raw_P95=float(q0),corrected_P95=float(q1),
                        **{k:float(v.mean()) for k,v in z.items()}))
                    for axis,level,sel in groups:
                        contrib.append(dict(**key,axis=axis,level=level,N=int(sel.sum()),N_window=len(obs),
                            observed_mean=float(obs[sel].mean()) if sel.any() else None,
                            raw_tail_N=int((t0&sel).sum()),corrected_tail_N=int((t1&sel).sum()),
                            corrected_above_raw_P95_N=int((tx&sel).sum()),
                            q20=float(edges[1]),q40=float(edges[2]),q60=float(edges[3]),q80=float(edges[4]),
                            **{k:float(v[sel].sum()/len(obs)) for k,v in z.items()}))
    table('autumn_residual_drift.csv',residual_rows)
    table('window_decomposition.csv',decomp_rows)
    table('stratified_contributions.csv',contrib)
    write_once(OUT/'diagnostic_receipt.json',dict(PASS=True,identity=IDENTITY,
        residual_rows=len(residual_rows),decomposition_rows=len(decomp_rows),contribution_rows=len(contrib),
        formal_scores=0,new_prediction_arrays=0,GPU_calls=0,new_integrations=0,
        pointwise_tolerance=TOL,resources=resource_log(start)))


if __name__=='__main__':
    main()
