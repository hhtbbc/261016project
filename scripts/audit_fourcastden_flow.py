"""Independent final checks of saved Flow and immutable historical artifacts."""
import sys,json,csv
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_fourcastden_multistep import sha,dump
from fourcastden.flow_validation import flow_feedback_check
F=ROOT/'experiments/fourcastden_flow_two_step_v1'
D=ROOT/'data/processed/fourcastden_flow_two_step_v1'
def main():
 protected=json.loads((F/'protected.json').read_text())
 for p,h in protected.items():
  file=(ROOT/p).resolve();assert file.is_relative_to(ROOT) and sha(file)==h,p
 pre=json.loads((F/'preflight.json').read_text());rt=json.loads((F/'runtime.json').read_text())
 for p,h in pre['code_sha256'].items():assert sha(ROOT/p)==h,p
 assert sha(F/'config.yaml')==pre['config_sha256'] and sha(D/'result.npz')==rt['file_sha256']
 assert rt['network_calls']==2 and rt['no_Direct_execution'] and rt['GPU_phase_wall_s']<300
 with np.load(D/'result.npz') as z:q={k:z[k].copy() for k in z.files}
 real=q['real'][0];pred=q['pred'][0];sw=np.vstack([np.zeros(4),q['scalars0'].reshape(4),q['scalars1'].reshape(4)])
 flow_feedback_check([(q['input0'],q['scalars0']),(q['input1'],q['scalars1'])],[q['increment0'],q['increment1']],real,pred,sw)
 mu=q['means'][:171].astype(float);sig=q['stds'][:171].astype(float)
 physical=pred.astype(float)*sig+mu;ref=real[:,:171].astype(float)*sig+mu
 assert np.isfinite(physical).all() and (physical[:,142:]>0).all() and (physical[:,:28]>0).all()
 lat=np.load(ROOT/'data/processed/static/lat.npy');w=np.cos(np.deg2rad(lat));weights=np.broadcast_to(w[:,None],(36,72));weight_sum=weights.sum()
 check={}
 # Different weighted-sum formulation from channel_metrics: independently audit all 342 channels.
 for h in (1,2):
  err=physical[h]-ref[h];rmse=np.sqrt(np.sum(err**2*weights,axis=(1,2))/weight_sum)
  ap=physical[h]-q['climatology'];ar=ref[h]-q['climatology'];den=np.sqrt(np.sum(weights*ap**2,axis=(1,2))*np.sum(weights*ar**2,axis=(1,2)));assert (den>0).all()
  acc=np.sum(weights*ap*ar,axis=(1,2))/den
  np.testing.assert_allclose(rmse,q['author_rmse'][0,h-1],rtol=2e-5,atol=1e-25);np.testing.assert_allclose(acc,q['author_acc'][0,h-1],rtol=2e-5,atol=2e-6)
  check[str(h)]=dict(max_RMSE_relative=float(np.max(abs(rmse-q['author_rmse'][0,h-1])/rmse)),max_ACC_absolute=float(np.max(abs(acc-q['author_acc'][0,h-1]))))
 expected={'layers':1026,'summary':36,'density_layers':174,'paired':12}
 for name,count in expected.items():
  rows=list(csv.DictReader((ROOT/f'results/metrics/fourcastden_direct_flow_v1_{name}.csv').open()));assert len(rows)==count
 logs=(ROOT/'logs/fourcastden_flow_tests.log').read_text();assert 'Ran 198 tests' in logs and logs.rstrip().endswith('OK')
 plan=json.loads((F/'future_data_plan.json').read_text());inv={x['name'] for x in json.loads((ROOT/'logs/test_archive_inventory.json').read_text())}
 for p in plan['plans']:assert len(p['required_names'])==p['n_history']+p['horizon_hours']+1 and set(p['required_names']).issubset(inv)
 paths=set(F.rglob('*'))|set(D.rglob('*'))
 for folder,pattern in [('results/figures','fourcastden_direct_flow_v1*'),('results/metrics','fourcastden_direct_flow_v1*'),('logs','fourcastden_flow*')]:paths.update((ROOT/folder).glob(pattern))
 files=[p for p in paths if p.is_file() and p.name not in ('delivery_audit.json','fourcastden_flow_audit.log')]
 assert all(p.resolve().is_relative_to(ROOT) for p in files);total=sum(p.stat().st_size for p in files);assert total+1024**2<500*1024**2
 result=dict(status='PASS',protected_files_unchanged=len(protected),Direct_result_sha256=protected['data/processed/fourcastden_two_step_v1/result.npz'],Flow_result_sha256=rt['file_sha256'],formal_Flow_runs=1,real_forwards=2,Direct_rerun=False,tests=198,independent_weighted_sum_metrics=check,feedback_exact=True,DEN_positive_fraction=1.,GPU_phase_wall_s=rt['GPU_phase_wall_s'],new_experiment_bytes=total,code_docs_upper_allowance_bytes=1024**2,budget_bytes=500*1024**2,CSV_row_counts=expected,new_artifact_sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)})
 dump(F/'delivery_audit.json',result)
 print(json.dumps({k:v for k,v in result.items() if k!='new_artifact_sha256'},indent=2))
if __name__=='__main__':main()
