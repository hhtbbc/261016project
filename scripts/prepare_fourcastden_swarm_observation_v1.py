"""Bounded two-day official DNS download, archive CRC and CDF contract audit."""
from pathlib import Path
import argparse,hashlib,json,sys,time,urllib.request,urllib.parse,zipfile,resource,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
TAG='fourcastden_swarm_observation_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG;D=ROOT/'data/raw'/TAG


def inside(p):p=Path(p);p.resolve().relative_to(ROOT);return p
def sha(p):
    h=hashlib.sha256()
    with inside(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
    return h.hexdigest()
def dump(p,x):
    with inside(p).open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')
def bounded_get(url,path,limit,expected=None):
    inside(path)
    if path.exists():raise FileExistsError(path)
    total=0
    with urllib.request.urlopen(url,timeout=25) as r:
        if r.status!=200:raise ValueError('Unexpected HTTP '+str(r.status))
        cl=r.headers.get('Content-Length')
        if cl and int(cl)>limit:raise ValueError('Advertised size exceeds budget')
        with path.open('xb') as f:
            while True:
                data=r.read(min(16384,limit-total+1))
                if not data:break
                total+=len(data);f.write(data)
                if total>limit:raise ValueError('Download over limit; partial retained')
    if expected is not None and total!=expected:raise ValueError('Byte size does not match official listing')
    return dict(URL=url,bytes=total,SHA256=sha(path),path=str(path.relative_to(ROOT)),HTTP=200)


def main():
    start=time.perf_counter();import cdflib
    listing=json.loads((F/'listing_request.json').read_text());assert sha(D/'official_listing.json')==listing['SHA256']
    targets=listing['targets'];assert len(targets)==2 and all(t['name'].endswith('_0301.ZIP') for t in targets)
    n=sum(t['size'] for t in targets)
    assert n<10*2**20 and shutil.disk_usage(ROOT).free>20*2**30
    mem={x.split(':')[0]:int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')}
    dump(F/'protocol.json',dict(tag=TAG,label='PROVISIONAL_OBSERVATION_COMPARISON / HINDCAST',dates=['2023-01-04','2023-03-24'],
        UTC_hours=[1,13],update_hour=7,models=['Direct','Flow','LogDEN','History'],download_bytes_expected=n,
        raw_download_limit_bytes=10*2**20,CPU_wall_limit_s=1800,RSS_limit_GiB=4,output_limit_MiB=500,
        available_memory=mem,expected_analysis_s=600,expected_analysis_RSS_GiB=1,expected_output_MiB=60,
        quality='actual 0301 CDF + official flag definition: 0 nominal, 1 anomalous, unknown flags explicitly rejected',
        density_field='density only; density_orbitmean separately preserved, never substituted',
        coordinates=dict(input='product geodetic, GRS80 per official service; verify one actual point per day',
            A='WGS84 geodetic lat and ellipsoid height as native hypothesis',B='geocentric latitude, r-6371000m hypothesis',
            D='A height with B latitude; single-factor diagnostic',E='A latitude with B height; single-factor diagnostic'),
        metrics=dict(units='kg/m3',weights='one equal weight per 30s observation, not independent replicates',relative_denominator='positive observed instantaneous density; no floor',
            periods={'pre':'01<=UTC<07','event':'UTC=07; separate left/right, excluded from forecast gain',
                     'transition':'07<UTC<08','post':'08<=UTC<=13'},regions={'south':'latitude<=-60','north':'latitude>=60','midlow':'abs(latitude)<60'},
            primary_mask='same quality-valid samples valid for reference and all 8 branches under both A/B mappings; per-model paired masks reported separately'),
        no_training=True,no_GPU=True,no_TIE=True,no_orbit=True,formal_external_datum='EXTERNAL_DATUM_UNVERIFIED'))
    downloads=[];contracts=[];ex=D/'extracted';inside(ex);ex.mkdir(exist_ok=False)
    for item in targets:
        url='https://swarm-diss.eo.esa.int/?'+urllib.parse.urlencode(dict(do='download',file=item['path']))
        record=bounded_get(url,D/item['name'],10*2**20-sum(x['bytes'] for x in downloads),expected=item['size'])
        with zipfile.ZipFile(D/item['name']) as z:
            assert len(z.infolist())==2 and sum(x.file_size for x in z.infolist())<4*2**20
            assert z.testzip() is None
            members=[]
            for x in z.infolist():
                assert Path(x.filename).name==x.filename and not x.is_dir()
                p=ex/x.filename;inside(p)
                with p.open('xb') as f:f.write(z.read(x))
                members.append(dict(path=str(p.relative_to(ROOT)),SHA256=sha(p),CRC32=f'{x.CRC:08x}',bytes=x.file_size))
        record['members']=members;downloads.append(record)
        cdf=next(ex.glob(item['name'][:-4]+'*.cdf'))
        with cdflib.CDF(cdf) as c:
            g=c.globalattsget();assert g['TIME SYSTEM']==['UTC']
            var={k:{'attrs':c.varattsget(k),'type':c.varinq(k).Data_Type_Description} for k in c.cdf_info().zVariables}
            assert var['density']['attrs']['UNITS']=='kg/m3'
            ts=cdflib.cdfepoch.to_datetime(c.varget('time'));flags=c.varget('validity_flag')
            cadence=np.diff(ts)/np.timedelta64(1,'s');assert np.all(cadence==30)
            u,v=np.unique(flags,return_counts=True)
            contracts.append(dict(file=str(cdf.relative_to(ROOT)),SHA256=sha(cdf),global_attributes=g,variables=var,
                records=len(ts),start=str(ts[0]),end=str(ts[-1]),cadence_s=30,flag_distribution={str(k):int(n) for k,n in zip(u,v)}))
    dump(F/'download_manifest.json',downloads);dump(F/'CDF_contracts.json',contracts)
    info=bounded_get('https://vires.services/hapi/info?id=SW_OPER_DNSAPOD_2_',D/'HAPI_info.json',65536)
    j=json.loads((D/'HAPI_info.json').read_text());assert j['status']['code']==1200
    params={x['name']:x for x in j['parameters']}
    assert params['validity_flag']['description']=='0 = nominal data, 1 = anomalous data'
    assert 'GRS80' in params['Latitude_GD']['description']
    dump(F/'official_service_contract.json',dict(request=info,contract=j))
    dump(F/'download_completed.json',dict(raw_observation_bytes=sum(x['bytes'] for x in downloads),metadata_bytes=listing['bytes']+info['bytes'],
        wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
        publisher_checksum_available=False,local_SHA_and_ZIP_CRC_verified=True))
    print((F/'download_completed.json').read_text());print(json.dumps(contracts,indent=2))


if __name__=='__main__':main()
