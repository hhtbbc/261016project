"""Freeze v11 inputs and roles before matching or fitting; no downloads."""
from pathlib import Path
import sys,json,csv,hashlib,shutil,os,time,datetime
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/cross_year_causal_density_validation_v1';sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from prepare_fourcastden_swarm_observation_v1 import sha

def main():
 start=time.perf_counter();assert not F.exists();assert F.resolve().is_relative_to(ROOT);F.mkdir();protected={};source={};notes={}
 contexts=['AGENTS.md','STATUS.md','WORKLOG.md','reports/CAUSAL_DENSITY_CORRECTION_PILOT_V1.md','reports/SWARM_TIEGCM_2021_SPINUP_OBSERVATION_V1.md','reports/HEIGHT_DATUM_OFFICIAL_EVIDENCE_UPDATE_V1.md','docs/CAUSAL_DENSITY_CORRECTION_NEXT_DECISION_V1.md']
 for n in contexts:
  text=(ROOT/n).read_text();notes[n]={'SHA256':sha(ROOT/n),'bytes':len(text.encode())}
 prior=ROOT/'experiments/causal_density_correction_v1';old=json.loads((prior/'sha256_manifest.json').read_text())
 for n,h in old['public_files_SHA256'].items():assert sha(ROOT/n)==h,n;protected[n]=h
 coeff=json.loads((prior/'correction_parameters.json').read_text())['parameters']['B14'];assert coeff['b']==.1261252775057784 and coeff['density_multiplier']==1.1344242772252575
 inventory=ROOT/'experiments/swarm_tiegcm_2021_spinup_observation_v1/inputs.json';j=json.loads(inventory.read_text());protected[str(inventory.relative_to(ROOT))]=sha(inventory)
 sources=list(csv.DictReader((ROOT/'results/thermosphere_observation_assimilation_feasibility_v1/eight_trajectory_provenance.csv').open()))
 for case in ['B14','A7','B7','A14']:
  row=next(x for x in sources if x['case']=='2021_'+case);folder=(ROOT/row['input']).parent;audit=json.loads((folder/'data_audit.json').read_text());run=json.loads((folder/'run_status.json').read_text());assert audit['engineering_PASS'] and run['returncode']==0 and run['normal_exit_count']==4
  for n,h in [(row['input'],row['input_SHA256']),(row['source'],row['source_SHA256']),(row['GPI'],row['GPI_SHA256'])]:assert sha(ROOT/n)==h;protected[n]=h
  for e in j[case]['files']:
   path=folder/e['file'];assert sha(path)==e['SHA256'];assert next(x for x in audit['files'] if x['file']==e['file'])['SHA256']==e['SHA256'];protected[str(path.relative_to(ROOT))]=e['SHA256']
  for name in ['data_audit.json','run_status.json']:protected[str((folder/name).relative_to(ROOT))]=sha(folder/name)
  source[case]=dict(folder=str(folder.relative_to(ROOT)),files=j[case]['files'],source_config=row,engineering='PASS',role='PRIMARY' if case=='B14' else ('SENSITIVITY_ONLY' if case=='A14' else 'CONTROL'),launcher_returncode=0,normal_exits=4,scientific_state='Full-state science NOT_PASS; DEN valid != full-state convergence; 2021 O1/O2/N2 failures retained')
 proof=next(x for x in json.loads((ROOT/'experiments/thermosphere_observation_assimilation_feasibility_v1/observation_quality.json').read_text()) if x['satellite']=='A' and x['year']==2021);assert sha(ROOT/proof['source_file'])==proof['source_SHA256'];protected[proof['source_file']]=proof['source_SHA256']
 protocol=dict(tag=F.name,frozen_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),identity='CROSS_YEAR_METHOD_REPLICATION / PROVISIONAL MAP_A / HINDCAST / NOT_BLIND',day='2021-03-24',cutoff='2021-03-24T06:00:00Z',calibration_half_open=['03:00','06:00'],cumulative_future_half_open=[['06:00','07:00'],['06:00','09:00'],['06:00','12:00']],nonoverlap_half_open=[['06:00','07:00'],['07:00','09:00'],['09:00','12:00']],primary='B14',controls=['A7','B7'],sensitivity=['A14'],A14_engineering_2021='PASS; sensitivity by role',A14_engineering_2022='PARTIAL unchanged',methods={'Raw':'b=0','Transfer':'B14 ONLY, exact v10 b2022; no 2021 fit','Adaptive':'separate case median(log(obs)-log(background)), A history only'},transfer_b=coeff['b'],transfer_multiplier=coeff['density_multiplier'],no_hyperparameter_search=True,no_future_observations_in_fit=True,mask='Same per-window IDs for Raw/Transfer/Adaptive; all-case own/common coverage also reported',regions='existing frozen strata; low abs<30,mid30-60,high>=60,north/south>=60 and height400/430/440/450/460/470/500km; N<30 N/A',metrics='existing compare_density/metric_row; observed denominator no new floor; model-observation Bias; log_RMS; relative P95; pointwise counts',comparison2022='read-only frozen v10 history residuals/parameters/metrics; never re-estimate2022',illustration='B14 fixed primary, all four backgrounds retained, no best-example selection',resource_limits={'CPU_wall_s':600,'RSS_GiB':4,'output_MiB':150,'downloads':0,'GPU':0,'TIE':0,'DART':0,'orbit':0},science_guards={'training':False,'external_datum':'EXTERNAL_DATUM_UNVERIFIED','real_orbit':'BLOCKED','restart':'FAIL','DART':'NOT_ADMITTED'})
 for n,obj in [('frozen_protocol.json',protocol),('source_manifest.json',dict(cases=source,observation=proof,protected_inputs=protected,context=notes)),('preflight.json',dict(PASS=True,source_volumes_SHA_pass=8,observations_SHA_pass=True,all2021_engineering_PASS=True,full_state_science_PASS=False,old_v10_files_unchanged=len(old['public_files_SHA256']),free_disk_bytes=shutil.disk_usage(ROOT).free,available_memory=[x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable')],cpu_affinity=len(os.sched_getaffinity(0)),wall_s=time.perf_counter()-start))]:
  with (F/n).open('x') as out:json.dump(obj,out,indent=2)
 assert shutil.disk_usage(ROOT).free>20*2**30;print('FROZEN BEFORE ANY 2021 FIT',flush=True)
if __name__=='__main__':main()
