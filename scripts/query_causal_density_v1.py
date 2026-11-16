"""Read-only real-observation matching, no residual fitting or correction."""
from pathlib import Path
import sys,json,csv,time,resource,hashlib,warnings
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np,cdflib
from astropy.time import Time
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from atmosphere.causal_observation_operator import map_a_queries,observe_map_a,split_masks
from observations.density_catalog import read_swarm_pod
from prepare_fourcastden_swarm_observation_v1 import sha
TAG='causal_density_correction_v1';F=ROOT/'experiments'/TAG;V=ROOT/'experiments/thermosphere_observation_assimilation_feasibility_v1'
def dump(name,obj):
 p=F/name;assert p.resolve().is_relative_to(ROOT)
 with p.open('x') as f:json.dump(obj,f,indent=2,allow_nan=False)
def main():
 start=time.perf_counter()
 def record_warning(message,category,filename,lineno,file=None,line=None):
  with (F/'python_warnings_local.jsonl').open('a') as w:w.write(json.dumps(dict(message=str(message),category=category.__name__,filename=filename,line=lineno))+'\n')
 warnings.showwarning=record_warning
 assert not (F/'matched_local.npz').exists();proof=json.loads((V/'observation_quality.json').read_text());data={};checks=[];protected={};coords={};queries={}
 for e in proof:
  path=ROOT/e['source_file'];protected[e['source_file']]=e['source_SHA256']
  # All three historical CDFs are checked at nine fixed records, never Swarm B.
  with cdflib.CDF(path) as c:
   tt=cdflib.cdfepoch.to_datetime(c.varget('time'));rr=c.varget('density');la=c.varget('latitude');hh=c.varget('altitude')
  if e['year']!=2022:
   from run_swarm_tiegcm_2022_observation import read_observation
   a,_=read_observation(path)
  else:
   info=next((ROOT/'data/raw/thermosphere_observation_assimilation_feasibility_v1').glob('*DNS'+e['satellite']+'POD*info.json'),None)
   # v9 exact official HAPI metadata names recorded in receipts.
   if info is None:
    candidates=list((ROOT/'data/raw/thermosphere_observation_assimilation_feasibility_v1').rglob('*info.json'))
    info=next(p for p in candidates if json.loads(p.read_text()).get('x_dataset')==e['product_id'])
   rows,a,_=read_swarm_pod(path,info,e['source_SHA256'],satellite=e['satellite']);data[e['satellite']]=a
  assert sha(path)==e['source_SHA256']
  for i in [0,1440,2879]:
   assert tt[i]==a['utc'][i] and rr[i]==a['density'][i] and la[i]==a['latitude'][i] and hh[i]==a['altitude'][i]
   checks.append(dict(file=e['source_file'],record=i,PASS=True))
 for sat,a in data.items():
  m=split_masks(a['utc']);idx=np.flatnonzero((m['calibration']|m['future_6h']) if sat=='A' else m['future_6h']);a={k:v[idx] for k,v in a.items()};data[sat]=a
  queries[sat]=map_a_queries(a['utc'],a['latitude'],a['longitude'],a['altitude']);coords[sat]=np.array([[q.latitude_deg,q.longitude_deg,q.height_wgs84_m] for q in queries[sat]])
 oldpath=ROOT/'results/tiegcm_2022_b14_exploratory_pair_v2/observation/aligned_local.npz';old=np.load(oldpath);old_identity=json.loads((F/'legacy_comparison_identity.json').read_text());assert sha(oldpath)==old_identity['SHA256'];protected[str(oldpath.relative_to(ROOT))]=sha(oldpath)
 provenance=list(csv.DictReader((ROOT/'results/thermosphere_observation_assimilation_feasibility_v1/eight_trajectory_provenance.csv').open()));values={};cases=[];probes=[]
 with (F/'query_trace_local.jsonl').open('x') as out:
  for case in ['B14','A7','B7','A14']:
   row=next(x for x in provenance if x['case']=='2022_'+case);folder=(ROOT/row['input']).parent;auditpath=folder/'data_audit.json';audit=json.loads(auditpath.read_text());assert sha(ROOT/row['input'])==row['input_SHA256'];eng='PARTIAL' if case=='A14' else 'PASS';assert audit['engineering_PASS']==(eng=='PASS');assert eng=='PASS' or audit['data_integrity_PASS']
   for name,expected in [(row['input'],row['input_SHA256']),(row['source'],row['source_SHA256']),(row['GPI'],row['GPI_SHA256'])]:assert sha(ROOT/name)==expected;protected[name]=expected
   entries=[e for e in audit['files'] if e['file'].startswith('secondary') and any('2022-03-24' in t for t in e['UTC'])];expected={e['file']:e['SHA256'] for e in entries}
   protected[str(auditpath.relative_to(ROOT))]=sha(auditpath)
   for e in entries:protected[str((folder/e['file']).relative_to(ROOT))]=e['SHA256']
   p=HourlyTiegcmObservation([folder/e['file'] for e in entries],expected,'2022-03-24T03:00:00','2022-03-24T12:00:00',case);v={};fail={};before=time.perf_counter()
   for sat,a in data.items():
    v[sat]=np.full(len(a['utc']),np.nan)
    for i,q in enumerate(queries[sat]):
     result,c=observe_map_a(p,q)
     if result.valid:v[sat][i]=result.rho_kg_m3
     else:fail[result.reason]=fail.get(result.reason,0)+1
     out.write(json.dumps(dict(case=case,engineering=eng,satellite=sat,sample=i,UTC=str(a['utc'][i])+'Z',quality_flag=int(a['validity_flag'][i]),coordinate=c,valid=result.valid,reason=result.reason,rho_kg_m3=result.rho_kg_m3,unit_conversion='DEN g/cm3 *1000; ZG cm *.01',metadata=result.metadata))+'\n')
     if i in [0,len(a['utc'])//2,len(a['utc'])-1] and result.valid:
      md=result.metadata;w=md['weights'];weights=np.array([1-w['time'],w['time']])[:,None,None]*np.array([1-w['latitude'],w['latitude']])[None,:,None]*np.array([1-w['longitude'],w['longitude']])[None,None,:];terms=[]
      for col in md['columns']:
       k=next(k for k,(_,path,rec) in enumerate(p.records) if path.name==col['file'] and rec==col['record']);z,rho=p._column(k,col['lat_index'],col['lon_index']);terms.append(np.exp(np.interp(c['model_zg_m'],z,np.log(rho))))
      direct=float(np.sum(weights*np.array(terms).reshape(2,2,2)));assert np.isclose(direct,result.rho_kg_m3,rtol=1e-13,atol=0);probes.append(dict(case=case,satellite=sat,sample=i,relative_difference=abs(direct/result.rho_kg_m3-1)))
   oldidx=np.searchsorted(old['utc'],data['A']['utc']);gi=['A7','B7','A14','B14'].index(case);base=old['values'][0,gi,oldidx];both=np.isfinite(base)&np.isfinite(v['A']);rel=float(np.max(abs(v['A'][both]/base[both]-1)));assert rel<1e-12
   cases.append(dict(case=case,engineering=eng,frames=len(p.records),grid=[len(p.ilev),len(p.lat),len(p.lon)],input_files=entries,query_failures=fail,A_prior_max_relative_difference=rel,wall_s=time.perf_counter()-before));values[case]=v;p.close();print('Matched',case,'failures',fail,flush=True)
 arrays={}
 for sat,a in data.items():
  for k in ['utc','density','quality','latitude','longitude','altitude','validity_flag']:arrays[sat+'_'+k]=a[k]
  arrays[sat+'_map_A_coordinates']=coords[sat]
  for case in values:arrays[case+'_'+sat]=values[case][sat]
 np.savez_compressed(F/'matched_local.npz',**arrays)
 for n,h in protected.items():assert sha(ROOT/n)==h,n
 dump('matched_samples_manifest.json',dict(cases=cases,observation_files=proof,protected_inputs=protected,Swarm_B_values_read=False,Map_A_only=True,new_observation_downloads=0,matched_SHA256=sha(F/'matched_local.npz')))
 dump('operator_independent_probes.json',dict(PASS=True,CDF_checks=checks,interpolation_reconstructions=probes))
 dump('query_run.json',dict(PASS=True,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,queries=4*(len(data['A']['utc'])+len(data['C']['utc'])),correction_fits=0))
 print('READ ONLY MATCH COMPLETE',flush=True)
if __name__=='__main__':main()
