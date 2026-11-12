"""A14 -> full engineering audit -> B14 -> full audit, exactly once each."""
from pathlib import Path
import sys,subprocess,json,time
ROOT=Path(__file__).resolve().parents[1];TAG='tiegcm_2022_spinup_14day_v1';F=ROOT/'experiments'/TAG

def call(script,args,log):
    with (ROOT/'logs'/log).open('x') as f:subprocess.run([sys.executable,str(ROOT/'scripts'/script),*args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
def main():
    start=time.monotonic()
    with (F/'pair_launch_once.json').open('x') as f:json.dump(dict(max_model_launches=2,ordered_groups=['A14','B14'],no_retry=True,started_monotonic=start),f,indent=2)
    for group in ['A14','B14']:
        if group=='B14':call('run_tiegcm_2022_14day.py',['--group',group],f'tiegcm_2022_14day_{group}_prepare.log')
        print('Starting once',group,flush=True)
        call('run_tiegcm_2022_14day.py',['--group',group,'--execute'],f'tiegcm_2022_14day_{group}_supervisor.log')
        call('audit_tiegcm_2022_14day.py',['--group',group],f'tiegcm_2022_14day_{group}_audit.log')
        assert json.loads((F/group/'data_audit.json').read_text())['engineering_PASS']
        assert time.monotonic()-start<9600
        print('Full engineering PASS',group,flush=True)
    with (F/'pair_status.json').open('x') as f:json.dump(dict(PASS=True,model_launches=2,orchestration_wall_s=time.monotonic()-start),f,indent=2)
if __name__=='__main__':main()
