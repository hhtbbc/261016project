"""V21 metered HTTPS transport and independent data-contract guards.

Budget charges TCP-stream bytes consumed/sent, including proxy CONNECT, TLS and
HTTP headers, redirect/error transfers. IP/TCP packet headers/retransmissions are
not observed by this application; this is not an OS/network packet quota.
"""
from pathlib import Path
import socket,ssl,io,http.client,urllib.parse,os,time,json,hashlib
from observations.bounded_swarm_acquisition import inside,sha,atomic_publish
class BudgetError(ValueError):pass
class Meter:
 def __init__(self,small=2**20,initial=20*2**20):
  self.limits={'small':small,'initial':initial};self.rx={'small':0,'initial':0};self.tx={'small':0,'initial':0};self.reserved_failed_tx={'small':0,'initial':0}
 def remaining(self,group):return self.limits[group]-self.rx[group]-self.tx[group]-self.reserved_failed_tx[group]
 def receive(self,group,n):
  if n<0 or n>self.remaining(group):raise BudgetError('Transport receive budget exceeded')
  self.rx[group]+=n
 def send(self,group,data,raw):
  offset=0
  while offset<len(data):
   n=min(len(data)-offset,self.remaining(group))
   if n<=0:raise BudgetError('Transport send budget exhausted')
   try:sent=raw.send(data[offset:offset+n])
   except Exception:
    self.reserved_failed_tx[group]+=n;raise
   if sent<=0:raise ConnectionError('Socket send failed')
   self.tx[group]+=sent;offset+=sent
 def summary(self):
  return dict(limits=self.limits,received_transport_bytes=dict(self.rx),sent_transport_bytes=dict(self.tx),conservative_failed_send_reservations=dict(self.reserved_failed_tx),charged_bytes={k:self.limits[k]-self.remaining(k) for k in self.limits},total_received_bytes=sum(self.rx.values()),total_sent_bytes=sum(self.tx.values()),total_charged_bytes=sum(self.limits[k]-self.remaining(k) for k in self.limits),definition='Application TCP-stream consumed bytes inclTLS/HTTP/CONNECT; outbound also charged conservatively; includes all attempts/redirects/errors, not only saved bodies. IP-level overhead/retransmissions not observable; not OS packet isolation.')

def official(url,host):
 u=urllib.parse.urlsplit(url)
 if u.scheme!='https' or u.hostname!=host or u.username or u.password or u.port not in (None,443):raise ValueError('Official same-origin HTTPS only')
 return u

def redirect_allowed(original,new):
 a=urllib.parse.urlsplit(original);b=official(new,a.hostname);qa=urllib.parse.parse_qs(a.query);qb=urllib.parse.parse_qs(b.query)
 if a.hostname=='swarm-diss.eo.esa.int':
  if qb.get('file')!=qa.get('file') and Path(b.path).name!=Path(qa.get('file',[''])[0]).name:raise ValueError('Redirect changed Swarm product')
 elif a.hostname=='kp.gfz.de':
  if any(qb.get(k)!=qa.get(k) for k in ['start','end','index','status']):raise ValueError('Redirect changed GFZ request identity')
 elif Path(a.path).name!=Path(b.path).name:raise ValueError('Redirect changed initial filename')
 return new

class TLSStream(io.RawIOBase):
 def __init__(self,host,meter,group,timeout=25):
  self.meter,self.group=meter,group;self.sock=None;self.incoming=ssl.MemoryBIO();self.outgoing=ssl.MemoryBIO()
  proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
  if proxy:
   p=urllib.parse.urlsplit(proxy)
   if p.scheme!='http' or p.username or p.password:raise ValueError('Unsupported authenticated/changed proxy route')
   self.sock=socket.create_connection((p.hostname,p.port or 80),timeout);self.sock.settimeout(timeout)
   meter.send(group,f'CONNECT {host}:443 HTTP/1.1\r\nHost: {host}:443\r\n\r\n'.encode(),self.sock);header=b''
   while not header.endswith(b'\r\n\r\n'):
    header+=self.raw_receive(1)
    if len(header)>16384:raise ValueError('Proxy header too large')
   if len(header.split())<2 or header.split()[1]!=b'200':raise ConnectionError('Existing proxy CONNECT refused')
  else:self.sock=socket.create_connection((host,443),timeout);self.sock.settimeout(timeout)
  context=ssl.create_default_context();self.tls=context.wrap_bio(self.incoming,self.outgoing,server_side=False,server_hostname=host);self.operate(self.tls.do_handshake)
 def raw_receive(self,n):
  remaining=self.meter.remaining(self.group)
  if remaining<=0:raise BudgetError('Transport receive budget exhausted')
  block=self.sock.recv(min(n,remaining));self.meter.receive(self.group,len(block))
  if not block:raise EOFError('Unexpected transport EOF')
  return block
 def flush_tls(self):
  while self.outgoing.pending:self.meter.send(self.group,self.outgoing.read(),self.sock)
 def operate(self,operation):
  while True:
   try:r=operation();self.flush_tls();return r
   except ssl.SSLWantReadError:self.flush_tls();self.incoming.write(self.raw_receive(16384))
   except ssl.SSLWantWriteError:self.flush_tls()
 def send_request(self,data):
  done=0
  while done<len(data):done+=self.operate(lambda:self.tls.write(data[done:]))
 def readable(self):return True
 def readinto(self,b):
  try:data=self.operate(lambda:self.tls.read(len(b)))
  except (ssl.SSLZeroReturnError,ssl.SSLEOFError):return 0
  b[:len(data)]=data;return len(data)
 def makefile(self,*args,**kwargs):return io.BufferedReader(self,buffer_size=8192)
 def close(self):
  if self.sock is not None:self.sock.close();self.sock=None
  super().close()

