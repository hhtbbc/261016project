"""Read-only passthrough timers; preserve original return values and arithmetic."""
import time
class DatasetTimer:
    def __init__(self,dataset):self.dataset=dataset;self.read_decode_s=0.;self.normalization_s=0.;self.files=0
    def __enter__(self):
        import dataset.dataset_tiegcm as module
        self.module=module;self.original_load=module.load_variables;self.original_normalize=self.dataset._normalize
        self.had_instance_normalize='_normalize' in self.dataset.__dict__
        def load(*args,**kwargs):
            t=time.perf_counter();v=self.original_load(*args,**kwargs);self.read_decode_s+=time.perf_counter()-t;self.files+=1;return v
        def normalize(*args,**kwargs):
            t=time.perf_counter();v=self.original_normalize(*args,**kwargs);self.normalization_s+=time.perf_counter()-t;return v
        module.load_variables=load;self.dataset._normalize=normalize;return self
    def __exit__(self,*args):
        self.module.load_variables=self.original_load
        if self.had_instance_normalize:self.dataset._normalize=self.original_normalize
        else:del self.dataset.__dict__['_normalize']
class MetricTimer:
    def __init__(self,module):self.module=module;self.records=[];self.originals={}
    def __enter__(self):
        import torch
        for name in ['weighted_rmse_channels','weighted_acc_channels','unweighted_acc_channels']:
            original=getattr(self.module,name);self.originals[name]=original
            def wrap(*args,_name=name,_fn=original,**kwargs):
                start=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True);t=time.perf_counter();start.record();v=_fn(*args,**kwargs);end.record();end.synchronize();self.records.append(dict(function=_name,GPU_ms=start.elapsed_time(end),call_wall_s=time.perf_counter()-t));return v
            setattr(self.module,name,wrap)
        return self
    def __exit__(self,*args):
        for name,fn in self.originals.items():setattr(self.module,name,fn)
