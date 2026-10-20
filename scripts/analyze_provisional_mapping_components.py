"""PROVISIONAL coarse factorial coordinate and seam diagnostics, no integration."""
import sys,csv,json,time
from pathlib import Path
from dataclasses import asdict,replace
import numpy as np
from astropy.time import Time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from atmosphere.density_interface import DensityQuery
from atmosphere.provisional_coordinate_adapter import ProvisionalCoordinateAdapter,ProvisionalDensityResult,A_WGS84,B_SPHERE
from atmosphere.tiegcm_density_provider import TiegcmDensityProvider,DATUM
from summarize_swarm_provisional_density import load,metric,I
TAG='swarm_provisional_v1';OUT=ROOT/'experiments'/TAG

def main():
 report={'status':'PROVISIONAL','definitions':{'D_LAT_ONLY':'A height + B geocentric latitude','E_HEIGHT_ONLY':'A geodetic latitude + B sphere height','interaction':'rho_B * rho_A / (rho_D * rho_E) - 1; not an additive uncertainty'},'sources':{}}
 start=time.perf_counter();rows=[]
 for source in ['S3','S7']:
  with (ROOT/f'results/metrics/{TAG}_coarse_{source}.csv').open() as f:records=list(csv.DictReader(f))
  a_rows={r['sample']:r for r in records if r['scenario']=='A+0km'};b_rows={r['sample']:r for r in records if r['scenario']=='B_R6371km'}
  factors=[]
  with TiegcmDensityProvider((ROOT/f'experiments/tiegcm2023_{source.lower()}_continuous_v1').glob('secondary_*.nc'),source) as p:
   for key,row in a_rows.items():
    q=DensityQuery.from_itrs(Time(row['utc'],scale='utc'),[float(row[k]) for k in ['itrs_x_m','itrs_y_m','itrs_z_m']])
    a=ProvisionalCoordinateAdapter(assumption=A_WGS84).adapt(q)
    b=ProvisionalCoordinateAdapter(assumption=B_SPHERE,sphere_radius_m=6371000).adapt(q)
    coords=[replace(a,assumption='D_LAT_ONLY',model_latitude_deg=b.model_latitude_deg),replace(a,assumption='E_HEIGHT_ONLY',model_zg_m=b.model_zg_m,sphere_radius_m=6371000)]
    density=[]
    for c in coords:
     result=ProvisionalDensityResult(c,p.query_native(q.utc,c.model_latitude_deg,c.model_longitude_deg,c.model_zg_m,datum=DATUM))
     assert result.native_result.valid
     density.append(result.native_result.rho_kg_m3)
     rows.append({'status':'PROVISIONAL','source':source,'sample':key,'assumption':c.assumption,'utc':c.utc,'itrs_m':json.dumps(c.itrs_m),'wgs84_lon_deg':c.wgs84_longitude_deg,'wgs84_lat_deg':c.wgs84_latitude_deg,'wgs84_height_m':c.wgs84_height_m,'model_lat_deg':c.model_latitude_deg,'model_lon_deg':c.model_longitude_deg,'model_zg_m':c.model_zg_m,'sphere_radius_m':c.sphere_radius_m,'height_offset_m':c.height_offset_m,'rho_kg_m3':density[-1],'limitations':c.limitations})
    rho_a=float(row['rho_kg_m3']);rho_b=float(b_rows[key]['rho_kg_m3'])
    factors.append([density[0]/rho_a-1,density[1]/rho_a-1,rho_b*rho_a/(density[0]*density[1])-1])
  factors=np.array(factors)
  full=load(ROOT/f'data/processed/{TAG}/PROVISIONAL_full_{source}.csv')
  continuity={}
  for scenario,data in full.items():
   rho=data[:,I['rho_kg_m3']];lon=data[:,I['model_lon_deg']];lat=data[:,I['model_lat_deg']]
   step=np.diff(np.log(rho));seam=np.flatnonzero(abs(np.diff(lon))>180)
   high=(abs(lat[:-1])>85)|(abs(lat[1:])>85)
   events=[{'sample0':int(data[i,0]),'sample1':int(data[i+1,0]),'lon0':float(lon[i]),'lon1':float(lon[i+1]),'log_density_step':float(step[i])} for i in seam]
   continuity[scenario]={'all_10s_log_steps':metric(step),'seam_10s_log_steps':metric(step[seam]),'high_lat_10s_log_steps':metric(step[high]),'seam_events':events,'minimum_latitude_center_margin_deg':float(87.5-np.max(abs(lat)))}
  report['sources'][source]={'latitude_only_relative':metric(factors[:,0]),'height_only_relative':metric(factors[:,1]),'interaction_relative':metric(factors[:,2]),'continuity':continuity}
 report['seconds']=time.perf_counter()-start
 with (OUT/'mapping_components_and_continuity.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False)
 with (ROOT/f'results/metrics/{TAG}_mapping_components.csv').open('x') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
 print(json.dumps({s:{k:v for k,v in r.items() if k!='continuity'} for s,r in report['sources'].items()},indent=2))
if __name__=='__main__':main()
