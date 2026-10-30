"""Final read-only checks/status artifacts; never run a model or touch a remote."""
from pathlib import Path
import sys,csv,json,re,hashlib,ast,datetime
import numpy as np
from netCDF4 import Dataset
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import run_tiegcm_runtime_restart_audit as m
O=m.OUT;S=m.SUITE

def main():
 c=json.loads((O/'comparison.json').read_text());assert c['RESTART_RECOVERY_READY']=='FAIL'
 # Keep unobserved downstream quantities absent, not zero.
 states={'INSTRUMENTATION_INVARIANCE_READY':'PARTIAL','STEPWISE_BUDGET_READY':'PARTIAL','SCIENTIFIC_TRAINING_READY':'FAIL','stage2_execution':'NOT_EXECUTED_UPSTREAM_FAIL','stage3_execution':'NOT_EXECUTED_UPSTREAM_FAIL','instrumented_builds':0,'stage2_launches':0,'stage3_launches':0,'process_percentages_available':False,'physical_budget_residual':None,'no_remote_sync':True}
 m.save(O/'dependent_stage_status.json',states)
 rows=[]
 for variable in ['O1','O2','N2','HE','TN','UN','VN']:
  for term in ['chemistry','horizontal_advection','vertical_transport','molecular_diffusion','eddy_diffusion','heating_external_source','boundary','numerical_filter','clipping','memory_bridge','closure_R']:
   rows.append({'variable':variable,'process':term,'per_step_value':None,'cumulative_value':None,'normalized_closure':None,'status':'NOT_EVALUATED_STAGE1_FAIL','note':'not an inferred zero; some terms require variable-specific equation applicability review'})
 with (O/'unavailable_budget.csv').open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 safe=[]
 for stage in ['continuous','segment','resumed']:
  with Dataset(S/stage/'secondary.nc') as n:
   for i,t in enumerate(n['mtime'][:]):
    den,md=m.fields(n,'DEN',i);tn,mt=m.fields(n,'TN',i);zg,mz=m.fields(n,'ZG',i)
    assert not md.any() and (den>0).all() and np.isfinite(den).all();assert not mz.any() and (np.diff(zg,axis=0)>0).all();assert tn[~mt].min()>100 and tn[~mt].max()<5000
    safe.append({'stage':stage,'mtime':t.tolist(),'DEN_min_g_cm3':float(den.min()),'DEN_max_g_cm3':float(den.max()),'TN_min_K':float(tn[~mt].min()),'TN_max_K':float(tn[~mt].max()),'ZG_monotonic':True})
 m.save(O/'basic_physical_sanity.json',{'records':safe,'note':'basic numeric sanity is not restart equivalence or atmospheric validation'})
 # Compare the actual rounded diagnostic prints against independent historical forcing.
 drv=m.GpiDriver(m.GPI);points=[]
 pat=r'GPI run: mtime=\s*(\d+)\s+(\d+)\s+(\d+) power=\s*([\d.E+-]+) ctpoten=\s*([\d.E+-]+) f107=\s*([\d.E+-]+) f107a=\s*([\d.E+-]+)'
 for stage in ['continuous','segment','resumed']:
  txt=(R/'logs'/f'tiegcm_runtime_restart_audit_v1_{stage}.log').read_text()
  for row in re.findall(pat,txt):
   d,h,minute=map(int,row[:3]);exp=drv.at(2021000+d,h*3600+minute*60);observed=dict(zip(['hpower','ctpoten','f107d','f107a'],map(float,row[3:])))
   err=max(abs(observed[k]-exp[k]) for k in observed);assert err<=.0005000001
   points.append({'stage':stage,'mtime':[d,h,minute],'rounded_log_max_error':err})
 assert points
 m.save(O/'driver_log_audit.json',{'records':points,'precision_limit':.0005000001,'source':'original three-decimal model prints; unchanged GPI','full_precision_record_checks_in':'comparison.json'})
 for p in [R/'scripts/run_tiegcm_runtime_restart_audit.py',R/'scripts/analyze_tiegcm_runtime_restart_audit.py',R/'scripts/audit_tiegcm_runtime_state_inventory.py',R/'scripts/finalize_tiegcm_runtime_restart_audit.py',R/'tests/test_runtime_restart_audit.py']:ast.parse(p.read_text())
 protected=json.loads((S/'protected_files.json').read_text());assert all(m.sha(R/p)==h for p,h in protected.items())
 outputs=[p for p in O.rglob('*') if p.is_file()]
 audit={'verified_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protected_files_unchanged':len(protected),'new_model_launches':3,'new_model_steps':40,'new_instrumentation_runs':0,'new_budget_runs':0,'original_candidates_unchanged':True,'no_remote_sync':True,'new_output_SHA256':{str(p.relative_to(R)):m.sha(p) for p in outputs},'new_code_SHA256':{str(p.relative_to(R)):m.sha(p) for p in (R/'scripts').glob('*tiegcm_runtime*py')}}
 m.save(O/'final_delivery_audit.json',audit)
 print('Final PASS: preservation, schema/sanity/log verification and stage-stop enforcement. Scientific restart remains FAIL.')
 print('Full-precision record-driver max difference',max(x['maximum_absolute_driver_error'] for x in c['drivers']))
if __name__=='__main__':main()
