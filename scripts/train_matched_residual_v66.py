"""One CPU training per arm, identical V65 inputs and sampling, diagnostic scores only."""
import csv
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from collections import Counter

import numpy as np
import torch

from run_validation_events_v66 import OUT, ROOT
from run_training_events_v65 import sha, require, load, write_once
from runtime.supervisor import Limits, supervise
from train_tiny_direct_v60 import TinyDirectCNN, vector
from run_native_density_baselines_v59 import table, read_csv, SHAPE

TRAIN=ROOT/'experiments/thermosphere_multi_event_training_dataset_v65'
ARRAYS=TRAIN/'data_local/training_arrays'
LOCAL=OUT/'data_local'
BASE='e08046480edcb9d5f5db531b73e584b074980a6e'
LEADS=(1,3,6)
ARMS=('P','LT')
LIMIT=2**32


def pinned(path):
    require(path.resolve()==path and path.read_bytes()==subprocess.check_output(
        ['git','show',f'{BASE}:{path.relative_to(ROOT)}'],cwd=ROOT),'Frozen V65 identity '+path.name)
    return path


def configure():
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    require(os.environ.get('CUDA_VISIBLE_DEVICES')=='','Require hidden CUDA devices')
    torch.random.default_generator.manual_seed(42)


def immutable_input():
    frozen=load(pinned(TRAIN/'training_arrays_SHA256.json'))
    for name,v in frozen.items():
        p=ARRAYS/name
        require(p.resolve()==p and p.stat().st_size==v['bytes'] and sha(p)==v['SHA256'],'Training array SHA '+name)
    samples=read_csv(pinned(TRAIN/'hourly_training_sample_manifest.csv'))
    counts=Counter(r['event_id'] for r in samples)
    expected={'quiet_20240329T00':39,'quiet_20211125T06':54,
              'disturbed_20250915T00':6,'disturbed_20210301T03':33}
    require(counts==expected and len({r['sample_id'] for r in samples})==132
            and {r['role'] for r in samples}=={'TRAIN'},'Training role or count')
    normalization=load(pinned(TRAIN/'train_normalization.json'))
    require(normalization['primary_unique_input_frames']['frames']==140,'Normalization scope')
    return samples,normalization,frozen


