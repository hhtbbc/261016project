"""Frozen four-window official Direct/Flow experiment; no January replays."""
import sys,json,time,shutil,zipfile,traceback,argparse,gc,resource
from pathlib import Path
from datetime import datetime,timedelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'third_party/FourCastDEN_linux'))
from run_fourcastden_multistep import sha,dump
from fourcastden.multidate import DATES,KEYS,names_for,validate_npz,BoundedRemoteZip
F=ROOT/'experiments/fourcastden_multidate_v1';RAW=ROOT/'data/raw/fourcastden_multidate_v1';D=ROOT/'data/processed/fourcastden_multidate_v1'
def verify_protected():
 for p,h in json.loads((F/'protected.json').read_text()).items():assert (ROOT/p).resolve().is_relative_to(ROOT) and sha(ROOT/p)==h,p
 pre=json.loads((F/'preflight.json').read_text())
 for p,h in pre['code_sha256'].items():assert sha(ROOT/p)==h,p
 for model in ['Direct','Flow']:assert sha(F/f'{model}.yaml')==pre['config_sha256'][model]
def prepare():
 from ruamel.yaml import YAML
 for p in [F,RAW,D]:p.resolve().relative_to(ROOT);assert not p.exists(),p
 log=(ROOT/'logs/fourcastden_multidate_tests.log').read_text();assert 'Ran 206 tests' in log and log.rstrip().endswith('OK')
 protected=json.loads((ROOT/'experiments/fourcastden_flow_two_step_v1/protected.json').read_text())
 for folder in ['experiments/fourcastden_flow_two_step_v1','data/processed/fourcastden_flow_two_step_v1']:
  for p in (ROOT/folder).rglob('*'):
   if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 for sub,pattern in [('logs','fourcastden_flow*'),('results/metrics','fourcastden_direct_flow_v1*'),('results/figures','fourcastden_direct_flow_v1*')]:
  for p in (ROOT/sub).glob(pattern):
   if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 for p,h in protected.items():assert (ROOT/p).resolve().is_relative_to(ROOT) and sha(ROOT/p)==h,p
 inv={e['name']:e for e in json.loads((ROOT/'logs/test_archive_inventory.json').read_text())};names=[n for day in DATES for n in names_for(day)];assert all(n in inv for n in names)
 assert shutil.disk_usage(ROOT).free>20*2**30
 F.mkdir();dump(F/'protected.json',protected)
 yaml=YAML();cfg=yaml.load((ROOT/'experiments/fourcastden_flow_two_step_v1/config.yaml').read_text())
 for model in ['Direct','Flow']:
  cfg['afno_inference'].update(best_checkpoint_path=str(ROOT/f'models/checkpoints/author/{model}_ckpt.tar'),test_data_path=str(RAW),pre_resultname=f'multidate_{model}',flow=model=='Flow')
  with (F/f'{model}.yaml').open('x') as f:yaml.dump(cfg,f)
 dump(F/'selection.json',dict(dates=list(DATES),members=[inv[n] for n in names],planned_member_bytes=sum(inv[n]['bytes'] for n in names),selected_before_new_errors=True,January_replay=False))
 code=['scripts/run_fourcastden_multidate.py','src/fourcastden/multidate.py','tests/test_fourcastden_multidate.py','docs/FOURCASTDEN_MULTIDATE_PREREGISTRATION.md','src/fourcastden/validation.py','src/fourcastden/flow_validation.py']
 dump(F/'preflight.json',dict(passed=True,tests=206,config_sha256={m:sha(F/f'{m}.yaml') for m in ['Direct','Flow']},code_sha256={p:sha(ROOT/p) for p in code},free_disk_GiB=shutil.disk_usage(ROOT).free/2**30,budgets=dict(transfer_bytes=100*2**20,new_bytes=250*2**20,GPU_wall_s=600,RSS_bytes=4*2**30)))
 print('Static selection/assets/test gate PASS: 12 selected members; no new GPU inference.')
