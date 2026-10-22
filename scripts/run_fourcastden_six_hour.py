"""Two frozen six-hour official-model sequences; no training or state resets."""
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
F=ROOT/'experiments/fourcastden_six_hour_v1';D=ROOT/'data/processed/fourcastden_six_hour_v1';RAW=ROOT/'data/raw/fourcastden_six_hour_v1';DATES=('2023-01-04','2023-03-24');MODELS=('Direct','Flow','LogDEN','History');PREVIOUS=ROOT/'experiments/fourcastden_four_model_multidate_v1'

def fetch():
 verify_previous();F.mkdir(exist_ok=False);RAW.mkdir(exist_ok=False)
 names=[d.replace('-','_')+f'_{h:02d}0000.npz' for d in DATES for h in range(4 if d==DATES[0] else 0,8)]
 inventory={x['name']:x for x in json.loads((ROOT/'logs/test_archive_inventory.json').read_text())};assert len(names)==12 and all(n in inventory for n in names);assert sum(inventory[n]['compressed'] for n in names)+2*2**20<40*2**20
 dump(F/'fetch_once.json',dict(members=names,limit=40*2**20,saved_directory_compressed_sum=sum(inventory[n]['compressed'] for n in names)))
 protected=json.loads((PREVIOUS/'protected.json').read_text())
 for folder in [PREVIOUS,ROOT/'data/processed/fourcastden_four_model_multidate_v1',ROOT/'data/raw/fourcastden_four_model_multidate_v1']:
  for p in folder.rglob('*'):
   if p.is_file() and not p.is_symlink():protected[str(p.relative_to(ROOT))]=sha(p)
 for folder,pattern in [('results/metrics','fourcastden_four_model_multidate_v1*'),('results/figures','fourcastden_four_model_multidate_v1*'),('logs','fourcastden_four_model*'),('reports','FOURCASTDEN_FOUR_MODEL_MULTIDATE*')]:
  for p in (ROOT/folder).glob(pattern):
   if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 for name in ['scripts/run_fourcastden_four_model_multidate.py','scripts/analyze_fourcastden_four_model_multidate.py','src/fourcastden/four_model_windows.py']:protected[name]=sha(ROOT/name)
 for p,h in protected.items():assert sha(ROOT/p)==h,p
 dump(F/'protected.json',protected)
 meta=json.loads((ROOT/'logs/zenodo_21859635_20261019.json').read_text())['files'][0];remote=BoundedRemoteZip(meta['links']['self'],meta['size'],limit=40*2**20);records=[]
 try:
  with zipfile.ZipFile(remote) as z:
   infos=[z.getinfo(n) for n in names]
   for i in infos:assert (i.file_size,i.compress_size,i.CRC)==(inventory[i.filename]['bytes'],inventory[i.filename]['compressed'],inventory[i.filename]['crc'])
   assert sum(i.compress_size for i in infos)+remote.reserved+2**20<40*2**20
   dump(F/'member_preflight.json',dict(all_twelve_present=True,archive_members=len(z.infolist()),members=[dict(name=i.filename,bytes=i.file_size,compressed_bytes=i.compress_size,CRC32=i.CRC,header_offset=i.header_offset) for i in infos]))
   for info in infos:
    b=z.read(info.filename);assert zlib.crc32(b)&0xffffffff==info.CRC;p=RAW/info.filename
    with p.open('xb') as f:f.write(b)
    stats=validate_npz(p);p.chmod(0o444);r=dict(name=info.filename,bytes=len(b),CRC32=info.CRC,CRC32_verified=True,sha256=sha(p),stats=stats);records.append(r);dump(F/(p.stem+'_download.json'),r)
  dump(F/'download.json',dict(status='PASS',source=meta['links']['self'],archive_bytes=meta['size'],records=records))
 finally:dump(F/'ranges.json',dict(transfer_bytes=remote.total,reserved_bytes=remote.reserved,limit_bytes=remote.limit,requests=remote.requests,completed_members=[r['name'] for r in records]))
 print('Twelve new members verified; body bytes',remote.total)

