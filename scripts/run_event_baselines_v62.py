"""Three predetermined no-fit predictions from authorized V59 historical inputs."""
import json
import os
import resource
import time
from datetime import timedelta

import numpy as np

from analyze_direct_event_v61 import assets, checked_array, R59, R60, H, SHAPE, METHODS, weighted
from analyze_direct_event_v61 import require, sha, csvread
from build_non_target_horizon_index_v56 import ROOT, utc, iso

OUT=ROOT/'experiments/thermosphere_independent_event_production_v62'
LOCAL=OUT/'data_local'
NEW=('ThreeFrameOLSLog','DampedLogTrend','LocalTimePersistence')
TAU_H=3.0


def save(name, payload):
    require(OUT.resolve()==OUT,'Unsafe output directory')
    with (OUT/name).open('x') as f:
        json.dump(payload,f,indent=2,allow_nan=False)
        f.write('\n')


def table(name, records):
    import csv
    require(OUT.resolve()==OUT,'Unsafe output directory')
    with (OUT/name).open('x',newline='') as f:
        w=csv.DictWriter(f,list(records[0]),lineterminator='\n')
        w.writeheader()
        w.writerows(records)


def rotate(z, cells):
    i=int(np.floor(cells))
    a=cells-i
    return (1-a)*np.roll(z,-i,axis=-1)+a*np.roll(z,-i-1,axis=-1)


def forecast(history,lead,spacing):
    z=np.log(history)
    slope=(z[2]-z[0])/2
    elapsed=lead+1
    return np.exp(np.stack([z.mean(axis=0)+(lead+2)*slope,
                        z[2]+TAU_H*(-np.expm1(-elapsed/TAU_H))*slope,
                        rotate(z[2],15*elapsed/spacing)]))


