"""Exclusive one-shot CPU verification, no physical/scientific execution entry."""
from pathlib import Path
import sys,os,json
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from evaluation.density_verification import reserve,write_json,sha,require
from runtime.supervisor import supervise,Limits
F=R/'experiments/tiegcm_2022_mar25_independent_verification_v19'
if __name__=='__main__':
 tests=json.loads((F/'tests.json').read_text());require(tests['PASS'],'Tests required')
 protocol=json.loads((F/'protocol.json').read_text())
 for n,h in protocol['code_SHA256'].items():require(sha(R/n)==h,'Code SHA changed')
 job=F/'verification_once_local';reserve(job)
 result=supervise([sys.executable,str(R/'scripts/verify_density_validation_v19.py')],job,Limits(600,4*2**30,20*2**30,150*2**20,100*2**20,.25,1,3,120,150*2**20),env=dict(os.environ,CUDA_VISIBLE_DEVICES=''),total_dir=F)
 write_json(F,'supervision_result.json',result);print(json.dumps({k:result.get(k) for k in ['qualification','returncode','elapsed_s','stop_reason']}));require(result['returncode']==0 and result['qualification']=='PASS','Verification unsuccessful; no automatic retry')
