"""Read-only historical evidence and future-only B14 preparation; never Popen."""
from pathlib import Path
import sys,json,re,hashlib,shutil,time,os,difflib
import numpy as np
from netCDF4 import Dataset,num2date
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from atmosphere.tiegcm_drivers import GpiDriver
from run_tiegcm_mar23_2021_longrun import stream_sha
import run_tiegcm_2022_14day as old
from runtime.supervisor import ProcReader
TAG='tiegcm_supervision_repair_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG
H=ROOT/'experiments/tiegcm_2022_spinup_14day_v1';A=H/'A14'
def write(name,obj):
 with (F/name).open('x') as f:json.dump(obj,f,indent=2,allow_nan=False)
def main():
 start=time.perf_counter();paths=[p for p in H.rglob('*') if p.is_file() and 'prelaunch_incident_local' not in p.parts]
 paths += [ROOT/'logs'/n for n in ['tiegcm_2022_14day_A14.log','tiegcm_2022_14day_A14_supervisor.log','tiegcm_2022_14day_A14_guardian.log','tiegcm_2022_14day_resume.log']]
 before={str(p.relative_to(ROOT)):stream_sha(p) for p in paths}
 audit=json.loads((A/'data_audit.json').read_text());run=json.loads((A/'run_status.json').read_text());pre=json.loads((A/'preflight.json').read_text());driver=json.loads((H/'driver_audit.json').read_text());drv=GpiDriver(old.GPI);records=[];primary=[];secondary=[];maximum_driver=0.
 for e in audit['files']:
  path=A/e['file'];assert stream_sha(path)==e['SHA256'];old.basic_file(path)
  with Dataset(path) as n:
   times=num2date(n['time'][:],n['time'].units);clock=[]
   assert np.all(n['year'][:]==2022)
   for i,t in enumerate(times):
    sec=int(t.strftime('%j'))*86400+t.hour*3600+t.minute*60;clock.append(sec);assert list(map(int,n['mtime'][i]))==[int(t.strftime('%j')),t.hour,t.minute]
    if path.name.startswith('secondary'):
     values=drv.at(2022000+int(t.strftime('%j')),t.hour*3600+t.minute*60)
     for k,v in values.items():maximum_driver=max(maximum_driver,abs(float(n[k][i])-v))
   (primary if path.name.startswith('primary') else secondary).extend(clock)
   records.append(dict(file=path.name,records=len(clock),SHA256=e['SHA256'],first_doy_seconds=clock[0],last_doy_seconds=clock[-1],schema={k:dict(dimensions=n[k].dimensions,units=getattr(n[k],'units',None),dtype=str(n[k].dtype)) for k in ['DEN','ZG','TN','UN','VN','O1','O2','N2','HE'] if k in n.variables},absent_diagnostic_fields=[k for k in ['DEN','ZG'] if k not in n.variables]))
 assert primary==list(range(68*86400,84*86400+1,86400));assert secondary==list(range(68*86400+3600,84*86400+1,3600));assert maximum_driver<1e-10
 log=(ROOT/'logs/tiegcm_2022_14day_A14.log').read_text();steps=[int(x) for x in re.findall(r'Step\s+(\d+) of\s+23040',log)]
 assert max(steps)==23040 and log.count('NORMAL EXIT')==4 and run['returncode'] is None and not audit['engineering_PASS']
 g=json.loads((A/'guardian_launch_once.json').read_text());gap=run['resource_samples'][0]['wall_s']-g['original_progress']['wall_s']
 write('A14_evidence.json',dict(data_integrity='PASS',physical_field_engineering='PASS',actual_exit_status='UNKNOWN_UNRECOVERABLE_FROM_RETAINED_EVIDENCE',limited_offline_analysis='ALLOWED_WITH_DISCLOSURE',original_complete_engineering='PARTIAL',steps_log_max=max(steps),printed_step_records=len(steps),normal_exit_count=4,primary_records=len(primary),secondary_records=len(secondary),NetCDF_files=records,driver_max_abs_difference=maximum_driver,sampling_gap_s=gap,previous_rss_sample_s=g['original_progress']['wall_s'],first_guardian_sample_s=run['resource_samples'][0]['wall_s'],returncode=None,exit_evidence_search=['original supervisor traceback: exited before wait','original guardian status: raw wait status null','resume controller assertion: did not launch B14','no retained waitpid/wait4/system-accounting return status found in prior manifests/logs'],historical_proc_now_not_used_as_exit_evidence=True))
 # Reverify inputs and compatibility, without calling old prepare/execute/preflight.
 source=old.initial.source_audit();assert source['required_count']==34
 inputs={pre['source']:pre['restart_sha256'],str(old.initial.SOURCE.relative_to(ROOT)):source['SHA256'],str(old.GPI.relative_to(ROOT)):driver['SHA256'],str((old.m.s.BUILD/'tiegcm2.0').relative_to(ROOT)):pre['executable_sha256'],str((old.m.s.BUILD/'apex.F90').relative_to(ROOT)):pre['apex_sha256']}
 for name,expected in inputs.items():assert stream_sha(ROOT/name)==expected
 for minute in range(23041):
  t=68*86400+minute*60;v=drv.at(2022000+t//86400,t%86400);assert all(np.isfinite(x) for x in v.values())
 atext=(A/'input.inp').read_text();assert stream_sha(A/'input.inp')==pre['input_sha256'];btext=old.configuration('B14');assert btext.replace(str(old.initial.SOURCE),str(old.m.s.SUPPORT/'tiegcm_res5.0_mareqx_smin_prim.nc'))==atext
 assert not (H/'B14').exists()
 a7=json.loads((old.A7/'run_status.json').read_text());b7=json.loads((old.B7/'run_status.json').read_text());estimate=run['elapsed_s']*b7['elapsed_s']/a7['elapsed_s'];free=shutil.disk_usage(ROOT).free;available=int(re.search(r'MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text())[1])*1024
 active=[];reader=ProcReader()
 for name in reader.names():
  if not name.isdigit():continue
  try:
   if (Path('/proc')/name/'comm').read_text().strip()=='tiegcm2.0':active.append(int(name))
  except OSError:pass
 spec=dict(status='STATIC_PREPARATION_ONLY_NOT_AUTHORIZATION',protocol_A='BLOCKED: historical A14 full engineering requirement unsatisfied',protocol_B='DRAFT_REQUIRES_SEPARATE_USER_AUTHORIZATION_AND_PRELAUNCH_FREEZE',future_output='experiments/tiegcm_2022_b14_exploratory_pair_v2/B14 (must not exist)',argv=['mpirun','-np','4',str(old.m.s.BUILD/'tiegcm2.0'),'input.inp'],namelist=btext,namelist_SHA256=hashlib.sha256(btext.encode()).hexdigest(),configuration_diff=list(difflib.unified_diff(atext.splitlines(),btext.splitlines(),fromfile='A14',tofile='B14_future')),expected_steps=23040,expected_primary_records=17,expected_secondary_records=384,MPI=4,OMP_NUM_THREADS=1,SOURCE_START=[80,0,0],input_SHA256=inputs,estimated_wall_s=estimate,safety_wall_s=estimate*1.5,reference_wall_limit_s=4800,reference_RSS_limit_bytes=16*2**30,reference_output_limit_bytes=5*2**30,reference_volume_limit_bytes=256*2**20,reference_disk_floor_bytes=20*2**30,estimated_NetCDF_bytes=run['netcdf_bytes'],current_free_disk_bytes=free,current_available_memory_bytes=available,cpu_affinity_count=len(os.sched_getaffinity(0)),active_TIEGCM_pids=active,current_resources_PASS=free>25*2**30 and available>16*2**30 and len(os.sched_getaffinity(0))>=4 and not active,supervisor='runtime.supervisor.supervise, direct owned child, pidfd termination, independent closed-volume validator',required_future_steps=['user authorizes protocol version and new output identity','revalidate all SHA and current resources, exclude concurrent TIE','freeze environment, supervisor SHA, validator SHA and whole-run budget including cleanup','stage exact namelist via input_files in fresh output; exclusive launch marker; no retries','validator checks only closed NC while running, all33 after true wait returncode0','separate engineering and scientific states; no promotion of historical A14'])
 write('B14_static_preflight.json',spec)
 for name,expected in before.items():assert stream_sha(ROOT/name)==expected,name
 write('history_preservation.json',dict(PASS=True,files=len(before),SHA256=before,wall_s=time.perf_counter()-start,real_model_launches=0))
 print('A14 evidence audited; B14 static only; no model starts',len(before),estimate,spec['current_resources_PASS'])
if __name__=='__main__':main()
