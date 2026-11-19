"""Future single-year autumn execution; V23 task does NOT authorize this flag."""
import argparse,sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from runtime.tiegcm_autumn_execution import execute
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--year',type=int,choices=[2021,2022],required=True);p.add_argument('--authorize-16day-run',action='store_true');a=p.parse_args()
    if not a.authorize_16day_run:p.error('New explicit single-year model authorization required; no launch')
    print(json.dumps(execute(a.year,authorized=True),indent=2))
