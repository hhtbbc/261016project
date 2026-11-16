"""RAR5 metadata only, per rarlab.com/technote.htm; never decompress or execute."""
from pathlib import Path,PurePosixPath
import sys,json,hashlib,zlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts')]
from prepare_fourcastden_swarm_observation_v1 import dump,sha
TAG='thermosphere_observation_assimilation_feasibility_v1';D=ROOT/'data/raw'/TAG;F=ROOT/'experiments'/TAG

def main():
 p=D/'official/Code.rar';b=p.read_bytes();assert b[:8]==bytes.fromhex('526172211a070100');assert hashlib.md5(b).hexdigest()=='0ebc22065451eab6b149b37f0441a756'
 def vint(pos):
  v=0
  for shift in range(0,70,7):
   byte=b[pos];pos+=1;v|=(byte&127)<<shift
   if not byte&128:return v,pos
  raise ValueError('Unbounded vint')
 pos=8;items=[];headers=0
 while pos<len(b):
  crc=int.from_bytes(b[pos:pos+4],'little');n,q=vint(pos+4);end=q+n;assert end<=len(b) and zlib.crc32(b[pos+4:end])==crc;typ,q=vint(q);flags,q=vint(q);extra=packed=0
  if flags&1:extra,q=vint(q)
  if flags&2:packed,q=vint(q)
  if typ==4:raise ValueError('Encrypted archive metadata cannot be inspected')
  if typ in [2,3]:
   ff,q=vint(q);unpacked,q=vint(q);attrs,q=vint(q)
   if ff&2:q+=4
   if ff&4:q+=4
   compression,q=vint(q);host,q=vint(q);ln,q=vint(q);name=b[q:q+ln].decode('utf-8');assert q+ln<=end
   safe=not PurePosixPath(name.replace('\\','/')).is_absolute() and '..' not in PurePosixPath(name.replace('\\','/')).parts
   items.append(dict(name=name,directory=bool(ff&1),unpacked_bytes=unpacked,packed_bytes=packed,compression_method=(compression>>7)&7,safe_relative_name=safe,contents_read=False))
  headers+=1;pos=end+packed
  if typ==5:break
 dump(F/'author_code_archive_inventory.json',dict(PASS=True,source='Zenodo10732144v2',archive_SHA256=sha(p),official_MD5_matches=True,header_CRCs_verified=headers,entries=items,contents_decompressed=False,code_executed=False,limitation='No local RAR5 decompressor; only archive member names/sizes proven, not program contents',specification='https://www.rarlab.com/technote.htm'));print(json.dumps(items,indent=2))
if __name__=='__main__':main()
