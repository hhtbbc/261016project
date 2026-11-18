"""Read-only model acceptance CLI. It never launches a model or scores densities."""
from pathlib import Path
import sys,json,argparse
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from atmosphere.tiegcm_mar25_acceptance import accept_run
from runtime.tiegcm_rank_exit import write_once

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--run-id',required=True);p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.resolve().relative_to(ROOT)
 protocol=json.loads((ROOT/'experiments/tiegcm_2022_mar25_preparation_v1/launch_protocol.json').read_text());result=accept_run(Path(a.run),a.run_id,protocol);write_once(out,result);print(json.dumps(dict(ACTUAL_MODEL_RUN=result['ACTUAL_MODEL_RUN'],overall=result['overall'])));raise SystemExit(0 if result['overall']=='PASS' else 2)
if __name__=='__main__':main()
