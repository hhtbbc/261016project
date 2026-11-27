"""V60 CPU only. Fit one frozen network on four 2021 cutoffs."""
from collections import defaultdict
import json
import os
import resource
import subprocess
import time

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

import run_native_density_baselines_v59 as v59
from build_non_target_horizon_index_v56 import ROOT, sha

OUT=ROOT/'experiments/thermosphere_tiny_direct_cpu_v60'
LOCAL=OUT/'data_local'
BASE='98149a3dcf361c1c9d16cab16ba472a9351d536f'
CONFIG=dict(seed=42,steps=80,batch_cutoffs=1,torch_threads=4,learning_rate=.001,
            optimizer='Adam',params=1027,hidden_channels=8,output_kernel=3,
            latitude_boundary='reflect',longitude_boundary='circular',
            normalization='per-ilev population moments of 2021 historical log inputs only',
            loss='equal cutoff and horizon mean of cosine latitude weighted log MAE',
            order='four cutoffs in UTC order repeated',device='cpu',dtype='float32',
            initialization='zero output convolution; recent-density residual')


def save(name, data):
    with (OUT/name).open('x') as f:
        json.dump(data,f,indent=2,allow_nan=False)
        f.write('\n')


def table(name,data):
    import csv
    with (OUT/name).open('x',newline='') as f:
        w=csv.DictWriter(f,list(data[0]),lineterminator='\n')
        w.writeheader()
        w.writerows(data)


def frozen():
    manifest=v59.OUT/'publication_SHA256.json'
    v59.need(manifest.read_bytes()==subprocess.check_output(['git','show',f'{BASE}:{manifest.relative_to(ROOT)}']),
             'V59 frozen publication registry')
    pinned=json.loads(manifest.read_text())
    v59.need(all(sha(ROOT/p)==h for p,h in pinned.items()),'V59 publication file drift')
    rows,sources,_,_,_,_,_=v59.inputs()  # SHA and native time checks only
    ids={r['sample_id']:r for r in rows}
    samples=defaultdict(list)
    for r in v59.read_csv(v59.OUT/'sample_manifest.csv'):
        v59.need(all(r[k]==v for k,v in ids[r['sample_id']].items()) and
                 r['native_run_id']==v59.RUNS[r['date'][:4]],'Sample drift')
        samples[r['cutoff_UTC']].append(r)
    v59.need(len(samples)==8 and sum(map(len,samples.values()))==24,'Sample count')
    return {k:sorted(v,key=lambda row:int(row['horizon'])) for k,v in sorted(samples.items())}, sources


def read_history(cut,rows):
    payload=v59.LOCAL/('jail_'+cut.replace(':',''))/'anchors.txt'
    x=np.fromfile(payload,dtype='<f8').reshape(3,*v59.SHAPE)
    v59.need(all(r['input_SHA256']==sha(payload) for r in rows) and
             np.all(np.isfinite(x)&(x>0)),'History archive mismatch')
    return x


def read_targets(rows,year):
    v59.need(year in ('2021','2022') and all(r['date'].startswith(year) for r in rows),'Year access scope')
    if year=='2022':
        v59.need((OUT/'evaluation_prediction_lock.json').is_file(),'Targets still sealed')
    ledger={r['UTC']:r for r in v59.read_csv(v59.OUT/'den_read_ledger.csv')
            if r['stage']=='trusted_evaluation_after_prediction_lock' and r['UTC'].startswith(year)}
    ys=[]
    for r in rows:
        p=v59.LOCAL/'targets'/(r['sample_id']+'.bin')
        proof=ledger[r['prediction_target_UTC']]
        v59.need(proof['source_run']==r['source_run_id'] and sha(p)==proof['frame_SHA256'] and
                 proof['converted_units']=='kg/m3','Target identity')
        ys.append(np.fromfile(p,dtype='<f8').reshape(v59.SHAPE))
    y=np.stack(ys)
    v59.need(np.all(np.isfinite(y)&(y>0)),'Target validity drift')
    return y


class TinyDirectCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.layers=nn.ModuleList([nn.Conv2d(3,8,3),nn.Conv2d(8,8,3),nn.Conv2d(8,3,3)])
        nn.init.zeros_(self.layers[-1].weight)
        nn.init.zeros_(self.layers[-1].bias)

    def forward(self,x,last):
        for i,layer in enumerate(self.layers):
            x=F.pad(x,(1,1,0,0),mode='circular')
            x=F.pad(x,(0,0,1,1),mode='reflect')
            x=layer(x)
            if i<2:
                x=F.relu(x)
        return last+x


def vector(model):
    return np.concatenate([p.detach().numpy().ravel() for p in model.parameters()]).astype('<f8')


