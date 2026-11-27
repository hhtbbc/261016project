"""One-shot, bounded native-grid experiment. All sources pinned to V58."""
import csv
import ctypes
from collections import defaultdict
from datetime import timedelta
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

from netCDF4 import Dataset, num2date
import numpy as np

from build_non_target_horizon_index_v56 import ROOT, V37, iso, pin, sha, utc
from check_external_evidence_v55 import check as handoff
from inventory_historical_density_v58 import OUT as V58

OUT = ROOT/'experiments/thermosphere_native_density_baselines_v59'
LOCAL = OUT/'data_local'
BASE = '8a8616d4562a98452cd82e38992f2bbbece59114'
SHAPE = (29,36,72)
METHODS = ('Persistence','TwoFrameLinear','LogLinear')
LEADS = (1,3,6)
HOUR = timedelta(hours=1)
RUNS = {'2021':'18726974f5d3450ba61f82c23c8da3a0','2022':'4a89e99eaee548f28240ea47f4b98e47'}
ELF = 'f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776'


def need(ok,message):
    if not ok:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_csv(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def table(path,rows):
    with (OUT/path).open('x',newline='') as stream:
        writer=csv.DictWriter(stream,list(rows[0]),lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def save(path,obj):
    with (OUT/path).open('x') as stream:
        json.dump(obj,stream,indent=2,allow_nan=False)
        stream.write('\n')


def inputs():
    manifest=V58/'publication_SHA256.json'
    need(manifest.read_bytes()==subprocess.check_output(['git','show',f'{BASE}:{manifest.relative_to(ROOT)}']),
         'V58 publication identity')
    frozen=json.loads(manifest.read_text())
    need(all(sha(ROOT/p)==h for p,h in frozen.items()),'V58 artifact changed')
    protocol=pin(V37)
    sealed=set(protocol['first_pair']+protocol['later_pair'])
    samples=read_csv(V58/'prospective_mvp_split.csv')
    sources=json.loads((V58/'prospective_mvp_sources.json').read_text())
    vols=read_csv(V58/'model_volumes.csv')
    old_runs={x['run']:x for x in json.loads((V58/'model_runs.json').read_text())}
    need(len(sources)==2 and len(samples)==len({s['sample_id'] for s in samples})==24,'Sample count')
    byrun={s['path']:s for s in sources}
    schedules={}
    for year,rid in RUNS.items():
        run=f'experiments/thermosphere_autumn_mareqx_config_v23/{year}/actual_run'
        s=byrun[run]
        folder=ROOT/run
        launch=folder/'launch_once.json'
        argv=json.loads(launch.read_text())['argv']
        flag=lambda name:argv[argv.index(name)+1]
        need(s['native_run_id']==flag('--run-id')==rid,'Run ID mismatch')
        need(sha(launch)==s['launch_receipt_SHA256'] and
             sha(Path(flag('--model')))==s['model_ELF_SHA256']==flag('--model-sha')==ELF and
             sha(folder/'input.inp')==flag('--input-sha'),'Launch provenance')
        gpi=ROOT/old_runs[run]['local_GPI_path']
        need(sha(gpi)==s['GPI_SHA256'],'GPI identity')
        volumes=sorted((r for r in vols if r['run']==run),key=lambda x:x['path'])
        need(len(volumes)==16,'Expected 16 secondary files')
        checks=[]
        schedule={}
        for row in volumes:
            path=ROOT/row['path']
            need(path.resolve()==path and path.parent==folder,'Volume path mismatch')
            checksum=sha(path)
            need(checksum==row['SHA256'],'Model volume bytes changed')
            checks.append((path.name,checksum))
            with Dataset(path) as nc:
                need(nc.data_model=='NETCDF3_CLASSIC','Storage layout changed')
                t=nc['time']
                times=num2date(t[:],t.units,getattr(t,'calendar','standard'))
                for index,k in enumerate(times):
                    key=k.isoformat()+'Z'
                    need(key not in schedule,'Duplicate UTC')
                    schedule[key]=(path,index,checksum)
        model_id=digest(json.dumps(checks,separators=(',',':')).encode())
        need(model_id==s['output_manifest_SHA256'],'Output manifest identity')
        schedules[run]=schedule
    grouped=defaultdict(list)
    for r in samples:
        run=r['source_run_id']
        c=utc(r['cutoff_UTC'])
        y=str(c.year)
        h=int(r['horizon'])
        target=iso(c+h*HOUR)
        need(r['date'] in (y+'-09-23',y+'-09-24') and r['date']==iso(c)[:10] and
             c.hour in (6,18) and not (c.minute or c.second or c.microsecond) and h in LEADS and
             target==r['prediction_target_UTC'] and target[:10] not in sealed and
             iso(c-3*HOUR)==r['input_start_UTC'] and iso(c)==r['input_end_UTC_exclusive'] and
             r['independent_science_test']=='NO' and r['source_SHA256']==byrun[run]['output_manifest_SHA256'] and
             r['split']==('engineering_train_candidate' if y=='2021' else 'engineering_validation_candidate'),
             'Frozen sample identity or scope drift')
        grouped[(run,iso(c))].append(r)
    history={(run,iso(utc(c)-i*HOUR)) for run,c in grouped for i in (1,2,3)}
    labels={(r['source_run_id'],r['prediction_target_UTC']) for r in samples}
    need(len(grouped)==8 and len(history)==len(labels)==24 and not history&labels,'Exact DEN authorization')
    need(all(when in schedules[run] for run,when in history|labels),'Time unavailable')
    return samples,byrun,schedules,grouped,history,labels,sha(manifest)


def frame(key,schedule,allow,phase,ledger,coordinates):
    need(key in allow,'Unauthorized DEN record')
    run,when=key
    path,index,checksum=schedule[run][when]
    with Dataset(path) as nc:
        den=nc['DEN']
        need(den.dimensions==nc['ZG'].dimensions==('time','ilev','lat','lon') and
             den.shape[1:]==SHAPE and den.units=='g/cm3' and not {'scale_factor','add_offset'}&set(den.ncattrs()),
             'Native coordinates or units changed')
        grid={name:np.asarray(nc[name][:],dtype=float) for name in ('ilev','lat','lon')}
        for name,axis in grid.items():
            need(np.isfinite(axis).all() and (np.diff(axis)>0).all(),'Invalid coordinate')
            need(name not in coordinates or np.array_equal(axis,coordinates[name]),'Moving native coordinates')
            coordinates[name]=axis
        need(np.array_equal(grid['lat'],np.arange(-87.5,90,5)) and
             np.allclose(np.diff(np.r_[grid['lon'],grid['lon'][0]+360]),5),'Latitude or cyclic longitude')
        t=nc['time']
        need(num2date(t[index],t.units).isoformat()+'Z'==when,'DEN timestamp mismatch')
        den.set_auto_maskandscale(False)
        raw=np.asarray(den[index,:,:,:])
        fill=np.array([getattr(den,a) for a in ('_FillValue','missing_value') if a in den.ncattrs()],dtype=raw.dtype)
        filled=np.isin(raw,fill)
        valid=np.isfinite(raw)&(raw>0)&~filled
        converted=np.where(valid,raw.astype(float)*1000,np.nan).astype('<f8')
        ledger.append(dict(stage=phase,source_run=run,UTC=when,path=str(path.relative_to(ROOT)),
          source_SHA256=checksum,record_index=index,source_units=den.units,converted_units='kg/m3',
          fill_values=';'.join(str(v) for v in fill),grid_points=raw.size,fill_count=int(filled.sum()),
          nonfinite_count=int((~np.isfinite(raw)).sum()),nonpositive_count=int(((raw<=0)&~filled).sum()),
          valid_count=int(valid.sum()),frame_SHA256=digest(converted.tobytes())))
    return converted


def readonly(path,data):
    with path.open('xb') as stream:
        stream.write(data)
    path.chmod(0o444)
    return digest(data)


def worker(binary,jail,*args):
    return subprocess.run([str(binary),str(jail),*map(str,args)],stdin=subprocess.DEVNULL,
        capture_output=True,close_fds=True,env={'LC_ALL':'C'},timeout=30,check=True).stdout


def isolation(binary,folder,run_paths):
    jail=folder/'probe'
    jail.mkdir()
    outside=folder/'future.csv'
    outside.write_bytes(b'synthetic target placeholder')
    readonly(jail/'anchors.txt',np.ones((3,*SHAPE),dtype='<f8').tobytes())
    (jail/'escape').symlink_to(outside)
    jail.chmod(0o555)
    log=worker(binary,jail,outside,*run_paths).decode().splitlines()
    need(len(log)==12,'OS rejection probes incomplete')
    before=worker(binary,jail)
    outside.write_bytes(b'poison synthetic target')
    after=worker(binary,jail)
    need(before==after,'Poison reached predictions')
    return dict(kernel_probes=log,synthetic_poison_output_sha256=digest(after),
                synthetic_poison_invariant=True,real_label_in_worker=False)


def seal(data):
    # Linux UAPI values from <linux/memfd.h> and <linux/fcntl.h>.
    libc=ctypes.CDLL(None,use_errno=True)
    libc.memfd_create.argtypes=(ctypes.c_char_p,ctypes.c_uint)
    libc.memfd_create.restype=ctypes.c_int
    fd=libc.memfd_create(b'v59-prediction',0x0001|0x0002)
    if fd<0:
        errno=ctypes.get_errno()
        raise OSError(errno,os.strerror(errno))
    with os.fdopen(os.dup(fd),'wb') as stream:
        stream.write(data)
    flags=0x0008|0x0004|0x0002|0x0001
    fcntl.fcntl(fd,1033,flags)  # F_ADD_SEALS
    need(fcntl.fcntl(fd,1034)==flags,'Missing Linux file seals')  # F_GET_SEALS
    try:
        os.pwrite(fd,b'\x00',0)
    except PermissionError:
        pass
    else:
        raise ValueError('Evaluation-side system seal failed')
    return fd


def statistics(y,p,weight,target,valid):
    coverage=float(np.count_nonzero(valid)/max(1,np.count_nonzero(target)))
    yy,pp,w=y[valid],p[valid],weight[valid]
    if not yy.size:
        return dict(n=0,target_n=int(target.sum()),coverage=coverage,mae=None,rmse=None,bias=None,
            relative_rmse=None,log_rmse=None,max_abs=None,p95_abs=None)
    err=pp-yy
    absolute=np.abs(err)
    order=np.argsort(absolute,kind='stable')
    mass=np.cumsum(w[order])
    p95=absolute[order[np.searchsorted(mass,.95*mass[-1])]]
    avg=lambda a:float(np.dot(w,a)/w.sum())
    return dict(n=len(yy),target_n=int(target.sum()),coverage=coverage,mae=avg(absolute),
        rmse=np.sqrt(avg(err**2)),bias=avg(err),relative_rmse=np.sqrt(avg((err/yy)**2)),
        log_rmse=np.sqrt(avg((np.log(pp)-np.log(yy))**2)),max_abs=float(absolute.max()),p95_abs=float(p95))


def metrics(samples,labels,predictions,coords):
    lat=coords['lat']
    y=np.stack(labels)
    p=np.stack(predictions)
    weight=np.broadcast_to(np.cos(np.deg2rad(lat))[None,None,:,None],y.shape)
    target=np.isfinite(y)&(y>0)
    good=np.isfinite(p)&(p>0)
    common=target&good.all(axis=1)
    result=[]
    for year in ('ALL','2021','2022'):
        for lead in LEADS:
            select=np.array([(year=='ALL' or r['date'].startswith(year)) and int(r['horizon'])==lead for r in samples])
            for region,zone in [('ALL',np.ones(len(lat),bool)),('low',abs(lat)<30),
                                ('mid',(abs(lat)>=30)&(abs(lat)<60)),('polar',abs(lat)>=60)]:
                for layer in (['ALL',*range(SHAPE[0])] if region=='ALL' else ['ALL']):
                    idx=np.arange(SHAPE[0]) if layer=='ALL' else [layer]
                    ix=np.ix_(np.flatnonzero(select),idx,np.flatnonzero(zone),np.arange(SHAPE[2]))
                    for k,method in enumerate(METHODS):
                        for mask in ('own','common'):
                            vv=(target&good[:,k] if mask=='own' else common)[ix]
                            pp=p[:,k][ix]
                            yy=y[ix]
                            nonpositive=np.isfinite(pp)&(pp<=0)
                            result.append(dict(year=year,horizon=lead,region=region,ilev_index=layer,
                                ilev_value='' if layer=='ALL' else coords['ilev'][layer],method=method,mask=mask,
                                nonpositive=int(np.count_nonzero(nonpositive&target[ix])),
                                invalid=int(np.count_nonzero(target[ix]&~good[:,k][ix])),
                                **statistics(yy,pp,weight[ix],target[ix],vv)))
    return result


def main():
    started=time.monotonic()
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    need(OUT.resolve()==OUT and not LOCAL.exists(),'Existing artifact directory; one-shot run')
    samples,sources,schedule,grouped,hist,labels,pin_sha=inputs()
    LOCAL.mkdir(mode=0o700)
    prediction_root=LOCAL/'predictions'
    prediction_root.mkdir(mode=0o700)
    evaluation_root=LOCAL/'targets'
    evaluation_root.mkdir(mode=0o700)
    save('authorization.json',dict(V58_head=BASE,V58_manifest_sha256=pin_sha,
        user_scope='V59 once, frozen autumn native DEN records only',run_ids=RUNS,history_records=len(hist),
        target_records=len(labels),Swarm_fields_authorized=False,independent_science_test=False,
        authorized_fields=['DEN','time','ilev','lat','lon','metadata-only ZG']))
    binary=LOCAL/'worker'
    subprocess.run(['/usr/bin/gcc','-static','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror',
         str(ROOT/'scripts/native_density_worker_v59.c'),'-lm','-o',str(binary)],
         env={'PATH':'/usr/bin:/bin','TMPDIR':str(LOCAL)},check=True)
    isolation_receipt=isolation(binary,LOCAL,[ROOT/r/'secondary_015.nc' for r in sources])
    schedule_ledger=[]
    coordinates={}
    forecasts={}
    records=[]
    handles=[]
    for (run,c),rows in sorted(grouped.items()):
        when=[iso(utc(c)-j*HOUR) for j in (3,2,1)]
        series=[frame((run,t),schedule,hist,'historical_only',schedule_ledger,coordinates) for t in when]
        jail=LOCAL/('jail_'+c.replace(':',''))
        jail.mkdir()
        input_sha=readonly(jail/'anchors.txt',np.stack(series).astype('<f8').tobytes())
        jail.chmod(0o555)
        raw=worker(binary,jail)
        need(len(raw)==9*np.prod(SHAPE)*8,'Worker result length')
        shaped=np.frombuffer(raw,dtype='<f8').reshape(3,3,*SHAPE)
        for row in rows:
            i=LEADS.index(int(row['horizon']))
            sid=row['sample_id']
            data=shaped[i].tobytes()
            handle=seal(data)
            handles.append(handle)
            file=prediction_root/(sid+'.bin')
            forecast_sha=readonly(file,data)
            forecasts[sid]=(handle,file,forecast_sha)
            records.append(dict(**row,native_run_id=sources[run]['native_run_id'],
              input_UTC=';'.join(when),input_SHA256=input_sha,prediction_SHA256=forecast_sha,
              **{m+'_SHA256':digest(shaped[i,k].tobytes()) for k,m in enumerate(METHODS)}))
    need(len(forecasts)==24 and not any(evaluation_root.iterdir()),'Target phase started early')
    table('sample_manifest.csv',records)
    (OUT/'sample_manifest.csv').chmod(0o444)
    save('prediction_lock.json',dict(locked_predictions=len(forecasts),sample_manifest_sha256=sha(OUT/'sample_manifest.csv'),
        worker_SHA256=sha(binary),kernel_memfd_write_rejections=len(handles),target_reads_at_lock=0,**isolation_receipt))
    predicted,true=[],[]
    for r in samples:
        key=(r['source_run_id'],r['prediction_target_UTC'])
        y=frame(key,schedule,labels,'trusted_evaluation_after_prediction_lock',schedule_ledger,coordinates)
        readonly(evaluation_root/(r['sample_id']+'.bin'),y.tobytes())
        handle,file,checksum=forecasts[r['sample_id']]
        data=os.pread(handle,3*y.nbytes,0)
        need(digest(data)==checksum==sha(file),'Locked prediction changed')
        predicted.append(np.frombuffer(data,dtype='<f8').reshape(3,*SHAPE))
        true.append(y)
        os.close(handle)
    need(all(sha(p)==d for _,p,d in forecasts.values()),'Post-evaluation hash mismatch')
    table('den_read_ledger.csv',schedule_ledger)
    save('native_grid.json',{k:v.tolist() for k,v in coordinates.items()})
    table('metrics.csv',metrics(samples,true,predicted,coordinates))
    profiles=[]
    for j in range(SHAPE[0]):
        for year in ('2021','2022'):
            group=np.stack([y[j] for r,y in zip(samples,true) if r['date'].startswith(year)])
            value=group[np.isfinite(group)]
            profiles.append(dict(year=year,ilev_index=j,ilev=float(coordinates['ilev'][j]),valid=len(value),
                min_kg_m3=float(value.min()) if value.size else '',max_kg_m3=float(value.max()) if value.size else '',
                median_kg_m3=float(np.median(value)) if value.size else ''))
    table('target_profiles.csv',profiles)
    save('handoff.json',handoff())
    save('execution.json',dict(elapsed_seconds=time.monotonic()-started,peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
         CPU_affinity=len(os.sched_getaffinity(0)),target_reads=len(labels),history_reads=len(hist),Swarm_density_reads=0,
         AI_training=0,GPU=0,new_TIEGCM_runs=0))


if __name__=='__main__':
    main()
