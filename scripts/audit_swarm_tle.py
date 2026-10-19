"""Validate archived historical TLE syntax/identity and freeze a pre-t0 selection."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'data/raw/meeting_sources/swarm_A_tle_202303.txt'
d=json.loads(p.read_text());out=ROOT/'data/raw/orbits/tle';out.mkdir(parents=True,exist_ok=True)
rows=[]
for item in d['results']:
    lines=item['norad_str'].splitlines();l1,l2=lines[-2:]
    assert len(l1)==69 and len(l2)==69 and l1.startswith('1 39452') and l2.startswith('2 39452')
    for line in [l1,l2]:assert sum(int(x) if x.isdigit() else 1 if x=='-' else 0 for x in line[:68])%10==int(line[68])
    year=int(l1[18:20]);year+=(1900 if year>=57 else 2000)
    epoch=datetime(year,1,1,tzinfo=timezone.utc)+timedelta(days=float(l1[20:32])-1)
    rows.append({'archive_id':item['id'],'norad':39452,'epoch_utc':epoch.isoformat(),'lines':[l1,l2]})
assert d['next'] is None
(out/'swarm_a_20230320_23_eth_archive.json').write_bytes(p.read_bytes())
(out/'swarm_a_20230320_23.tle').write_text('\n'.join(x['norad_str'] for x in d['results'])+'\n')
t0=datetime(2023,3,21,0,0,2,tzinfo=timezone.utc)
candidates=[x for x in rows if datetime.fromisoformat(x['epoch_utc'])<=t0]
selected=max(candidates,key=lambda x:x['epoch_utc'])
(out/'swarm_a_selected_before_t0.tle').write_text('SWARM A\n'+'\n'.join(selected['lines'])+'\n')
report={'source':'ETH Satellite Database (archive fetched from CelesTrak)','raw_response_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'count':len(rows),'all_checksums_valid':True,'all_norad_match':True,'t0_proposed_utc':t0.isoformat(),'selected':selected,'age_hours':(t0-datetime.fromisoformat(selected['epoch_utc'])).total_seconds()/3600,'element_availability_at_t0_verified':False,'note':'Epoch-before-t0 is verified. Historical provider retrieval/publication time not supplied, so strict real-time availability is not established. No SGP4 propagation today.'}
(ROOT/'logs/swarm_tle_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
