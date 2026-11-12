"""B14 only; identical model launcher with race-safe read-only RSS sampling."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import run_tiegcm_2022_14day as r
from tiegcm_2022_runtime_guardian import safe_rss
if __name__=='__main__':
    r.GROUP='B14';r.m.GROUP='B14'
    assert json.loads((r.F/'A14/data_audit.json').read_text())['engineering_PASS']
    assert not (r.F/'B14/launch_once.json').exists()
    r.m.c.process_tree_rss=safe_rss
    r.dump(r.F/'B14/supervisor_diagnostic_patch.json',dict(purpose='Catch disappearing /proc entries while sampling RSS; no model/physics/namelist changes',original_runner_SHA256=r.stream_sha(ROOT/'scripts/run_tiegcm_2022_14day.py'),guardian_SHA256=r.stream_sha(ROOT/'scripts/tiegcm_2022_runtime_guardian.py'),wrapper_SHA256=r.stream_sha(Path(__file__))))
    r.m.execute(r.F/'B14')
