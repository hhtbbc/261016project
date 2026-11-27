"""Recompute all frozen V59 prediction fields and statistics from authorized records."""
from collections import Counter
from datetime import timedelta
import json
import os
from pathlib import Path

from netCDF4 import Dataset, num2date
import numpy as np

from run_native_density_baselines_v59 import (ROOT, OUT, LOCAL, V58, LEADS, METHODS, RUNS,
                                              SHAPE, digest, need, read_csv, save, sha, iso, utc)


def check_native():
    frozen={r['sample_id']:r for r in read_csv(V58/'prospective_mvp_split.csv')}
    samples=read_csv(OUT/'sample_manifest.csv')
    need(len(samples)==len(frozen)==24 and {r['sample_id'] for r in samples}==set(frozen),'Sample IDs')
    history={(r['source_run_id'],iso(utc(r['cutoff_UTC'])-timedelta(hours=i)))
             for r in samples for i in (1,2,3)}
    targets={(r['source_run_id'],r['prediction_target_UTC']) for r in samples}
    lock=json.loads((OUT/'prediction_lock.json').read_text())
    need(lock['locked_predictions']==24 and lock['target_reads_at_lock']==0 and
         lock['kernel_memfd_write_rejections']==24 and len(lock['kernel_probes'])==12 and
         lock['synthetic_poison_invariant'] and not lock['real_label_in_worker'] and
         lock['sample_manifest_sha256']==sha(OUT/'sample_manifest.csv'),'Prediction lock')
    ledger=read_csv(OUT/'den_read_ledger.csv')
    keys=[(r['source_run'],r['UTC']) for r in ledger]
    need(len(keys)==48 and set(keys[:24])==history and set(keys[24:])==targets and
         all(r['stage']=='historical_only' for r in ledger[:24]) and
         all(r['stage']=='trusted_evaluation_after_prediction_lock' for r in ledger[24:]),'DEN read scope')
    volumes={(r['run'],r['path']):r['SHA256'] for r in read_csv(V58/'model_volumes.csv')}
    frames={}
    for key,r in zip(keys,ledger):
        run,path=r['source_run'],r['path']
        n=int(r['record_index'])
        need(r['source_SHA256']==volumes[run,path] and (ROOT/path).parent==ROOT/run,'Record provenance')
        with Dataset(ROOT/path) as nc:
            t=nc['time']
            need(num2date(t[n],t.units).isoformat()+'Z'==r['UTC'],'Native clock')
            den=nc['DEN']
            need(den.units=='g/cm3' and nc['ZG'].dimensions==den.dimensions,'Native unit/grid')
            # Independent path uses the library's mask for file sentinels,
            # then separately rejects nonfinite and nonpositive values.
            physical=den[n,:,:,:].astype(np.float64).filled(np.nan)
        valid=np.isfinite(physical)&(physical>0)
        converted=np.where(valid,physical*1000.0,np.nan).astype('<f8')
        need(converted.shape==SHAPE and int(valid.sum())==int(r['valid_count']) and
             digest(converted.tobytes())==r['frame_SHA256'],'Independent native frame conversion')
        frames[key]=converted
    yy,pp=[],[]
    max_relative=0.
    for sample in samples:
        sid=sample['sample_id']
        need(all(sample[k]==v for k,v in frozen[sid].items()),'Frozen row differs')
        run=sample['source_run_id']
        when=sample['cutoff_UTC']
        need(sample['native_run_id']==RUNS[when[:4]],'Run crossover')
        expected_times=[iso(utc(when)-timedelta(hours=i)) for i in (3,2,1)]
        recent=np.stack([frames[run,t] for t in expected_times])
        anchor=LOCAL/('jail_'+when.replace(':',''))/'anchors.txt'
        need(sample['input_UTC']==';'.join(expected_times) and
             sha(anchor)==sample['input_SHA256']==digest(recent.tobytes()),'History SHA or UTC')
        lag=int(sample['horizon'])+1
        last=recent[-1]
        previous=recent[-2]
        with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
            expected=np.stack([last,last+lag*(last-previous),last*np.power(last/previous,lag)])
        file=LOCAL/'predictions'/(sid+'.bin')
        pred=np.fromfile(file,dtype='<f8').reshape((3,*SHAPE))
        need(sha(file)==sample['prediction_SHA256'] and (file.stat().st_mode&0o222)==0,'Archived prediction integrity')
        for i,m in enumerate(METHODS):
            need(digest(pred[i].tobytes())==sample[m+'_SHA256'],'Method SHA')
            need(np.array_equal(np.isfinite(pred[i]),np.isfinite(expected[i])) and
                 np.array_equal(pred[i]>0,expected[i]>0) and
                 np.allclose(pred[i],expected[i],rtol=8e-13,atol=0,equal_nan=True),'Worker baseline formula')
        good=np.isfinite(expected[2])&(expected[2]>0)
        max_relative=max(max_relative,float(np.max(np.abs(pred[2][good]/expected[2][good]-1))))
        truth=frames[run,sample['prediction_target_UTC']]
        need(sha(LOCAL/'targets'/(sid+'.bin'))==digest(truth.tobytes()),'Target archive changed')
        yy.append(truth)
        pp.append(pred)
    return samples,np.array(yy),np.array(pp),max_relative


