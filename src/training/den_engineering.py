"""DEN-only engineering adapters. Official inference/old pipeline remain unchanged."""
from pathlib import Path
from types import SimpleNamespace
import sys
import numpy as np
import torch
from training.pipeline import (ROOT, EpochPairs, OfficialFrameSource,
                              DirectTrainer, AffineNormalizer)
sys.path.insert(0,str(ROOT/'third_party/FourCastDEN_linux'))
from dataset.dataset_tiegcm import TGCMDataset
from utils.YParams import get_channel_index
from fourcastden.validation import NAMES,LENGTHS
PHYS=list(NAMES);LBC=['TLBC','ULBC','VLBC'];LENS=list(LENGTHS)+[1,1,1]
CHANNELS=get_channel_index(PHYS+LBC)
DEN_INDICES=np.asarray(CHANNELS['DEN'],dtype=int)
assert np.array_equal(DEN_INDICES,np.arange(142,171))
LABEL='DEN_ONLY / ENGINEERING_RESEARCH / HINDCAST / LIMITED_PHYSICAL_VALIDATION'
TAG='fourcastden_den_engineering_v3'
F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG;DATA=ROOT/'data/processed'/TAG

def native_fields(path):
    with np.load(path,allow_pickle=False) as n:
        return np.concatenate([n[k] for k in PHYS+LBC],axis=0).astype(np.float64)

def stats_policy(mean,std,maxabs):
    """No absolute universal threshold that would erase tiny DEN variability."""
    threshold=1e-12*np.maximum(np.maximum(abs(mean),maxabs),np.finfo(np.float64).tiny)
    constant=std<=threshold
    effective=np.where(constant,np.where(abs(mean)>0,abs(mean),1.),std)
    return effective,constant

def load_statistics():
    with np.load(DATA/'statistics.npz',allow_pickle=False) as n:
        return AffineNormalizer(n['means'],n['stds'])

def author_dataset(year):
    if year not in (2021,2022):raise ValueError('2023 is not part of v3')
    norm=load_statistics();means={};stds={};start=0
    for name,n in zip(PHYS+LBC,LENS):
        means[name]=norm.means[start:start+n];stds[name]=norm.stds[start:start+n];start+=n
    static=ROOT/'data/processed/static'
    config=SimpleNamespace(dt=1,n_history=0,log_DEN=False,index=CHANNELS,solar=True,
        geomagnetic=True,in_variables=PHYS+LBC,in_drivers=['f107d','f107a','Kp'],
        out_variables=PHYS,n_in_channels=177,n_out_channels=171,
        normalization='zscore',means=means,stds=stds,noise_std=0.,
        two_step_training=False,add_noise=False,n_lon_periodic=0,
        lat=np.load(static/'lat.npy'),lon=np.load(static/'lon.npy'),
        static_data_path=str(static))
    ds=TGCMDataset(config,str(DATA/str(year)),train=False)
    if ds.means.shape!=(174,1,1):raise ValueError('Wrong author normalization layout')
    np.testing.assert_array_equal(ds.means,norm.means)
    return ds

def pairs(year):
    ds=author_dataset(year)
    return EpochPairs([t.replace(tzinfo=__import__('datetime').timezone.utc) for t in ds.epochs],
                      OfficialFrameSource(ds),'train' if year==2021 else 'validation')

class DenTrainer(DirectTrainer):
    """Scheme A: unchanged 171 head, DEN-only weighted normalized MSE."""
    def loss(self,batch):
        x,d,y=batch
        if x.shape[1:]!=(177,36,72) or d.shape[1:]!=(1,4) or y.shape[1:]!=(171,36,72):
            raise ValueError('Invalid v3 shapes')
        if x.shape[0]!=d.shape[0] or x.shape[0]!=y.shape[0]:raise ValueError('Unequal batch sizes')
        if not all(torch.isfinite(a).all() for a in batch):raise ValueError('Nonfinite batch')
        p=self.model(x,d)
        if p.shape!=y.shape or not torch.isfinite(p).all():raise ValueError('Bad output')
        return den_objective(p,y,self.config['latitude_deg'])

