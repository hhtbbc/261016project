"""Resume only already downloaded immutable files; no network acquisition call."""
from pathlib import Path
import sys,os,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from runtime.supervisor import supervise,Limits
F=ROOT/'experiments/causal_density_latitude_acquisition_v1'
if __name__=='__main__':
 job=F/'logs/local_verify';job.mkdir(exist_ok=False)
 r=supervise([sys.executable,str(ROOT/'scripts/acquire_causal_density_latitude_v1.py'),'verify-local'],job,Limits(350,4*2**30,20*2**30,150*2**20,100*2**20,.3,1,3,120,150*2**20),env=dict(os.environ,CUDA_VISIBLE_DEVICES='',MPLBACKEND='Agg'),total_dir=F)
 print(json.dumps({k:r.get(k) for k in ['qualification','returncode','elapsed_s','stop_reason']},indent=2));assert r['qualification']=='PASS' and r['returncode']==0
