"""v8's separate resume policy; does not change checkpoint config or v7 policy."""
SOURCE_SHA256='82483f890db2d20ec00159ff0588217dd71d37889195ca5b77b1b3ac740e722f'

def additional_order():return [i%72 for i in range(200,720)]

def validate_plan(plan,source_config=None):
    if (plan['start_step'],plan['additional_updates'],plan['end_step'])!=(200,520,720):
        raise ValueError('Only frozen200->720 resume permitted')
    if plan['train_order']!=additional_order() or plan['cumulative_exposure_counts']!=[10]*72:
        raise ValueError('Cyclic720 schedule changed')
    if plan['forward_budget']!=dict(initial_restore=1,training=520,train_evaluation=72,validation=48,checkpoint_restore=1):
        raise ValueError('Expected642 model forwards')
    if plan['source_checkpoint']!='experiments/fourcastden_den_multisample_v7/step200.pt' or plan['source_checkpoint_SHA256']!=SOURCE_SHA256:
        raise ValueError('Not the authorized v7 source')
    if plan['evaluation_after_step']!=720 or plan['validation_after_step']!=720 or plan['train_evaluation_indices']!=list(range(72)) or plan['validation_indices']!=list(range(48)):
        raise ValueError('Final evaluation domain changed')
    cfg=plan['training_config']
    if cfg['max_train_steps']!=200 or (source_config is not None and cfg!=source_config):
        raise ValueError('Original checkpoint config must remain unchanged')
    if cfg['optimizer']!=dict(name='AdamW',lr=1e-4,weight_decay=0.) or cfg['scheduler']!=dict(step_size=1,gamma=1.) or cfg['gradient_clip_norm']!=1. or cfg['batch_size']!=1:
        raise ValueError('Original optimization changed')
    if plan['source_model_training'] is not False or plan['restore_array_rtol']!=0 or plan['restore_array_atol']!=0:
        raise ValueError('Strict eval-mode/output source check changed')
    return True
