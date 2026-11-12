"""Continue only after exact A14 exit + full audit; never relaunch A14."""
from pathlib import Path
import json,sys,time,subprocess
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/tiegcm_2022_spinup_14day_v1'
def call(script,args,log):
    with (ROOT/'logs'/log).open('x') as f:subprocess.run([sys.executable,str(ROOT/'scripts'/script),*args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
if __name__=='__main__':
    (F/'resume_guardian_once.json').open('x').write(json.dumps(dict(no_A14_launch=True,B14_max_launches=1)))
    while not (F/'A14/run_status.json').exists():
        elapsed=time.monotonic()-json.loads((F/'pair_launch_once.json').read_text())['started_monotonic']
        if elapsed>4800:raise RuntimeError('A14 completion evidence not obtained within budget')
        time.sleep(2)
    a=json.loads((F/'A14/run_status.json').read_text());assert a['returncode']==0 and a['stop_reason'] is None and a['normal_exit_count']==4,a
    call('audit_tiegcm_2022_14day.py',['--group','A14'],'tiegcm_2022_14day_A14_audit.log')
    assert json.loads((F/'A14/data_audit.json').read_text())['engineering_PASS']
    call('run_tiegcm_2022_14day.py',['--group','B14'],'tiegcm_2022_14day_B14_prepare.log')
    call('run_tiegcm_2022_B14_guarded.py',[],'tiegcm_2022_14day_B14_supervisor.log')
    call('audit_tiegcm_2022_14day.py',['--group','B14'],'tiegcm_2022_14day_B14_audit.log')
    assert json.loads((F/'B14/data_audit.json').read_text())['engineering_PASS']
    elapsed=time.monotonic()-json.loads((F/'pair_launch_once.json').read_text())['started_monotonic'];assert elapsed<=9600
    (F/'pair_status.json').open('x').write(json.dumps(dict(PASS=True,model_launches=2,orchestration_wall_s=elapsed,guardian_recovery=True)))
    for case in ['delta14','A14_A7','B14_B7']:call('compare_tiegcm_2022_14day.py',['--case',case],f'tiegcm_2022_14day_compare_{case}.log')
    call('joint_tiegcm_2021_2022_14day.py',[],'tiegcm_2022_14day_joint.log')
    call('observe_tiegcm_2022_14day.py',[],'tiegcm_2022_14day_observation.log')
    print('Both models and analyses completed',flush=True)
