"""One exclusively reserved CPU analysis job. Never executes TIE-GCM."""
from pathlib import Path
import sys,os,json
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'));sys.path.insert(0,str(R/'scripts'))
from runtime.supervisor import Limits,supervise
from run_density_validation_v18 import F,load,dump,sha
if __name__=='__main__':
 assert load(F/'preflight.json')['PASS'];protocol=load(F/'frozen_protocol.json')
 for n,h in protocol['new_scripts'].items():
  expected=load(F/'implementation_addendum.json')['replacement_SHA256'].get(n,h);assert sha(R/n)==expected
 job=F/'cpu_once_local';job.mkdir(exist_ok=False)
 result=supervise([sys.executable,str(R/'scripts/run_density_validation_v18.py'),'worker'],job,Limits(600,4*2**30,20*2**30,150*2**20,100*2**20,.25,1.,3,120.,150*2**20),env=dict(os.environ,CUDA_VISIBLE_DEVICES='',MPLBACKEND='Agg'),total_dir=F)
 dump('supervision_result.json',result)
 print(json.dumps({k:result.get(k) for k in ['qualification','returncode','elapsed_s','stop_reason']}));assert result['qualification']=='PASS' and result['returncode']==0
