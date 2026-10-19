"""Read ZIP directory and three real hourly members via validated HTTP byte ranges.
A hard 32 MB transfer cap prevents accidental full dataset downloads.
"""
from pathlib import Path
import io,json,urllib.request,zipfile,hashlib
ROOT=Path(__file__).resolve().parents[1]
meta=json.loads((ROOT/'logs/zenodo_21859635_20261019.json').read_text())
f=meta['files'][0]
class RemoteZip(io.RawIOBase):
    def __init__(self): self.pos=0; self.total=0; self.requests=[]
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        self.pos=offset if whence==0 else (self.pos if whence==1 else f['size'])+offset
        if self.pos<0: raise ValueError('negative seek')
        return self.pos
    def read(self,n=-1):
        n=min(n if n>=0 else f['size']-self.pos,f['size']-self.pos)
        if n<=0:return b''
        assert n<8_000_000 and self.total+n<32_000_000
        start=self.pos; end=start+n-1
        req=urllib.request.Request(f['links']['self']+f'?range_start={start}&range_end={end}',headers={'Range':f'bytes={start}-{end}'})
        with urllib.request.urlopen(req,timeout=60) as response:
            assert response.status==206,(response.status,dict(response.headers))
            assert response.headers['Content-Range']==f'bytes {start}-{end}/{f["size"]}'
            b=response.read(n+1); assert len(b)==n
        self.requests.append({'start':start,'end':end,'bytes':n});self.total+=n;self.pos+=n
        return b
remote=RemoteZip()
try:
    with zipfile.ZipFile(remote) as z:
        inventory=[{'name':i.filename,'bytes':i.file_size,'compressed':i.compress_size,'method':i.compress_type,'crc':i.CRC} for i in z.infolist()]
        (ROOT/'logs/test_archive_inventory.json').write_text(json.dumps(inventory,indent=2))
        names=[f'2023_01_04_{hour:02d}0000.npz' for hour in range(3)]
        output=ROOT/'data/raw/test_minimal_2023';output.mkdir(exist_ok=True)
        saved=[]
        for name in names:
            info=z.getinfo(name); assert info.file_size<10_000_000
            b=z.read(name) # zipfile validates member CRC32
            p=output/name; assert not p.exists();p.write_bytes(b)
            saved.append({'name':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'crc32_verified':True})
        print(json.dumps({'inventory_entries':len(inventory),'saved':saved,'transferred':remote.total},indent=2),flush=True)
finally:
    (ROOT/'logs/minimal_data_ranges.json').write_text(json.dumps({'url':f['links']['self'],'archive_bytes':f['size'],'transfer_bytes':remote.total,'requests':remote.requests},indent=2))
