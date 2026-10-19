"""Prepare/run/audit B1, then gate B2. Never reruns the continuous reference."""
from pathlib import Path
import argparse,importlib.util,sys,json,re,shutil,resource,os,signal,time,socket,getpass,csv
import numpy as np
from netCDF4 import Dataset,num2date
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from atmosphere.restart_validation import REQUIRED,inspect_restart,compare_arrays
from atmosphere.tiegcm_drivers import GpiDriver
spec=importlib.util.spec_from_file_location('crossday_runner',ROOT/'scripts/run_tiegcm2023_crossday.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
REF=ROOT/'experiments/tiegcm2023_crossday_24h10_v1'
CHECKPOINT_SHA='d0aab5804eeab7680977f0fa9ad1de165600fd884bde2ddc1e0c6754c5ab9a4f'
SPECS={'B1':{'start':[77,23,50],'stop':[78,0,0],'reference':'primary_003.nc','secondary_index':1},
       'B2':{'start':[78,0,0],'stop':[78,0,10],'reference':'primary_004.nc','secondary_index':2}}

def require_B1_pass(check):
    if check.get('all_gates_pass') is not True:raise ValueError('B1 failed; B2 prohibited')

def inside(p):return c.startup.inside(p)
def sha(p):return c.startup.sha(p)

def unit_rule(unit):
    # Existing thresholds remain unchanged; additional unit classes are frozen
    # before either model run. Scale native quantities into SI.
    return {'K':(1.,1e-8,'K'),'cm/s':(.01,1e-8,'m/s'),'cm':(.01,1e-5,'m'),
            'mmr':(1.,1e-12,'1'),'MMR':(1.,1e-12,'1'),
            'cm-3':(1e6,1e-6,'m-3'),'s-1':(1.,1e-14,'s-1'),
            'volts':(1.,1e-8,'V'),'g/cm3':(1000.,1e-25,'kg/m3')}[unit]

def configuration(stage):
    sp=SPECS[stage];text=c.startup.configuration()
    text=re.sub(r'(?m)^\s*SOURCE(?:_START)?\s*=.*\n','',text)
    text=re.sub(r'(?m)^\s*LABEL\s*=.*$',f" LABEL = '2023 native continuation {stage}; no cold reinitialization request'",text)
    vals={'START_DAY':str(sp['start'][0]),'START':' '.join(map(str,sp['start'])),
          'STOP':' '.join(map(str,sp['stop'])),'HIST':'0 0 10',
          'OUTPUT':"'branch_primary_001.nc'",'MXHIST_PRIM':'3',
          'SECSTART':' '.join(map(str,sp['stop'])),'SECSTOP':' '.join(map(str,sp['stop'])),
          'SECHIST':'0 0 10','SECOUT':"'branch_secondary_001.nc'"}
    for key,val in vals.items():
        text,n=re.subn(rf'(?m)^\s*{key}\s*=.*$',f' {key} = {val}',text);assert n==1,key
    return text

def validate_config(text,stage):
    if text!=configuration(stage):raise ValueError('Only reviewed native continuation configuration allowed')
    if re.search(r'(?im)^\s*(SOURCE|SOURCE_START|F107|F107A|KP|POWER|CTPOTEN)(?:_TIME)?\s*=',text):
        raise ValueError('SOURCE or driver override forbidden')
    assert (c.seconds(SPECS[stage]['stop'])-c.seconds(SPECS[stage]['start']))==600

def inspect_seed(path,start):
    row=inspect_restart(path,start)
    if not row['structure_complete'] or not row['record_available']:raise ValueError('Incomplete or ambiguous restart')
    with Dataset(path) as n:
        times=np.asarray(n['mtime'][:],dtype=int)
        if any(c.seconds(t)>c.seconds(start) for t in times):raise ValueError('Future records in OUTPUT seed')
        assert np.all(n['year'][:]==2023)
        for name in REQUIRED:unit_rule(n[name].units)
    return row

def read_field(v,index):
    v.set_auto_mask(False);raw=np.asarray(v[index]);mask=np.zeros(raw.shape,bool)
    for attr in ['_FillValue','missing_value']:
        if attr in v.ncattrs():
            for marker in np.asarray(v.getncattr(attr)).reshape(-1):mask|=raw==np.asarray(marker,dtype=raw.dtype)
    mask|=abs(raw)>1e30
    return raw,mask

def compare_variable(reference,candidate,name,ri,ci):
    x=reference[name];y=candidate[name]
    if x.dimensions!=y.dimensions or x.dtype!=y.dtype or x.units!=y.units:
        raise ValueError(f'Schema mismatch: {name}')
    scale,atol,si=unit_rule(x.units);a,ma=read_field(x,ri);b,mb=read_field(y,ci)
    rtol=1e-10 if x.dtype==np.dtype('float64') else 1e-6
    m=compare_arrays(a,b,ma,mb,atol=atol,rtol=rtol,scale=scale)
    return {'variable':name,'native_unit':x.units,'SI_unit':si,'dtype':str(x.dtype),
            'atol_SI':atol,'rtol':rtol,**m}

def init_suite(suite):
    if suite.exists():return
    pre=c.startup.preflight()
    assert sha(REF/'primary_002.nc')==CHECKPOINT_SHA
    assert shutil.disk_usage(ROOT).free>20*1024**3
    protected={}
    for base in ['third_party/TIEGCM2.0','data','experiments','results','reports']:
        for path in (ROOT/base).rglob('*'):
            if path.is_file() and not path.is_symlink():protected[str(path.relative_to(ROOT))]=sha(path)
    suite.mkdir();(suite/'protected_files.json').write_text(json.dumps(protected,indent=2)+'\n')
    with Dataset(REF/'primary_002.nc') as n:
        rules={name:{'native_unit':n[name].units,'scale_to_SI':unit_rule(n[name].units)[0],
                     'atol_SI':unit_rule(n[name].units)[1],'SI_unit':unit_rule(n[name].units)[2],'rtol':1e-10} for name in REQUIRED}
    (suite/'frozen_comparison_rules.json').write_text(json.dumps(rules,indent=2)+'\n')
    (suite/'suite_preflight.json').write_text(json.dumps({**pre,'total_output_budget_bytes':512*1024**2,
        'estimated_two_branch_output_bytes':120*1024**2,'wall_per_launch_s':90,'cpu_per_process_s':120,
        'allowed_stages':['B1','B2'],'require_B1_audit_pass_before_B2':True},indent=2)+'\n')

def prepare(suite,stage):
    init_suite(suite);out=inside(ROOT/'experiments'/f'{suite.name}_{stage}')
    if out.exists():raise FileExistsError(out)
    if stage=='B1':seed=REF/'primary_002.nc'
    else:
        b1=ROOT/'experiments'/f'{suite.name}_B1'
        check=json.loads((b1/'audit.json').read_text())
        require_B1_pass(check)
        seed=b1/'branch_primary_001.nc'
        assert sha(seed)==check['output_primary_sha256']
    sp=SPECS[stage];inspect_seed(seed,sp['start']);text=configuration(stage);validate_config(text,stage)
    out.mkdir();copied=out/'branch_primary_001.nc';shutil.copyfile(seed,copied)
    assert sha(seed)==sha(copied)
    (out/'input.inp').write_text(text)
    (out/'preflight.json').write_text(json.dumps({'stage':stage,'seed':str(seed.relative_to(ROOT)),
        'seed_sha256':sha(seed),'copied_sha256':sha(copied),'input_sha256':sha(out/'input.inp'),
        'seed_inspection':inspect_seed(copied,sp['start']),'original_seed_must_remain_unchanged':True,
        'free_disk_bytes':shutil.disk_usage(ROOT).free,'meminfo':Path('/proc/meminfo').read_text().splitlines()[:3],
        'static_pass':True},indent=2)+'\n');print('STATIC PASS',out)

def limits():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3));resource.setrlimit(resource.RLIMIT_FSIZE,(512*1024**2,512*1024**2))

