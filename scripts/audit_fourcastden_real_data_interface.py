"""CPU real 2023 diagnostic only: intercept official inference BEFORE model evaluation."""
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
import sys,json,time,types,hashlib
from pathlib import Path
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'third_party/FourCastDEN_linux'));sys.path.insert(0,str(ROOT/'scripts'))
from run_fourcastden_multistep import sha,dump
from training.pipeline import OfficialFrameSource,EpochPairs,AffineNormalizer
from training.readonly_interface import inspect_pair,array_hash
from fourcastden.multidate import validate_npz
F=ROOT/'experiments/fourcastden_real_interface_v2'
class InputCaptured(Exception):pass

def capture_official(dataset,means,stds,ic,override=None):
    from inference.inference import TGCMForecast
    f=object.__new__(TGCMForecast)
    for k,v in dict(dt=1,n_prediction=1,n_history=0,img_shape_x=36,img_shape_y=72,n_in_channels=177,n_out_channels=171,device=torch.device('cpu'),time_means=torch.zeros((174,36,72)),means=torch.as_tensor(means),stds=torch.as_tensor(stds),wgt=torch.ones(36),log_to_screen=False,perturb=False,dataset=override or dataset).items():setattr(f,k,v)
    captured={}
    def intercept(self,x,s):
        captured['x']=x.clone();captured['s']=s.clone();raise InputCaptured()
    f.forecast=types.MethodType(intercept,f)
    try:f.inference(ic)
    except InputCaptured:pass
    assert set(captured)=={'x','s'}
    return captured['x'],captured['s']