def resume_fetch():
 assert not (F/'download.json').exists();previous=json.loads((F/'ranges.json').read_text());dump(F/'resume_fetch_once.json',dict(reason='one bounded retry of remaining files after HTTP500; no CRC/Range failure bypass',previous_body_bytes=previous['transfer_bytes'],previous_reserved_bytes=previous['reserved_bytes']))
 records=[]
 for name in previous['completed_members']:
  r=json.loads((F/(Path(name).stem+'_download.json')).read_text());assert sha(RAW/name)==r['sha256'];validate_npz(RAW/name);records.append(r)
 pre=json.loads((F/'member_preflight.json').read_text());pending=[x['name'] for x in pre['members'] if x['name'] not in previous['completed_members']];meta=json.loads((ROOT/'logs/zenodo_21859635_20261019.json').read_text())['files'][0];remaining=40*2**20-previous['reserved_bytes'];remote=BoundedRemoteZip(meta['links']['self'],meta['size'],limit=remaining)
 try:
  with zipfile.ZipFile(remote) as z:
   infos=[z.getinfo(name) for name in pending];assert sum(x.compress_size for x in infos)+remote.reserved+2**20<remaining
   for info in infos:
    b=z.read(info.filename);assert zlib.crc32(b)&0xffffffff==info.CRC;p=RAW/info.filename
    with p.open('xb') as f:f.write(b)
    stats=validate_npz(p);p.chmod(0o444);r=dict(name=info.filename,bytes=len(b),CRC32=info.CRC,CRC32_verified=True,sha256=sha(p),stats=stats);records.append(r);dump(F/(p.stem+'_download.json'),r)
  assert len(records)==12
  dump(F/'download.json',dict(status='PASS',source=meta['links']['self'],archive_bytes=meta['size'],records=records,network_body_bytes=previous['transfer_bytes']+remote.total,network_reserved_bytes=previous['reserved_bytes']+remote.reserved,HTTP500_in_first_attempt=True,bounded_resume_of_remaining_only=True))
 finally:dump(F/'ranges_resume.json',dict(transfer_bytes=remote.total,reserved_bytes=remote.reserved,limit_bytes=remote.limit,requests=remote.requests,completed_members=[r['name'] for r in records],cumulative_body_bytes=previous['transfer_bytes']+remote.total,cumulative_reserved_bytes=previous['reserved_bytes']+remote.reserved))
 print('All 12 members verified; cumulative body bytes',previous['transfer_bytes']+remote.total)

