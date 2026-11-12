"""Year/window-only isolated adaptation of validated 2021 sixteen/seventeen-day audit."""
from pathlib import Path
import sys,json,argparse,hashlib
ROOT=Path(__file__).resolve().parents[1];TAG='tiegcm_2022_spinup_14day_v1'
def adapted():
    s=(ROOT/'scripts/audit_tiegcm_2021_14day.py').read_text()
    s=s.replace("R/'scripts/run_tiegcm_2021_14day.py'","R/'scripts/run_tiegcm_2022_14day.py'")
    s=s.replace('tiegcm_2021_spinup_14day_v1',TAG).replace('gpi_2021_14day.nc','gpi_2022_14day.nc')
    s=s.replace("m.GROUP=GROUP;m.s.GPI=", "m.GROUP=GROUP;m.m.GROUP=GROUP;m.s.GPI=")
    # The new wrapper exposes its reused module explicitly below.
    s=s.replace('2021','2022').replace("('primary',18),('secondary',17)","('primary',17),('secondary',16)")
    s=s.replace('85*86400','84*86400').replace('analysis_window_records=73','analysis_window_records=49')
    s=s.replace('range(18)','range(17)').replace('range(1,409)','range(1,385)').replace('==73','==49').replace('408','384').replace('24480','23040').replace('24481','23041')
    s=s.replace('datetime(2022,3,26','datetime(2022,3,25').replace("'2022-03-26'","'2022-03-25'").replace("'2022-03-24','2022-03-25'","'2022-03-23','2022-03-25'")
    # Source filename in compile location only stays historical; behavior source is isolated.
    return s
if __name__=='__main__':
    # The imported wrapper exports field/basic_file/CASE/GROUP for the old audit contract.
    s=adapted();args=sys.argv;group=args[args.index('--group')+1];F=ROOT/'experiments'/TAG
    with (F/group/'engineering_audit_adapter.json').open('x') as f:json.dump(dict(origin='scripts/audit_tiegcm_2021_14day.py',adapted_SHA256=hashlib.sha256(s.encode()).hexdigest(),changes=['year2022','endMar25','17 primary/384 secondary/23040 steps','paths only']),f,indent=2)
    exec(compile(s,str(ROOT/'scripts/audit_tiegcm_2021_14day.py'),'exec'),dict(__name__='__main__',__file__=str(ROOT/'scripts/audit_tiegcm_2021_14day.py')))