def execute(suite,stage):
    out=ROOT/'experiments'/f'{suite.name}_{stage}';pre=json.loads((out/'preflight.json').read_text())
    validate_config((out/'input.inp').read_text(),stage)
    assert sha(out/'input.inp')==pre['input_sha256']
    assert sha(out/'branch_primary_001.nc')==pre['copied_sha256'] and sha(ROOT/pre['seed'])==pre['seed_sha256']
    now=c.startup.preflight();old=json.loads((suite/'suite_preflight.json').read_text())
    for k in ['executable_sha256','gpi_sha256','restart_sha256','apex_sha256']:assert now[k]==old[k]
    assert shutil.disk_usage(ROOT).free>20*1024**3
    if stage=='B2':require_B1_pass(json.loads((ROOT/'experiments'/f'{suite.name}_B1'/'audit.json').read_text()))
    with (out/'launch_once.json').open('x') as f:json.dump({'stage':stage,'model_launches':1,'no_retry':True},f)
    env=dict(os.environ,OMPI_ALLOW_RUN_AS_ROOT='1',OMPI_ALLOW_RUN_AS_ROOT_CONFIRM='1',OMPI_MCA_pml='ob1',
        OMPI_MCA_btl='self,tcp',OMPI_MCA_osc='rdma',PMIX_MCA_gds='hash',HOST=socket.gethostname(),LOGNAME=getpass.getuser(),OMP_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='')
    start=time.perf_counter();peak=0;reason=None;logpath=ROOT/'logs'/f'{suite.name}_{stage}.log'
    with logpath.open('x') as log:
        proc=__import__('subprocess').Popen(['mpirun','-np','4',str(c.startup.BUILD/'tiegcm2.0'),'input.inp'],cwd=out,
                env=env,stdout=log,stderr=__import__('subprocess').STDOUT,start_new_session=True,preexec_fn=limits)
        while proc.poll() is None:
            rss=c.process_tree_rss(proc.pid);peak=max(peak,rss)
            size=sum(f.stat().st_size for folder in [suite,ROOT/'experiments'/f'{suite.name}_B1',ROOT/'experiments'/f'{suite.name}_B2'] if folder.exists() for f in folder.rglob('*') if f.is_file())
            size+=sum(p.stat().st_size for p in (ROOT/'logs').glob(suite.name+'*.log'))
            if time.perf_counter()-start>90:reason='wall_timeout'
            elif rss>16*1024**3:reason='rss_limit'
            elif size>512*1024**2:reason='suite_output_limit'
            elif shutil.disk_usage(ROOT).free<20*1024**3:reason='disk_floor'
            if reason:os.killpg(proc.pid,signal.SIGKILL);break
            time.sleep(.1)
        proc.wait()
    status={'returncode':proc.returncode,'elapsed_s':time.perf_counter()-start,'stop_reason':reason,
            'peak_sampled_tree_rss_bytes':peak,'normal_exit_count':logpath.read_text().count('NORMAL EXIT'),
            'original_seed_unchanged':sha(ROOT/pre['seed'])==pre['seed_sha256'],'model_launches':1}
    (out/'run_status.json').write_text(json.dumps(status,indent=2)+'\n');print(json.dumps(status,indent=2))
    if proc.returncode or reason:raise SystemExit(1)

