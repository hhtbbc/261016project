"""Freeze TRAIN-only sliding windows, extract DEN slices, and diagnose residuals."""
import hashlib
import os
import resource
import time
from datetime import timedelta

import numpy as np
from netCDF4 import Dataset, num2date

from run_training_events_v65 import EVENTS, OUT, PRIVATE, ROOT, V62, at, annual, load, require, sha, utc, write_once
from run_native_density_baselines_v59 import SHAPE, read_csv, table

LEADS=(1,3,6)
H=timedelta(hours=1)
METHODS=('Persistence','LogLinear','LocalTimePersistence')


def freeze():
    candidates={r['event_id']:r for r in read_csv(V62/'geomagnetic_event_candidates.csv')}
    roles=load(OUT/'event_role_registry.json')
    require({r['event'] for r in roles['TRAIN']}=={x[0] for x in EVENTS.values()},'TRAIN universe')
    samples,fields,raw_index,volumes=[],[],[],[]
    runs=set()
    counts={}
    for tag,(event,*_) in EVENTS.items():
        receipt=load(OUT/'run_receipts'/f'{tag}_run_receipt.json')
        plan=load(OUT/'prepared_configs'/tag/'preflight.json')['plan']
        require(receipt['engineering']=='PASS' and receipt['independent_science_status']=='TRAIN'
                and receipt['event_id']==event and receipt['run_id'] not in runs,'Run role or identity')
        runs.add(receipt['run_id'])
        run=PRIVATE/tag.lower()
        require(run.resolve()==run and str(run.relative_to(ROOT))==receipt['directory'],'Run path')
        c=candidates[event]
        start,stop=at(c['core_start']),at(c['core_end_exclusive'])
        allowed_start=max(start,at(plan['start'])+timedelta(days=14))
        authorized={at(r['UTC']):r for r in receipt['time_index']}
        require(len(authorized)==plan['hourly_DEN_frames'],'Time index count')
        volumes.extend(r | {'path':str((run/r['file']).relative_to(ROOT))} for r in receipt['files'])
        raw_index.extend(receipt['time_index'])
        begin=len(samples)
        used=set()
        for t in sorted(authorized):
            if t-3*H<allowed_start or t+6*H>=stop:
                continue
            hist=[t+k*H for k in (-3,-2,-1)]
            fut=[t+k*H for k in LEADS]
            require(all(t+k*H in authorized for k in range(-3,7)),'Unexpected core time gap')
            s={'event_id':event,'run_id':receipt['run_id'],'cutoff_UTC':utc(t),'role':'TRAIN',
               'fixed_06Z_18Z':utc(t) in plan['cutoffs']}
            for field,when in zip(('x_m3','x_m2','x_m1','y_p1','y_p3','y_p6'),hist+fut):
                s[field]=utc(when)
            s['sample_id']=hashlib.sha256(f"{receipt['run_id']}|{utc(t)}|V65".encode()).hexdigest()
            used.update(hist+fut)
            samples.append(s)
        selected=samples[begin:]
        require({s['cutoff_UTC'] for s in selected if s['fixed_06Z_18Z']}==set(plan['cutoffs']),
                'Fixed cutoff missing')
        counts[event]=len(selected)
        by_filename={r['file']:r for r in receipt['files']}
        for t in sorted(used):
            r=authorized[t]
            fields.append(r | dict(field_index=len(fields),volume_SHA256=by_filename[r['file']]['sha256'],
                          volume_path=str((run/r['file']).relative_to(ROOT))))
    require(len({s['sample_id'] for s in samples})==len(samples) and
            len({(f['run_id'],f['UTC']) for f in fields})==len(fields),'Canonical sample keys')
    table(OUT/'native_output_inventory.csv',volumes)
    table(OUT/'native_time_index.csv',raw_index)
    table(OUT/'train_cutoff_inventory.csv',[s for s in samples if s['fixed_06Z_18Z']])
    table(OUT/'hourly_training_sample_manifest.csv',samples)
    table(OUT/'training_field_manifest.csv',fields)
    manifest=['native_output_inventory.csv','native_time_index.csv','train_cutoff_inventory.csv',
              'hourly_training_sample_manifest.csv','training_field_manifest.csv']
    write_once(OUT/'training_scope_lock.json',dict(SHA256={n:sha(OUT/n) for n in manifest},
               TRAIN_only=True,scope='approved core, first history age >= 14 days'))
    return samples,fields,counts


