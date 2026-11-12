"""Audit completed A14 files without inventing an unobserved MPI exit code."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
import audit_tiegcm_2022_14day as a
if __name__=='__main__':
 s=a.adapted();F=ROOT/'experiments/tiegcm_2022_spinup_14day_v1';status=json.loads((F/'A14/run_status.json').read_text())
 assert status['returncode'] is None and status['stop_reason']=='launcher_disappeared_without_observable_exit_status' and status['normal_exit_count']==4
 s=s.replace("assert status['returncode']==0 and status['stop_reason'] is None and status['normal_exit_count']==4","assert status['returncode'] is None and status['normal_exit_count']==4")
 s=s.replace('engineering_PASS=True','engineering_PASS=False,data_integrity_PASS=True,launcher_exit_verified=False')
 s=s.replace("print('AUDIT PASS',len(rows))","print('DATA INTEGRITY PASS / ENGINEERING UNVERIFIED',len(rows))")
 (F/'A14/engineering_audit_adapter.json').open('x').write(json.dumps(dict(adapted_SHA256=hashlib.sha256(s.encode()).hexdigest(),kind='PARTIAL: data audit only; launcher status unrecoverable; B14 blocked',physical_data_checks_unchanged=True),indent=2))
 sys.argv=[__file__,'--group','A14'];exec(compile(s,str(ROOT/'scripts/audit_tiegcm_2021_14day.py'),'exec'),dict(__name__='__main__',__file__=str(ROOT/'scripts/audit_tiegcm_2021_14day.py')))
