"""Once-only official Direct 00->01->02 inference with runtime feedback audit."""
import sys,json,time,hashlib,zipfile,shutil,traceback,argparse
from pathlib import Path
from datetime import datetime,timedelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'third_party/FourCastDEN_linux'))
F=ROOT/'experiments/fourcastden_two_step_v1';D=ROOT/'data/processed/fourcastden_two_step_v1'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def dump(p,j):
 with p.open('x') as f:json.dump(j,f,indent=2,allow_nan=False)
def prepare():
 import numpy as np
 F.resolve().relative_to(ROOT);D.resolve().relative_to(ROOT);F.mkdir(exist_ok=False)
 protected={}
 # Original archive and both source trees are read only. Verify original byte-for-byte.
 with zipfile.ZipFile(ROOT/'data/raw/FourCastDEN.zip') as z:
  for info in z.infolist():
   if info.is_dir():continue
   p=ROOT/'third_party/FourCastDEN'/info.filename;p.resolve().relative_to(ROOT);assert p.read_bytes()==z.read(info.filename),p
 for tree in ['third_party/FourCastDEN','third_party/FourCastDEN_linux']:
  for p in (ROOT/tree).rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts:protected[str(p.relative_to(ROOT))]=sha(p)
 for name,e in json.loads((ROOT/'logs/checkpoint_sha256.json').read_text()).items():
  p=ROOT/'models/checkpoints/author'/name;assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'];protected[str(p.relative_to(ROOT))]=e['sha256']
 for kind in ['static','static_log']:
  with zipfile.ZipFile(ROOT/f'data/raw/{kind}.zip') as z:
   for info in z.infolist():
    if info.is_dir():continue
    p=ROOT/f'data/processed/{kind}'/info.filename;assert p.read_bytes()==z.read(info.filename);protected[str(p.relative_to(ROOT))]=sha(p)
 dates=[]
 for e in json.loads((ROOT/'logs/minimal_data_download.log').read_text())['saved']:
  p=ROOT/'data/raw/test_minimal_2023'/e['name'];assert sha(p)==e['sha256'];protected[str(p.relative_to(ROOT))]=e['sha256'];dates.append(datetime.strptime(p.stem,'%Y_%m_%d_%H%M%S'))
  with np.load(p,allow_pickle=False) as n:assert all(np.isfinite(n[k]).all() for k in n.files) and (n['DEN']>0).all()
 assert sorted(dates)==[datetime(2023,1,4)+timedelta(hours=i) for i in range(3)]
 # Existing science artifacts and frozen forces: no rerun or mutation allowed.
 for e in json.loads((ROOT/'experiments/common_density_h6_v1/independent_audit.json').read_text())['artifacts']:
  assert sha(ROOT/e['file'])==e['sha256'],e['file'];protected[e['file']]=e['sha256']
 for p in [ROOT/'experiments/20261019_minimal_direct/result.npz',ROOT/'logs/minimal_validation.json',ROOT/'logs/independent_result_checks.json',ROOT/'configs/fourcastden_direct_minimal.yaml',ROOT/'configs/provisional_common_force_model.json']:
  protected[str(p.relative_to(ROOT))]=sha(p)
 assert 'Ran 192 tests' in (ROOT/'logs/fourcastden_two_step_tests.log').read_text() and (ROOT/'logs/fourcastden_two_step_tests.log').read_text().rstrip().endswith('OK')
 dump(F/'protected.json',protected)
 from ruamel.yaml import YAML
 yaml=YAML();cfg=yaml.load((ROOT/'configs/fourcastden_direct_minimal.yaml').read_text());cfg['afno_inference'].update(n_prediction=2,n_history=0,flow=False,log_DEN=False,perturb=False,step_con=False,log_to_screen=False)
 with (F/'config.yaml').open('x') as f:yaml.dump(cfg,f)
 dump(F/'preflight.json',dict(passed=True,original_source_matches_archive=True,official_static_and_weights_verified=True,history_legacy_one_hour_result_sha256=sha(ROOT/'experiments/20261019_minimal_direct/result.npz'),three_sample_hours=[d.isoformat() for d in sorted(dates)],protected_count=len(protected),free_disk_GiB=shutil.disk_usage(ROOT).free/2**30,resource_limits=dict(GPU_wall_s=300,new_bytes=500*2**20),author_inference_direct_call_reason='Dataset has 3 real frames, H=0,L=2; get_data(0,1,2) valid; full-year CLI index loop not used',code_sha256={p:sha(ROOT/p) for p in ['scripts/run_fourcastden_multistep.py','src/fourcastden/validation.py','docs/FOURCASTDEN_TWO_STEP_PREREGISTRATION.md']}))
 print('Preflight passed; old single-hour result is historical evidence only.',flush=True)
