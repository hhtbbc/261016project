"""Final immutable assets, step/resource accounting and synthetic checkpoint audit."""
import sys,json,hashlib,csv
from pathlib import Path
import torch
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/fourcastden_training_smoke_v1';G=ROOT/'experiments/fourcastden_training_smoke_cublas_v2'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def main():
 protected=json.loads((F/'protected.json').read_text())
 for n,h in protected.items():assert sha(ROOT/n)==h,n
 for folder in [F,G]:
  pre=json.loads((folder/'preflight.json').read_text())
  for n,h in pre['code_SHA256'].items():assert sha(ROOT/n)==h,n
 tests=(ROOT/'logs/fourcastden_training_tests.log').read_text();assert 'Ran 247 tests' in tests and tests.rstrip().endswith('OK')
 failed=json.loads((F/'supervision.json').read_text());sup=json.loads((G/'supervision.json').read_text());r=json.loads((G/'gpu_result.json').read_text());assert failed['status']=='FAILED' and sup['status']==r['status']=='PASS'
 first=(ROOT/'logs/fourcastden_training_GPU.log').read_text();assert 'CUBLAS_WORKSPACE_CONFIG' in first and not any(line.startswith('{"step":') for line in first.splitlines())
 assert [x['step'] for x in r['records']]==[1,2,3] and r['train_steps']==3 and all(x['gradient_l2_before_clip']>0 for x in r['records'])
 assert sup['wall_s']+failed['wall_s']<300 and max(sup['peak_GPU_process_bytes'],failed['peak_GPU_process_bytes'])<20*2**30
 assert not r['official_weights_loaded'] and not r['real_data_read']
 p=G/'synthetic_step2.pt';payload=torch.load(p,map_location='cpu',weights_only=False);assert payload['step']==2 and set(payload['model_state']) and set(payload['optimizer_state'])=={'state','param_groups'}
 h=hashlib.sha256()
 for n,t in payload['model_state'].items():h.update(n.encode());h.update(t.contiguous().numpy().tobytes())
 assert h.hexdigest()==r['checkpoint_restore']['parameter_SHA256'];assert sum(x.numel() for x in payload['model_state'].values())==64695744
 assert all(torch.isfinite(t).all() for t in payload['model_state'].values());assert len(payload['model_state'])==150
 artifacts=set()
 for folder in [F,G,ROOT/'src/training',ROOT/'configs/training']:
  artifacts.update(p for p in folder.rglob('*') if p.is_file() and '__pycache__' not in str(p))
 for folder,pattern in [('scripts','*fourcastden_training*.py'),('tests','test_training_pipeline.py'),('reports','FOURCASTDEN_*TRAINING*'),('docs','FOURCASTDEN_MINIMAL_TRAINING_DESIGN.md'),('docs','FOURCASTDEN_DATA_ACQUISITION_PLAN.md'),('docs','FOURCASTDEN_IMPROVEMENT_EXPERIMENT_DESIGN.md'),('logs','fourcastden_training*.log')]:artifacts.update((ROOT/folder).glob(pattern))
 for name in ['STATUS.md','WORKLOG.md','AGENTS.md','.gitignore','docs/FOURCASTDEN_PHASE2_RESEARCH_PLAN.md']:artifacts.add(ROOT/name)
 artifacts={x for x in artifacts if x.name!='delivery_audit.json' and not x.name.endswith('_audit.log')}
 assert all(x.resolve().is_relative_to(ROOT) for x in artifacts)
 size=sum(x.stat().st_size for x in artifacts);assert size<500*2**20
 result=dict(status='PASS',label=r['label'],protected_files_unchanged=len(protected),tests=247,GPU_process_launches=2,failed_launch_completed_steps=0,successful_launch_completed_steps=3,total_optimizer_updates=3,aggregate_supervised_wall_s=sup['wall_s']+failed['wall_s'],peak_GPU_process_bytes=max(sup['peak_GPU_process_bytes'],failed['peak_GPU_process_bytes']),checkpoint_bytes=p.stat().st_size,checkpoint_model_sha256=h.hexdigest(),checkpoint_state_entries=150,checkpoint_optimizer_restored=True,checkpoint_rng_CPU_test=True,new_files_bytes=size,official_weights_unchanged=True,no_real_training_data=True,artifact_SHA256={str(x.relative_to(ROOT)):sha(x) for x in sorted(artifacts)})
 with (G/'delivery_audit.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k!='artifact_SHA256'},indent=2))
if __name__=='__main__':main()