def prepare():
 from ruamel.yaml import YAML
 assert not (F/'preflight.json').exists() and not D.exists();assert json.loads((F/'download.json').read_text())['status']=='PASS'
 for p,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==h,p
 log=(ROOT/'logs/fourcastden_six_hour_tests.log').read_text();assert 'Ran 232 tests' in log and log.rstrip().endswith('OK');assert shutil.disk_usage(ROOT).free>20*2**30
 view=F/'data_view';view.mkdir();data=[]
 for day in DATES:
  for h in range(8):
   folder='data/raw/test_minimal_2023' if day==DATES[0] and h<3 else 'data/raw/fourcastden_history_comparison_v1' if day==DATES[0] and h==3 else 'data/raw/fourcastden_six_hour_v1'
   p=(ROOT/folder/f"{day.replace('-','_')}_{h:02d}0000.npz").resolve();p.relative_to(ROOT);stats=validate_npz(p);(view/p.name).symlink_to(p);data.append(dict(source=str(p.relative_to(ROOT)),name=p.name,sha256=sha(p),stats=stats))
 yaml=YAML();yaml.width=240;configs={}
 for m in MODELS:
  cfg=yaml.load((PREVIOUS/f'{m}.yaml').read_text());cfg['afno_inference'].update(n_prediction=6,test_data_path=str(view),pre_resultname='six_hour_'+m)
  with (F/f'{m}.yaml').open('x') as f:yaml.dump(cfg,f)
  configs[m]=sha(F/f'{m}.yaml')
 prev=json.loads((PREVIOUS/'preflight.json').read_text())
 dump(F/'preflight.json',dict(status='PASS',dates=list(DATES),models=list(MODELS),t0_hour_UTC=1,target_hours_UTC=list(range(2,8)),data=data,config_sha256=configs,checkpoint_sha256=prev['checkpoint_sha256'],overlay_sha256=prev['overlay_sha256'],code_sha256={p:sha(ROOT/p) for p in ['scripts/run_fourcastden_six_hour.py','src/fourcastden/autoregression.py','src/fourcastden/profiling.py','tests/test_fourcastden_six_hour.py','docs/FOURCASTDEN_SIX_HOUR_PREREGISTRATION.md']},tests=232,resource_forecast=dict(conservative_wall_s=240,result_bytes_upper=700*2**20,estimated_peak_RSS_GiB=2.),limits=dict(GPU_wall_s=600,RSS_bytes=4*2**30,new_bytes=800*2**20),free_disk_GiB=shutil.disk_usage(ROOT).free/2**30))
 print('Preflight PASS: 8 x 6 forwards, plus one Direct single-forward short check')

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
 pre=verify();D.mkdir(exist_ok=False);dump(F/'launch_once.json',dict(formal_sequences=8,formal_forwards=48,precheck_forwards=1,no_retry=True));tick=time.perf_counter();records=[];day=model=None;short_output=None
 try:
  torch.set_num_threads(4);assert torch.cuda.is_available();torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
  for model in MODELS:
   module=load_overlay(ROOT/'experiments/fourcastden_logden_multidate_v1/inference_overlay.py') if model=='LogDEN' else ordinary
   params=YParams(str(F/f'{model}.yaml'),'afno_inference');params['experiment_dir']=str(F);t=time.perf_counter();forecast=module.TGCMForecast(params);torch.cuda.synchronize();loading=time.perf_counter()-t;loadpeak=torch.cuda.max_memory_allocated();hist=int(model=='History')
   assert (params.n_in_channels,params.n_out_channels,params.n_history,params.n_prediction,params.n_in_indices)==(177,171,hist,6,4)
   for i,day in enumerate(DATES):
    ic=i*8+(0 if hist else 1);indices=list(range(ic,i*8+8));assert forecast.dataset.epochs[i*8:i*8+8]==[datetime.fromisoformat(day)+timedelta(hours=h) for h in range(8)]
    t=time.perf_counter()
    with DatasetTimer(forecast.dataset) as initial_io:data,sw,_,stds,means=forecast.dataset.get_data(indices,inference=True)
    read=time.perf_counter()-t
    for k,h in enumerate(range(0 if hist else 1,8)):
     with np.load(F/'data_view'/f"{day.replace('-','_')}_{h:02d}0000.npz") as z:
      raw=np.concatenate([z[v] for v in ['TN','UN','VN','WN','Z','DEN','TLBC','ULBC','VLBC']])
      if model=='LogDEN':raw[142:171]=np.log10(raw[142:171])
      np.testing.assert_array_equal(data[k,:174].numpy(),((raw-means)/stds).astype(np.float32))
    if model=='Direct' and i==0:
     dump(F/'short_check_launch.json',dict(model='Direct',date=day,forwards=1))
     x=torch.cat([data[0,:171],data[1,171:]],dim=0)[None].to('cuda');s=sw[1].reshape(1,1,4).to('cuda');a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True);a.record()
     with torch.no_grad():o=forecast.forecast(x,s)
     b.record();b.synchronize();short_output=o.cpu().numpy().copy();ph=decode_physical(short_output,means[:171],stds[:171]);assert (ph[:,:28]>0).all();dump(F/'short_check.json',dict(status='PASS',GPU_ms=a.elapsed_time(b),shape=list(short_output.shape),finite=True,DEN_positive=True));del x,s,o,ph
    dump(F/f'{day}_{model}_launch.json',dict(date=day,model=model,forwards=6));inputs=[];raw_outputs=[];gpu=[];events=[];step_physics=[]
    def before(net,args):
     inputs.append(tuple(x.detach().cpu().numpy().copy() for x in args));a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True);events.append((a,b));a.record()
    def after(net,args,result):
     a,b=events[-1];b.record();b.synchronize();gpu.append(a.elapsed_time(b));out=result.detach().cpu().numpy().copy();raw_outputs.append(out)
     state=out+inputs[-1][0][:,:171] if model=='Flow' else out
     ph=decode_physical(state,means[:171],stds[:171],model=='LogDEN');assert (ph[:,:28]>0).all()
     step_physics.append(dict(lead_hour=len(raw_outputs),DEN_min_kg_m3=float(ph[:,142:].min()*1000),DEN_max_kg_m3=float(ph[:,142:].max()*1000),TN_min_K=float(ph[:,:28].min()),TN_max_K=float(ph[:,:28].max()),max_abs_wind_m_s=float(abs(ph[:,28:113]).max()*.01),Z_min_m=float(ph[:,113:142].min()*.01),Z_max_m=float(ph[:,113:142].max()*.01),nonfinite=0,DEN_nonpositive=0))
    h1=forecast.model.register_forward_pre_hook(before);h2=forecast.model.register_forward_hook(after);torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
    try:
     with DatasetTimer(forecast.dataset) as loop_io,MetricTimer(module) as metric_timer,MetricTrace(module) as trace:real,pred,rmse,acc,accu,last,_,_=forecast.inference(ic)
    except Exception:
     np.savez_compressed(D/f'{day}_{model}_failed_prefix.npz',**{f'raw_forward{k}':x for k,x in enumerate(raw_outputs)},**{f'input{k}':x[0] for k,x in enumerate(inputs)})
     dump(F/f'{day}_{model}_failed_prefix.json',dict(completed_network_forwards=len(raw_outputs),step_physics=step_physics));raise
    torch.cuda.synchronize();loop=time.perf_counter()-t;h1.remove();h2.remove();assert len(inputs)==6
    states=[pred[0,k+1:k+2] for k in range(6)];check=check_autoregression(inputs,states,data.numpy(),sw.numpy(),hist,raw_outputs,model=='Flow')
    if short_output is not None and model=='Direct' and i==0:np.testing.assert_array_equal(short_output,states[0])
    physical=decode_physical(pred[0],means[:171],stds[:171],model=='LogDEN');assert (physical[:,:28]>0).all()
    output=D/f'{day}_{model}.npz';t=time.perf_counter();np.savez_compressed(output,pred=pred,means=means,stds=stds,climatology=forecast.time_means[:171].cpu().numpy(),author_rmse=rmse,author_acc=acc,author_acc_unweighted=accu,author_normalized_rmse=np.stack(trace.normalized_rmse),author_physical_den_pred=np.concatenate(trace.physical_pred,axis=0) if trace.physical_pred else np.empty(0),author_physical_den_target=np.concatenate(trace.physical_target,axis=0) if trace.physical_target else np.empty(0),inputs=np.concatenate([x[0] for x in inputs]),scalars=np.concatenate([x[1] for x in inputs]),raw_network=np.concatenate(raw_outputs),full_data=data.numpy(),full_sw=sw.numpy());save=time.perf_counter()-t
    r=dict(date=day,model=model,status='PASS',parameters=sum(p.numel() for p in forecast.model.parameters()),checkpoint_sha256=pre['checkpoint_sha256'][model],config_sha256=pre['config_sha256'][model],n_history=hist,formal_forwards=6,input_shape=list(inputs[0][0].shape),output_shape=list(states[0].shape),prediction_shape=list(pred.shape),model_load_s=loading if i==0 else 0.,model_reused=i>0,loading_peak_allocated_bytes=loadpeak,read_preprocess_s=read,read_decode_s=initial_io.read_decode_s,normalization_s=initial_io.normalization_s,preprocess_excluding_read_s=read-initial_io.read_decode_s,loop_read_decode_s=loop_io.read_decode_s,loop_normalization_s=loop_io.normalization_s,native_metric_timing=metric_timer.records,native_metrics_GPU_ms=sum(x['GPU_ms'] for x in metric_timer.records),native_metrics_call_wall_s=sum(x['call_wall_s'] for x in metric_timer.records),author_loop_metrics_hooks_s=loop,save_s=save,GPU_forward_ms=gpu,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,feedback=check,result_sha256=sha(output),result_bytes=output.stat().st_size,step_physics=step_physics)
    dump(F/f'{day}_{model}_runtime.json',r);records.append(r);print(json.dumps(dict(date=day,model=model,status='PASS',forward_ms=gpu)),flush=True)
    del data,sw,real,pred,physical,inputs,raw_outputs,states,trace;gc.collect()
   del forecast;gc.collect();torch.cuda.empty_cache()
  dump(F/'runtime.json',dict(status='PASS',labels=['HINDCAST','TIEGCM_REFERENCE_ONLY','NO_TRAINING'],formal_sequences=8,formal_forwards=48,precheck_forwards=1,GPU_phase_wall_s=time.perf_counter()-tick,records=records,torch=torch.__version__,cuda=torch.version.cuda,device=torch.cuda.get_device_name(),FP32=True,TF32=False))
 except Exception as e:dump(F/'failure.json',dict(date=day,model=model,error=str(e),traceback=traceback.format_exc(),completed_sequences=[r['date']+'_'+r['model'] for r in records],no_retry=True));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fetch',action='store_true');p.add_argument('--resume-fetch',action='store_true');p.add_argument('--execute',action='store_true');a=p.parse_args();fetch() if a.fetch else resume_fetch() if a.resume_fetch else execute() if a.execute else prepare()
