"""Two specific official 0203 SP3s; bounded listing/download, no propagation."""
from pathlib import Path
import sys,json,time,zipfile,urllib.parse,shutil,resource
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from prepare_fourcastden_swarm_observation_v1 import bounded_get,sha,inside,dump
TAG='swarm_coordinate_orbit_readiness_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG;D=ROOT/'data/raw'/TAG


def main():
    start=time.perf_counter()
    for p in (F,O,D):inside(p);p.mkdir(exist_ok=False)
    names=['AGENTS.md','STATUS.md','WORKLOG.md','reports/FOURCASTDEN_SWARM_OBSERVATION_COMPARISON_V1.md',
        'reports/FOURCASTDEN_IDEAL_UPDATE_6H_V1.md','reports/FOURCASTDEN_COORDINATE_AND_UPDATE_INTERFACE_V1.md',
        'docs/TIEGCM_SWARM_COORDINATE_DATUM.md','docs/TIEGCM2023_HEIGHT_DATUM_REVIEW.md','docs/SWARM_FORMAL_FORCE_PARAMETERS.md',
        'docs/ORBIT_DENSITY_EXPERIMENT_PROTOCOL.md']
    dump(F/'context_read.json',{p:sha(ROOT/p) for p in names})
    assert shutil.disk_usage(ROOT).free>20*2**30
    dump(F/'protocol.json',dict(download_total_limit_bytes=10*2**20,listing_limit_bytes=6*2**20,version='0203',
        selection='same previously used version, not chosen by SP3/DNS residual',dates=['2023-01-04','2023-03-24'],UTC_hours=[1,13],
        CPU_phase_limit_s=1800,RSS_limit_GiB=4,expected_CPU_s=120,expected_RSS_MiB=500,
        geometry='DNS GRS80 geodetic -> Earth-fixed; SP3 GPS/declared frame -> UTC/ITRS realization assumption',
        interpolation='cubic Hermite from native P,V; no extrapolation or gap bridging',
        independent_check='withheld alternate native samples plus independent degree6 position polynomial at DNS UTC',
        residual_budget='signed residual exact identity; MSE cross term retained, no additive RMSE',
        blocks='fixed one-hour UTC bins, 13 endpoint separate',ACF='descriptive lag correlation of contiguous 30s pairs; no CI or significance',
        formal_datum='EXTERNAL_DATUM_UNVERIFIED',no_new_density_queries=True,no_new_forward=True,no_new_orbit=True))
    url='https://swarm-diss.eo.esa.int/?'+urllib.parse.urlencode(dict(do='list',maxfiles=10000,pos=0,file='swarm/Level2daily/Latest_baselines/POD/RD/Sat_A'))
    listing=bounded_get(url,D/'official_listing.json',6*2**20);j=json.loads((D/'official_listing.json').read_text());assert j['success']
    targets=[]
    for prefix in ('SW_OPER_SP3ACOM_2__20230103T235942_20230104T235942','SW_OPER_SP3ACOM_2__20230323T235942_20230324T235942'):
        candidates=[r for r in j['results'] if r['name']==prefix+'_0203.ZIP'];assert len(candidates)==1;targets+=candidates
    assert listing['bytes']+sum(r['size'] for r in targets)<10*2**20
    dump(F/'download_plan.json',dict(listing=listing,targets=targets,expected_raw_bytes=sum(r['size'] for r in targets),local_existing_target_files=False))
    ex=inside(D/'extracted');ex.mkdir(exist_ok=False);records=[]
    for target in targets:
        url='https://swarm-diss.eo.esa.int/?'+urllib.parse.urlencode(dict(do='download',file=target['path']))
        rec=bounded_get(url,D/target['name'],10*2**20-listing['bytes']-sum(x['bytes'] for x in records),expected=target['size'])
        with zipfile.ZipFile(D/target['name']) as z:
            assert len(z.infolist())==2 and sum(x.file_size for x in z.infolist())<10*2**20
            assert z.testzip() is None;members=[]
            for x in z.infolist():
                assert Path(x.filename).name==x.filename and not x.is_dir();p=inside(ex/x.filename)
                with p.open('xb') as f:f.write(z.read(x))
                members.append(dict(path=str(p.relative_to(ROOT)),bytes=x.file_size,CRC32=f'{x.CRC:08x}',SHA256=sha(p)))
        rec['members']=members;records.append(rec)
    dump(F/'download_manifest.json',records)
    dump(F/'download_complete.json',dict(raw_bytes=sum(x['bytes'] for x in records),all_network_payload_bytes=listing['bytes']+sum(x['bytes'] for x in records),
        wall_s=time.perf_counter()-start,RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,publisher_checksum_available=False,CRC_and_local_SHA=True))
    print((F/'download_complete.json').read_text())


if __name__=='__main__':main()
