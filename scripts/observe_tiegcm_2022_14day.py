"""Read-only DNS/old predictions; query only A14/B14 and use 16-way common IDs."""
from pathlib import Path
import sys,json,csv,time,resource
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

def main():
    started=time.perf_counter();out=O/'observation';out.mkdir(exist_ok=False);oldroot=ROOT/'results/tiegcm_2022_dual_initial_spinup_v1/observation';old=np.load(oldroot/'aligned_local.npz')
    protected=json.loads((F/'protected_files.json').read_text());assert sha(oldroot/'aligned_local.npz')==protected[str((oldroot/'aligned_local.npz').relative_to(ROOT))]
    manifest=json.loads((ROOT/'experiments/swarm_tiegcm_2022_observation_v1/downloads.json').read_text())
    for e in [manifest['product'],*manifest['members']]:assert sha(ROOT/e['path'])==e['SHA256']
    raw,_=read_observation(next((ROOT/'data/raw/swarm_tiegcm_2022_observation_v1').glob('*.cdf')))
    np.testing.assert_array_equal(raw['density'],old['observed']);np.testing.assert_array_equal(raw['utc'],old['utc']);np.testing.assert_array_equal(raw['quality'],old['quality'])
    values=np.full((4,4,len(raw['utc'])),np.nan);values[:,:2]=old['values'];coords=old['coords'];queries=[]
    for gi,group in [(2,'A14'),(3,'B14')]:
        folder=F/group;j=json.loads((folder/'data_audit.json').read_text());entries=[e for e in j['files'] if e['file'].startswith('secondary') and any('2022-03-24' in t or '2022-03-25T00:00' in t for t in e['UTC'])]
        p=HourlyTiegcmObservation([folder/e['file'] for e in entries],{e['file']:e['SHA256'] for e in entries},'2022-03-24','2022-03-25',group)
        for mi,ma in enumerate('ABDE'):
            for i,t in enumerate(Time(raw['utc'])):
                if not raw['quality'][i]:continue
                r=p.query_native(t,*coords[i,mi],datum=DATUM)
                if r.valid:values[mi,gi,i]=r.rho_kg_m3
                queries.append(dict(group=group,mapping=ma,sample=i,UTC=str(raw['utc'][i]),valid=r.valid,reason=r.reason,rho_kg_m3=r.rho_kg_m3,top_margin_m=r.metadata.get('top_margin_m')))
    common=paired_valid_mask(raw['quality'],*values.reshape(16,-1));metrics=[];counts=[];improvements=[]
    for mi,ma in enumerate('ABDE'):
        for gi,group in enumerate(['A7','B7','A14','B14']):
            for region,mask in strata(raw['latitude'],raw['altitude'],raw['utc']).items():metrics.append(dict(year=2022,mapping=ma,group=group,region=region,**metric_row(values[mi,gi],raw['density'],raw['quality'],common,mask)))
            failures={}
            for r in queries:
                if r['mapping']==ma and r['group']==group and not r['valid']:failures[r['reason']]=failures.get(r['reason'],0)+1
            counts.append(dict(mapping=ma,group=group,quality=int(raw['quality'].sum()),own_valid=int(np.isfinite(values[mi,gi]).sum()),common=int(common.sum()),failed_reasons=json.dumps(failures)))
        for name,ia,ib in [('A14_vs_A7',0,2),('B14_vs_B7',1,3)]:
            a,b=[compare_density(values[mi,g,common],raw['density'][common]) for g in [ia,ib]]
            improvements.append(dict(mapping=ma,pair=name,n=int(common.sum()),RMSE_7=a['RMSE'],RMSE_14=b['RMSE'],RMSE_reduction_pct=100*(1-b['RMSE']/a['RMSE']),relative_RMS_7=a['relative_RMS'],relative_RMS_14=b['relative_RMS'],relative_RMS_reduction_pct=100*(1-b['relative_RMS']/a['relative_RMS'])))
    h.csvout(out/'metrics.csv',metrics);h.csvout(out/'coverage.csv',counts);h.csvout(out/'improvements.csv',improvements);h.csvout(out/'queries_local.csv',queries)
    np.savez_compressed(out/'aligned_local.npz',values=values,observed=raw['density'],quality=raw['quality'],common=common,utc=raw['utc'],coords=coords)
    old21=np.load(ROOT/'results/swarm_tiegcm_2021_spinup_observation_v1/aligned_local.npz');jointmetrics=[]
    for year,arr,obs,quality,mask in [(2021,old21['values'],old21['observed'],old21['quality'],old21['common']),(2022,values,raw['density'],raw['quality'],common)]:
        for mi,ma in enumerate('ABDE'):
            for gi,group in enumerate(['A7','B7','A14','B14']):jointmetrics.append(dict(year=year,mapping=ma,group=group,**metric_row(arr[mi,gi],obs,quality,mask,np.ones(len(mask),bool))))
    h.csvout(out/'joint_year_metrics.csv',jointmetrics)
    dump(F/'observation_audit.json',dict(new_native_queries=len(queries),common=int(common.sum()),quality=int(raw['quality'].sum()),old_A7_B7_not_requeried=True,new_download_bytes=0,raw_SHA=manifest['product']['SHA256'],wall_s=time.perf_counter()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
    print('Four-state observation comparison completed',int(common.sum()))
if __name__=='__main__':main()
