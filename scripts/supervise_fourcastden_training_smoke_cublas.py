"""Owned process group watchdog: 300 seconds, 20GiB GPU, 500MiB generated files."""
import subprocess,os,sys,time,signal,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/fourcastden_training_smoke_cublas_v2'
def memory(pid):
 try:
  lines=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader,nounits'],text=True,timeout=3).splitlines()
  return sum(int(x.split(',')[1])*2**20 for x in lines if int(x.split(',')[0])==pid)
 except (ValueError,subprocess.SubprocessError):return None
with (F/'supervision_once.json').open('x') as f:json.dump(dict(wall_s=295,GPU_bytes=20*2**30,new_bytes=500*2**20),f)
t=time.monotonic();peak=0;reason=None;measurements=0
with (ROOT/'logs/fourcastden_training_GPU_cublas_v2.log').open('x') as log:
 p=subprocess.Popen([sys.executable,str(ROOT/'scripts/run_fourcastden_training_smoke_cublas.py')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 while p.poll() is None:
  m=memory(p.pid)
  if m is not None:peak=max(peak,m);measurements+=1
  size=sum(x.stat().st_size for x in F.rglob('*') if x.is_file())
  if time.monotonic()-t>295:reason='wall limit'
  elif peak>20*2**30:reason='GPU limit'
  elif size>500*2**20:reason='file limit'
  elif shutil.disk_usage(ROOT).free<20*2**30:reason='disk free'
  if reason:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   break
  time.sleep(.25)
 rc=p.wait()
r=dict(status='PASS' if rc==0 and reason is None else 'FAILED',returncode=rc,wall_s=time.monotonic()-t,peak_GPU_process_bytes=peak,GPU_measurements=measurements,stop_reason=reason,no_retry=True)
with (F/'supervision.json').open('x') as f:json.dump(r,f,indent=2)
print(json.dumps(r));sys.exit(rc or int(reason is not None))
