"""Independent values, UTC/feedback, reset cost, and immutable-asset audit."""
from pathlib import Path
import csv,gzip,json,sys,time,resource,shutil,lzma
from datetime import datetime,timedelta
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src'),str(ROOT/'third_party/FourCastDEN_linux')]
import run_fourcastden_ideal_update_6h as run
from fourcastden.autoregression import check_autoregression
F,O,D=run.F,run.O,run.D


def main():
    start=time.perf_counter();protocol=run.verify();runtime=json.loads((F/'runtime.json').read_text());assert runtime['effective_forwards']==48
    with (O/'metrics.csv').open() as f:rows=list(csv.DictReader(f))
    index={(x['date'],x['model'],x['scheme'],int(x['target_hour_UTC']),x['region'],x['group']):x for x in rows if x['variable']=='DEN' and x['domain']=='pressure_valid'}
    lat=np.load(ROOT/'data/processed/static/lat.npy');w=np.broadcast_to(np.cos(np.deg2rad(lat))[:,None],(36,72))
    regions={'global':np.ones((36,72),bool),'south':np.broadcast_to((lat<=-60)[:,None],(36,72)),
             'north':np.broadcast_to((lat>=60)[:,None],(36,72)),'midlow':np.broadcast_to((abs(lat)<60)[:,None],(36,72))}
    timeline=[];verification=[]
    for day in run.DATES:
        for model in run.MODELS:
            old=run.load_old(day,model);hist=int(model=='History');p=D/f'{day}_{model}.npz'
            meta=json.loads((F/f'{day}_{model}_runtime.json').read_text());assert run.sha(p)==meta['result_SHA']
            with np.load(p) as z:new={k:z[k].copy() for k in ('pred','means','stds','inputs','scalars','raw_network','full_data','full_sw')}
            np.testing.assert_array_equal(new['full_data'],old['full_data'][6:]);np.testing.assert_array_equal(new['full_sw'],old['full_sw'][6:])
            np.testing.assert_array_equal(new['scalars'],old['scalars'][6:])
            np.testing.assert_array_equal(new['inputs'].reshape(6,hist+1,177,36,72)[:,:,171:],old['inputs'][6:].reshape(6,hist+1,177,36,72)[:,:,171:])
            check_autoregression([(new['inputs'][i:i+1],new['scalars'][i:i+1]) for i in range(6)],
                [new['pred'][0,i+1:i+2] for i in range(6)],new['full_data'],new['full_sw'],hist,[new['raw_network'][i:i+1] for i in range(6)],model=='Flow')
            # Independent affine and base-10 physical decode, without decode_physical.
            predicted={}
            for label,data in [('Open',old),('Updated',new)]:
                q=np.asarray(data['pred'][0],np.float64)*np.asarray(data['stds'][:171],np.float64)+np.asarray(data['means'][:171],np.float64)
                if model=='LogDEN':q[:,142:171]=np.float_power(10.,q[:,142:171])
                predicted[label]=q
            for hour in range(1,14):
                role='reused_open' if hour<7 else 'ideal_reset_not_forecast' if hour==7 else 'new_forecast'
                timeline.append(dict(date=day,model=model,UTC=(datetime.fromisoformat(day)+timedelta(hours=hour)).isoformat()+'Z',
                    published_source='Open' if hour<7 else 'Updated',record=hour-1 if hour<7 else hour-7,role=role,forecast_comparison_included=hour>=8))
            timeline.append(dict(date=day,model=model,UTC=day+'T07:00:00Z',published_source='Open',record=6,role='left_limit_before_update',forecast_comparison_included=False))
            for hour in range(8,14):
                truth,zg,_=run.reference(day,hour);truth=truth[142:].astype(float)*1000
                med=np.median(zg,axis=(1,2))/1000;groups={'all':np.arange(29),'near400_500':np.flatnonzero((med>=400)&(med<=500)),'upper20_28':np.arange(20,29),'top':np.array([28])}
                for label in ('Open','Updated'):
                    ph=predicted[label][hour-1 if label=='Open' else hour-7,142:]*1000
                    assert np.isfinite(ph).all() and (ph>0).all()
                    for region,mask in regions.items():
                        ww=w[mask];den=ww.sum()
                        for group,inds in groups.items():
                            d=(ph-truth)[inds][:,mask];t=truth[inds][:,mask];relative=d/t
                            rms=np.sqrt(np.array([np.dot(ww,v*v)/den for v in d]));rr=np.sqrt(np.array([np.dot(ww,v*v)/den for v in relative]))
                            values=dict(RMSE=float(np.sqrt(np.mean(rms**2))),mean_layer_RMSE=float(rms.mean()),MAE=float(np.sum(abs(d)*ww)/(len(inds)*den)),
                                max_abs=float(abs(d).max()),relative_RMS=float(np.sqrt(np.mean(rr**2))),mean_layer_relative_RMS=float(rr.mean()),relative_P95=float(np.quantile(abs(relative),.95)))
                            row=index[day,model,label,hour,region,group]
                            for name,value in values.items():np.testing.assert_allclose(value,float(row[name]),rtol=2e-10,atol=1e-25 if name in ('RMSE','mean_layer_RMSE','MAE','max_abs') else 1e-14)
                            verification.append(dict(date=day,model=model,scheme=label,target_hour_UTC=hour,region=region,group=group,metrics_checked=len(values),PASS=True))
    run.csvout(O/'independent_DEN_metric_checks.csv',verification);run.csvout(F/'published_state_timeline.csv',timeline)
    # CPU-only local acquisition of only the reset frames. No network/model calls.
    import torch
    from unittest.mock import patch
    from utils.YParams import YParams
    from dataset.dataset_tiegcm import TGCMDataset
    from fourcastden.profiling import DatasetTimer
    resetcost=[]
    def forbid(*a,**k):raise AssertionError('Model execution forbidden in reset-cost audit')
    with patch('torch.nn.Module.__call__',forbid),patch('torch.Tensor.backward',forbid),torch.inference_mode():
        for model in run.MODELS:
            params=YParams(str(F/f'{model}.yaml'),'afno_inference');params['device']='cpu';dataset=TGCMDataset(params,str(F/'data_view'),train=False)
            for di,day in enumerate(run.DATES):
                hist=int(model=='History');indices=list(range(di*14+7-hist,di*14+8));tick=time.perf_counter()
                with DatasetTimer(dataset) as timer:data,sw,*_=dataset.get_data(indices,inference=True)
                processing=time.perf_counter()-tick;tick=time.perf_counter();copy=data[:,:171].clone();copy_s=time.perf_counter()-tick
                with np.load(D/f'{day}_{model}.npz') as n:np.testing.assert_array_equal(data.numpy(),n['full_data'][:hist+1])
                resetcost.append(dict(date=day,model=model,local_reset_frames=hist+1,UTC_hours='6;7' if hist else '7',
                    cached_local_read_preprocess_s=processing,read_decode_s=timer.read_decode_s,normalization_s=timer.normalization_s,
                    normalized_state_copy_s=copy_s,external_global_state_generation_or_observation_acquisition_s='NOT_MEASURED',
                    standalone_CPU_diagnostic_not_added_to_GPU_timing=True))
    run.csvout(O/'standalone_reset_processing_cost.csv',resetcost)
    # Full layer statistics remain local; publish a byte-identical compressed copy.
    raw=O/'layer_metrics.csv';packed=O/'layer_metrics.csv.gz'
    with raw.open('rb') as inp,packed.open('xb') as out:
        with gzip.GzipFile(filename='',mode='wb',fileobj=out,mtime=0,compresslevel=9) as compressed:shutil.copyfileobj(inp,compressed)
    import hashlib
    with gzip.open(packed,'rb') as stream:
        h=hashlib.sha256()
        for block in iter(lambda:stream.read(4*1024**2),b''):h.update(block)
    assert h.hexdigest()==run.sha(raw)
    finish()