def den_objective(prediction,target,latitude):
    lat=torch.as_tensor(latitude,device=prediction.device,dtype=prediction.dtype)
    weights=torch.cos(torch.deg2rad(lat));weights=weights/weights.mean()
    loss=((prediction[:,DEN_INDICES.tolist()]-target[:,DEN_INDICES.tolist()])**2*weights[None,None,:,None]).mean()
    if not torch.isfinite(loss):raise ValueError('Nonfinite DEN loss')
    return loss


def density_metrics(pred,truth,lat):
    """All finite predictions, including nonpositive, count in ordinary errors."""
    p,t=np.asarray(pred,float),np.asarray(truth,float)
    if p.shape!=t.shape or p.ndim!=3 or not np.isfinite(p).all() or not np.isfinite(t).all() or not (t>0).all():
        raise ValueError('Finite aligned C/lat/lon and strictly positive truth required')
    w=np.broadcast_to(np.cos(np.deg2rad(np.asarray(lat)))[None,:,None],p.shape);delta=p-t
    positive=p>0
    return dict(n=int(p.size),coverage=1.,positive_fraction=float(positive.mean()),
        RMSE=float(np.sqrt(np.average(delta**2,weights=w))),
        MAE=float(np.average(abs(delta),weights=w)),bias=float(np.average(delta,weights=w)),
        relative_RMS=float(np.sqrt(np.average((delta/t)**2,weights=w))),
        log_RMS=float(np.sqrt(np.average(np.log(p[positive]/t[positive])**2,weights=w[positive]))) if positive.any() else None,
        log_coverage=float(positive.mean()),max_abs=float(abs(delta).max()))

def evaluate_fields(pred,truth,lat,zg):
    """Per level/region plus upper20-28 and reference median ZG group."""
    rows=[];lat=np.asarray(lat)
    regions={'global':np.ones(len(lat),bool),'south_high':lat<=-60,'north_high':lat>=60,'midlow':abs(lat)<60}
    groups={'all':np.arange(29),'upper20_28':np.arange(20,29),'top28':np.array([28]),
            'reference_median_ZG_400_500':np.flatnonzero((np.median(zg,axis=(1,2))>=400e3)&(np.median(zg,axis=(1,2))<=500e3))}
    groups.update({f'level_{i:02d}':np.array([i]) for i in range(29)})
    for group,levels in groups.items():
        if not len(levels):continue
        for region,mask in regions.items():
            rows.append(dict(group=group,region=region,levels=' '.join(map(str,levels)),**density_metrics(pred[levels][:,mask],truth[levels][:,mask],lat[mask])))
    return rows

def restore_den(trainer,path,expected_sha):
    """Restore only this task's SHA-verified locally generated v3 checkpoint."""
    import hashlib,random
    path=Path(path).resolve();path.relative_to(F)
    if path.suffix!='.pt' or hashlib.sha256(path.read_bytes()).hexdigest()!=expected_sha:
        raise ValueError('Untrusted/mismatched v3 checkpoint')
    payload=torch.load(path,map_location='cpu',weights_only=False)
    if payload['metadata'].get('label')!=LABEL or payload['config']!=trainer.config:
        raise ValueError('Not the frozen v3 DEN task')
    trainer.model.load_state_dict(payload['model_state'],strict=True)
    trainer.optimizer.load_state_dict(payload['optimizer_state']);trainer.scheduler.load_state_dict(payload['scheduler_state']);trainer.step=payload['step']
    random.setstate(payload['rng']['python']);np.random.set_state(payload['rng']['numpy']);torch.set_rng_state(payload['rng']['torch'].cpu())
    if payload['rng']['cuda']:torch.cuda.set_rng_state_all([x.cpu() for x in payload['rng']['cuda']])
    trainer.model.train(payload['model_training'])
    return payload['metadata']
