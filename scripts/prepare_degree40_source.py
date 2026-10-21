"""Prepare the frozen 256KiB EGM2008 prefix only, never the complete model."""
from pathlib import Path
import hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parents[1];m=json.loads((ROOT/'configs/egm2008_degree40_source.json').read_text());p=ROOT/'data/raw/gravity_sources/EGM2008_DEG40_PREFIX.gfc';p.resolve().relative_to(ROOT)
if not p.exists():
 with urllib.request.urlopen(m['url'],timeout=40) as r:data=r.read(m['bytes_read'])
 if hashlib.sha256(data).hexdigest()!=m['sha256']:raise ValueError('Source changed; preserve original and investigate')
 p.write_bytes(data)
if hashlib.sha256(p.read_bytes()).hexdigest()!=m['sha256']:raise ValueError('Existing prefix integrity failure')
print('Frozen degree40 prefix verified; full model not downloaded')
