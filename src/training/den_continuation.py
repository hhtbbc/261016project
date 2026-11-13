"""Separate continuation budget and strict local restore audit; old config is immutable."""
from dataclasses import dataclass
from pathlib import Path
import hashlib,gc,random

@dataclass
class ContinuationBudget:
    start_step:int
    additional_updates:int
    completed:int=0
    def before_step(self,current_step):
        if self.start_step<0 or self.additional_updates<=0 or self.completed>=self.additional_updates or current_step!=self.start_step+self.completed:
            raise RuntimeError('Continuation budget exhausted or cumulative step inconsistent')
    def after_step(self,current_step):
        if current_step!=self.start_step+self.completed+1 or self.completed>=self.additional_updates:
            raise RuntimeError('Unexpected cumulative optimizer update')
        self.completed+=1
    def assert_finished(self,current_step):
        if self.completed!=self.additional_updates or current_step!=self.start_step+self.additional_updates:
            raise RuntimeError('Continuation incomplete')

def validate_continuation_plan(plan,source_config=None):
    if (plan['start_step'],plan['additional_updates'],plan['end_step'])!=(100,100,200):
        raise ValueError('Only frozen100->200 continuation allowed')
    if plan['evaluation_steps']!=[100,150,200] or plan['validation_after_step']!=200 or plan['validation_indices']!=list(range(48)):
        raise ValueError('Evaluation schedule changed')
    if plan['train_pair_index']!=0 or plan['forward_budget']!=dict(training=100,fixed_evaluation=3,checkpoint_restore=1,validation=48):
        raise ValueError('Fixed sample or forward budget changed')
    cfg=plan['training_config']
    if cfg['max_train_steps']!=100 or (source_config is not None and cfg!=source_config):
        raise ValueError('Original checkpoint config must remain exactly unchanged')
    if cfg['optimizer']!=dict(name='AdamW',lr=1e-4,weight_decay=0.) or cfg['scheduler']!=dict(step_size=1,gamma=1.) or cfg['gradient_clip_norm']!=1.:
        raise ValueError('Optimization changed')
    return True

def rng_snapshot():
    import numpy as np,torch
    return dict(python=random.getstate(),numpy=np.random.get_state(),torch=torch.get_rng_state(),cuda=torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [])

def rng_fingerprint(rng):
    from training.den_overfit import array_sha
    n=rng['numpy']
    return dict(python=hashlib.sha256(repr(rng['python']).encode()).hexdigest(),numpy_keys=array_sha(n[1]),numpy_metadata=[n[0],int(n[2]),int(n[3]),float(n[4])],torch=array_sha(rng['torch']),cuda=[array_sha(x) for x in rng['cuda']])

def checkpoint_summary(path,expected_sha,root,expected_step,expected_metadata,config):
    import torch
    from training.pipeline import ROOT
    from training.den_engineering import LABEL
    from training.den_overfit import state_digest
    root=Path(root).resolve();root.relative_to(ROOT/'experiments');path=Path(path).resolve();path.relative_to(root)
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    if path.suffix!='.pt' or h.hexdigest()!=expected_sha:raise ValueError('Checkpoint SHA/path mismatch before deserialization')
    payload=torch.load(path,map_location='cpu',weights_only=False)
    if payload['step']!=expected_step or payload['config']!=config or payload['metadata'].get('label')!=LABEL:
        raise ValueError('Checkpoint step/config/label mismatch')
    if any(payload['metadata'].get(k)!=v for k,v in expected_metadata.items()):raise ValueError('Checkpoint metadata provenance mismatch')
    if config['optimizer']['name']=='AdamW':
        if not payload['optimizer_state']['state'] or any(float(x['step'])!=expected_step for x in payload['optimizer_state']['state'].values()):raise ValueError('AdamW update counter mismatch')
    summary=dict(checkpoint_SHA256=expected_sha,step=payload['step'],config=payload['config'],model_SHA256=state_digest(payload['model_state']),optimizer_SHA256=state_digest(payload['optimizer_state']),scheduler_SHA256=state_digest(payload['scheduler_state']),RNG=rng_fingerprint(payload['rng']),model_training=payload['model_training'],metadata_checks=expected_metadata,optimizer_state_entries=len(payload['optimizer_state']['state']))
    del payload;gc.collect();return summary

def audited_restore(trainer,path,expected_sha,*,root,expected_step,expected_metadata):
    from training.den_engineering import restore_den
    from training.den_overfit import state_digest
    summary=checkpoint_summary(path,expected_sha,root,expected_step,expected_metadata,trainer.config)
    restore_den(trainer,path,expected_sha,trusted_root=root)  # original strict config equality retained
    actual=dict(step=trainer.step,model_SHA256=state_digest(trainer.model.state_dict()),optimizer_SHA256=state_digest(trainer.optimizer.state_dict()),scheduler_SHA256=state_digest(trainer.scheduler.state_dict()),RNG=rng_fingerprint(rng_snapshot()),model_training=trainer.model.training)
    for k,v in actual.items():
        if v!=summary[k]:raise RuntimeError('Restore state mismatch: '+k)
    return dict(PASS=True,**summary)
