"""Static CDF review only. No force parameters inferred from validation orbits."""
import json,csv,hashlib,sys
from pathlib import Path
import numpy as np
import cdflib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'experiments/high_order_gravity_v1/swarm_parameter_audit.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def counts(a):
 u,n=np.unique(a,return_counts=True);return {str(x):int(y) for x,y in zip(u,n)}
def intervals(times,mask,kind,file):
 idx=np.flatnonzero(mask);out=[]
 if not len(idx):return out
 groups=np.split(idx,np.flatnonzero((np.diff(idx)>1)|((np.diff(times[idx])/np.timedelta64(1,'s'))>1.5))+1)
 for g in groups:out.append({'file':file,'kind':kind,'first_utc':str(times[g[0]]),'last_sample_utc':str(times[g[-1]]),'sample_count':len(g),'physical_net_impulse_known':False})
 return out
def main():
 if OUT.exists():raise FileExistsError(OUT)
 out={'status':'STATIC_REVIEW_NOT_USED_IN_PROPAGATION','products':[],'intervals':[],'Cd':None,'effective_area_m2':None,'mass_standard_uncertainty_kg':None,'ballistic_parameter_ready':False,'product_definition_5_13_applies_to_0601_confirmed':False}
 for folder,kind in [('swarm_drag','SC_ADYN'),('swarm_attitude_2023','STRAATT')]:
  for p in sorted((ROOT/f'data/raw/{folder}/extracted').glob(f'*{kind}*2023032[123]*.cdf')):
   old=sha(p)
   with cdflib.CDF(p) as c:
    g=c.globalattsget();time=c.varget('Timestamp');assert c.varinq('Timestamp').Data_Type_Description=='CDF_EPOCH';times=cdflib.cdfepoch.to_datetime(time)
    window=(times>=np.datetime64('2023-03-21T00:00:02'))&(times<=np.datetime64('2023-03-21T06:00:02'))
    origin=np.datetime64(g['Sensing_Start'][0].removeprefix('UTC='));assert abs((times[0]-origin)/np.timedelta64(1,'s'))<.001
    r={'file':str(p.relative_to(ROOT)),'sha256':old,'samples':len(times),'File_Version':g.get('File_Version'),'Software_Version':g.get('Software_Version'),'Proc_Time':g.get('Proc_Time'),'Ref_Doc':g.get('Ref_Doc'),'SyncStatus':counts(c.varget('SyncStatus')),'Flags_q':counts(c.varget('Flags_q')),'six_hour_samples':int(window.sum()),'epoch_system':'CDF_EPOCH + product UTC header; no GPS offset','unit_attributes':{}}
    if kind=='SC_ADYN':
     mass=c.varget('m_SC');dt=c.varget('dt_thr');force=c.varget('f_thr');platform=c.varget('Flags_Platform');thr_set=c.varget('thr_set')
     r.update(mass_min_kg=float(np.min(mass)),mass_max_kg=float(np.max(mass)),thruster_on_records=int(np.any(dt>0,axis=1).sum()),nonzero_nominal_force_records=int(np.any(force!=0,axis=1).sum()),Flags_Platform=counts(platform),thr_set=counts(thr_set),six_hour_on_records=int(np.any(dt[window]>0,axis=1).sum()),six_hour_platform_flag16_records=int((platform[window]==16).sum()))
     for key in ['m_SC','A_head','A_right','A_left','A_down','dt_thr','f_thr','thr_set','Flags_Platform']:r['unit_attributes'][key]=c.varattsget(key)
     out['intervals']+=intervals(times,np.any(dt>0,axis=1),'dt_thr_positive_NOT_net_deltaV',str(p.relative_to(ROOT)))
     out['intervals']+=intervals(times,platform==16,'Flags_Platform_equals_16_product_semantics_UNCONFIRMED',str(p.relative_to(ROOT)))
    else:
     q=c.varget('q');finite=np.isfinite(q).all(axis=1);maneuver=c.varget('Maneuver_Id')
     r.update(nonfinite_quaternion_rows=int((~finite).sum()),finite_quaternion_norm_min=float(np.linalg.norm(q[finite],axis=1).min()),finite_quaternion_norm_max=float(np.linalg.norm(q[finite],axis=1).max()),Maneuver_Id=counts(maneuver),quaternion_attributes=c.varattsget('q'),six_hour_Maneuver_Id=counts(maneuver[window]))
     out['intervals']+=intervals(times,maneuver==4,'Maneuver_Id_4_UNDECODED',str(p.relative_to(ROOT)))
     out['intervals']+=intervals(times,~finite,'nonfinite_quaternion_REJECT',str(p.relative_to(ROOT)))
   assert sha(p)==old;out['products'].append(r)
 pdf=ROOT/'data/raw/gravity_sources/swarm_L1b_5_13.pdf';out['official_document']={'version':'SW-RS-DSC-SY-0007 Issue5.13 2013-10-09','file':str(pdf.relative_to(ROOT)),'sha256':sha(pdf),'sections_checked':['4.4.2/Table4-13','6.14','6.17/Table6-5','Table6-1','AppendixB','AppendixD'],'publication':'Official ESA documents webpage link; PDF retained locally only'}
 OUT.write_text(json.dumps(out,indent=2)+'\n')
 with (ROOT/'results/metrics/high_order_gravity_v1_swarm_review_intervals.csv').open('x') as f:
  w=csv.DictWriter(f,fieldnames=list(out['intervals'][0]),lineterminator='\n');w.writeheader();w.writerows(out['intervals'])
 print('Products',len(out['products']),'intervals',len(out['intervals']),'no use in force model')
if __name__=='__main__':main()
