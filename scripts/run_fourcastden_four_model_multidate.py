"""Four frozen dates, four official models, common 01 UTC; January read-only."""
import sys,json,time,argparse,zipfile,zlib,gc,traceback,shutil,resource
from pathlib import Path
from datetime import datetime,timedelta
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'third_party/FourCastDEN_linux'))
from run_fourcastden_multistep import sha,dump
from run_fourcastden_history_comparison import CHECKPOINTS,verify as verify_january
from fourcastden.multidate import BoundedRemoteZip,validate_npz,DATES
from fourcastden.four_model_windows import MODELS,ALL_DATES,window_indices
from fourcastden.logden import decode_physical,load_overlay,MetricTrace
from fourcastden.history import history_feedback_check
from fourcastden.validation import feedback_check
F=ROOT/'experiments/fourcastden_four_model_multidate_v1';D=ROOT/'data/processed/fourcastden_four_model_multidate_v1';RAW=ROOT/'data/raw/fourcastden_four_model_multidate_v1'
JAN=ROOT/'experiments/fourcastden_history_comparison_v1';JAND=ROOT/'data/processed/fourcastden_history_comparison_v1'

def fetch():
 verify_january();F.mkdir(exist_ok=False);RAW.mkdir(exist_ok=False);dump(F/'fetch_once.json',dict(members=[d.replace('-','_')+'_030000.npz' for d in DATES],limit=20*2**20))
 protected=json.loads((JAN/'protected.json').read_text())
 for folder in [JAN,JAND,ROOT/'data/raw/fourcastden_history_comparison_v1']:
  for p in folder.rglob('*'):
   if p.is_file() and not p.is_symlink():protected[str(p.relative_to(ROOT))]=sha(p)
 for folder,pattern in [('results/metrics','fourcastden_history_v1*'),('results/figures','fourcastden_history_v1*'),('logs','fourcastden_history*'),('reports','FOURCASTDEN_HISTORY_VALIDATION.md'),('reports','FOURCASTDEN_FOUR_MODEL_COMPARISON.md')]:
  for p in (ROOT/folder).glob(pattern):
   if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 for name in ['src/fourcastden/history.py','src/fourcastden/logden.py','src/fourcastden/validation.py','src/fourcastden/multidate.py','scripts/run_fourcastden_history_comparison.py','scripts/analyze_fourcastden_history.py']:protected[name]=sha(ROOT/name)
 for p,h in protected.items():assert sha(ROOT/p)==h,p
 dump(F/'protected.json',protected)
 meta=json.loads((ROOT/'logs/zenodo_21859635_20261019.json').read_text())['files'][0];remote=BoundedRemoteZip(meta['links']['self'],meta['size'],limit=20*2**20);records=[]
 try:
  with zipfile.ZipFile(remote) as z:
   infos=[z.getinfo(d.replace('-','_')+'_030000.npz') for d in DATES]
   assert sum(x.compress_size for x in infos)+remote.reserved<20*2**20
   dump(F/'member_preflight.json',dict(all_four_members_present=True,central_directory_entries=len(z.infolist()),members=[dict(name=i.filename,header_offset=i.header_offset,bytes=i.file_size,compressed=i.compress_size,CRC32=i.CRC) for i in infos]))
   for info in infos:
    b=z.read(info.filename);assert zlib.crc32(b)&0xffffffff==info.CRC;p=RAW/info.filename
    with p.open('xb') as stream:stream.write(b)
    stats=validate_npz(p);p.chmod(0o444);record=dict(name=info.filename,CRC32_verified=True,CRC32=info.CRC,sha256=sha(p),bytes=len(b),stats=stats);records.append(record);dump(F/(p.stem+'_download.json'),record)
  dump(F/'download.json',dict(status='PASS',source=meta['links']['self'],archive_bytes=meta['size'],records=records,no_existing_data_download=True))
 finally:dump(F/'ranges.json',dict(transfer_bytes=remote.total,reserved_bytes=remote.reserved,limit_bytes=remote.limit,requests=remote.requests,completed_members=[r['name'] for r in records]))
 print('Four 03h members PASS; network body bytes',remote.total)

