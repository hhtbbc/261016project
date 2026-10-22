"""Four official Mar24 continuous twelve-hour sequences; no training or resets."""
import sys,json,time,argparse,zipfile,zlib,gc,traceback,shutil,resource
from pathlib import Path
from datetime import datetime,timedelta
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'third_party/FourCastDEN_linux'))
from run_fourcastden_multistep import sha,dump
from run_fourcastden_four_model_multidate import verify as verify_previous
from run_fourcastden_history_comparison import CHECKPOINTS
from fourcastden.multidate import BoundedRemoteZip,validate_npz
from fourcastden.logden import decode_physical,load_overlay,MetricTrace
from fourcastden.autoregression import check_autoregression
from fourcastden.profiling import DatasetTimer,MetricTimer
F=ROOT/'experiments/fourcastden_twelve_hour_mar24_v1';D=ROOT/'data/processed/fourcastden_twelve_hour_mar24_v1';RAW=ROOT/'data/raw/fourcastden_twelve_hour_mar24_v1';DATES=('2023-03-24',);MODELS=('Direct','Flow','LogDEN','History');PREVIOUS=ROOT/'experiments/fourcastden_four_model_multidate_v1'

def fetch():
 from run_fourcastden_six_hour import verify as verify_six
 verify_six();
 from run_fourcastden_twelve_hour_jan4 import verify as verify_jan
 verify_jan();F.mkdir(exist_ok=False);RAW.mkdir(exist_ok=False)
 names=[f'2023_03_24_{h:02d}0000.npz' for h in range(8,14)]
 inventory={x['name']:x for x in json.loads((ROOT/'logs/test_archive_inventory.json').read_text())}
 assert all(n in inventory for n in names)
 total=sum(inventory[n]['compressed'] for n in names);assert total+2*2**20<25*2**20
 protected=json.loads((ROOT/'experiments/fourcastden_six_hour_v1/protected.json').read_text())
 for folder in [ROOT/'experiments/fourcastden_six_hour_v1',ROOT/'data/processed/fourcastden_six_hour_v1',ROOT/'data/raw/fourcastden_six_hour_v1',ROOT/'experiments/fourcastden_twelve_hour_jan4_v1',ROOT/'data/processed/fourcastden_twelve_hour_jan4_v1',ROOT/'data/raw/fourcastden_twelve_hour_jan4_v1']:
  for p in folder.rglob('*'):
   if p.is_file() and not p.is_symlink():protected[str(p.relative_to(ROOT))]=sha(p)
 for folder,pattern in [('reports','FOURCASTDEN_SIX_HOUR*'),('reports','FOURCASTDEN_GEOMAGNETIC_WINDOW*'),('results/metrics','fourcastden_six_hour_v1*'),('results/figures','fourcastden_six_hour_v1*'),('scripts','*fourcastden_six_hour*.py')]:
  for p in (ROOT/folder).glob(pattern):
   if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 for folder,pattern in [('reports','FOURCASTDEN_TWELVE_HOUR_JAN4*'),('results/metrics','fourcastden_twelve_hour_jan4_v1*'),('results/figures','fourcastden_twelve_hour_jan4_v1*'),('scripts','*fourcastden_twelve_hour_jan4*.py')]:
  for p in (ROOT/folder).glob(pattern):
   if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 for p,h in protected.items():assert sha(ROOT/p)==h,p
 dump(F/'protected.json',protected);dump(F/'fetch_once.json',dict(members=names,limit=25*2**20,compressed_sum=total))
 meta=json.loads((ROOT/'logs/zenodo_21859635_20261019.json').read_text())['files'][0];remote=BoundedRemoteZip(meta['links']['self'],meta['size'],limit=25*2**20);records=[]
 try:
  with zipfile.ZipFile(remote) as z:
   infos=[z.getinfo(n) for n in names]
   for i in infos:assert (i.file_size,i.compress_size,i.CRC)==(inventory[i.filename]['bytes'],inventory[i.filename]['compressed'],inventory[i.filename]['crc'])
   assert sum(i.compress_size for i in infos)+remote.reserved+2**20<25*2**20
   dump(F/'member_preflight.json',dict(members=[dict(name=i.filename,bytes=i.file_size,compressed=i.compress_size,CRC32=i.CRC,header_offset=i.header_offset) for i in infos]))
   for info in infos:
    body=z.read(info.filename);assert zlib.crc32(body)&0xffffffff==info.CRC;p=RAW/info.filename
    with p.open('xb') as f:f.write(body)
    stats=validate_npz(p);p.chmod(0o444);r=dict(name=p.name,sha256=sha(p),CRC32=info.CRC,stats=stats);records.append(r);dump(F/(p.stem+'_download.json'),r)
  dump(F/'download.json',dict(status='PASS',records=records))
 finally:dump(F/'ranges.json',dict(transfer_bytes=remote.total,reserved_bytes=remote.reserved,limit_bytes=remote.limit,requests=remote.requests,completed_members=[r['name'] for r in records]))
 print('Six members verified',remote.total,flush=True)

