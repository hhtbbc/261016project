"""Official apex update overlay; leaves original 2.0 and previous builds intact."""
from pathlib import Path
import subprocess,sys,json,hashlib,difflib,re
ROOT=Path(__file__).resolve().parents[1]
tag='tiegcm2_apex2023_v1';output=ROOT/'experiments'/tag
meta=json.loads((ROOT/'data/raw/tiegcm2023_sources/apex_current_commit.json').read_text())[0]
archived=json.loads((ROOT/'data/raw/meeting_sources/tiegcm_apex_latest_commit.txt').read_text())[0]
if meta['sha']!=archived['sha']:raise RuntimeError('Official apex changed: review new file before use')
new=ROOT/'data/raw/meeting_sources/tiegcm_apex_update.txt'
if not output.exists():subprocess.run([sys.executable,str(ROOT/'scripts/build_tiegcm2_workspace.py'),'--build-tag',tag],check=True)
(output/'apex.F90').write_bytes(new.read_bytes())
files=(output/'Srcfiles').read_text().splitlines();assert sum(x in ('apex.F','apex.F90') for x in files)==1
files=[x for x in files if x not in ('apex.F','apex.F90')];files.append('apex.F90');(output/'Srcfiles').write_text('\n'.join(sorted(files))+'\n')
patch=''.join(difflib.unified_diff((ROOT/'third_party/TIEGCM2.0/src/apex.F90').read_text().splitlines(True),new.read_text().splitlines(True),fromfile='a/src/apex.F90',tofile='b/src/apex.F90'))
p=ROOT/'configs/patches/tiegcm2_official_apex2023.patch';p.write_text(patch)
record={'official_notice':'https://www.hao.ucar.edu/modeling/tgcm/index.php','commit':meta['sha'],'raw_url':f'https://raw.githubusercontent.com/NCAR/tiegcm/{meta["sha"]}/src/apex.F90','source_sha256':hashlib.sha256(new.read_bytes()).hexdigest(),'patch_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'old_source_sha256':hashlib.sha256((ROOT/'third_party/TIEGCM2.0/src/apex.F90').read_bytes()).hexdigest(),'original_source_preserved':True,'source_list_apex_entries':[x for x in files if x.startswith('apex.')],'version_label':'TIE-GCM2.0 + official 2025 apex/IGRF14 update + recorded GNU12 compatibility overlays'}
(output/'apex_provenance.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
