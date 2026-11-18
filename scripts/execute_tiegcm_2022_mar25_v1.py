"""Future-only entry; explicit next-task authorization and full acceptance required."""
from pathlib import Path
import sys,argparse,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from runtime.tiegcm_mar25_execution import execute

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--authorize-17day-run',action='store_true');a=parser.parse_args()
 if not a.authorize_17day_run:parser.error('Next explicit user authorization required; model launch refused')
 print(json.dumps(execute(authorized=True),indent=2))
if __name__=='__main__':main()
