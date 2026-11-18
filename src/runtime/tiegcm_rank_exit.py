"""MPI rank adapter: direct wait receipts, no scientific success inference."""
from pathlib import Path
import os,sys,json,hashlib,signal,subprocess,time,argparse
ROOT=Path(__file__).resolve().parents[2]
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def write_once(path,data):
 with Path(path).open('x') as f:json.dump(data,f,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
def wrapped(model,run_id,expected_model,expected_input):
 cwd=Path.cwd().resolve();cwd.relative_to(ROOT);model=Path(model).resolve();model.relative_to(ROOT)
 rank=int(os.environ['OMPI_COMM_WORLD_RANK']);size=int(os.environ['OMPI_COMM_WORLD_SIZE'])
 if size!=4 or rank not in range(4):raise ValueError('Exactly four unique MPI ranks required')
 if digest(model)!=expected_model or digest(cwd/'input.inp')!=expected_input:raise ValueError('Rank input/executable SHA changed')
 base=dict(run_id=run_id,rank=rank,size=size,model_SHA256=expected_model,input_SHA256=expected_input,started_unix=time.time(),wrapper_pid=os.getpid(),wrapper_sid=os.getsid(0),wrapper_pgid=os.getpgid(0),wait_source='direct subprocess.Popen.wait')
 write_once(cwd/f'rank_{rank:03d}_started.json',base);child=None;child_sid=None;child_pgid=None;rc=None;error=None;signals=[];saved={}
 def forward(sig,frame):
  signals.append(sig)
  if child is not None and child.poll() is None:child.send_signal(sig)
 try:
  for sig in [signal.SIGTERM,signal.SIGINT]:saved[sig]=signal.signal(sig,forward)
  with (cwd/f'rank_{rank:03d}.log').open('xb') as log:
   child=subprocess.Popen([str(model),'input.inp'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
   child_sid=os.getsid(child.pid);child_pgid=os.getpgid(child.pid)
   for line in iter(child.stdout.readline,b''):
    log.write(line);log.flush();os.write(1,line)  # retain existing fatal/progress monitor
   child.stdout.close();rc=child.wait()
 except BaseException as e:
  error=type(e).__name__
  if child is not None and child.poll() is None:child.terminate();rc=child.wait()
 finally:
  for sig,handler in saved.items():signal.signal(sig,handler)
  write_once(cwd/f'rank_{rank:03d}_exit.json',dict(base,child_pid=child.pid if child else None,child_sid=child_sid,child_pgid=child_pgid,returncode=rc,error=error,received_signals=signals,ended_unix=time.time()))
 if error:return 125
 return rc if rc is not None and rc>=0 else 128+abs(rc or 1)
def main():
 p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--run-id',required=True);p.add_argument('--model-sha',required=True);p.add_argument('--input-sha',required=True);a=p.parse_args();raise SystemExit(wrapped(a.model,a.run_id,a.model_sha,a.input_sha))
if __name__=='__main__':main()
