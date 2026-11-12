"""Isolated reuse of the completed 2022 engineering audit; no model launch."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];TAG='tiegcm_2022_dual_initial_spinup_v1';F=ROOT/'experiments'/TAG

def adapted_source():
    p=ROOT/'scripts/audit_tiegcm_mar23_2022_longrun.py';s=p.read_text()
    old="F=R/'experiments/tiegcm_training_mar23_v2_2022_longrun';RESULT=R/'results/tiegcm_training_mar23_v2_2022_longrun'"
    new=f"F=R/'experiments/{TAG}';RESULT=R/'results/{TAG}/engineering'"
    assert s.count(old)==1;s=s.replace(old,new)
    s=s.replace("RESULT.mkdir(exist_ok=False)","RESULT.mkdir(parents=True,exist_ok=False)")
    return s
if __name__=='__main__':
    s=adapted_source();assert not (F/'engineering_audit_adapter.json').exists()
    (F/'engineering_audit_adapter.json').open('x').write(json.dumps(dict(origin='scripts/audit_tiegcm_mar23_2022_longrun.py',origin_SHA256=hashlib.sha256((ROOT/'scripts/audit_tiegcm_mar23_2022_longrun.py').read_bytes()).hexdigest(),adapted_SHA256=hashlib.sha256(s.encode()).hexdigest(),changes=['F/RESULT paths','parent directory creation'],no_physical_check_changes=True),indent=2))
    exec(compile(s,str(ROOT/'scripts/audit_tiegcm_mar23_2022_longrun.py'),'exec'),dict(__name__='__main__',__file__=str(ROOT/'scripts/audit_tiegcm_mar23_2022_longrun.py')))
