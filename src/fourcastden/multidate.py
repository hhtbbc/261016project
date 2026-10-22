"""Frozen four-date sample contract and bounded HTTP ZIP reads.
Range mechanism follows scripts/fetch_minimal_test_window.py, without its
legacy top-level downloads or writes to historical manifests.
"""
import io,urllib.request
from datetime import datetime,timedelta
import numpy as np
DATES=('2023-03-23','2023-06-21','2023-09-23','2023-12-21')
KEYS=('TN','UN','VN','WN','Z','ZG','DEN','NE','TLBC','ULBC','VLBC','f107d','f107a','Kp')
UNITS=dict(TN='K',UN='cm/s',VN='cm/s',WN='cm/s',Z='cm',ZG='cm',DEN='g/cm3',NE='cm-3',TLBC='K',ULBC='cm/s',VLBC='cm/s',f107d='sfu',f107a='sfu',Kp='unitless')
def names_for(day):
 if day not in DATES:raise ValueError('Window is not preregistered')
 t=datetime.fromisoformat(day)
 return [(t+timedelta(hours=h)).strftime('%Y_%m_%d_%H%M%S.npz') for h in range(3)]
def validate_npz(path):
 with np.load(path,allow_pickle=False) as q:
  if set(q.files)!=set(KEYS):raise ValueError('Exactly fourteen author variables required')
  stats={}
  for k in KEYS:
   x=q[k];shape=(28,36,72) if k in ('TN','UN','VN') else (29,36,72) if k in ('WN','Z','ZG','DEN','NE') else (1,36,72) if k in ('TLBC','ULBC','VLBC') else (1,)
   if x.shape!=shape:raise ValueError(f'{k}: shape {x.shape}, expected {shape}')
   if not np.isfinite(x).all() or np.any(abs(x)>1e30):raise ValueError(f'{k}: nonfinite/sentinel')
   if k in ('DEN','TN','TLBC') and not (x>0).all():raise ValueError(f'{k}: nonpositive')
   stats[k]=dict(shape=list(x.shape),dtype=str(x.dtype),min=float(x.min()),max=float(x.max()),unit=UNITS[k],unit_source='author UNIT_VARS/source; NPZ has no unit attributes')
  if not (np.diff(q['ZG'],axis=0)>0).all():raise ValueError('Nonmonotone ZG')
  return stats
class BoundedRemoteZip(io.RawIOBase):
 def __init__(self,url,size,limit=100*2**20,opener=None):
  self.url=url;self.size=size;self.limit=limit;self.pos=0;self.total=0;self.reserved=0;self.requests=[];self.opener=opener or urllib.request.urlopen
 def seekable(self):return True
 def readable(self):return True
 def tell(self):return self.pos
 def seek(self,offset,whence=0):
  self.pos=offset if whence==0 else (self.pos if whence==1 else self.size)+offset
  if self.pos<0:raise ValueError('Negative seek')
  return self.pos
 def read(self,n=-1):
  n=min(n if n>=0 else self.size-self.pos,self.size-self.pos)
  if n<=0:return b''
  if n>=8_000_000 or self.reserved+n+1>self.limit:raise ValueError('HTTP transfer budget exceeded before request')
  start=self.pos;end=start+n-1;self.reserved+=n+1
  record=dict(start=start,end=end,requested_bytes=n,body_bytes_read=0);self.requests.append(record)
  req=urllib.request.Request(self.url+f'?range_start={start}&range_end={end}',headers={'Range':f'bytes={start}-{end}','Accept-Encoding':'identity'})
  with self.opener(req,timeout=30) as response:
   record['status']=response.status
   if response.status!=206:raise ValueError('Server did not return 206; body not read, stop')
   cr=response.headers.get('Content-Range');record['Content-Range']=cr
   if cr!=f'bytes {start}-{end}/{self.size}':raise ValueError('Content-Range mismatch; body not read')
   body=response.read(n+1);record['body_bytes_read']=len(body);self.total+=len(body)
   if len(body)!=n:raise ValueError('Range body length mismatch')
  self.pos+=n;return body
