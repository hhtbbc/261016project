"""Independent PyTorch CPU forward check using only already extracted histories."""
import os
import numpy as np
import torch

from evaluate_matched_validation_v67 import OUT,LOCAL,V66,SHA,LEADS,SHAPE,sha,save
from run_native_density_baselines_v59 import read_csv,need
from train_tiny_direct_v60 import TinyDirectCNN


def main():
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    need(os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU-only environment')
    forecast=read_csv(OUT/'prediction_manifest.csv')
    cuts=sorted({r['cutoff_UTC'] for r in forecast})
    n=0
    maximum=0.
    for arm in ('P','LT'):
        path=V66/'data_local'/arm/'checkpoint.pt'
        need(sha(path)==SHA[arm][0],'Checkpoint changed')
        state=torch.load(path,map_location='cpu',weights_only=True)
        model=TinyDirectCNN().cpu().eval()
        model.load_state_dict(state['state_dict'])
        packet=V66/'data_local'/arm/'parameter_packet.bin'
        need(sha(packet)==SHA[arm][1],'Parameter packet changed')
        a=np.fromfile(packet,dtype='<f8')
        weights=np.concatenate([p.detach().numpy().ravel() for p in model.parameters()])
        need(np.array_equal(weights,a[:1027]),'Checkpoint and C packet diverge')
        mean,std=[v.reshape(29,1,1,1) for v in np.split(a[1027:],2)]
        for i,cut in enumerate(cuts):
            history=np.fromfile(LOCAL/f'cut_{i:02}_{arm}/anchors.txt',dtype='<f8').reshape(3,*SHAPE)
            z=np.log(history).transpose(1,0,2,3)
            x=torch.from_numpy(((z-mean)/std).astype('f4'))
            with torch.inference_mode():
                correction=model(x,torch.zeros_like(x)).numpy().transpose(1,0,2,3)
            for j,h in enumerate(LEADS):
                source=history[2] if arm=='P' else np.take(history[2],(np.arange(72)+3*(h+1))%72,axis=-1)
                row=next(r for r in forecast if r['cutoff_UTC']==cut and r['method']==arm+'-Residual-CNN' and
                         int(r['lead'])==h)
                p=LOCAL/row['file']
                need(sha(p)==row['SHA256'],'Prediction drift')
                calculated=source*np.exp(correction[j].astype(float))
                exact=np.fromfile(p,dtype='<f8').reshape(SHAPE)
                error=float(np.max(np.abs(calculated/exact-1)))
                need(error<2e-6,'Independent CPU forecast mismatch')
                maximum=max(maximum,error)
                n+=1
    save(OUT/'checkpoint_forward_verification.json',dict(fields=n,max_relative_float32_vs_C=maximum,
         packets_match_checkpoint=True,validation_DEN_targets_reread=0,optimizer_updates=0))
    print(n,maximum)


if __name__=='__main__':
    main()
