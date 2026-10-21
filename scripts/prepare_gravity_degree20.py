"""Fetch ONLY the frozen 64KiB prefix if absent; no full model download."""
import json,hashlib,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];m=json.loads((ROOT/'configs/egm2008_degree20_source.json').read_text());p=ROOT/'data/raw/gravity_sources/EGM2008_DEG20_PREFIX.gfc';p.resolve().relative_to(ROOT)
if not p.exists():
 with urllib.request.urlopen(m['url'],timeout=40) as r:data=r.read(m['bytes_read'])
 if hashlib.sha256(data).hexdigest()!=m['sha256']:raise ValueError('Source changed; stop instead of substituting coefficients')
 p.write_bytes(data)
if hashlib.sha256(p.read_bytes()).hexdigest()!=m['sha256']:raise ValueError('Existing prefix SHA mismatch; preserve and investigate')
print('Frozen 64KiB source prefix verified; no full model download')