def main():
    from utils.YParams import YParams
    from dataset.dataset_tiegcm import TGCMDataset
    tick=time.perf_counter();F.mkdir(exist_ok=True);dump(F/'launch_once.json',dict(read_only=True,model_forwards=0,backward=0,optimizer_steps=0,CPU_only=True))
    prior=ROOT/'experiments/fourcastden_training_smoke_cublas_v2/delivery_audit.json';p=json.loads(prior.read_text());protected=json.loads((ROOT/'experiments/fourcastden_training_smoke_v1/protected.json').read_text())
    for name,h in p['artifact_SHA256'].items():
        if name not in ['STATUS.md','WORKLOG.md','AGENTS.md','.gitignore','docs/FOURCASTDEN_PHASE2_RESEARCH_PLAN.md']:protected[name]=h
    protected[str(prior.relative_to(ROOT))]=sha(prior)
    for name,h in protected.items():assert sha(ROOT/name)==h,name
    dump(F/'protected.json',protected)
    cfg=YParams(str(ROOT/'experiments/fourcastden_two_step_v1/config.yaml'),'afno_inference');cfg['device']='cpu';dataset=TGCMDataset(cfg,cfg.test_data_path,train=False)
    assert dataset.epochs==[datetime(2023,1,4,h) for h in range(3)]
    source=OfficialFrameSource(dataset);data,sw,_,stds,means=dataset.get_data([0,1,2],inference=True)
    normalizer=AffineNormalizer(means,stds);rawchecks=[];roundtrip=[];pairchecks=[];poison=[]
    epochs=[x.replace(tzinfo=timezone.utc) for x in dataset.epochs]
    def forbidden(*args,**kwargs):raise AssertionError('Training/model evaluation forbidden in this audit')
    with patch('torch.Tensor.backward',forbidden),patch('torch.autograd.backward',forbidden),patch('training.pipeline.DirectTrainer.__init__',forbidden),patch('torch.nn.Module.__call__',forbidden),torch.inference_mode():
        for h in range(3):
            path=ROOT/f'data/raw/test_minimal_2023/2023_01_04_{h:02d}0000.npz';stats=validate_npz(path)
            with np.load(path,allow_pickle=False) as z:
                raw=np.concatenate([z[n] for n in ['TN','UN','VN','WN','Z','DEN','TLBC','ULBC','VLBC']])
                encoded=normalizer.encode(raw);author_encoded=((raw-means)/stds).astype(np.float32);np.testing.assert_array_equal(author_encoded,data[h,:174].numpy())
                affine_difference=float(abs(encoded-author_encoded).max())
                restored=normalizer.decode(encoded);err=abs(restored-raw);bound=np.abs(stds)*np.maximum(np.abs(encoded),1)*np.finfo(np.float32).eps*2
                assert np.all(err<=bound+1e-25)
                # Independent scalar formulas from author _normalize, not refitted statistics.
                expected=np.array([(float(z['f107d'][0])-190)/110,(float(z['f107a'][0])-190)/110,(float(z['Kp'][0])-4.5)/4.5],np.float32)
                np.testing.assert_allclose(sw[h,:3].numpy(),expected,rtol=0,atol=2*np.finfo(np.float32).eps)
                rawchecks.append(dict(name=path.name,SHA256=sha(path),fields=stats,finite=True,positive_DEN=True,ZG_strictly_increasing=True,finite_sentinel_count=0))
                for name,start,n,si in [('TN',0,28,1),('UN',28,28,.01),('VN',56,28,.01),('WN',84,29,.01),('Z',113,29,.01),('DEN',142,29,1000),('TLBC',171,1,1),('ULBC',172,1,.01),('VLBC',173,1,.01)]:
                    sl=slice(start,start+n);roundtrip.append(dict(hour=h,variable=name,channels=n,official_float32_encoded_exact=True,auxiliary_float64_max_normalized_difference=float(abs(encoded[sl]-author_encoded[sl]).max()),max_native_roundtrip_abs=float(err[sl].max()),max_native_roundtrip_relative=float((err[sl]/np.maximum(abs(raw[sl]),1e-30)).max()),max_SI_roundtrip_abs=float(err[sl].max()*si),reference_SI_min=float(raw[sl].min()*si),reference_SI_max=float(raw[sl].max()*si),theoretical_float32_bound_pass=True))
        for i in range(2):
            x,s=capture_official(dataset,means,stds,i)
            record=inspect_pair(source,epochs[i],epochs[i+1],x,s,data[i+1:i+2,:171],current_split='2023_test',target_split='2023_test')
            pairchecks.append(record)
            # Poison only the target's 171 physical channels, preserve external conditions.
            class PoisonDataset:
                def get_data(self,indices,**kw):
                    q=list(dataset.get_data(indices,**kw));q[0]=q[0].clone()
                    for k,index in enumerate(indices):
                        if index==i+1:q[0][k,:171]=9.
                    return tuple(q)
            xp,sp=capture_official(dataset,means,stds,i,PoisonDataset());np.testing.assert_array_equal(x,xp);np.testing.assert_array_equal(s,sp)
            def poisoned_source(t):
                st,ax,sc=source(t)
                return (torch.full_like(st,9.) if t==epochs[i+1] else st),ax,sc
            rp=inspect_pair(poisoned_source,epochs[i],epochs[i+1],x,s,torch.full((1,171,36,72),9.),current_split='2023_test',target_split='2023_test')
            assert rp['input_SHA256']==record['input_SHA256'] and rp['target_SHA256']!=record['target_SHA256']
            poison.append(dict(current=record['current_UTC'],target=record['target_UTC'],official_input_unchanged=True,adapter_input_unchanged=True,target_changed=True))
        for split in ['train','validation']:
            try:EpochPairs(epochs,source,split)
            except ValueError:pass
            else:raise AssertionError('2023 training guard lost')
        # First true input of the historical official 00->01 experiment is a fixed external oracle.
        with np.load(ROOT/'data/processed/fourcastden_two_step_v1/result.npz') as old:
            x,s=capture_official(dataset,means,stds,0);np.testing.assert_array_equal(x,old['input0']);np.testing.assert_array_equal(s,old['scalars0'])
    stats={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'data/processed/static').rglob('*') if p.is_file()}
    result=dict(status='PASS',label='READ_ONLY_TEST_INTERFACE / NOT_TRAINING',samples=rawchecks,pairs=pairchecks,roundtrip=roundtrip,poison=poison,source_epoch_contract='Author naive datetime from UTC filename, explicitly registered as UTC; NPZ has no internal timezone/unit attributes',n_state=171,n_aux=6,n_input=177,n_scalar=4,ordinary_static_SHA256=stats,means_SHA256=array_hash(means),stds_SHA256=array_hash(stds),scalar_conditions_normalized_exact_to_author=True,historical_input0_exact=True,normalization_fitted=False,model_instantiated=False,model_forward_calls=0,backward_calls=0,optimizer_steps=0,CUDA_used=False,training_2023_rejected=True,padding_policy='No invalid values in selected official NPZ; validate rejects NaN/Inf/abs>1e30; never replace raw model top padding with zero',wall_s=time.perf_counter()-tick)
    dump(F/'interface_audit.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['samples','ordinary_static_SHA256','roundtrip']},indent=2))
if __name__=='__main__':main()
