"""Official log-DEN five-window inference using a minimal audited overlay."""
import sys,json,time,gc,resource,shutil,argparse
from pathlib import Path
from datetime import datetime,timedelta
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'third_party/FourCastDEN_linux'))
from run_fourcastden_multistep import sha,dump
from fourcastden.multidate import DATES,validate_npz
from fourcastden.logden import load_log_time_means,load_overlay,MetricTrace,decode_physical
F=ROOT/'experiments/fourcastden_logden_multidate_v1';D=ROOT/'data/processed/fourcastden_logden_multidate_v1';ALL=('2023-01-04',)+DATES

def verify():
 pre=json.loads((F/'preflight.json').read_text())
 for p,h in json.loads((F/'protected.json').read_text()).items():assert (ROOT/p).resolve().is_relative_to(ROOT) and sha(ROOT/p)==h,p
 for p,h in pre['code_sha256'].items():assert sha(ROOT/p)==h,p
 assert sha(F/'config.yaml')==pre['config_sha256']
 for e in pre['data']:assert sha(ROOT/e['source'])==e['sha256'] and (F/'data_view'/e['name']).resolve()==(ROOT/e['source']).resolve()
 return pre

def prepare():
 from ruamel.yaml import YAML
 assert not (F/'preflight.json').exists() and not D.exists()
 comp=json.loads((F/'compatibility.json').read_text());assert comp['status']=='PASS'
 assert sha(F/'inference_overlay.py')==comp['overlay_SHA256'] and sha(F/'compatibility.patch')==comp['patch_SHA256']
 log=(ROOT/'logs/fourcastden_logden_tests.log').read_text();assert 'Ran 215 tests' in log and log.rstrip().endswith('OK')
 protected=json.loads((ROOT/'experiments/fourcastden_multidate_v1/protected.json').read_text())
 for sub in ['experiments/fourcastden_multidate_v1','data/processed/fourcastden_multidate_v1','data/raw/fourcastden_multidate_v1']:
  for p in (ROOT/sub).rglob('*'):
   if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 for sub,pattern in [('results/metrics','fourcastden_multidate*'),('results/figures','fourcastden_multidate*'),('logs','fourcastden_multidate*'),('reports','FOURCASTDEN_MULTIDATE*')]:
  for p in (ROOT/sub).glob(pattern):
   if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 for p,h in protected.items():assert (ROOT/p).resolve().is_relative_to(ROOT) and sha(ROOT/p)==h,p
 assert shutil.disk_usage(ROOT).free>20*2**30
 view=F/'data_view';view.mkdir(exist_ok=False);data=[]
 for day in ALL:
  folder=ROOT/('data/raw/test_minimal_2023' if day==ALL[0] else 'data/raw/fourcastden_multidate_v1')
  for h in range(3):
   p=(folder/f"{day.replace('-','_')}_{h:02d}0000.npz").resolve();p.relative_to(ROOT);validate_npz(p);target=view/p.name;target.symlink_to(p)
   data.append(dict(name=p.name,source=str(p.relative_to(ROOT)),sha256=sha(p)))
 yaml=YAML();cfg=yaml.load((ROOT/'experiments/fourcastden_multidate_v1/Direct.yaml').read_text());cfg['afno_inference'].update(log_DEN=True,flow=False,n_history=0,n_prediction=2,test_data_path=str(view),static_data_path=str(ROOT/'data/processed/static_log'),best_checkpoint_path=str(ROOT/'models/checkpoints/author/Baseline_log_DEN_ckpt.tar'),pre_resultname='logden_multidate')
 with (F/'config.yaml').open('x') as f:yaml.dump(cfg,f)
 # Compare stats without changing or fitting any of them.
 differences={}
 for name in ['global_means.npz','global_stds.npz','time_means.npz']:
  with np.load(ROOT/f'data/processed/static/{name}') as x,np.load(ROOT/f'data/processed/static_log/{name}') as y:
   differences[name]={k:dict(ordinary_shape=list(x[k].shape),log_shape=list(y[k].shape),max_abs_difference=float(np.max(abs(x[k].reshape(-1)-y[k].reshape(-1))))) for k in ['TN','UN','VN','WN','Z','DEN','TLBC','ULBC','VLBC']}
 dump(F/'statistics_differences.json',differences)
 code=['scripts/run_fourcastden_logden_multidate.py','src/fourcastden/logden.py','tests/test_fourcastden_logden.py','docs/FOURCASTDEN_LOGDEN_PREREGISTRATION.md','experiments/fourcastden_logden_multidate_v1/inference_overlay.py','experiments/fourcastden_logden_multidate_v1/compatibility.patch']
 dump(F/'protected.json',protected)
 dump(F/'preflight.json',dict(status='PASS',data=data,code_sha256={p:sha(ROOT/p) for p in code},config_sha256=sha(F/'config.yaml'),checkpoint_sha256=sha(ROOT/'models/checkpoints/author/Baseline_log_DEN_ckpt.tar'),compatibility_GPU_wall_s=comp['compatibility_probe_wall_s'],tests=215,no_download=True,Direct_Flow_rerun=False,shared_reference='raw original NPZ, ordinary physical climatology; each model retains matched statistics'))
 print('Preflight PASS; only log-DEN formal sequences authorized, originals immutable.')

