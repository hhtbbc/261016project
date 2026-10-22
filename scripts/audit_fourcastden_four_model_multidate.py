"""Independent physical/native metrics, feedback, SHA and resource audit."""
import sys,json,csv
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_fourcastden_multistep import sha,dump
from run_fourcastden_four_model_multidate import F,D,RAW,JAN,MODELS,verify
from analyze_fourcastden_four_model_multidate import source,rawpath,TAG
from fourcastden.four_model_windows import ALL_DATES
from fourcastden.validation import feedback_check,NAMES,LENGTHS,SI_FACTORS
from fourcastden.history import history_feedback_check

def main(final=False):
 pre=verify();rt=json.loads((F/'runtime.json').read_text());sup=json.loads((F/'supervision.json').read_text());a=json.loads((F/'analysis.json').read_text());assert rt['status']==sup['status']==a['status']=='PASS'
 assert rt['formal_sequences']==16 and rt['formal_forwards']==32 and rt['precheck_forwards']==0 and not rt['January_rerun']
 assert len(rt['records'])==16 and len(list(F.glob('*_launch.json')))==16
 assert sup['wall_s']<600 and sup['peak_RSS_bytes']<4*2**30
 test=(ROOT/'logs/fourcastden_four_model_tests.log').read_text();assert 'Ran 226 tests' in test and test.rstrip().endswith('OK')
 ranges=json.loads((F/'ranges.json').read_text());download=json.loads((F/'download.json').read_text());assert len(download['records'])==4 and ranges['transfer_bytes']<ranges['reserved_bytes']<20*2**20
 assert all(r['status']==206 and r['Content-Range']==f"bytes {r['start']}-{r['end']}/{download['archive_bytes']}" and r['body_bytes_read']==r['requested_bytes'] for r in ranges['requests'])
 rows=list(csv.DictReader((ROOT/f'results/metrics/{TAG}_layers.csv').open()));w=np.broadcast_to(np.cos(np.deg2rad(np.load(ROOT/'data/processed/static/lat.npy')))[:,None],(36,72));factor=np.repeat(SI_FACTORS,LENGTHS);checked=0;native_max=0.;accmax=0.;persist_better={}
 for day in ALL_DATES:
  raw=[];heights=[]
  for h in range(4):
   with np.load(rawpath(day,h)) as z:raw.append(np.concatenate([z[k] for k in NAMES]).astype(float));heights.append(z['ZG'].astype(float)*.01)
  with np.load(source(day,'Direct')) as q:clim=q['climatology'].astype(float)
  for m in MODELS:
   with np.load(source(day,m)) as q:
    p=q['pred'][0].astype(float)*q['stds'][:171].astype(float)+q['means'][:171].astype(float)
    if m=='LogDEN':p[:,142:]=10.**p[:,142:]
    assert np.isfinite(p).all() and (p[:,142:]>0).all() and (p[:,:28]>0).all()
    inputs=[(q[f'input{k}'],q[f'scalars{k}']) for k in range(2)];out=[q[f'out{k}'] for k in range(2)]
    if m=='History':history_feedback_check(inputs,out,q['full_data'],q['full_sw'])
    else:feedback_check(inputs,out,q['real'][0],q['full_sw'])
    for k in range(2):np.testing.assert_array_equal(out[k][0],q['pred'][0,k+1])
    for h in (1,2):
     err=p[h]-raw[h+1];r=np.sqrt(np.sum(w*err**2,axis=(1,2))/w.sum());pa=p[h]-clim;ta=raw[h+1]-clim;acc=np.sum(w*pa*ta,axis=(1,2))/np.sqrt(np.sum(w*pa**2,axis=(1,2))*np.sum(w*ta**2,axis=(1,2)))
     rr=[x for x in rows if x['date']==day and x['model']==m and int(x['hour'])==h];assert len(rr)==171
     np.testing.assert_allclose([float(x['RMSE_SI']) for x in rr],r*factor,rtol=1e-12,atol=1e-25);np.testing.assert_allclose([float(x['physical_ACC']) for x in rr],acc,rtol=1e-12,atol=1e-12);checked+=171
     persist=np.sqrt(np.sum(w*(raw[1]-raw[h+1])**2,axis=(1,2))/w.sum());persist_better[f'{day}_{m}_{h}']=int((r<persist).sum())
     med=np.median(heights[h+1],axis=(1,2))/1000;near=np.flatnonzero((med>=400)&(med<=500));rel=p[h,142:]/raw[h+1][142:]-1;ln=np.log(p[h,142:]/raw[h+1][142:]);relrms=np.sqrt(np.sum(w*rel**2,axis=(1,2))/w.sum());lrms=np.sqrt(np.sum(w*ln**2,axis=(1,2))/w.sum());wr=next(x for x in a['windows'] if x['date']==day and x['model']==m and x['hour']==h)
     np.testing.assert_allclose(wr['near400_500_mean_relative_RMS'],relrms[near].mean(),rtol=1e-12);np.testing.assert_allclose(wr['near400_500_mean_log_RMS'],lrms[near].mean(),rtol=1e-12)
     norm=q['pred'][0,h].astype(float);tar=q['real'][0,h,:171].astype(float);nc=(q['climatology']-q['means'][:171])/q['stds'][:171];nr=np.sqrt(np.sum(w*(norm-tar)**2,axis=(1,2))/w.sum());na=np.sum(w*(norm-nc)*(tar-nc),axis=(1,2))/np.sqrt(np.sum(w*(norm-nc)**2,axis=(1,2))*np.sum(w*(tar-nc)**2,axis=(1,2)))
     np.testing.assert_allclose(nr,q['author_normalized_rmse'][h-1],rtol=2e-5,atol=1e-25);np.testing.assert_allclose(na,q['author_acc'][0,h-1],rtol=2e-5,atol=2e-6);native_max=max(native_max,float(np.max(abs(nr-q['author_normalized_rmse'][h-1])/nr)));accmax=max(accmax,float(np.max(abs(na-q['author_acc'][0,h-1]))))
     if m=='LogDEN':dr=np.sqrt(np.sum(w*(q['author_physical_den_pred'][h-1].astype(float)-q['author_physical_den_target'][h-1].astype(float))**2,axis=(1,2))/w.sum());np.testing.assert_allclose(dr,q['author_rmse'][0,h-1,142:],rtol=2e-5,atol=1e-25)
     else:np.testing.assert_allclose(nr*q['stds'][:171,0,0],q['author_rmse'][0,h-1],rtol=2e-5,atol=1e-25)
 counts=dict(layers=8550,summary=300,density_layers=4350,windows=50,author_native=6840,aggregate=48,density_aggregate=40,pairs=360,density_pairs=300,growth=120,rankings=50,initialization=360,performance=20,drivers=20,reference_changes=90)
 for name,n in counts.items():assert len(list(csv.DictReader((ROOT/f'results/metrics/{TAG}_{name}.csv').open())))==n,(name,n)
 for row in a['aggregate']:
  vals=[r['mean_layer_RMSE_SI'] for r in a['summary'] if r['model']==row['model'] and r['hour']==row['hour'] and r['variable']==row['variable']];np.testing.assert_allclose([row[k] for k in ['mean','median','minimum','maximum']],[np.mean(vals),np.median(vals),min(vals),max(vals)],rtol=1e-12)
 files=set(p for folder in [F,D,RAW] for p in folder.rglob('*') if p.is_file() and not p.is_symlink())
 for folder,pattern in [('logs','fourcastden_four_model*'),('results/metrics',TAG+'*'),('results/figures',TAG+'*')]:files.update(p for p in (ROOT/folder).glob(pattern) if p.is_file())
 files={p for p in files if p.name not in ['delivery_audit.json','final_delivery_audit.json'] and not p.name.endswith('_audit.log')}
 if final:
  for name in ['reports/FOURCASTDEN_FOUR_MODEL_MULTIDATE_VALIDATION.md','reports/FOURCASTDEN_FOUR_MODEL_MULTIDATE_COMPARISON.md','docs/FOURCASTDEN_SIX_HOUR_EXPERIMENT_PLAN.md','docs/FOURCASTDEN_FOUR_MODEL_MULTIDATE_PREREGISTRATION.md','docs/FOURCASTDEN_PHASE2_RESEARCH_PLAN.md','docs/FOURCASTDEN_NEXT_EXPERIMENT_DECISION.md','STATUS.md','WORKLOG.md','AGENTS.md','.gitignore','src/fourcastden/four_model_windows.py','tests/test_fourcastden_four_model_multidate.py']:files.add(ROOT/name)
  files.update((ROOT/'scripts').glob('*fourcastden_four_model*.py'))
 size=sum(p.stat().st_size for p in files);assert size+2**20<650*2**20 and all(p.resolve().is_relative_to(ROOT) for p in files)
 result=dict(status='PASS',protected_files_unchanged=len(json.loads((F/'protected.json').read_text())),new_sequences=16,new_forwards=32,January_rerun=False,tests=226,common_physical_channel_checks=checked,author_normalized_RMSE_max_relative=native_max,author_ACC_max_absolute=accmax,DEN_positive_fraction=1.,all_feedback_exact=True,network_body_bytes=ranges['transfer_bytes'],new_files_bytes=size,wall_s=sup['wall_s'],peak_RSS_bytes=sup['peak_RSS_bytes'],CSV_rows=counts,channels_better_than_persistence=persist_better,artifact_sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)})
 dump(F/('final_delivery_audit.json' if final else 'delivery_audit.json'),result);print(json.dumps({k:v for k,v in result.items() if k not in ['artifact_sha256','channels_better_than_persistence']},indent=2))
if __name__=='__main__':main('--final' in sys.argv)
