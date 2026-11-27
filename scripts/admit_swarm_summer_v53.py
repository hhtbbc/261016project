"""Locate and snapshot uploaded ZIPs, then replay frozen V39 admission."""
from contextlib import contextmanager
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import stat
import tempfile
from unittest.mock import patch
import zipfile

from cdflib import CDF
import import_summer_handoff_v39 as handoff
import verify_summer_handoff_v39 as verify
from runtime.tiegcm_rank_exit import write_once

ROOT = handoff.ROOT
OUT = ROOT/'experiments/thermosphere_swarm_summer_metadata_v53'
PRODUCTS = {name:day for name,day in handoff.PRODUCTS.items() if day}
FIELDS = tuple(handoff.audit.DATA_FIELDS)


@contextmanager
def sealed_access(log):
    original = CDF.varget
    def read(cdf, variable, *a, **kw):
        allowed = variable in FIELDS
        log.append(dict(variable=variable,allowed=allowed))
        if not allowed:
            raise ValueError('Sealed CDF variable')
        return original(cdf,variable,*a,**kw)
    with patch.object(CDF,'varget',read):
        yield


def archive(path):
    if path.resolve(strict=True)!=path or not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError(f'Unsafe uploaded ZIP: {path}')
    stream,size=handoff.open_bounded(path,2**19)
    with stream:
        magic=stream.read(4)
        if magic!=b'PK\x03\x04':
            raise ValueError('Unexpected ZIP signature')
        stream.seek(0)
        with zipfile.ZipFile(stream) as z:
            entries=z.infolist()
            if any(x.compress_type not in {zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED}
                   or x.flag_bits&1 or stat.S_ISLNK(x.external_attr>>16) for x in entries):
                raise ValueError('Unsupported compression or encryption')
            names=[x.filename for x in entries]
            candidates=[n for n in PRODUCTS if set(names)=={Path(n).stem+'.cdf',Path(n).stem+'.HDR'}]
            if len(entries)!=2 or len(candidates)!=1 or sum(x.file_size for x in entries)>2**20:
                raise ValueError('Unknown or unsafe member inventory')
            if z.testzip() is not None:
                raise ValueError('ZIP CRC failed')
            return dict(path=str(path),bytes=size,mtime_UTC=datetime.fromtimestamp(
                path.stat().st_mtime,timezone.utc).isoformat(),SHA256=handoff.sha(path),
                ZIP_magic=magic.hex(),ZIP_CRC='PASS',members=[
                    dict(name=x.filename,bytes=x.file_size,ZIP_CRC32=f'{x.CRC:08x}') for x in entries],
                product=candidates[0],regular_file=True,symlink=False)


def discover():
    matches={name:[] for name in PRODUCTS}
    # Search by basename, pruning environments, model repositories and build caches.
    ignored={'.git','.envs','.tmp','__pycache__','third_party','node_modules'}
    pattern=re.compile(r'^SW_OPER_DNSAPOD_2__202[12]0621T000000_202[12]0621T235930_0301.*\.ZIP(?:.*)?$',re.I)
    for base,dirs,files in os.walk(ROOT,followlinks=False):
        dirs[:]=[n for n in dirs if n not in ignored and not n.startswith('.venv')]
        for file in files:
            if pattern.fullmatch(file):
                candidate=archive(Path(base)/file)
                matches[candidate['product']].append(candidate)
    for name,candidates in matches.items():
        if not candidates or len({x['SHA256'] for x in candidates})!=1:
            raise ValueError(f'Missing or conflicting ZIP copies: {name}')
    return matches


def main():
    if OUT.resolve()!=OUT:
        raise ValueError('Unsafe output path')
    protected=handoff.protect()
    handoff.check_directories(handoff.HOME_DIR)
    found=discover()
    staged={}
    for name,candidates in found.items():
        record=min(candidates,key=lambda r:len(Path(r['path']).parts))
        path=Path(record['path'])
        target=handoff.HOME_DIR/'staging'/name
        if os.path.lexists(target):
            if archive(target)['SHA256']!=record['SHA256']:
                raise ValueError(f'Staging conflict: {name}')
        else:
            # Write a verified sibling before publishing the ordinary file without replacement.
            with tempfile.TemporaryDirectory(dir=target.parent,prefix='.v53-stage-') as tmp:
                copy=Path(tmp)/name
                size,digest=handoff.snapshot(path,copy,2**19)
                if (size,digest)!=(record['bytes'],record['SHA256']):
                    raise ValueError('Source changed since discovery')
                copy.chmod(0o444)
                os.link(copy,target,follow_symlinks=False)
        if handoff.sha(path)!=handoff.sha(target):
            raise ValueError('Source/staging SHA mismatch')
        staged[name]=str(target.relative_to(ROOT))
    write_once(OUT/'handoff.json',dict(protected=protected,uploads=found,staging=staged))
    log=[]
    with sealed_access(log):
        rows=[handoff.inspect_one(handoff.HOME_DIR,name) for name in PRODUCTS]
        independently_accepted=verify.verify_accepted()
    write_once(OUT/'V39_admission.json',dict(importer=rows,V39_independent=independently_accepted,
        accessed=log,target_density_reads=0))


if __name__=='__main__':
    main()
