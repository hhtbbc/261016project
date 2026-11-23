"""Validate and quarantine-accept exact summer assets without accessing target density."""
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
from urllib.parse import urlsplit
import zipfile

import audit_summer_assets_v38 as audit
from fetch_summer_assets_v38 import ROOT, DAYS, SEED, history_pins
from observations.bounded_swarm_acquisition import Budget, extract_members, sha

BASE = '26a28cfbe8ce2e05ba15755618ca411bf841579e'
NAME = 'thermosphere_summer_asset_handoff_v39'
HOME_DIR = ROOT/'data/raw/thermosphere_summer_data_handoff_v39'
OUT = ROOT/'experiments'/NAME
V38 = ROOT/'experiments/thermosphere_summer_data_acquisition_v38'
PRODUCTS = {f"SW_OPER_DNSAPOD_2__{d.replace('-','')}T000000_{d.replace('-','')}T235930_0301.ZIP": d
            for d in DAYS}
PRODUCTS[SEED] = None
TRUSTED_UPSTREAM_SHA256 = {}  # No independently authenticated publisher checksum in V39.


def require(ok, detail):
    if not ok:
        raise ValueError(detail)


def protect():
    pub=V38/'publication_SHA256.json'
    blob=subprocess.check_output(['git','show',f'{BASE}:{pub.relative_to(ROOT)}'],cwd=ROOT)
    require(pub.read_bytes()==blob,'V38 publication mismatch')
    pins=json.loads(blob)
    for name,expected in (pins['published']|pins['original_local_only']).items():
        p=ROOT/name
        require(p.resolve(strict=True)==p and sha(p)==expected,f'Changed V38 asset: {name}')
    return {k:len(v) for k,v in pins.items()} | {'V37':len(history_pins())}


def check_directories(base):
    for path in (base,base/'staging',base/'accepted'):
        require(path.is_relative_to(ROOT) and path.resolve(strict=True)==path
                and path.is_dir(),'Unexpected handoff path')


def open_bounded(path,cap):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    src=os.fdopen(fd,'rb')
    try:
        info=os.fstat(src.fileno())
        require(stat.S_ISREG(info.st_mode) and 0<info.st_size<=cap,'Unsupported file or size')
        return src,info.st_size
    except Exception:
        src.close()
        raise


def snapshot(source, target, cap):
    s,size=open_bounded(source,cap)
    h=hashlib.sha256()
    count=0
    with s, target.open('xb') as out:
        for block in iter(lambda:s.read(65536),b''):
            count+=len(block)
            require(count<=cap,'Growing source exceeded size limit')
            out.write(block)
            h.update(block)
    require(count==size and sha(target)==h.hexdigest(),'Snapshot integrity mismatch')
    return count,h.hexdigest()


def provenance(sidecar, digest):
    if not sidecar.exists() and not sidecar.is_symlink():
        return None
    stream,_=open_bounded(sidecar,8192)
    with stream:
        raw=stream.read(8193)
    require(len(raw)<=8192,'Source declaration too large')
    obj=json.loads(raw)
    require(isinstance(obj,dict) and {'download_url','download_date','source_note'}<=obj.keys()
            and set(obj)<={'download_url','download_date','source_note','file_sha256'},'Source declaration schema')
    require(all(isinstance(v,str) and len(v)<=2048 for v in obj.values()),'Invalid source metadata')
    url=urlsplit(obj['download_url'])
    require(url.scheme=='https' and url.hostname and not url.username and not url.password
            and not url.fragment,'Use a public, credential-free HTTPS source URL')
    require(not re.search(r'(?i)(token|signature|credential|password|secret|session|auth=|key=)',url.query),
            'Do not store access credentials in source metadata')
    require(date.fromisoformat(obj['download_date']).isoformat()==obj['download_date'],'Date must be YYYY-MM-DD')
    if 'file_sha256' in obj:
        require(obj['file_sha256']==digest,'Uploader checksum mismatch')
    return obj


def inspect_seed(path):
    info=audit.seed_inspection(path)
    native=[datetime.fromisoformat(t) for t in info['actual_calendar_records']]
    require(info['primary_records']==1 and len(native)==1 and native[0].month==6
            and 19<=native[0].day<=24 and tuple(info['SOURCE_START'][1:])==(0,0),
            'Original summer-solstice 00:00 primary required')
    return info