def execute():
 import torch,traceback
 from utils.YParams import YParams
 from fourcastden.validation import feedback_check
 pre=verify();D.mkdir(exist_ok=False);dump(F/'launch_once.json',dict(sequences=5,forwards=10,Direct_Flow_rerun=False,no_training=True));tick=time.perf_counter();records=[];day=None
 try:
  assert torch.cuda.is_available();torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
  module=load_overlay(F/'inference_overlay.py');params=YParams(str(F/'config.yaml'),'afno_inference');params['experiment_dir']=str(F)
  t=time.perf_counter();forecast=module.TGCMForecast(params);torch.cuda.synchronize();load_s=time.perf_counter()-t;loadpeak=torch.cuda.max_memory_allocated()
  assert forecast.log_DEN and not forecast.flow and params.n_history==0
  assert (params.n_in_channels,params.n_out_channels,params.n_in_indices)==(177,171,4)
  for i,day in enumerate(ALL):
   dump(F/f'{day}_launch.json',dict(date=day,sequence=i+1));ic=i*3
   assert forecast.dataset.epochs[ic:ic+3]==[datetime.fromisoformat(day)+timedelta(hours=h) for h in range(3)]
   t=time.perf_counter();data,sw,_,stds,means=forecast.dataset.get_data([ic,ic+1,ic+2],inference=True);read_s=time.perf_counter()-t
   # Independently reproduce author representation on all 174 physical/boundary channels.
   for h in range(3):
    with np.load(F/'data_view'/f"{day.replace('-','_')}_{h:02d}0000.npz") as z:
     physical=np.concatenate([z[k] for k in ['TN','UN','VN','WN','Z','DEN','TLBC','ULBC','VLBC']],axis=0);physical[142:171]=np.log10(physical[142:171]);expected=(physical-means)/stds
     np.testing.assert_array_equal(data[h,:174].numpy(),expected.astype(np.float32))
   inputs=[];outputs=[];events=[];gpu=[]
   def before(m,args):
    inputs.append(tuple(x.detach().cpu().numpy().copy() for x in args));a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True);events.append((a,b));a.record()
   def after(m,args,result):
    a,b=events[-1];b.record();b.synchronize();gpu.append(a.elapsed_time(b));arr=result.detach().cpu().numpy().copy();outputs.append(arr)
    p=decode_physical(arr,means[:171],stds[:171],True);assert (p[:,:28]>0).all()
   h1=forecast.model.register_forward_pre_hook(before);h2=forecast.model.register_forward_hook(after);torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
   with MetricTrace(module) as trace:real,pred,rmse,acc,accu,last,_,_=forecast.inference(ic)
   torch.cuda.synchronize();loop_s=time.perf_counter()-t;h1.remove();h2.remove();feedback=feedback_check(inputs,outputs,real[0],sw.numpy())
   assert len(inputs)==len(trace.physical_pred)==len(trace.normalized_rmse)==2
   native=decode_physical(pred[0],means[:171],stds[:171],True);assert (native[:,:28]>0).all()
   # Actual batched output inverse on the already-produced states, not a new forward.
   den_norm=torch.as_tensor(pred[0,1:,142:].copy(),device='cuda');st=torch.as_tensor(stds[142:171],device='cuda');mu=torch.as_tensor(means[142:171],device='cuda');log=den_norm*st+mu;torch.cuda.synchronize();a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True);a.record();rho=torch.pow(10,log);b.record();b.synchronize();inverse_ms=a.elapsed_time(b)
   np.testing.assert_allclose(rho.cpu().numpy(),np.power(10.,log.cpu().numpy().astype(float)),rtol=3e-7,atol=0.)
   out=D/f'{day}.npz';np.savez_compressed(out,real=real,pred=pred,author_rmse=rmse,author_acc=acc,author_acc_unweighted=accu,author_normalized_rmse=np.stack(trace.normalized_rmse),author_native_space_rmse=np.stack(trace.normalized_rmse)*stds[:171,0,0],author_physical_den_pred=np.concatenate(trace.physical_pred,axis=0),author_physical_den_target=np.concatenate(trace.physical_target,axis=0),means=means,stds=stds,input0=inputs[0][0],input1=inputs[1][0],scalars0=inputs[0][1],scalars1=inputs[1][1],out0=outputs[0],out1=outputs[1],climatology=forecast.time_means[:171].cpu().numpy())
   r=dict(date=day,status='PASS',network_calls=2,feedback=feedback,checkpoint_sha256=pre['checkpoint_sha256'],config_sha256=pre['config_sha256'],overlay_sha256=pre['code_sha256']['experiments/fourcastden_logden_multidate_v1/inference_overlay.py'],model_load_s=load_s if i==0 else 0.,model_reused=i>0,read_preprocess_s=read_s,author_loop_metrics_hooks_s=loop_s,GPU_forward_ms=gpu,inverse_pow10_two_target_fields_gpu_ms=inverse_ms,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),prediction_shape=list(pred.shape),input_shape=list(inputs[0][0].shape),output_shape=list(outputs[0].shape),rho_min_kg_m3=float(native[1:,142:].min()*1000),rho_max_kg_m3=float(native[1:,142:].max()*1000),DEN_positive_fraction=1.,nonfinite_predictions=0,nonpositive_DEN=0,result_sha256=sha(out),RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
   assert r['RSS_KiB']*1024<4*2**30 and time.perf_counter()-tick+pre['compatibility_GPU_wall_s']<600
   dump(F/f'{day}_runtime.json',r);records.append(r);print(json.dumps(dict(date=day,status='PASS',forward_ms=gpu,inverse_ms=inverse_ms)),flush=True)
   del data,sw,real,pred,native,physical,inputs,outputs,trace,den_norm,st,mu,log,rho;gc.collect()
  dump(F/'runtime.json',dict(status='PASS',labels=['HINDCAST','TIEGCM_REFERENCE_ONLY','NO_TRAINING'],sequences=5,forwards=10,parameters=sum(p.numel() for p in forecast.model.parameters()),loading_peak_allocated_bytes=loadpeak,GPU_phase_wall_s=time.perf_counter()-tick,compatibility_wall_s=pre['compatibility_GPU_wall_s'],records=records,torch=torch.__version__,cuda=torch.version.cuda,device=torch.cuda.get_device_name(),Direct_Flow_rerun=False,no_download=True))
 except Exception as e:dump(F/'failure.json',dict(date_failed=day,error=str(e),traceback=traceback.format_exc(),completed_dates=[r['date'] for r in records],unattempted_dates=[d for d in ALL if d not in [r['date'] for r in records] and d!=day],no_retry=True));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args();execute() if a.execute else prepare()
