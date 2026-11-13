"""New B14 queries only; reuse A7/B7/A14 previous real observations unchanged."""
from pathlib import Path
import sys,json,time,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_tiegcm_2022_b14_v2 import F,O,B,H,dump
from run_tiegcm_mar23_2021_longrun import stream_sha
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from atmosphere.tiegcm_density_provider import DATUM
from evaluation.swarm_density_comparison import paired_valid_mask,compare_density
from evaluation.swarm_crossyear import strata,metric_row
from run_swarm_tiegcm_2022_observation import read_observation
from astropy.time import Time
import compare_tiegcm_2021_initial_conditions as h
if __name__=='__main__':
 start=time.perf_counter();assert json.loads((F/'B14_engineering_gate.json').read_text())['PASS'];out=O/'observation';out.mkdir(exist_ok=False)
 oldpath=ROOT/'results/tiegcm_2022_spinup_14day_v1/observation_partial/aligned_local.npz';assert stream_sha(oldpath)==json.loads((F/'protected_files.json').read_text())[str(oldpath.relative_to(ROOT))];old=np.load(oldpath)
 manifest=json.loads((ROOT/'experiments/swarm_tiegcm_2022_observation_v1/downloads.json').read_text())
 for e in [manifest['product'],*manifest['members']]:assert stream_sha(ROOT/e['path'])==e['SHA256']
 raw,_=read_observation(next((ROOT/'data/raw/swarm_tiegcm_2022_observation_v1').glob('*.cdf')))
 for k,v in [('density','observed'),('quality','quality'),('utc','utc')]:np.testing.assert_array_equal(raw[k],old[v])
 values=np.full((4,4,len(raw['utc'])),np.nan);values[:,:3]=old['values'];coords=old['coords'];audit=json.loads((B/'data_audit.json').read_text());entries=[e for e in audit['files'] if e['file'].startswith('secondary') and any('2022-03-24' in t or '2022-03-25T00:00' in t for t in e['UTC'])]
 provider=HourlyTiegcmObservation([B/e['file'] for e in entries],{e['file']:e['SHA256'] for e in entries},'2022-03-24','2022-03-25','B14_EXPLORATORY_V2');queries=[]
 for mi,ma in enumerate('ABDE'):
  for i,t in enumerate(Time(raw['utc'])):
   if not raw['quality'][i]:continue
   q=provider.query_native(t,*coords[i,mi],datum=DATUM)
   if q.valid:values[mi,3,i]=q.rho_kg_m3
   queries.append(dict(mapping=ma,sample=i,UTC=str(raw['utc'][i]),valid=q.valid,reason=q.reason,rho_kg_m3=q.rho_kg_m3))
 common=paired_valid_mask(raw['quality'],*values.reshape(16,-1));metrics=[];coverage=[];improvements=[]
 for mi,ma in enumerate('ABDE'):
  for gi,group in enumerate(['A7','B7','A14','B14']):
   for region,mask in strata(raw['latitude'],raw['altitude'],raw['utc']).items():metrics.append(dict(mapping=ma,group=group,region=region,**metric_row(values[mi,gi],raw['density'],raw['quality'],common,mask)))
   bad={}
   for q in queries:
    if group=='B14' and q['mapping']==ma and not q['valid']:bad[q['reason']]=bad.get(q['reason'],0)+1
   coverage.append(dict(mapping=ma,group=group,quality=int(raw['quality'].sum()),own_valid=int(np.isfinite(values[mi,gi]).sum()),common=int(common.sum()),failure_reasons=json.dumps(bad)))
  for name,ia,ib in [('A14_vs_A7',0,2),('B14_vs_B7',1,3)]:
   x,y=[compare_density(values[mi,g,common],raw['density'][common]) for g in [ia,ib]]
   improvements.append(dict(mapping=ma,pair=name,n=int(common.sum()),RMSE_7=x['RMSE'],RMSE_14=y['RMSE'],RMSE_reduction_pct=100*(1-y['RMSE']/x['RMSE']),relative_RMS_7=x['relative_RMS'],relative_RMS_14=y['relative_RMS'],relative_RMS_reduction_pct=100*(1-y['relative_RMS']/x['relative_RMS'])))
 for name,rows in [('metrics.csv',metrics),('coverage.csv',coverage),('improvements.csv',improvements),('queries_local.csv',queries)]:h.csvout(out/name,rows)
 np.savez_compressed(out/'aligned_local.npz',values=values,observed=raw['density'],quality=raw['quality'],common=common,utc=raw['utc'],coords=coords)
 old21=np.load(ROOT/'results/swarm_tiegcm_2021_spinup_observation_v1/aligned_local.npz');joint=[]
 for year,arr,truth,quality,mask in [(2021,old21['values'],old21['observed'],old21['quality'],old21['common']),(2022,values,raw['density'],raw['quality'],common)]:
  for mi,ma in enumerate('ABDE'):
   for gi,group in enumerate(['A7','B7','A14','B14']):joint.append(dict(year=year,mapping=ma,group=group,**metric_row(arr[mi,gi],truth,quality,mask,np.ones(len(mask),bool))))
 h.csvout(out/'joint_year_metrics.csv',joint)
 dump(F/'observation_audit.json',dict(new_queries=len(queries),old_three_schemes_reused=True,common=int(common.sum()),quality=int(raw['quality'].sum()),new_download_bytes=0,raw_product_SHA256=manifest['product']['SHA256'],A14_engineering='PARTIAL',wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024));print('Four-scheme observation complete',common.sum())
