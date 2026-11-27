"""Read only V59/V60 authorized DEN cache files. The event script has no DEN reader."""
import csv
import hashlib
import json
import os
from pathlib import Path
import resource
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
R59=ROOT/'experiments/thermosphere_native_density_baselines_v59'
R60=ROOT/'experiments/thermosphere_tiny_direct_cpu_v60'
OUT=ROOT/'experiments/thermosphere_direct_failure_event_v61'
SHAPE=(29,36,72)
METHODS=('Persistence','TwoFrameLinear','LogLinear','TinyDirectCNN')
H=(1,3,6)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def csvread(p):
    with p.open() as f:
        return list(csv.DictReader(f))


def table(name, rows):
    require(OUT.resolve()==OUT,'Output path')
    with (OUT/name).open('x',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]),lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def save(name, data):
    require(OUT.resolve()==OUT,'Output path')
    with (OUT/name).open('x') as f:
        json.dump(data,f,indent=2,allow_nan=False)
        f.write('\n')


def checked_array(path, digest, shape):
    data=path.read_bytes()
    require(path.resolve()==path and hashlib.sha256(data).hexdigest()==digest,'Cached array SHA')
    return np.frombuffer(data,dtype='<f8').reshape(shape)


def assets():
    for base in (R59,R60):
        manifest=json.loads((base/'publication_SHA256.json').read_text())
        require(all(sha(ROOT/p)==v for p,v in manifest.items()),'Frozen publication asset changed')
    receipt=json.loads((R60/'training_receipt.json').read_text())
    require(receipt['parameter_count']==1027 and
       sha(R60/'data_local/weights.pt')==receipt['weights_SHA256'] and
       sha(R60/'normalization.json')==receipt['normalization_SHA256'],'Frozen checkpoint/normalization')
    old={r['sample_id']:r for r in csvread(R59/'sample_manifest.csv')}
    identities={r['sample_id']:r for r in csvread(R60/'prediction_manifest.csv')}
    samples=csvread(R60/'sample_scope.csv')
    require(len(samples)==len(identities)==len(old)==24,'Frozen sample count')
    targets={(r['source_run'],r['UTC']):r['frame_SHA256'] for r in csvread(R59/'den_read_ledger.csv')
             if r['stage']=='trusted_evaluation_after_prediction_lock'}
    y,p,x=[],[],{}
    for r in samples:
        sid=r['sample_id']
        require(all(r[k]==v for k,v in old[sid].items()) and
                identities[sid]['weights_SHA256']==receipt['weights_SHA256'],'Frozen sample identity')
        a=R59/'data_local'
        b=R60/'data_local/inference'
        y.append(checked_array(a/'targets'/(sid+'.bin'),targets[r['source_run_id'],r['prediction_target_UTC']],SHAPE))
        base=checked_array(a/'predictions'/(sid+'.bin'),r['prediction_SHA256'],(3,*SHAPE))
        direct=checked_array(b/(sid+'.bin'),identities[sid]['SHA256'],SHAPE)
        p.append(np.concatenate([base,direct[None]]))
        cut=r['cutoff_UTC']
        if cut not in x:
            x[cut]=checked_array(a/('jail_'+cut.replace(':',''))/'anchors.txt',r['input_SHA256'],(3,*SHAPE))
    coords=json.loads((R59/'native_grid.json').read_text())
    return samples,np.array(y),np.array(p),x,coords,receipt


def desc(x):
    q=np.percentile(x,[5,50,95])
    return [float(np.mean(x)),*map(float,q),float(x.min()),float(x.max())]


def weighted(y,p,w):
    e=p-y
    le=np.log(p/y)
    z=float(w.sum())
    sse=float(np.sum(w*e**2))
    logsse=float(np.sum(w*le**2))
    return dict(weight_sum=z,sse=sse,log_sse=logsse,
         mae=float(np.sum(w*abs(e))/z),rmse=float(np.sqrt(sse/z)),
         bias=float(np.sum(w*e)/z),relative_rmse=float(np.sqrt(np.sum(w*(e/y)**2)/z)),
         log_rmse=float(np.sqrt(logsse/z)))


