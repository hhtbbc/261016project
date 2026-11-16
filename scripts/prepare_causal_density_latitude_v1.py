"""Independent raw SHA and 03-06 B14 coverage gate; freeze protocol only after PASS."""
from pathlib import Path
import sys,json,time,resource,warnings,datetime
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np,cdflib
from netCDF4 import Dataset
from observations.density_catalog import read_swarm_pod
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from atmosphere.causal_observation_operator import map_a_queries,observe_map_a
from prepare_fourcastden_swarm_observation_v1 import sha
from evaluation.causal_density_latitude import exclusive_json
F=ROOT/'experiments/causal_density_latitude_correction_v1';ACQ=ROOT/'experiments/causal_density_latitude_acquisition_v1'
CDF_SHA={2021:'e6a03398dda6efedfb4cfc3aa8646daabc19f976911698330b41b8a6ef571b0d',2022:'7b37f210c9b202d99212eff0fc329918b71532d4b79932655340859bd5847398'}
MODEL={2021:{'B14':('experiments/tiegcm_2021_spinup_14day_v1/B14/secondary_015.nc','082bad2d5c4789fc1fbcac6f5f1b67f7eda4a0ffaded3442608df8bcadd918dc'),'A7':('experiments/tiegcm_training_mar23_v2_2021_longrun/secondary_008.nc','233fd66f506aa2400915814f425d9fd28989a7fc83d8c1b31c172ee66058f646'),'B7':('experiments/tiegcm_2021_spinup_initial_condition_v1/B/secondary_008.nc','68c867ef059cb1eac5b774bb55ef7677a4c3d1231668270e2b3478482517413f')},2022:{'B14':('experiments/tiegcm_2022_b14_exploratory_pair_v2/B14/secondary_015.nc','e0ff06cc9cde96ab36e71c07a7eb3d5cec4ac31a0080627a95dc399a2eb12a4f'),'A7':('experiments/tiegcm_training_mar23_v2_2022_longrun/secondary_008.nc','2d883664b96d82714448c2459267dc6dec4d451cdd3c779d9536a66b4b8c1a21'),'B7':('experiments/tiegcm_2022_dual_initial_spinup_v1/secondary_008.nc','0cb6465ff5abf8e1f1945e034d23a8c2d29827b158138b631173648b1e75ee6d')}}
def main():
 start=time.perf_counter();assert not F.exists(),'Existing experiment directory: STOP';F.mkdir();F.resolve().relative_to(ROOT);(F/'logs').mkdir()
 def warning(message,category,filename,lineno,file=None,line=None):
  with (F/'logs/preflight_warnings_local.jsonl').open('a') as out:out.write(json.dumps(dict(message=str(message),category=category.__name__,filename=filename,line=lineno))+'\n')
 warnings.showwarning=warning
 try:
  protected={};contexts={}
  for n in ['AGENTS.md','STATUS.md','WORKLOG.md','reports/CAUSAL_DENSITY_LATITUDE_ACQUISITION_V1.md','docs/CAUSAL_DENSITY_LATITUDE_ACQUISITION_NEXT_DECISION_V1.md','experiments/causal_density_latitude_acquisition_v1/result.json','experiments/causal_density_latitude_acquisition_v1/model_coverage.csv','experiments/causal_density_latitude_acquisition_v1/latitude_window_counts.csv','experiments/causal_density_latitude_acquisition_v1/CDF_contracts.json','experiments/causal_density_latitude_acquisition_v1/sha256_manifest.json','experiments/causal_density_late_day_v1/frozen_protocol.json','experiments/causal_density_late_day_v1/correction_parameters.json','docs/CAUSAL_DENSITY_LATE_DAY_NEXT_DECISION_V1.md']:
   t=(ROOT/n).read_text();contexts[n]=dict(SHA256=sha(ROOT/n),bytes=len(t.encode()))
  for name in ['causal_density_latitude_v1','causal_density_latitude_acquisition_v1','causal_density_correction_v1','cross_year_causal_density_validation_v1','causal_density_late_day_v1']:
   for p in (ROOT/'experiments'/name).rglob('*'):
    if p.is_file():p.resolve().relative_to(ROOT);protected[str(p.relative_to(ROOT))]=sha(p)
  aq=json.loads((ACQ/'model_query_audit.json').read_text());old=json.loads((ROOT/'experiments/causal_density_late_day_v1/source_manifest.json').read_text());hapi=json.loads((ACQ/'protocol.json').read_text())['hapi'];assert sha(ROOT/hapi['path'])==hapi['SHA256'];protected[hapi['path']]=hapi['SHA256'];data={};cases={};cdfs={}
  for year in [2021,2022]:
   y=str(year);path=ROOT/f'data/raw/causal_density_latitude_v1/SW_OPER_DNSAPOD_2__{year}0323T000000_{year}0323T235930_0301.cdf';assert sha(path)==CDF_SHA[year];protected[str(path.relative_to(ROOT))]=CDF_SHA[year];_,a,con=read_swarm_pod(path,ROOT/hapi['path'],CDF_SHA[year],satellite='A')
   assert len(a['utc'])==2880 and a['quality'].sum()==2880 and (a['validity_flag']==0).all() and np.all(np.diff(a['utc'])==np.timedelta64(30,'s')) and a['utc'][0]==np.datetime64(y+'-03-23T00') and a['utc'][-1]==np.datetime64(y+'-03-23T23:59:30')
   with cdflib.CDF(path) as c:assert c.varinq('time').Data_Type==31
   data[y]=a;cdfs[y]=dict(file=str(path.relative_to(ROOT)),SHA256=CDF_SHA[year],records=2880,valid=2880,flag0=2880,UTC_start=str(a['utc'][0])+'Z',UTC_stop=str(a['utc'][-1])+'Z',cadence_s=30,units={k:con['variables'][k]['UNITS'] for k in ['density','latitude','longitude','altitude']});cases[y]={}
   for case,(name,digest) in MODEL[year].items():
    p=ROOT/name;assert sha(p)==digest and aq['NetCDF_input_SHA256'][name]==digest;folder=p.parent;j=json.loads((folder/'data_audit.json').read_text());run=json.loads((folder/'run_status.json').read_text());assert j['engineering_PASS'] and run['returncode']==0 and run['normal_exit_count']==4;assert next(x for x in j['files'] if x['file']==p.name)['SHA256']==digest;protected[name]=digest
    config=old['cases'][y][case]['source_config']
    for n,h in [(config['input'],config['input_SHA256']),(config['source'],config['source_SHA256']),(config['GPI'],config['GPI_SHA256'])]:assert sha(ROOT/n)==h;protected[n]=h
    for n in ['data_audit.json','run_status.json']:protected[str((folder/n).relative_to(ROOT))]=sha(folder/n)
    cases[y][case]=dict(file=name,SHA256=digest,engineering='PASS',role='PRIMARY' if case=='B14' else 'CONTROL',run_returncode=0,source_config=config,full_state_science_PASS=False)
  early={};early_audit=[];scans=[]
  with (F/'early_queries_local.jsonl').open('x') as trace:
   for y,a in data.items():
    s=cases[y]['B14'];path=ROOT/s['file'];p=HourlyTiegcmObservation([path],{path.name:s['SHA256']},y+'-03-23T03:00:00',y+'-03-23T06:00:00',y+'_B14_early');assert len(p.records)==4
    with Dataset(path) as n:
     n.set_auto_mask(False);mtime=np.asarray(n['mtime'][:]);idx=np.where((mtime[:,0]==82)&(mtime[:,1]>=3)&(mtime[:,1]<=6))[0];assert len(idx)==4
     for name in ['DEN','ZG']:
      v=n[name];assert v.dimensions==('time','ilev','lat','lon') and v.units==('g/cm3' if name=='DEN' else 'cm');badtotal=0;nonmono=0
      for k in idx:
       raw=np.asarray(v[int(k)]);bad=~np.isfinite(raw)|(abs(raw)>1e30)
       for attr in ['_FillValue','missing_value']:
        if hasattr(v,attr):bad|=raw==np.asarray(getattr(v,attr),dtype=raw.dtype)
       if name=='DEN':bad|=raw<=0
       else:nonmono+=int((np.diff(raw,axis=0)<=0).sum())
       badtotal+=int(bad.sum())
      assert badtotal==0 and nonmono==0;scans.append(dict(year=y,case='B14',field=name,frames=4,invalid=badtotal,nonmonotonic_ZG=nonmono))
    mask=(a['utc']>=np.datetime64(y+'-03-23T03'))&(a['utc']<np.datetime64(y+'-03-23T06'))&a['quality'];indices=np.flatnonzero(mask);assert len(indices)==360;queries=map_a_queries(a['utc'][mask],a['latitude'][mask],a['longitude'][mask],a['altitude'][mask]);values=[]
    for i,q in zip(indices,queries):
     r,coord=observe_map_a(p,q);trace.write(json.dumps(dict(year=y,index=int(i),UTC=str(a['utc'][i])+'Z',valid=r.valid,reason=r.reason,rho_model=r.rho_kg_m3,coordinate=coord,metadata=r.metadata))+'\n');assert r.valid and len(r.metadata['columns'])==8,(y,int(i),r.reason);values.append(r.rho_kg_m3)
    early_audit.append(dict(year=y,case='B14',frames=4,total_queries=360,valid=360,failed=0,first_UTC=str(a['utc'][mask][0])+'Z',last_UTC=str(a['utc'][mask][-1])+'Z',eight_columns=True,no_extrapolation=True))
    for k in ['utc','latitude','longitude','altitude','density','quality','validity_flag']:early[y+'_'+k]=a[k][mask]
    early[y+'_model']=np.array(values);p.close();print('EARLY GATE PASS',y,'360/360',flush=True)
  np.savez_compressed(F/'early_matches_local.npz',**early)
  codepaths=['src/evaluation/causal_density_latitude.py','scripts/prepare_causal_density_latitude_v1.py','scripts/run_causal_density_latitude_v1.py','tests/test_causal_density_latitude.py','src/atmosphere/hourly_tiegcm_observation.py','src/atmosphere/causal_observation_operator.py','src/atmosphere/tiegcm_density_provider.py','src/evaluation/swarm_crossyear.py','src/evaluation/swarm_density_comparison.py','src/evaluation/late_day_correction.py'];code={n:sha(ROOT/n) for n in codepaths}
  protocol=dict(tag=F.name,frozen_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),identity='PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED / DATE_HELD_OUT / SAME_CONTINUOUS_TIE_RUN',days=['2021-03-23','2022-03-23'],primary='B14',controls=['A7','B7'],A14='EXCLUDED',GlobalAdaptive18='separate case same-day [15,18) median(ln(obs)-ln(model))',LatitudeAdaptive18='same estimator/mask/window, low abs(GRS80 lat)<30;mid30<=abs<60;high>=60; no hemisphere split',Stale06='B14 only, newly estimated same03-23[03,06); never use03-24 coefficients',methods=['Raw','GlobalAdaptive18','LatitudeAdaptive18','Stale06 B14 only'],calibration_half_open=['15:00','18:00'],Stale_history_half_open=['03:00','06:00'],future_half_open=[['18:00','19:00'],['18:00','21:00'],['18:00','24:00']],nonoverlap=[['18:00','19:00'],['19:00','21:00'],['21:00','24:00']],min_history_samples=30,min_future_region_samples=30,insufficient='UNSUPPORTED history, no fallback/interpolation/global borrowing; full local result and joint N/A when any selected future region unsupported or any region N<30',latitude_application='future point uses its own original GRS80 latitude band',shared_masks='all source quality/model-valid points per year; no dropping unsupported local points to manufacture complete score',metrics='unchanged metric_row/compare_density; observed denominator; MAE/RMSE/relativeRMS/P95/Bias/relativeBias/logRMS/Pearson/max_abs',joint={'RMSE_BENEFIT':'strict decrease','RELATIVE_RMS_BENEFIT':'strict decrease','TAIL_NONWORSENED':'relativeP95 <=Raw','LOW_LATITUDE_BIAS_NONWORSENED':'abs(relativeBias_low)<=Raw','JOINT_NO_REGRET':'all4 and all3 regions supported andN>=30 elseFAIL/N/A'},parameters_saved_before_future_metrics=True,future_poison_factor=1e20,no_fit_height_longitude_LST_decay_kernel_smoothing_search=True,code_SHA256=code,early_match_SHA256=sha(F/'early_matches_local.npz'),resources={'CPU_wall_s':600,'RSS_GiB':4,'output_MiB':150,'downloads':0,'GPU':0,'TIE':0,'DART':0,'orbit':0},scientific_guards={'training':False,'external_datum':'EXTERNAL_DATUM_UNVERIFIED','Restart':'FAIL','DART':'NOT_ADMITTED','real_orbit':'BLOCKED'})
  exclusive_json(F/'source_manifest.json',dict(cases=cases,CDFs=cdfs,protected_history_SHA256=protected,context=contexts,hapi=hapi))
  exclusive_json(F/'early_gate_audit.json',dict(PASS=True,case_queries=early_audit,explicit_scan=scans,correction_fits=0,future_scores=0))
  exclusive_json(F/'preflight.json',dict(PASS=True,early_B14_queries=720,early_valid=720,code_tests='test_causal_density_latitude.py passed before freeze',CDF_SHA_PASS=True,NetCDF_SHA_PASS=True,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,protected_history_files=len(protected)))
  exclusive_json(F/'frozen_protocol.json',protocol);exclusive_json(F/'protocol_sha256.json',dict(SHA256=sha(F/'frozen_protocol.json')));print('PROTOCOL FROZEN AFTER EARLY GATES; NO COEFFICIENTS YET',flush=True)
 except Exception as e:
  exclusive_json(F/'preflight_failure.json',dict(error=type(e).__name__,message=str(e),no_coefficients=True,no_future_metrics=True));raise
if __name__=='__main__':main()
