"""Independent weighted-sum evaluation and immutable-asset/resource audit."""
import sys,json,csv
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_fourcastden_multistep import sha,dump
from run_fourcastden_twelve_hour_mar24 import F,D,RAW,DATES,MODELS,verify
from fourcastden.validation import NAMES,LENGTHS,SI_FACTORS
from fourcastden.autoregression import check_autoregression
TAG='fourcastden_twelve_hour_mar24_v1'
def main(final=False):
 pre=verify();rt=json.loads((F/'runtime.json').read_text());sup=json.loads((F/'supervision.json').read_text());a=json.loads((F/'analysis.json').read_text());assert rt['status']==sup['status']==a['status']=='PASS';assert rt['formal_sequences']==4 and rt['formal_forwards']==48 and rt['precheck_forwards']==0 and len(rt['records'])==4
 assert sum(r['formal_forwards'] for r in rt['records'])==48 and len(list(F.glob('2023-*_launch.json')))==4
 assert sup['wall_s']<600 and sup['peak_RSS_bytes']<4*2**30
 from ruamel.yaml import YAML
 yaml=YAML(typ='safe')
 oldF=ROOT/'experiments/fourcastden_six_hour_v1'
 for model in MODELS:
  newcfg=yaml.load((F/f'{model}.yaml').read_text())['afno_inference'];oldcfg=yaml.load((oldF/f'{model}.yaml').read_text())['afno_inference']
  assert {k:v for k,v in newcfg.items() if k not in ['n_prediction','test_data_path','pre_resultname']}=={k:v for k,v in oldcfg.items() if k not in ['n_prediction','test_data_path','pre_resultname']}
  assert newcfg['n_prediction']==12 and oldcfg['n_prediction']==6
  gate=json.loads((F/f'2023-03-24_{model}_prefix_gate.json').read_text());assert gate['status']=='PASS' and gate['max_normalized_difference']==0
 if final:assert json.loads((F/'prefix_metrics_gate.json').read_text())['status']=='PASS'

 tests=(ROOT/'logs/fourcastden_twelve_hour_mar24_tests.log').read_text();assert 'Ran 239 tests' in tests and tests.rstrip().endswith('OK')
 dl=json.loads((F/'download.json').read_text());assert len(dl['records'])==6
 attempts=[json.loads((F/'ranges.json').read_text())]
 if (F/'ranges_resume.json').exists():attempts.append(json.loads((F/'ranges_resume.json').read_text()))
 assert sum(r['reserved_bytes'] for r in attempts)<25*2**20 and sum(r['transfer_bytes'] for r in attempts)==dl.get('network_body_bytes',attempts[0]['transfer_bytes'])
 failures=0
 for j,ranges in enumerate(attempts):
  for i,r in enumerate(ranges['requests']):
   if r.get('status')!=206:
    assert j==0 and i==len(ranges['requests'])-1 and r['body_bytes_read']==0 and 'HTTP Error 500' in (ROOT/'logs/fourcastden_twelve_hour_mar24_fetch.log').read_text();failures+=1;continue
   assert r['Content-Range']==f"bytes {r['start']}-{r['end']}/{18149758909}" and r['body_bytes_read']==r['requested_bytes']
 rows=list(csv.DictReader((ROOT/f'results/metrics/{TAG}_layers.csv').open()));w=np.broadcast_to(np.cos(np.deg2rad(np.load(ROOT/'data/processed/static/lat.npy')))[:,None],(36,72));factors=np.repeat(SI_FACTORS,LENGTHS);checked=0;native_max=0.;accmax=0.;persistence=[]
 for day in DATES:
  raw=[];zg=[]
  for h in range(14):
   with np.load(F/'data_view'/f"{day.replace('-','_')}_{h:02d}0000.npz") as z:raw.append(np.concatenate([z[k] for k in NAMES]).astype(float));zg.append(z['ZG'].astype(float)*.01)
  with np.load(D/f'{day}_Direct.npz') as z:clim=z['climatology'].astype(float)
  for m in MODELS:
   path=D/f'{day}_{m}.npz';assert sha(path)==next(r['result_sha256'] for r in rt['records'] if r['date']==day and r['model']==m)
   with np.load(path) as q:
    p=q['pred'][0].astype(float)*q['stds'][:171].astype(float)+q['means'][:171].astype(float)
    if m=='LogDEN':p[:,142:]=10.**p[:,142:]
    assert np.isfinite(p).all() and (p[:,142:]>0).all() and (p[:,:28]>0).all()
    hist=int(m=='History');real=q['full_data'][hist:];ins=[(q['inputs'][k:k+1],q['scalars'][k:k+1]) for k in range(12)];out=[q['pred'][0,k+1:k+2] for k in range(12)];rawout=[q['raw_network'][k:k+1] for k in range(12)];check_autoregression(ins,out,q['full_data'],q['full_sw'],hist,rawout,m=='Flow')
    for h in range(1,13):
     err=p[h]-raw[h+1];r=np.sqrt(np.sum(w*err**2,axis=(1,2))/w.sum());pa=p[h]-clim;ra=raw[h+1]-clim;den=np.sqrt(np.sum(w*pa**2,axis=(1,2))*np.sum(w*ra**2,axis=(1,2)));valid=den>0;acc=np.full(171,np.nan);acc[valid]=np.sum(w*pa*ra,axis=(1,2))[valid]/den[valid]
     rr=[x for x in rows if x['date']==day and x['model']==m and int(x['hour'])==h];assert len(rr)==171;np.testing.assert_allclose([float(x['RMSE_SI']) for x in rr],r*factors,rtol=1e-12,atol=1e-25);np.testing.assert_allclose([float(x['physical_ACC']) for x in rr if x['ACC_valid']=='True'],acc[valid],rtol=1e-12,atol=1e-12);checked+=171
     pe=np.sqrt(np.sum(w*(raw[1]-raw[h+1])**2,axis=(1,2))/w.sum());persistence.append(dict(date=day,model=m,hour=h,channels_better_than_persistence=int((r<pe).sum())))
     med=np.median(zg[h+1],axis=(1,2))/1000;near=np.flatnonzero((med>=400)&(med<=500));rel=p[h,142:]/raw[h+1][142:]-1;ln=np.log(p[h,142:]/raw[h+1][142:]);relrms=np.sqrt(np.sum(w*rel**2,axis=(1,2))/w.sum());lrms=np.sqrt(np.sum(w*ln**2,axis=(1,2))/w.sum());win=next(x for x in a['windows'] if x['date']==day and x['model']==m and x['hour']==h);np.testing.assert_allclose(win['near400_500_mean_relative_RMS'],relrms[near].mean(),rtol=1e-12);np.testing.assert_allclose(win['near400_500_mean_log_RMS'],lrms[near].mean(),rtol=1e-12)
     norm=q['pred'][0,h].astype(float);tar=real[h,:171].astype(float);nc=(q['climatology']-q['means'][:171])/q['stds'][:171];nr=np.sqrt(np.sum(w*(norm-tar)**2,axis=(1,2))/w.sum());na=np.sum(w*(norm-nc)*(tar-nc),axis=(1,2))/np.sqrt(np.sum(w*(norm-nc)**2,axis=(1,2))*np.sum(w*(tar-nc)**2,axis=(1,2)));np.testing.assert_allclose(nr,q['author_normalized_rmse'][h-1],rtol=2e-5,atol=1e-25);np.testing.assert_allclose(na,q['author_acc'][0,h-1],rtol=2e-5,atol=2e-6);native_max=max(native_max,float(np.max(abs(nr-q['author_normalized_rmse'][h-1])/nr)));accmax=max(accmax,float(np.max(abs(na-q['author_acc'][0,h-1]))))
     if m=='LogDEN':dr=np.sqrt(np.sum(w*(q['author_physical_den_pred'][h-1].astype(float)-q['author_physical_den_target'][h-1].astype(float))**2,axis=(1,2))/w.sum());np.testing.assert_allclose(dr,q['author_rmse'][0,h-1,142:],rtol=2e-5,atol=1e-25)
     else:np.testing.assert_allclose(nr*q['stds'][:171,0,0],q['author_rmse'][0,h-1],rtol=2e-5,atol=1e-25)
 counts=dict(layers=10260,summary=360,density_layers=5220,windows=60,author_native=8208,growth=24,performance=4,drivers=14)
 for name,n in counts.items():assert len(list(csv.DictReader((ROOT/f'results/metrics/{TAG}_{name}.csv').open())))==n,(name,n)
 assert all(r['exact'] and r['first_six_predictions_max_normalized_difference']==0 for r in a['historical_Mar24_prefix'])
 files=set(p for folder in [F,D,RAW] for p in folder.rglob('*') if p.is_file() and not p.is_symlink())
 for folder,pattern in [('logs','fourcastden_twelve_hour_mar24*'),('results/metrics',TAG+'*'),('results/figures',TAG+'*')]:files.update(p for p in (ROOT/folder).glob(pattern) if p.is_file())
 files={p for p in files if p.name not in ['delivery_audit.json','final_delivery_audit.json'] and not p.name.endswith('_audit.log')}
 if final:
  for name in ['reports/FOURCASTDEN_TWELVE_HOUR_MAR24_VALIDATION.md','reports/FOURCASTDEN_TWELVE_HOUR_TWO_WINDOW_COMPARISON.md','docs/FOURCASTDEN_TRAINING_IMPLEMENTATION_PLAN.md','docs/FOURCASTDEN_MAR24_TWELVE_HOUR_PREREGISTRATION.md','docs/FOURCASTDEN_LONG_HORIZON_DECISION.md','docs/FOURCASTDEN_PHASE2_RESEARCH_PLAN.md','STATUS.md','WORKLOG.md','AGENTS.md','.gitignore','tests/test_fourcastden_twelve_hour_mar24.py']:files.add(ROOT/name)
  files.update((ROOT/'scripts').glob('*fourcastden_twelve_hour_mar24*.py'))
 size=sum(p.stat().st_size for p in files);assert size+2**20<800*2**20 and all(p.resolve().is_relative_to(ROOT) for p in files)
 result=dict(status='PASS',protected_files_unchanged=len(json.loads((F/'protected.json').read_text())),formal_sequences=4,formal_forwards=48,short_check_forwards=0,tests=239,common_physical_channel_checks=checked,author_normalized_RMSE_max_relative=native_max,author_ACC_max_absolute=accmax,DEN_positive_fraction=1.,all_steps_feedback_exact=True,history_third_step_onward_two_predictions=True,March_first_six_steps_exact_to_history=True,network_body_bytes=sum(x['transfer_bytes'] for x in attempts),network_reserved_bytes=sum(x['reserved_bytes'] for x in attempts),HTTP500_count=failures,download_attempts=len(attempts),new_files_bytes=size,wall_s=sup['wall_s'],peak_RSS_bytes=sup['peak_RSS_bytes'],CSV_rows=counts,persistence_checks=persistence,artifact_sha256={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)})
 dump(F/('final_delivery_audit.json' if final else 'delivery_audit.json'),result);print(json.dumps({k:v for k,v in result.items() if k not in ['artifact_sha256','persistence_checks']},indent=2))
if __name__=='__main__':main('--final' in sys.argv)