def fetch():
 verify_protected();assert not (F/'download.json').exists() and not RAW.exists()
 meta=json.loads((ROOT/'logs/zenodo_21859635_20261019.json').read_text());entry=next(e for e in meta['files'] if e['key']=='2023.zip')
 remote=BoundedRemoteZip(entry['links']['self'],entry['size']);audit=dict(status='running',url=entry['links']['self'],archive_bytes=entry['size'],saved=[],coordinate_contract='36x72 lat/lon from immutable author static, native lev/ilev; NPZ has no coordinate/unit attributes')
 RAW.mkdir();tick=time.perf_counter()
 try:
  selection=json.loads((F/'selection.json').read_text());old={e['name']:e for e in selection['members']}
  with zipfile.ZipFile(remote) as z:
   infos=[]
   for day in DATES:
    for name in names_for(day):
     info=z.getinfo(name);expected=old[name]
     assert (info.file_size,info.compress_size,info.CRC,info.compress_type)==(expected['bytes'],expected['compressed'],expected['crc'],expected['method'])
     assert 0<=info.header_offset<entry['size'] and info.file_size<8_000_000
     infos.append(info)
   for info in infos:
    b=z.read(info.filename);p=RAW/info.filename
    with p.open('xb') as f:f.write(b)
    stats=validate_npz(p);p.chmod(0o444)
    audit['saved'].append(dict(name=info.filename,bytes=len(b),sha256=sha(p),CRC32_verified=True,CRC32=info.CRC,header_offset=info.header_offset,compressed_bytes=info.compress_size,variable_checks=stats))
  assert len(audit['saved'])==12;audit['status']='PASS'
 except Exception as e:audit.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
 finally:
  audit.update(transfer_body_bytes=remote.total,conservative_reserved_bytes=remote.reserved,requests=remote.requests,wall_s=time.perf_counter()-tick)
  dump(F/'download.json',audit);print(json.dumps(dict(status=audit['status'],saved=len(audit['saved']),transfer_bytes=remote.total,wall_s=audit['wall_s']),indent=2),flush=True)
