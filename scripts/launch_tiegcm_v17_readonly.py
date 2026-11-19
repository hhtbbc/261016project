"""Fixed-command read-only audit supervisor. At most one full batch; no model API."""
from pathlib import Path
import sys,json,os
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from runtime.supervisor import supervise,Limits
F=R/'experiments/tiegcm_2022_mar25_postrun_acceptance_v17'
def audit_argv():return [sys.executable,str(R/'scripts/audit_tiegcm_v17_readonly.py')]
def main():
 plan=json.loads((F/'audit_protocol.json').read_text())
 if not plan['targeted_tests_PASS']:raise ValueError('Tests not passed')
 directory=F/'audit_once_local';directory.mkdir(exist_ok=False)
 st=supervise(audit_argv(),directory,Limits(600,4*2**30,20*2**30,150*2**20,20*2**20,.25,1,3,120,150*2**20),env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'),total_dir=F)
 print(json.dumps({k:st.get(k) for k in ['qualification','returncode','elapsed_s','stop_reason','peak_sampled_tree_rss_bytes']},indent=2))
 if st['qualification']!='PASS' or st['returncode']!=0:raise SystemExit(2)
if __name__=='__main__':main()
