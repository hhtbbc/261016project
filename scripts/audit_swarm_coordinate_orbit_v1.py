"""Independent closure/provenance checks and cached-height metadata review."""
from pathlib import Path
import csv,json,sys,time,resource,zipfile,collections
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from prepare_fourcastden_swarm_observation_v1 import sha,dump,inside
from analyze_fourcastden_swarm_observation_v1 import table,FIELDS,MODELS
from PIL import Image
F=ROOT/'experiments/swarm_coordinate_orbit_readiness_v1';O=ROOT/'results/swarm_coordinate_orbit_readiness_v1';PRIOR=ROOT/'results/fourcastden_swarm_observation_v1'


def main():
    begin=time.perf_counter();b=list(csv.DictReader((O/'residual_budget.csv').open()));verified=0
    hour=[];largest=[]
    for day in ('2023-01-04','2023-03-24'):
        with np.load(PRIOR/(day+'_aligned_local.npz')) as n:
            v=n['predictions'];valid=n['valid'];obs=n['observed'];h=n['hours'];good=n['quality'];co=n['coordinates']
        common=good&valid[:2].all(axis=(0,1))
        for r in b:
            if r['date']!=day:continue
            mp='AB'.index(r['mapping']);idx=FIELDS.index(r['model']+'_'+r['scheme']);lat=co[:,0,0]
            rm={'global':np.ones(len(h),bool),'south':lat<=-60,'north':lat>=60,'midlow':abs(lat)<60}[r['region']]
            mask=common&rm&(((h>=1)&(h<7)) if r['period']=='pre' else ((h>=8)&(h<=13)))
            a,t,o=v[mp,idx,mask],v[mp,0,mask],obs[mask];x=a-t;y=t-o;z=a-o
            # Independent dot products; all three terms same sample IDs.
            np.testing.assert_allclose(np.dot(z,z)/len(z),float(r['MSE_AI_TIE'])+float(r['MSE_TIE_Swarm'])+float(r['cross_term']),rtol=1e-12,atol=1e-39)
            np.testing.assert_allclose(np.dot(z/o,z/o)/len(z),float(r['relative_MSE_AI_TIE'])+float(r['relative_MSE_TIE_Swarm'])+float(r['relative_cross_term']),rtol=1e-12,atol=1e-14)
            verified+=1
        g=list(csv.DictReader((O/(day+'_geometry_local.csv')).open()))
        for hh in range(1,13):
            rr=[r for r in g if hh<=1+int(r['sample'])/120<hh+1]
            norm=np.array([float(r['position_difference_m']) for r in rr]);dh=np.array([float(r['height_difference_GRS80_m']) for r in rr])
            hour.append(dict(date=day,hour_UTC=hh,n=len(rr),position_RMS_m=float(np.sqrt(np.mean(norm**2))),position_max_m=float(norm.max()),height_RMS_m=float(np.sqrt(np.mean(dh**2))),height_abs_max_m=float(abs(dh).max())))
        for r in sorted(g,key=lambda r:float(r['position_difference_m']),reverse=True)[:5]:largest.append(dict(date=day,UTC=r['UTC'],position_difference_m=r['position_difference_m'],height_difference_m=r['height_difference_GRS80_m'],interpretation='ranked descriptive extremes, not rejected quality samples'))
    table(O/'geometry_hourly_summary.csv',hour);table(O/'largest_geometry_differences.csv',largest)
    # Existing metadata records native-height stencil bounds separately from
    # physical density differences. No height or density queries are repeated.
    ref={};group=collections.defaultdict(list)
    with (PRIOR/'queries_local.csv').open() as f:
        for r in csv.DictReader(f):
            if r['mapping'] in ('A','B') and r['field']=='Reference':ref[(r['date'],r['mapping'],r['sample'])]=r
    with (PRIOR/'queries_local.csv').open() as f:
        for r in csv.DictReader(f):
            if r['mapping'] not in ('A','B') or r['field']=='Reference' or r['valid']!='True':continue
            hh=1+int(r['sample'])/120
            if not 8<=hh<=13:continue
            base=ref[(r['date'],r['mapping'],r['sample'])]
            if base['valid']!='True':continue
            key=(r['date'],r['mapping'],r['field'])
            group[key].append((float(r['height_lower_m'])-float(base['height_lower_m']),float(r['height_upper_m'])-float(base['height_upper_m'])))
    rows=[]
    for (day,mp,field),a in group.items():
        x=np.array(a);rows.append(dict(date=day,mapping=mp,field=field,valid_own_samples=len(a),lower_stencil_bound_difference_P95_m=float(np.quantile(abs(x[:,0]),.95)),
            upper_stencil_bound_difference_P95_m=float(np.quantile(abs(x[:,1]),.95)),
            meaning='AI reconstructed vs reference stencil height range; not isolated height error at satellite, no density attribution'))
    table(O/'cached_height_representation.csv',rows)
    protected=json.loads((F/'protected.json').read_text());assert all(sha(ROOT/p)==h for p,h in protected.items())
    old=json.loads((ROOT/'experiments/tiegcm_runtime_restart_audit_v1/protected_files.json').read_text());assert all(sha(ROOT/p)==h for p,h in old.items())
    for rec in json.loads((F/'download_manifest.json').read_text()):
        with zipfile.ZipFile(ROOT/rec['path']) as z:
            assert z.testzip() is None
            for m in rec['members']:assert (ROOT/m['path']).read_bytes()==z.read(Path(m['path']).name)
    failed=list(csv.DictReader((O/'Flow_failed_samples.csv').open()));assert sum(r['date']=='2023-03-24' and r['mapping']=='A' for r in failed)==18
    sources={'DNS_SP3_geometry_alignment':'*_geometry_local.csv','DNS_SP3_geodetic_differences':'*_geometry_local.csv',
        'threeway_density_RMSE':'residual_budget.csv','signed_MSE_cross_term':'residual_budget.csv','time_blocks_and_autocorrelation':'fixed_hour_blocks.csv;descriptive_ACF.csv'}
    figs=[]
    for p in O.glob('*.png'):
        with Image.open(p) as im:im.verify()
        figs.append(dict(figure=p.name,SHA256=sha(p),data=sources[p.stem],generator='scripts/plot_swarm_coordinate_orbit_v1.py',products='SP3 0203/DNS0301; A/B provisional'))
    assert len(figs)==5;table(O/'figure_sources.csv',figs)
    dump(F/'independent_audit.json',dict(budget_cells_independently_verified=verified,identities='signed + MSE and shared-observation-denominator relative MSE',
        input_SHA_unchanged=len(protected),historical_SHA_unchanged=len(old),additional_cached_query_metadata_SHA=sha(PRIOR/'queries_local.csv'),
        PNGs_verified=5,Flow18_failures_retained=True,wall_s=time.perf_counter()-begin,RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        new_density_queries=0,new_forward=0,new_TIE=0,new_orbit=0,REAL_ORBIT_VALIDATION_READY='BLOCKED',SCIENTIFIC_TRAINING_READY=False))
    print((F/'independent_audit.json').read_text())


if __name__=='__main__':main()