def slice_fields(fields,directory):
    density=np.lib.format.open_memmap(directory/'density_kg_m3.npy',mode='w+',dtype='<f4',
                                      shape=(len(fields),*SHAPE))
    logs=np.lib.format.open_memmap(directory/'log_density.npy',mode='w+',dtype='<f4',shape=density.shape)
    decoded=np.empty(density.shape,dtype=np.float64)
    rows=[]
    coordinates={}
    volumes={}
    for r in fields:
        path=ROOT/r['volume_path']
        require(path.resolve()==path and path.stat().st_mode&0o777==0o400,'Custody')
        if path not in volumes:
            volumes[path]=sha(path)
        require(volumes[path]==r['volume_SHA256'],'Sealed volume mismatch')
        with Dataset(path) as n:
            x=n['DEN']
            i=r['record']
            require(x.shape[1:]==SHAPE and x.dimensions==('time','ilev','lat','lon') and
                    x.units=='g/cm3' and not {'scale_factor','add_offset'}&set(x.ncattrs()),'Density contract')
            t=n['time']
            require(num2date(t[i],t.units).isoformat()+'Z'==r['UTC'],'Record time identity')
            for axis in ('ilev','lat','lon'):
                v=np.asarray(n[axis][:],dtype=float)
                require(not coordinates or axis not in coordinates or np.array_equal(coordinates[axis],v),'Grid mismatch')
                coordinates[axis]=v
            x.set_auto_maskandscale(False)
            a=np.asarray(x[i,:,:,:])
            bad=~np.isfinite(a)|(a<=0)
            for attr in ('_FillValue','missing_value'):
                if attr in x.ncattrs():
                    bad |= np.isin(a,np.asarray(x.getncattr(attr),dtype=a.dtype))
        d=np.where(bad,np.nan,a.astype(np.float64)*1000)
        index=r['field_index']
        density[index]=d
        decoded[index]=d
        logs[index]=np.log(d)
        rec=dict(r,invalid=int(bad.sum()),finite_positive=int((~bad).sum()),
                 raw_slice_SHA256=hashlib.sha256(a.tobytes()).hexdigest(),
                 float32_SI_SHA256=hashlib.sha256(density[index].tobytes()).hexdigest(),
                 max_relative_float32_error=float(np.max(abs(density[index][~bad]/d[~bad]-1))) if not bad.all() else None)
        rows.append(rec)
    for a in (density,logs):
        a.flush()
    table(OUT/'training_field_receipt.csv',rows)
    require(not any(r['invalid'] for r in rows),'Invalid observed TRAIN records retained in field receipt')
    require(np.all(np.isfinite(density)&(density>0)) and np.isfinite(logs).all(),'Precision conversion coverage')
    require(np.array_equal(np.diff(np.r_[coordinates['lon'],coordinates['lon'][0]+360]),np.full(72,5)),
            'Cyclic longitude spacing')
    return decoded,coordinates,rows


def stats(res,w):
    """Float64, area-weighted moments; pooled empirical gridpoint quantiles."""
    weight=np.broadcast_to(w,res.shape)
    mean=np.average(res,weights=weight)
    rms=np.sqrt(np.average(res**2,weights=weight))
    by_q=np.quantile(res,(.01,.05,.50,.95,.99))
    return dict(n=res.size,weighted_sse=float(np.sum(weight*res**2)),
                rms=float(rms),mean=float(mean),std=float(np.sqrt(np.average((res-mean)**2,weights=weight))),
                **{f'p{p}':float(x) for p,x in zip((1,5,50,95,99),by_q)},
                positive=float(np.mean(res>0)),negative=float(np.mean(res<0)))


