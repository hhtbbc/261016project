"""Bounded official ZIP acquisition; atomic no-clobber publication and safe extraction."""
from pathlib import Path,PurePosixPath
from dataclasses import dataclass
import ssl,urllib.request,urllib.parse,zipfile,stat,os,hashlib,zlib,time
ROOT=Path(__file__).resolve().parents[2];HOST='swarm-diss.eo.esa.int'
def inside(p):
 p=Path(p);p.resolve().relative_to(ROOT);return p

def sha(p):
 h=hashlib.sha256()
 with inside(p).open('rb') as f:
  for b in iter(lambda:f.read(65536),b''):h.update(b)
 return h.hexdigest()
def official_url(url):
 u=urllib.parse.urlsplit(url)
 if u.scheme!='https' or u.hostname!=HOST or u.username or u.password or u.port not in (None,443):raise ValueError('Official HTTPS host only')
 return url
class OfficialRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  official_url(newurl);return super().redirect_request(req,fp,code,msg,headers,newurl)
@dataclass
class Budget:
 network_limit:int=2**20
 extract_limit:int=2*2**20
 network_bytes:int=0
 extracted_bytes:int=0

def archive_plan(path,stem,remaining):
 path=inside(path)
 with path.open('rb') as f:
  if f.read(4)!=b'PK\x03\x04':raise ValueError('Not a ZIP local header; possible HTML')
 with zipfile.ZipFile(path) as z:
  info=z.infolist();names=[x.filename for x in info];expected={stem+'.cdf',stem+'.HDR'}
  if len(info)!=2 or set(names)!=expected or len(set(names))!=2:raise ValueError('Exactly matching CDF and HDR required')
  if sum(x.file_size for x in info)>remaining:raise ValueError('Aggregate extraction budget exceeded')
  for x in info:
   pp=PurePosixPath(x.filename);mode=x.external_attr>>16
   if pp.is_absolute() or '..' in pp.parts or len(pp.parts)!=1 or '\\' in x.filename or x.is_dir() or stat.S_ISLNK(mode) or x.flag_bits&1:raise ValueError('Unsafe archive member')
   if stat.S_IFMT(mode) not in (0,stat.S_IFREG):raise ValueError('Non-regular ZIP member')
  if z.testzip() is not None:raise ValueError('ZIP CRC verification failed')
  return [dict(name=x.filename,bytes=x.file_size,CRC32=f'{x.CRC:08x}') for x in info]

def atomic_publish(partial,final):
 partial,final=inside(partial),inside(final)
 # Same-directory hardlink makes final publication atomic and refuses overwrite.
 os.link(partial,final);partial.unlink()

def download_zip(url,path,expected_bytes,stem,budget,*,opener=None):
 url=official_url(url);path=inside(path);partial=inside(path.with_name(path.name+'.partial'))
 if path.exists():
  if path.stat().st_size!=expected_bytes:raise ValueError('Existing ZIP size mismatch; no overwrite/download')
  members=archive_plan(path,stem,budget.extract_limit-budget.extracted_bytes)
  return dict(URL=url,final_URL=None,HTTP=None,bytes=expected_bytes,SHA256=sha(path),path=str(path.relative_to(ROOT)),existing=True,new_download_bytes=0,CRC_test_PASS=True,members=members)
 if partial.exists():raise FileExistsError('Existing partial retained; no automatic retry')
 if expected_bytes>budget.network_limit-budget.network_bytes:raise ValueError('Network budget unavailable')
 if opener is None:opener=urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl.create_default_context()),OfficialRedirect())
 started=time.time();received=0
 request=urllib.request.Request(url,headers={'Accept':'application/zip','User-Agent':'Satellite-AI-bounded-acquisition/1.0'})
 with opener.open(request,timeout=25) as response:
  if response.status!=200:raise ValueError('Unexpected HTTP status')
  final=official_url(response.geturl());cl=response.headers.get('Content-Length')
  if cl is None or int(cl)!=expected_bytes:raise ValueError('Content-Length differs from frozen listing size')
  if 'html' in response.headers.get('Content-Type','').lower():raise ValueError('HTML response rejected')
  with partial.open('xb') as f:
   while True:
    left=budget.network_limit-budget.network_bytes
    if left<=0:raise ValueError('Network budget exhausted; partial retained')
    block=response.read(min(16384,left,expected_bytes-received+1))
    if not block:break
    received+=len(block);budget.network_bytes+=len(block);f.write(block)
    if received>expected_bytes:raise ValueError('Body larger than frozen size; partial retained')
   f.flush();os.fsync(f.fileno())
 if received!=expected_bytes:raise ValueError('Truncated body; partial retained')
 members=archive_plan(partial,stem,budget.extract_limit-budget.extracted_bytes);digest=sha(partial);atomic_publish(partial,path)
 return dict(URL=url,final_URL=final,HTTP=200,Content_Length=int(cl),bytes=received,SHA256=digest,path=str(path.relative_to(ROOT)),existing=False,new_download_bytes=received,CRC_test_PASS=True,members=members,download_started_unix=started,download_finished_unix=time.time(),TLS='ssl.create_default_context; hostname/certificate verification enabled',timeout_s=25)

def extract_members(path,stem,budget,destination):
 path=inside(path);destination=inside(destination);plan=archive_plan(path,stem,budget.extract_limit-budget.extracted_bytes);out=[]
 with zipfile.ZipFile(path) as z:
  for item in plan:
   target=inside(destination/item['name']);partial=inside(target.with_name(target.name+'.partial'));digest=hashlib.sha256();crc=0;total=0
   if partial.exists():raise FileExistsError('Existing extraction partial retained')
   # Verify an existing member against the immutable archive, never overwrite it.
   existing=target.exists()
   stream=None if existing else partial.open('xb')
   try:
    with z.open(item['name']) as src:
     while True:
      block=src.read(16384)
      if not block:break
      if total+len(block)>item['bytes'] or budget.extracted_bytes+len(block)>budget.extract_limit:raise ValueError('Stream extraction budget exceeded')
      total+=len(block);budget.extracted_bytes+=len(block);digest.update(block);crc=zlib.crc32(block,crc)
      if stream is not None:stream.write(block)
    if total!=item['bytes'] or f'{crc:08x}'!=item['CRC32']:raise ValueError('Member byte count/CRC mismatch')
    if stream is not None:stream.flush();os.fsync(stream.fileno())
   finally:
    if stream is not None:stream.close()
   if existing:
    if sha(target)!=digest.hexdigest():raise ValueError('Existing member differs; no overwrite')
   else:atomic_publish(partial,target)
   out.append(dict(path=str(target.relative_to(ROOT)),bytes=total,SHA256=digest.hexdigest(),CRC32=f'{crc:08x}',CRC_PASS=True,existing=existing))
 return out

def posix_cksum(path):
    """POSIX cksum CRC (length appended), distinct from ZIP/zlib CRC-32."""
    table=[]
    for i in range(256):
        x=i<<24
        for _ in range(8):x=((x<<1)^0x04c11db7 if x&0x80000000 else x<<1)&0xffffffff
        table.append(x)
    crc=0;length=0
    with inside(path).open('rb') as f:
        for block in iter(lambda:f.read(65536),b''):
            length+=len(block)
            for b in block:crc=((crc<<8)^table[((crc>>24)^b)&255])&0xffffffff
    n=length
    while n:
        crc=((crc<<8)^table[((crc>>24)^(n&255))&255])&0xffffffff;n>>=8
    return (~crc)&0xffffffff,length
