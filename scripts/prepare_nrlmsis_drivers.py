"""Freeze existing GFZ inputs without downloading weather data."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from atmosphere.msis_density_provider import FrozenGfzDrivers
from astropy.time import Time
import numpy as np
paths=['data/raw/meeting_sources/gfz_Fobs_spinup_support.txt','data/raw/tiegcm2023_sources/gfz_ap_support.json','data/raw/tiegcm2023_sources/gfz_Ap_support.json']
d=[json.loads((ROOT/p).read_text()) for p in paths]
prior=json.loads((ROOT/'logs/tiegcm2023_driver_audit.json').read_text())['sources']
manifest=json.loads((ROOT/'data/raw/tiegcm2023_sources/manifest.json').read_text())
for p in paths:
 actual=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
 expected=prior[p] if p in prior else next(x['sha256'] for x in manifest if x.get('path')==p)
 assert actual==expected, 'Existing raw data hash differs: '+p
assert all(x=='def' for x in d[1]['status']+d[2]['Apstatus'])
def pairs(i,key,day=False):
 t=d[i]['datetime'];assert len(t)==len(set(t));v=d[i][key];assert np.isfinite(v).all() and min(v)>=0
 return dict(zip([x[:10] if day else x for x in t],v))
f={'status':'HINDCAST','solar_observed_sfu':pairs(0,'Fobs',True),'ap_3hour':pairs(1,'ap'),'Ap_daily':pairs(2,'Ap',True),'source_quality':{'ap':'def','Ap':'def','Fobs':'API provides no per-value quality flag; no clipping','license':'GFZ CC BY 4.0'},'sources':[{'path':p,'sha256':hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in paths]}
for day,v in f['Ap_daily'].items():
 assert abs(v-np.mean([f['ap_3hour'][day+f'T{h:02d}:00:00Z'] for h in range(0,24,3)]))<=.5
out=ROOT/'configs/nrlmsis2023_gfz_frozen.json'
if out.exists():
 assert json.loads(out.read_text()) == f, 'Frozen input differs; refuse overwrite'
else:out.write_text(json.dumps(f,indent=2)+'\n')
g=FrozenGfzDrivers(out)
rows=[]
for t in Time(np.arange(np.datetime64('2023-03-20'),np.datetime64('2023-03-24'),np.timedelta64(3,'h')).astype('datetime64[ms]')):
 a=g.at(t);rows.append({'utc':t.isot,'f107_previous_day':a.f107_previous_day,'f107a_centered81':a.f107a_centered81,'ap':a.ap})
(ROOT/'logs/nrlmsis_drivers_audit.json').write_text(json.dumps({'driver_sha256':g.sha256,'rows':rows,'sources':f['sources'],'quality':f['source_quality']},indent=2)+'\n')
print('Frozen drivers:',g.sha256,len(rows),'boundary rows validated')
