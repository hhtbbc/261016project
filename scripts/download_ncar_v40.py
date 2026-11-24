"""Bounded NCAR delivery probe and resumable download without registration bypass."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tarfile
from time import monotonic
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request

from extract_ncar_junsol_v40 import (
    ARCHIVE_NAME, FILE_URL, REG_URL, OUT, RAW, TAR_LIMIT, dump_exclusive, inspect_archive, require,
)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None


def request(url,method,headers=None):
    require(url in (REG_URL,FILE_URL),'Unrecognized official delivery URL')
    try:
        return build_opener(NoRedirect()).open(Request(url,method=method,
                headers={'Accept-Encoding':'identity'} | (headers or {})),timeout=25)
    except HTTPError as exc:
        return exc


def header_snapshot(response,url):
    headers={k:response.headers.get(k) for k in (
        'Content-Type','Content-Length','Content-Disposition','Accept-Ranges','ETag','Last-Modified')}
    loc=response.headers.get('Location')
    resolved=urljoin(url,loc) if loc else None
    public_location = (resolved if resolved==FILE_URL else
        'https://registration.hao.ucar.edu/hao-reg_email.php' if is_registration(resolved) else
        'WITHHELD_UNVERIFIED_REDIRECT' if resolved else None)
    return dict(URL=url,status=response.status,headers=headers,Location=public_location,
                TLS_hostname_verified=True,request_body_bytes=0)


def is_registration(url):
    if not url:
        return False
    parts=urlsplit(url)
    return parts.scheme=='https' and parts.netloc=='registration.hao.ucar.edu' and parts.path=='/hao-reg_email.php'


def binary(headers):
    ct=headers.get('Content-Type','') or ''
    return ct.split(';')[0].strip().lower() in (
        'application/x-tar','application/tar','application/octet-stream','application/x-gtar'
    )


def deliver_metadata(url,headers):
    require(binary(headers),'Response is not a TAR delivery content type')
    length=int(headers['Content-Length'])
    require(1024<=length<=TAR_LIMIT and length%512==0,'Archive length missing or outside bound')
    disposition=headers.get('Content-Disposition')
    if disposition:
        require(ARCHIVE_NAME in disposition,'Unexpected attachment filename')
    return dict(url=url,size=length,etag=headers.get('ETag'),
                ranges=(headers.get('Accept-Ranges') or '').lower()=='bytes')


def range_metadata(url,response,headers):
    require(response.status==206 and binary(headers),'No direct bounded TAR delivery')
    match=re.fullmatch(r'bytes 0-511/([0-9]+)',response.headers.get('Content-Range',''))
    require(match is not None and response.headers.get('Content-Length')=='512'
            and response.headers.get('Content-Encoding','identity')=='identity',
            'Range HEAD fallback did not return a bounded first block')
    # Header bytes only; refuse an HTML or malformed first TAR header.
    first=response.read(512)
    require(len(first)==512 and any(first),'Missing TAR first block')
    tarfile.TarInfo.frombuf(first,'utf-8','strict')
    return deliver_metadata(url,headers|{'Content-Length':match[1],'Accept-Ranges':'bytes'})


def probe():
    url=REG_URL
    attempts=[]
    for _ in range(2):
        try:
            with request(url,'HEAD') as response:
                loc=response.headers.get('Location')
                resolved=urljoin(url,loc) if loc else None
                entry=header_snapshot(response,url)
                attempts.append(entry)
                if response.status in (301,302,303,307,308) and is_registration(resolved):
                    return dict(state='NCAR_DOWNLOAD_REGISTRATION_REQUIRED',delivery=None,attempts=attempts,
                                stopped_before_form=True)
                if response.status in (301,302,303,307,308) and resolved==FILE_URL and url!=FILE_URL:
                    url=FILE_URL
                    continue
                if response.status in (405,501):
                    with request(url,'GET',{'Range':'bytes=0-511'}) as partial:
                        bounded=header_snapshot(partial,url)
                        bounded['method']='GET Range bytes=0-511'
                        attempts.append(bounded)
                        delivery=range_metadata(url,partial,bounded['headers'])
                        bounded['response_body_bytes_read']=512
                    return dict(state='DIRECT_OFFICIAL_TAR_AVAILABLE',delivery=delivery,attempts=attempts)
                if response.status==200 and binary(entry['headers']):
                    return dict(state='DIRECT_OFFICIAL_TAR_AVAILABLE',
                                delivery=deliver_metadata(url,entry['headers']),attempts=attempts)
                return dict(state='NCAR_DOWNLOAD_FAILED',delivery=None,attempts=attempts,
                            reason='No authorized binary delivery established by HEAD')
        except (OSError,ValueError,KeyError,TypeError,tarfile.TarError) as exc:
            return dict(state='NCAR_DOWNLOAD_FAILED',delivery=None,attempts=attempts,
                        reason=f'{type(exc).__name__}: {exc}')
    return dict(state='NCAR_DOWNLOAD_FAILED',delivery=None,attempts=attempts,reason='Redirect bound exceeded')


def resume_headers(delivery,prior,offset):
    if offset==0:
        return {}
    etag=delivery['etag']
    require(prior==delivery and 0<offset<delivery['size'] and delivery['ranges']
            and isinstance(etag,str) and re.fullmatch(r'"[^"]+"',etag),
            'Cannot resume without exact URL, size, byte ranges and unchanged strong ETag')
    return {'Range':f'bytes={offset}-','If-Range':etag}


def validate_reply(status,headers,delivery,offset):
    require(binary(headers) and headers.get('Content-Encoding','identity')=='identity',
            'Nonbinary or encoded response rejected')
    if delivery['etag']:
        require(headers.get('ETag')==delivery['etag'],'GET version differs from HEAD')
    if offset:
        require(status==206 and headers.get('Content-Range')==
                f"bytes {offset}-{delivery['size']-1}/{delivery['size']}",'Resume range mismatch')
    else:
        require(status==200,'Initial GET must return HTTP 200')
    require(int(headers.get('Content-Length',-1))==delivery['size']-offset,'GET length mismatch')


def transfer(delivery):
    require(RAW.resolve(strict=True)==RAW and shutil.disk_usage(RAW).free>=5*2**30,'Need 5 GiB free')
    final=RAW/ARCHIVE_NAME
    part=RAW/(ARCHIVE_NAME+'.part')
    identity=RAW/(ARCHIVE_NAME+'.part.source.json')
    require(not final.exists() and not final.is_symlink(),'Existing archive preserved')
    require(not part.is_symlink() and not identity.is_symlink(),'Symlink partial rejected')
    lock=RAW/'.ncar-download-lock'
    lock.mkdir()
    try:
        if part.exists():
            require(stat.S_ISREG(part.stat().st_mode),'Partial must be a regular file')
        if identity.exists():
            require(stat.S_ISREG(identity.stat().st_mode),'Provenance must be a regular file')
        offset=part.stat().st_size if part.exists() else 0
        prior=json.loads(identity.read_text()) if identity.exists() else None
        require(prior is None or prior==delivery,'Partial provenance changed')
        if offset!=delivery['size']:
            extra=resume_headers(delivery,prior,offset)
            with request(delivery['url'],'GET',extra) as response:
                validate_reply(response.status,response.headers,delivery,offset)
                if prior is None:
                    dump_exclusive(identity,delivery)
                with part.open('ab' if part.exists() else 'xb') as stream:
                    left=delivery['size']-offset
                    deadline=monotonic()+1800
                    while left:
                        require(monotonic()<deadline,'Transfer time bound exceeded')
                        chunk=response.read(min(left,1024*1024))
                        require(chunk,'Transfer dropped; partial preserved')
                        stream.write(chunk)
                        left-=len(chunk)
                    stream.flush()
                    os.fsync(stream.fileno())
        else:
            require(prior==delivery,'Complete-size partial has no bound version')
        require(part.stat().st_size==delivery['size'],'Final body byte count mismatch')
        manifest=inspect_archive(part)
        os.link(part,final)
        part.unlink()
        manifest['tar_path']=str(final.relative_to(RAW.parents[2]))
        manifest.update(delivery_metadata=delivery,OFFICIAL_PROVENANCE_VERIFIED=True,
                        state='NCAR_TAR_ACQUIRED')
        return manifest
    finally:
        lock.rmdir()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download',action='store_true',help='Only transfer an officially delivered binary')
    args=parser.parse_args()
    require(OUT.resolve(strict=True)==OUT and RAW.resolve(strict=True)==RAW,'Unexpected project directories')
    report=probe()
    report.update(UTC=datetime.now(timezone.utc).isoformat(),method='HEAD only before direct delivery',
                  no_credentials_or_form_submission=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    path=OUT/f'http_probe_{stamp}_local.json'
    dump_exclusive(path,report)
    print(path.name,report['state'],flush=True)
    if args.download and report['delivery']:
        try:
            result=transfer(report['delivery'])
        except Exception as exc:
            result=dict(state='NCAR_DOWNLOAD_FAILED',reason=str(exc),partial_may_be_present=True)
        dump_exclusive(OUT/f'transfer_{stamp}_local.json',result)
        print(result['state'])


if __name__=='__main__':
    main()