def learn(arm):
    configure()
    arm_path=LOCAL/arm
    require(arm_path.resolve()==arm_path and os.getcwd()==str(arm_path),'Arm scope')
    samples=read_csv(TRAIN/'hourly_training_sample_manifest.csv')
    cfg=load(OUT/'training_protocol.json')
    sequence=read_csv(OUT/'shared_sampling_sequence.csv')
    require(sha(OUT/'shared_sampling_sequence.csv')==cfg['sampling_SHA256'] and
            len(sequence)==200,'Sample sequence lock')
    model=TinyDirectCNN().to(device='cpu',dtype=torch.float32)
    initial=torch.load(LOCAL/'initial.pt',map_location='cpu',weights_only=True)
    model.load_state_dict(initial)
    init=vector(model).copy()
    require(init.size==1027,'Architecture count')
    optimizer=torch.optim.Adam(model.parameters(),lr=.001)
    field=np.load(ARRAYS/'log_density.npy',mmap_mode='r')
    index=np.load(ARRAYS/'sample_field_indices.npy',mmap_mode='r')
    true_res=np.load(ARRAYS/'log_residuals.npy',mmap_mode='r')
    quality=load(TRAIN/'data_quality_report.json')
    coords=quality['coordinates']
    norm=load(OUT/'normalization.json')['primary_unique_input_frames']
    mean=np.asarray(norm['mean'],dtype='f4').reshape(29,1,1,1)
    sd=np.asarray(norm['std'],dtype='f4').reshape(29,1,1,1)
    weights=torch.from_numpy(np.cos(np.deg2rad(coords['lat'])).astype('f4').reshape(1,1,36,1))
    denom=weights.sum()*29*72*3
    arm_i=ARMS.index(arm)

    def data(i):
        logs=field[index[i,:3]]
        shaped=logs.transpose(1,0,2,3)
        x=torch.from_numpy((shaped-mean)/sd)
        residual=torch.from_numpy(np.array(true_res[arm_i,i].transpose(1,0,2,3)))
        last=logs[2]
        back=np.stack([last if arm=='P' else np.roll(last,-3*(h+1),axis=-1) for h in LEADS])
        return x,residual,torch.from_numpy(back.transpose(1,0,2,3).copy())

    def objective(correction,target):
        return torch.sum(weights*(correction-target).abs())/denom

    def correction(net,x):
        return net(x,torch.zeros((29,3,36,72),dtype=torch.float32,device='cpu'))

    milestones=[]
    last_gradient=0.
    use=np.cos(np.deg2rad(coords['lat']))[None,None,:,None]
    moment_den=29*72*float(use.sum())*len(samples)

    @torch.inference_mode()
    def diagnostics(step):
        sums=np.zeros((3,6))
        valid=0
        losses=[]
        snapshot=np.lib.format.open_memmap(arm_path/'correction.npy',mode='w+',dtype='<f4',
                                            shape=(132,3,*SHAPE)) if step==200 else None
        for i in range(len(samples)):
            x,target,bg=data(i)
            delta=correction(model,x)
            logp=bg+delta
            if step==0:
                require(torch.equal(logp,bg),'Step 0 background is not exact')
            losses.append(float(objective(delta,target)))
            p=logp.numpy().transpose(1,0,2,3).astype('f8')
            t=field[index[i,3:]].astype('f8')
            diff=p-t
            c=delta.numpy().transpose(1,0,2,3).astype('f8')
            r=target.numpy().transpose(1,0,2,3).astype('f8')
            d=np.exp(p)
            valid+=int((np.isfinite(d)&(d>0)).sum())
            for j,a in enumerate((diff,np.expm1(diff),d-np.exp(t),c,r,abs(diff))):
                power=a if j==5 else a*a
                sums[:,j]+=(power*use).sum(axis=(1,2,3))
            if snapshot is not None:
                snapshot[i]=c
        if snapshot is not None:
            snapshot.flush()
        for h,xx in zip(LEADS,sums):
            log_rmse,rel,absolute,corr_rms,background_rms=np.sqrt(xx[:5]/moment_den)
            milestones.append(dict(arm=arm,step=step,horizon=h,TRAIN_DIAGNOSTIC=True,
                loss=float(np.mean(losses)),log_rmse=log_rmse,relative_rmse=rel,absolute_rmse=absolute,
                correction_RMS=corr_rms,true_background_residual_RMS=background_rms,
                ratio=corr_rms/background_rms,coverage=valid/(len(samples)*3*np.prod(SHAPE)),
                last_gradient_norm=last_gradient,weight_L2_delta=float(np.linalg.norm(vector(model)-init))))
        require(valid==len(samples)*3*np.prod(SHAPE),'Coverage invalid')

    start=time.monotonic()
    diagnostics(0)
    step_rows=[]
    for k,row in enumerate(sequence,1):
        i=int(row['window_index'])
        require(int(row['step'])==k and row['sample_id']==samples[i]['sample_id'],'Sequence row mismatch')
        st=time.monotonic()
        x,target,_=data(i)
        optimizer.zero_grad(set_to_none=True)
        loss=objective(correction(model,x),target)
        require(bool(torch.isfinite(loss)),'Nonfinite loss')
        loss.backward()
        last_gradient=float(torch.sqrt(sum((p.grad.detach()**2).sum() for p in model.parameters())))
        require(np.isfinite(last_gradient),'Nonfinite gradient')
        optimizer.step()
        step_rows.append(dict(arm=arm,step=k,event_id=row['event_id'],sample_id=row['sample_id'],
                              loss=float(loss.detach()),gradient_L2=last_gradient,update_s=time.monotonic()-st))
        if k in (50,100,150,200):
            diagnostics(k)
    checkpoint=arm_path/'checkpoint.pt'
    torch.save({'state_dict':model.state_dict(),'optimizer':optimizer.state_dict(),
                'torch_rng':torch.get_rng_state(),'steps':200,'arm':arm,
                'sequence_SHA256':cfg['sampling_SHA256']},checkpoint)
    packet=arm_path/'parameter_packet.bin'
    packet.write_bytes(np.concatenate([vector(model),np.asarray(norm['mean']+norm['std'])]).astype('<f8').tobytes())
    recovered=torch.load(checkpoint,map_location='cpu',weights_only=True)
    replica=TinyDirectCNN().to('cpu')
    replica.load_state_dict(recovered['state_dict'])
    reopened=torch.optim.Adam(replica.parameters(),lr=.001)
    reopened.load_state_dict(recovered['optimizer'])
    xx,_,_=data(0)
    with torch.inference_mode():
        require(torch.equal(correction(replica,xx),correction(model,xx)) and
                np.array_equal(vector(replica),vector(model)) and
                all(int(s['step'])==200 for s in reopened.state.values()) and len(reopened.state)==6,
                'Restoration or update count')
    require(not np.array_equal(init,vector(model)),'No weight updates')
    table(arm_path/'training_log.csv',step_rows)
    table(arm_path/'milestones.csv',milestones)
    for p in (checkpoint,packet,arm_path/'correction.npy'):
        p.chmod(0o400)
    write_once(arm_path/'training_receipt.json',dict(
        arm=arm,parameters=1027,initial_vector_SHA256=hashlib.sha256(init.tobytes()).hexdigest(),
        sequence_SHA256=cfg['sampling_SHA256'],updates=200,step0_exact_background=True,
        checkpoint_recovered=True,checkpoint_SHA256=sha(checkpoint),packet_SHA256=sha(packet),
        correction_SHA256=sha(arm_path/'correction.npy'),elapsed_s=time.monotonic()-start,
        update_time_s=sum(r['update_s'] for r in step_rows),max_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        exposure=dict(Counter(r['event_id'] for r in sequence)),device='cpu'))
    print('ARM_TRAINED',arm,flush=True)


