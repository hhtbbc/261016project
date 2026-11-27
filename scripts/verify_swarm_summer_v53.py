"""Independent acceptance of byte-level integrity and sealed geometry fields."""
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from xml.etree import ElementTree
import zipfile

import numpy as np
from cdflib import CDF, cdfepoch

import admit_swarm_summer_v53 as a
import diagnose_summer_n2_residual_v52 as history

UNITS={'latitude':'deg','longitude':'deg','altitude':'m','density':'kg/m3'}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def shape_time(rows, day):
    expected=np.datetime64(day,'ns')+np.arange(2880)*np.timedelta64(30,'s')
    need(rows.shape==(2880,) and np.array_equal(rows,expected),'Wrong UTC day, cadence, or sample count')


def geometry(lat,lon,h,flag):
    need(all(len(x)==2880 and x.ndim==1 for x in (lat,lon,h,flag)), 'Invalid shapes')
    need(all(np.isfinite(x).all() for x in (lat,lon,h,flag)) and
         (abs(lat)<=90).all() and (abs(lon)<=180).all() and
         ((h>0)&(h<1e9)).all(),'Coordinate bounds or fill value')
    need(np.isin(flag,[0,1]).all(),'Unknown validity code')


def identity(attrs,stem):
    need(attrs.get('TITLE')==[stem]
         and attrs.get('TIME SYSTEM')==['UTC'] and attrs.get('SATELLITE')==['Swarm-A'],
         'CDF product identity mismatch')


def check_units(values):
    need(values==UNITS, 'Wrong coordinate or density unit metadata')


def decode(name,day,log):
    base=a.handoff.HOME_DIR/'accepted'/name
    zip_path=base/name
    stem=Path(name).stem
    cdf_path=base/(stem+'.cdf')
    hdr_path=base/(stem+'.HDR')
    for path in (base,zip_path,cdf_path,hdr_path,base/'receipt.json'):
        need(path.resolve(strict=True)==path and path.stat().st_mode&0o222==0,'Accepted path or mode')
    receipt=json.loads((base/'receipt.json').read_text())
    upload=json.loads((a.OUT/'handoff.json').read_text())['uploads'][name]
    dig=hashlib.sha256(zip_path.read_bytes()).hexdigest()
    need(dig==receipt['SHA256'] and zip_path.stat().st_size==receipt['size'],'ZIP bytes differ')
    for row in upload:
        source=Path(row['path'])
        need(hashlib.sha256(source.read_bytes()).hexdigest()==dig,'Uploaded bytes changed')
    with zipfile.ZipFile(zip_path) as z:
        need(sorted(z.namelist())==sorted([cdf_path.name,hdr_path.name]) and z.testzip() is None,
             'ZIP CRC or inventory')
        member_digests={}
        for path in (cdf_path,hdr_path):
            payload=z.read(path.name)
            need(path.read_bytes()==payload,'Accepted member bytes differ')
            member_digests[path.name]=dict(SHA256=hashlib.sha256(payload).hexdigest(),
                                          bytes=len(payload),ZIP_CRC32=f'{z.getinfo(path.name).CRC:08x}')
    xml=ElementTree.parse(hdr_path).getroot()
    expected={'File_Name':stem,'Mission':'Swarm','File_Type':'DNSAPOD_2_','File_Version':'0301',
              'Validity_Period/Validity_Start':f'UTC={day}T00:00:00',
              'Validity_Period/Validity_Stop':f'UTC={day}T23:59:30'}
    need(all(xml.findtext('Fixed_Header/'+k)==x for k,x in expected.items()),'HDR identity mismatch')
    crc,length,*_=subprocess.check_output(['cksum',str(cdf_path)],text=True).split()
    need((int(crc),int(length))==(int(xml.findtext('Variable_Header/MPH/CRC')),
                         int(xml.findtext('Variable_Header/MPH/Tot_Size'))),'POSIX CRC/length mismatch')
    cdf=CDF(cdf_path)
    attrs=cdf.globalattsget()
    identity(attrs,stem)
    upstream=attrs.get('ORIGINAL_PRODUCT_NAME',[])
    need(any('SA_Basic/Orbit_Geo' in x and "'altitude'" in x for x in upstream), 'Missing Swarm A geometry lineage')
    check_units({k:cdf.varattsget(k).get('UNITS') for k in UNITS})
    variables={k:dict(record_count=cdf.varinq(k).Last_Rec+1,dimensions=cdf.varinq(k).Dim_Sizes,
        dtype=cdf.varinq(k).Data_Type_Description,attributes=cdf.varattsget(k)) for k in (*a.FIELDS,'density')}
    need(all(x['record_count']==2880 and not x['dimensions'] for x in variables.values()),'CDF record metadata')
    with a.sealed_access(log):
        clock,lat,lon,h,flags=[cdf.varget(k) for k in a.FIELDS]
    utc=cdfepoch.to_datetime(clock).astype('datetime64[ns]')
    shape_time(utc,day)
    geometry(lat,lon,h,flags)
    rows=[dict(product_sha256=dig,product='DNSAPOD_2',satellite='Swarm A',baseline='0301',date=day,
        sample_id=i,UTC=np.datetime_as_string(t,unit='s')+'Z',latitude_deg=float(x),longitude_deg=float(y),
        altitude_m=float(z),validity_flag=int(f),quality_code_legal=True)
        for i,(t,x,y,z,f) in enumerate(zip(utc,lat,lon,h,flags))]
    counts=Counter(int(f) for f in flags)
    summary=dict(file=name,day=day,accepted=str(base.relative_to(a.ROOT)),size=receipt['size'],SHA256=dig,
        satellite_attribute=attrs['SATELLITE'],upstream_geometry=upstream,orbital_period_seconds=int(attrs['ORBITAL_PERIOD_SECONDS'][0]),
        members=member_digests,CDF_POSIX_CRC=int(crc),CDF_bytes=int(length),variables=variables,
        coordinate_ranges={k:[float(v.min()),float(np.median(v)),float(v.max())]
                           for k,v in [('latitude_deg',lat),('longitude_deg',lon),('altitude_m',h),
                           ('nominal_altitude_m',h[flags==0])]},
        flags={'0':counts[0],'1':counts[1],'unknown':0},records=len(rows),cadence_seconds=30,
        first_UTC=rows[0]['UTC'],last_UTC=rows[-1]['UTC'],BYTE_INTEGRITY_VERIFIED=True,
        PRODUCT_IDENTITY_VERIFIED=True,METADATA_VERIFIED=True,provenance='OFFICIAL_PROVENANCE_UNVERIFIED',
        user_supplied=True,source_claim_present=receipt['uploader_claim'] is not None)
    return rows,summary


