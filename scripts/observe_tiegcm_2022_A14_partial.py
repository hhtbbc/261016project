"""Completed-file A14 comparison only; B14 was NOT launched; no dual14 conclusion."""
from pathlib import Path
import sys,json,time,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from atmosphere.tiegcm_density_provider import DATUM
from evaluation.swarm_density_comparison import paired_valid_mask,compare_density
from evaluation.swarm_crossyear import strata,metric_row
from run_swarm_tiegcm_2022_observation import read_observation
from prepare_fourcastden_swarm_observation_v1 import sha,dump
from astropy.time import Time
import compare_tiegcm_2021_initial_conditions as h
TAG='tiegcm_2022_spinup_14day_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG
if __name__=='__main__':
 started=time.perf_counter();out=O/'observation_partial';out.mkdir(exist_ok=False);folder=F/'A14';audit=json.loads((folder/'data_audit.json').read_text());assert audit['data_integrity_PASS'] and not audit['engineering_PASS'] and not (F/'B14/launch_once.json').exists()
 oldroot=ROOT/'results/tiegcm_2022_dual_initial_spinup_v1/observation';old=np.load(oldroot/'aligned_local.npz');protected=json.loads((F/'protected_files.json').read_text());assert sha(oldroot/'aligned_local.npz')==protected[str((oldroot/'aligned_local.npz').relative_to(ROOT))]
 manifest=json.loads((ROOT/'experiments/swarm_tiegcm_2022_observation_v1/downloads.json').read_text())
 for e in [manifest['product'],*manifest['members']]:assert sha(ROOT/e['path'])==e['SHA256']
 raw,_=read_observation(next((ROOT/'data/raw/swarm_tiegcm_2022_observation_v1').glob('*.cdf')))
 for k,key in [('density','observed'),('utc','utc'),('quality','quality')]:np.testing.assert_array_equal(raw[k],old[key])
 entries=[e for e in audit['files'] if e['file'].startswith('secondary') and any('2022-03-24' in t or '2022-03-25T00:00' in t for t in e['UTC'])]
 p=HourlyTiegcmObservation([folder/e['file'] for e in entries],{e['file']:e['SHA256'] for e in entries},'2022-03-24','2022-03-25','A14_PARTIAL_ENGINEERING')
 values=np.full((4,3,len(raw['utc'])),np.nan);values[:,:2]=old['values'];coords=old['coords'];queries=[]
 for mi,ma in enumerate('ABDE'):
  for i,t in enumerate(Time(raw['utc'])):
   if not raw['quality'][i]:continue
   r=p.query_native(t,*coords[i,mi],datum=DATUM)
   if r.valid:values[mi,2,i]=r.rho_kg_m3
   queries.append(dict(group='A14',mapping=ma,sample=i,UTC=str(raw['utc'][i]),valid=r.valid,reason=r.reason,rho_kg_m3=r.rho_kg_m3))
 common=paired_valid_mask(raw['quality'],*values.reshape(12,-1));metrics=[];coverage=[];changes=[]
 for mi,ma in enumerate('ABDE'):
  for gi,group in enumerate(['A7','B7','A14']):
   for region,mask in strata(raw['latitude'],raw['altitude'],raw['utc']).items():metrics.append(dict(mapping=ma,group=group,region=region,**metric_row(values[mi,gi],raw['density'],raw['quality'],common,mask)))
   bad={}
   for q in queries:
    if group=='A14' and q['mapping']==ma and not q['valid']:bad[q['reason']]=bad.get(q['reason'],0)+1
   coverage.append(dict(mapping=ma,group=group,quality=int(raw['quality'].sum()),own_valid=int(np.isfinite(values[mi,gi]).sum()),common=int(common.sum()),failure_reasons=json.dumps(bad)))
  a,b=[compare_density(values[mi,g,common],raw['density'][common]) for g in [0,2]]
  changes.append(dict(mapping=ma,n=int(common.sum()),RMSE_7=a['RMSE'],RMSE_14=b['RMSE'],RMSE_reduction_pct=100*(1-b['RMSE']/a['RMSE']),relative_RMS_7=a['relative_RMS'],relative_RMS_14=b['relative_RMS'],relative_RMS_reduction_pct=100*(1-b['relative_RMS']/a['relative_RMS'])))
 for name,rows in [('metrics.csv',metrics),('coverage.csv',coverage),('improvements.csv',changes),('queries_local.csv',queries)]:h.csvout(out/name,rows)
 np.savez_compressed(out/'aligned_local.npz',values=values,observed=raw['density'],quality=raw['quality'],common=common,utc=raw['utc'],coords=coords)
 dump(F/'observation_partial_audit.json',dict(new_native_queries=len(queries),common=int(common.sum()),quality=int(raw['quality'].sum()),old_A7_B7_read_only=True,raw_SHA=manifest['product']['SHA256'],new_observation_download_bytes=0,qualification='A14 data integrity passed; MPI exit code unavailable; B14 absent; NO dual14 inference',wall_s=time.perf_counter()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
 print('Partial A14 observation comparison completed',common.sum())
