"""Verify an uncompressed TAR and stage only the original NCAR summer primary."""
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile
import tempfile

import import_summer_handoff_v39 as v39

ROOT=v39.ROOT
OUT=ROOT/'experiments/thermosphere_ncar_junsol_acquisition_v40'
RAW=ROOT/'data/raw/thermosphere_ncar_junsol_acquisition_v40'
STAGING=v39.HOME_DIR/'staging'
SEED=v39.SEED
TAR_LIMIT=2*2**30
SEED_LIMIT=20*2**20
ARCHIVE_NAME='tiegcm2.0_res5.0_data.tar'
FILE_URL=f'https://www.hao.ucar.edu/modeling/tgcm/download/files/{ARCHIVE_NAME}'
PUBLIC_FORM='https://www.hao.ucar.edu/modeling/tgcm/download.php'
REG_URL=f'https://registration.hao.ucar.edu/hao-reg_file-deliver.php?file={FILE_URL}&referer={PUBLIC_FORM}&instrument=tiegcm'


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def checked(path):
    p=Path(path).absolute()
    require(p.is_relative_to(ROOT/'data/raw') and p.resolve(strict=True)==p,'Require a local non-symlink file in data/raw')
    return p


def inspect_archive(path, *, member_limit=SEED_LIMIT, max_archive=TAR_LIMIT, target=None):
    """Visit all uncompressed TAR headers, then hash and optionally copy the exact member."""
    p=checked(path)
    flags=os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK
    with os.fdopen(os.open(p,flags),'rb') as stream:
        before=os.fstat(stream.fileno())
        size=before.st_size
        require(stat.S_ISREG(before.st_mode) and 1024<=size<=max_archive and size%512==0,
                'TAR file type, bound or block alignment violated')
        count=0
        found=None
        with tarfile.open(fileobj=stream,mode='r:') as archive:
            for member in archive:
                count+=1
                require(count<=100_000,'Excessive member count')
                raw=member.name
                rel=PurePosixPath(raw)
                require(raw and not rel.is_absolute() and '..' not in rel.parts and '\\' not in raw
                        and not any(ord(ch)<32 for ch in raw),'Unsafe TAR path')
                require(member.isdir() or (member.isreg() and not member.sparse),
                        'Links, special or sparse TAR members rejected')
                require(0<=member.size<=size and member.offset_data+member.size<=size,
                        'Member extends outside TAR')
                if rel.name==SEED:
                    require(found is None,'Duplicate target TAR member')
                    require(member.isreg() and 0<member.size<=member_limit,'Invalid target length or type')
                    found=member
            terminal=archive.offset
            require(found is not None,'Required target TAR member missing')
            require(0<=terminal<=size-1024,'Missing two TAR end marker blocks')
            stream.seek(terminal)
            for block in iter(lambda:stream.read(1024*1024),b''):
                require(not any(block),'Nonzero data after TAR terminator or corrupt header')
            stream.seek(0)
            tar_sha=hashlib.sha256()
            for block in iter(lambda:stream.read(1024*1024),b''):
                tar_sha.update(block)
            src=archive.extractfile(found)
            require(src is not None,'Cannot read regular TAR member')
            count_member=0
            seed_sha=hashlib.sha256()
            output=target.open('xb') if target else None
            try:
                with src:
                    for block in iter(lambda:src.read(131072),b''):
                        count_member+=len(block)
                        require(count_member<=found.size,'Member length exceeded')
                        seed_sha.update(block)
                        if output:
                            output.write(block)
                require(count_member==found.size,'Member data truncated')
            finally:
                if output:
                    output.close()
        after=os.fstat(stream.fileno())
        require((before.st_size,before.st_mtime_ns,before.st_ctime_ns)==
                (after.st_size,after.st_mtime_ns,after.st_ctime_ns),'TAR changed during inspection')
    return dict(tar_status='NCAR_TAR_VERIFIED',tar_path=str(p.relative_to(ROOT)),tar_size=size,
                tar_SHA256=tar_sha.hexdigest(),regular_directory_entries=count,
                member_path=found.name,member_size=found.size,member_SHA256=seed_sha.hexdigest(),
                member_status='JUNSOL_MEMBER_EXTRACTED' if target else 'TARGET_VERIFIED_NOT_WRITTEN')


