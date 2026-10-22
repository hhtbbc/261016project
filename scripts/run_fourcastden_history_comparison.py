"""Official four-model 01->02->03 experiment, with H=1 native history path."""
import sys,json,time,argparse,zipfile,zlib,gc,traceback,shutil,resource
from pathlib import Path
from datetime import datetime,timedelta
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'third_party/FourCastDEN_linux'))
from run_fourcastden_multistep import sha,dump
from fourcastden.multidate import BoundedRemoteZip,validate_npz
from fourcastden.logden import decode_physical,load_overlay,MetricTrace
from fourcastden.history import history_feedback_check
from fourcastden.validation import feedback_check
F=ROOT/'experiments/fourcastden_history_comparison_v1';D=ROOT/'data/processed/fourcastden_history_comparison_v1';RAW=ROOT/'data/raw/fourcastden_history_comparison_v1'
MODELS=('History','Direct','Flow','LogDEN')
CHECKPOINTS=dict(History='Baseline_1h_history_ckpt.tar',Direct='Direct_ckpt.tar',Flow='Flow_ckpt.tar',LogDEN='Baseline_log_DEN_ckpt.tar')

def fetch():
 F.mkdir(exist_ok=False);RAW.mkdir(exist_ok=False);dump(F/'fetch_once.json',dict(member='2023_01_04_030000.npz',limit=10*2**20))
 protected=json.loads((ROOT/'experiments/fourcastden_logden_multidate_v1/protected.json').read_text())
 for folder in ['experiments/fourcastden_logden_multidate_v1','data/processed/fourcastden_logden_multidate_v1']:
  for p in (ROOT/folder).rglob('*'):
   if p.is_file() and not p.is_symlink():protected[str(p.relative_to(ROOT))]=sha(p)
 for p,h in protected.items():assert sha(ROOT/p)==h,p
 dump(F/'protected.json',protected)
 meta=json.loads((ROOT/'logs/zenodo_21859635_20261019.json').read_text())['files'][0];remote=BoundedRemoteZip(meta['links']['self'],meta['size'],limit=10*2**20)
 try:
  with zipfile.ZipFile(remote) as z:
   info=z.getinfo('2023_01_04_030000.npz');assert info.file_size<10*2**20 and info.compress_size<10*2**20
   b=z.read(info.filename);assert zlib.crc32(b)&0xffffffff==info.CRC
   p=RAW/info.filename
   with p.open('xb') as stream:stream.write(b)
   stats=validate_npz(p);dump(F/'download.json',dict(status='PASS',url=meta['links']['self'],archive_bytes=meta['size'],member=info.filename,header_offset=info.header_offset,compressed_bytes=info.compress_size,bytes=info.file_size,CRC32=info.CRC,CRC32_verified=True,SHA256=sha(p),stats=stats,central_directory_members=len(z.infolist())))
 finally:dump(F/'ranges.json',dict(transfer_bytes=remote.total,reserved_bytes=remote.reserved,limit_bytes=remote.limit,requests=remote.requests))
 print('Single 03h member fetched and verified',remote.total,'bytes',flush=True)

def prepare():
 from ruamel.yaml import YAML
 assert not (F/'preflight.json').exists() and not D.exists();assert json.loads((F/'download.json').read_text())['status']=='PASS'
 assert shutil.disk_usage(ROOT).free>20*2**30
 for p,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==h,p
 tests=(ROOT/'logs/fourcastden_history_tests.log').read_text();assert 'Ran 221 tests' in tests and tests.rstrip().endswith('OK')
 view=F/'data_view';view.mkdir();data=[]
 for h in range(4):
  p=(ROOT/('data/raw/test_minimal_2023' if h<3 else 'data/raw/fourcastden_history_comparison_v1')/f'2023_01_04_{h:02d}0000.npz').resolve();p.relative_to(ROOT);stats=validate_npz(p);(view/p.name).symlink_to(p);data.append(dict(source=str(p.relative_to(ROOT)),name=p.name,sha256=sha(p),stats=stats))
 yaml=YAML();configs={}
 for model in MODELS:
  cfg=yaml.load((ROOT/'experiments/fourcastden_multidate_v1/Direct.yaml').read_text());cfg['afno_inference'].update(n_history=int(model=='History'),flow=model=='Flow',log_DEN=model=='LogDEN',test_data_path=str(view),static_data_path=str(ROOT/'data/processed'/('static_log' if model=='LogDEN' else 'static')),best_checkpoint_path=str(ROOT/'models/checkpoints/author'/CHECKPOINTS[model]),pre_resultname='history_common_'+model,date_time='2023-01-04 01:00:00')
  with (F/f'{model}.yaml').open('x') as stream:yaml.dump(cfg,stream)
  configs[model]=sha(F/f'{model}.yaml')
 old=ROOT/'experiments/fourcastden_logden_multidate_v1';comp=json.loads((old/'compatibility.json').read_text());assert sha(old/'inference_overlay.py')==comp['overlay_SHA256']
 dump(F/'preflight.json',dict(status='PASS',models=list(MODELS),t0='2023-01-04T01:00:00Z',targets=['2023-01-04T02:00:00Z','2023-01-04T03:00:00Z'],data=data,config_sha256=configs,checkpoint_sha256={m:sha(ROOT/'models/checkpoints/author'/CHECKPOINTS[m]) for m in MODELS},overlay_sha256=comp['overlay_SHA256'],code_sha256={p:sha(ROOT/p) for p in ['scripts/run_fourcastden_history_comparison.py','src/fourcastden/history.py','tests/test_fourcastden_history.py','docs/FOURCASTDEN_HISTORY_PREREGISTRATION.md']},tests=221,limits=dict(GPU_wall_s=600,RSS_bytes=4*2**30,new_bytes=150*2**20),history_information_advantage='00+01 vs 01 only; not a training ablation'))
 print('All static gates PASS')

