"""Prepare isolated external validation binary; does not install into Python env."""
import json,hashlib,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 meta=json.loads((ROOT/'configs/spherical_reference.json').read_text());p=ROOT/meta['wheel_path'];dest=ROOT/meta['isolated_directory']
 for q in [p,dest]:q.resolve().relative_to(ROOT)
 if not p.exists():
  with urllib.request.urlopen(meta['wheel_url'],timeout=45) as r:data=r.read(meta['wheel_size_bytes']+1)
  if len(data)!=meta['wheel_size_bytes'] or hashlib.sha256(data).hexdigest()!=meta['wheel_sha256']:raise ValueError('Download integrity failure')
  p.write_bytes(data)
 if hashlib.sha256(p.read_bytes()).hexdigest()!=meta['wheel_sha256']:raise ValueError('Wheel integrity failure')
 if dest.exists():print('Existing reference retained; wheel SHA verified');return
 dest.mkdir(parents=True)
 with zipfile.ZipFile(p) as z:
  for n in z.namelist():
   (dest/n).resolve().relative_to(dest.resolve())
   if n.startswith(('pyshtools/','pyshtools.libs/')):z.extract(n,dest)
 print('Isolated Fortran reference ready; full pyshtools API/dependencies not installed')
if __name__=='__main__':main()