def main():
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    t=time.monotonic()
    require(not (OUT/'new_baseline_protocol.json').exists(),'Frozen protocol already present')
    save('new_baseline_protocol.json',dict(
        A='OLS z on UTC offsets -3,-2,-1; intercept at -2 equals mean(z); slope=(z[-1]-z[-3])/2; forecast mean+(h+2)*slope',
        B='Latest z plus slope*tau*(1-exp(-(h+1)/tau)); fixed exponential trend memory tau=3h, one 3h forcing interval; not learned',
        C='NOT_EXECUTED: lawful new history request at t+h-24h; no prior target repurposing',
        D='Solar local phase lon+15*UTC_hours. Sample east-positive source longitude lon+15*(h+1), wrap 360, linear interpolation of log density',
        newer_parameters=0,tuning='none; all formulas frozen before opening target data',
        low_density='per native level fifth percentile of authorized 2021 target values, frozen after predictions',
        weights='cos(latitude); own and all-method common validity; separately report finite nonpositive',
        roles='2021/2022 prior historical engineering data; no independent test'))
    reference=np.arange(8)
    require(np.array_equal(rotate(reference,1),np.r_[1:8,0]) and
            np.isclose(rotate(reference,.5)[-1],3.5),'Sign or periodic seam')
    lon=np.arange(0,360,5.)
    phase=np.cos(np.deg2rad(lon))
    require(np.allclose(rotate(phase,15*4/5),np.cos(np.deg2rad(lon+60)),atol=1e-14),'Local phase direction')
    coords=json.loads((R59/'native_grid.json').read_text())
    spacing=np.diff(coords['lon'])
    require(np.allclose(spacing,5) and len(coords['lon'])*spacing[0]==360,'Longitude spacing changed')
    rows=csvread(R60/'sample_scope.csv')
    hashes=[]
    output=[]
    request=[]
    for r in rows:
        c=r['cutoff_UTC']
        h=int(r['horizon'])
        x=checked_array(R59/'data_local'/('jail_'+c.replace(':',''))/'anchors.txt',r['input_SHA256'],(3,*SHAPE))
        y=forecast(x,h,spacing[0])
        require(np.all(np.isfinite(y)&(y>0)),'Nonpositive/no-fit forecast')
        p=LOCAL/('baseline_'+r['sample_id']+'.bin')
        with p.open('xb') as f:
            f.write(y.astype('<f8').tobytes())
        p.chmod(0o444)
        hashes.append(dict(sample_id=r['sample_id'],prediction_SHA256=sha(p)))
        output.append(y)
        request.append(dict(sample_id=r['sample_id'],source_run_id=r['source_run_id'],
             required_history_UTC=iso(utc(r['prediction_target_UTC'])-timedelta(hours=24)),
             cutoff_UTC=c,status='NOT_AUTHORIZED_FOR_C'))
    table('new_baseline_predictions_sha.csv',hashes)
    table('periodic_history_authorization_request.csv',request)
    save('baseline_prediction_lock.json',dict(protocol_SHA256=sha(OUT/'new_baseline_protocol.json'),
           manifest_SHA256=sha(OUT/'new_baseline_predictions_sha.csv'),target_reads_before_lock=0))
    checked,y,old,_,_,_=assets()
    require(rows==checked,'Frozen sample order')
    p=np.concatenate([old,np.array(output)],axis=1)
    w=np.broadcast_to(np.cos(np.deg2rad(coords['lat']))[None,None,:,None],y.shape)
    good=np.isfinite(p)&(p>0)
    both=np.all(good,axis=1)&np.isfinite(y)&(y>0)
    lat=np.asarray(coords['lat'])
    base=y[[r['date'].startswith('2021') for r in rows]]
    floors=np.percentile(base,5,axis=(0,2,3))
    save('low_density_thresholds.json',dict(unit='kg/m3',trained_model_parameters=0,source='2021 engineering target P5 only',thresholds=floors.tolist()))
    bucket={k:[] for k in ('baseline_metrics.csv','baseline_layer_metrics.csv','baseline_region_metrics.csv')}
    for yr in ('2021','2022'):
        for h in H:
            ii=[i for i,r in enumerate(rows) if r['date'].startswith(yr) and int(r['horizon'])==h]
            yy=y[ii];ww=w[ii]
            zones=[('global',np.ones(yy.shape,bool),'baseline_metrics.csv')]
            for l in range(SHAPE[0]):
                zones.append((str(l),np.broadcast_to((np.arange(SHAPE[0])==l)[None,:,None,None],yy.shape),'baseline_layer_metrics.csv'))
            zones.extend([(z,np.broadcast_to(latmask[None,None,:,None],yy.shape),'baseline_region_metrics.csv')
                          for z,latmask in [('north_polar',lat>=60),('south_polar',lat<=-60),('low_latitude',abs(lat)<30),
                                          ('mid_latitude',(abs(lat)>=30)&(abs(lat)<60))]])
            zones.append(('low_density',yy<=floors[None,:,None,None],'baseline_region_metrics.csv'))
            for z,area,filename in zones:
                for mask in ('own','common'):
                    v=(both[ii] if mask=='common' else good[ii,0])&area
                    ref=weighted(yy[v],p[ii,0][v],ww[v])
                    for k,m in enumerate((*METHODS,*NEW)):
                        mv=(both[ii] if mask=='common' else good[ii,k])&area
                        d=weighted(yy[mv],p[ii,k][mv],ww[mv])
                        bucket[filename].append(dict(year=yr,horizon=h,region=z,mask=mask,method=m,
                         n=int(mv.sum()),coverage=float(mv.sum()/area.sum()),
                         nonpositive=int(np.count_nonzero(area&np.isfinite(p[ii,k])&(p[ii,k]<=0))),
                         **d,rmse_pct_vs_persistence=100*(d['rmse']/ref['rmse']-1),
                         log_rmse_pct_vs_persistence=100*(d['log_rmse']/ref['log_rmse']-1)))
    for name,records in bucket.items():
        table(name,records)
    save('baseline_resources.json',dict(seconds=time.monotonic()-t,RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        completed=list(NEW),C='NOT_EXECUTED',authorized_target_count=24,new_DEN_records=0,GPU=0,training=0,integrations=0))


if __name__=='__main__':
    main()
