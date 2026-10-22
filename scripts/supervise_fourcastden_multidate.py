"""Single GPU worker supervision: wall, aggregate RSS, output and disk budgets."""
import os,sys,json,time,signal,subprocess,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/fourcastden_multidate_v1'
def rss_tree(pid):
 total=0
 try:
  for line in Path(f'/proc/{pid}/status').read_text().splitlines():
   if line.startswith('VmRSS:'):total=int(line.split()[1])*1024
  for child in Path(f'/proc/{pid}/task/{pid}/children').read_text().split():total+=rss_tree(int(child))
 except (FileNotFoundError,ProcessLookupError):pass
 return total
def main():
 assert json.loads((F/'download.json').read_text())['status']=='PASS'
 with (F/'supervisor_once.json').open('x') as f:json.dump(dict(wall_s=600,RSS_bytes=4*2**30,new_bytes=250*2**20),f)
 tick=time.monotonic();peak=0;failure=None
 with (ROOT/'logs/fourcastden_multidate_GPU.log').open('x') as log:
  p=subprocess.Popen([sys.executable,str(ROOT/'scripts/run_fourcastden_multidate.py'),'--execute'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  while p.poll() is None:
   peak=max(peak,rss_tree(p.pid));wall=time.monotonic()-tick
   size=sum(x.stat().st_size for folder in [F,ROOT/'data/raw/fourcastden_multidate_v1',ROOT/'data/processed/fourcastden_multidate_v1'] if folder.exists() for x in folder.rglob('*') if x.is_file())
   if wall>600:failure='wall limit'
   elif peak>4*2**30:failure='RSS limit'
   elif size>250*2**20:failure='output limit'
   elif shutil.disk_usage(ROOT).free<20*2**30:failure='disk free limit'
   if failure:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    break
   time.sleep(.25)
  rc=p.wait()
 report=dict(status='PASS' if rc==0 and failure is None else 'FAILED',returncode=rc,wall_s=time.monotonic()-tick,peak_tree_RSS_bytes=peak,stop_reason=failure,no_retry=True)
 with (F/'supervision.json').open('x') as f:json.dump(report,f,indent=2)
 print(json.dumps(report,indent=2));raise SystemExit(0 if report['status']=='PASS' else 1)
if __name__=='__main__':main()
