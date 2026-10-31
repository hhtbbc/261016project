"""Final physical-field spot checks, provenance and delivery audit, CPU only."""
from pathlib import Path
import ast,csv,json,sys,time,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from atmosphere.fourcastden_density import reconstruct_native_zg
from run_fourcastden_ideal_update_6h import oldpaths,reference
from audit_fourcastden_coordinate_update_v1 import load
import prepare_fourcastden_swarm_observation_v1 as task
from analyze_fourcastden_swarm_observation_v1 import table,FIELDS
from PIL import Image
F,O,D=task.F,task.O,task.D


def main():
    start=time.perf_counter();lat=np.load(ROOT/'data/processed/static/lat.npy');lon=np.load(ROOT/'data/processed/static/lon.npy');iv=np.load(ROOT/'data/processed/static/ilev.npy')
    checks=[]
    for day in ('2023-01-04','2023-03-24'):
        with np.load(O/(day+'_aligned_local.npz'),allow_pickle=False) as n:values=n['predictions'];coords=n['coordinates'];hours=n['hours']
        tl=np.stack([reference(day,h)[2] for h in range(1,14)])
        for model in ('Direct','Flow','LogDEN','History'):
            for scheme in ('Open','Updated'):
                ph=load(oldpaths(day)[1]/f'{day}_{model}.npz',model) if scheme=='Open' else load(ROOT/'data/processed/fourcastden_ideal_update_6h_v1'/f'{day}_{model}.npz',model)
                zg,valid,mu=reconstruct_native_zg(ph[:,:28],ph[:,142:],ph[:,113:142],tl if scheme=='Open' else tl[6:],lat,iv)
                for sample in (660,720,780,1380): # 06:30,07:00,07:30,12:30 UTC
                    for mp in range(2):
                        fi=FIELDS.index(model+'_'+scheme);old=values[mp,fi,sample]
                        # Updated pre-event explicitly uses the untouched Open.
                        if scheme=='Updated' and hours[sample]<7:continue
                        x=hours[sample]-(1 if scheme=='Open' else 7);k=min(int(np.floor(x)),len(ph)-2);wt=x-k
                        la,lo,h=coords[sample,mp];j=int(np.clip(np.floor((la-lat[0])/5),0,len(lat)-2));wy=(la-lat[j])/5
                        ll=(lo-lon[0])%360+lon[0];i=int(np.floor((ll-lon[0])/5));ii=(i+1)%len(lon);wx=(ll-lon[i])/5
                        rho=0.;ok=True
                        for t,tw in [(k,1-wt),(k+1,wt)]:
                            for y,yw in [(j,1-wy),(j+1,wy)]:
                                for z,zw in [(i,1-wx),(ii,wx)]:
                                    zz=zg[t,:,y,z];rr=ph[t,142:,y,z]*1000
                                    ok &= bool(valid[t,y,z] and zz[0]<=h<=zz[-1])
                                    b=int(np.clip(np.searchsorted(zz,h)-1,0,len(zz)-2));fraction=(h-zz[b])/(zz[b+1]-zz[b])
                                    v=np.exp(np.log(rr[b])+fraction*(np.log(rr[b+1])-np.log(rr[b])))
                                    rho+=tw*yw*zw*v
                        assert ok==np.isfinite(old)
                        if ok:np.testing.assert_allclose(rho,old,rtol=4e-13,atol=1e-26)
                        checks.append(dict(date=day,model=model,scheme=scheme,sample=sample,mapping='AB'[mp],valid=ok,
                            independent_rho=rho if ok else None,cached_rho=old if ok else None,passed=True))
    table(O/'independent_interpolation_spot_checks.csv',checks)
    for p,h in json.loads((F/'protected.json').read_text()).items():assert task.sha(ROOT/p)==h
    figures=[]
    source={'Swarm_TIEGCM_reference_density':'*_aligned_local.npz','four_models_alongtrack_A':'*_aligned_local.npz',
        'observation_error_hourly_A_B':'hourly_metrics.csv','post_update_gain_A_B':'paired_update_changes.csv',
        'regional_observation_update_gain':'paired_update_changes.csv','coordinate_sensitivity_same_track':'geometry_local.csv;*_coordinate_density_sensitivity_local.csv',
        'query_validity_by_model':'query_validity.csv','observation_event_seam':'event_07_left_right_local.csv',
        'calculable_sensitivity_budget':'interpolation_sensitivity_summary.csv'}
    for p in sorted(O.glob('*.png')):
        with Image.open(p) as im:im.verify()
        figures.append(dict(figure=p.name,SHA256=task.sha(p),source=source[p.stem],product='DNSAPOD_0301',UTC_dates='2023-01-04;2023-03-24',
            label='PROVISIONAL_OBSERVATION_COMPARISON',generator='scripts/plot_fourcastden_swarm_observation_v1.py'))
    assert len(figures)==9;table(O/'figure_sources.csv',figures)
    files=[ROOT/'src/evaluation/swarm_density_comparison.py',ROOT/'tests/test_swarm_density_comparison.py']+sorted((ROOT/'scripts').glob('*fourcastden_swarm*.py'))
    for p in files:ast.parse(p.read_text())
    manifest={str(p.relative_to(ROOT)):task.sha(p) for p in files}
    for folder in (F,O,D):
        for p in folder.rglob('*'):
            if p.is_file():manifest[str(p.relative_to(ROOT))]=task.sha(p)
    task.dump(F/'delivery_SHA_manifest.json',manifest)
    size=sum(p.stat().st_size for folder in (F,O) for p in folder.rglob('*') if p.is_file());assert size<500*2**20
    tests=(ROOT/'logs/fourcastden_swarm_observation_v1_tests.log').read_text();assert 'Ran 8 tests' in tests and 'OK' in tests
    task.dump(F/'delivery_audit.json',dict(status='PASS',new_CPU_tests=8,independent_actual_interpolation_checks=len(checks),PNGs=9,
        output_bytes=size,final_audit_wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        raw_observation_upload=False,formal_datum='EXTERNAL_DATUM_UNVERIFIED',real_orbit_READY=False,SCIENTIFIC_TRAINING_READY=False,
        new_GPU_forward=0,new_TIE=0,new_orbit=0))
    print((F/'delivery_audit.json').read_text())


if __name__=='__main__':main()
