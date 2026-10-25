"""Single authorized A14 -> engineering audit -> B14 -> audit sequence, no retries."""
from pathlib import Path
import subprocess,sys,json,time
R=Path(__file__).resolve().parents[1];C=R/'experiments/tiegcm_2021_spinup_14day_v1'
def call(script,args,log):
 p=R/'logs'/log
 with p.open('x') as f:subprocess.run([sys.executable,str(R/'scripts'/script),*args],cwd=R,stdout=f,stderr=subprocess.STDOUT,check=True)
def main():
 assert not (C/'pair_launch_once.json').exists();(C/'pair_launch_once.json').open('x').write(json.dumps({'max_model_launches':2,'ordered_groups':['A14','B14'],'no_retry':True}))
 start=time.monotonic()
 for group in ['A14','B14']:
  if group=='B14':call('run_tiegcm_2021_14day.py',['--group',group,'--run-tag',C.name],f'tiegcm_2021_14day_{group}_prepare.log')
  print('Starting once:',group,flush=True)
  call('run_tiegcm_2021_14day.py',['--group',group,'--run-tag',C.name,'--execute'],f'tiegcm_2021_14day_{group}_supervisor.log')
  call('audit_tiegcm_2021_14day.py',['--group',group],f'tiegcm_2021_14day_{group}_audit.log')
  assert json.loads((C/group/'data_audit.json').read_text())['engineering_PASS'];print('Engineering PASS:',group,flush=True)
 (C/'pair_status.json').open('x').write(json.dumps({'PASS':True,'model_launches':2,'orchestration_wall_s':time.monotonic()-start},indent=2))
if __name__=='__main__':main()
