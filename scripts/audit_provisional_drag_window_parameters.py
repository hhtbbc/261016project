"""Read existing ESA CDF metadata/flags in the six-hour research window only."""
from pathlib import Path
import json,hashlib
import numpy as np
import cdflib
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'experiments/provisional_drag_orbit_v1/window_parameter_review.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 result={'labels':['PROVISIONAL','SYNTHETIC_AERODYNAMIC_PARAMETERS','HINDCAST'],'window_utc':['2023-03-21T00:00:02','2023-03-21T06:00:02'],'used_in_force':False,'products':[]}
 files=[next((ROOT/'data/raw/swarm_drag/extracted').glob('*SC_ADYN*20230321*.cdf')),next((ROOT/'data/raw/swarm_attitude_2023/extracted').glob('*STRAATT*20230321*.cdf'))]
 for path in files:
  before=sha(path)
  with cdflib.CDF(path) as c:
   assert c.varinq('Timestamp').Data_Type_Description=='CDF_EPOCH'
   times=cdflib.cdfepoch.to_datetime(c.varget('Timestamp'));mask=(times>=np.datetime64(result['window_utc'][0]))&(times<=np.datetime64(result['window_utc'][1]))
   global_attrs=c.globalattsget();origin=global_attrs['Sensing_Start'][0].removeprefix('UTC=')
   assert abs((times[0]-np.datetime64(origin))/np.timedelta64(1,'s'))<.001
   record={'file':str(path.relative_to(ROOT)),'sha256':before,'time_type':'CDF_EPOCH interpreted on product HDR UTC calendar; no GPS offset applied','HDR_UTC_anchor_difference_s':float((times[0]-np.datetime64(origin))/np.timedelta64(1,'s')),'samples':int(mask.sum()),'start_utc':str(times[mask][0]),'end_utc':str(times[mask][-1])}
   def counts(key):
    values=c.varget(key)[mask];u,n=np.unique(values,return_counts=True);return {str(v):int(count) for v,count in zip(u,n)}
   for key in ['SyncStatus','Flags_q']:record[key]=counts(key)
   if 'SC_ADYN' in path.name:
    mass=c.varget('m_SC')[mask];dt=c.varget('dt_thr')[mask];force=c.varget('f_thr')[mask]
    record.update(mass_range_kg=[float(mass.min()),float(mass.max())],thruster_ontime_nonzero_records=int(np.any(dt>0,axis=1).sum()),max_thruster_ontime_s=float(dt.max()),nonzero_nominal_force_records=int(np.any(force!=0,axis=1).sum()),Flags_Platform=counts('Flags_Platform'))
   else:
    q=c.varget('q')[mask];good=np.isfinite(q).all(axis=1)
    record.update(nonfinite_quaternion_rows=int((~good).sum()),finite_norm_range=[float(np.linalg.norm(q[good],axis=1).min()),float(np.linalg.norm(q[good],axis=1).max())],Maneuver_Id=counts('Maneuver_Id'),quaternion_attributes=c.varattsget('q'))
  assert sha(path)==before;result['products'].append(record)
 with OUT.open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
