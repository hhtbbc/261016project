"""Reuse frozen metrics and matched-domain machinery with explicit v2 paths."""
from pathlib import Path
import sys,json,argparse,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import run_tiegcm_2022_b14_v2 as r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['delta14','B14_B7','joint']);a=p.parse_args();assert json.loads((r.F/'B14_engineering_gate.json').read_text())['PASS']
 if a.stage=='joint':
  import joint_tiegcm_2021_2022_14day as j
  j.F=r.F;j.O=r.O;j.CASES[2022][2]=r.A;j.CASES[2022][3]=r.B;j.main()
 else:
  import compare_tiegcm_2022_14day as c
  c.F=r.F;c.O=r.O;c.CASES['delta14']=(r.A,r.B);c.CASES['B14_B7']=(r.legacy_data.B7,r.B);c.main(a.stage)
