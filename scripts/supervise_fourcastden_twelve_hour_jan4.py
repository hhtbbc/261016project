"""Single bounded GPU worker: 48 formal forwards, no extra GPU check."""
import sys,os,json,time,subprocess,signal,shutil
from pathlib import Path
from supervise_fourcastden_multidate import rss_tree
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/fourcastden_twelve_hour_jan4_v1';D=ROOT/'data/processed/fourcastden_twelve_hour_jan4_v1';RAW=ROOT/'data/raw/fourcastden_twelve_hour_jan4_v1'
def main():
 assert json.loads((F/'preflight.json').read_text())['status']=='PASS'
 with (F/'supervisor_once.json').open('x') as f:json.dump(dict(wall_s=600,RSS_bytes=4*2**30,new_bytes=800*2**20),f)
 tick=time.monotonic();peak=0;stop=None
 with (ROOT/'logs/fourcastden_twelve_hour_jan4_GPU.log').open('x') as log:
  p=subprocess.Popen([sys.executable,str(ROOT/'scripts/run_fourcastden_twelve_hour_jan4.py'),'--execute'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  while p.poll() is None:
   peak=max(peak,rss_tree(p.pid));size=sum(x.stat().st_size for folder in [F,D,RAW] if folder.exists() for x in folder.rglob('*') if x.is_file() and not x.is_symlink())
   if time.monotonic()-tick>600:stop='wall limit'
   elif peak>4*2**30:stop='RSS limit'
   elif size>800*2**20:stop='output limit'
   elif shutil.disk_usage(ROOT).free<20*2**30:stop='disk free limit'
   if stop:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    break
   time.sleep(.25)
  rc=p.wait()
 result=dict(status='PASS' if rc==0 and stop is None else 'FAILED',returncode=rc,wall_s=time.monotonic()-tick,peak_RSS_bytes=peak,stop_reason=stop,no_retry=True)
 with (F/'supervision.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result,indent=2));raise SystemExit(0 if result['status']=='PASS' else 1)
if __name__=='__main__':main()
