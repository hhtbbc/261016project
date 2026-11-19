"""One CPU read-only audit batch. No model launcher import or model subprocess."""
from pathlib import Path
import sys,json,time,traceback,hashlib
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R)]
from runtime.readonly_audit_warning_channel import WarningChannel
from runtime.tiegcm_rank_exit import write_once
from atmosphere.tiegcm_mar25_acceptance import accept_run
import numpy as np
from netCDF4 import Dataset
F=R/'experiments/tiegcm_2022_mar25_postrun_acceptance_v17';PREP=R/'experiments/tiegcm_2022_mar25_preparation_v1';RUN=R/'experiments/tiegcm_2022_mar25_execution_review_v1/actual_run'
def main():
 started=time.perf_counter();plan=json.loads((F/'audit_protocol.json').read_text())
 for n,h in plan['code_SHA256'].items():
  if hashlib.sha256((R/n).read_bytes()).hexdigest()!=h:raise ValueError('Audit code identity changed')
 reader=R/'src/atmosphere/hourly_tiegcm_observation.py';protocol=json.loads((PREP/'launch_protocol.json').read_text());cwd=Path.cwd();cwd.resolve().relative_to(F)
 properties=[]
 for path in sorted(RUN.glob('secondary_*.nc')):
  with Dataset(path) as n:
   for name in ['DEN','ZG']:
    v=n[name];attrs={}
    for key in ['missing_value','_FillValue']:
     if key in v.ncattrs():
      value=np.asarray(v.getncattr(key));cast=value.astype(v.dtype)
      if not np.isfinite(cast).all():raise ValueError('Nonfinite cast of missing metadata')
      attrs[key]=dict(attribute_dtype=str(value.dtype),value=value.tolist(),native_cast=cast.tolist(),exactly_representable=bool(np.array_equal(cast.astype(value.dtype),value)))
    properties.append(dict(file=path.name,variable=name,dtype=str(v.dtype),dimensions=list(v.dimensions),attributes=attrs))
 write_once(cwd/'netcdf_property_audit.json',dict(records=properties,policy='No attribute or data change; explicit native validity gates before old query reader, warnings retained'))
 print(json.dumps(dict(event='READONLY_BATCH_STARTED',model_launches=0,original_V16='FAIL')),flush=True)
 try:
  with WarningChannel(cwd,{reader:plan['frozen_reader_SHA256']}) as channel:
   result=accept_run(RUN,plan['run_id'],protocol,query_observations=True)
  result.update(audit_version='V17_READONLY_WARNING_PROVENANCE_CHANNEL',V16_ORIGINAL_ENGINEERING_STATUS='FAIL',model_launches_this_task=0,warning_count=channel.count,frozen_scientific_conditions_unchanged=True)
  write_once(cwd/'acceptance.json',result)
  if result['overall']!='PASS':raise ValueError('Original engineering conditions did not pass')
  print(json.dumps(dict(event='ORIGINAL_ENGINEERING_CHECKS_PASS',warning_count=channel.count)),flush=True)
  # Independent native reading, calendar/hash, drivers and neighbor reconstruction.
  import importlib.util
  path=R/'scripts/verify_tiegcm_v17_independent.py';spec=importlib.util.spec_from_file_location('v17_independent',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.main()
  independent=json.loads((F/'independent_verification.json').read_text())
  if not independent['PASS'] or independent['overall']!='ENGINEERING_PASS':raise ValueError('Independent check disagrees')
  write_once(cwd/'batch_result.json',dict(overall='ENGINEERING_PASS',V16_ORIGINAL_ENGINEERING_STATUS='FAIL',main_acceptance='PASS',independent_acceptance='PASS',wall_s=time.perf_counter()-started,warning_count=channel.count,model_launches=0,density_metrics=0,correction_fits=0))
  print(json.dumps(dict(event='READONLY_BATCH_COMPLETE',overall='ENGINEERING_PASS',model_launches=0)),flush=True)
 except BaseException as e:
  if not (cwd/'batch_failure.json').exists():write_once(cwd/'batch_failure.json',dict(overall='ENGINEERING_FAIL',error_type=type(e).__name__,message=str(e),no_retry=True,model_launches=0))
  traceback.print_exc();raise
if __name__=='__main__':main()
