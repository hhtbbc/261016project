"""Frozen v7 sampling and budget policies; original model/trainer are unchanged."""
from collections import Counter
INITIAL_MODEL_SHA256='b3c177d26245e7be75f25995f243318b47f8a44148645010f6a3d4cfe16a68e7'

def cyclic_indices():return [i%72 for i in range(200)]
def exposure_counts(order):
    c=Counter(order);return [c[i] for i in range(72)]
def require_initial_hash(actual):
    if actual!=INITIAL_MODEL_SHA256:raise RuntimeError('Random initial model SHA mismatch; no updates permitted')
def require_gpu_budget(used_bytes):
    if used_bytes>20*2**30:raise MemoryError('GPU process over20GiB')
def validate_multisample_plan(plan,source_config=None):
    if plan['updates']!=200 or plan['train_order']!=cyclic_indices() or plan['exposure_counts']!=[3]*56+[2]*16:
        raise ValueError('Frozen200-update cyclic order/exposure changed')
    if plan['forward_budget']!=dict(training=200,train_evaluation=72,validation=48,checkpoint_restore=1):
        raise ValueError('Expected321 model forwards')
    if plan['validation_after_step']!=200 or plan['validation_indices']!=list(range(48)) or plan['train_evaluation_indices']!=list(range(72)):
        raise ValueError('Final evaluation domain changed')
    cfg=plan['training_config']
    if cfg['max_train_steps']!=200 or cfg['seed']!=20261113 or cfg['batch_size']!=1:
        raise ValueError('Fresh run seed/batch/budget changed')
    if cfg['optimizer']!=dict(name='AdamW',lr=1e-4,weight_decay=0.) or cfg['scheduler']!=dict(step_size=1,gamma=1.) or cfg['gradient_clip_norm']!=1.:
        raise ValueError('Optimization changed')
    if source_config is not None:
        expected=dict(source_config,max_train_steps=200)
        if cfg!=expected:raise ValueError('Only fresh-run max_train_steps may differ from source config')
    if plan['initial_model_SHA256']!=INITIAL_MODEL_SHA256 or plan['loss_trend']!=dict(type='trailing_arithmetic_mean',window=24,min_periods=24,descriptive_only=True):
        raise ValueError('Initialization/trend protocol changed')
    return True