def prepare():
 from ruamel.yaml import YAML
 assert not (F/'preflight.json').exists() and not D.exists();assert json.loads((F/'download.json').read_text())['status']=='PASS'
 for p,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==h,p
 log=(ROOT/'logs/fourcastden_twelve_hour_mar24_tests.log').read_text();assert 'Ran 239 tests' in log and log.rstrip().endswith('OK');assert shutil.disk_usage(ROOT).free>20*2**30
 view=F/'data_view';view.mkdir();data=[]
 for day in DATES:
  for h in range(14):
   folder='data/raw/fourcastden_six_hour_v1' if h<8 else 'data/raw/fourcastden_twelve_hour_mar24_v1'
   p=(ROOT/folder/f"{day.replace('-','_')}_{h:02d}0000.npz").resolve();p.relative_to(ROOT);stats=validate_npz(p);(view/p.name).symlink_to(p);data.append(dict(source=str(p.relative_to(ROOT)),name=p.name,sha256=sha(p),stats=stats))
 yaml=YAML();yaml.width=240;configs={}
 for m in MODELS:
  cfg=yaml.load((PREVIOUS/f'{m}.yaml').read_text());cfg['afno_inference'].update(n_prediction=12,test_data_path=str(view),pre_resultname='twelve_hour_'+m)
  with (F/f'{m}.yaml').open('x') as f:yaml.dump(cfg,f)
  configs[m]=sha(F/f'{m}.yaml')
 prev=json.loads((PREVIOUS/'preflight.json').read_text())
 dump(F/'preflight.json',dict(status='PASS',dates=list(DATES),models=list(MODELS),t0_hour_UTC=1,target_hours_UTC=list(range(2,14)),data=data,config_sha256=configs,checkpoint_sha256=prev['checkpoint_sha256'],overlay_sha256=prev['overlay_sha256'],code_sha256={p:sha(ROOT/p) for p in ['scripts/run_fourcastden_twelve_hour_mar24.py','src/fourcastden/autoregression.py','src/fourcastden/profiling.py','tests/test_fourcastden_twelve_hour_mar24.py','docs/FOURCASTDEN_MAR24_TWELVE_HOUR_PREREGISTRATION.md']},tests=239,resource_forecast=dict(conservative_wall_s=240,result_bytes_upper=700*2**20,estimated_peak_RSS_GiB=2.),limits=dict(GPU_wall_s=600,RSS_bytes=4*2**30,new_bytes=800*2**20),free_disk_GiB=shutil.disk_usage(ROOT).free/2**30))
 print('Preflight PASS: 4 x 12 forwards; no additional GPU precheck')

def verify():
 pre=json.loads((F/'preflight.json').read_text());assert pre['status']=='PASS'
 for p,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==h,p
 for p,h in pre['code_sha256'].items():assert sha(ROOT/p)==h,p
 for m,h in pre['config_sha256'].items():assert sha(F/f'{m}.yaml')==h
 for e in pre['data']:assert sha(ROOT/e['source'])==e['sha256']
 assert sha(ROOT/'experiments/fourcastden_logden_multidate_v1/inference_overlay.py')==pre['overlay_sha256'];return pre

