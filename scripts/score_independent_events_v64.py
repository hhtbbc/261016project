"""One authorized V64-B evaluation. Requires the checked V64-A prediction lock."""
import hashlib
import json
from pathlib import Path

import numpy as np
from netCDF4 import Dataset, num2date

from evaluate_locked_events_v64 import evaluate, self_test
from run_independent_predictions_v64 import (
    METHODS, OUT, ROOT, RUNS, SHAPE, V62, V63, frozen, key, need, read_csv,
    readonly, save, sha, table, utc,
)
from verify_independent_predictions_v64 import verify

B=OUT/'evaluation_v64b'
LOCK='f66ed4fb06a2f849a32d6b10261f986f4826b9d802159fb011d1eeb2e226b47f'
START='69615b5beaac760d7b1d89c50d9436747de63172'


def preflight():
    fresh=verify()
    need(fresh==json.loads((OUT/'independent_lock_verification.json').read_text())
         and fresh['prediction_lock_SHA256']==LOCK,'Prediction lock or independent check drift')
    code=json.loads((OUT/'evaluation_code_SHA256.json').read_text())
    for path,checksum in code.items():
        need(sha(ROOT/path)==checksum,'Frozen evaluation code drift')
    for name in ('isolation_probe_results','cross_cutoff_probe_results'):
        probe=json.loads((OUT/f'{name}.json').read_text())
        need(len(probe)==2 and all(r['poison_invariant'] and len(r['rejections'])==12
                                  for r in probe.values()),'Isolation evidence incomplete')
        if name.startswith('cross'):
            need(all(len(r['actual_sibling_rejections'])==12 for r in probe.values()),'Sibling access evidence')
    method=json.loads((OUT/'frozen_method_protocol.json').read_text())
    need(tuple(method['methods'])==METHODS,'Method drift')
    for path,checksum in method['worker_source_SHA256'].items():
        need(sha(ROOT/'scripts'/path)==checksum,'Worker source drift')
    index=V63/'target_record_index.csv'
    index_sha=frozen(index)
    frozen(V63/'native_output_inventory.csv')
    frozen(V62/'low_density_thresholds.json')
    records=read_csv(index)
    volumes={(r['run_id'],r['file']):r for r in read_csv(V63/'native_output_inventory.csv')}
    checked={}
    for r in records:
        rid,name,pos=key(r)
        v=volumes[rid,name]
        need(r['stage']=='target' and rid==RUNS[r['event_id']] and v['kind']=='secondary'
             and v['sha256']==r['volume_SHA256'] and v['relative_directory']==r['relative_directory']
             and 0<=pos<int(v['records'])
             and (utc(r['UTC'])-utc(r['cutoff_UTC'])).total_seconds()==3600*int(r['lead_hours']),
             'Target source identity mismatch')
        p=ROOT/r['relative_directory']/name
        need(p.resolve()==p and p.is_file() and p.stat().st_mode&0o777==0o400
             and p.stat().st_uid==0 and p.stat().st_size==int(v['bytes']),'Volume custody mismatch')
        if p not in checked:
            checked[p]=sha(p)
        need(checked[p]==v['sha256'],'Volume SHA mismatch')
    return records,index_sha,len(checked)


def read_target(row,grid):
    path=ROOT/row['relative_directory']/row['file']
    i=int(row['record'])
    with Dataset(path) as nc:
        den=nc['DEN']
        need(den.dimensions==('time','ilev','lat','lon') and den.shape[1:]==SHAPE
             and den.units=='g/cm3' and not {'scale_factor','add_offset'}&set(den.ncattrs()),'DEN descriptor')
        for axis in ('ilev','lat','lon'):
            need(np.array_equal(nc[axis][:],grid[axis]),f'Coordinate drift {axis}')
        t=nc['time']
        need(num2date(t[i],t.units).isoformat()+'Z'==row['UTC'],'Target UTC drift')
        den.set_auto_maskandscale(False)
        x=np.asarray(den[i,:,:,:])
        vals=np.asarray([getattr(den,k) for k in ('_FillValue','missing_value') if k in den.ncattrs()],
                        dtype=x.dtype).ravel()
        valid=np.isfinite(x)&(x>0)&~np.isin(x,vals)
        y=np.where(valid,x.astype(float)*1000,np.nan).astype('<f8')
        return y,row | dict(raw_slice_SHA256=hashlib.sha256(x.tobytes()).hexdigest(),
                           converted_slice_SHA256=hashlib.sha256(y.tobytes()).hexdigest(),
                           valid=int(valid.sum()),invalid=int((~valid).sum()),
                           native_units='g/cm3',output_units='kg/m3')


