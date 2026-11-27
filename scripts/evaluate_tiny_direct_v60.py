"""Isolated inference, then a locked same-mask comparison with V59."""
import json
import os
import subprocess
import time

import numpy as np

from train_tiny_direct_v60 import OUT,LOCAL,ROOT,save,table,read_history,read_targets
import run_native_density_baselines_v59 as v59

METHODS=(*v59.METHODS,'TinyDirectCNN')


def groups(samples,coords):
    lat=np.asarray(coords['lat'])
    for year in ('2021','2022'):
        for h in v59.LEADS:
            indices=[i for i,r in enumerate(samples) if r['date'].startswith(year) and int(r['horizon'])==h]
            for region,where in [('ALL',np.ones(lat.size,bool)),('low',abs(lat)<30),
                                 ('mid',(abs(lat)>=30)&(abs(lat)<60)),('polar',abs(lat)>=60)]:
                for layer in (['ALL',*range(v59.SHAPE[0])] if region=='ALL' else ['ALL']):
                    layers=range(v59.SHAPE[0]) if layer=='ALL' else [layer]
                    yield (year,h,region,str(layer)),np.ix_(indices,layers,np.flatnonzero(where),range(v59.SHAPE[2]))


def run():
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    train=json.loads((OUT/'training_receipt.json').read_text())
    v59.need(v59.sha(LOCAL/'weights.pt')==train['weights_SHA256'] and
             v59.sha(LOCAL/'model.bin')==train['packet_SHA256'] and
             v59.sha(OUT/'normalization.json')==train['normalization_SHA256'],'Frozen model bundle drift')
    v59.need(not (LOCAL/'inference').exists(),'One-shot prediction already started')
    folder=LOCAL/'inference'
    folder.mkdir(mode=0o700)
    binary=folder/'worker'
    subprocess.run(['/usr/bin/gcc','-static','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror',
         str(ROOT/'scripts/tiny_direct_worker_v60.c'),'-lm','-o',str(binary)],
         env={'PATH':'/usr/bin:/bin','TMPDIR':str(folder)},check=True)
    samples=v59.read_csv(OUT/'sample_scope.csv')
    scope={k:[r for r in samples if r['cutoff_UTC']==k] for k in sorted({r['cutoff_UTC'] for r in samples})}
    v59.need(len(scope)==8 and sum(len(r) for r in scope.values())==24,'Invalid inference scope')
    sentinel=folder/'future.csv'
    sentinel.write_bytes(b'only synthetic placeholder')
    handles={}
    predictions=[]
    timings=[]
    for cut,rows in scope.items():
        jail=folder/('cutoff_'+cut.replace(':',''))
        jail.mkdir()
        history=read_history(cut,rows)
        input_hash=v59.readonly(jail/'anchors.txt',history.tobytes())
        v59.readonly(jail/'model.bin',(LOCAL/'model.bin').read_bytes())
        test=not predictions
        if test:
            (jail/'escape').symlink_to(sentinel)
        jail.chmod(0o555)
        if test:
            target=v59.LOCAL/'targets'/(next(r['sample_id'] for r in samples if r['date'].startswith('2022'))+'.bin')
            raw=ROOT/next(r['source_run_id'] for r in samples if r['date'].startswith('2022'))/'secondary_015.nc'
            probes=v59.worker(binary,jail,sentinel,target,raw).decode().splitlines()
            v59.need(len(probes)==12,'Isolation probes failed')
        t=time.monotonic()
        stream=v59.worker(binary,jail)
        elapsed=time.monotonic()-t
        if test:
            sentinel.write_bytes(b'poisoned synthetic placeholder')
            v59.need(v59.worker(binary,jail)==stream,'Poison affected forecast')
        t=time.monotonic()
        v59.worker(v59.LOCAL/'worker',jail)
        baseline_elapsed=time.monotonic()-t
        timings.append(dict(cutoff=cut,CNN_seconds=elapsed,three_baselines_seconds=baseline_elapsed))
        v59.need(len(stream)==3*np.prod(v59.SHAPE)*8,'Invalid worker payload')
        array=np.frombuffer(stream,dtype='<f8').reshape(3,*v59.SHAPE)
        v59.need(np.all(np.isfinite(array)&(array>0)),'Invalid predicted densities')
        for r,density in zip(rows,array):
            k=r['sample_id']
            payload=density.tobytes()
            handle=v59.seal(payload)
            path=folder/(k+'.bin')
            checksum=v59.readonly(path,payload)
            handles[k]=(handle,path,checksum)
            predictions.append(dict(sample_id=k,cutoff_UTC=cut,horizon=r['horizon'],target_UTC=r['prediction_target_UTC'],
                 input_SHA256=input_hash,weights_SHA256=train['weights_SHA256'],SHA256=checksum))
    table('prediction_manifest.csv',predictions)
    (OUT/'prediction_manifest.csv').chmod(0o444)
    table('inference_timings.csv',timings)
    save('evaluation_prediction_lock.json',dict(n=len(handles),worker_SHA256=v59.sha(binary),
         prediction_manifest_SHA256=v59.sha(OUT/'prediction_manifest.csv'),
         weight_packet_SHA256=train['packet_SHA256'],lock_checks=len(handles),kernel_probes=probes,
         synthetic_poison_invariant=True,validation_targets_read_before_lock=0))
    y,p=[],[]
    for row in samples:
        sid=row['sample_id']
        y.append(read_targets([row],row['date'][:4])[0])
        old=v59.LOCAL/'predictions'/(sid+'.bin')
        v59.need(v59.sha(old)==row['prediction_SHA256'],'V59 baseline changed')
        fd,path,checksum=handles[sid]
        value=os.pread(fd,int(np.prod(v59.SHAPE))*8,0)
        os.close(fd)
        v59.need(v59.digest(value)==checksum==v59.sha(path),'Direct prediction SHA')
        p.append(np.concatenate((np.fromfile(old,dtype='<f8').reshape(3,*v59.SHAPE),
                                 np.frombuffer(value,dtype='<f8').reshape(1,*v59.SHAPE))))
    v59.need(all(v59.sha(path)==checksum for _,path,checksum in handles.values()),'Post-evaluation mutation')
    y,p=np.stack(y),np.stack(p)
    v59.need(all(np.any(p[i,3]!=p[i,0]) for i in range(len(samples))),'CNN degenerated to persistence')
    coords=json.loads((v59.OUT/'native_grid.json').read_text())
    w=np.broadcast_to(np.cos(np.deg2rad(coords['lat']))[None,None,:,None],y.shape)
    valid=np.isfinite(p)&(p>0)
    ok=np.isfinite(y)&(y>0)
    common=ok&valid.all(axis=1)
    old={(r['year'],int(r['horizon']),r['region'],r['ilev_index'],r['method'],r['mask']):r
         for r in v59.read_csv(v59.OUT/'metrics.csv')}
    results=[]
    for key,ix in groups(samples,coords):
        for j,m in enumerate(METHODS):
            density=p[:,j][ix]
            for mask in ('own','common'):
                use=(ok&valid[:,j] if mask=='own' else common)[ix]
                metrics=v59.statistics(y[ix],density,w[ix],ok[ix],use)
                if j<3:
                    original=old[(*key,m,mask)]
                    v59.need(all(np.isclose(float(original[k]),val,rtol=1e-11,atol=1e-24)
                                 for k,val in metrics.items() if val is not None),'V59 subset mismatch')
                results.append(dict(year=key[0],horizon=key[1],region=key[2],ilev_index=key[3],method=m,
                     mask=mask,nonpositive=int(np.count_nonzero(np.isfinite(density)&(density<=0))),
                     nonfinite=int(np.count_nonzero(~np.isfinite(density))),**metrics))
    table('metrics.csv',results)
    table('global_comparison.csv',[r for r in results if r['region']==r['ilev_index']=='ALL'])
    save('evaluation_receipt.json',dict(validation_cutoffs=4,validation_targets_read_after_lock=12,
         prediction_files=24,rows=len(results),all_direct_positive=True,
         metrics='cos(latitude), native pressure grid, exact V59 year/lead masks',
         additional_distinct_native_records=0,Swarm_reads=0,GPU=0,new_integrations=0,formal_scoring=0))


if __name__=='__main__':
    run()
