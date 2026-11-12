"""Two new 2022 cold-start trajectories; isolated reuse of proven supervisor."""
from pathlib import Path
import sys,json,re,os,shutil,argparse,importlib.util,inspect,difflib,hashlib,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from atmosphere.tiegcm_drivers import GpiDriver
from run_tiegcm_mar23_2021_longrun import stream_sha
import run_tiegcm_2022_dual_initial as initial
spec=importlib.util.spec_from_file_location('isolated_14day_supervisor',ROOT/'scripts/run_tiegcm_2021_14day.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
TAG='tiegcm_2022_spinup_14day_v1';F=ROOT/'experiments'/TAG;A7=ROOT/'experiments/tiegcm_training_mar23_v2_2022_longrun';B7=ROOT/'experiments/tiegcm_2022_dual_initial_spinup_v1';GPI=ROOT/'data/processed'/TAG/'gpi_2022_14day.nc'
GROUP='A14';m.CASE=F;m.__file__=__file__;m.s.YEAR=2022;m.s.sha=stream_sha

def dump(p,j):
    m.s.inside(p)
    with p.open('x') as f:json.dump(j,f,indent=2,allow_nan=False);f.write('\n')
def schedules():
    return (m.series([(68,0,0)],[(84,0,0)],[(1,0,0)],1),m.series([(68,1,0)],[(84,0,0)],[(0,1,0)],24))
def configuration(group=None):
    group=group or GROUP;text=(A7/'input.inp').read_text()
    assert stream_sha(A7/'input.inp')==json.loads((A7/'preflight.json').read_text())['input_sha256']
    changes={'START_DAY':'68','START':'68 0 0','SECSTART':'68 1 0','OUTPUT':', '.join(f"'primary_{i:03d}.nc'" for i in range(1,18)),'SECOUT':', '.join(f"'secondary_{i:03d}.nc'" for i in range(1,17)),'GPI_NCFILE':"'"+str(GPI)+"'"}
    for k,v in changes.items():text,n=re.subn(rf'(?m)^\s*{k}\s*=.*$',f' {k} = {v}',text);assert n==1,k
    if group=='B14':text=text.replace(str(m.s.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc'),str(initial.SOURCE))
    return text

def validate(text):
    if text!=configuration():raise ValueError('Unexpected physical/configuration change')
    assert 'START_YEAR = 2022' in text and 'SOURCE_START = 80 0 0' in text and 'STOP = 84 0 0' in text
    if re.search(r'(?im)^\s*(F107|F107A|KP|POWER|CTPOTEN)(?:_TIME)?\s*=',text):raise ValueError('Driver override')
    p,q=schedules();assert len(p)==17 and len(q)==16 and len(sum(q,[]))==384

def preflight():
    if GROUP=='B14':
        st=json.loads((F/'A14/run_status.json').read_text());assert st['returncode']==0 and st['stop_reason'] is None and st['normal_exit_count']==4
        assert json.loads((F/'A14/data_audit.json').read_text())['engineering_PASS']
    m.s.GPI=ROOT/'data/processed/training_window_mar23_v2/gpi_2022_mar23_v2.nc';pre=m.s.preflight();m.s.GPI=GPI
    driver=json.loads((F/'driver_audit.json').read_text());assert driver['status']=='PASS' and stream_sha(GPI)==driver['SHA256']
    source=initial.SOURCE if GROUP=='B14' else m.s.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc'
    a=initial.source_audit();expected=a['SHA256'] if GROUP=='B14' else '180475215a4922e9c55a77e80153cf641bc8fbb2b8d52633b4686ddee6942fff'
    assert stream_sha(source)==expected
    for folder in [A7,B7]:
        for e in json.loads((folder/'data_audit.json').read_text())['files']:assert stream_sha(folder/e['file'])==e['SHA256']
    drv=GpiDriver(GPI)
    for minute in range(23041):
        sec=68*86400+minute*60;v=drv.at(2022000+sec//86400,sec%86400);assert all(np.isfinite(z) for z in v.values())
    estimate=json.loads((A7/'run_status.json').read_text())['elapsed_s']*16/9 if GROUP=='A14' else json.loads((B7/'run_status.json').read_text())['elapsed_s']*16/9
    available=int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1])*1024;free=shutil.disk_usage(ROOT).free
    assert estimate*1.5<4800 and available>16*2**30 and free>32*2**30 and len(os.sched_getaffinity(0))>=4
    assert not any('tiegcm2.0' in p.read_text(errors='ignore') for p in Path('/proc').glob('[0-9]*/comm') if p.exists())
    if GROUP=='B14':
        elapsed=time.monotonic()-json.loads((F/'pair_launch_once.json').read_text())['started_monotonic'];assert elapsed+estimate*1.5<9600,'Insufficient remaining total supervision budget'
    prim,sec=schedules()
    return dict(**{k:v for k,v in pre.items() if k not in ['gpi_sha256','restart_sha256','year','free_disk_bytes']},year=2022,group=GROUP,gpi_sha256=stream_sha(GPI),restart_sha256=expected,source=str(source.relative_to(ROOT)),frozen_comparison_rules_SHA256=stream_sha(F/'frozen_comparison_rules.json'),expected_steps=23040,expected_primary=17,expected_secondary=384,primary_volumes=17,secondary_volumes=16,primary_volume_seconds=prim,secondary_volume_seconds=sec,estimated_wall_s=estimate,safety_wall_s=estimate*1.5,estimated_netcdf_GiB=3.14,wall_limit_s=4800,total_wall_limit_s=9600,aggregate_rss_limit_bytes=16*2**30,per_group_generated_limit_bytes=5*2**30,total_generated_limit_bytes=12*2**30,volume_limit_bytes=256*2**20,free_disk_bytes=free,mem_available_bytes=available,static_pass=True)

def prepare():
    out=F/GROUP
    if out.exists():raise FileExistsError(out)
    if not (F/'frozen_comparison_rules.json').exists():
        rules=json.loads((B7/'frozen_comparison_rules.json').read_text());rules.update(new_model_launch_limit=2,new_B_launch_limit=1,optional_short_launch_limit=0)
        dump(F/'frozen_comparison_rules.json',rules);dump(F/'initial_state_audit.json',initial.source_audit())
        protected=json.loads((B7/'protected_files.json').read_text())
        for folder in [B7,ROOT/'results/tiegcm_2022_dual_initial_spinup_v1',ROOT/'data/raw/swarm_tiegcm_2022_observation_v1',ROOT/'results/swarm_tiegcm_2021_spinup_observation_v1']:
            for p in folder.rglob('*'):
                if p.is_file():m.s.inside(p);protected[str(p.relative_to(ROOT))]=stream_sha(p)
        dump(F/'protected_files.json',protected)
        aa,bb=configuration('A14'),configuration('B14')
        assert bb.replace(str(initial.SOURCE),str(m.s.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc'))==aa
        dump(F/'configuration_diff.json',dict(A14_vs_B14=list(difflib.unified_diff(aa.splitlines(),bb.splitlines(),fromfile='A14',tofile='B14')),A7_vs_A14=list(difflib.unified_diff((A7/'input.inp').read_text().splitlines(),aa.splitlines(),fromfile='A7',tofile='A14')),allowed_changes=['start day/time','same-year extended GPI with identical overlap','output volume schedule/path identity','initial SOURCE only between A14/B14'],no_physics_changes=True))
    text=configuration();validate(text);pre=preflight();out.mkdir();(out/'input.inp').open('x').write(text)
    pre.update(input_sha256=stream_sha(out/'input.inp'),runner_sha256=stream_sha(Path(__file__)),original_supervisor_SHA256=stream_sha(ROOT/'scripts/run_tiegcm_2021_14day.py'))
    dump(out/'preflight.json',pre);print('STATIC PASS',GROUP,pre['safety_wall_s'])

# Original physics checks and monitor are reused in an isolated namespace.
basic=inspect.getsource(m.basic_file).replace('2021','2022');exec(compile(basic,'<2022 year-only basic-file adapter>','exec'),m.__dict__)
execute=inspect.getsource(m.execute).replace('24480','23040').replace('tiegcm_2021_14day_','tiegcm_2022_14day_')
execute=execute.replace("elif GROUP=='B14' and elapsed+json.loads((CASE/'A14/run_status.json').read_text())['elapsed_s']>9600:reason='total_wall_timeout'","elif time.monotonic()-json.loads((CASE/'pair_launch_once.json').read_text())['started_monotonic']>9600:reason='total_wall_timeout'")
exec(compile(execute,'<2022 supervisor path/count adapter>','exec'),m.__dict__)
m.configuration=configuration;m.validate=validate;m.preflight=preflight;m.schedules=schedules
s=m.s;field=m.field;basic_file=m.basic_file;CASE=F

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--group',choices=['A14','B14'],required=True);p.add_argument('--execute',action='store_true');a=p.parse_args();GROUP=a.group;m.GROUP=GROUP
    if a.execute:m.execute(F/GROUP)
    else:prepare()
