"""Metadata/SHA preflight and protocol freeze. No future residual analysis."""
from pathlib import Path
import sys,json,time,resource,hashlib,shutil
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R),str(R/'src')]
from netCDF4 import Dataset
import numpy as np
from observations.density_catalog import read_swarm_pod
F=R/'experiments/thermosphere_residual_representativeness_v1'
TAGS=['causal_density_correction_v1','cross_year_causal_density_validation_v1','causal_density_late_day_v1','causal_density_latitude_correction_v1']
def sha(p):
 p=Path(p);p.resolve().relative_to(R);h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(2**20),b''):h.update(x)
 return h.hexdigest()
def dump(n,x):
 with (F/n).open('x') as out:json.dump(x,out,indent=2,allow_nan=False)
def main():
 start=time.perf_counter();assert R.resolve()==Path('/workspace/data/20261016');assert not F.exists();F.resolve().relative_to(R);F.mkdir();(F/'logs').mkdir();protected={};context={}
 reports=['reports/CAUSAL_DENSITY_CORRECTION_PILOT_V1.md','reports/CROSS_YEAR_CAUSAL_DENSITY_VALIDATION_V1.md','reports/CAUSAL_DENSITY_LATE_DAY_VALIDATION_V1.md','reports/CAUSAL_DENSITY_LATITUDE_CORRECTION_V1.md','docs/CAUSAL_DENSITY_LATITUDE_CORRECTION_NEXT_DECISION_V1.md','docs/TIEGCM_SWARM_COORDINATE_DATUM.md','docs/TIEGCM_ZG_REGISTRATION_STATUS_20261103.md','reports/HEIGHT_DATUM_OFFICIAL_EVIDENCE_UPDATE_V1.md','reports/TIEGCM_ZG_EXTERNAL_REGISTRATION_PACKAGE_V2.md']
 for n in ['AGENTS.md','STATUS.md','WORKLOG.md']+reports:(R/n).read_text();context[n]=sha(R/n)
 for n in reports:protected[n]=context[n]
 caches={}
 for tag in TAGS:
  p=R/'experiments'/tag;old=json.loads((p/'sha256_manifest.json').read_text());cache=p/'matched_local.npz';expected=old.get('matched_values_local_SHA256',old.get('matched_local_SHA256',old.get('local_only_hashes',{}).get(str(cache.relative_to(R)))));assert expected and sha(cache)==expected; caches[tag]=dict(path=str(cache.relative_to(R)),SHA256=expected)
  for x in p.rglob('*'):
   if x.is_file():protected[str(x.relative_to(R))]=sha(x)
 late=json.loads((R/'experiments/causal_density_late_day_v1/source_manifest.json').read_text());lat=json.loads((R/'experiments/causal_density_latitude_correction_v1/source_manifest.json').read_text());hapi=lat['hapi'];assert sha(R/hapi['path'])==hapi['SHA256'];protected[hapi['path']]=hapi['SHA256'];obs={};models={}
 for y in ['2021','2022']:
  for day in ['23','24']:
   date=y+'-03-'+day;s=lat['CDFs'][y] if day=='23' else late['observations'][y];path=s['file'] if day=='23' else s['source_file'];digest=s['SHA256'] if day=='23' else s['source_SHA256'];assert sha(R/path)==digest
   _,a,contract=read_swarm_pod(R/path,R/hapi['path'],digest,satellite='A');assert len(a['utc'])==2880 and a['quality'].all() and (a['validity_flag']==0).all() and np.all(np.diff(a['utc'])==np.timedelta64(30,'s'));assert a['utc'][0]==np.datetime64(date+'T00') and a['utc'][-1]==np.datetime64(date+'T23:59:30');obs[date]=dict(path=path,SHA256=digest,records=2880,valid=2880);protected[path]=digest
  models[y]={}
  for case in ['B14','A7','B7']:
   s=late['cases'][y][case];folder=R/s['folder'];assert json.loads((folder/'data_audit.json').read_text())['engineering_PASS'] and json.loads((folder/'run_status.json').read_text())['returncode']==0;files=[]
   for entry in s['files']:
    p=folder/entry['file'];assert sha(p)==entry['SHA256'];protected[str(p.relative_to(R))]=entry['SHA256'];files.append(dict(path=str(p.relative_to(R)),SHA256=entry['SHA256']))
    with Dataset(p) as n:
     assert n['DEN'].dimensions==n['ZG'].dimensions==('time','ilev','lat','lon') and n['DEN'].units=='g/cm3' and n['ZG'].units=='cm'
   models[y][case]=dict(files=files,engineering='PASS',full_state_science='NOT_PASS',source_config=s['source_config'])
 code_names=['src/evaluation/residual_representativeness.py','scripts/run_residual_representativeness_v1.py','scripts/verify_residual_representativeness_v1.py','scripts/prepare_residual_representativeness_v1.py','tests/test_residual_representativeness.py','src/evaluation/swarm_crossyear.py','src/evaluation/late_day_correction.py','src/evaluation/causal_density_latitude.py','src/atmosphere/causal_density_correction.py','src/atmosphere/provisional_coordinate_adapter.py','src/atmosphere/causal_observation_operator.py','src/atmosphere/hourly_tiegcm_observation.py','src/atmosphere/tiegcm_density_provider.py','src/atmosphere/density_interface.py']
 code={n:sha(R/n) for n in code_names};protected.update({n:h for n,h in code.items() if n.startswith('src/') and 'residual_representativeness' not in n})
 protocol=dict(tag=F.name,frozen_UTC=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),identity='PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED',days=sorted(obs),cutoffs_UTC=[6,18],primary='B14',controls=['A7','B7'],A14='EXCLUDED',half_open=True,history_hours=3,future_hours=[1,3,6],nonoverlap_future_hours=[[0,1],[1,3],[3,6]],descriptive_time_block_hours=1,min_region_samples=30,statistics='mean/median/population std ddof0/unscaledMAD/linear quantiles .05,.25,.75,.95/strict positive fraction',residual='ln(observation)-ln(model); future median descriptive only, never used to make prediction',overlap='sum min(histogram probabilities); fixed residual edges -inf,-4 to4 step.1,+inf; no dropped overflow; descriptive only',latitude_regions='abs(GRS80 lat)<30,30<=abs<60,abs>=60; merged hemispheres',density_bins='unchanged v12 diagnostic_quintiles, ties together; future observed quintiles descriptive only',decomposition='same paired IDs; absolute/relative SS and contributions normalized by whole windowN; byquintile/latitude/timeblock and quintile xlatitude; groupN<30 clearly descriptive smallN',frozen_prediction_scope='only existing GlobalAdaptive/LatitudeAdaptive forecasts;03-23 06Z only raw residual diagnostics, no new forecast from historical median; unavailable methodsN/A',coordinate_contract=dict(ellipsoids={'GRS80':[6378137.,298.257222101],'WGS84':[6378137.,298.257223563]},independent='explicit double precision ellipsoid forward and20-step fixed-point inverse, independent of Astropy EarthLocation; same-point GRS/WGS differences not forced tozero',analytic_lat=[0,30,-30,45,-45,60,-60,89.999,-89.999,90,-90],analytic_lon=[-180,180,540,-540,0,90],analytic_height_m=[0,450000,800000],actual_points='every120th record eachday pluslast record:25/day,100 total',tolerances=dict(XYZ_m=1e-5,height_m=1e-5,angle_deg=5e-10,metric_rtol=1e-13,metric_atol=0,identity_rtol=1e-12),rationale='float64 epsilon~2.22e-16, Earth position scale~1e7m; numerical regression tolerances with guard factors, not physical accuracy bounds; no post-result adjustment',pole_longitude='undefined at horizontal radius<1e-6m; compare Cartesian position and height, not longitude'),new_queries='only missing03-23 early B14future720 and A7/B7 history+future1080each, peryear2880; bothyears5760; exact old Map-A/eight-column rule',old_results_recomputed='independent reproduction only, no tuning or new fitted parameters',resources=dict(supervised_wall_s=600,RSS_GiB=4,public_MiB=150,downloads=0,GPU=0,TIE=0,DART=0,orbit=0),code_SHA256=code)
 dump('source_manifest.json',dict(observations=obs,models=models,caches=caches,hapi=hapi,protected_SHA256=protected,context_SHA256=context));dump('frozen_protocol.json',protocol);dump('protocol_sha256.json',dict(SHA256=sha(F/'frozen_protocol.json')));dump('preflight.json',dict(PASS=True,days=4,date_cutoff_combinations=8,background_combinations=24,raw_observation_records=11520,new_fit_allowed=False,free_disk_bytes=shutil.disk_usage(R).free,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,algorithm_tests='run after protocol freeze, before supervised diagnostic',protected_files=len(protected)))
 print('Protocol frozen; no future residual distribution calculated yet.')
if __name__=='__main__':main()
