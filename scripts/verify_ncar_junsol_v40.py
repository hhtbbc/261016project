"""V40 bounded archive/downloader tests and independent check of staged native originals."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import resource
import subprocess
import tarfile
import tempfile
from time import monotonic
import unittest
from unittest.mock import MagicMock

from netCDF4 import Dataset
import numpy as np

import download_ncar_v40 as net
import extract_ncar_junsol_v40 as tar
import import_summer_handoff_v39 as v39
from verify_summer_handoff_v39 import Handoff, V38Fixtures, verify_accepted
from atmosphere.restart_validation import REQUIRED

BASE='4da58915638aa3c8e0f2f912799803406f1f7d7b'
ROOT=tar.ROOT
V39=ROOT/'experiments/thermosphere_summer_asset_handoff_v39'
NAME='data/tiegcm/'+tar.SEED


class V40(unittest.TestCase):
    def setUp(self):
        work=tempfile.TemporaryDirectory(dir=tar.RAW)
        self.addCleanup(work.cleanup)
        self.folder=Path(work.name)
        self.path=self.folder/'fixture.tar'

    def make(self,*members):
        with tarfile.open(self.path,'w') as archive:
            for name,data in members:
                info=tarfile.TarInfo(name)
                if data is None:
                    info.type=tarfile.SYMTYPE
                    info.linkname='other'
                    archive.addfile(info)
                else:
                    info.size=len(data)
                    archive.addfile(info,io.BytesIO(data))

    def test_strict_target_only_copy(self):
        self.make(('other.nc',b'other'),(NAME,b'original'))
        target=self.folder/'extracted'
        result=tar.inspect_archive(self.path,target=target)
        self.assertEqual(result['member_path'],NAME)
        self.assertEqual(result['member_SHA256'],hashlib.sha256(b'original').hexdigest())
        self.assertEqual(result['tar_SHA256'],hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(target.read_bytes(),b'original')
        self.assertFalse((self.folder/'other.nc').exists())

    def test_real_tar_wrong_extension(self):
        self.make((NAME,b'original'))
        path=self.path.rename(self.folder/'upload.blob')
        self.assertEqual(tar.inspect_archive(path)['member_size'],8)

    def test_fake_tar(self):
        self.path.write_bytes(b'<html>'+bytes(1530))
        with self.assertRaises((ValueError,tarfile.TarError)):
            tar.inspect_archive(self.path)

    def test_truncated_and_extra_junk(self):
        self.make((NAME,b'original'))
        data=self.path.read_bytes()
        for body in (data[:1536],data[:1510],data+b'junk'+bytes(508)):
            self.path.write_bytes(body)
            with self.assertRaises(ValueError):
                tar.inspect_archive(self.path)

    def test_path_traversal_and_absolute_path(self):
        for base in ('../foo','/absolute','parent/../../bad'):
            self.make((NAME,b'original'),(base,b'invalid'))
            with self.assertRaisesRegex(ValueError,'Unsafe'):
                tar.inspect_archive(self.path)

    def test_symlink_and_hardlink(self):
        self.make((NAME,None))
        with self.assertRaisesRegex(ValueError,'Links'):
            tar.inspect_archive(self.path)
        with tarfile.open(self.path,'w') as archive:
            member=tarfile.TarInfo(NAME)
            member.type=tarfile.LNKTYPE
            member.linkname='other'
            archive.addfile(member)
        with self.assertRaisesRegex(ValueError,'Links'):
            tar.inspect_archive(self.path)

    def test_source_symlink_rejected(self):
        self.make((NAME,b'original'))
        link=self.folder/'shortcut.tar'
        link.symlink_to(self.path)
        with self.assertRaisesRegex(ValueError,'non-symlink'):
            tar.inspect_archive(link)

    def test_duplicate_basename(self):
        self.make((NAME,b'original'),('second/'+tar.SEED,b'other'))
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            tar.inspect_archive(self.path)

    def test_target_limit(self):
        self.make((NAME,b'0123'))
        with self.assertRaisesRegex(ValueError,'target length'):
            tar.inspect_archive(self.path,member_limit=2)

    def test_missing_target(self):
        self.make(('different.nc',b'other'))
        with self.assertRaisesRegex(ValueError,'missing'):
            tar.inspect_archive(self.path)

    def test_email_redirect_recognized(self):
        self.assertTrue(net.is_registration('https://registration.hao.ucar.edu/hao-reg_email.php?file=x'))
        self.assertFalse(net.is_registration('https://outside.example/hao-reg_email.php'))

    def test_html_not_archive(self):
        self.assertFalse(net.binary({'Content-Type':'text/html; charset=utf-8'}))

    def test_bounded_range_fallback(self):
        first=tarfile.TarInfo(NAME).tobuf()
        response=MagicMock(status=206,headers={'Content-Range':'bytes 0-511/10240',
                                              'Content-Length':'512'})
        response.read.return_value=first
        result=net.range_metadata(tar.FILE_URL,response,{'Content-Type':'application/x-tar'})
        self.assertEqual(result['size'],10240)
        response.read.assert_called_once_with(512)
        response.status=200
        response.read.reset_mock()
        with self.assertRaises(ValueError):
            net.range_metadata(tar.FILE_URL,response,{'Content-Type':'application/x-tar'})
        response.read.assert_not_called()

    def test_resume_exact_version(self):
        d=dict(url=tar.FILE_URL,size=2048,etag='"v1"',ranges=True)
        self.assertEqual(net.resume_headers(d,d,1024),{'Range':'bytes=1024-','If-Range':'"v1"'})
        for prior in (dict(d,etag='"different"'),dict(d,url=tar.REG_URL),None):
            with self.assertRaises(ValueError):
                net.resume_headers(d,prior,1024)

    def test_resume_no_ranges_or_weak_etag(self):
        for d in (dict(url=tar.FILE_URL,size=2048,etag='W/"v1"',ranges=True),
                  dict(url=tar.FILE_URL,size=2048,etag='"v1"',ranges=False)):
            with self.assertRaises(ValueError):
                net.resume_headers(d,d,1024)

    def test_get_resume_mismatch(self):
        d=dict(url=tar.FILE_URL,size=2048,etag='"v1"',ranges=True)
        headers={'Content-Type':'application/x-tar','Content-Length':'1024','ETag':'"v1"',
                 'Content-Range':'bytes 1024-2047/2048'}
        net.validate_reply(206,headers,d,1024)
        for status,changed in ((200,headers),(206,headers|{'ETag':'"v2"'}),
                               (206,headers|{'Content-Range':'bytes 0-1023/2048'})):
            with self.assertRaises(ValueError):
                net.validate_reply(status,changed,d,1024)


def history():
    counts=v39.protect()
    pub=V39/'publication_SHA256.json'
    blob=subprocess.check_output(['git','show',f'{BASE}:{pub.relative_to(ROOT)}'],cwd=ROOT)
    assert blob==pub.read_bytes()
    manifest=json.loads(blob)
    for name,sha in manifest.items():
        p=ROOT/name
        assert p.resolve(strict=True)==p and v39.sha(p)==sha
    ref=json.loads(v39.audit.V27.read_text())
    p=ROOT/ref['physical_paths']['source']
    assert v39.sha(p)==ref['physical_SHA256']['source']
    return counts|{'V39':len(manifest),'mareqx_SHA256':ref['physical_SHA256']['source']}


def independent_native():
    ready=v39.HOME_DIR/'accepted'/tar.SEED
    if not ready.is_dir():
        return None
    reviews=verify_accepted()
    p=ready/tar.SEED
    receipt=json.loads((ready/'receipt.json').read_text())
    native=receipt['contract']['native']
    with Dataset(p,'r') as n:
        assert n.history_type=='primary' and n.data_model==native['NetCDF_format']
        assert n['year'][:].tolist()==native['years'] and n['mtime'][0].tolist()==native['SOURCE_START']
        assert tuple(len(n.dimensions[k]) for k in ('lat','lon','lev','ilev'))==(36,72,29,29)
        assert len(REQUIRED)==34 and set(REQUIRED)<=set(n.variables)
        for record in native['state_values']:
            variable=n[record['variable']]
            assert list(variable.dimensions)==record['dimensions'] and getattr(variable,'units','')==record['units']
            variable.set_auto_mask(False)
            source=np.asarray(variable[:])
            absent=np.abs(source)>1e30
            for key in ('_FillValue','missing_value'):
                if key in variable.ncattrs():
                    absent|=np.isin(source,np.asarray(variable.getncattr(key),dtype=source.dtype))
            assert np.isfinite(source).all() and np.count_nonzero(~absent)==record['valid_count']
            valid=source[~absent]
            assert valid.min()==record['min_valid'] and valid.max()==record['max_valid']
    return dict(member_SHA256=v39.sha(p),SOURCE_START=native['SOURCE_START'],
                native_calendar=native['actual_calendar_records'],verified_assets=reviews)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--accepted-only',action='store_true')
    args=parser.parse_args()
    start=monotonic()
    hashes=history()
    count=0
    if not args.accepted_only:
        suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(k)
                                 for k in (V38Fixtures,Handoff,V40))
        result=unittest.TextTestRunner().run(suite)
        if not result.wasSuccessful():
            raise SystemExit(1)
        count=result.testsRun
    native=independent_native()
    report=dict(UTC=datetime.now(timezone.utc).isoformat(),CPU_tests=count,failures=0,
                historical_protection=hashes,real_accepted=verify_accepted(),real_junsol_native=native,
                unseen_density_reads=0,new_GPI=0,new_formal_input=0,model_runs=0,GPU=0,
                wall_s=monotonic()-start,peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    dest=tar.OUT/f'accepted_review_{stamp}_local.json' if args.accepted_only else tar.OUT/'verification.json'
    tar.dump_exclusive(dest,report)
    print(dest.relative_to(ROOT))


if __name__=='__main__':
    main()
