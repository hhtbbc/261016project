"""One authorized smax run; reuse 2022 supervisor without editing legacy code."""
from pathlib import Path
import sys,importlib.util,json,re,os,shutil,argparse,datetime,difflib
import numpy as np
from netCDF4 import Dataset
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from atmosphere.restart_validation import REQUIRED,inspect_restart,check_source_clock
from atmosphere.tiegcm_drivers import GpiDriver
from run_tiegcm_mar23_2021_longrun import stream_sha
spec=importlib.util.spec_from_file_location('isolated_2022_supervisor',ROOT/'scripts/run_tiegcm_mar23_2022_longrun.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
TAG='tiegcm_2022_dual_initial_spinup_v1';F=ROOT/'experiments'/TAG;A=ROOT/'experiments/tiegcm_training_mar23_v2_2022_longrun'
SOURCE=ROOT/'data/raw/tiegcm_2021_spinup_initial_condition_v1/tiegcm_res5.0_mareqx_smax_prim.nc'
m.__file__=__file__;m.s.sha=stream_sha

def dump(p,obj):
    m.s.inside(p)
    with p.open('x') as f:json.dump(obj,f,indent=2,allow_nan=False);f.write('\n')
def configuration():
    original=(A/'input.inp').read_text();assert stream_sha(A/'input.inp')==json.loads((A/'preflight.json').read_text())['input_sha256']
    old=str(m.s.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc');assert original.count(old)==1
    return original.replace(old,str(SOURCE))
def validate(text):
    if text!=configuration():raise ValueError('Only SOURCE path may change')
    assert 'START_YEAR = 2022' in text and 'SOURCE_START = 80 0 0' in text
    if re.search(r'(?im)^\s*(F107|F107A|KP|POWER|CTPOTEN)(?:_TIME)?\s*=',text):raise ValueError('Driver override')
    p,q=m.schedules();assert len(p)==10 and len(q)==9 and len(sum(q,[]))==216

def source_audit():
    provenance=json.loads((ROOT/'experiments/tiegcm_2021_spinup_initial_condition_v1/initial_state_audit.json').read_text())
    assert stream_sha(SOURCE)==provenance['B_SHA256'];check_source_clock([75,0,0],[80,0,0])
    audit=inspect_restart(SOURCE,[80,0,0]);assert audit['structure_complete'] and audit['record_available']
    schemas={}
    with Dataset(m.s.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc') as a,Dataset(SOURCE) as b:
        assert b.history_type=='primary' and np.array_equal(b['year'][:],[2002]) and np.array_equal(b['mtime'][:],[[80,0,0]])
        for k in ['lat','lon','lev','ilev']:np.testing.assert_array_equal(a[k][:],b[k][:])
        for k in REQUIRED:
            assert a[k].dimensions==b[k].dimensions and a[k].dtype==b[k].dtype==np.dtype('float64') and getattr(a[k],'units',None)==getattr(b[k],'units',None)
            av,bv=m.field(a[k]),m.field(b[k]);np.testing.assert_array_equal(np.ma.getmaskarray(av),np.ma.getmaskarray(bv));assert bv.count()>0
            schemas[k]=dict(dimensions=b[k].dimensions,unit=getattr(b[k],'units',None),dtype=str(b[k].dtype),valid_min=float(bv.min()),valid_max=float(bv.max()),masked=int(np.ma.getmaskarray(bv).sum()))
    return dict(**audit,SHA256=stream_sha(SOURCE),source_year=2002,actual_run_year=2022,source_start=[80,0,0],required_count=len(REQUIRED),schemas=schemas,provenance=json.loads((ROOT/'experiments/tiegcm_2021_spinup_initial_condition_v1/second_initial_download.json').read_text()),source_not_relabelled=True)

def preflight():
    pre=m.s.preflight();sa=source_audit();drv=GpiDriver(m.s.GPI)
    for minute in range(12961):
        sec=75*86400+minute*60;d=drv.at(2022000+sec//86400,sec%86400)
        assert all(np.isfinite(v) for v in d.values()) and d['f107d']>0 and d['f107a']>0 and 0<=d['Kp']<=9
    for e in json.loads((A/'data_audit.json').read_text())['files']:assert stream_sha(A/e['file'])==e['SHA256']
    history=json.loads((A/'run_status.json').read_text());estimate=history['elapsed_s'];available=int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1])*1024
    assert available>16*2**30 and len(os.sched_getaffinity(0))>=4 and shutil.disk_usage(ROOT).free>=20*2**30
    assert estimate*1.5<3600 and history['netcdf_bytes']<5*2**30
    assert not any('tiegcm2.0' in p.read_text(errors='ignore') for p in Path('/proc').glob('[0-9]*/comm') if p.exists())
    return dict(**{k:v for k,v in pre.items() if k!='restart_sha256'},restart_sha256=sa['SHA256'],source_path=str(SOURCE.relative_to(ROOT)),expected_steps=12960,primary_records=10,secondary_records=216,primary_files=10,secondary_files=9,estimated_wall_s=estimate,estimated_safety_wall_s=estimate*1.5,estimated_netcdf_bytes=history['netcdf_bytes'],estimated_RSS_bytes=history['peak_sampled_tree_rss_bytes'],wall_limit_s=3600,aggregate_rss_limit_bytes=16*2**30,generated_limit_bytes=5*2**30,volume_limit_bytes=256*2**20,mem_available_bytes=available,cpu_affinity_count=len(os.sched_getaffinity(0)),frozen_comparison_rules_SHA256=stream_sha(F/'frozen_comparison_rules.json'),static_pass=True)

def prepare():
    if F.exists():raise FileExistsError(F)
    F.mkdir();rules=json.loads((ROOT/'experiments/tiegcm_2021_spinup_initial_condition_v1/frozen_comparison_rules.json').read_text())
    rules.update(candidate_window_UTC=['2022-03-23T00:00:00Z','2022-03-25T00:00:00Z'],last24h_UTC=['2022-03-24T00:00:00Z','2022-03-25T00:00:00Z'],candidate_hourly_frames=49,last24h_hourly_frames=25,optional_short_launch_limit=0,new_B_launch_limit=1,comparison_sign='B minus A; baseline A is numerical reference, not truth')
    dump(F/'frozen_comparison_rules.json',rules);dump(F/'initial_state_audit.json',source_audit())
    text=configuration();validate(text);(F/'input.inp').open('x').write(text)
    dump(F/'configuration_diff.json',dict(only_changed_namelist_field='SOURCE',output_identity='independent cwd; original LABEL retained without physical effect',diff=list(difflib.unified_diff((A/'input.inp').read_text().splitlines(),text.splitlines(),fromfile='A7/input.inp',tofile='B7/input.inp')),source_start_unchanged=True))
    pre=preflight();pre.update(input_sha256=stream_sha(F/'input.inp'),runner_sha256=stream_sha(Path(__file__)),supervisor_sha256=stream_sha(ROOT/'scripts/run_tiegcm_mar23_2022_longrun.py'))
    protected={}
    for folder in [A,ROOT/'results/swarm_tiegcm_2022_observation_v1',ROOT/'experiments/swarm_tiegcm_2022_observation_v1',ROOT/'data/raw/swarm_tiegcm_2022_observation_v1',ROOT/'results/tiegcm_2021_spinup_initial_condition_v1',ROOT/'results/tiegcm_2021_spinup_14day_v1']:
        for p in folder.rglob('*'):
            if p.is_file():m.s.inside(p);protected[str(p.relative_to(ROOT))]=stream_sha(p)
    protected[str(SOURCE.relative_to(ROOT))]=stream_sha(SOURCE)
    for year in [2021,2022]:
        for e in json.loads((ROOT/f'experiments/tiegcm_training_mar23_v2_{year}_longrun/candidate_audit.json').read_text())['frames']:
            p=ROOT/e['file'];assert stream_sha(p)==e['SHA256'];protected[e['file']]=e['SHA256']
    for p in [ROOT/'scripts/run_tiegcm_mar23_2022_longrun.py',m.s.BUILD/'tiegcm2.0',m.s.BUILD/'apex.F90',m.s.GPI]:protected[str(p.relative_to(ROOT))]=stream_sha(p)
    dump(F/'protected_files.json',protected);dump(F/'preflight.json',pre)
    print(json.dumps({k:v for k,v in pre.items() if 'expected_drivers'!=k},indent=2))

m.configuration=configuration;m.validate=validate;m.preflight=preflight
if __name__=='__main__':
    arg=argparse.ArgumentParser();arg.add_argument('--execute',action='store_true');a=arg.parse_args()
    m.execute(F) if a.execute else prepare()