def audit(suite,stage):
    out=ROOT/'experiments'/f'{suite.name}_{stage}'
    if (out/'audit.json').exists():raise FileExistsError('Audit exists')
    sp=SPECS[stage];status=json.loads((out/'run_status.json').read_text());pre=json.loads((out/'preflight.json').read_text())
    rows=[];structural=[];driver_rows=[]
    with Dataset(out/'branch_primary_001.nc') as n,Dataset(REF/sp['reference']) as ref:
        m=np.asarray(n['mtime'][:],dtype=int);target=np.array(sp['stop']);hits=np.flatnonzero((m==target).all(axis=1))
        assert len(hits)==1 and len(m)==len({tuple(t) for t in m}) and all(c.seconds(t)<=c.seconds(target) for t in m)
        ci=int(hits[0]);assert np.array_equal(ref['mtime'][0],target)
        assert int(n['year'][ci])==2023 and int(n['day'][ci])==target[0]
        assert int(n['iter'][ci])==target[0]*1440+target[1]*60+target[2]
        assert str(num2date(n['time'][ci],n['time'].units))==str(num2date(ref['time'][0],ref['time'].units))
        for grid in ['lat','lon','lev','ilev']:assert np.array_equal(n[grid][:],ref[grid][:])
        for k in ['initial_year','initial_day','initial_mtime']:assert np.array_equal(n['time'].getncattr(k),ref['time'].getncattr(k))
        for name in REQUIRED:rows.append({'group':'primary_endpoint',**compare_variable(ref,n,name,0,ci)})
        # Saved start record must remain exactly equal to the source after append.
        with Dataset(ROOT/pre['seed']) as seed:
            si=int(np.flatnonzero((np.asarray(seed['mtime'][:])==sp['start']).all(axis=1))[0])
            ni=int(np.flatnonzero((m==sp['start']).all(axis=1))[0])
            for name in REQUIRED:
                x,mx=read_field(seed[name],si);y,my=read_field(n[name],ni)
                assert np.array_equal(x,y,equal_nan=True) and np.array_equal(mx,my),name
    driver=GpiDriver(c.startup.GPI)
    for file in ['branch_primary_001.nc','branch_secondary_001.nc']:
        with Dataset(out/file) as n:
            for i,m in enumerate(np.asarray(n['mtime'][:],dtype=int)):
                expected=driver.at(2023000+int(m[0]),int(m[1])*3600+int(m[2])*60)
                diff={k:float(n[k][i])-v for k,v in expected.items()};assert max(map(abs,diff.values()))<1e-10
                driver_rows.append({'file':file,'mtime':m.tolist(),'max_driver_abs_error':max(map(abs,diff.values()))})
    with Dataset(out/'branch_secondary_001.nc') as n,Dataset(REF/'secondary_001.nc') as ref:
        assert np.array_equal(n['mtime'][:],[sp['stop']])
        for name in ['DEN','ZG','TN','UN','VN','O1','O2','N2','HE']:
            rows.append({'group':'secondary_endpoint',**compare_variable(ref,n,name,sp['secondary_index'],0)})
        den,mask=read_field(n['DEN'],0);zg,zmask=read_field(n['ZG'],0)
        assert not mask.any() and not zmask.any() and np.isfinite(den).all() and (den>0).all() and (np.diff(zg,axis=0)>0).all()
    log=(ROOT/'logs'/f'{suite.name}_{stage}.log').read_text()
    assert log.count('NORMAL EXIT')==4 and status['returncode']==0 and status['stop_reason'] is None
    assert re.search(r'nstep=\s*10 step=\s*60',log)
    assert not re.search(r'(?im)^.*(?:\bNaN\b|\bInf\b|WARNING|ERROR|bad isec_req).*$',log)
    csvpath=ROOT/'results/metrics'/f'{suite.name}_{stage}_errors.csv'
    with csvpath.open('x',newline='') as f:
        keys=list(rows[0]);w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
    failed=[x['variable'] for x in rows if not x['passed']]
    original_ok=sha(ROOT/pre['seed'])==pre['seed_sha256']
    result={'stage':stage,'primary_variables_compared':34,'secondary_variables_compared':9,'rows':rows,
            'failed_variables':failed,'all_gates_pass':not failed and original_ok,'time_and_driver_pass':True,
            'driver_checks':driver_rows,'original_seed_unchanged':original_ok,
            'output_primary_sha256':sha(out/'branch_primary_001.nc'),'runtime_status':status}
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['rows','driver_checks']},indent=2))
    if not result['all_gates_pass']:raise SystemExit(2)

def main():
    p=argparse.ArgumentParser();p.add_argument('--suite-tag',required=True);p.add_argument('--stage',choices=['B1','B2'],required=True)
    g=p.add_mutually_exclusive_group();g.add_argument('--execute',action='store_true');g.add_argument('--audit',action='store_true');a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+',a.suite_tag):raise ValueError('Bad tag')
    suite=inside(ROOT/'experiments'/a.suite_tag)
    if a.execute:execute(suite,a.stage)
    elif a.audit:audit(suite,a.stage)
    else:prepare(suite,a.stage)
if __name__=='__main__':main()