def write_metrics(y,p,samples,lat,threshold):
    rows=list(evaluate(y,p,samples,METHODS,lat,threshold))
    lookup={(r['group_key'],r['group'],r['lead_hours'],r['region'],r['mask'],r['method']):r for r in rows}
    for key_,r in lookup.items():
        for method,short in [('Persistence','P'),('LocalTimePersistence','LT')]:
            ref=lookup[(*key_[:-1],method)]
            for metric in ('rmse','log_rmse','relative_rmse','mae'):
                a,b=r[metric],ref[metric]
                r[f'{metric}_change_pct_vs_{short}']=100*(a/b-1) if a is not None and b else None
    event=[r for r in rows if r['group_key']=='event_id']
    global_rows=[r for r in event if r['region']=='global']
    table(B/'global_metrics.csv',global_rows)
    table(B/'event_metrics.csv',event)
    table(B/'cutoff_metrics.csv',[r for r in rows if r['group_key']=='cutoff_id'])
    table(B/'layer_metrics.csv',[r for r in event if r['region'].startswith('ilev')])
    table(B/'regional_metrics.csv',[r for r in event if r['region'] in ('north_polar','south_polar','low_density')])
    stats=[]
    for r in rows:
        if r['method'] in ('Persistence','LocalTimePersistence'):
            stats.append({k:r[k] for k in ('group_key','group','lead_hours','region','mask','method','valid_count')}
                         |dict(rms=r['log_rmse'],mean=neg(r['log_bias']),p05=neg(r['log_error_p95']),
                               p50=neg(r['log_error_p50']),p95=neg(r['log_error_p05'])))
    table(B/'local_time_residual_diagnostics.csv',stats)
    return lookup,global_rows


def neg(x):
    return -x if x is not None else None


def independent(y,p,samples,lat,lookup):
    n=0
    for event in RUNS:
        for h in (1,3,6):
            idx=[i for i,s in enumerate(samples) if s['event_id']==event and int(s['lead_hours'])==h]
            a=y[idx]
            b=p[:,idx]
            base=np.isfinite(a)&(a>0)
            valid=np.isfinite(b)&(b>0)
            paired=np.logical_and.reduce(valid)
            weights=np.cos(np.deg2rad(lat))[None,None,:,None]
            for m,name in enumerate(METHODS):
                for mask,ok in [('own',base&valid[m]),('common',base&paired)]:
                    r=lookup['event_id',event,h,'global',mask,name]
                    w=np.where(ok,weights,0)
                    denom=np.sum(w)
                    with np.errstate(divide='ignore',invalid='ignore'):
                        errors=b[m]-a
                        logs=np.log(b[m]/a)
                    abs_sse=np.sum(w*np.where(ok,errors**2,0))
                    log_sse=np.sum(w*np.where(ok,logs**2,0))
                    need(int(ok.sum())==r['valid_count'] and
                         np.allclose([abs_sse,log_sse],[r['sse'],r['log_sse']],rtol=1e-12,atol=0)
                         and np.allclose(np.sqrt([abs_sse/denom,log_sse/denom]),
                                         [r['rmse'],r['log_rmse']],rtol=1e-12,atol=0),
                         'Independent score mismatch')
                    layers=[lookup['event_id',event,h,f'ilev_{l:02}',mask,name] for l in range(29)]
                    need(sum(x['valid_count'] for x in layers)==r['valid_count']
                         and np.isclose(sum(x['sse'] or 0 for x in layers),abs_sse,rtol=1e-12,atol=0),
                         'Layer additivity')
                    n+=1
    return n


def main():
    need(B.resolve()==B and not B.exists(),'One-shot target opening already claimed')
    self_test()
    records,index_sha,volumes=preflight()
    grid=json.loads((OUT/'native_coordinates.json').read_text())
    forecast={(r['record_id'],r['method']):r for r in read_csv(OUT/'prediction_manifest.csv')}
    p=np.stack([np.stack([np.fromfile(OUT/forecast[r['record_id'],m]['file'],dtype='<f8').reshape(SHAPE)
                         for r in records]) for m in METHODS])
    thresholds=np.asarray(json.loads((V62/'low_density_thresholds.json').read_text())['thresholds'])
    B.mkdir(mode=0o755)
    local=B/'data_local'
    local.mkdir(mode=0o700)
    save(B/'phase_2_authorization.json',dict(scope='One V64-B evaluation of indexed model DEN and necessary metadata',
         v64a_commit=START,prediction_lock_SHA256=LOCK,target_index_SHA256=index_sha,target_records=21,
         passed_preflight=True,verified_volumes=volumes,Swarm_authorized=False))
    targets,receipt=[],[]
    with (local/'target_access.jsonl').open('x',buffering=1) as log:
        for r in records:
            log.write(json.dumps(dict(record_id=r['record_id'],attempt='exact_slice'))+'\n')
            y,row=read_target(r,grid)
            targets.append(y)
            receipt.append(row)
    y=np.stack(targets)
    readonly(local/'targets.bin',y.tobytes())
    table(B/'target_extraction_manifest.csv',receipt)
    lookup,global_rows=write_metrics(y,p,records,np.asarray(grid['lat']),thresholds)
    checks=independent(y,p,records,np.asarray(grid['lat']),lookup)
    save(B/'independent_verification.json',dict(global_rows_independently_recomputed=checks,
         layer_SSE_identity=True,confirmed_predictions=168,confirmed_target_records=21,
         target_cache_SHA256=sha(local/'targets.bin'),target_index_SHA256=index_sha,forecast_lock_SHA256=LOCK,
         nonpositive_target_cells=sum(r['invalid'] for r in receipt),Swarm_reads=0,GPU=0,training=0,new_integrations=0))
    print(f'{len(global_rows)} global rows, {checks} independent checks')


if __name__=='__main__':
    main()
