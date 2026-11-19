"""Read-only autumn audit; fixed package paths, V17 warning channel, no launcher call."""
import argparse,sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R)]
from runtime.tiegcm_autumn_execution import PACKAGE,verify_package,require
from runtime.readonly_audit_warning_channel import WarningChannel
from runtime.tiegcm_rank_exit import write_once,digest
from atmosphere.tiegcm_autumn_acceptance import accept
if __name__=='__main__':
    q=argparse.ArgumentParser();q.add_argument('--year',type=int,choices=[2021,2022],required=True);q.add_argument('--run-id',required=True);q.add_argument('--output',required=True);a=q.parse_args()
    p=verify_package(a.year);out=Path(a.output);require(out.resolve()==(PACKAGE/str(a.year)/'postrun_audit_local/acceptance.json').resolve(),'Wrong audit destination')
    reader=R/'src/atmosphere/hourly_tiegcm_observation.py'
    with WarningChannel(out.parent,{reader:digest(reader)}) as channel:result=accept(R/p['cwd'],a.run_id,p)
    result.update(warning_count=channel.count,model_launches_this_audit=0);write_once(out,result)
    print(json.dumps(dict(ACTUAL_MODEL_RUN=result['ACTUAL_MODEL_RUN'],overall=result['overall'])))
    raise SystemExit(0 if result['overall']=='PASS' else 2)
