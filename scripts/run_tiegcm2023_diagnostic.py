"""Prepare or execute one fixed ten-minute 2023 diagnostic; never spin up."""
from pathlib import Path
import argparse, hashlib, json, os, re, resource, shutil, signal, socket
import subprocess, time, getpass
import numpy as np
from netCDF4 import Dataset

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'experiments/tiegcm2_apex2023_v1'
GPI=ROOT/'data/processed/tiegcm2023/gpi_20230312_20230325.nc'
SUPPORT=ROOT/'data/raw/tiegcm2_support'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inside(path):
    if not path.resolve().is_relative_to(ROOT):
        raise ValueError(f'Outside workspace: {path}')
    return path

def configuration():
    text=(ROOT/'third_party/TIEGCM2.0/scripts/tiegcm_res5.0_default.inp').read_text()
    replacements={'START_YEAR':'2023','START_DAY':'77','START':'77 0 0',
                  'STOP':'77 0 10','HIST':'0 0 5','SECSTART':'77 0 5',
                  'SECSTOP':'77 0 10','SECHIST':'0 0 5',
                  'LABEL':"'2023-03-18 diagnostic; 2002 numerical initial guess; not spun up'"}
    for key,value in replacements.items():
        text,n=re.subn(rf'(?m)^\s*{key}\s*=.*$',f' {key} = {value}',text)
        if n!=1:raise ValueError(f'Unexpected template field {key}')
    text=re.sub(r'(?m)^\s*(?:F107|F107A|KP|POWER|CTPOTEN)\s*=.*\n','',text)
    text=text.replace('$TGCMDATA',str(SUPPORT))
    text=text.replace("\n/",f"\n GPI_NCFILE = '{GPI}'\n/")
    return text

def validate_config(text):
    expected={'START_YEAR':'2023','START_DAY':'77','SOURCE_START':'80 0 0',
              'START':'77 0 0','STOP':'77 0 10','STEP':'60','CALENDAR_ADVANCE':'1',
              'HIST':'0 0 5','SECSTART':'77 0 5','SECSTOP':'77 0 10','SECHIST':'0 0 5'}
    for key,val in expected.items():
        m=re.findall(rf'(?m)^\s*{key}\s*=\s*(.*?)\s*$',text)
        if m!=[val]:raise ValueError(f'Invalid fixed diagnostic field {key}: {m}')
    if re.search(r'(?im)^\s*(F107|F107A|KP|POWER|CTPOTEN)(?:_TIME)?\s*=',text):
        raise ValueError('Fixed/time-series driver override forbidden')
    if f"GPI_NCFILE = '{GPI}'" not in text or "POTENTIAL_MODEL = 'HEELIS'" not in text:
        raise ValueError('Missing GPI/HEELIS')

def expected_drivers(seconds):
    with Dataset(GPI) as n:
        idx=list(n['year_day'][:]).index(2023077)
        values={}
        # Four-point noon-anchored Lagrange interpolation, same convention as
        # gpi.F, implemented independently using generic polynomial weights.
        x=np.array([-1.,0.,1.,2.]);t=(seconds+43200)/86400
        w=np.array([np.prod([(t-x[j])/(x[i]-x[j]) for j in range(4) if j!=i]) for i in range(4)])
        for var in ['f107d','f107a']:values[var]=float(w@np.asarray(n[var][idx-2:idx+2]))
        kp0=float(n['kp'][idx-1,7]);kp1=float(n['kp'][idx,0])
        kp=kp0+(kp1-kp0)*(seconds+5400)/10800
        values.update(kp=kp,hpower=float(16.82*np.exp(.32*kp)-4.86) if kp<=7 else 153.13+(kp-7)/2*(300-153.13),ctpoten=15+15*kp+.8*kp**2)
        return values

def preflight():
    for p in [ROOT,BUILD,GPI,SUPPORT,Path(os.environ.get('TMPDIR','/outside'))]:inside(p)
    audit=json.loads((ROOT/'logs/tiegcm2023_driver_audit.json').read_text())
    assert sha(GPI)==audit['sha256']
    with Dataset(GPI) as n:
        assert n.yearday_beg<=2023077<=n.yearday_end
        assert list(n['year_day'][:])==list(range(2023071,2023085))
        assert n['kp'].shape==(14,8)
    for item in json.loads((SUPPORT/'manifest.json').read_text()):
        path=inside(ROOT/item['path']);assert sha(path)==item['sha256']
    source=SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc'
    with Dataset(source) as n:
        assert np.array_equal(n['mtime'][:],[[80,0,0]]) and np.all(n['year'][:]==2002)
        # N2 is diagnosed from the other major mass mixing ratios, not a
        # required prognostic restart variable. Check both leapfrog levels.
        for var in ['TN','UN','VN','O2','O1','HE','OP','TN_NM','UN_NM','VN_NM','O2_NM','O1_NM']:
            assert var in n.variables
    provenance=json.loads((BUILD/'apex_provenance.json').read_text())
    assert sha(BUILD/'apex.F90')==provenance['source_sha256']
    assert sha(ROOT/'third_party/TIEGCM2.0/src/apex.F90')==provenance['old_source_sha256']
    assert (BUILD/'Srcfiles').read_text().splitlines().count('apex.F90')==1
    assert './apex.F90' in (BUILD/'Depends').read_text()
    executable=inside(BUILD/'tiegcm2.0');assert os.access(executable,os.X_OK)
    nm=subprocess.check_output(['nm','--defined-only',str(executable)],text=True)
    for name in ['__apex_MOD_cofrm','__apex_MOD_feldg','__apex_MOD_apex_mka']:
        assert sum(line.split()[-1]==name for line in nm.splitlines() if line.split())==1
    free=shutil.disk_usage(ROOT).free;assert free>10*1024**3
    return {'gpi_sha256':sha(GPI),'restart_sha256':sha(source),'apex_sha256':sha(BUILD/'apex.F90'),
            'executable_sha256':sha(executable),'free_disk_bytes':free,
            'meminfo':Path('/proc/meminfo').read_text().splitlines()[:3],
            'expected_drivers':{str(s):expected_drivers(s) for s in [0,60,300,600]},
            'mpi_version':subprocess.check_output(['mpirun','--version'],text=True).splitlines()[0],
            'compiler_version':subprocess.check_output(['mpifort','--version'],text=True).splitlines()[0]}