def save(name,rows):
    with (a.OUT/name).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    v52=a.ROOT/'experiments/thermosphere_summer_n2_residual_v52'
    result=history.run.load(v52/'result.json')
    assert result['state']=='V52_N2_RESIDUAL_DIAGNOSIS_COMPLETE_VERIFIED'
    release=v52/'publication_SHA256.json'
    blob=subprocess.check_output(['git','show',f'e955e2c:{release.relative_to(a.ROOT)}'],cwd=a.ROOT)
    need(release.read_bytes()==blob,'V52 publication changed')
    for p,h in json.loads(blob).items():
        need(history.run.sha(a.ROOT/p)==h,f'Changed V52 asset {p}')
    _,history_ids=history.identity()
    log=[]
    by_year={}
    reviews=[]
    for name,day in a.PRODUCTS.items():
        rows,summary=decode(name,day,log)
        by_year[day[:4]]=rows
        reviews.append(summary)
    class Contracts(unittest.TestCase):
        def test_bad_time_count(self):
            with self.assertRaises(ValueError): shape_time(np.arange(3),'2021-06-21')
        def test_bad_time_step_date(self):
            for day,step in [('2021-06-22',30),('2021-06-21',31)]:
                with self.assertRaises(ValueError):
                    shape_time(np.datetime64(day)+np.arange(2880)*np.timedelta64(step,'s'),'2021-06-21')
        def test_invalid_flags_coords(self):
            x=np.ones(2880)
            for j,bad in [(0,91),(1,181),(2,np.inf),(3,127)]:
                args=[x.copy() for _ in range(4)]
                args[j][12]=bad
                with self.assertRaises(ValueError): geometry(*args)
        def test_altitude_units(self):
            with self.assertRaises(ValueError): check_units(UNITS|{'altitude':'km'})
        def test_wrong_satellite_or_version(self):
            n=Path(next(iter(a.PRODUCTS))).stem
            attrs={'TITLE':[n],'ORIGINAL_PRODUCT_NAME':[n],'TIME SYSTEM':['UTC'],'SATELLITE':['Swarm-A']}
            for x in [attrs|{'SATELLITE':['B']},attrs|{'TITLE':[n[:-1]+'2']}]:
                with self.assertRaises(ValueError): identity(x,n)
        def test_sealed(self):
            with a.sealed_access(log):
                with self.assertRaises(ValueError): CDF.varget(object(),'density')
                with self.assertRaises(ValueError): CDF.varget(object(),'density_orbitmean')
    test=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Contracts))
    need(test.wasSuccessful(),'Independent negative test failure')
    for year,rows in by_year.items():
        save(f'metadata_{year}.csv',rows)
    grids={y:{r['UTC'][11:]:r for r in rows} for y,rows in by_year.items()}
    common=sorted(set(grids['2021'])&set(grids['2022']))
    save('common_UTC_time_of_day.csv',[dict(UTC_time_of_day=t,UTC_2021=grids['2021'][t]['UTC'],
         sample_2021=grids['2021'][t]['sample_id'],flag_2021=grids['2021'][t]['validity_flag'],
         UTC_2022=grids['2022'][t]['UTC'],sample_2022=grids['2022'][t]['sample_id'],
         flag_2022=grids['2022'][t]['validity_flag']) for t in common])
    a.write_once(a.OUT/'independent.json',dict(history=history_ids,V52_files=len(json.loads(blob)),products=reviews,
        common_time_of_day=len(common),absolute_UTC_intersection=len(
            {r["UTC"] for r in by_year["2021"]}&{r["UTC"] for r in by_year["2022"]}),
        both_nominal=sum(not grids['2021'][t]['validity_flag'] and not grids['2022'][t]['validity_flag'] for t in common),
        negative_tests=test.testsRun,accessed=log,target_density_reads=0,
        GPU=0,model_runs=0,formal_scores=0))


if __name__=='__main__':
    main()
