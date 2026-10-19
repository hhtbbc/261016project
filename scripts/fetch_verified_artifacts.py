"""Download only verified software artifacts smaller than 5 GB; never fetch full 2023.zip."""
from pathlib import Path
import hashlib,json,urllib.request,time,zipfile,stat
ROOT=Path(__file__).resolve().parents[1]
meta=json.loads((ROOT/'logs/zenodo_22250238_20261019.json').read_text())
records=[]
for key in ['static.zip','static_log.zip','checkpoint_files.zip']:
 f=next(x for x in meta['files'] if x['key']==key)
 assert f['size']<=5_000_000_000
 dest=ROOT/('models/checkpoints' if key.startswith('checkpoint') else 'data/raw')/key
 assert dest.resolve().is_relative_to(ROOT) and not dest.exists()
 partial=dest.with_suffix('.zip.part'); h=hashlib.md5(); count=0; start=time.time()
 with urllib.request.urlopen(f['links']['self']+'?download=1',timeout=120) as response,partial.open('xb') as out:
  assert response.status==200
  while True:
   b=response.read(4*1024*1024)
   if not b: break
   count+=len(b); assert count<=f['size']; h.update(b); out.write(b)
 assert count==f['size'] and 'md5:'+h.hexdigest()==f['checksum']
 partial.rename(dest)
 with zipfile.ZipFile(dest) as z:
  inv=[{'name':i.filename,'size':i.file_size,'compressed':i.compress_size,'method':i.compress_type,'crc':i.CRC} for i in z.infolist()]
  target=ROOT/('models/checkpoints/author' if key.startswith('checkpoint') else ('data/processed/'+Path(key).stem))
  for i in z.infolist():
   assert not Path(i.filename).is_absolute() and '..' not in Path(i.filename).parts and not stat.S_ISLNK(i.external_attr>>16)
   assert (target/i.filename).resolve().is_relative_to(ROOT)
  assert sum(i.file_size for i in z.infolist())<12_000_000_000
  z.extractall(target)
 records.append({'file':str(dest.relative_to(ROOT)),'bytes':count,'md5':h.hexdigest(),'seconds':time.time()-start,'inventory':inv})
 (ROOT/'logs/artifact_downloads.json').write_text(json.dumps(records,indent=2))
 print(key,count,'verified',flush=True)
