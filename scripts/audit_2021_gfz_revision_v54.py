"""Bounded, public metadata retrieval and read-only GFZ revision audit."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPRedirectHandler, Request
from urllib.error import HTTPError, URLError

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'experiments/thermosphere_swarm_external_datum_v54'
DAYS=('2021-05-09','2021-06-16')
API='https://kp.gfz.de/app/json/'
ARCHIVE='https://www-app3.gfz-potsdam.de/kp_index/Kp_ap_Ap_SN_F107_2021.txt'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None


def get(name,url,cap=512*1024):
    dest=OUT/'public_evidence'/name
    assert dest.resolve()==dest and dest.parent.is_dir()
    info={'URL':url,'retrieved_UTC':datetime.now(timezone.utc).isoformat(),'cap':cap}
    if dest.is_file():
        payload=dest.read_bytes()
        if len(payload)>cap:
            raise ValueError('local response exceeds cap')
        info.update(recovered_from_V54_local_copy=True,bytes=len(payload),SHA256=hashlib.sha256(payload).hexdigest(),
                    file=str(dest.relative_to(ROOT)),retrieved_UTC=datetime.fromtimestamp(
                        dest.stat().st_mtime,timezone.utc).isoformat())
        return info
    try:
        with build_opener(NoRedirect()).open(Request(url,headers={'User-Agent':'V54 scientific metadata audit/1.0'}),timeout=12) as f:
            payload=f.read(cap+1)
            if len(payload)>cap:
                raise ValueError('response byte cap exceeded')
            with dest.open('xb') as target:
                target.write(payload)
            info.update(HTTP=f.status,type=f.headers.get('Content-Type'),last_modified=f.headers.get('Last-Modified'),
                        bytes=len(payload),SHA256=hashlib.sha256(payload).hexdigest(),
                        file=str(dest.relative_to(ROOT)))
    except HTTPError as e:
        info.update(HTTP=e.code,error='HTTP request denied or unavailable; no redirect followed')
    except (URLError, TimeoutError, ValueError) as e:
        info.update(error=str(e))
    return info


def observed(obj,day):
    if 'Fobs' not in obj or obj.get('index','Fobs')!='Fobs':
        raise ValueError('expected GFZ observed flux')
    dates=obj.get('datetime')
    values=obj['Fobs']
    if dates!=[day+'T00:00:00Z'] or len(values)!=1 or not isinstance(values[0],(int,float)):
        raise ValueError('GFZ daily grid mismatch')
    return values[0]


def daily_archive(text):
    output={}
    for line in text.splitlines():
        parts=line.split()
        if len(parts)==28 and '-'.join(parts[:3]) in DAYS:
            day='-'.join(parts[:3])
            if day in output:
                raise ValueError('Duplicate year-file day')
            output[day]={'Fobs':float(parts[-3]),'Fadj':float(parts[-2]),'D':int(parts[-1])}
    if set(output)!=set(DAYS):
        raise ValueError('Missing historical day row')
    return output


def main():
    evidence=OUT/'public_evidence'
    assert OUT.resolve()==OUT
    evidence.mkdir(exist_ok=True)
    result={}
    for day in DAYS:
        url=API+'?'+urlencode(dict(start=day+'T00:00:00Z',end=day+'T23:59:59Z',index='Fobs'))
        result[day]=get(day+'_Fobs.json',url,16384)
    year=get('GFZ_2021_year.txt',ARCHIVE,180*1024)
    alternate=None
    if 'file' not in year:
        alternate=get('GFZ_2021_year.txt','https://ftp.gfz.de/pub/home/obs/Kp_ap_Ap_SN_F107/Kp_ap_Ap_SN_F107_2021.txt',180*1024)
    prior=json.loads((ROOT/'experiments/thermosphere_summer_data_acquisition_v38/download_manifest.json').read_text())
    for day,r in result.items():
        if 'file' not in r:
            continue
        payload=json.loads((ROOT/r['file']).read_text())
        r['Fobs']=observed(payload,day)
        r['status_fields']={k:payload.get(k) for k in ('status','meta') if k in payload}
        old=[x for x in prior['assets'].values() if day in x.get('URL','') and 'index=Fobs' in x.get('URL','')]
        if old:
            saved=json.loads((ROOT/old[0]['path']).read_text())
            r['prior_Fobs']=observed(saved,day)
            r['same_parsed_payload']=saved==payload
    old_archive=ROOT/'data/raw/f107_2021_recovery_v1/gfz_year.txt'
    year['old_rows']=daily_archive(old_archive.read_text())
    if 'file' in year:
        year['current_rows']=daily_archive((ROOT/year['file']).read_text())
        year['same_bytes_as_frozen']=old_archive.read_bytes()==(ROOT/year['file']).read_bytes()
    if alternate and 'file' in alternate:
        alternate['current_rows']=daily_archive((ROOT/alternate['file']).read_text())
        alternate['same_bytes_as_frozen']=old_archive.read_bytes()==(ROOT/alternate['file']).read_bytes()
    out={'API':result,'year_file':year,'alternate_year_file':alternate,'writes_to_GPI':0,'fill_values_substituted':0}
    with (OUT/'gfz.json').open('x') as stream:
        json.dump(out,stream,indent=2)
        stream.write('\n')


if __name__=='__main__':
    main()
