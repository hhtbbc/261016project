"""Small tensor CPU/CUDA and official static_log probes; no network forward."""
import sys,json,time,difflib,traceback
from pathlib import Path
import numpy as np,torch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'third_party/FourCastDEN_linux'))
from run_fourcastden_multistep import sha,dump
from fourcastden.logden import checked_tensor_pow10,load_log_time_means
F=ROOT/'experiments/fourcastden_logden_multidate_v1'
def main():
 F.resolve().relative_to(ROOT);F.mkdir(exist_ok=False);tick=time.perf_counter();report=dict(no_model_forward=True,devices={})
 for device in ['cpu','cuda']:
  if device=='cuda':assert torch.cuda.is_available()
  x=torch.tensor([-15.9,-12.3,-9.0],dtype=torch.float32,device=device)
  rec={}
  try:
   y=np.power(10,x);rec['original_np_power']=dict(success=True,type=type(y).__name__,dtype=str(y.dtype),device=str(getattr(y,'device','CPU ndarray')))
  except Exception as e:rec['original_np_power']=dict(success=False,error_type=type(e).__name__,error=str(e))
  y=checked_tensor_pow10(x);expected=np.power(10.,x.cpu().numpy().astype(float));np.testing.assert_allclose(y.cpu().numpy(),expected,rtol=3e-7)
  rec['torch_pow']=dict(success=True,dtype=str(y.dtype),device=str(y.device),max_relative_error=float(np.max(abs(y.cpu().numpy()-expected)/expected)),finite=True,positive=True)
  for value in [100.,-100.]:
   try:checked_tensor_pow10(torch.tensor([value],device=device));raise AssertionError('Overflow/underflow not rejected')
   except ValueError:pass
  report['devices'][device]=rec
 from utils.YParams import get_time_means
 try:get_time_means(str(ROOT/'data/processed/static_log/time_means.npz'));report['original_static_loader']='PASS'
 except Exception as e:report['original_static_loader']=dict(error_type=type(e).__name__,error=str(e))
 corrected=load_log_time_means(ROOT/'data/processed/static_log/time_means.npz');report['climatology_shapes']={k:list(v.shape) for k,v in corrected.items() if k in ['TN','UN','VN','WN','Z','DEN','TLBC','ULBC','VLBC']}
 with np.load(ROOT/'data/processed/static_log/time_means.npz') as z:
  for k in corrected:np.testing.assert_array_equal(corrected[k].reshape(-1),z[k].reshape(-1))
 src=ROOT/'third_party/FourCastDEN_linux/inference/inference.py';before=src.read_text();after=before.replace('from utils.YParams import SW_VARS, get_time_means, UNIT_VARS','from utils.YParams import SW_VARS, UNIT_VARS\nfrom fourcastden.logden import load_log_time_means as get_time_means')
 for var in ['pred_den_log','tar_den_log']:
  old=f'np.power(10,{var})';assert after.count(old)==1;after=after.replace(old,f'torch.pow(10,{var})')
 for var in ['pred','tar']:
  old=f'{var}[den_idx] * std[den_idx] + mean[den_idx]';assert after.count(old)==1;after=after.replace(old,f'{var}[den_idx] * std[den_idx, None, None] + mean[den_idx, None, None]')
 assert before!=after
 (F/'inference_overlay.py').write_text(after)
 patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='FourCastDEN_linux/inference/inference.py',tofile='isolated/inference_overlay.py'))
 (F/'compatibility.patch').write_text(patch)
 report.update(status='PASS',source_SHA256=sha(src),overlay_SHA256=sha(F/'inference_overlay.py'),patch_SHA256=sha(F/'compatibility.patch'),value_preserving_climatology_reshape=True,compatibility_probe_wall_s=time.perf_counter()-tick)
 dump(F/'compatibility.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()
