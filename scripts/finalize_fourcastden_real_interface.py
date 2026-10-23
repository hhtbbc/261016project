"""Immutable historical assets and read-only real-data delivery audit."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'experiments/fourcastden_real_interface_v2';OLD=ROOT/'experiments/fourcastden_real_interface_v1'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def main():
 protected=json.loads((F/'protected.json').read_text());allowed={'docs/FOURCASTDEN_TRAINING_IMPLEMENTATION_PLAN.md'};changes=[];checked=0
 for n,h in protected.items():
  actual=sha(ROOT/n)
  if n in allowed:
   changes.append(dict(path=n,before_SHA256=h,after_SHA256=actual,reason='User explicitly requested training implementation documentation update'))
  else:assert actual==h,n;checked+=1
 a=json.loads((F/'interface_audit.json').read_text());assert a['status']=='PASS' and len(a['samples'])==3 and len(a['pairs'])==2 and len(a['roundtrip'])==27
 assert all(r['exact'] and r['max_input_abs_difference']==r['max_scalar_abs_difference']==r['max_target_abs_difference']==0 for r in a['pairs'])
 assert a['training_2023_rejected'] and not a['normalization_fitted'] and not a['CUDA_used'] and a['model_forward_calls']==a['backward_calls']==a['optimizer_steps']==0
 assert all(r['official_input_unchanged'] and r['adapter_input_unchanged'] and r['target_changed'] for r in a['poison'])
 for r in a['samples']:assert sha(ROOT/'data/raw/test_minimal_2023'/r['name'])==r['SHA256']
 tests=(ROOT/'logs/fourcastden_real_interface_tests_v2.log').read_text();assert 'Ran 11 tests' in tests and tests.rstrip().endswith('OK')
 with np.load(ROOT/'data/processed/static/mag.npz') as z:years=z['years'].tolist()
 files=set()
 for folder in [F,OLD]:files.update(p for p in folder.rglob('*') if p.is_file() and not p.is_symlink())
 for folder,pattern in [('src/training','readonly_interface.py'),('scripts','*fourcastden_real*interface*.py'),('scripts','finalize_fourcastden_real_interface.py'),('tests','test_fourcastden_real_data_interface.py'),('logs','fourcastden_real_interface*.log'),('results/metrics','fourcastden_real_interface*')]:files.update((ROOT/folder).glob(pattern))
 for n in ['docs/FOURCASTDEN_AUTHOR_RESOURCE_REQUEST.md','docs/FOURCASTDEN_ALTERNATIVE_TRAINING_DATA_PLAN.md','docs/FOURCASTDEN_REAL_TRAINING_READINESS.md','docs/FOURCASTDEN_TRAINING_IMPLEMENTATION_PLAN.md','docs/FOURCASTDEN_PHASE2_RESEARCH_PLAN.md','reports/FOURCASTDEN_REAL_DATA_INTERFACE_AUDIT.md','STATUS.md','WORKLOG.md','AGENTS.md','.gitignore']:files.add(ROOT/n)
 files={p for p in files if p.name!='delivery_audit.json' and not p.name.endswith('_audit.log')}
 assert all(p.resolve().is_relative_to(ROOT) for p in files);size=sum(p.stat().st_size for p in files);assert size<200*2**20
 result=dict(status='PASS',label=a['label'],protected_immutable_files=checked,authorized_document_updates=changes,real_samples=3,consecutive_pairs=2,input_channels=177,target_channels=171,external_scalars=4,all_inputs_targets_scalars_exact=True,tests_executed=11,prior_full_suite_247_not_rerun=True,model_forwards=0,backward_calls=0,optimizer_steps=0,CUDA_used=False,training_2023_guard_intact=True,official_email_sent=False,official_contact_email_verified=False,official_followup_new_training_resources_found=False,static_magnetic_years=years,new_files_bytes=size,artifact_SHA256={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)})
 with (F/'delivery_audit.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k not in ['artifact_SHA256','static_magnetic_years']},indent=2));print('static magnetic coverage',years[0],years[-1])
if __name__=='__main__':main()
