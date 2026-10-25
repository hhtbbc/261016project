"""Final read-only protection and complete input/output SHA ledger; no simulation."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];C=R/'experiments/tiegcm_2021_spinup_14day_v1';O=R/'results/tiegcm_2021_spinup_14day_v1'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
 return h.hexdigest()
def main():
 protected={}
 for group in ['A14','B14']:
  x=json.loads((C/group/'protected_files.json').read_text())
  for k,v in x.items():
   if k in protected:assert protected[k]==v,k
   protected[k]=v
 failures=[k for k,v in protected.items() if not (R/k).exists() or sha(R/k)!=v];assert not failures,failures
 outputs=[]
 for group in ['A14','B14']:
  a=json.loads((C/group/'data_audit.json').read_text());assert a['engineering_PASS']
  for x in a['files']:assert sha(C/group/x['file'])==x['SHA256'];outputs.append({'group':group,**x})
 files={}
 paths=list(C.rglob('*'))+list(O.rglob('*'))+list((R/'scripts').glob('*2021*14day*.py'))+list((R/'scripts').glob('*2021*7vs14*.py'))+list((R/'reports').glob('TIEGCM_2021_*14*.md'))+list((R/'reports').glob('TIEGCM_2021_COMPOSITION_POLAR_ANALYSIS.md'))+[R/'tests/test_tiegcm_2021_14day.py',R/'logs/tiegcm_2021_14day_tests.log']
 for p in paths:
  if p.is_file() and p.suffix not in ['.nc','.npz'] and p.name!='input.inp':files[str(p.relative_to(R))]={'SHA256':sha(p),'bytes':p.stat().st_size}
 result={'protected_files_verified':len(protected),'changed_protected_files':failures,'new_NetCDF_files_verified':len(outputs),'outputs':outputs,'files':files,'model_launches':2,'old_model_relaunches':0,'candidate_replacement_or_extraction':False,'training_or_scaler_fitting':False,'classification':'B','science_training_ready':False}
 (C/'delivery_audit.json').open('x').write(json.dumps(result,indent=2)+'\n');print('All protected files unchanged:',len(protected),'new source volumes verified:',len(outputs))
if __name__=='__main__':main()