def main():
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    started=time.monotonic()
    samples,y,p,inputs,coords,receipt=assets()
    lat=np.array(coords['lat'])
    w=np.broadcast_to(np.cos(np.deg2rad(lat))[None,None,:,None],y.shape)
    target=np.isfinite(y)&(y>0)
    positive=np.isfinite(p)&(p>0)
    common=target&positive.all(axis=1)
    layers,regions,residual,shift,summary=[] ,[],[],[],[]
    zones={'ALL':np.ones(len(lat),bool),'low':abs(lat)<30,'mid':(abs(lat)>=30)&(abs(lat)<60),
           'south_polar':lat<=-60,'north_polar':lat>=60}
    global_defect=0.
    frozen={(r['year'],int(r['horizon']),r['method']):r for r in csvread(R60/'global_comparison.csv')
            if r['mask']=='common'}
    for year in ('2021','2022'):
        for h in H:
            ids=[i for i,r in enumerate(samples) if r['date'].startswith(year) and int(r['horizon'])==h]
            yy,ww=y[ids],w[ids]
            for k,method in enumerate(METHODS):
                pp=p[ids,k]
                for mask in ('own','common'):
                    use=(target[ids]&positive[ids,k]) if mask=='own' else common[ids]
                    d=weighted(yy[use],pp[use],ww[use])
                    if mask=='common':
                        require(all(np.isclose(d[m],float(frozen[year,h,method][m]),rtol=2e-11,atol=1e-25)
                                    for m in ('mae','rmse','log_rmse','bias','relative_rmse')),'V60 global metric discrepancy')
                    block=[]
                    for name,zone in zones.items():
                        for l in range(29):
                            field=yy[:,l,zone,:]
                            forecast=pp[:,l,zone,:]
                            ok=use[:,l,zone,:]
                            n=int(target[ids][:,l,zone,:].sum())
                            vals=weighted(field[ok],forecast[ok],ww[:,l,zone,:][ok])
                            r=dict(year=year,horizon=h,method=method,mask=mask,region=name,
                                   ilev_index=l,ilev=coords['ilev'][l],target_n=n,valid_n=int(ok.sum()),
                                   coverage=float(ok.sum()/n),**vals,sse_share=vals['sse']/d['sse'],
                                   log_sse_share=vals['log_sse']/d['log_sse'])
                            for prefix,data in [('target',field[ok]),('prediction',forecast[ok])]:
                                r.update({prefix+'_'+key:v for key,v in zip(('mean','p5','p50','p95','min','max'),desc(data))})
                            (block if name=='ALL' else regions).append(r)
                    global_defect=max(global_defect,abs(sum(r['sse'] for r in block)/d['sse']-1),
                                      abs(sum(r['log_sse'] for r in block)/d['log_sse']-1))
                    layers.extend(block)
            b=p[ids,0]
            d=p[ids,3]
            good=common[ids]
            ex=(d-yy)**2*ww
            eb=(b-yy)**2*ww
            diff=np.sum(np.where(good,ex-eb,0),axis=(0,2,3))
            totalgain=-float(diff.sum())
            top=np.argsort(diff)[:3]
            direct_log=np.log(d[good]/yy[good])
            base_log=np.log(b[good]/yy[good])
            tail=abs(direct_log)>=np.quantile(abs(direct_log),.99)
            mass=ww[good]
            log_delta=mass*(direct_log**2-base_log**2)
            summary.append(dict(year=year,horizon=h,net_sse_reduction=totalgain,top_layers=top.tolist(),
                top_layer_reductions=(-diff[top]).tolist(),top_layer_pct_net=(-100*diff[top]/totalgain).tolist(),
                worsened_sse=float(diff[diff>0].sum()),worsened_layers=int((diff>0).sum()),
                worsened_log_layers=int(sum((r['log_sse']>next(q['log_sse'] for q in reversed(layers)
                    if q['year']==year and q['horizon']==h and q['method']=='Persistence' and
                    q['mask']=='common' and q['ilev_index']==r['ilev_index']))
                    for r in layers[-29:])),log_sse_delta=float(log_delta.sum()),
                untrimmed_direct_log_rmse=float(np.sqrt(np.average(direct_log**2,weights=mass))),
                top1pct_direct_log_sse_share=float(np.sum(mass[tail]*direct_log[tail]**2)/np.sum(mass*direct_log**2)),
                trim99_direct_log_rmse=float(np.sqrt(np.average(direct_log[~tail]**2,weights=mass[~tail]))),
                trim99_persistence_log_rmse=float(np.sqrt(np.average(base_log[~tail]**2,weights=mass[~tail])))))
    reference={(r['year'],r['horizon'],r['mask'],r['ilev_index']):r['sse'] for r in layers if r['method']=='Persistence'}
    for r in layers:
        r['delta_sse_vs_persistence']=r['sse']-reference[r['year'],r['horizon'],r['mask'],r['ilev_index']]
    for i,r in enumerate(samples):
        for l in (0,10,28,-1):
            for region,zone in zones.items():
                for j,m in enumerate(METHODS):
                    q=p[i,j]
                    ok=common[i].copy()
                    ok[:,~zone,:]=False
                    if l>=0:
                        ok[np.arange(29)!=l]=False
                    yy,pp,last=y[i][ok],q[ok],p[i,0][ok]
                    a=np.log(pp/last)
                    b=np.log(yy/last)
                    le=a-b
                    wgt=w[i][ok]
                    corr=float(np.corrcoef(a,b)[0,1]) if np.std(a)>0 and np.std(b)>0 else ''
                    ratios=np.percentile(pp/yy,[1,5,50,95,99])
                    avg=lambda data:float(np.average(data,weights=wgt))
                    residual.append(dict(cutoff=r['cutoff_UTC'],target_UTC=r['prediction_target_UTC'],horizon=r['horizon'],
                        layer='ALL' if l<0 else l,region=region,method=m,n=len(yy),
                        weighted_log_bias=avg(le),weighted_log_rmse=float(np.sqrt(avg(le**2))),
                        pred_residual_rms=float(np.sqrt(avg(a**2))),true_residual_rms=float(np.sqrt(avg(b**2))),
                        residual_correlation=corr,positive_fraction=float(np.mean(le>0)),negative_fraction=float(np.mean(le<0)),
                        improved_abs_fraction=float(np.mean(abs(pp-yy)<abs(last-yy))),
                        worsened_abs_fraction=float(np.mean(abs(pp-yy)>abs(last-yy))),
                        **dict(zip(('ratio_p1','ratio_p5','ratio_p50','ratio_p95','ratio_p99'),map(float,ratios)))))
    n=json.loads((R60/'normalization.json').read_text())
    for year in ('2021','2022'):
        x=np.stack([a for c,a in inputs.items() if c.startswith(year)])
        for l in range(29):
            z=(np.log(x[:,:,l])-n['mean'][l])/n['std'][l]
            shift.append(dict(year=year,ilev_index=l,ilev=coords['ilev'][l],
               mean=float(z.mean()),sd=float(z.std()),p5=float(np.quantile(z,.05)),p50=float(np.median(z)),
               p95=float(np.quantile(z,.95)),fraction_outside_3=float(np.mean(abs(z)>3))))
    require(global_defect<2e-14,'Layer SSE decomposition failed')
    table('layer_error_contribution.csv',layers)
    table('regional_error_comparison.csv',regions)
    table('residual_quantiles.csv',residual)
    table('input_distribution_shift.csv',shift)
    save('sse_summary.json',summary)
    save('numerical_checks.json',dict(distinct_targets=24,cutoffs=8,weights_SHA256=receipt['weights_SHA256'],
         max_relative_layer_closure=global_defect,frozen_global_metrics_checked=24,threads=len(os.sched_getaffinity(0)),
         seconds=time.monotonic()-started,peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
         new_DEN_labels=0,Swarm_reads=0,training=0,GPU=0,integrations=0))


if __name__=='__main__':
    main()
