from pathlib import Path
import sys,os,json
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from runtime.supervisor import supervise,Limits
F=R/'experiments/thermosphere_residual_representativeness_v1'
if __name__=='__main__':
 assert (R/'logs/residual_representativeness_v1_tests.log').read_text().rstrip().endswith('OK')
 job=F/'logs/worker';job.mkdir(exist_ok=False)
 result=supervise([sys.executable,str(R/'scripts/run_residual_representativeness_v1.py')],job,Limits(600,4*2**30,20*2**30,150*2**20,100*2**20,.3,1,3,120,150*2**20),env=dict(os.environ,CUDA_VISIBLE_DEVICES='',MPLBACKEND='Agg'),total_dir=F)
 print(json.dumps({k:result.get(k) for k in ['qualification','returncode','elapsed_s','stop_reason']},indent=2));assert result['qualification']=='PASS' and result['returncode']==0
