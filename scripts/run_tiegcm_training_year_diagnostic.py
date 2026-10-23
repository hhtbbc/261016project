"""Prepare or execute one gated ten-minute historical-year diagnostic; never spin up."""
from pathlib import Path
import argparse, hashlib, json, os, re, resource, shutil, signal, socket
import subprocess, time, getpass
import numpy as np
from netCDF4 import Dataset

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'experiments/tiegcm2_apex2023_v1'
YEAR=2022
GPI=ROOT/'data/processed/tiegcm_training_years_v1/gpi_2022_training_candidate.nc'
SUPPORT=ROOT/'data/raw/tiegcm2_support'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def inside(path):
    if not path.resolve().is_relative_to(ROOT):
        raise ValueError(f'Outside workspace: {path}')
    return path

def configuration():
    text=(ROOT/'third_party/TIEGCM2.0/scripts/tiegcm_res5.0_default.inp').read_text()
    replacements={'START_YEAR':str(YEAR),'START_DAY':'95','START':'95 0 0',
                  'STOP':'95 0 10','HIST':'0 0 5','SECSTART':'95 0 5',
                  'SECSTOP':'95 0 10','SECHIST':'0 0 5',
                  'LABEL':"'Historical-year diagnostic; 2002 numerical initial guess; not spun up'"}
    for key,value in replacements.items():
        text,n=re.subn(rf'(?m)^\s*{key}\s*=.*$',f' {key} = {value}',text)
        if n!=1:raise ValueError(f'Unexpected template field {key}')
    text=re.sub(r'(?m)^\s*(?:F107|F107A|KP|POWER|CTPOTEN)\s*=.*\n','',text)
    text=text.replace('$TGCMDATA',str(SUPPORT))
    text=text.replace("\n/",f"\n GPI_NCFILE = '{GPI}'\n/")
    return text

def validate_config(text):
    expected={'START_YEAR':str(YEAR),'START_DAY':'95','SOURCE_START':'80 0 0',
              'START':'95 0 0','STOP':'95 0 10','STEP':'60','CALENDAR_ADVANCE':'1',
              'HIST':'0 0 5','SECSTART':'95 0 5','SECSTOP':'95 0 10','SECHIST':'0 0 5'}
    for key,val in expected.items():
        m=re.findall(rf'(?m)^\s*{key}\s*=\s*(.*?)\s*$',text)
        if m!=[val]:raise ValueError(f'Invalid fixed diagnostic field {key}: {m}')
    if re.search(r'(?im)^\s*(F107|F107A|KP|POWER|CTPOTEN)(?:_TIME)?\s*=',text):
        raise ValueError('Fixed/time-series driver override forbidden')
    if f"GPI_NCFILE = '{GPI}'" not in text or "POTENTIAL_MODEL = 'HEELIS'" not in text:
        raise ValueError('Missing GPI/HEELIS')

def expected_drivers(seconds):
    with Dataset(GPI) as n:
        idx=list(n['year_day'][:]).index(YEAR*1000+95)
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
    inside(GPI);inside(Path(os.environ.get('TMPDIR','/outside')))
    audit=json.loads((ROOT/f'experiments/tiegcm_training_years_v1/{YEAR}/driver_audit.json').read_text())
    assert audit['status']=='PASS' and audit['year']==YEAR and sha(GPI)==audit['SHA256']
    assert sha(BUILD/'tiegcm2.0')=='f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776'
    source=SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc'
    assert sha(source)=='180475215a4922e9c55a77e80153cf641bc8fbb2b8d52633b4686ddee6942fff'
    for item in json.loads((SUPPORT/'manifest.json').read_text()):assert sha(inside(ROOT/item['path']))==item['sha256']
    provenance=json.loads((BUILD/'apex_provenance.json').read_text())
    assert sha(BUILD/'apex.F90')==provenance['source_sha256']=='7dc94d3826d1b8d555fa6a6dea26e2a3788fbca2a86581aff3bcdefb52c5cdc3'
    assert sha(ROOT/'third_party/TIEGCM2.0/src/apex.F90')==provenance['old_source_sha256']
    assert '2020' in (BUILD/'apex.F90').read_text() and '2025' in (BUILD/'apex.F90').read_text()
    with Dataset(source) as n:assert np.array_equal(n['mtime'][:],[[80,0,0]]) and np.all(n['year'][:]==2002)
    with Dataset(GPI) as n:assert n.yearday_beg<=YEAR*1000+95<=n.yearday_end
    free=shutil.disk_usage(ROOT).free;assert free>20*1024**3
    historical=json.loads((ROOT/'experiments/tiegcm2023_startup_10min_v1/run_status.json').read_text())
    estimate=historical['elapsed_s']*8;assert estimate<60
    return dict(gpi_sha256=sha(GPI),restart_sha256=sha(source),apex_sha256=sha(BUILD/'apex.F90'),executable_sha256=sha(BUILD/'tiegcm2.0'),free_disk_bytes=free,year=YEAR,expected_drivers={str(s):expected_drivers(s) for s in range(0,601,60)},predicted_wall_s=estimate,initial_state='2002 numerical initial guess, NOT TRAINING DATA')

def limits():
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE,(512*1024**2,512*1024**2))
    resource.setrlimit(resource.RLIMIT_CPU,(60,60))

def main():
    global YEAR,GPI
    p=argparse.ArgumentParser();p.add_argument('--year',type=int,choices=[2021,2022],required=True);p.add_argument('--run-tag',required=True)
    p.add_argument('--execute',action='store_true',help='Consumes a single model launch for this prepared run')
    a=p.parse_args();YEAR=a.year;GPI=ROOT/f'data/processed/tiegcm_training_years_v1/gpi_{YEAR}_training_candidate.nc'
    if a.run_tag!=f'tiegcm_training_d{YEAR}_v1':raise ValueError('Only one fixed tag per year')
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
            elif shutil.disk_usage(ROOT).free<20*1024**3:reason='low_disk'
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