def execute():
 import numpy as np,torch
 from fourcastden.validation import feedback_check
 pre=json.loads((F/'preflight.json').read_text());assert pre['passed']
 for p,h in pre['code_sha256'].items():assert sha(ROOT/p)==h,p
 for p,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==h,p
 D.mkdir(exist_ok=False);dump(F/'launch_once.json',dict(real_model_forecast_calls=2,formal_autoregressive_runs=1,no_training=True));tick=time.perf_counter();report=dict(labels=['HINDCAST','TIEGCM_REFERENCE_ONLY','NO_TRAINING'],status='running')
 try:
  assert torch.cuda.is_available();torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
  from utils.YParams import YParams
  from inference.inference import TGCMForecast
  params=YParams(str(F/'config.yaml'),'afno_inference');params['experiment_dir']=str(F)
  t=time.perf_counter();forecast=TGCMForecast(params);torch.cuda.synchronize();load_s=time.perf_counter()-t
  assert (params.n_in_channels,params.n_out_channels,params.n_in_indices,params.n_history,params.n_prediction)==(177,171,4,0,2)
  t=time.perf_counter();data,sw,_,stds,means=forecast.dataset.get_data([0,1,2],inference=True);read_s=time.perf_counter()-t;assert len(forecast.dataset.epochs)==3;assert np.isfinite(data.numpy()).all() and (stds>0).all()
  inputs=[];outputs=[];events=[];gpu_times=[]
  def before(module,args):
   inputs.append(tuple(x.detach().cpu().numpy().copy() for x in args));a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True);events.append((a,b));a.record()
  def after(module,args,result):
   a,b=events[-1];b.record();b.synchronize();gpu_times.append(a.elapsed_time(b));outputs.append(result.detach().cpu().numpy().copy())
  hook1=forecast.model.register_forward_pre_hook(before);hook2=forecast.model.register_forward_hook(after);torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
  real,pred,rmse,acc,accu,last,_,_=forecast.inference(0);torch.cuda.synchronize();inference_s=time.perf_counter()-t;hook1.remove();hook2.remove()
  assert np.isfinite(pred).all();check=feedback_check(inputs,outputs,real[0],sw.numpy())
  sigma=stds[:171].astype(np.float64);mu=means[:171].astype(np.float64);physical=pred[0].astype(np.float64)*sigma+mu
  assert np.isfinite(physical).all() and (physical[:,142:171]>0).all(), 'Nonphysical density: stop, do not clip'
  assert (physical[:,:28]>0).all()
  with np.load(ROOT/'experiments/20261019_minimal_direct/result.npz') as old:
   historical_delta=float(np.max(abs(pred[0,1]-old['pred'][0,1])));np.testing.assert_allclose(pred[0,1],old['pred'][0,1],rtol=2e-5,atol=2e-6)
  np.savez_compressed(D/'result.npz',real=real,pred=pred,author_rmse=rmse,author_acc=acc,author_acc_unweighted=accu,means=means,stds=stds,input0=inputs[0][0],input1=inputs[1][0],scalars0=inputs[0][1],scalars1=inputs[1][1],out0=outputs[0],out1=outputs[1],climatology=forecast.time_means[:171].cpu().numpy())
  raw_drivers=[]
  for p in sorted((ROOT/'data/raw/test_minimal_2023').glob('*.npz')):
   with np.load(p) as n:raw_drivers.append(dict(file=p.name,**{k:n[k].tolist() for k in ['f107d','f107a','Kp']}))
  elapsed=time.perf_counter()-tick;newbytes=sum(p.stat().st_size for folder in [F,D] for p in folder.rglob('*') if p.is_file());assert elapsed<300 and newbytes<500*2**20
  report.update(status='two_step_execution_passed_not_full_paper_reproduction',parameters=sum(p.numel() for p in forecast.model.parameters()),strict_author_checkpoint_loading=True,torch=torch.__version__,device=torch.cuda.get_device_name(),cuda=torch.version.cuda,FP32=True,TF32=False,model_load_s=load_s,data_read_preprocess_s=read_s,author_inference_plus_metrics_and_hooks_s=inference_s,network_GPU_ms=gpu_times,GPU_phase_wall_s=elapsed,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),new_result_bytes=newbytes,feedback=check,first_step_vs_historical_max_normalized_difference=historical_delta,historical_validation_not_new=True,raw_drivers=raw_drivers,known_future_conditions='target-hour LBC, solar elevation/eccentricity, magnetic coordinates and F107/Kp; no target physical state is fed',pressure_channels=dict(zip(['TN','UN','VN','WN','Z','DEN'],[28,28,28,29,29,29])),file_sha256=sha(D/'result.npz'),last_loaded_time=str(last))
  dump(F/'runtime.json',report);print(json.dumps(report,indent=2),flush=True)
 except Exception as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc(),wall_s=time.perf_counter()-tick);dump(F/'failure.json',report);raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');args=p.parse_args()
 if args.execute:execute()
 else:prepare()
