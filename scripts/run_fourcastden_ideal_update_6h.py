"""48-forward ideal-state-update experiment; open-loop arrays stay read-only."""
from pathlib import Path
from datetime import datetime,timedelta
import argparse,csv,gc,hashlib,json,os,resource,shutil,signal,subprocess,sys,time,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'third_party/FourCastDEN_linux')]
from fourcastden.logden import decode_physical,load_overlay,MetricTrace
from fourcastden.autoregression import check_autoregression
from fourcastden.profiling import DatasetTimer,MetricTimer
from fourcastden.ideal_update import update_indices,layer_rmse
from fourcastden.validation import NAMES,LENGTHS,SI_FACTORS
TAG='fourcastden_ideal_update_6h_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG;D=ROOT/'data/processed'/TAG
DATES=('2023-01-04','2023-03-24');MODELS=('Direct','Flow','LogDEN','History')
CHECKPOINTS=dict(Direct='Direct_ckpt.tar',Flow='Flow_ckpt.tar',LogDEN='Baseline_log_DEN_ckpt.tar',History='Baseline_1h_history_ckpt.tar')


def inside(p):p=Path(p);p.resolve().relative_to(ROOT);return p
def sha(p):
    h=hashlib.sha256()
    with inside(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
    return h.hexdigest()
def dump(p,x):
    with inside(p).open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')
def csvout(p,rows):
    with inside(p).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def oldpaths(day):
    tag='fourcastden_twelve_hour_jan4_v1' if day==DATES[0] else 'fourcastden_twelve_hour_mar24_v1'
    return ROOT/'experiments'/tag,ROOT/'data/processed'/tag,tag
def reference(day,hour,full=False):
    folder,_,_=oldpaths(day)
    with np.load(folder/'data_view'/f'{day.replace("-","_")}_{hour:02d}0000.npz',allow_pickle=False) as n:
        fields=np.concatenate([n[k] for k in NAMES]+([n[k] for k in ('TLBC','ULBC','VLBC')] if full else []))
        height=n['ZG'].astype(float)*.01;tlbc=n['TLBC'].astype(float)
    if not np.isfinite(fields).all() or (abs(fields)>1e30).any():raise ValueError('Invalid reference')
    return fields,height,tlbc
def load_old(day,model,keys=None):
    _,p,_=oldpaths(day)
    with np.load(p/f'{day}_{model}.npz',allow_pickle=False) as n:
        return {k:n[k].copy() for k in (keys or ('pred','means','stds','full_data','full_sw','inputs','scalars','raw_network','climatology'))}


def baseline():
    from ruamel.yaml import YAML
    started=time.perf_counter()
    for p in (F,O,D):inside(p);p.mkdir(exist_ok=False)
    view=F/'data_view';view.mkdir();protected={};baserows=[];checks=[];historical=[]
    lat=np.load(ROOT/'data/processed/static/lat.npy')
    for day in DATES:
        exp,data,tag=oldpaths(day);pre=json.loads((exp/'preflight.json').read_text())
        for entry in pre['data']:
            p=(ROOT/entry['source']).resolve();assert sha(p)==entry['sha256'];protected[str(p.relative_to(ROOT))]=entry['sha256']
            target=view/p.name
            if not target.exists():target.symlink_to(p)
        with (ROOT/f'results/metrics/{tag}_summary.csv').open() as f:oldsummary=list(csv.DictReader(f))
        with (ROOT/f'results/metrics/{tag}_windows.csv').open() as f:oldwindows=list(csv.DictReader(f))
        truth=np.stack([reference(day,h)[0].astype(float) for h in range(1,14)])
        for model in MODELS:
            p=data/f'{day}_{model}.npz';runtime=json.loads((exp/f'{day}_{model}_runtime.json').read_text());assert sha(p)==runtime['result_sha256'];protected[str(p.relative_to(ROOT))]=sha(p)
            cp=ROOT/'models/checkpoints/author'/CHECKPOINTS[model];assert sha(cp)==runtime['checkpoint_sha256'];protected[str(cp.relative_to(ROOT))]=sha(cp)
            old=load_old(day,model);assert old['pred'].shape==(1,13,171,36,72)
            assert np.isfinite(old['means']).all() and np.isfinite(old['stds']).all() and (old['stds']>0).all()
            hist=int(model=='History')
            for j,h in enumerate(range(0 if hist else 1,14)):
                r=reference(day,h,full=True)[0]
                if model=='LogDEN':r[142:171]=np.log10(r[142:171])
                np.testing.assert_array_equal(old['full_data'][j,:174],((r-old['means'])/old['stds']).astype(np.float32))
            np.testing.assert_array_equal(old['pred'][0,0],old['full_data'][hist,:171])
            check_autoregression([(old['inputs'][i:i+1],old['scalars'][i:i+1]) for i in range(12)],
                [old['pred'][0,i+1:i+2] for i in range(12)],old['full_data'],old['full_sw'],hist,
                [old['raw_network'][i:i+1] for i in range(12)],model=='Flow')
            physical=decode_physical(old['pred'][0],old['means'][:171],old['stds'][:171],model=='LogDEN')
            assert (physical[:,:28]>0).all()
            for lead in range(1,13):
                rms=layer_rmse(physical[lead],truth[lead],lat);offset=0
                for name,n,factor in zip(NAMES,LENGTHS,SI_FACTORS):
                    value=float(rms[offset:offset+n].mean()*factor)
                    prior=next(x for x in oldsummary if x['date']==day and x['model']==model and int(x['hour'])==lead and x['variable']==name)
                    np.testing.assert_allclose(value,float(prior['mean_layer_RMSE_SI']),rtol=2e-10,atol=1e-25 if name=='DEN' else 1e-8)
                    baserows.append(dict(date=day,model=model,lead=lead,target_UTC=f'{day}T{lead+1:02d}:00:00Z',variable=name,
                        mean_layer_RMSE_SI=value,historical=float(prior['mean_layer_RMSE_SI']),absolute_reproduction_difference=abs(value-float(prior['mean_layer_RMSE_SI']))))
                    offset+=n
                height=reference(day,lead+1)[1];med=np.median(height,axis=(1,2))/1000;near=np.flatnonzero((med>=400)&(med<=500))
                w=np.cos(np.deg2rad(lat))[:,None];w=np.broadcast_to(w,(36,72));w=w/w.mean()
                rel=physical[lead,142:]/truth[lead,142:]-1
                layerrel=np.sqrt(np.sum(w[None]*rel**2,axis=(1,2))/(36*72))
                previous=next(x for x in oldwindows if x['date']==day and x['model']==model and int(x['hour'])==lead)
                values=dict(mean_DEN_layer_RMSE_kg_m3=float(rms[142:].mean()*1000),near400_500_mean_relative_RMS=float(layerrel[near].mean()),
                    upper20_28_mean_relative_RMS=float(layerrel[20:29].mean()),top_relative_RMS=float(layerrel[-1]),
                    all_point_relative_P95=float(np.percentile(abs(rel),95)))
                for key,val in values.items():np.testing.assert_allclose(val,float(previous[key]),rtol=2e-10,atol=1e-25 if 'kg_m3' in key else 1e-15)
                checks.append(dict(date=day,model=model,lead=lead,**values,passed=True))
            historical.append(dict(date=day,model=model,load_s=runtime['model_load_s'],GPU_forward_total_ms=sum(runtime['GPU_forward_ms']),
                GPU_peak_allocated_bytes=runtime['peak_allocated_bytes'],RSS_KiB=runtime['RSS_KiB'],bytes=runtime['result_bytes']))
            del old,physical;gc.collect()
    for folder in ('static','static_log'):
        for p in (ROOT/'data/processed'/folder).iterdir():
            if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
    for p in [ROOT/'experiments/fourcastden_logden_multidate_v1/inference_overlay.py',ROOT/'third_party/FourCastDEN_linux/inference/inference.py',ROOT/'third_party/FourCastDEN_linux/models/afnonet.py',ROOT/'third_party/FourCastDEN_linux/dataset/dataset_tiegcm.py',ROOT/'src/atmosphere/fourcastden_density.py']:
        protected[str(p.relative_to(ROOT))]=sha(p)
    yaml=YAML()
    for model in MODELS:
        a=oldpaths(DATES[0])[0]/f'{model}.yaml';cfg=yaml.load(a.read_text())
        cfg['afno_inference'].update(n_prediction=6,test_data_path=str(view),pre_resultname=TAG+'_'+model,date_time='2023-01-04 07:00:00')
        with (F/f'{model}.yaml').open('x') as f:yaml.dump(cfg,f)
        protected[str((F/f'{model}.yaml').relative_to(ROOT))]=sha(F/f'{model}.yaml')
    gpu=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.total,memory.free','--format=csv,noheader'],text=True).strip()
    apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader'],text=True).strip()
    mem={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemTotal:','MemAvailable:'))}
    if apps or shutil.disk_usage(ROOT).free<20*2**30 or mem['MemAvailable']<4*2**30:raise RuntimeError('Resource preflight blocked')
    csvout(O/'baseline_frozen_variables.csv',baserows);csvout(O/'baseline_frozen_density.csv',checks)
    dump(F/'protected.json',protected)
    protocol=dict(tag=TAG,labels=['OFFLINE_IDEAL_TIEGCM_FULL_STATE_UPDATE','HINDCAST','TIEGCM_REFERENCE_ONLY','NO_TRAINING'],
        dates=list(DATES),models=list(MODELS),original_start_hour=1,reset_hour=7,targets=list(range(8,14)),
        history_real_initial_hours=[6,7],other_real_initial_hours=[7],future_physical_targets_feedback=False,
        extra_forward_budget=48,sequences=8,forwards_each=6,GPU_precheck_forwards=0,open_loop_reruns=0,
        metric_regions={'global':'all centres','south':'lat<=-60','north':'lat>=60','midlow':'abs(lat)<60'},
        DEN_groups={'all':'0:29','near400_500':'per-target reference ZG global median in [400,500] km','upper20_28':'20:29','top':'28'},
        density_denominator='strict positive reference; no numerical floor',weights='cos(latitude)',
        primary_relative_statistic='mean per-layer weighted relative RMS, matching existing windows CSV',
        baseline_tolerance=dict(rtol=2e-10,relative_atol=1e-15,DEN_absolute_atol_SI=1e-25,other_absolute_atol_SI=1e-8),
        scientific_training_READY=False,limits=dict(GPU_wall_s=600,RSS_bytes=4*2**30,GPU_allocated_bytes=4*2**30,new_bytes=800*2**20,free_disk_bytes=20*2**30),
        estimate=dict(conservative_wall_s=120,new_bytes=500*2**20,peak_RSS_bytes=2*2**30),gpu=gpu,other_GPU_apps=apps,CPU_memory=mem,
        free_disk_bytes=shutil.disk_usage(ROOT).free,historical_performance=historical,
        baseline_reproduction='PASS',baseline_rows=len(baserows),baseline_density_rows=len(checks),baseline_wall_s=time.perf_counter()-started,
        config_SHA={m:sha(F/f'{m}.yaml') for m in MODELS},no_retry=True)
    dump(F/'protocol.json',protocol);print(json.dumps({k:protocol[k] for k in ('baseline_reproduction','baseline_rows','baseline_density_rows','baseline_wall_s','gpu','estimate')},indent=2))


def verify():
    p=json.loads((F/'protocol.json').read_text());assert p['baseline_reproduction']=='PASS'
    for path,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/path)==h,path
    for path,h in json.loads((F/'code_frozen.json').read_text()).items():assert sha(ROOT/path)==h,path
    return p


def worker():
    os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
    import torch
    from utils.YParams import YParams
    import inference.inference as ordinary
    from unittest.mock import patch
    verify();dump(F/'worker_once.json',dict(max_forwards=48,no_retry=True));tick=time.perf_counter();records=[];attempted=0;completed=0
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
    def no_training(*args,**kwargs):raise AssertionError('Training/backward forbidden')
    try:
        with patch('torch.Tensor.backward',no_training),patch('torch.autograd.backward',no_training),torch.inference_mode():
            for model in MODELS:
                module=load_overlay(ROOT/'experiments/fourcastden_logden_multidate_v1/inference_overlay.py') if model=='LogDEN' else ordinary
                params=YParams(str(F/f'{model}.yaml'),'afno_inference');params['experiment_dir']=str(F)
                hist=int(model=='History');assert (params.n_in_channels,params.n_out_channels,params.n_history,params.n_prediction,params.n_in_indices)==(177,171,hist,6,4)
                torch.cuda.reset_peak_memory_stats();t=time.perf_counter();forecast=module.TGCMForecast(params);torch.cuda.synchronize();load_s=time.perf_counter()-t
                expected=[datetime.fromisoformat(day)+timedelta(hours=h) for day in DATES for h in range(14)]
                assert forecast.dataset.epochs==expected
                for di,day in enumerate(DATES):
                    indices=update_indices(di*14,hist);assert forecast.dataset.epochs[indices[hist]]==datetime.fromisoformat(day)+timedelta(hours=7)
                    t=time.perf_counter()
                    with DatasetTimer(forecast.dataset) as io:real,sw,_,std,mean=forecast.dataset.get_data(indices,inference=True)
                    preprocess=time.perf_counter()-t
                    old=load_old(day,model,('means','stds','full_data','full_sw','pred'))
                    np.testing.assert_array_equal(mean,old['means']);np.testing.assert_array_equal(std,old['stds'])
                    np.testing.assert_array_equal(real.numpy(),old['full_data'][6:])
                    np.testing.assert_array_equal(sw.numpy(),old['full_sw'][6:])
                    del old;gc.collect()
                    inputs=[];raws=[];events=[];timings=[];physics=[]
                    def prehook(net,args):
                        nonlocal attempted
                        if attempted>=48:raise RuntimeError('Forward budget exhausted')
                        attempted+=1;inputs.append(tuple(x.detach().cpu().numpy().copy() for x in args))
                        a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True);events.append((a,b));a.record()
                    def posthook(net,args,result):
                        nonlocal completed
                        a,b=events[-1];b.record();b.synchronize();timings.append(a.elapsed_time(b));out=result.detach().cpu().numpy().copy();raws.append(out);completed+=1
                        state=out+inputs[-1][0][:,:171] if model=='Flow' else out
                        ph=decode_physical(state,mean[:171],std[:171],model=='LogDEN')
                        if not (ph[:,:28]>0).all():raise ValueError('Nonpositive TN')
                        physics.append(dict(target_hour=7+len(raws),TN_min_K=float(ph[:,:28].min()),DEN_min_kg_m3=float(ph[:,142:].min()*1000),nonfinite=int((~np.isfinite(ph)).sum())))
                        (F/'forward_progress.json').write_text(json.dumps(dict(attempted=attempted,completed=completed,date=day,model=model)))
                        if torch.cuda.max_memory_allocated()>4*2**30:raise RuntimeError('GPU memory budget')
                    dump(F/f'{day}_{model}_launch.json',dict(initial_hours=[6,7] if hist else [7],target_hours=list(range(8,14)),forwards=6,no_retry=True))
                    h1=forecast.model.register_forward_pre_hook(prehook);h2=forecast.model.register_forward_hook(posthook)
                    torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
                    try:
                        with DatasetTimer(forecast.dataset) as loopio,MetricTimer(module) as mt,MetricTrace(module) as trace:
                            returned,pred,rmse,acc,accu,last,_,_=forecast.inference(indices[0])
                    except Exception:
                        np.savez_compressed(D/f'{day}_{model}_failed_prefix.npz',**{f'raw_{i}':v for i,v in enumerate(raws)},**{f'input_{i}':v[0] for i,v in enumerate(inputs)})
                        raise
                    finally:h1.remove();h2.remove()
                    torch.cuda.synchronize();loop_s=time.perf_counter()-start;assert len(raws)==6
                    check=check_autoregression(inputs,[pred[0,i+1:i+2] for i in range(6)],real.numpy(),sw.numpy(),hist,raws,model=='Flow')
                    poison=real.numpy().copy();poison[hist+1:,:171]=987654
                    check_autoregression(inputs,[pred[0,i+1:i+2] for i in range(6)],poison,sw.numpy(),hist,raws,model=='Flow')
                    np.testing.assert_array_equal(pred[0,0],real[hist,:171].numpy())
                    path=D/f'{day}_{model}.npz';t=time.perf_counter()
                    np.savez_compressed(path,pred=pred,means=mean,stds=std,inputs=np.concatenate([x[0] for x in inputs]),scalars=np.concatenate([x[1] for x in inputs]),raw_network=np.concatenate(raws),full_data=real.numpy(),full_sw=sw.numpy(),author_rmse=rmse,author_acc=acc)
                    save_s=time.perf_counter()-t
                    row=dict(date=day,model=model,model_load_s=load_s if di==0 else 0.,model_reused=bool(di),
                        read_preprocess_s=preprocess,read_decode_s=io.read_decode_s,normalization_s=io.normalization_s,
                        reset_state_extraction_s=preprocess,reset_cost_note='overlaps preprocessing; not additive; external reference acquisition excluded',
                        loop_read_decode_s=loopio.read_decode_s,loop_normalization_s=loopio.normalization_s,
                        six_step_loop_s=loop_s,forward_GPU_ms=timings,network_GPU_total_ms=sum(timings),native_metric_GPU_ms=sum(x['GPU_ms'] for x in mt.records),
                        save_s=save_s,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),
                        process_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        input_shape=list(inputs[0][0].shape),output_shape=list(raws[0].shape),feedback=check,future_truth_poison_PASS=True,
                        state_hours_UTC=list(range(7,14)),initial_history_hours=[6,7] if hist else [7],physics=physics,
                        checkpoint_SHA=sha(ROOT/'models/checkpoints/author'/CHECKPOINTS[model]),result_SHA=sha(path),bytes=path.stat().st_size)
                    dump(F/f'{day}_{model}_runtime.json',row);records.append(row);print(json.dumps(dict(date=day,model=model,forwards=6,network_ms=sum(timings))),flush=True)
                    del real,sw,returned,pred,inputs,raws,trace;gc.collect()
                del forecast;gc.collect();torch.cuda.empty_cache()
        assert attempted==completed==48
        dump(F/'runtime.json',dict(status='PASS',attempted_forwards=attempted,effective_forwards=completed,extra_precheck_forwards=0,
            GPU_phase_wall_s=time.perf_counter()-tick,records=records,torch=torch.__version__,cuda=torch.version.cuda,device=torch.cuda.get_device_name(),FP32=True,TF32=False))
    except Exception:
        dump(F/'worker_failure.json',dict(attempted=attempted,completed=completed,traceback=traceback.format_exc(),completed_sequences=len(records),no_retry=True));raise


