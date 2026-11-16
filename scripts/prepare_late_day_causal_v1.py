"""Read-only SHA/boundary gate, frozen late-day methods before residual fitting."""
from pathlib import Path
import sys,json,csv,time,datetime,shutil,os,warnings
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
from prepare_fourcastden_swarm_observation_v1 import sha
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
F=ROOT/'experiments/causal_density_late_day_v1'
def main():
 start=time.perf_counter();assert not F.exists();F.mkdir();assert F.resolve().is_relative_to(ROOT)
 def warning(message,category,filename,lineno,file=None,line=None):
  with (F/'preflight_warnings_local.jsonl').open('a') as f:f.write(json.dumps(dict(message=str(message),category=category.__name__,filename=filename,line=lineno))+'\n')
 warnings.showwarning=warning;protected={};context={}
 for n in ['AGENTS.md','STATUS.md','WORKLOG.md','reports/CAUSAL_DENSITY_CORRECTION_PILOT_V1.md','docs/CAUSAL_DENSITY_CORRECTION_NEXT_DECISION_V1.md','reports/CROSS_YEAR_CAUSAL_DENSITY_VALIDATION_V1.md','docs/CROSS_YEAR_CAUSAL_DENSITY_NEXT_DECISION_V1.md','reports/HEIGHT_DATUM_OFFICIAL_EVIDENCE_UPDATE_V1.md']:
  s=(ROOT/n).read_text();context[n]={'bytes':len(s.encode()),'SHA256':sha(ROOT/n)}
 old=json.loads((ROOT/'experiments/cross_year_causal_density_validation_v1/sha256_manifest.json').read_text())
 for n,h in old['public_files_SHA256'].items():
  if n in ['STATUS.md','WORKLOG.md','.gitignore']:continue
  assert sha(ROOT/n)==h,n;protected[n]=h
 v11=json.loads((ROOT/'experiments/cross_year_causal_density_validation_v1/source_manifest.json').read_text());v10=json.loads((ROOT/'experiments/causal_density_correction_v1/matched_samples_manifest.json').read_text());p21=ROOT/'experiments/cross_year_causal_density_validation_v1/correction_parameters.json';p22=ROOT/'experiments/causal_density_correction_v1/correction_parameters.json';assert sha(p21)==old['public_files_SHA256'][str(p21.relative_to(ROOT))];assert sha(p22)==v11['protected_inputs'][str(p22.relative_to(ROOT))]
 stale={2021:json.loads(p21.read_text())['adaptive']['B14']['b_2021'],2022:json.loads(p22.read_text())['parameters']['B14']['b']};assert stale=={2021:.09399076703699727,2022:.1261252775057784};protected[str(p22.relative_to(ROOT))]=sha(p22)
 provenance=list(csv.DictReader((ROOT/'results/thermosphere_observation_assimilation_feasibility_v1/eight_trajectory_provenance.csv').open()));sources={};boundaries=[]
 for year in [2021,2022]:
  sources[str(year)]={}
  inputpath=ROOT/('experiments/swarm_tiegcm_2021_spinup_observation_v1/inputs.json' if year==2021 else 'experiments/swarm_tiegcm_2022_observation_v1/inputs.json');inp=json.loads(inputpath.read_text());protected[str(inputpath.relative_to(ROOT))]=sha(inputpath)
  for case in ['B14','A7','B7']:
   row=next(x for x in provenance if x['case']==f'{year}_{case}');folder=(ROOT/row['input']).parent;data=json.loads((folder/'data_audit.json').read_text());run=json.loads((folder/'run_status.json').read_text());assert data['engineering_PASS'] and run['returncode']==0 and run['normal_exit_count']==4
   entries=v11['cases'][case]['files'] if year==2021 else next(x for x in v10['cases'] if x['case']==case)['input_files']
   expected={e['file']:e['SHA256'] for e in entries}
   for e in entries:
    path=folder/e['file'];assert sha(path)==e['SHA256'];assert next(x for x in data['files'] if x['file']==e['file'])['SHA256']==e['SHA256'];protected[str(path.relative_to(ROOT))]=e['SHA256']
   # A7 original year-specific inputs are an additional independent legacy source.
   if case=='A7':assert {e['file']:e['SHA256'] for e in (inp[case]['files'] if year==2021 else inp['files'])}==expected
   stop=f'{year}-03-25T00:00:00';p=HourlyTiegcmObservation([folder/e['file'] for e in entries],expected,f'{year}-03-24T15:00:00',stop,f'{year}_{case}');assert len(p.records)==10 and p.records[-1][0].utc.isot==stop+'.000'
   boundaries.append(dict(year=year,case=case,first_frame=p.records[0][0].utc.isot,last_frame=p.records[-1][0].utc.isot,frames=10,supports_last_observation_UTC=f'{year}-03-24T23:59:30Z',hourly_continuity_PASS=True))
   for n,h in [(row['input'],row['input_SHA256']),(row['source'],row['source_SHA256']),(row['GPI'],row['GPI_SHA256'])]:assert sha(ROOT/n)==h;protected[n]=h
   for n in ['data_audit.json','run_status.json']:protected[str((folder/n).relative_to(ROOT))]=sha(folder/n)
   sources[str(year)][case]=dict(folder=str(folder.relative_to(ROOT)),files=entries,source_config=row,engineering='PASS',role='PRIMARY' if case=='B14' else 'CONTROL',real_launcher_returncode=0,normal_exits=4,full_state_science='NOT_PASS; density-only use, no release of composition gates');p.close()
 observations={}
 for e in json.loads((ROOT/'experiments/thermosphere_observation_assimilation_feasibility_v1/observation_quality.json').read_text()):
  if e['satellite']=='A':
   assert sha(ROOT/e['source_file'])==e['source_SHA256'];protected[e['source_file']]=e['source_SHA256'];observations[str(e['year'])]=e
 protocol=dict(tag=F.name,frozen_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),identity='LATE_DAY_ROLLING_ORIGIN / PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED',years=[2021,2022],cutoff_hour=18,history_half_open=['15:00','18:00'],cumulative_half_open=[['18:00','19:00'],['18:00','21:00'],['18:00','24:00']],nonoverlap_half_open=[['18:00','19:00'],['19:00','21:00'],['21:00','24:00']],primary='B14',controls=['A7','B7'],A14='EXCLUDED both years; historical engineering2021PASS/2022PARTIAL unchanged',methods={'Raw':'b=0','Adaptive18':'each year/background median past A log(obs/model), unchanged estimator','Stale06':'B14 only, exact frozen same-year06Z coefficient, no refit','CrossYearTransfer18':'B14 only, other-year15-18 coefficient, no target-future fitting'},stale06_coefficients=stale,parameter_freeze='All 6 own late-day coefficients and4 B14 applied coefficients written before any future-error evaluation',quality='0301 flag0; positive finite; eight model columns mandatory; no fill/extrapolation',common='per-year intersection all3 cases; separate own and common coverage',metrics='existing metric_row; original observation relative denominator; relativeP95; physical units; N<30 N/A',density_bins='Per-year per-future-window observation quintiles (np.quantile linear), ties remain together; descriptive only; not fit/tune/select',density_contributions='both SSE sum, SSE/N (MSE contribution), share of total; relative analog; identity verified without different density weighting',regions='Frozen v11 strata; additional low/mid/high x preexisting height bins; raw observed ellipsoid height used only for descriptive stratification; N>=30',joint_rules={'RMSE_BENEFIT':'corrected RMSE < raw RMSE','RELATIVE_RMS_BENEFIT':'corrected relative RMS < raw','TAIL_NONWORSENED':'corrected relative P95 <= raw','LOW_LATITUDE_BIAS_NONWORSENED':'abs(mean corrected low-lat relativeBias) <= abs(raw); lowN>=30','JOINT_NO_REGRET':'all4 true; missing region never PASS'},no_parameter_search=True,no_new_observation_download=True,science_guards={'training':False,'external':'EXTERNAL_DATUM_UNVERIFIED','Restart':'FAIL','DART':'NOT_ADMITTED','real_orbit':'BLOCKED'},resources={'CPU_wall_s':600,'RSS_GiB':4,'output_MiB':150,'GPU':0,'TIE':0,'DART':0,'orbit':0})
 assert shutil.disk_usage(ROOT).free>20*2**30
 for n,x in [('frozen_protocol.json',protocol),('source_manifest.json',dict(cases=sources,observations=observations,protected_inputs=protected,context=context,boundary_audit=boundaries)),('preflight.json',dict(PASS=True,boundary_24Z_PASS=True,six_cases_complete=True,source_file_SHA_PASS=True,free_disk_bytes=shutil.disk_usage(ROOT).free,available_memory=[s for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable')],cpu_affinity=len(os.sched_getaffinity(0)),wall_s=time.perf_counter()-start,formal_height_unverified=True))]:
  with (F/n).open('x') as out:json.dump(x,out,indent=2)
 print('LATE-DAY FROZEN; all six24Z boundary gates PASS',flush=True)
if __name__=='__main__':main()
