"""Once-only official Flow inference. Direct is read-only historical evidence."""
import sys,json,time,shutil,traceback,argparse,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'third_party/FourCastDEN_linux'))
from run_fourcastden_multistep import sha,dump
F=ROOT/'experiments/fourcastden_flow_two_step_v1'
D=ROOT/'data/processed/fourcastden_flow_two_step_v1'
OLD=ROOT/'experiments/fourcastden_two_step_v1'
def prepare():
 from ruamel.yaml import YAML
 import numpy as np
 for p in (F,D):p.resolve().relative_to(ROOT);assert not p.exists(),p
 assert 'Ran 198 tests' in (ROOT/'logs/fourcastden_flow_tests.log').read_text()
 assert (ROOT/'logs/fourcastden_flow_tests.log').read_text().rstrip().endswith('OK')
 protected=json.loads((OLD/'protected.json').read_text())
 for p in OLD.rglob('*'):
  if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 for folder,pattern in [('results/metrics','fourcastden_two_step_v1*'),('results/figures','fourcastden_two_step_v1*'),('logs','fourcastden_two_step*')]:
  for p in (ROOT/folder).glob(pattern):
   if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 legacy=json.loads((OLD/'runtime.json').read_text())
 oldresult=ROOT/'data/processed/fourcastden_two_step_v1/result.npz'
 assert sha(oldresult)==legacy['file_sha256'];protected[str(oldresult.relative_to(ROOT))]=legacy['file_sha256']
 for p,h in protected.items():assert (ROOT/p).resolve().is_relative_to(ROOT) and sha(ROOT/p)==h,p
 yaml=YAML();official=yaml.load((ROOT/'third_party/FourCastDEN/config/AFNO.yaml').read_text())['afno_inference']
 direct=yaml.load((OLD/'config.yaml').read_text())['afno_inference']
 keys=['model_name','num_blocks','patch_size','dt','depth','embed_dim','mlp_ratio','drop_rate','in_variables','out_variables','in_drivers','n_history','log_DEN','normalization','solar','geomagnetic','n_lon_periodic']
 assert all(official[k]==direct[k] for k in keys)
 cfg=dict(official);cfg.update(test_data_path=str(ROOT/'data/raw/test_minimal_2023'),best_checkpoint_path=str(ROOT/'models/checkpoints/author/Flow_ckpt.tar'),static_data_path=str(ROOT/'data/processed/static'),n_prediction=2,num_workers=0,img_shape_x=36,img_shape_y=72,log_to_screen=False,pre_resultname='flow_two_step')
 assert cfg['flow'] and not cfg['log_DEN'] and cfg['n_history']==0
 assert shutil.disk_usage(ROOT).free>20*2**30
 F.mkdir()
 with (F/'config.yaml').open('x') as f:yaml.dump({'afno_inference':cfg},f)
 dump(F/'protected.json',protected)
 g=subprocess.check_output(['nvidia-smi','--query-gpu=name,memory.free,utilization.gpu','--format=csv,noheader'],text=True).strip()
 dump(F/'preflight.json',dict(passed=True,Direct_not_rerun=True,architecture_keys_equal=keys,protected_files=len(protected),checkpoint_SHA256=protected['models/checkpoints/author/Flow_ckpt.tar'],free_disk_GiB=shutil.disk_usage(ROOT).free/2**30,gpu=g,code_sha256={p:sha(ROOT/p) for p in ['scripts/run_fourcastden_flow_two_step.py','src/fourcastden/flow_validation.py','docs/FOURCASTDEN_FLOW_PREREGISTRATION.md','tests/test_fourcastden_flow.py']},config_sha256=sha(F/'config.yaml')))
 print('Flow preflight PASS; Direct is read-only; no GPU inference launched.')
