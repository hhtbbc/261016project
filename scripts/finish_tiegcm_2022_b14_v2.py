"""Wait for new direct-wait gate, audit, then offline analysis; no model launch."""
from pathlib import Path
import sys,time,json,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_tiegcm_2022_b14_v2 import F,O,B
if __name__=='__main__':
 (F/'postprocess_once.json').open('x').write(json.dumps(dict(real_model_launches_added=0,require_B14_engineering=True)))
 start=json.loads((F/'model_launch_once.json').read_text())['start_monotonic']
 while not (F/'B14_supervision_gate.json').exists():
  if (B/'status.json').exists():
   s=json.loads((B/'status.json').read_text())
   if s['qualification']!='PASS' or s['returncode']!=0:raise RuntimeError('B14 supervisor not PASS; no dependent analysis')
  if time.monotonic()-start>4805:raise RuntimeError('B14 gate unavailable within authorized wall budget')
  time.sleep(2)
 def call(script,args,label):
  with (ROOT/'logs'/f'tiegcm_2022_b14_v2_{label}.log').open('x') as log:subprocess.run([sys.executable,str(ROOT/'scripts'/script),*args],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
 call('audit_tiegcm_2022_b14_v2.py',[],'audit')
 for stage in ['delta14','B14_B7','joint']:call('analyze_tiegcm_2022_b14_v2.py',[stage],'analysis_'+stage)
 call('observe_tiegcm_2022_b14_v2.py',[],'observation')
 print('B14 engineering and all offline comparisons completed',flush=True)