def limits():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE,(512*1024**2,512*1024**2))
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-tag',required=True)
    p.add_argument('--execute',action='store_true',help='Consumes a single model launch for this prepared run')
    a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+',a.run_tag):raise ValueError('Invalid tag')
    out=inside(ROOT/'experiments'/a.run_tag)
    if not a.execute:
        if out.exists():raise FileExistsError(out)
        report=preflight();text=configuration();validate_config(text)
        out.mkdir();(out/'input.inp').write_text(text)
        report.update(static_pass=True,input_sha256=sha(out/'input.inp'),wall_limit_s=60,
                      mpi_ranks=4,simulated_seconds=600,output_limit_bytes=512*1024**2,
                      aggregate_rss_limit_bytes=16*1024**3,per_process_address_limit_bytes=8*1024**3)
        (out/'preflight.json').write_text(json.dumps(report,indent=2)+'\n');print('STATIC PASS',out);return
    report=json.loads((out/'preflight.json').read_text());validate_config((out/'input.inp').read_text())
    assert report['input_sha256']==sha(out/'input.inp')
    current=preflight()
    for k in ['gpi_sha256','restart_sha256','apex_sha256','executable_sha256']:assert report[k]==current[k]
    with (out/'launch_once.json').open('x') as f:json.dump({'single_launch':True,'model_seconds':600},f)
    env=dict(os.environ,OMPI_ALLOW_RUN_AS_ROOT='1',OMPI_ALLOW_RUN_AS_ROOT_CONFIRM='1',
             OMPI_MCA_pml='ob1',OMPI_MCA_btl='self,tcp',OMPI_MCA_osc='rdma',PMIX_MCA_gds='hash',
             HOST=socket.gethostname(),LOGNAME=getpass.getuser())
    status={'mpi_ranks':4,'simulated_seconds_requested':600,'peak_process_group_rss_bytes':0}
    start=time.perf_counter()
    with (ROOT/'logs'/f'{a.run_tag}.log').open('x') as log:
        proc=subprocess.Popen(['mpirun','-np','4',str(BUILD/'tiegcm2.0'),'input.inp'],cwd=out,
                              env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limits)
        reason=None
        while proc.poll() is None:
            process_table={}
            for statfile in Path('/proc').glob('[0-9]*/stat'):
                try:
                    fields=statfile.read_text().rsplit(')',1)[1].split()
                    process_table[int(statfile.parent.name)]=(int(fields[1]),int(fields[2]),int(fields[21])*os.sysconf('SC_PAGE_SIZE'))
                except (OSError,ValueError,IndexError):pass
            descendants={proc.pid}
            while True:
                new={pid for pid,(parent,group,_) in process_table.items() if parent in descendants or group==proc.pid}
                if new.issubset(descendants):break
                descendants.update(new)
            rss=sum(process_table[pid][2] for pid in descendants if pid in process_table)
            status['peak_process_group_rss_bytes']=max(rss,status['peak_process_group_rss_bytes'])
            size=sum(f.stat().st_size for f in out.iterdir() if f.is_file())
            if time.perf_counter()-start>60:reason='wall_timeout'
            elif rss>16*1024**3:reason='aggregate_memory_limit'
            elif size>512*1024**2:reason='output_limit'
            elif shutil.disk_usage(ROOT).free<10*1024**3:reason='low_disk'
            if reason:
                os.killpg(proc.pid,signal.SIGKILL);break
            time.sleep(.1)
        proc.wait()
    status.update(returncode=proc.returncode,stop_reason=reason,elapsed_s=time.perf_counter()-start,
                  rss_sampling='process group plus recursive descendants, 0.1 second sampling; sums RSS including shared pages',
                  normal_exit='NORMAL EXIT' in (ROOT/'logs'/f'{a.run_tag}.log').read_text(),
                  restart_after_sha256=sha(SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc'))
    status['restart_unchanged']=status['restart_after_sha256']==report['restart_sha256']
    (out/'run_status.json').write_text(json.dumps(status,indent=2)+'\n');print(json.dumps(status,indent=2))
    if proc.returncode or reason or not status['normal_exit']:raise SystemExit(1)

if __name__=='__main__':main()
