"""Diagnostic-only pairing: returns scalar/hash evidence, never a trainable Dataset."""
from datetime import timedelta
import hashlib
import numpy as np
import torch
from training.pipeline import utc

def array_hash(x):
    a = x.detach().cpu().contiguous().numpy() if torch.is_tensor(x) else np.ascontiguousarray(x)
    return hashlib.sha256(a.tobytes()).hexdigest()

@torch.inference_mode()
def inspect_pair(source, current, target, official_input, official_scalar, official_target, *, current_split, target_split):
    current, target = utc(current), utc(target)
    if target-current != timedelta(hours=1) or current.year != target.year or current_split != target_split:
        raise ValueError('Diagnostic times must be consecutive, same-year and same split')
    state, _, _ = source(current)
    truth, aux, scalar = source(target)
    x = torch.cat((state, aux), dim=0)[None]
    s = torch.as_tensor(scalar).reshape(1, 1, 4)
    y = torch.as_tensor(truth)[None]
    if x.shape != (1,177,36,72) or y.shape != (1,171,36,72) or not all(torch.isfinite(t).all() for t in (x,s,y)):
        raise ValueError('Invalid diagnostic fields')
    for a,b in [(x,official_input),(s,official_scalar),(y,official_target)]:
        np.testing.assert_array_equal(a.cpu().numpy(),torch.as_tensor(b).cpu().numpy())
    return dict(label='READ_ONLY_TEST_INTERFACE / NOT_TRAINING',current_UTC=current.isoformat(),target_UTC=target.isoformat(),
                input_shape=list(x.shape),scalar_shape=list(s.shape),target_shape=list(y.shape),
                input_SHA256=array_hash(x),scalar_SHA256=array_hash(s),target_SHA256=array_hash(y),
                max_input_abs_difference=0.,max_scalar_abs_difference=0.,max_target_abs_difference=0.,exact=True)