def finish():
    """Finalize already-written, completed checks; never rerun inference or metrics."""
    started=time.perf_counter();run.verify()
    with (O/'independent_DEN_metric_checks.csv').open() as f:verification=list(csv.DictReader(f))
    assert len(verification)==1536 and all(x['PASS']=='True' for x in verification)
    with (O/'standalone_reset_processing_cost.csv').open() as f:costs=list(csv.DictReader(f))
    assert len(costs)==8
    raw=O/'layer_metrics.csv';packed=O/'layer_metrics.csv.gz';compressed=O/'layer_metrics.csv.xz'
    raw_sha=run.sha(raw)
    with gzip.open(packed,'rb') as stream:
        import hashlib
        checksum=hashlib.sha256()
        for block in iter(lambda:stream.read(4*1024**2),b''):checksum.update(block)
    assert checksum.hexdigest()==raw_sha
    with raw.open('rb') as inp,compressed.open('xb') as out:
        with lzma.LZMAFile(out,mode='wb',preset=6) as encoded:shutil.copyfileobj(inp,encoded)
    with lzma.open(compressed,'rb') as stream:
        checksum=hashlib.sha256()
        for block in iter(lambda:stream.read(4*1024**2),b''):checksum.update(block)
    assert checksum.hexdigest()==raw_sha
    oldprotected=json.loads((ROOT/'experiments/tiegcm_runtime_restart_audit_v1/protected_files.json').read_text())
    changed=[path for path,expected in oldprotected.items() if run.sha(ROOT/path)!=expected];assert not changed,changed
    for path,expected in json.loads((F/'protected.json').read_text()).items():assert run.sha(ROOT/path)==expected,path
    figures=list(O.glob('*.png'));assert len(figures)==16
    from PIL import Image
    for p in figures:
        with Image.open(p) as image:image.verify()
    run.dump(O/'delivery_audit.json',dict(historical_assets_SHA_verified=len(oldprotected),changed=changed,task_assets_SHA_verified=len(json.loads((F/'protected.json').read_text())),
        independent_metric_rows=len(verification),independent_scalar_metrics=len(verification)*7,forward_count=48,GPU_prechecks=0,
        open_loop_model_reruns=0,orbit_integrations=0,TIE_integrations=0,training_steps=0,
        compressed_layer_CSV_bytes=packed.stat().st_size,published_xz_bytes=compressed.stat().st_size,compressed_layer_CSV_restores_exact_SHA=checksum.hexdigest(),original_layer_CSV_SHA=raw_sha,
        PNGs_verified=len(figures),all_07_UTC_reset_scores_excluded=True,
        audit_finalization_wall_s=time.perf_counter()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        prior_serialization_incident='preserved in experiments/audit_serialization_incident.json; no scientific tolerances changed'))
    print('Independent evaluation and source integrity PASS:',len(verification)*7,'scalar metrics')


if __name__=='__main__':finish() if '--finish' in sys.argv else main()
