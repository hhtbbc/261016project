"""Once-only bounded official acquisition. No scientific data decoding."""
from datetime import datetime, timezone
import json
from pathlib import Path
import resource
import subprocess
import sys
from time import monotonic, process_time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from observations.autumn_acquisition import Meter, bounded_get
from observations.bounded_swarm_acquisition import sha

NAME = 'thermosphere_summer_data_acquisition_v38'
OUT = ROOT/'experiments'/NAME
RAW = ROOT/'data/raw'/NAME
OLD = ROOT/'experiments/thermosphere_shrinkage_unseen_prereg_v37'
BASE = 'b13f2c1608b4d11d480278c3bb38bb32e5e35486'
DAYS = ('2021-06-21', '2022-06-21')
SEED = 'tiegcm_res5.0_junsol_smax_prim.nc'


def save(name, value):
    p = OUT/name
    if p.resolve() != p:
        raise ValueError('Unexpected receipt destination')
    with p.open('x') as f:
        json.dump(value,f,indent=2,allow_nan=False)
        f.write('\n')


def history_pins():
    path = OLD/'publication_SHA256.json'
    blob = subprocess.check_output(['git','show',f'{BASE}:{path.relative_to(ROOT)}'],cwd=ROOT)
    if path.read_bytes() != blob:
        raise ValueError('V37 publication mismatch')
    pins = json.loads(blob)
    for name,digest in pins.items():
        p=ROOT/name
        if p.resolve(strict=True)!=p or sha(p)!=digest:
            raise ValueError(f'Changed frozen V37 artifact {name}')
    return pins


def main():
    started,cpu = monotonic(),process_time()
    if RAW.resolve()!=RAW or OUT.resolve()!=OUT or any(RAW.iterdir()):
        raise ValueError('Fresh, local output directories required')
    frozen = history_pins()
    gaps=json.loads((OLD/'acquisition_gaps.json').read_bytes())
    candidates=gaps['by_date'][:2]
    assert tuple(row['date'] for row in candidates)==DAYS
    jobs=[]
    for row in candidates:
        for req in row['driver_requests']:
            key=f"{req['index']}_{req['start']}_{req['stop']}"
            jobs.append((key,req['URL'],key+'.json','small',None,(b'{',)))
    for row in candidates:
        o=row['observation']
        jobs.append((f"Swarm_{row['date']}",o['historical_index_URL'],o['product'],
                     'small',o['historical_index_bytes'],(b'PK\x03\x04',)))
    seed=next(x for x in gaps['seasonal_seed_candidates'] if x['season']=='summer')
    assert seed['name']==SEED
    jobs.append(('junsol',seed['URL'],SEED,'initial',None,(b'CDF\x01',b'CDF\x02',b'CDF\x05',b'\x89HDF')))
    save('acquisition_once.json',dict(UTC=datetime.now(timezone.utc).isoformat(),dates=DAYS,
         V37_SHA256=frozen, scope='official GFZ x4, ESA x2, NCAR x1'))
    meter=Meter()
    complete={}
    for key,url,name,group,expected,magic in jobs:
        trace=[]
        try:
            complete[key]=bounded_get(url,RAW/name,meter,group,trace,
                expected_bytes=expected,magic=magic,max_body=meter.limits[group])
            print(key,complete[key]['HTTP'],complete[key]['bytes'],flush=True)
        except (ValueError,OSError,EOFError) as exc:
            print(key,'FAILED',str(exc),flush=True)
        finally:
            save(key+'_http.json',dict(key=key,requests=trace))
    save('download_manifest.json',dict(assets=complete,network=meter.summary(),
        saved_body_bytes=sum(x['bytes'] for x in complete.values()),wall_s=monotonic()-started,
        CPU_s=process_time()-cpu,peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))


if __name__=='__main__':
    main()
