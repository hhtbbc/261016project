"""Independent CSV geometry, chronology and protected-file audit (offline only)."""
import sys,csv,json,hashlib
from pathlib import Path
import numpy as np
from astropy.time import Time
ROOT=Path(__file__).resolve().parents[1]
TAG='swarm_provisional_v1';OUT=ROOT/'experiments'/TAG

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 audit=json.loads((OUT/'audit.json').read_text());config=json.loads((OUT/'configuration.json').read_text())
 assert audit['model_launches']==audit['orbit_integrations']==0
 for path,digest in audit['protected'].items():assert sha(ROOT/path)==digest
 for entry in audit['files']:assert sha(ROOT/entry['file'])==entry['sha256']
 for path,key in [('src/atmosphere/tiegcm_density_provider.py','formal_provider_sha256'),('src/atmosphere/provisional_coordinate_adapter.py','adapter_sha256')]:assert sha(ROOT/path)==config[key]
 result={'status':'PROVISIONAL','protected_files_verified':len(audit['protected']),'formal_interface_unchanged':True,'datasets':{},'model_launches':0,'orbit_integrations':0}
 for entry in audit['files']:
  path=ROOT/entry['file']
  with path.open() as f:rows=list(csv.DictReader(f))
  assert all(r['status']=='PROVISIONAL' and 'not bounds' in r['limitations'] for r in rows)
  maximum=0.;step_error=0.
  for scenario in sorted(set(r['scenario'] for r in rows)):
   rr=[r for r in rows if r['scenario']==scenario]
   r=np.array([[float(x[k]) for k in ['itrs_x_m','itrs_y_m','itrs_z_m']] for x in rr]);latitude=np.radians([float(x['wgs84_lat_deg']) for x in rr]);longitude=np.radians([float(x['wgs84_lon_deg']) for x in rr]);height=np.array([float(x['wgs84_height_m']) for x in rr])
   a=6378137.;f=1/298.257223563;e2=f*(2-f);N=a/np.sqrt(1-e2*np.sin(latitude)**2)
   expected=np.array([(N+height)*np.cos(latitude)*np.cos(longitude),(N+height)*np.cos(latitude)*np.sin(longitude),(N*(1-e2)+height)*np.sin(latitude)]).T
   maximum=max(maximum,float(np.max(np.linalg.norm(r-expected,axis=1))))
   assert maximum<2e-6,'Independent ellipsoid forward reconstruction failed'
   target=np.array([float(x['model_zg_m']) for x in rr]);lat_target=np.array([float(x['model_lat_deg']) for x in rr])
   if scenario.startswith('A'):
    assert np.max(abs(target-height-np.array([float(x['offset_m']) for x in rr])))<1e-8
    assert np.max(abs(lat_target-np.degrees(latitude)))<1e-10
   else:
    assert np.max(abs(target-(np.linalg.norm(r,axis=1)-6371000)))<1e-8
    assert np.max(abs(lat_target-np.degrees(np.arctan2(r[:,2],np.hypot(r[:,0],r[:,1])))))<1e-10
   seconds=(Time([x['utc'] for x in rr],scale='utc')-Time('2023-03-21T00:00:02',scale='utc')).sec
   expected_seconds=np.array([int(x['sample'])*10 for x in rr]);step_error=max(step_error,float(np.max(abs(seconds-expected_seconds))))
   assert step_error<1e-6 and np.all(np.diff(seconds)>0)
   assert all(int(x['valid'])==1 and float(x['rho_kg_m3'])>0 and np.isfinite(float(x['rho_kg_m3'])) for x in rr)
  result['datasets'][str(path.relative_to(ROOT))]={'rows':len(rows),'maximum_forward_WGS84_reconstruction_m':maximum,'maximum_epoch_difference_s':step_error}
 sources=['third_party/TIEGCM2.0/src/'+name for name in ['addiag.F','lbc.F','params.F','getapex.F','cons.F','init.F','diags.F']]
 result['source_sha256']={name:sha(ROOT/name) for name in sources}
 result['frozen_time_manifest']=json.loads((ROOT/'logs/20261020_frozen_time_data.json').read_text())
 result['official_pdf']={'url':'https://download.hao.ucar.edu/pub/stans/tgcm/ZCoordinates.pdf','bytes':(ROOT/'data/raw/tiegcm2023_sources/ZCoordinates_official_20261020.pdf').stat().st_size,'sha256':sha(ROOT/'data/raw/tiegcm2023_sources/ZCoordinates_official_20261020.pdf')}
 with (OUT/'independent_delivery_audit.json').open('x') as f:json.dump(result,f,indent=2,allow_nan=False)
 print(json.dumps(result['datasets'],indent=2))
if __name__=='__main__':main()
