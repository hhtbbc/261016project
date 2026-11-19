"""V22 bounded offline generation using unchanged historical builder; no model entry."""
from pathlib import Path
import sys,json,hashlib,datetime,time,resource,csv,subprocess
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R/'scripts')]
import numpy as np
import prepare_tiegcm_training_drivers as old
from atmosphere.autumn_gpi_validation import read_raw,check_file,compare_driver,stamp
F=R/'experiments/thermosphere_autumn_gpi_seed_policy_v22'
V21=R/'experiments/thermosphere_autumn_data_acquisition_v21'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):
    if not p.resolve().is_relative_to(R):raise ValueError('Outside project')
    with p.open('x') as h:json.dump(x,h,indent=2,allow_nan=False)
def sources(year):
    raw=R/'data/raw/thermosphere_autumn_data_acquisition_v21'
    return [R/'data/raw/f107_2021_recovery_v1/gfz_year.txt'] if year==2021 else [raw/'GFZ_Fobs_20220729_20221106.json',raw/'GFZ_Kp_def_20220907_20220927.json']
def adapter(year):
    if year==2022:return tuple(old.decode(json.loads(p.read_text()),k) for p,k in zip(sources(year),['Fobs','Kp']))
    # Literal archive columns/time semantics from successful spring 2021 builder.
    solar={};kp={}
    for line in sources(year)[0].read_text().splitlines():
        a=line.split()
        if not a or a[0]!='2021':continue
        d=datetime.date(*map(int,a[:3]));t=datetime.datetime.combine(d,datetime.time(),datetime.timezone.utc)
        if datetime.date(year,7,29)<=d<=datetime.date(year,11,6):
            if t in solar:raise ValueError('Duplicate Fobs')
            solar[t]=float(a[25])
        if datetime.date(year,9,7)<=d<=datetime.date(year,9,27):
            if a[27]!='2':raise ValueError('Non-def archive')
            for j in range(8):
                u=t+datetime.timedelta(hours=3*j)
                if u in kp:raise ValueError('Duplicate Kp')
                kp[u]=float(a[7+j])
    return solar,kp

def main():
    begin=time.monotonic();cpu=time.process_time()
    F.mkdir(exist_ok=False)
    protected={}
    for row in json.loads((V21/'raw_asset_protection.json').read_text())['files']:
        p=R/row['path'];assert sha(p)==row['SHA256'];protected[row['path']]=sha(p)
    for name,digest in json.loads((V21/'preflight.json').read_text())['protected_SHA256'].items():
        assert sha(R/name)==digest;protected[name]=digest
    # Freeze all existing tracked V20/V21 artifacts and unchanged physical builder/runtime code.
    for folder in ['thermosphere_autumn_data_acquisition_v21','thermosphere_independent_date_validation_plan_v20']:
        for p in (R/'experiments'/folder).glob('*'):
            if p.is_file() and p.suffix in ['.json','.csv']:protected[str(p.relative_to(R))]=sha(p)
    for name,expected in [('scripts/prepare_tiegcm_training_drivers.py','82fdbf2c4d39f04041013de0b3e5a16bd9d9bbeedd7ee31b6c1c0f9eb7465675'),('src/atmosphere/tiegcm_drivers.py','3bdbd2b576bbf9440be91f84efc6940280bac1b544716b2582e6d3f3196e7f3a')]:
        assert sha(R/name)==expected;protected[name]=expected
    dump(F/'preflight.json',dict(base_HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),protected_SHA256=protected,PASS=True))
    dump(F/'protocol.json',dict(task='V22',mean_abs_strict=1e-12,driver_abs_strict=1e-10,raw_days=21,solar_days=101,Kp_count=168,model_intervals=['2021-09-09/2021-09-25','2022-09-09/2022-09-25'],time='UTC; inclusive source days; query seconds in [0,86400)',builder_SHA256=sha(Path(old.__file__)),formula_changed=False,no_model_launch=True,no_scoring=True))
    summaries={}
    for year in [2021,2022]:
        manifest={str(p.relative_to(R)):sha(p) for p in sources(year)}
        dump(F/f'input_sources_{year}.json',dict(files=manifest,protocol_SHA256=sha(F/'protocol.json'),frozen_before_generation=True))
        try:
            independent_s,independent_k=read_raw(year,sources(year))
            solar,kp=adapter(year)
            assert solar==independent_s and kp==independent_k
            days,f,a,k=old.arrays(solar,kp,datetime.date(year,9,7),datetime.date(year,9,27))
            p=F/f'gpi_{year}_autumn.nc';old.write_gpi(p,days,f,a,k,datetime.date(year,9,9),datetime.date(year,9,25));p.chmod(0o444)
            means,mean_error=check_file(p,independent_s,independent_k,year,R/'experiments/tiegcm_2022_mar25_preparation_v1/gpi_2022_extended.nc')
            audit=compare_driver(old.GpiDriver(p),independent_s,means,independent_k,year)
            audit.update(status='GPI_READY',file=str(p.relative_to(R)),SHA256=sha(p),bytes=p.stat().st_size,raw_dates=[f'{year}-09-07',f'{year}-09-27'],valid_model_interval=[f'{year}-09-09T00:00:00Z',f'{year}-09-25T00:00:00Z'],ndays=21,Kp_nodes=168,Fobs_source_days=101,center81_max_abs=mean_error,schema_matches_spring=True,missing=0,duplicates=0,input_SHA256=manifest)
            assert manifest=={str(q.relative_to(R)):sha(q) for q in sources(year)}
            dump(F/f'gpi_audit_{year}.json',audit);summaries[str(year)]=audit
        except Exception as e:
            dump(F/f'gpi_failure_{year}.json',dict(status='GPI_FAILED',error=repr(e)));summaries[str(year)]=dict(status='GPI_FAILED')
    assert all(sha(R/k)==v for k,v in protected.items())
    dump(F/'asset_protection_after.json',dict(PASS=True,files_checked=len(protected),all_SHA_unchanged=True))
    dump(F/'result.json',dict(years={y:a['status'] for y,a in summaries.items()},initial='SEPEQX_SOURCE_NOT_ACQUIRED',seed_policy='USER_DECISION_PENDING',model_RUN_READY=False,model_launches=0))
    dump(F/'resource_worker.json',dict(wall_seconds=time.monotonic()-begin,CPU_seconds=time.process_time()-cpu,max_self_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,raw_data_download_bytes=0,GPU=0,model_launches=0))
    print(json.dumps({y:{k:a[k] for k in ['status','SHA256','center81_max_abs','max_abs_difference','total_unique_nodes'] if k in a} for y,a in summaries.items()},indent=2))
if __name__=='__main__':main()
