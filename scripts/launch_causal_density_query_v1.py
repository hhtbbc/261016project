"""Bounded read-only operator validation; fitting is a separate frozen phase."""
from pathlib import Path
import sys,os,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from runtime.supervisor import supervise,Limits
F=ROOT/'experiments/causal_density_correction_v1'
if __name__=='__main__':
 job=F/'query_job_v3';job.mkdir(exist_ok=False)
 result=supervise([sys.executable,str(ROOT/'scripts/query_causal_density_v1.py')],job,Limits(300,4*2**30,20*2**30,150*2**20,100*2**20,.3,1.,3,120.,150*2**20),env=dict(os.environ,CUDA_VISIBLE_DEVICES='',MPLBACKEND='Agg'),total_dir=F)
 print(json.dumps({k:result.get(k) for k in ['qualification','returncode','elapsed_s','peak_sampled_tree_rss_bytes','stop_reason']},indent=2));assert result['qualification']=='PASS' and result['returncode']==0
