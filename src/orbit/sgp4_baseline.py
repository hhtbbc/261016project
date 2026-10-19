"""Historical single-TLE SGP4 baseline; SI output in TEME, no data assimilation."""
from dataclasses import dataclass
from pathlib import Path
from decimal import Decimal
import json
import numpy as np
from astropy.time import Time,TimeDelta
from sgp4.api import Satrec,WGS72,SGP4_ERRORS

@dataclass
class TLERecord:
    line1:str
    line2:str
    epoch:Time
    archive_id:int|None=None
    publication_time:str|None=None

def parse_tle(line1,line2,expected_norad=39452,archive_id=None):
    for n,line in enumerate([line1,line2],1):
        if len(line)!=69 or not line.startswith(str(n)+' '):raise ValueError('Invalid TLE length/prefix')
        checksum=sum(int(x) if x.isdigit() else 1 if x=='-' else 0 for x in line[:68])%10
        if checksum!=int(line[68]):raise ValueError('TLE checksum mismatch')
        if int(line[2:7])!=expected_norad:raise ValueError('Unexpected satellite')
    year=int(line1[18:20]);year+=1900 if year>=57 else 2000
    days=Decimal(line1[20:32])-1
    epoch=Time(f'{year}-01-01T00:00:00',scale='utc')+TimeDelta(float(days*86400),format='sec')
    return TLERecord(line1,line2,epoch,archive_id)

def read_archive(path):
    data=json.loads(Path(path).read_text())
    if data.get('next') is not None:raise ValueError('Incomplete TLE archive pagination')
    records=[]
    for item in data['results']:
        a,b=item['norad_str'].splitlines()[-2:]
        records.append(parse_tle(a,b,archive_id=item['id']))
    return records

def select_before(records,start,allow_unverified_availability=False):
    eligible=[r for r in records if r.epoch<=start]
    if not eligible:raise ValueError('No pre-start TLE')
    selected=max(eligible,key=lambda r:r.epoch.utc.jd)
    if selected.publication_time is None and not allow_unverified_availability:
        raise ValueError('Historical publication/availability time is unverified')
    return selected

def propagate(record,times):
    sat=Satrec.twoline2rv(record.line1,record.line2,WGS72)
    error,p,v=sat.sgp4_array(np.atleast_1d(times.utc.jd1),np.atleast_1d(times.utc.jd2))
    if np.any(error):
        idx=np.flatnonzero(error)
        raise RuntimeError({int(i):SGP4_ERRORS.get(int(error[i]),'unknown') for i in idx[:10]})
    p=p*1000.;v=v*1000.
    if not np.isfinite(p).all() or not np.isfinite(v).all():raise ValueError('Nonfinite SGP4 output')
    return p,v,error
