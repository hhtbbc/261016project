"""Read existing DNS/A7; query new B7 once under all frozen coordinate mappings."""
from pathlib import Path
import sys,json,time,resource,csv
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from atmosphere.tiegcm_density_provider import DATUM
from evaluation.swarm_density_comparison import compare_density,paired_valid_mask
from evaluation.swarm_crossyear import metric_row,strata
from run_swarm_tiegcm_2022_observation import read_observation
from prepare_fourcastden_swarm_observation_v1 import sha,dump
from astropy.time import Time
TAG='tiegcm_2022_dual_initial_spinup_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG
OLD=ROOT/'results/swarm_tiegcm_2022_observation_v1'
def table(path,rows):
    with path.open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def main():
    started=time.perf_counter();out=O/'observation';out.mkdir(exist_ok=False)
    protected=json.loads((F/'protected_files.json').read_text());assert sha(OLD/'aligned_local.npz')==protected[str((OLD/'aligned_local.npz').relative_to(ROOT))]
    manifest=json.loads((ROOT/'experiments/swarm_tiegcm_2022_observation_v1/downloads.json').read_text())
    for e in [manifest['product'],*manifest['members']]:assert sha(ROOT/e['path'])==e['SHA256']
    raw,_=read_observation(next((ROOT/'data/raw/swarm_tiegcm_2022_observation_v1').glob('*.cdf')));old=np.load(OLD/'aligned_local.npz')
    for k in ['density','quality','utc']:np.testing.assert_array_equal(raw[k],old[k])
    coords=old['coords'];times=old['utc'];quality=old['quality'];obs=old['density']
    audit=json.loads((F/'data_audit.json').read_text());entries=[e for e in audit['files'] if e['file'].startswith('secondary') and any('2022-03-24' in t or '2022-03-25T00:00' in t for t in e['UTC'])]
    p=HourlyTiegcmObservation([F/e['file'] for e in entries],{e['file']:e['SHA256'] for e in entries},'2022-03-24','2022-03-25','2022_B7_smax')
    values=np.full((4,2,len(times)),np.nan);values[:,0]=old['values'];queries=[]
    for mi,ma in enumerate('ABDE'):
        for i,t in enumerate(Time(times)):
            if not quality[i]:continue
            r=p.query_native(t,*coords[i,mi],datum=DATUM)
            if r.valid:values[mi,1,i]=r.rho_kg_m3
            queries.append(dict(sample=i,UTC=str(times[i]),mapping=ma,valid=r.valid,reason=r.reason,rho_kg_m3=r.rho_kg_m3,top_margin_m=r.metadata.get('top_margin_m')))
    common=paired_valid_mask(quality,*values.reshape(8,-1));metrics=[];counts=[];pairs=[]
    for mi,ma in enumerate('ABDE'):
        for gi,group in enumerate(['A7','B7']):
            for name,mask in strata(raw['latitude'],raw['altitude'],times).items():metrics.append(dict(mapping=ma,group=group,region=name,**metric_row(values[mi,gi],obs,quality,common,mask)))
            failed={}
            if gi:
                for r in queries:
                    if r['mapping']==ma and not r['valid']:failed[r['reason']]=failed.get(r['reason'],0)+1
            counts.append(dict(mapping=ma,group=group,total=len(times),quality=int(quality.sum()),own_valid=int(np.isfinite(values[mi,gi]).sum()),common=int(common.sum()),failed_reasons=json.dumps(failed)))
        pairs.append(dict(mapping=ma,**compare_density(values[mi,1,common],values[mi,0,common])))
        # Signed residual identity on the exact common samples, not addition of RMS.
        a,b=values[mi,0,common],values[mi,1,common];o=obs[common]
        np.testing.assert_allclose((b-o)-(a-o),b-a,rtol=0,atol=1e-27)
        if common.all():
            rr=[r for r in csv.DictReader((OLD/'metrics.csv').open()) if r['year']=='2022' and r['mapping']==ma and r['region']=='all'][0]
            met=compare_density(a,o)
            for k in ['RMSE','MAE','bias','relative_RMS']:assert np.isclose(float(rr[k]),met[k],rtol=1e-13,atol=0)
    table(out/'metrics.csv',metrics);table(out/'coverage.csv',counts);table(out/'queries_local.csv',queries);table(out/'internal_along_track.csv',pairs)
    np.savez_compressed(out/'aligned_local.npz',values=values,observed=obs,quality=quality,common=common,utc=times,coords=coords)
    dump(F/'observation_audit.json',dict(new_B_queries=len(queries),quality=int(quality.sum()),common=int(common.sum()),raw_product_SHA=manifest['product']['SHA256'],old_A_not_requeried=True,all_common_A_metrics_reproduced=bool(common.all()),signed_residual_identity=True,wall_s=time.perf_counter()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
    print('Observation comparison complete',int(common.sum()))
if __name__=='__main__':main()