def supervise():
    from supervise_fourcastden_multidate import rss_tree
    protocol=verify();apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader'],text=True).strip()
    if apps:raise RuntimeError('GPU newly occupied; stop before launch')
    dump(F/'supervisor_once.json',protocol['limits']);start=time.monotonic();peak=0;reason=None
    env=dict(os.environ,CUBLAS_WORKSPACE_CONFIG=':4096:8')
    with (ROOT/'logs'/f'{TAG}_GPU.log').open('x') as log:
        proc=subprocess.Popen([sys.executable,__file__,'worker'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        while proc.poll() is None:
            peak=max(peak,rss_tree(proc.pid));size=sum(p.stat().st_size for folder in (F,D,O) for p in folder.rglob('*') if p.is_file() and not p.is_symlink())
            if time.monotonic()-start>600:reason='GPU phase wall limit'
            elif peak>4*2**30:reason='CPU RSS limit'
            elif size>800*2**20:reason='New files limit'
            elif shutil.disk_usage(ROOT).free<20*2**30:reason='Disk floor'
            if reason:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                break
            time.sleep(.25)
    result=dict(status='PASS' if proc.returncode==0 and reason is None else 'FAIL',returncode=proc.returncode,wall_s=time.monotonic()-start,peak_tree_RSS_bytes=peak,stop_reason=reason,no_retry=True)
    dump(F/'supervision.json',result);print(json.dumps(result,indent=2))
    if result['status']!='PASS':raise RuntimeError('GPU worker failed; do not retry')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['baseline','worker','supervise']);a=p.parse_args()
    try:globals()[a.phase]()
    except Exception:
        if F.exists():dump(F/f'{a.phase}_failure_{time.time_ns()}.json',dict(traceback=traceback.format_exc(),no_retry=True))
        raise
