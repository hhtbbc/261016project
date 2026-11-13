"""Small experiment-policy helpers; optimizer/model remain existing DenTrainer/AFNONet."""
from pathlib import Path
import hashlib

CHECK_STEPS = (0, 10, 50, 100)

def validate_overfit_plan(plan):
    if plan['train_pair_index'] != 0 or plan['updates'] != 100:
        raise ValueError('Only frozen first2021 pair and100 updates allowed')
    if tuple(plan['evaluation_steps']) != CHECK_STEPS or plan['validation_after_step'] != 100:
        raise ValueError('Checkpoint/validation schedule changed')
    if plan['validation_indices'] != list(range(48)):
        raise ValueError('Complete48 final validation pairs required')
    if plan['forward_budget'] != dict(training=100,fixed_evaluation=4,checkpoint_restore=1,validation=48):
        raise ValueError('Forward accounting changed')
    cfg = plan['training_config']
    if cfg['seed'] != 20261113 or cfg['max_train_steps'] != 100 or cfg['batch_size'] != 1:
        raise ValueError('Seed/step/batch changed')
    if cfg['optimizer'] != dict(name='AdamW', lr=1e-4, weight_decay=0.0):
        raise ValueError('Optimizer changed')
    if cfg['scheduler'] != dict(step_size=1, gamma=1.0) or cfg['gradient_clip_norm'] != 1.0:
        raise ValueError('Schedule/clip changed')
    return True

def array_sha(value):
    """Stable dtype/shape-aware CPU tensor digest, no CUDA API call."""
    import numpy as np
    if hasattr(value, 'detach'): value=value.detach().cpu().numpy()
    a=np.ascontiguousarray(value)
    h=hashlib.sha256();h.update(str(a.dtype).encode());h.update(str(a.shape).encode());h.update(a.tobytes())
    return h.hexdigest()

def state_digest(value):
    import torch
    h=hashlib.sha256()
    def walk(x):
        if torch.is_tensor(x):
            h.update(str(x.dtype).encode());h.update(x.detach().cpu().contiguous().numpy().tobytes())
        elif isinstance(x,dict):
            for k,v in x.items():h.update(str(k).encode());walk(v)
        elif isinstance(x,(list,tuple)):
            for v in x:walk(v)
        else:h.update(repr(x).encode())
    walk(value);return h.hexdigest()