def check_metrics(samples,y,p):
    coords=json.loads((OUT/'native_grid.json').read_text())
    lat=np.asarray(coords['lat'])
    w=np.broadcast_to(np.cos(lat*np.pi/180)[None,None,:,None],y.shape)
    target_ok=np.isfinite(y)&(y>0)
    pred_ok=np.isfinite(p)&(p>0)
    both=np.logical_and.reduce(pred_ok,axis=1)&target_ok
    rows=read_csv(OUT/'metrics.csv')
    worst=0.
    fields=('mae','rmse','bias','relative_rmse','log_rmse','max_abs','p95_abs')
    for r in rows:
        k=METHODS.index(r['method'])
        which=r['region']
        zones={'ALL':np.ones(lat.size,bool),'low':abs(lat)<30,'mid':(abs(lat)>=30)&(abs(lat)<60),
               'polar':abs(lat)>=60}
        layers=np.ones(SHAPE[0],bool)
        if r['ilev_index']!='ALL':
            layers[:]=False
            layers[int(r['ilev_index'])]=True
        subset=np.array([(r['year']=='ALL' or s['date'].startswith(r['year'])) and
                         r['horizon']==s['horizon'] for s in samples])
        region=subset[:,None,None,None]&layers[None,:,None,None]&zones[which][None,None,:,None]
        reference=region&target_ok
        include=region&(both if r['mask']=='common' else target_ok&pred_ok[:,k])
        forecast=p[:,k]
        n=int(include.sum())
        need(n==int(r['n']) and int(reference.sum())==int(r['target_n']) and
             int(np.count_nonzero(reference&~pred_ok[:,k]))==int(r['invalid']) and
             int(np.count_nonzero(reference&np.isfinite(forecast)&(forecast<=0)))==int(r['nonpositive']) and
             float(r['coverage'])==n/max(1,int(reference.sum())),'Validity and coverage')
        if not n:
            need(all(r[key]=='' for key in fields),'Missing region metric')
            continue
        truth=y[include]
        pred=forecast[include]
        weights=w[include]
        e=pred-truth
        a=abs(e)
        unique,inverse=np.unique(a,return_inverse=True)
        mass=np.bincount(inverse,weights=weights)
        p95=unique[np.searchsorted(np.cumsum(mass),.95*mass.sum())]
        m=(np.average(a,weights=weights),
           np.sqrt(np.average(e*e,weights=weights)),np.average(e,weights=weights),
           np.sqrt(np.average((e/truth)**2,weights=weights)),
           np.sqrt(np.average((np.log(pred)-np.log(truth))**2,weights=weights)),max(a),p95)
        for key,value in zip(fields,m):
            observed=float(r[key])
            need(np.isclose(observed,value,rtol=1e-11,atol=1e-24),f'Independent {key} failed: {r}')
            worst=max(worst,abs(observed-value)/max(abs(value),1e-24))
    need(len(rows)==1782,'Missing evaluation strata')
    return len(rows),worst


def main():
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    samples,y,p,error=check_native()
    metrics,worst=check_metrics(samples,y,p)
    save('independent.json',dict(samples=len(samples),cutoffs=len({r['cutoff_UTC'] for r in samples}),
          run_ids=RUNS,records_rechecked_within_original_scope=48,additional_distinct_records=0,
          metric_rows=metrics,max_log_linear_formula_relative_difference=error,max_metric_relative_difference=worst,
          Swarm_density_reads=0,GPU=0,AI_training=0,new_TIEGCM_runs=0))


if __name__=='__main__':
    main()