def metrics_and_arrays(d,samples,fields,coords,directory):
    ids={(r['run_id'],r['UTC']):r['field_index'] for r in fields}
    matrix=np.array([[ids[s['run_id'],s[k]] for k in ('x_m3','x_m2','x_m1','y_p1','y_p3','y_p6')] for s in samples])
    np.save(directory/'sample_field_indices.npy',matrix,allow_pickle=False)
    hist,future=matrix[:,:3],matrix[:,3:]
    h_id,y_id=np.unique(hist),np.unique(future)
    z=np.log(d)

    def norm(index):
        values=z[index].reshape(-1,*SHAPE)
        return dict(mean=values.mean(axis=(0,2,3)).tolist(),std=values.std(axis=(0,2,3)).tolist(),
                    frames=len(values))

    normal=norm(h_id)
    require(min(normal['std'])>0,'Degenerate layer scale')
    write_once(OUT/'train_normalization.json',dict(primary_unique_input_frames=normal,
               sensitivity_sliding_window_exposure=norm(hist.ravel()),roles=['TRAIN'],
               target_frames_used_to_fit=False,
               note='A frame that is also a training target enters only via its authorized history association.',
               low_density_p5_unique_train_inputs=np.quantile(d[h_id],.05,axis=(0,2,3)).tolist()))
    lat=coords['lat']
    w=np.cos(np.deg2rad(lat))[None,None,:,None]
    residual=np.lib.format.open_memmap(directory/'log_residuals.npy',mode='w+',dtype='<f4',
                                       shape=(2,len(samples),3,*SHAPE))
    zi=z[hist[:,2]]
    earlier=z[hist[:,1]]
    aggregate=[]
    strata=[]
    spatial=[]
    fields_stats=[]
    daily_structure=[]
    roles=[e[0] for e in EVENTS.values()]
    for e in roles:
        field_idx=[r['field_index'] for r in fields if r['event_id']==e]
        data=d[field_idx]
        times={at(fields[i]['UTC']): j for j,i in enumerate(field_idx)}
        pairs=[(j,times[t+24*H]) for t,j in times.items() if t+24*H in times]
        for l,ilev in enumerate(coords['ilev']):
            a=data[:,l]
            v=np.quantile(a,(.05,.5,.95))
            fields_stats.append(dict(event=e,level=l,ilev=ilev,min=float(a.min()),max=float(a.max()),
                   mean=float(a.mean()),p05=float(v[0]),p50=float(v[1]),p95=float(v[2]),
                   mean_spatial_std=float(np.std(a,axis=(1,2)).mean()),
                   temporal_log_difference_rms=float(np.sqrt(np.mean(np.diff(np.log(a),axis=0)**2)))))
            log_a=np.log(a)
            harmonics=2*np.fft.rfft(log_a,axis=-1)[...,1]/SHAPE[-1]
            # An eastward source shift of 3 cells per hour advances this Fourier phase.
            phase_step=np.angle(harmonics[1:]*harmonics[:-1].conj())
            daily_structure.append(dict(event=e,level=l,diurnal_zonal_harmonic_amplitude=float(abs(harmonics).mean()),
                rms_phase_change_error_radians=float(np.sqrt(np.mean(np.angle(
                    np.exp(1j*(phase_step-2*np.pi/24)))**2))),
                legal_24h_pairs=len(pairs),log_difference_rms_24h=float(np.sqrt(np.mean(
                    [(log_a[j]-log_a[i])**2 for i,j in pairs]))) if pairs else None))
    table(OUT/'event_layer_density_stats.csv',fields_stats)
    table(OUT/'diurnal_structure.csv',daily_structure)
    for j,h in enumerate(LEADS):
        truth=z[future[:,j]]
        ps,ls,lts=zi,zi+(h+1)*(zi-earlier),np.roll(zi,-3*(h+1),axis=-1)
        residual[0,:,j]=truth-ps
        residual[1,:,j]=truth-lts
        group=[(e,[i for i,s in enumerate(samples) if s['event_id']==e]) for e in roles]
        group += [('ALL',list(range(len(samples))))]
        group += [(cls,[i for i,s in enumerate(samples) if s['event_id'].startswith(cls)])
                  for cls in ('quiet','disturbed')]
        for e,idx in group:
            for name,back in zip(METHODS,(ps,ls,lts)):
                err=truth[idx]-back[idx]
                absolute=np.exp(back[idx])-np.exp(truth[idx])
                g=stats(err,w)
                aggregate.append(dict(event=e,horizon=h,method=name,role='TRAIN_DIAGNOSTIC',samples=len(idx),
                    absolute_rmse=float(np.sqrt(np.average(absolute**2,weights=np.broadcast_to(w,absolute.shape)))),
                    **g))
                if name=='LogLinear':
                    continue
                for region,sl in [('south_polar',lat<=-60),('north_polar',lat>=60)]:
                    strata.append(dict(event=e,horizon=h,method=name,domain=region,**stats(err[:,:,sl,:],w[:,:,sl,:])))
                for l in range(SHAPE[0]):
                    strata.append(dict(event=e,horizon=h,method=name,domain=f'ilev_{l:02}',
                                       **stats(err[:,l:l+1],w)))
                centered=err-err.mean(axis=-1,keepdims=True)
                denominator=np.sum(centered**2,axis=-1)
                numerator=np.sum(centered*np.roll(centered,1,axis=-1),axis=-1)
                valid=denominator>0
                spatial.append(dict(event=e,horizon=h,method=name,statistic='mean zonal lag-one correlation',
                                    value=float(np.mean(numerator[valid]/denominator[valid])) if valid.any() else None))
    residual.flush()
    table(OUT/'training_baseline_metrics.csv',aggregate)
    table(OUT/'residual_comparison.csv',strata)
    table(OUT/'residual_spatial_correlation.csv',spatial)
    comparisons=[]
    for e in (*roles,'ALL','quiet','disturbed'):
        for h in LEADS:
            p,lt=[next(r for r in aggregate if (r['event'],r['horizon'],r['method'])==(e,h,m))
                  for m in ('Persistence','LocalTimePersistence')]
            comparisons.append(dict(event=e,horizon=h,P_RMS=p['rms'],LT_RMS=lt['rms'],
                                    LT_reduction_pct=100*(1-lt['rms']/p['rms']),
                                    P_weighted_SSE=p['weighted_sse'],LT_weighted_SSE=lt['weighted_sse']))
    table(OUT/'residual_summary.csv',comparisons)
    for r in comparisons:
        if r['event']=='ALL':
            for method in ('P','LT'):
                k=method+'_weighted_SSE'
                require(np.isclose(r[k],sum(s[k] for s in comparisons if s['horizon']==r['horizon']
                                           and s['event'] in roles),rtol=1e-12),'Event SSE additivity')
    share=len(set(h_id)&set(y_id))
    write_once(OUT/'data_quality_report.json',dict(fixed_cutoffs=sum(r['fixed_06Z_18Z'] for r in samples),
        windows=len(samples),independent_events=4,targets=int(future.size),unique_frames=len(fields),
        unique_history=len(h_id),unique_targets=len(y_id),history_target_overlap=share,
        shared_fraction_of_history=share/len(h_id),shared_fraction_of_targets=share/len(y_id),
        history_links=int(hist.size),repeated_history_links=int(hist.size-len(h_id)),
        repeated_target_links=int(future.size-len(y_id)),repeated_all_links=int(matrix.size-len(fields)),
        coordinates={k:v.tolist() for k,v in coords.items()},min_kg_m3=float(d.min()),max_kg_m3=float(d.max()),
        invalid_cells=0,statistics_precision='float64',arrays_precision='float32',
        field_array_unit='kg/m3',only_core_values_used=True,convergence='NOT_ESTABLISHED'))
    return comparisons,matrix