def bounded_get(url,path,meter,group,receipts,*,expected_bytes=None,magic=None,max_body=None):
 """One GET per origin step, <=2 same-origin redirects, no file retry."""
 path=inside(path);part=inside(path.with_name(path.name+'.partial'));host=urllib.parse.urlsplit(url).hostname;official(url,host)
 if host not in ['swarm-diss.eo.esa.int','kp.gfz.de','download.hao.ucar.edu']:raise ValueError('Unapproved source')
 if path.exists() or part.exists():raise FileExistsError('Existing original/partial preserved; no overwrite or automatic retry')
 current=url;cap=max_body or meter.remaining(group);started=time.time();body_total=0
 for hop in range(3):
  u=official(current,host);record=dict(URL=current,original_URL=url,group=group,redirect_hop=hop,started_unix=time.time(),meter_before=meter.summary(),HTTP=None);receipts.append(record);conn=None;response=None
  try:
   conn=TLSStream(host,meter,group);target=urllib.parse.urlunsplit(('', '',u.path or '/',u.query,''));request=f'GET {target} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: Satellite-AI-bounded-V21/1.0\r\nAccept-Encoding: identity\r\nConnection: close\r\n\r\n';conn.send_request(request.encode('ascii'));response=http.client.HTTPResponse(conn);response.begin();record.update(HTTP=response.status,TLS_hostname_verified=True,headers={k:response.getheader(k) for k in ['Content-Length','Content-Type','Content-Encoding','Last-Modified','ETag','Location'] if response.getheader(k) is not None},header_checked_before_body_write=True)
   if response.status in [301,302,303,307,308]:
    if hop==2:raise ValueError('Redirect limit reached')
    new=urllib.parse.urljoin(current,response.getheader('Location',''));redirect_allowed(url,new);current=new;record['redirect_followed_same_identity']=True;continue
   if response.status!=200:raise ValueError('HTTP status not200; no retry or authentication')
   cl=response.getheader('Content-Length');length=int(cl) if cl is not None else None
   if expected_bytes is not None and length is not None and length!=expected_bytes:raise ValueError('Frozen listing byte size changed')
   if length is not None and (length>cap or length>meter.remaining(group)):raise BudgetError('Declared body exceeds file/transport budget')
   if 'html' in response.getheader('Content-Type','').lower():raise ValueError('HTML is not the authorized data')
   if response.getheader('Content-Encoding','identity').lower() not in ['identity','']:raise ValueError('Unexpected encoded content; no identity substitution')
   with part.open('xb') as f:
    last_progress=time.monotonic()
    while True:
     # Do not exceed the authorized body cap even if the length is not advertised.
     remaining=cap-body_total
     if remaining<=0:
      if length==body_total:break
      raise BudgetError('Body cap reached before verified EOF')
     block=response.read(min(16384,remaining))
     if not block:break
     body_total+=len(block);f.write(block)
     if time.monotonic()-last_progress>5:
      print(json.dumps(dict(event='V21_TRANSFER_PROGRESS',group=group,body_bytes=body_total,charged_bytes=meter.summary()['total_charged_bytes'])),flush=True);last_progress=time.monotonic()
     if expected_bytes is not None and body_total>expected_bytes:raise ValueError('Body larger than frozen product')
    f.flush();os.fsync(f.fileno())
   if expected_bytes is not None and body_total!=expected_bytes:raise ValueError('Body size differs from frozen product')
   if length is not None and body_total!=length:raise ValueError('Incomplete body')
   if magic is not None:
    with part.open('rb') as f:prefix=f.read(8)
    if not any(prefix.startswith(x) for x in magic):raise ValueError('Wrong file magic')
   digest=sha(part);atomic_publish(part,path);record.update(body_bytes=body_total,final_URL=current,SHA256=digest,relative_path=str(path.relative_to(Path(__file__).resolve().parents[2])),published_atomic_no_clobber=True,completed_unix=time.time(),file_elapsed_s=time.time()-started)
   return dict(path=record['relative_path'],SHA256=digest,bytes=body_total,URL=url,final_URL=current,HTTP=200,Content_Length=length,existing_reused=False)
  except Exception as e:
   record.update(error_type=type(e).__name__,error=str(e),body_bytes_saved=body_total,partial_preserved=part.exists());raise
  finally:
   if response is not None:response.close()
   if conn is not None:conn.close()
   record['meter_after']=meter.summary()
 raise ValueError('No successful data response')
