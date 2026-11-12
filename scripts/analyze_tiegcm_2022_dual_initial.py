"""Wait for the one existing model run, then gated offline analysis; never launch MPI."""
from pathlib import Path
import sys,time,json,subprocess,hashlib,resource
ROOT=Path(__file__).resolve().parents[1];TAG='tiegcm_2022_dual_initial_spinup_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG
SCRIPTS=['audit_tiegcm_2022_dual_initial.py','compare_tiegcm_2022_dual_initial.py','accept_tiegcm_2022_dual_initial.py','observe_tiegcm_2022_dual_initial.py','joint_tiegcm_dual_initial_years.py','finalize_tiegcm_2022_dual_initial.py']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def limits():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_AS,(8*2**30,8*2**30))
def main():
    clock=time.monotonic();record={};code={x:sha(ROOT/'scripts'/x) for x in SCRIPTS}
    with (F/'offline_analysis_frozen_code.json').open('x') as f:json.dump(code,f,indent=2)
    while not (F/'run_status.json').exists():
        assert time.monotonic()-clock<3700,'Run completion wait budget'
        time.sleep(2)
    status=json.loads((F/'run_status.json').read_text());assert status['returncode']==0 and status['stop_reason'] is None and status['normal_exit_count']==4,status
    for name in SCRIPTS:
        assert sha(ROOT/'scripts'/name)==code[name]
        start=time.monotonic();log=ROOT/'logs'/(TAG+'_'+Path(name).stem+'.log')
        with log.open('x') as f:
            r=subprocess.run([sys.executable,str(ROOT/'scripts'/name)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=1800,preexec_fn=limits)
        record[name]=dict(returncode=r.returncode,wall_s=time.monotonic()-start,log=str(log.relative_to(ROOT)))
        with (F/'offline_progress.json').open('w') as f:json.dump(record,f,indent=2)
        if r.returncode:raise RuntimeError('Offline stage failed; preserved, no automatic retry: '+name)
        generated=sum(p.stat().st_size for d in [F,O] for p in d.rglob('*') if p.is_file())+sum(p.stat().st_size for p in (ROOT/'logs').glob(TAG+'*.log'))
        assert generated<=5*2**30,'Total new experiment budget'
    with (F/'offline_status.json').open('x') as f:json.dump(dict(PASS=True,stages=record,total_new_generated_bytes=generated,wait_plus_analysis_wall_s=time.monotonic()-clock,new_model_launches=0),f,indent=2)
if __name__=='__main__':main()
