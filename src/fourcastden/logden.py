"""Value-preserving official static_log compatibility and density decoding."""
from pathlib import Path
import importlib.util
import numpy as np

def load_log_time_means(path):
    lengths=dict(TN=28,UN=28,VN=28,WN=29,Z=29,ZG=29,DEN=29,NE=29,TLBC=1,ULBC=1,VLBC=1)
    with np.load(path,allow_pickle=False) as z:out={k:z[k].copy() for k in z.files}
    for key,n in lengths.items():
        x=out[key]
        if x.shape==(1,n,36,72):out[key]=x.reshape(n,36,72)
        elif x.shape!=(n,36,72):raise ValueError(f'{key}: unexpected climatology shape {x.shape}')
        if not np.isfinite(out[key]).all():raise ValueError(f'{key}: invalid climatology')
    return out

def decode_physical(normalized,means,stds,log_density=False):
    """Float64 native physical fields; density in g/cm3, others author units."""
    x=np.asarray(normalized,dtype=np.float64)*np.asarray(stds,dtype=np.float64)+np.asarray(means,dtype=np.float64)
    if log_density:
        with np.errstate(over='raise',under='raise',invalid='raise'):
            x[...,142:171,:,:]=np.power(10.,x[...,142:171,:,:])
    if not np.isfinite(x).all() or not (x[...,142:171,:,:]>0).all():raise ValueError('Invalid physical density; no clipping allowed')
    return x

def checked_tensor_pow10(x):
    import torch
    if x.dtype not in (torch.float32,torch.float64):raise TypeError('FP32/FP64 floating tensor required')
    y=torch.pow(10,x)
    if not torch.isfinite(y).all() or not (y>0).all():raise ValueError('pow10 overflow/underflow/nonpositive; no clipping')
    return y

def load_overlay(path):
    spec=importlib.util.spec_from_file_location('fourcastden_logden_isolated_inference',str(Path(path)))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

class MetricTrace:
    """Capture author's metric operands/results, leaving all arithmetic intact."""
    def __init__(self,module):self.module=module;self.normalized_rmse=[];self.physical_pred=[];self.physical_target=[]
    def __enter__(self):
        self.original=self.module.weighted_rmse_channels
        def wrapper(pred,target,weight):
            if pred.ndim==4:
                import torch
                if not torch.isfinite(pred).all() or not torch.isfinite(target).all() or not (pred>0).all() or not (target>0).all():raise ValueError('Invalid physical density operands; stop')
            value=self.original(pred,target,weight)
            if pred.ndim==3:self.normalized_rmse.append(value.detach().cpu().numpy().copy())
            elif pred.ndim==4:
                self.physical_pred.append(pred.detach().cpu().numpy().copy())
                self.physical_target.append(target.detach().cpu().numpy().copy())
            return value
        self.module.weighted_rmse_channels=wrapper
        return self
    def __exit__(self,*args):self.module.weighted_rmse_channels=self.original
