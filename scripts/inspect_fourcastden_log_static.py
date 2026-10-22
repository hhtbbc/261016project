"""CPU checkpoint/schema inspection only: no log-DEN model forward."""
import sys,json,resource
from pathlib import Path
import numpy as np,torch
from ruamel.yaml.scalarfloat import ScalarFloat
ROOT=Path(__file__).resolve().parents[1]
from run_fourcastden_multistep import sha,dump
F=ROOT/'experiments/fourcastden_multidate_v1'
p=ROOT/'models/checkpoints/author/Baseline_log_DEN_ckpt.tar'
manifest=json.loads((ROOT/'logs/checkpoint_sha256.json').read_text());assert sha(p)==manifest[p.name]['sha256']
torch.serialization.add_safe_globals([ScalarFloat]);ckpt=torch.load(p,map_location='cpu',weights_only=True);state=ckpt['model_state']
with np.load(ROOT/'data/processed/static_log/global_means.npz') as m,np.load(ROOT/'data/processed/static_log/global_stds.npz') as s:
 means=m['DEN'];std=s['DEN'];assert np.isfinite(means).all() and np.isfinite(std).all() and (std>0).all()
 report=dict(status='STATIC_ONLY_NO_FORWARD',checkpoint_sha256=sha(p),model_state_entries=len(state),tensor_shapes={k:list(v.shape) for k,v in state.items()},DEN_log_means=dict(shape=list(means.shape),min=float(means.min()),max=float(means.max())),DEN_log_stds=dict(shape=list(std.shape),min=float(std.min()),max=float(std.max())),compatible_expected_input_channels=177,normalization='Official log10(DEN in g/cm3), then matching static_log zscore; inverse requires pow10 then *1000 for kg/m3',cuda_branch_risk='Author inference.py np.power(10,pred_den_log) on torch tensor: CUDA/NumPy compatibility remains untested. Need isolated reviewed wrapper/overlay and synthetic checks before authorization of real log-DEN inference.',requirements=dict(flow=False,n_history=0,log_DEN=True,static='static_log'),no_model_constructed=True,no_GPU_forward=True,available_windows=5,extra_raw_frames_for_two_hour_log_variant=0,peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
assert any(k.endswith('patch_embed.proj.weight') and v.shape[1]==177 for k,v in state.items())
dump(F/'log_DEN_static.json',report);print(json.dumps({k:v for k,v in report.items() if k!='tensor_shapes'},indent=2))