def main():
    t=time.monotonic()
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    require(OUT.resolve()==OUT and PRIVATE.resolve()==PRIVATE,'Unsafe output')
    samples,fields,counts=freeze()
    directory=PRIVATE/'training_arrays'
    directory.mkdir(mode=0o700)
    d,coords,rows=slice_fields(fields,directory)
    comparisons,matrix=metrics_and_arrays(d,samples,fields,coords,directory)
    sse_share=[]
    for r in comparisons:
        if r['event'] in counts:
            total=next(s for s in comparisons if s['event']=='ALL' and s['horizon']==r['horizon'])
            sse_share.append(dict(event=r['event'],horizon=r['horizon'],
                    P_sse_share=r['P_weighted_SSE']/total['P_weighted_SSE'],
                    LT_sse_share=r['LT_weighted_SSE']/total['LT_weighted_SSE']))
    table(OUT/'event_residual_contribution.csv',sse_share)
    write_once(OUT/'event_sampling_plan.json',dict(
        preferred='uniform event then uniform window within event, deterministic shared sampler',
        comparison=['all windows equally weighted','all events equally weighted','quiet/disturbed classes equally weighted',
                    'uniform within each event; varying event weight separately'],
        event_windows=counts,window_weights={k:v/len(samples) for k,v in counts.items()},
        event_weights={k:.25 for k in counts},class_weights={'quiet':.5,'disturbed':.5},
        caution='Six neighboring short-storm windows describe one event; equal exposure increases reuse, not independence.'))
    write_once(OUT/'matched_model_preregistration.json',dict(
        model='V60 TinyDirectCNN 1027 parameters, same 3x3 3→8→8→3 kernels per ilev, ReLU, linear output',
        inputs='same t-3,t-2,t-1 logDEN, unique TRAIN history normalization, no future forcing',
        backgrounds=['Persistence','LocalTimePersistence'],loss='three-horizon mean of cosine-weighted log residual MAE',
        initial='same seeded initialization, zero output head; seed 42',
        optimizer='Adam',learning_rate=.001,updates_per_arm=200,
        historical_v60_80_updates_seconds=13.556757763028145,
        extrapolated_optimizer_seconds_per_arm=33.9,
        budget_note='Linear V60 update-time extrapolation at same native grid and four CPU threads. '
                    'Data reading, validation and setup excluded. No V65 training performed.',
        ceiling_s_per_arm_proposed=600,
        comparison_policy='same event/window order and updates; independent validation and fresh event test after lock'))
    write_once(OUT/'next_stage_authorization.json',dict(
        states=['TRAIN_DATA_READY_IF_INDEPENDENT_VERIFICATION_PASSES','V66_TRAINING_NEEDS_NEW_AUTHORIZATION',
                'VALIDATION_AND_TEST_NOT_PRODUCED_OR_OPENED'],
        validation=['quiet_20220301T21','disturbed_20211103T21'],
        locked_test=['quiet_20231009T21','disturbed_20231105T09'],
        limitation='Two events per role; strong disturbance outside moderate-only training set.'))
    lst=sorted(directory.glob('*.npy'))
    write_once(OUT/'training_arrays_SHA256.json',{p.name:{'SHA256':sha(p),'bytes':p.stat().st_size} for p in lst})
    write_once(OUT/'training_data_resources.json',dict(elapsed_s=time.monotonic()-t,
                  max_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  array_bytes=sum(p.stat().st_size for p in lst),CUDA=False,
                  max_relative_float32_error=max(r['max_relative_float32_error'] for r in rows)))
    print(f'Built {len(samples)} windows, {len(fields)} fields and {matrix[:,3:].size} targets',flush=True)


if __name__=='__main__':
    main()
