"""Independent sum-weighted metrics / bytes / SHA audit, never a forward."""
import sys,json,csv
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_fourcastden_multistep import sha,dump
from run_fourcastden_history_comparison import F,D,RAW,MODELS,verify
from fourcastden.history import history_feedback_check
from fourcastden.validation import feedback_check,NAMES,LENGTHS,SI_FACTORS

def main(final=False,release=False):
 pre=verify();rt=json.loads((F/'runtime.json').read_text());a=json.loads((F/'analysis.json').read_text());sup=json.loads((F/'supervision.json').read_text());assert rt['status']==a['status']==sup['status']=='PASS'
 assert rt['formal_forwards']==8 and rt['precheck_forwards']==1 and len(rt['records'])==4
 assert sup['wall_s']<600 and sup['peak_RSS_bytes']<4*2**30
 assert 'Ran 221 tests' in (ROOT/'logs/fourcastden_history_tests.log').read_text() and (ROOT/'logs/fourcastden_history_tests.log').read_text().rstrip().endswith('OK')
 ranges=json.loads((F/'ranges.json').read_text());assert ranges['transfer_bytes']<=ranges['reserved_bytes']<10*2**20
 assert all(r['status']==206 and r['Content-Range']==f"bytes {r['start']}-{r['end']}/18149758909" for r in ranges['requests'])
 rows=list(csv.DictReader((ROOT/'results/metrics/fourcastden_history_v1_layers.csv').open()));raw=[];zg=[]
 for h in range(4):
  with np.load(F/'data_view'/f'2023_01_04_{h:02d}0000.npz') as z:raw.append(np.concatenate([z[k] for k in NAMES],axis=0).astype(float));zg.append(z['ZG'].astype(float)*.01)
 w=np.broadcast_to(np.cos(np.deg2rad(np.load(ROOT/'data/processed/static/lat.npy')))[:,None],(36,72));factors=np.repeat(SI_FACTORS,LENGTHS)
 with np.load(D/'Direct.npz') as q:clim=q['climatology'].astype(float)
 checked=0;nativecheck=[]
 for m in MODELS:
  with np.load(D/f'{m}.npz') as q:
   assert sha(D/f'{m}.npz')==next(r['result_sha256'] for r in rt['records'] if r['model']==m)
   pred=q['pred'][0].astype(float)*q['stds'][:171].astype(float)+q['means'][:171].astype(float)
   if m=='LogDEN':pred[:,142:]=10.**pred[:,142:]
   assert np.isfinite(pred).all() and (pred[:,142:]>0).all() and (pred[:,:28]>0).all()
   inputs=[(q[f'input{k}'],q[f'scalars{k}']) for k in range(2)];out=[q[f'out{k}'] for k in range(2)]
   if m=='History':history_feedback_check(inputs,out,q['full_data'],q['full_sw'])
   else:feedback_check(inputs,out,q['real'][0],q['full_sw'])
   for k in range(2):np.testing.assert_array_equal(out[k][0],q['pred'][0,k+1])
   for h in (1,2):
    target=raw[h+1];err=pred[h]-target;rmse=np.sqrt(np.sum(w*err**2,axis=(1,2))/w.sum());pa=pred[h]-clim;ra=target-clim;acc=np.sum(w*pa*ra,axis=(1,2))/np.sqrt(np.sum(w*pa**2,axis=(1,2))*np.sum(w*ra**2,axis=(1,2)))
    rr=[r for r in rows if r['model']==m and int(r['hour'])==h];assert len(rr)==171
    np.testing.assert_allclose([float(r['RMSE_SI']) for r in rr],rmse*factors,rtol=1e-12,atol=1e-25);np.testing.assert_allclose([float(r['physical_ACC']) for r in rr],acc,rtol=1e-12,atol=1e-12);checked+=171
    med=np.median(zg[h+1],axis=(1,2))/1000;near=np.flatnonzero((med>=400)&(med<=500));rel=pred[h,142:]/target[142:]-1;logs=np.log(pred[h,142:]/target[142:]);relrms=np.sqrt(np.sum(w*rel**2,axis=(1,2))/w.sum());logrms=np.sqrt(np.sum(w*logs**2,axis=(1,2))/w.sum());win=next(r for r in a['windows'] if r['model']==m and r['hour']==h)
    np.testing.assert_allclose(win['near400_500_mean_relative_RMS'],relrms[near].mean(),rtol=1e-12);np.testing.assert_allclose(win['near400_500_mean_log_RMS'],logrms[near].mean(),rtol=1e-12)
    p=q['pred'][0,h].astype(float);t=q['real'][0,h,:171].astype(float);cl=(q['climatology']-q['means'][:171])/q['stds'][:171];nr=np.sqrt(np.sum(w*(p-t)**2,axis=(1,2))/w.sum());na=np.sum(w*(p-cl)*(t-cl),axis=(1,2))/np.sqrt(np.sum(w*(p-cl)**2,axis=(1,2))*np.sum(w*(t-cl)**2,axis=(1,2)))
    np.testing.assert_allclose(nr,q['author_normalized_rmse'][h-1],rtol=2e-5,atol=1e-25);np.testing.assert_allclose(na,q['author_acc'][0,h-1],rtol=2e-5,atol=2e-6)
    if m=='LogDEN':
     dr=np.sqrt(np.sum(w*(q['author_physical_den_pred'][h-1].astype(float)-q['author_physical_den_target'][h-1].astype(float))**2,axis=(1,2))/w.sum());np.testing.assert_allclose(dr,q['author_rmse'][0,h-1,142:],rtol=2e-5,atol=1e-25)
    else:np.testing.assert_allclose(nr*q['stds'][:171,0,0],q['author_rmse'][0,h-1],rtol=2e-5,atol=1e-25)
    nativecheck.append(dict(model=m,hour=h,normalized_RMSE_max_relative=float(np.max(abs(nr-q['author_normalized_rmse'][h-1])/nr)),ACC_max_absolute=float(np.max(abs(na-q['author_acc'][0,h-1])))))
 counts=dict(layers=1710,summary=60,density_layers=870,windows=10,growth=24,performance=4,drivers=4)
 for name,n in counts.items():assert len(list(csv.DictReader((ROOT/f'results/metrics/fourcastden_history_v1_{name}.csv').open())))==n
 files=set()
 for folder in [F,D,RAW]:files.update(p for p in folder.rglob('*') if p.is_file() and not p.is_symlink())
 for folder,pattern in [('logs','fourcastden_history*'),('results/metrics','fourcastden_history_v1*'),('results/figures','fourcastden_history_v1*')]:files.update(p for p in (ROOT/folder).glob(pattern) if p.is_file())
 files={p for p in files if p.name not in ['delivery_audit.json','fourcastden_history_audit.log','fourcastden_history_release_audit.log','fourcastden_history_publication_audit.log']};size=sum(p.stat().st_size for p in files);assert size+2**20<150*2**20

 if final:
  assert len(list(csv.DictReader((ROOT/'results/metrics/fourcastden_history_v1_author_native.csv').open())))==1368
  counts['author_native']=1368
  for p in [ROOT/'reports/FOURCASTDEN_HISTORY_VALIDATION.md',ROOT/'reports/FOURCASTDEN_FOUR_MODEL_COMPARISON.md',ROOT/'docs/FOURCASTDEN_NEXT_EXPERIMENT_DECISION.md',ROOT/'docs/FOURCASTDEN_PHASE2_RESEARCH_PLAN.md',ROOT/'STATUS.md',ROOT/'WORKLOG.md',ROOT/'AGENTS.md',ROOT/'.gitignore',ROOT/'docs/FOURCASTDEN_HISTORY_PREREGISTRATION.md']:
   assert p.exists();files.add(p)
  for pattern in ['*fourcastden_history*.py']:
   files.update((ROOT/'scripts').glob(pattern))
  files.update([ROOT/'src/fourcastden/history.py',ROOT/'tests/test_fourcastden_history.py'])
  size=sum(p.stat().st_size for p in files);assert size+2**20<150*2**20
 out=dict(status='PASS',protected_files_unchanged=len(json.loads((F/'protected.json').read_text())),formal_sequences=4,formal_forwards=8,History_precheck_forwards=1,tests=221,independent_common_channel_checks=checked,native_checks=nativecheck,all_feedback_exact=True,DEN_positive_fraction=1.,new_downloaded_member='2023_01_04_030000.npz',network_body_bytes=ranges['transfer_bytes'],new_files_bytes=size,source_code_docs_allowance_bytes=2**20,budget_bytes=150*2**20,wall_s=sup['wall_s'],peak_RSS_bytes=sup['peak_RSS_bytes'],CSV_rows=counts,artifact_sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)})
 dump(F/('publication_audit.json' if '--publication' in sys.argv else 'release_audit.json' if release else 'final_delivery_audit.json' if final else 'delivery_audit.json'),out);print(json.dumps({k:v for k,v in out.items() if k!='artifact_sha256'},indent=2))
if __name__=='__main__':main('--final' in sys.argv or '--release' in sys.argv or '--publication' in sys.argv,'--release' in sys.argv)
