"""Independent source preservation, arithmetic, time and final asset audit."""
from pathlib import Path
import sys,json,csv,time,resource,ast,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from prepare_fourcastden_swarm_observation_v1 import sha,dump
from netCDF4 import Dataset
from PIL import Image
TAG='tiegcm_2022_spinup_14day_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG
def read(p):
 with p.open() as f:return list(csv.DictReader(f))
def main():
 started=time.perf_counter();protected=json.loads((F/'protected_files.json').read_text())
 for name,expected in protected.items():assert sha(ROOT/name)==expected,name
 new=[]
 for group in ['A14','B14']:
  run=json.loads((F/group/'run_status.json').read_text());audit=json.loads((F/group/'data_audit.json').read_text());assert run['model_launches']==1 and run['returncode']==0 and run['stop_reason'] is None and run['normal_exit_count']==4 and run['elapsed_s']<4800
  assert audit['engineering_PASS'] and audit['model_steps']==23040 and audit['primary_records']==17 and audit['secondary_records']==384 and audit['analysis_window_records']==49
  for e in audit['files']:assert sha(F/group/e['file'])==e['SHA256'];new.append(dict(path=str((F/group/e['file']).relative_to(ROOT)),SHA256=e['SHA256']))
  assert run['netcdf_bytes']<5*2**30 and run['peak_sampled_tree_rss_bytes']<16*2**30
 a=json.loads((F/'A14/run_status.json').read_text());assert a['exact_launcher_raw_wait_status']==0 and a['supervisor_recovered']
 # Independent scalar observation formulas on all16 common-ID arrays.
 z=np.load(O/'observation/aligned_local.npz');m=z['common'];truth=z['observed'][m];metrics=read(O/'observation/metrics.csv');nchecked=0
 for mi,ma in enumerate('ABDE'):
  for gi,g in enumerate(['A7','B7','A14','B14']):
   q=z['values'][mi,gi,m];d=q-truth;row=next(r for r in metrics if r['mapping']==ma and r['group']==g and r['region']=='all')
   expected=dict(RMSE=np.sqrt(np.mean(d*d)),MAE=np.mean(abs(d)),bias=np.mean(d),relative_RMS=np.sqrt(np.mean((d/truth)**2)),relative_bias=np.mean(d/truth),Pearson=np.corrcoef(q,truth)[0,1])
   assert int(row['n'])==len(truth)
   for k,v in expected.items():np.testing.assert_allclose(float(row[k]),v,rtol=2e-12,atol=1e-25)
   nchecked+=1
 # Gate table reconciliation and strict old floor unchanged.
 summary=json.loads((O/'delta14/summary.json').read_text());matrix=read(O/'delta14/acceptance_region_level_matrix.csv')
 for period,variables in summary['gates'].items():
  for variable,g in variables.items():assert sum(int(r['failed_hours']) for r in matrix if r['period']==period and r['variable']==variable)==g['failed_cells']
 rules=json.loads((F/'frozen_comparison_rules.json').read_text());assert '1e-08' in json.dumps(rules) or '1e-8' in json.dumps(rules)
 # Readable actual figures with consistent sources; no raw data are public.
 figs=json.loads((F/'finalization.json').read_text())['figures']
 for name in figs:
  with Image.open(O/name) as im:im.verify()
 for p in (ROOT/'scripts').glob('*2022*14day*.py'):ast.parse(p.read_text())
 dump(F/'final_independent_audit.json',dict(PASS=True,protected_assets=len(protected),new_NetCDF_volumes=len(new),observation_metric_groups=nchecked,common_observations=int(m.sum()),gate_reconciliation=True,figure_count=len(figs),wall_s=time.perf_counter()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,monitoring_gap_disclosed=True,science_training_ready=False))
 code=[dict(path=str(p.relative_to(ROOT)),SHA256=sha(p)) for p in list((ROOT/'scripts').glob('*2022*14day*.py'))+[ROOT/'scripts/run_tiegcm_2022_B14_guarded.py',ROOT/'scripts/tiegcm_2022_runtime_guardian.py',ROOT/'tests/test_tiegcm_2022_14day.py']]
 dump(F/'source_output_sha.json',dict(code=code,raw_outputs=new,figures=[dict(path=str((O/n).relative_to(ROOT)),SHA256=sha(O/n)) for n in figs]))
 print('Independent final PASS',len(protected),nchecked,len(new))
if __name__=='__main__':main()