def run():
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.manual_seed(CONFIG['seed'])
    torch.use_deterministic_algorithms(True)
    torch.backends.mkldnn.enabled=False
    v59.need(OUT.resolve()==OUT and not LOCAL.exists(),'V60 one-shot path is occupied')
    samples,sources=frozen()
    train={k:v for k,v in samples.items() if k.startswith('2021')}
    v59.need(len(train)==4 and len(samples)-len(train)==4,'Cutoff division')
    LOCAL.mkdir(mode=0o700)
    save('authorization.json',dict(train_run=v59.RUNS['2021'],verification_run=v59.RUNS['2022'],
         train_cutoffs=list(train),verification_cutoffs=[k for k in samples if k not in train],
         scope='V60 once; reuse V59 archived DEN records; no new targets',no_Swarm=True,CPU_only=True,
         source_contracts=sources,V59_release_sha256=sha(v59.OUT/'publication_SHA256.json')))
    save('configuration.json',CONFIG)
    table('sample_scope.csv',[dict(r,stage='train' if k in train else 'engineering_validation')
                             for k,rows in samples.items() for r in rows])
    x=np.stack([read_history(t,r) for t,r in train.items()])
    y=np.stack([read_targets(r,'2021') for r in train.values()])
    log=np.log(x)
    mean=log.mean(axis=(0,1,3,4))
    std=log.std(axis=(0,1,3,4))
    v59.need(np.all(np.isfinite(std)&(std>0)),'Invalid training scale')
    save('normalization.json',dict(mean=mean.tolist(),std=std.tolist(),year='2021',targets_used=False,
         input_SHA256={t:r[0]['input_SHA256'] for t,r in train.items()}))
    xt=torch.from_numpy(((log-mean[None,None,:,None,None])/std[None,None,:,None,None]).transpose(0,2,1,3,4).astype('f4'))
    last=torch.from_numpy(log[:,-1,:,None].astype('f4'))
    yt=torch.from_numpy(np.log(y).transpose(0,2,1,3,4).astype('f4'))
    coords=json.loads((v59.OUT/'native_grid.json').read_text())
    w=torch.from_numpy(np.cos(np.deg2rad(coords['lat'])).astype('f4'))[None,None,:,None]
    norm=w.sum()*v59.SHAPE[0]*v59.SHAPE[2]
    model=TinyDirectCNN()
    initial=vector(model)
    v59.need(initial.size==CONFIG['params'],'Parameter count')
    def loss(i):
        pred=model(xt[i],last[i])
        value=(abs(pred-yt[i])*w).sum((0,2,3)).mean()/norm
        v59.need(torch.isfinite(pred).all() and torch.isfinite(value),'Nonfinite training value')
        return value
    start=time.monotonic()
    initial_pred=model(xt[0],last[0])
    v59.need(torch.equal(initial_pred,last[0].expand_as(initial_pred)),'Persistence init')
    loss(0).backward()
    v59.need(all(torch.isfinite(p.grad).all() for p in model.parameters()),'Invalid preflight gradients')
    model.zero_grad(set_to_none=True)
    preflight=time.monotonic()-start
    v59.need(preflight*CONFIG['steps']<1500 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<4*1024**2,
             'Preflight resource budget')
    opt=torch.optim.Adam(model.parameters(),lr=CONFIG['learning_rate'])
    with torch.no_grad():
        before=[float(loss(i)) for i in range(4)]
    logrows=[]
    start=time.monotonic()
    for step in range(CONFIG['steps']):
        i=step%4
        opt.zero_grad(set_to_none=True)
        l=loss(i)
        l.backward()
        grad=float(torch.sqrt(sum((p.grad.detach()**2).sum() for p in model.parameters())))
        v59.need(np.isfinite(grad) and grad<100,'Gradient stability guard')
        opt.step()
        logrows.append(dict(step=step+1,cutoff=list(train)[i],loss=float(l.detach()),grad_norm=grad,
                            elapsed_seconds=time.monotonic()-start))
    elapsed=time.monotonic()-start
    with torch.no_grad():
        after=[float(loss(i)) for i in range(4)]
    final=vector(model)
    v59.need(np.isfinite(final).all() and np.any(initial!=final),'Failed weight update')
    torch.save(model.state_dict(),LOCAL/'weights.pt')
    (LOCAL/'weights.pt').chmod(0o444)
    packet=v59.readonly(LOCAL/'model.bin',np.r_[final,mean,std].astype('<f8').tobytes())
    table('training_log.csv',logrows)
    save('training_receipt.json',dict(steps=80,train_seconds=elapsed,preflight_seconds=preflight,
         peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,CPU_threads=torch.get_num_threads(),
         torch_version=torch.__version__,parameter_count=final.size,loss_before=before,loss_after=after,
         training_loss_before=float(np.mean(before)),training_loss_after=float(np.mean(after)),
         max_gradient=max(r['grad_norm'] for r in logrows),weight_max_update=float(max(abs(final-initial))),
         initial_parameter_sha=v59.digest(initial.tobytes()),weights_SHA256=sha(LOCAL/'weights.pt'),packet_SHA256=packet,
         normalization_SHA256=sha(OUT/'normalization.json'),persistence_init_exact_log=True,
         validation_targets_read=0,validation_inputs_read=0,GPU=0))


if __name__=='__main__':
    run()