def prepare():
 from ruamel.yaml import YAML
 assert not (F/'preflight.json').exists() and not D.exists();assert json.loads((F/'download.json').read_text())['status']=='PASS'
 for p,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==h,p
 tests=(ROOT/'logs/fourcastden_four_model_tests.log').read_text();assert 'Ran 226 tests' in tests and tests.rstrip().endswith('OK')
 assert shutil.disk_usage(ROOT).free>20*2**30
 view=F/'data_view';view.mkdir();data=[]
 for day in DATES:
  for h in range(4):
   p=(ROOT/('data/raw/fourcastden_multidate_v1' if h<3 else 'data/raw/fourcastden_four_model_multidate_v1')/f"{day.replace('-','_')}_{h:02d}0000.npz").resolve();p.relative_to(ROOT);stats=validate_npz(p);(view/p.name).symlink_to(p);data.append(dict(source=str(p.relative_to(ROOT)),name=p.name,sha256=sha(p),stats=stats))
 configs={};yaml=YAML()
 for m in MODELS:
  cfg=yaml.load((JAN/f'{m}.yaml').read_text());cfg['afno_inference'].update(test_data_path=str(view),pre_resultname='four_model_multidate_'+m)
  with (F/f'{m}.yaml').open('x') as f:yaml.dump(cfg,f)
  configs[m]=sha(F/f'{m}.yaml')
 old=ROOT/'experiments/fourcastden_logden_multidate_v1';comp=json.loads((old/'compatibility.json').read_text());assert sha(old/'inference_overlay.py')==comp['overlay_SHA256']
 january=json.loads((JAN/'runtime.json').read_text());assert january['status']=='PASS'
 jan_sources={m:dict(source=str((JAND/f'{m}.npz').relative_to(ROOT)),sha256=next(r['result_sha256'] for r in january['records'] if r['model']==m)) for m in MODELS}
 for r in jan_sources.values():assert sha(ROOT/r['source'])==r['sha256']
 dump(F/'preflight.json',dict(status='PASS',new_dates=list(DATES),all_dates=list(ALL_DATES),models=list(MODELS),t0_hour_UTC=1,target_hours_UTC=[2,3],data=data,config_sha256=configs,checkpoint_sha256={m:sha(ROOT/'models/checkpoints/author'/CHECKPOINTS[m]) for m in MODELS},overlay_sha256=comp['overlay_SHA256'],january_read_only=jan_sources,code_sha256={p:sha(ROOT/p) for p in ['scripts/run_fourcastden_four_model_multidate.py','src/fourcastden/four_model_windows.py','tests/test_fourcastden_four_model_multidate.py','docs/FOURCASTDEN_FOUR_MODEL_MULTIDATE_PREREGISTRATION.md']},tests=226,resource_forecast=dict(conservative_wall_s=200,result_bytes_upper=500*2**20,estimated_peak_RSS_GiB=2.),limits=dict(GPU_wall_s=600,RSS_bytes=4*2**30,new_bytes=650*2**20),free_disk_GiB=shutil.disk_usage(ROOT).free/2**30))
 print('Preflight PASS; only 16 new sequences / 32 forwards; January read-only')

def verify():
 pre=json.loads((F/'preflight.json').read_text());assert pre['status']=='PASS'
 for p,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==h,p
 for p,h in pre['code_sha256'].items():assert sha(ROOT/p)==h,p
 for m,h in pre['config_sha256'].items():assert sha(F/f'{m}.yaml')==h
 for e in pre['data']:assert sha(ROOT/e['source'])==e['sha256']
 for e in pre['january_read_only'].values():assert sha(ROOT/e['source'])==e['sha256']
 assert sha(ROOT/'experiments/fourcastden_logden_multidate_v1/inference_overlay.py')==pre['overlay_sha256'];return pre