def orchestrate():
    configure()
    require(OUT.resolve()==OUT and not LOCAL.exists(),'Training already reserved')
    # Serial after validation production. Training worker receives TRAIN files only by contract.
    require(len(load(OUT/'validation_run_receipts.json'))==2,'Validation production incomplete')
    samples,norm,hashes=immutable_input()
    LOCAL.mkdir(mode=0o700)
    model=TinyDirectCNN().to('cpu')
    state=model.state_dict()
    torch.save(state,LOCAL/'initial.pt')
    (LOCAL/'initial.pt').chmod(0o400)
    require(vector(model).size==1027,'Shared model size')
    rng=np.random.default_rng(42)
    event_order=list(dict.fromkeys(r['event_id'] for r in samples))
    members={name:[i for i,r in enumerate(samples) if r['event_id']==name] for name in event_order}
    sequence=[]
    for k in range(1,201):
        event=event_order[int(rng.integers(4))]
        i=int(rng.choice(members[event]))
        sequence.append(dict(step=k,event_id=event,window_index=i,sample_id=samples[i]['sample_id']))
    table(OUT/'shared_sampling_sequence.csv',sequence)
    seq=sha(OUT/'shared_sampling_sequence.csv')
    (OUT/'shared_sampling_sequence.csv').chmod(0o444)
    write_once(OUT/'normalization.json',norm)
    write_once(OUT/'model_initialization_receipt.json',dict(seed=42,parameters=1027,last_layer_zero=True,
               initial_checkpoint_SHA256=sha(LOCAL/'initial.pt'),
               initial_vector_SHA256=hashlib.sha256(vector(model).tobytes()).hexdigest(),
               sampler_final_state=rng.bit_generator.state))
    write_once(OUT/'training_protocol.json',dict(arms=ARMS,updates_per_arm=200,optimizer='Adam',lr=.001,
               loss='equally weighted lead and cosine latitude log residual MAE',batch_cutoffs=1,
               seed=42,dtype='float32',device='cpu',CPU_threads=4,deterministic=True,
               sampling_SHA256=seq, normalization_SHA256=sha(OUT/'normalization.json'),
               input_array_HASHES=hashes,validation_early_stopping=False,
               longitude='circular',latitude='reflect',architecture='V60 TinyDirectCNN 3→8→8→3',
               field_shape=SHAPE,LT_eastward_grid_offsets=[6,12,21]))
    receipts={}
    logs=[]
    milestones=[]
    for arm in ARMS:
        cwd=LOCAL/arm
        cwd.mkdir(mode=0o700)
        write_once(OUT/f'arm_{arm}_claim.json',dict(attempts=1,automatic_retry=False,sequence_SHA256=seq))
        status=supervise([sys.executable,'-B',str(ROOT/'scripts/train_matched_residual_v66.py'),arm],
                         cwd,Limits(595,LIMIT,20*2**30,2**30,2**29,sample_s=.2,term_grace_s=1),
                         env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='4',
                                  MKL_NUM_THREADS='4',OPENBLAS_NUM_THREADS='1'))
        require(status['qualification']=='PASS' and status['returncode']==0 and status['cleanup_verified'],
                'Training supervision failed; no retry')
        receipt=load(cwd/'training_receipt.json')
        receipt.update(supervised_wall_s=status['elapsed_s'],sampled_tree_RSS_bytes=status['peak_sampled_tree_rss_bytes'])
        receipts[arm]=receipt
        logs.extend(read_csv(cwd/'training_log.csv'))
        milestones.extend(read_csv(cwd/'milestones.csv'))
    table(OUT/'training_log.csv',logs)
    table(OUT/'training_milestones.csv',milestones)
    write_once(OUT/'checkpoint_manifest.json',receipts)


if __name__=='__main__':
    if len(sys.argv)==2 and sys.argv[1] in ARMS:
        learn(sys.argv[1])
    else:
        orchestrate()
