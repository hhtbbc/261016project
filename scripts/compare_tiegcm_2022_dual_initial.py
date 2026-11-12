"""Isolated year/end-date adaptation; 2021 scientific arithmetic stays identical."""
from pathlib import Path
import ast,json,hashlib
ROOT=Path(__file__).resolve().parents[1];TAG='tiegcm_2022_dual_initial_spinup_v1';F=ROOT/'experiments'/TAG

def adapted_source():
    p=ROOT/'scripts/compare_tiegcm_2021_initial_conditions.py';old=p.read_text();s=old
    s=s.replace("F=R/'experiments/tiegcm_2021_spinup_initial_condition_v1';A=R/'experiments/tiegcm_training_mar23_v2_2021_longrun';B=F/'B';OUT=R/'results/tiegcm_2021_spinup_initial_condition_v1/comparison'",f"F=R/'experiments/{TAG}';A=R/'experiments/tiegcm_training_mar23_v2_2022_longrun';B=F;OUT=R/'results/{TAG}/comparison'")
    s=s.replace('85*86400','84*86400').replace("'last24h':t>=84*86400","'last24h':t>=83*86400")
    s=s.replace("r['time_doy_seconds']>=84*86400","r['time_doy_seconds']>=83*86400")
    s=s.replace('[167,239]','[167,215]').replace("'26 00 UTC'","'25 00 UTC'")
    # Ensure the frozen numerical routines are bytecode-independent AST identical.
    def funcs(src):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(src).body if isinstance(n,ast.FunctionDef)}
    a,b=funcs(old),funcs(s)
    for k in ['metrics','gate_cells','csvout']:assert a[k]==b[k],k
    assert "range(75*86400+3600,84*86400+1,3600)" in s
    return s
if __name__=='__main__':
    s=adapted_source();(F/'comparison_adapter.json').open('x').write(json.dumps(dict(origin='scripts/compare_tiegcm_2021_initial_conditions.py',original_SHA256=hashlib.sha256((ROOT/'scripts/compare_tiegcm_2021_initial_conditions.py').read_bytes()).hexdigest(),adapted_SHA256=hashlib.sha256(s.encode()).hexdigest(),changes=['experiment paths','stopDOY85->84','last24h startDOY84->83','endpoint array239->215','plot date26->25'],metrics_gate_AST_identical=True),indent=2))
    exec(compile(s,str(ROOT/'scripts/compare_tiegcm_2021_initial_conditions.py'),'exec'),dict(__name__='__main__',__file__=str(ROOT/'scripts/compare_tiegcm_2021_initial_conditions.py')))