def execute():
 import numpy as np,torch
 from fourcastden.flow_validation import flow_feedback_check
 from utils.YParams import YParams
 from inference.inference import TGCMForecast
 pre=json.loads((F/'preflight.json').read_text());assert pre['passed']
 assert sha(F/'config.yaml')==pre['config_sha256']
 for p,h in pre['code_sha256'].items():assert sha(ROOT/p)==h,p
 for p,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==h,p
 D.mkdir(exist_ok=False);dump(F/'launch_once.json',dict(formal_runs=1,expected_forwards=2,no_training=True,Direct_rerun=False))
 tick=time.perf_counter();report=dict(status='running',labels=['HINDCAST','TIEGCM_REFERENCE_ONLY','NO_TRAINING'])
 try:
  assert torch.cuda.is_available();torch.set_num_threads(4)
  torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
  params=YParams(str(F/'config.yaml'),'afno_inference');params['experiment_dir']=str(F)
  t=time.perf_counter();forecast=TGCMForecast(params);torch.cuda.synchronize();load_s=time.perf_counter()-t
  load_peak=torch.cuda.max_memory_allocated();assert forecast.flow and not forecast.log_DEN
  assert (params.n_in_channels,params.n_out_channels,params.n_in_indices,params.n_history,params.n_prediction)==(177,171,4,0,2)
  t=time.perf_counter();data,sw,_,stds,means=forecast.dataset.get_data([0,1,2],inference=True);read_s=time.perf_counter()-t
  assert len(forecast.dataset.epochs)==3 and (stds>0).all()
  inputs=[];increments=[];events=[];gpu_times=[]
  def before(module,args):
   inputs.append(tuple(x.detach().cpu().numpy().copy() for x in args));a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True);events.append((a,b));a.record()
  def after(module,args,result):
   a,b=events[-1];b.record();b.synchronize();gpu_times.append(a.elapsed_time(b));increments.append(result.detach().cpu().numpy().copy())
  h1=forecast.model.register_forward_pre_hook(before);h2=forecast.model.register_forward_hook(after)
  torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
  real,pred,rmse,acc,accu,last,_,_=forecast.inference(0);torch.cuda.synchronize();loop_s=time.perf_counter()-t;h1.remove();h2.remove()
  check=flow_feedback_check(inputs,increments,real[0],pred[0],sw.numpy())
  with np.load(ROOT/'data/processed/fourcastden_two_step_v1/result.npz') as old:
   for k,v in [('real',real),('means',means),('stds',stds),('climatology',forecast.time_means[:171].cpu().numpy())]:np.testing.assert_array_equal(v,old[k])
   np.testing.assert_array_equal(pred[0,0],old['pred'][0,0])
   for k in range(2):
    np.testing.assert_array_equal(inputs[k][0][:,171:],old[f'input{k}'][:,171:]);np.testing.assert_array_equal(inputs[k][1],old[f'scalars{k}'])
  physical=pred[0].astype(float)*stds[:171].astype(float)+means[:171].astype(float)
  assert np.isfinite(physical).all() and (physical[:,142:]>0).all() and (physical[:,:28]>0).all(),'Nonphysical prediction; no clipping permitted'
  np.savez_compressed(D/'result.npz',real=real,pred=pred,author_rmse=rmse,author_acc=acc,author_acc_unweighted=accu,means=means,stds=stds,input0=inputs[0][0],input1=inputs[1][0],scalars0=inputs[0][1],scalars1=inputs[1][1],increment0=increments[0],increment1=increments[1],climatology=forecast.time_means[:171].cpu().numpy())
  elapsed=time.perf_counter()-tick;newbytes=sum(p.stat().st_size for folder in [F,D] for p in folder.rglob('*') if p.is_file());assert elapsed<300 and newbytes<500*2**20
  report.update(status='Flow_two_step_passed_not_full_paper_reproduction',parameters=sum(p.numel() for p in forecast.model.parameters()),strict_author_checkpoint_loading=True,checkpoint_sha256=pre['checkpoint_SHA256'],network_calls=len(inputs),input_shape=list(inputs[0][0].shape),increment_shape=list(increments[0].shape),state_shape=list(pred.shape),feedback=check,Direct_initial_targets_stats_aux_drivers_equal=True,torch=torch.__version__,cuda=torch.version.cuda,device=torch.cuda.get_device_name(),FP32=True,TF32=False,model_load_including_CUDA_initialization_s=load_s,preprocess_read_s=read_s,author_loop_metrics_hooks_s=loop_s,network_GPU_ms=gpu_times,GPU_phase_wall_s=elapsed,loading_peak_allocated_bytes=load_peak,inference_peak_allocated_bytes=torch.cuda.max_memory_allocated(),inference_peak_reserved_bytes=torch.cuda.max_memory_reserved(),DEN_positive_fraction=float((physical[1:,142:]>0).mean()),file_sha256=sha(D/'result.npz'),new_experiment_bytes=newbytes,last_loaded_time=str(last),no_Direct_execution=True)
  dump(F/'runtime.json',report);print(json.dumps(report,indent=2))
 except Exception as e:
  report.update(status='failed',error=str(e),traceback=traceback.format_exc());dump(F/'failure.json',report);raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args()
 execute() if a.execute else prepare()