def execute():
 import torch
 from utils.YParams import YParams
 import inference.inference as ordinary
 pre=verify();D.mkdir(exist_ok=False);dump(F/'launch_once.json',dict(formal_sequences=4,formal_forwards=48,precheck_forwards=0,no_retry=True));tick=time.perf_counter();records=[];day=model=None;short_output=None
 try:
  torch.set_num_threads(4);assert torch.cuda.is_available();torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
  for model in MODELS:
   module=load_overlay(ROOT/'experiments/fourcastden_logden_multidate_v1/inference_overlay.py') if model=='LogDEN' else ordinary
   params=YParams(str(F/f'{model}.yaml'),'afno_inference');params['experiment_dir']=str(F);t=time.perf_counter();forecast=module.TGCMForecast(params);torch.cuda.synchronize();loading=time.perf_counter()-t;loadpeak=torch.cuda.max_memory_allocated();hist=int(model=='History')
   assert (params.n_in_channels,params.n_out_channels,params.n_history,params.n_prediction,params.n_in_indices)==(177,171,hist,12,4)
   for i,day in enumerate(DATES):
    ic=i*14+(0 if hist else 1);indices=list(range(ic,i*14+14));assert forecast.dataset.epochs[i*14:i*14+14]==[datetime.fromisoformat(day)+timedelta(hours=h) for h in range(14)]
    t=time.perf_counter()
    with DatasetTimer(forecast.dataset) as initial_io:data,sw,_,stds,means=forecast.dataset.get_data(indices,inference=True)
    read=time.perf_counter()-t
    for k,h in enumerate(range(0 if hist else 1,14)):
     with np.load(F/'data_view'/f"{day.replace('-','_')}_{h:02d}0000.npz") as z:
      raw=np.concatenate([z[v] for v in ['TN','UN','VN','WN','Z','DEN','TLBC','ULBC','VLBC']])
      if model=='LogDEN':raw[142:171]=np.log10(raw[142:171])
      np.testing.assert_array_equal(data[k,:174].numpy(),((raw-means)/stds).astype(np.float32))
    with np.load(ROOT/f'data/processed/fourcastden_six_hour_v1/{day}_{model}.npz') as oldfile:old={k:oldfile[k].copy() for k in ['pred','inputs','scalars','raw_network','means','stds']}
    np.testing.assert_array_equal(old['means'],means);np.testing.assert_array_equal(old['stds'],stds)
    dump(F/f'{day}_{model}_launch.json',dict(date=day,model=model,forwards=12));inputs=[];raw_outputs=[];gpu=[];events=[];step_physics=[];decode_times=[]
    def before(net,args):
     inputs.append(tuple(x.detach().cpu().numpy().copy() for x in args));a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True);events.append((a,b));a.record()
    def after(net,args,result):
     a,b=events[-1];b.record();b.synchronize();gpu.append(a.elapsed_time(b));out=result.detach().cpu().numpy().copy();raw_outputs.append(out)
     state=out+inputs[-1][0][:,:171] if model=='Flow' else out
     lead=len(raw_outputs)
     if lead<=6:
      np.testing.assert_array_equal(inputs[-1][0][0],old['inputs'][lead-1]);np.testing.assert_array_equal(inputs[-1][1][0],old['scalars'][lead-1]);np.testing.assert_array_equal(out[0],old['raw_network'][lead-1]);np.testing.assert_array_equal(state,old['pred'][0,lead:lead+1])
      if lead==6:dump(F/f'{day}_{model}_prefix_gate.json',dict(status='PASS',first_six_states_inputs_scalars_raw_exact=True,max_normalized_difference=0.))
     decode_start=time.perf_counter();ph=decode_physical(state,means[:171],stds[:171],model=='LogDEN');decode_times.append(time.perf_counter()-decode_start);assert (ph[:,:28]>0).all()
     step_physics.append(dict(lead_hour=len(raw_outputs),DEN_min_kg_m3=float(ph[:,142:].min()*1000),DEN_max_kg_m3=float(ph[:,142:].max()*1000),TN_min_K=float(ph[:,:28].min()),TN_max_K=float(ph[:,:28].max()),max_abs_wind_m_s=float(abs(ph[:,28:113]).max()*.01),Z_min_m=float(ph[:,113:142].min()*.01),Z_max_m=float(ph[:,113:142].max()*.01),nonfinite=0,DEN_nonpositive=0))
    h1=forecast.model.register_forward_pre_hook(before);h2=forecast.model.register_forward_hook(after);torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
    try:
     with DatasetTimer(forecast.dataset) as loop_io,MetricTimer(module) as metric_timer,MetricTrace(module) as trace:real,pred,rmse,acc,accu,last,_,_=forecast.inference(ic)
    except Exception:
     np.savez_compressed(D/f'{day}_{model}_failed_prefix.npz',**{f'raw_forward{k}':x for k,x in enumerate(raw_outputs)},**{f'input{k}':x[0] for k,x in enumerate(inputs)})
     dump(F/f'{day}_{model}_failed_prefix.json',dict(completed_network_forwards=len(raw_outputs),step_physics=step_physics));raise
    torch.cuda.synchronize();loop=time.perf_counter()-t;h1.remove();h2.remove();assert len(inputs)==12
    states=[pred[0,k+1:k+2] for k in range(12)];check=check_autoregression(inputs,states,data.numpy(),sw.numpy(),hist,raw_outputs,model=='Flow')

    physical=decode_physical(pred[0],means[:171],stds[:171],model=='LogDEN');assert (physical[:,:28]>0).all()
    output=D/f'{day}_{model}.npz';t=time.perf_counter();np.savez_compressed(output,pred=pred,means=means,stds=stds,climatology=forecast.time_means[:171].cpu().numpy(),author_rmse=rmse,author_acc=acc,author_acc_unweighted=accu,author_normalized_rmse=np.stack(trace.normalized_rmse),author_physical_den_pred=np.concatenate(trace.physical_pred,axis=0) if trace.physical_pred else np.empty(0),author_physical_den_target=np.concatenate(trace.physical_target,axis=0) if trace.physical_target else np.empty(0),inputs=np.concatenate([x[0] for x in inputs]),scalars=np.concatenate([x[1] for x in inputs]),raw_network=np.concatenate(raw_outputs),full_data=data.numpy(),full_sw=sw.numpy());save=time.perf_counter()-t
    r=dict(date=day,model=model,status='PASS',parameters=sum(p.numel() for p in forecast.model.parameters()),checkpoint_sha256=pre['checkpoint_sha256'][model],config_sha256=pre['config_sha256'][model],n_history=hist,formal_forwards=12,input_shape=list(inputs[0][0].shape),output_shape=list(states[0].shape),prediction_shape=list(pred.shape),model_load_s=loading if i==0 else 0.,model_reused=i>0,loading_peak_allocated_bytes=loadpeak,read_preprocess_s=read,read_decode_s=initial_io.read_decode_s,normalization_s=initial_io.normalization_s,preprocess_excluding_read_s=read-initial_io.read_decode_s,loop_read_decode_s=loop_io.read_decode_s,loop_normalization_s=loop_io.normalization_s,native_metric_timing=metric_timer.records,native_metrics_GPU_ms=sum(x['GPU_ms'] for x in metric_timer.records),native_metrics_call_wall_s=sum(x['call_wall_s'] for x in metric_timer.records),author_loop_metrics_hooks_s=loop,save_s=save,GPU_forward_ms=gpu,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,feedback=check,result_sha256=sha(output),result_bytes=output.stat().st_size,step_physics=step_physics,physical_decode_hook_s=sum(decode_times))
    dump(F/f'{day}_{model}_runtime.json',r);records.append(r);print(json.dumps(dict(date=day,model=model,status='PASS',forward_ms=gpu)),flush=True)
    del data,sw,real,pred,physical,inputs,raw_outputs,states,trace;gc.collect()
   del forecast;gc.collect();torch.cuda.empty_cache()
  dump(F/'runtime.json',dict(status='PASS',labels=['HINDCAST','TIEGCM_REFERENCE_ONLY','NO_TRAINING'],formal_sequences=4,formal_forwards=48,precheck_forwards=0,GPU_phase_wall_s=time.perf_counter()-tick,records=records,torch=torch.__version__,cuda=torch.version.cuda,device=torch.cuda.get_device_name(),FP32=True,TF32=False))
 except Exception as e:dump(F/'failure.json',dict(date=day,model=model,error=str(e),traceback=traceback.format_exc(),completed_sequences=[r['date']+'_'+r['model'] for r in records],no_retry=True));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fetch',action='store_true');p.add_argument('--execute',action='store_true');a=p.parse_args();fetch() if a.fetch else execute() if a.execute else prepare()
