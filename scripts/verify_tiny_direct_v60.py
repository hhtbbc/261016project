"""Verify the frozen CPU checkpoint, C inference parity, and all Direct metric strata."""
import json

import numpy as np
import torch
from torch.nn import functional as F

from train_tiny_direct_v60 import (OUT, LOCAL, CONFIG, TinyDirectCNN, frozen,
                                  read_history, read_targets, save, vector)
from evaluate_tiny_direct_v60 import groups
import run_native_density_baselines_v59 as v59


def run():
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.backends.mkldnn.enabled=False
    receipt=json.loads((OUT/'training_receipt.json').read_text())
    norm=json.loads((OUT/'normalization.json').read_text())
    lock=json.loads((OUT/'evaluation_prediction_lock.json').read_text())
    v59.need(v59.sha(LOCAL/'weights.pt')==receipt['weights_SHA256'] and
             v59.sha(OUT/'normalization.json')==receipt['normalization_SHA256'] and
             v59.sha(OUT/'prediction_manifest.csv')==lock['prediction_manifest_SHA256'] and
             v59.sha(LOCAL/'model.bin')==receipt['packet_SHA256']==lock['weight_packet_SHA256'],
             'Artifact SHA mismatch')
    v59.need(lock['lock_checks']==24 and lock['validation_targets_read_before_lock']==0 and
             len(lock['kernel_probes'])==12 and lock['synthetic_poison_invariant'],'Isolation ledger')
    scope, sources=frozen()
    ids={s['sample_id']:s for group in scope.values() for s in group}
    samples=v59.read_csv(OUT/'sample_scope.csv')
    v59.need(len(samples)==24 and {s['sample_id'] for s in samples}==set(ids) and
             all(all(s[k]==v for k,v in ids[s['sample_id']].items()) for s in samples),'Sample identity')
    means=np.asarray(norm['mean'])
    scales=np.asarray(norm['std'])
    training=[read_history(t,r) for t,r in scope.items() if t.startswith('2021')]
    v59.need(len(training)==4 and norm['year']=='2021' and not norm['targets_used'] and
             set(norm['input_SHA256'])=={k for k in scope if k.startswith('2021')},'Normalization scope')
    # Independent per-layer reductions over an explicitly flattened history.
    for k in range(v59.SHAPE[0]):
        values=np.concatenate([np.log(group[:,k]).ravel() for group in training])
        v59.need(np.isclose(means[k],values.mean(),atol=1e-12,rtol=0) and
                 np.isclose(scales[k],values.std(),atol=1e-12,rtol=0),'Normalization arithmetic')
    torch.manual_seed(CONFIG['seed'])
    model=TinyDirectCNN()
    initial=vector(model)
    v59.need(initial.size==1027 and receipt['initial_parameter_sha']==v59.digest(initial.tobytes()),'Initial model')
    zero=model(torch.zeros((29,3,36,72)),torch.full((29,1,36,72),-23.))
    v59.need(torch.equal(zero,torch.full_like(zero,-23)),'Persistence initialization')
    edge=torch.arange(12).reshape(1,1,3,4).float()
    pad=F.pad(F.pad(edge,(1,1,0,0),mode='circular'),(0,0,1,1),mode='reflect')
    v59.need(pad[0,0,0].tolist()==[7,4,5,6,7,4] and
             pad[0,0,4].tolist()==[7,4,5,6,7,4],'Period/reflection convention')
    model.load_state_dict(torch.load(LOCAL/'weights.pt',map_location='cpu',weights_only=True))
    final=vector(model)
    v59.need(np.any(initial!=final) and np.array_equal(np.fromfile(LOCAL/'model.bin',dtype='<f8'),np.r_[final,means,scales]),
             'Checkpoint/worker packet divergence')
    coords=json.loads((v59.OUT/'native_grid.json').read_text())
    weights=np.cos(np.deg2rad(coords['lat']))[None,None,:,None]
    pm={r['sample_id']:r for r in v59.read_csv(OUT/'prediction_manifest.csv')}
    p,y,common=[],[],[]
    delta=0.
    train_losses=[]
    initial_losses=[]
    with torch.no_grad():
        for cut,rows in scope.items():
            history=read_history(cut,rows)
            lg=np.log(history)
            inp=((lg-means[None,:,None,None])/scales[None,:,None,None]).transpose(1,0,2,3).astype('f4')
            logforecast=model(torch.from_numpy(inp),torch.from_numpy(lg[-1,:,None].astype('f4')))
            density=np.exp(logforecast.numpy().transpose(1,0,2,3).astype('f8'))
            target=read_targets(rows,cut[:4])
            if cut.startswith('2021'):
                denom=weights.sum()*29*72*3
                train_losses.append(float(np.sum(np.abs(np.log(density)-np.log(target))*weights)/denom))
                initial_losses.append(float(np.sum(np.abs(lg[-1]-np.log(target))*weights)/denom))
            for i,row in enumerate(rows):
                sid=row['sample_id']
                path=LOCAL/'inference'/(sid+'.bin')
                proof=pm[sid]
                v59.need(v59.sha(path)==proof['SHA256'] and proof['target_UTC']==row['prediction_target_UTC'] and
                         proof['cutoff_UTC']==cut and int(proof['horizon'])==v59.LEADS[i] and
                         (path.stat().st_mode&0o222)==0,'Prediction hash or index')
                q=np.fromfile(path,dtype='<f8').reshape(v59.SHAPE)
                ratio=np.max(np.abs(q/density[i]-1))
                v59.need(ratio<4e-6 and np.all(np.isfinite(q)&(q>0)),'C and Torch inference differ')
                delta=max(delta,float(ratio))
                b=np.fromfile(v59.LOCAL/'predictions'/(sid+'.bin'),dtype='<f8').reshape(3,*v59.SHAPE)
                common.append(np.all(np.isfinite(b)&(b>0),axis=0))
                p.append(q)
                y.append(target[i])
    v59.need(np.allclose(train_losses,receipt['loss_after'],atol=3e-7,rtol=0) and
             np.allclose(initial_losses,receipt['loss_before'],atol=3e-7,rtol=0),'Independent training loss')
    log=v59.read_csv(OUT/'training_log.csv')
    v59.need(len(log)==80 and all(r['cutoff'].startswith('2021') and np.isfinite(float(r['loss'])) and
                 0<float(r['grad_norm'])<100 for r in log),'Training log scope or gradient')
    p,y,common=np.array(p),np.array(y),np.array(common)
    w=np.broadcast_to(weights,y.shape)
    grid=dict(groups(samples,coords))
    reviewed=0
    maxd=0.
    for r in v59.read_csv(OUT/'metrics.csv'):
        if r['method']!='TinyDirectCNN':
            continue
        ix=grid[r['year'],int(r['horizon']),r['region'],r['ilev_index']]
        valid=common[ix] if r['mask']=='common' else np.ones(y[ix].shape,bool)
        pp,yy,ww=p[ix][valid],y[ix][valid],w[ix][valid]
        e=pp-yy
        mass=np.sum(ww)
        a=abs(e)
        unique,j=np.unique(a,return_inverse=True)
        cdf=np.cumsum(np.bincount(j,weights=ww))
        expected=dict(mae=np.sum(ww*a)/mass,rmse=np.sqrt(np.sum(ww*e**2)/mass),
            bias=np.sum(ww*e)/mass,relative_rmse=np.sqrt(np.sum(ww*(e/yy)**2)/mass),
            log_rmse=np.sqrt(np.sum(ww*(np.log(pp)-np.log(yy))**2)/mass),
            max_abs=max(a),p95_abs=unique[np.searchsorted(cdf,.95*cdf[-1])])
        v59.need(int(r['n'])==len(e) and float(r['coverage'])==len(e)/valid.size,'Metric mask')
        for k,value in expected.items():
            got=float(r[k])
            v59.need(np.isclose(got,value,rtol=1e-11,atol=1e-24),f'Independent metric failed {k}')
            maxd=max(maxd,abs(got-value)/max(1e-24,abs(value)))
        reviewed+=1
    v59.need(reviewed==396,'Direct metric row count')
    save('independent.json',dict(train_cutoffs=4,validation_cutoffs=4,source_ids=[s['native_run_id'] for s in sources.values()],
         checkpoint_inference_max_relative_delta=delta,independent_train_losses=train_losses,
         independent_initial_losses=initial_losses,independent_metric_rows=reviewed,
         independent_metric_max_relative_delta=maxd,baseline_subset_rows_checked=1188,checkpoint_shape='[4,3,29,36,72]',
         boundary_check=True,Swarm_reads=0,GPU=0,new_model_integrations=0,formal_scoring=0))


if __name__=='__main__':
    run()
