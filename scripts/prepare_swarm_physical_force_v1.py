"""Fetch only two official Jan4 auxiliary archives within a 30MiB bound."""
from pathlib import Path
import sys,json,urllib.parse,zipfile,time,resource,shutil
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from prepare_fourcastden_swarm_observation_v1 import bounded_get,dump,sha,inside
TAG='swarm_physical_force_readiness_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG;D=ROOT/'data/raw'/TAG

def main():
    start=time.perf_counter()
    for p in [F,O,D]:inside(p);p.mkdir(exist_ok=False)
    names=['AGENTS.md','STATUS.md','WORKLOG.md','reports/ORBIT_12H_ABCD_DOP853_CLOSURE_V1.md','reports/SWARM_COORDINATE_ORBIT_READINESS_V1.md','reports/FOURCASTDEN_SWARM_OBSERVATION_COMPARISON_V1.md','docs/SWARM_FORMAL_FORCE_PARAMETERS.md','docs/TIEGCM_ZG_EXTERNAL_REGISTRATION_QUESTIONS.md','docs/ORBIT_DENSITY_EXPERIMENT_PROTOCOL.md']
    dump(F/'context_read.json',{p:sha(ROOT/p) for p in names})
    protected=json.loads((ROOT/'experiments/orbit_12h_abcd_dop853_closure_v1/protected.json').read_text())
    for d in ['experiments/orbit_12h_abcd_dop853_closure_v1','results/orbit_12h_abcd_dop853_closure_v1']:
        for p in (ROOT/d).rglob('*'):
            if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
    dump(F/'protected.json',protected)
    dump(F/'protocol.json',dict(target_UTC=['2023-01-04T01:00:00','2023-01-04T13:00:00'],new_raw_download_limit=30*2**20,raw_plus_metadata_hard_limit=30*2**20,listing_limit_each=4*2**20,extraction_limit=100*2**20,no_propagation=True,no_GPU=True,no_TIE=True,formal_orbit='BLOCKED',expected_version='0601',formal_gate_cannot_be_bypassed=True,free_disk_bytes=shutil.disk_usage(ROOT).free))
    targets=[];transfers=[]
    for kind,folder in [('SC_ADYN','SC_xDYN'),('STRAATT','STRxATT')]:
        remote='swarm/Level1b/Latest_baselines/'+folder+'/Sat_A'
        url='https://swarm-diss.eo.esa.int/?'+urllib.parse.urlencode(dict(do='list',maxfiles=10000,pos=0,file=remote))
        rec=bounded_get(url,D/(kind+'_listing_local.json'),4*2**20);transfers.append(rec);listing=json.loads((D/(kind+'_listing_local.json')).read_text());assert listing['success']
        matches=[x for x in listing['results'] if f'{kind}_1B_20230104T000000_20230104T235959_0601.CDF.ZIP' in x['name']];assert len(matches)==1,matches;targets+=matches
    expected=sum(x['size'] for x in targets);assert expected+sum(x['bytes'] for x in transfers)<=30*2**20
    dump(F/'download_plan.json',dict(targets=targets,expected_ZIP_bytes=expected,metadata_bytes=sum(x['bytes'] for x in transfers),limit=30*2**20,official_public_service=True,no_other_dates=True))
    ex=D/'extracted';inside(ex);ex.mkdir(exist_ok=False);records=[]
    for target in targets:
        url='https://swarm-diss.eo.esa.int/?'+urllib.parse.urlencode(dict(do='download',file=target['path']))
        rec=bounded_get(url,D/target['name'],30*2**20-sum(x['bytes'] for x in transfers+records),expected=target['size']);members=[]
        with zipfile.ZipFile(D/target['name']) as z:
            assert sum(x.file_size for x in z.infolist())<100*2**20;assert z.testzip() is None
            for x in z.infolist():
                assert x.filename==Path(x.filename).name and not x.is_dir()
                p=ex/x.filename;inside(p)
                with p.open('xb') as f:f.write(z.read(x))
                members.append(dict(path=str(p.relative_to(ROOT)),bytes=x.file_size,CRC32=f'{x.CRC:08x}',SHA256=sha(p)))
        rec['members']=members;records.append(rec);dump(F/(target['name']+'_receipt.json'),rec)
    dump(F/'download_manifest.json',records)
    dump(F/'download_complete.json',dict(raw_ZIP_bytes=sum(x['bytes'] for x in records),metadata_bytes=sum(x['bytes'] for x in transfers),total_payload_bytes=sum(x['bytes'] for x in transfers+records),ZIP_CRC_verified=True,publisher_SHA_not_provided=True,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
    print((F/'download_complete.json').read_text())
if __name__=='__main__':main()