def verify():
 pre=json.loads((F/'preflight.json').read_text());assert pre['status']=='PASS'
 for p,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==h,p
 for p,h in pre['code_sha256'].items():assert sha(ROOT/p)==h,p
 for m,h in pre['config_sha256'].items():assert sha(F/f'{m}.yaml')==h
 for e in pre['data']:assert sha(ROOT/e['source'])==e['sha256']
 assert sha(ROOT/'experiments/fourcastden_logden_multidate_v1/inference_overlay.py')==pre['overlay_sha256']
 return pre

def execute():
 import torch
 from utils.YParams import YParams
 import inference.inference as ordinary
 pre=verify();D.mkdir(exist_ok=False);dump(F/'launch_once.json',dict(formal_sequences=4,formal_forwards=8,history_preflight_forwards=1,no_retry=True));tick=time.perf_counter();records=[];model=None
 try:
  torch.set_num_threads(4);assert torch.cuda.is_available();torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
  for model in MODELS:
   dump(F/f'{model}_launch.json',dict(model=model,formal_sequences=1,formal_forwards=2))
   module=load_overlay(ROOT/'experiments/fourcastden_logden_multidate_v1/inference_overlay.py') if model=='LogDEN' else ordinary
   params=YParams(str(F/f'{model}.yaml'),'afno_inference');params['experiment_dir']=str(F)
   t=time.perf_counter();forecast=module.TGCMForecast(params);torch.cuda.synchronize();loading=time.perf_counter()-t;loadpeak=torch.cuda.max_memory_allocated()
   hist=int(model=='History');ic=0 if hist else 1;assert params.n_in_channels==177 and params.n_out_channels==171 and params.n_history==hist and params.n_in_indices==4
   assert forecast.dataset.epochs==[datetime(2023,1,4)+timedelta(hours=h) for h in range(4)]
   t=time.perf_counter();data,sw,_,stds,means=forecast.dataset.get_data(list(range(ic,4)),inference=True);read=time.perf_counter()-t
   for k,h in enumerate(range(ic,4)):
    with np.load(F/'data_view'/f'2023_01_04_{h:02d}0000.npz') as z:
     raw=np.concatenate([z[v] for v in ['TN','UN','VN','WN','Z','DEN','TLBC','ULBC','VLBC']],axis=0)
     if model=='LogDEN':raw[142:171]=np.log10(raw[142:171])
     np.testing.assert_array_equal(data[k,:174].numpy(),((raw-means)/stds).astype(np.float32))
   # Only the explicitly authorized one real History-forward precheck, before formal autoregression.
   precheck=None
   if hist:
    x=torch.cat([data[:2,:171],data[1:3,171:]],dim=1).reshape(1,354,36,72).to('cuda');s=sw[2].reshape(1,1,4).to('cuda');a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True);a.record()
    with torch.no_grad():out=forecast.forecast(x,s)
    b.record();b.synchronize();phys=decode_physical(out.cpu().numpy(),means[:171],stds[:171]);assert (phys[:,:28]>0).all()
    precheck=dict(status='PASS',input_shape=list(x.shape),output_shape=list(out.shape),network_GPU_ms=a.elapsed_time(b),DEN_positive_fraction=1.,rho_min_kg_m3=float(phys[:,142:].min()*1000),rho_max_kg_m3=float(phys[:,142:].max()*1000));dump(F/'history_real_forward_precheck.json',precheck)
    precheck_output=out.cpu().numpy().copy();del x,s,out,phys
   inputs=[];outputs=[];gpu=[];events=[]
   def before(net,args):
    inputs.append(tuple(a.detach().cpu().numpy().copy() for a in args));a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True);events.append((a,b));a.record()
   def after(net,args,result):
    a,b=events[-1];b.record();b.synchronize();gpu.append(a.elapsed_time(b));out=result.detach().cpu().numpy().copy();outputs.append(out)
    # Flow's raw forward is a delta; its state is checked after the original forecast update.
    if model!='Flow':assert (decode_physical(out,means[:171],stds[:171],model=='LogDEN')[:,:28]>0).all()
   h1=forecast.model.register_forward_pre_hook(before);h2=forecast.model.register_forward_hook(after);torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
   with MetricTrace(module) as trace:real,pred,rmse,acc,accu,last,_,_=forecast.inference(ic)
   torch.cuda.synchronize();loop=time.perf_counter()-t;h1.remove();h2.remove();assert len(inputs)==2
   # Module forward hook runs before original Flow += input; freeze hook outputs then reproduce official update for auditing.
   states=[o+inputs[i][0][:,:171] for i,o in enumerate(outputs)] if model=='Flow' else outputs
   if hist:
    feedback=history_feedback_check(inputs,states,data.numpy(),sw.numpy());np.testing.assert_array_equal(precheck_output,states[0])
   else:feedback=feedback_check(inputs,states,real[0],sw.numpy())
   for i in range(2):np.testing.assert_array_equal(pred[0,i+1],states[i][0])
   physical=decode_physical(pred[0],means[:171],stds[:171],model=='LogDEN');assert (physical[:,:28]>0).all() and np.isfinite(pred).all()
   output=D/f'{model}.npz';t=time.perf_counter();np.savez_compressed(output,real=real,pred=pred,means=means,stds=stds,climatology=forecast.time_means[:171].cpu().numpy(),author_rmse=rmse,author_acc=acc,author_acc_unweighted=accu,author_normalized_rmse=np.stack(trace.normalized_rmse),author_physical_den_pred=np.concatenate(trace.physical_pred,axis=0) if trace.physical_pred else np.empty(0),author_physical_den_target=np.concatenate(trace.physical_target,axis=0) if trace.physical_target else np.empty(0),input0=inputs[0][0],input1=inputs[1][0],scalars0=inputs[0][1],scalars1=inputs[1][1],out0=states[0],out1=states[1],raw_network0=outputs[0],raw_network1=outputs[1],full_data=data.numpy(),full_sw=sw.numpy());save=time.perf_counter()-t
   r=dict(model=model,status='PASS',parameters=sum(p.numel() for p in forecast.model.parameters()),checkpoint_bytes=(ROOT/'models/checkpoints/author'/CHECKPOINTS[model]).stat().st_size,checkpoint_sha256=pre['checkpoint_sha256'][model],config_sha256=pre['config_sha256'][model],n_history=hist,input_shape=list(inputs[0][0].shape),output_shape=list(outputs[0].shape),formal_forwards=2,history_precheck=precheck,model_load_s=loading,loading_peak_allocated_bytes=loadpeak,read_preprocess_s=read,author_loop_metrics_hooks_s=loop,save_s=save,GPU_forward_ms=gpu,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,feedback=feedback,result_sha256=sha(output),result_bytes=output.stat().st_size,DEN_positive_fraction=1.,rho_min_kg_m3=float(physical[1:,142:].min()*1000),rho_max_kg_m3=float(physical[1:,142:].max()*1000))
   dump(F/f'{model}_runtime.json',r);records.append(r);print(json.dumps(dict(model=model,status='PASS',forward_ms=gpu,parameters=r['parameters'])),flush=True)
   del forecast,data,sw,real,pred,physical,inputs,outputs,states,trace;gc.collect();torch.cuda.empty_cache()
  dump(F/'runtime.json',dict(status='PASS',labels=['HINDCAST','TIEGCM_REFERENCE_ONLY','NO_TRAINING'],formal_sequences=4,formal_forwards=8,precheck_forwards=1,GPU_phase_wall_s=time.perf_counter()-tick,records=records,torch=torch.__version__,cuda=torch.version.cuda,device=torch.cuda.get_device_name(),FP32=True,TF32=False))
 except Exception as e:dump(F/'failure.json',dict(model=model,error=str(e),traceback=traceback.format_exc(),completed_models=[r['model'] for r in records],no_retry=True));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fetch',action='store_true');p.add_argument('--execute',action='store_true');a=p.parse_args();fetch() if a.fetch else execute() if a.execute else prepare()