def verify_content(path, name, destination):
    with path.open('rb') as stream:
        magic=stream.read(8)
    day=PRODUCTS[name]
    if day is None:
        require(magic.startswith((b'CDF\x01',b'CDF\x02',b'CDF\x05',b'\x89HDF\r\n\x1a\n')),
                'Not a NetCDF container')
        return dict(static_identity='JUNSOL_SEED_STATIC_COMPATIBLE',
                    native=inspect_seed(path),target_density_reads=0)
    require(magic.startswith(b'PK\x03\x04'),'Not a ZIP container')
    stem=audit.check_product_stem(Path(name).stem,day)
    members=extract_members(path,stem,Budget(extract_limit=2**20),destination)
    cp=destination/(stem+'.cdf')
    hp=destination/(stem+'.HDR')
    hdr=audit.verify_hdr(hp,stem,day,cp)
    accesses=[]
    meta=audit.verify_cdf(cp,stem,day,accesses)
    return dict(static_identity='METADATA_VERIFIED_DENSITY_SEALED', members=[
        dict(name=Path(m['path']).name,SHA256=m['SHA256'],bytes=m['bytes'],CRC32=m['CRC32'])
        for m in members], HDR=hdr, CDF=meta,accessed_data_variables=accesses,target_density_reads=0)


def inspect_one(base,name):
    check_directories(base)
    require(name in PRODUCTS,'Unregistered handoff name')
    staging=base/'staging'
    accepted=base/'accepted'
    source=staging/name
    final=accepted/name
    cap=20*2**20 if name==SEED else 2**19
    if not source.exists() and not source.is_symlink():
        return dict(file=name,status='ALREADY_ACCEPTED' if final.is_dir() else 'NOT_ACQUIRED')
    lock=accepted/('.lock-'+name)
    lock.mkdir()
    try:
        with tempfile.TemporaryDirectory(dir=accepted,prefix='.verify-') as tmp:
            folder=Path(tmp)
            content=folder/name
            count,digest=snapshot(source,content,cap)
            claimed=provenance(staging/(name+'.source.json'),digest)
            if final.exists() or final.is_symlink():
                require(final.is_dir() and not final.is_symlink() and sha(final/name)==digest,
                        'Same product name but different bytes; no replacement')
                return dict(file=name,status='DUPLICATE_ALREADY_ACCEPTED',SHA256=digest)
            checks=verify_content(content,name,folder)
            receipt=dict(file=name,size=count,SHA256=digest, BYTE_INTEGRITY_VERIFIED=True,
               PRODUCT_IDENTITY_VERIFIED=True,OFFICIAL_PROVENANCE_VERIFIED=(
                   TRUSTED_UPSTREAM_SHA256.get(name)==digest),
               uploader_claim=claimed,contract=checks,policy='SUMMER_SEED_POLICY_PENDING' if name==SEED else 'TARGET_DENSITY_SEALED')
            with (folder/'receipt.json').open('x') as f:
                json.dump(receipt,f,indent=2,allow_nan=False)
                f.write('\n')
            for p in folder.iterdir():
                p.chmod(0o444)
            os.rename(folder,final)
            final.chmod(0o555)
            return dict(file=name,status='ACCEPTED_STATIC_ONLY',
                        SHA256=digest,official_provenance=receipt['OFFICIAL_PROVENANCE_VERIFIED'])
    finally:
        lock.rmdir()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspect',action='store_true',help='Audit staging and accept verified static copies')
    parser.parse_args()
    evidence=protect()
    check_directories(HOME_DIR)
    rows=[]
    for name in PRODUCTS:
        try:
            rows.append(inspect_one(HOME_DIR,name))
        except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile) as exc:
            rows.append(dict(file=name,status='REJECTED',reason=str(exc)))
    current=dict(UTC=datetime.now(timezone.utc).isoformat(),protected_pins=evidence,
                 assets=rows,target_density_reads=0,new_GPI=0,new_formal_input=0,
                 new_model_runs=0,new_scores=0,GPU=0)
    with tempfile.NamedTemporaryFile(dir=OUT,prefix='import_receipt_',suffix='_local.json',
                                     mode='w',delete=False) as f:
        json.dump(current,f,indent=2)
        f.write('\n')
        print(Path(f.name).relative_to(ROOT))
    print(json.dumps(current,ensure_ascii=False,indent=2))
    if any(row['status']=='REJECTED' for row in rows):
        raise SystemExit(1)


if __name__=='__main__':
    main()