def execute():
 import torch
 from utils.YParams import YParams
 import inference.inference as ordinary
 pre=verify();D.mkdir(exist_ok=False);dump(F/'launch_once.json',dict(formal_sequences=16,formal_forwards=32,precheck_forwards=0,January_rerun=False,no_retry=True));tick=time.perf_counter();records=[];day=model=None
 try:
  torch.set_num_threads(4);assert torch.cuda.is_available();torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
  for model in MODELS:
   module=load_overlay(ROOT/'experiments/fourcastden_logden_multidate_v1/inference_overlay.py') if model=='LogDEN' else ordinary
   params=YParams(str(F/f'{model}.yaml'),'afno_inference');params['experiment_dir']=str(F)
   t=time.perf_counter();forecast=module.TGCMForecast(params);torch.cuda.synchronize();loading=time.perf_counter()-t;loadpeak=torch.cuda.max_memory_allocated();hist=int(model=='History')
   assert (params.n_in_channels,params.n_out_channels,params.n_history,params.n_prediction,params.n_in_indices)==(177,171,hist,2,4)
   for i,day in enumerate(DATES):
    dump(F/f'{day}_{model}_launch.json',dict(date=day,model=model,forwards=2))
    indices=window_indices(forecast.dataset.epochs,day,hist);ic=indices[0]
    t=time.perf_counter();data,sw,_,stds,means=forecast.dataset.get_data(indices,inference=True);read=time.perf_counter()-t
    for k,h in enumerate(range(0 if hist else 1,4)):
     with np.load(F/'data_view'/f"{day.replace('-','_')}_{h:02d}0000.npz") as z:
      raw=np.concatenate([z[v] for v in ['TN','UN','VN','WN','Z','DEN','TLBC','ULBC','VLBC']],axis=0)
      if model=='LogDEN':raw[142:171]=np.log10(raw[142:171])
      np.testing.assert_array_equal(data[k,:174].numpy(),((raw-means)/stds).astype(np.float32))
    inputs=[];outputs=[];gpu=[];events=[]
    def before(net,args):
     inputs.append(tuple(x.detach().cpu().numpy().copy() for x in args));a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True);events.append((a,b));a.record()
    def after(net,args,result):
     a,b=events[-1];b.record();b.synchronize();gpu.append(a.elapsed_time(b));out=result.detach().cpu().numpy().copy();outputs.append(out)
     if model!='Flow':assert (decode_physical(out,means[:171],stds[:171],model=='LogDEN')[:,:28]>0).all()
    h1=forecast.model.register_forward_pre_hook(before);h2=forecast.model.register_forward_hook(after);torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
    with MetricTrace(module) as trace:real,pred,rmse,acc,accu,last,_,_=forecast.inference(ic)
    torch.cuda.synchronize();loop=time.perf_counter()-t;h1.remove();h2.remove();assert len(inputs)==2
    states=[o+inputs[j][0][:,:171] for j,o in enumerate(outputs)] if model=='Flow' else outputs
    check=history_feedback_check(inputs,states,data.numpy(),sw.numpy()) if hist else feedback_check(inputs,states,real[0],sw.numpy())
    for j in range(2):np.testing.assert_array_equal(pred[0,j+1],states[j][0])
    physical=decode_physical(pred[0],means[:171],stds[:171],model=='LogDEN');assert (physical[:,:28]>0).all() and np.isfinite(pred).all()
    output=D/f'{day}_{model}.npz';t=time.perf_counter();np.savez_compressed(output,real=real,pred=pred,means=means,stds=stds,climatology=forecast.time_means[:171].cpu().numpy(),author_rmse=rmse,author_acc=acc,author_acc_unweighted=accu,author_normalized_rmse=np.stack(trace.normalized_rmse),author_physical_den_pred=np.concatenate(trace.physical_pred,axis=0) if trace.physical_pred else np.empty(0),author_physical_den_target=np.concatenate(trace.physical_target,axis=0) if trace.physical_target else np.empty(0),input0=inputs[0][0],input1=inputs[1][0],scalars0=inputs[0][1],scalars1=inputs[1][1],out0=states[0],out1=states[1],raw_network0=outputs[0],raw_network1=outputs[1],full_data=data.numpy(),full_sw=sw.numpy());save=time.perf_counter()-t
    r=dict(date=day,model=model,status='PASS',parameters=sum(p.numel() for p in forecast.model.parameters()),checkpoint_bytes=(ROOT/'models/checkpoints/author'/CHECKPOINTS[model]).stat().st_size,checkpoint_sha256=pre['checkpoint_sha256'][model],config_sha256=pre['config_sha256'][model],input_shape=list(inputs[0][0].shape),output_shape=list(outputs[0].shape),formal_forwards=2,n_history=hist,model_load_s=loading if i==0 else 0.,model_reused=i>0,loading_peak_allocated_bytes=loadpeak,read_preprocess_s=read,author_loop_metrics_hooks_s=loop,save_s=save,GPU_forward_ms=gpu,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,feedback=check,result_sha256=sha(output),result_bytes=output.stat().st_size,DEN_positive_fraction=1.,rho_min_kg_m3=float(physical[1:,142:].min()*1000),rho_max_kg_m3=float(physical[1:,142:].max()*1000))
    dump(F/f'{day}_{model}_runtime.json',r);records.append(r);print(json.dumps(dict(date=day,model=model,status='PASS',forward_ms=gpu)),flush=True)
    del data,sw,real,pred,physical,inputs,outputs,states,trace;gc.collect()
   del forecast;gc.collect();torch.cuda.empty_cache()
  dump(F/'runtime.json',dict(status='PASS',labels=['HINDCAST','TIEGCM_REFERENCE_ONLY','NO_TRAINING'],formal_sequences=16,formal_forwards=32,precheck_forwards=0,January_rerun=False,GPU_phase_wall_s=time.perf_counter()-tick,records=records,torch=torch.__version__,cuda=torch.version.cuda,device=torch.cuda.get_device_name(),FP32=True,TF32=False))
 except Exception as e:dump(F/'failure.json',dict(date=day,model=model,error=str(e),traceback=traceback.format_exc(),completed_sequences=[r['date']+'_'+r['model'] for r in records],no_retry=True));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fetch',action='store_true');p.add_argument('--execute',action='store_true');a=p.parse_args();fetch() if a.fetch else execute() if a.execute else prepare()