def dump_exclusive(path,value):
    with path.open('x') as f:
        json.dump(value,f,indent=2,allow_nan=False)
        f.write('\n')


def extract(path, *, date_text, source_url):
    v39.protect()
    v39.check_directories(v39.HOME_DIR)
    require(OUT.resolve(strict=True)==OUT and RAW.resolve(strict=True)==RAW,'Unexpected output directory')
    require(date.fromisoformat(date_text).isoformat()==date_text,'Use YYYY-MM-DD download/import date')
    require(source_url in (REG_URL,FILE_URL,PUBLIC_FORM),'Use one credential-free NCAR official source URL')
    target=STAGING/SEED
    sidecar=STAGING/(SEED+'.source.json')
    lock=STAGING/'.v40-junsol-import-lock'
    lock.mkdir()
    try:
        require(not any(p.exists() or p.is_symlink() for p in (target,sidecar)),
                'Staged original or source receipt already exists')
        with tempfile.TemporaryDirectory(dir=RAW,prefix='.member-') as work:
            original=Path(work)/SEED
            result=inspect_archive(path,target=original)
            require(v39.sha(original)==result['member_SHA256'],'Written member SHA mismatch')
            full=dict(result,UTC=datetime.now(timezone.utc).isoformat(),download_or_import_date=date_text,
                     registration_URL=REG_URL,declared_official_source_URL=source_url,
                     release='TIE-GCM 2.0 5 degree startup and data',OFFICIAL_PROVENANCE_VERIFIED=False,
                     static_status='NOT_YET_VERIFIED',target_density_reads=0)
            receipt=OUT/f"member_{result['tar_SHA256']}_{result['member_SHA256']}_local.json"
            try:
                full['native']=v39.inspect_seed(original)
                full['static_status']='PRECHECK_PASS_V39_ADMISSION_REQUIRED'
            except (ValueError,OSError,KeyError) as exc:
                full['static_status']='JUNSOL_SEED_INCOMPATIBLE'
                full['reason']=str(exc)
                dump_exclusive(receipt,full)
                raise
            declaration=dict(download_url=source_url,download_date=date_text,
                file_sha256=result['member_SHA256'],source_note=(
                    f"NCAR TAR handoff, publisher provenance not independently attested; "
                    f"archive SHA256 {result['tar_SHA256']}; member path {result['member_path']}"))
            # Serialize provenance before final links and keep the archive untouched.
            note=Path(work)/sidecar.name
            dump_exclusive(note,declaration)
            original.chmod(0o444)
            note.chmod(0o444)
            dump_exclusive(receipt,full)
            os.link(note,sidecar)
            try:
                os.link(original,target)
            except OSError:
                sidecar.unlink()
                raise
            print(receipt.relative_to(ROOT))
            return full
    finally:
        lock.rmdir()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tar',type=Path)
    parser.add_argument('--source-url',default=PUBLIC_FORM)
    parser.add_argument('--date',required=True,help='Official download or local import date (YYYY-MM-DD)')
    args=parser.parse_args()
    try:
        extract(args.tar,date_text=args.date,source_url=args.source_url)
    except (ValueError,OSError,KeyError,tarfile.TarError) as exc:
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        dump_exclusive(OUT/f'extract_failure_{stamp}_local.json',
            dict(state='NCAR_TAR_OR_MEMBER_REJECTED',reason=str(exc),target_density_reads=0))
        raise SystemExit(str(exc))


if __name__=='__main__':
    main()
