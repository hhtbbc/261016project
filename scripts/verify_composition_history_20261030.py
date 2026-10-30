"""Verify all four trajectories and original candidates against historical SHA ledgers."""
from pathlib import Path
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from analyze_tiegcm_composition_root_cause_20261030 import R,OUT,sha,CASES
expected={};origin=R/'experiments/tiegcm_2021_spinup_14day_v1'
for group in ['A14','B14']:
 p=origin/group/'protected_files.json';expected.update(json.loads(p.read_text()))
 for x in json.loads((origin/group/'data_audit.json').read_text())['files']:expected[str((origin/group/x['file']).relative_to(R))]=x['SHA256']
# Only original scientific binary assets and frozen physical source/config in historical ledger;
# mutable status/worklog are intentionally not historical scientific result files.
selected={p:h for p,h in expected.items() if Path(p).suffix in ['.nc','.npz'] or p.startswith('third_party/TIEGCM2.0/')}
fail=[]
for p,h in selected.items():
 if not (R/p).is_file() or sha(R/p)!=h:fail.append(p)
assert not fail,fail
(OUT/'historical_integrity.json').write_text(json.dumps({'historical_assets_verified':len(selected),'changed':fail,'definition':'old binary scientific assets plus original TIE-GCM source; primary and candidate NPZ included'},indent=2))
print(len(selected),'historical scientific assets unchanged')