def execute():
 import numpy as np,torch
 from utils.YParams import YParams
 from inference.inference import TGCMForecast
 from fourcastden.validation import feedback_check
 from fourcastden.flow_validation import flow_feedback_check
 verify_protected();download=json.loads((F/'download.json').read_text());assert download['status']=='PASS'
 for e in download['saved']:assert sha(RAW/e['name'])==e['sha256']
 D.mkdir(exist_ok=False);dump(F/'launch_once.json',dict(sequences=8,forwards=16,January_new_sequences=0,no_training=True));tick=time.perf_counter();records=[]
 try:
  assert torch.cuda.is_available();torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
  for model in ['Direct','Flow']:
   params=YParams(str(F/f'{model}.yaml'),'afno_inference');params['experiment_dir']=str(F)
   t=time.perf_counter();forecast=TGCMForecast(params);torch.cuda.synchronize();load_s=time.perf_counter()-t;loadpeak=torch.cuda.max_memory_allocated()
   assert (params.n_in_channels,params.n_out_channels,params.n_in_indices,params.n_history,params.n_prediction)==(177,171,4,0,2)
   assert forecast.flow==(model=='Flow') and not forecast.log_DEN
   for idx,day in enumerate(DATES):
    tag=f'{day}_{model}';out=D/f'{tag}.npz';dump(F/f'{tag}_launch.json',dict(date=day,model=model,sequence=idx+1))
    ic=idx*3;epochs=forecast.dataset.epochs[ic:ic+3];expected=[datetime.fromisoformat(day)+timedelta(hours=h) for h in range(3)];assert list(epochs)==expected
    t=time.perf_counter();data,sw,_,stds,means=forecast.dataset.get_data([ic,ic+1,ic+2],inference=True);read_s=time.perf_counter()-t
    inputs=[];outputs=[];events=[];gpu=[]
    def before(module,args):
     inputs.append(tuple(x.detach().cpu().numpy().copy() for x in args));a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True);events.append((a,b));a.record()
    def after(module,args,result):
     a,b=events[-1];b.record();b.synchronize();gpu.append(a.elapsed_time(b));outputs.append(result.detach().cpu().numpy().copy())
    h1=forecast.model.register_forward_pre_hook(before);h2=forecast.model.register_forward_hook(after);torch.cuda.reset_peak_memory_stats();t=time.perf_counter()
    real,pred,rmse,acc,accu,last,_,_=forecast.inference(ic);torch.cuda.synchronize();loop_s=time.perf_counter()-t;h1.remove();h2.remove()
    check=flow_feedback_check(inputs,outputs,real[0],pred[0],sw.numpy()) if model=='Flow' else feedback_check(inputs,outputs,real[0],sw.numpy())
    physical=pred[0].astype(float)*stds[:171].astype(float)+means[:171].astype(float)
    assert np.isfinite(physical).all() and (physical[:,142:]>0).all() and (physical[:,:28]>0).all(),'Nonphysical prediction; no clipping/retry'
    assert len(inputs)==2
    common=dict(real=real,pred=pred,author_rmse=rmse,author_acc=acc,author_acc_unweighted=accu,means=means,stds=stds,input0=inputs[0][0],input1=inputs[1][0],scalars0=inputs[0][1],scalars1=inputs[1][1],out0=outputs[0],out1=outputs[1],climatology=forecast.time_means[:171].cpu().numpy())
    if model=='Flow':
     with np.load(D/f'{day}_Direct.npz') as d:
      for k in ['real','means','stds','climatology']:np.testing.assert_array_equal(common[k],d[k])
      for k in range(2):np.testing.assert_array_equal(inputs[k][0][:,171:],d[f'input{k}'][:,171:]);np.testing.assert_array_equal(inputs[k][1],d[f'scalars{k}'])
    np.savez_compressed(out,**common)
    r=dict(tag=tag,date=day,model=model,status='PASS',checkpoint_sha256=sha(ROOT/f'models/checkpoints/author/{model}_ckpt.tar'),config_sha256=sha(F/f'{model}.yaml'),data_sha256={e['name']:e['sha256'] for e in download['saved'] if e['name'] in names_for(day)},feedback=check,network_calls=2,parameters=sum(p.numel() for p in forecast.model.parameters()),model_load_s=load_s if idx==0 else 0.,model_reused=idx>0,load_peak_allocated_bytes=loadpeak if idx==0 else None,read_preprocess_s=read_s,author_loop_metrics_hooks_s=loop_s,GPU_forward_ms=gpu,first_forward_cold_this_model=idx==0,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),DEN_positive_fraction=1.,max_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,result_sha256=sha(out),elapsed_GPU_phase_s=time.perf_counter()-tick)
    assert r['max_RSS_KiB']*1024<4*2**30 and r['elapsed_GPU_phase_s']<600
    dump(F/f'{tag}_runtime.json',r);records.append(r);print(json.dumps(dict(tag=tag,status='PASS',loop_s=loop_s,forward_ms=gpu)),flush=True)
    del common,data,sw,real,pred,physical,inputs,outputs,events
    assert sum(p.stat().st_size for folder in [F,D,RAW] for p in folder.rglob('*') if p.is_file())<250*2**20
   del forecast,params;gc.collect();torch.cuda.empty_cache()
  dump(F/'runtime.json',dict(status='PASS',labels=['HINDCAST','TIEGCM_REFERENCE_ONLY','NO_TRAINING'],formal_sequences=8,real_forwards=16,January_replayed=False,GPU_wall_s=time.perf_counter()-tick,max_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,records=records,torch=torch.__version__,cuda=torch.version.cuda,device=torch.cuda.get_device_name(),FP32=True,TF32=False))
 except Exception as e:dump(F/'failure.json',dict(error=str(e),traceback=traceback.format_exc(),completed_sequences=len(records),GPU_wall_s=time.perf_counter()-tick));raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fetch',action='store_true');p.add_argument('--execute',action='store_true');a=p.parse_args()
 if a.execute:execute()
 elif a.fetch:fetch()
 else:prepare()
