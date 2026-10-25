"""Wait for the single supervised pair and run read-only comparisons, no launch/retry."""
from pathlib import Path
import json,time,subprocess,sys
R=Path(__file__).resolve().parents[1];C=R/'experiments/tiegcm_2021_spinup_14day_v1'
def main():
 start=time.monotonic()
 while not (C/'pair_status.json').exists():
  for group in ['A14','B14']:
   p=C/group/'run_status.json'
   if p.exists():
    s=json.loads(p.read_text());assert s['returncode']==0 and s['stop_reason'] is None,s
  assert 'Traceback' not in (R/'logs/tiegcm_2021_14day_pair_supervisor.log').read_text(),'Pair controller failed; no retry'
  assert time.monotonic()-start<9600,'Analysis wait timeout'
  time.sleep(2)
 assert json.loads((C/'pair_status.json').read_text())['PASS']
 for kind in ['delta14','A14_A7','B14_B7']:
  print('Read-only comparison:',kind,flush=True)
  with (R/'logs'/f'tiegcm_2021_14day_comparison_{kind}.log').open('x') as f:subprocess.run([sys.executable,str(R/'scripts/compare_tiegcm_2021_7vs14.py'),'--comparison',kind],cwd=R,stdout=f,stderr=subprocess.STDOUT,check=True)
 (C/'analysis_status.json').open('x').write(json.dumps({'PASS':True,'comparisons':['delta14','A14_A7','B14_B7'],'no_simulation_launches':True}))
 print('Three comparisons completed',flush=True)
if __name__=='__main__':main()
