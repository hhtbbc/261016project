"""Independently hash real handoffs and exercise the sealed static admission pipeline."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import tempfile
from time import monotonic
import unittest
from unittest.mock import patch
import zipfile

import numpy as np
from cdflib import CDF, cdfepoch, cdfwrite

import import_summer_handoff_v39 as h
from verify_summer_assets_v38 import Fixtures as V38Fixtures
from observations.bounded_swarm_acquisition import posix_cksum

A=next(iter(h.PRODUCTS))
DAY=h.DAYS[0]
ROOT=h.ROOT
OUT=h.OUT


def synthetic_zip(base):
    stem=Path(A).stem
    cdf=base/(stem+'.cdf')
    c=cdfwrite.CDF(cdf)
    c.write_globalattrs({'TITLE':{0:stem},'TIME SYSTEM':{0:'UTC'}})
    q=np.arange(2880)*30
    seconds=np.array([[2021,6,21,int(t//3600),int(t//60%60),int(t%60),0] for t in q])
    fields=[('time',31,'',cdfepoch.compute_epoch(seconds)),
            ('latitude',45,'deg',np.linspace(-80,80,len(q))),
            ('longitude',45,'deg',np.linspace(-170,170,len(q))),
            ('altitude',45,'m',np.full(len(q),450000.)),
            ('validity_flag',4,'',np.zeros(len(q),np.int32)),
            ('density',45,'kg/m3',np.full(len(q),np.nan))]
    for k,t,u,v in fields:
        c.write_var(dict(Variable=k,Data_Type=t,Num_Elements=1,Rec_Vary=True,Dim_Sizes=[]),
                    var_attrs={'UNITS':u},var_data=v)
    c.close()
    crc,n=posix_cksum(cdf)
    hdr=(f'<Earth_Explorer_Header><Fixed_Header><File_Name>{stem}</File_Name>'
         '<Mission>Swarm</Mission><File_Type>DNSAPOD_2_</File_Type><File_Version>0301</File_Version>'
         '<Validity_Period><Validity_Start>UTC=2021-06-21T00:00:00</Validity_Start>'
         '<Validity_Stop>UTC=2021-06-21T23:59:30</Validity_Stop></Validity_Period></Fixed_Header>'
         f'<Variable_Header><MPH><CRC>{crc}</CRC><Tot_Size>{n}</Tot_Size></MPH></Variable_Header></Earth_Explorer_Header>')
    with zipfile.ZipFile(base/'staging'/A,'x',compression=zipfile.ZIP_DEFLATED) as z:
        z.write(cdf,cdf.name)
        z.writestr(stem+'.HDR',hdr)


class Handoff(unittest.TestCase):
    def setUp(self):
        ctx=tempfile.TemporaryDirectory(dir=OUT)
        self.addCleanup(ctx.cleanup)
        self.base=Path(ctx.name)
        (self.base/'staging').mkdir()
        (self.base/'accepted').mkdir()

    def accept_fixture(self):
        synthetic_zip(self.base)
        self.assertEqual(h.inspect_one(self.base,A)['status'],'ACCEPTED_STATIC_ONLY')
        return self.base/'accepted'/A

    def test_round_trip_complete_swarm_contract(self):
        real=h.audit.CDF
        calls=[]
        def guarded(*args,**kwargs):
            cdf=real(*args,**kwargs)
            original=cdf.varget
            def read(k,*args,**kwargs):
                self.assertIn(k,h.audit.DATA_FIELDS)
                calls.append(k)
                return original(k,*args,**kwargs)
            cdf.varget=read
            return cdf
        with patch.object(h.audit,'CDF',guarded):
            folder=self.accept_fixture()
        receipt=json.loads((folder/'receipt.json').read_text())
        self.assertEqual(receipt['contract']['CDF']['records'],2880)
        self.assertEqual(tuple(calls),h.audit.DATA_FIELDS)
        self.assertEqual((folder/A).stat().st_mode&0o777,0o444)
        self.assertFalse(receipt['OFFICIAL_PROVENANCE_VERIFIED'])

    def test_duplicate_and_conflicting_upload(self):
        original=self.accept_fixture()/A
        pinned=original.read_bytes()
        self.assertEqual(h.inspect_one(self.base,A)['status'],'DUPLICATE_ALREADY_ACCEPTED')
        (self.base/'staging'/A).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'different bytes'):
            h.inspect_one(self.base,A)
        self.assertEqual(original.read_bytes(),pinned)

    def test_fake_containers(self):
        for file in (A,h.SEED):
            (self.base/'staging'/file).write_bytes(b'not the expected container')
            with self.assertRaises(ValueError):
                h.inspect_one(self.base,file)

    def test_unregistered_winter_or_wrong_filename(self):
        with self.assertRaises(ValueError):
            h.inspect_one(self.base,A.replace('20210621','20211221'))

    def test_symlink_rejected(self):
        p=self.base/'source'
        p.write_bytes(b'data')
        (self.base/'staging'/A).symlink_to(p)
        with self.assertRaises(OSError):
            h.inspect_one(self.base,A)

    def test_untrusted_source_cannot_claim_provenance(self):
        synthetic_zip(self.base)
        sidecar=self.base/'staging'/(A+'.source.json')
        call=dict(download_url='https://swarm-diss.eo.esa.int/',download_date='2026-11-23',source_note='claimed')
        sidecar.write_text(json.dumps(call))
        h.inspect_one(self.base,A)
        receipt=json.loads((self.base/'accepted'/A/'receipt.json').read_text())
        self.assertEqual(receipt['uploader_claim'],call)
        self.assertFalse(receipt['OFFICIAL_PROVENANCE_VERIFIED'])

    def test_reject_checksum_mismatch(self):
        sidecar=self.base/'test.json'
        sidecar.write_text(json.dumps(dict(download_url='https://swarm-diss.eo.esa.int/',
                 download_date='2026-11-23',source_note='claimed',file_sha256='0'*64)))
        with self.assertRaisesRegex(ValueError,'checksum'):
            h.provenance(sidecar,'1'*64)

    def test_spring_seed_not_summer(self):
        receipt=dict(actual_calendar_records=['2002-03-21T00:00:00'],primary_records=1,SOURCE_START=[80,0,0])
        with patch.object(h.audit,'seed_inspection',return_value=receipt):
            with self.assertRaisesRegex(ValueError,'summer-solstice'):
                h.inspect_seed(self.base/'seed')

    def test_summer_clock_fixture(self):
        receipt=dict(actual_calendar_records=['2002-06-21T00:00:00'],primary_records=1,SOURCE_START=[172,0,0])
        with patch.object(h.audit,'seed_inspection',return_value=receipt):
            self.assertEqual(h.inspect_seed(self.base/'seed'),receipt)


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def assert_tracked(path):
    git_value=subprocess.check_output(['git','show',f'{h.BASE}:{path.relative_to(ROOT)}'],cwd=ROOT)
    assert git_value==path.read_bytes()


def solar_evidence():
    prior=ROOT/'experiments/f107_2021_recovery_v1'
    receipt=prior/'canada_range_requests.json'
    assert_tracked(receipt)
    item=next(x for x in json.loads(receipt.read_text()) if x['bytes']==56001)
    range_path=ROOT/item['path']
    assert digest(range_path)==item['SHA256']
    can={}
    for line in range_path.read_text().splitlines():
        p=line.split()
        if len(p)==7 and p[0].isdigit() and len(p[0])==8:
            can.setdefault(p[0],[]).append(dict(UTC=p[1],observed_sfu=float(p[4]),adjusted_sfu=float(p[5])))
    assert can['20210508'] and can['20210510'] and not can.get('20210509')
    assert [x['UTC'] for x in can['20210616']]==['170000','230000']
    anchors=prior/'source_requests.json'
    assert_tracked(anchors)
    noaa_source=next(x for x in json.loads(anchors.read_text()) if x['name']=='noaa_q2')
    noaa=ROOT/'data/raw/f107_2021_recovery_v1/noaa_q2.txt'
    assert digest(noaa)==noaa_source['SHA256']
    noaa_rows={}
    for line in noaa.read_text().splitlines():
        p=line.split()
        if len(p)>3 and p[0]=='2021':
            noaa_rows['-'.join(p[:3])]=int(p[3])
    archive=ROOT/'data/raw/f107_2021_recovery_v1/gfz_year.txt'
    pins=prior/'gfz_requests.json'
    assert_tracked(pins)
    assert digest(archive)==next(x['SHA256'] for x in json.loads(pins.read_text()) if x['name']=='gfz_year')
    compare=[]
    for line in archive.read_text().splitlines():
        p=line.split()
        if len(p)<26 or p[0]!='2021':
            continue
        key=''.join(str(int(x)).zfill(2) for x in p[:3])
        if not '20210426'<=key<='20210624' or Decimal(p[25])<=0:
            continue
        noon=[x for x in can.get(key,[]) if x['UTC']=='200000']
        if len(noon)==1:
            compare.append(abs(Decimal(str(noon[0]['observed_sfu']))-Decimal(p[25])))
    return dict(
        status='GFZ_BLOCKED_NO_CONTRACT_COMPATIBLE_REVISION',Canada_source=item,
        NOAA_source=noaa_source|{'path':str(noaa.relative_to(ROOT))},
        GFZ_archive=dict(path=str(archive.relative_to(ROOT)),SHA256=digest(archive)),
        dates={'2021-05-09':dict(GFZ=-1,Canada=can.get('20210509',[]),NOAA_DSD_sfu=noaa_rows['2021-05-09']),
               '2021-06-16':dict(GFZ=-1,Canada=can['20210616'],NOAA_DSD_sfu=noaa_rows['2021-06-16'])},
        Canada_20UTC_GFZ_overlap=dict(start='2021-04-26',stop='2021-06-24',eligible_pairs=len(compare),
                                     exact=sum(x==0 for x in compare),maximum_absolute_sfu=float(max(compare))),
        raw_evidence_reused=True,new_GFZ_requests=0,driver_substitution=False)


def save_unique(name, value):
    with (OUT/name).open('x') as f:
        json.dump(value,f,indent=2,allow_nan=False)
        f.write('\n')


def verify_accepted():
    reviews=[]
    for name in h.PRODUCTS:
        folder=h.HOME_DIR/'accepted'/name
        if not folder.exists():
            continue
        assert folder.resolve(strict=True)==folder
        receipt=json.loads((folder/'receipt.json').read_text())
        original=folder/name
        assert digest(original)==receipt['SHA256'] and original.stat().st_size==receipt['size']
        contract=receipt['contract']
        if h.PRODUCTS[name]:
            with zipfile.ZipFile(original) as z:
                assert set(z.namelist())=={x['name'] for x in contract['members']} and z.testzip() is None
                assert all(digest(folder/x['name'])==x['SHA256'] and
                       hashlib.sha256(z.read(x['name'])).hexdigest()==x['SHA256'] for x in contract['members'])
            stem=Path(name).stem
            cdf=CDF(folder/(stem+'.cdf'))
            attrs=cdf.globalattsget()
            assert attrs['TITLE']==[stem] and attrs['TIME SYSTEM']==['UTC']
            utc=cdfepoch.to_datetime(cdf.varget('time')).astype('datetime64[s]')
            expected=np.datetime64(h.PRODUCTS[name],'s')+np.arange(2880)*np.timedelta64(30,'s')
            assert np.array_equal(utc,expected)
            assert cdf.varattsget('density')['UNITS']=='kg/m3'
            assert cdf.varinq('density').Last_Rec==2879
            assert contract['target_density_reads']==0

        else:
            from netCDF4 import Dataset
            from atmosphere.restart_validation import REQUIRED
            with Dataset(original) as n:
                assert len(REQUIRED)==34 and set(REQUIRED)<=set(n.variables) and n.history_type=='primary'
                assert n['mtime'][0].tolist()==contract['native']['SOURCE_START']
        reviews.append(dict(file=name,SHA256=receipt['SHA256'],real=True))
    return reviews


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--accepted-only',action='store_true')
    if parser.parse_args().accepted_only:
        result=dict(UTC=datetime.now(timezone.utc).isoformat(),protected=h.protect(),
                    received_real_assets_verified=verify_accepted(),target_density_decoded=0)
        with tempfile.NamedTemporaryFile(dir=OUT,prefix='independent_receipt_',
                                         suffix='_local.json',mode='w',delete=False) as f:
            json.dump(result,f,indent=2)
            f.write('\n')
            print(Path(f.name).relative_to(ROOT))
        print(json.dumps(result,indent=2))
        return
    start=monotonic()
    tests=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(k) for k in (V38Fixtures,Handoff))
    results=unittest.TextTestRunner().run(tests)
    if not results.wasSuccessful():
        raise SystemExit(1)
    sources=solar_evidence()
    save_unique('Fobs_source_evidence.json',sources)
    reviewed=verify_accepted()
    save_unique('verification.json',dict(UTC=datetime.now(timezone.utc).isoformat(),
        CPU_tests=results.testsRun,failures=0,protected=h.protect(),
        received_real_assets_verified=reviewed,solar_original_sha_rechecked=3,
        target_density_decoded=0,GPU=0,model_runs=0,wall_s=monotonic()-start,
        peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))


if __name__=='__main__':
    main()
