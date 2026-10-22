"""Independent post-run audit of native and common physical metrics; no forward."""
import sys,json,csv
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_fourcastden_multistep import sha,dump
from analyze_fourcastden_three_models import load,ALL,MODELS
from fourcastden.validation import feedback_check,LENGTHS,SI_FACTORS
F=ROOT/'experiments/fourcastden_logden_multidate_v1';D=ROOT/'data/processed/fourcastden_logden_multidate_v1'
def main():
 pre=json.loads((F/'preflight.json').read_text());protected=json.loads((F/'protected.json').read_text());rt=json.loads((F/'runtime.json').read_text());sup=json.loads((F/'supervision.json').read_text());c=json.loads((F/'compatibility.json').read_text());a=json.loads((F/'analysis.json').read_text())
 for p,h in protected.items():assert (ROOT/p).resolve().is_relative_to(ROOT) and sha(ROOT/p)==h,p
 for p,h in pre['code_sha256'].items():assert sha(ROOT/p)==h,p
 assert sha(F/'config.yaml')==pre['config_sha256'];assert sha(F/'inference_overlay.py')==c['overlay_SHA256']
 for e in pre['data']:assert (F/'data_view'/e['name']).resolve()==(ROOT/e['source']).resolve() and sha(ROOT/e['source'])==e['sha256']
 assert rt['status']==sup['status']==a['status']=='PASS' and len(rt['records'])==5 and sum(r['network_calls'] for r in rt['records'])==10 and not rt['Direct_Flow_rerun']
 assert sup['wall_s']+sup['compatibility_wall_s']<600 and sup['peak_RSS_bytes']<4*2**30
 testlog=(ROOT/'logs/fourcastden_logden_tests.log').read_text();assert 'Ran 215 tests' in testlog and testlog.rstrip().endswith('OK')
 lat=np.load(ROOT/'data/processed/static/lat.npy');w=np.broadcast_to(np.cos(np.deg2rad(lat))[:,None],(36,72));factors=np.repeat(SI_FACTORS,LENGTHS)
 rows=list(csv.DictReader((ROOT/'results/metrics/fourcastden_three_model_v1_layers.csv').open()));checked=0;native_den_max=0.;native_acc_max=0.
 for day in ALL:
  rawdir=ROOT/('data/raw/test_minimal_2023' if day==ALL[0] else 'data/raw/fourcastden_multidate_v1');raw=[]
  for h in range(3):
   with np.load(rawdir/f"{day.replace('-','_')}_{h:02d}0000.npz") as z:raw.append(np.concatenate([z[k] for k in ['TN','UN','VN','WN','Z','DEN']],axis=0).astype(float))
  truth=np.stack(raw);direct=load(day,'Direct');clim=direct['climatology'].astype(float)
  for model in MODELS:
   q=load(day,model);assert (q['stds']>0).all()
   pred=q['pred'][0].astype(float)*q['stds'][:171].astype(float)+q['means'][:171].astype(float)
   if model=='LogDEN':pred[:,142:]=10.**pred[:,142:]
   assert np.isfinite(pred).all() and (pred[:,142:]>0).all() and (pred[:,:28]>0).all()
   if model=='LogDEN':
    feedback_check([(q['input0'],q['scalars0']),(q['input1'],q['scalars1'])],[q['out0'],q['out1']],q['real'][0],np.vstack([np.zeros(4),q['scalars0'].reshape(4),q['scalars1'].reshape(4)]))
    for k in range(2):np.testing.assert_array_equal(q[f'out{k}'][0],q['pred'][0,k+1]);np.testing.assert_array_equal(q[f'scalars{k}'],direct[f'scalars{k}'])
   for h in (1,2):
    err=pred[h]-truth[h];rmse=np.sqrt(np.sum(w*err**2,axis=(1,2))/w.sum());p=pred[h]-clim;r=truth[h]-clim;den=np.sqrt(np.sum(w*p**2,axis=(1,2))*np.sum(w*r**2,axis=(1,2)));valid=den>0;acc=np.full(171,np.nan);acc[valid]=np.sum(w*p*r,axis=(1,2))[valid]/den[valid]
    rr=[r for r in rows if r['date']==day and r['model']==model and int(r['hour'])==h];assert len(rr)==171
    np.testing.assert_allclose([float(r['RMSE_SI']) for r in rr],rmse*factors,rtol=1e-12,atol=1e-25)
    np.testing.assert_allclose([float(r['physical_ACC']) for r in rr],acc,rtol=1e-12,atol=1e-12)
    win=next(x for x in a['windows'] if x['date']==day and x['model']==model and x['hour']==h)
    with np.load(rawdir/f"{day.replace('-','_')}_{h:02d}0000.npz") as z:heights=np.median(z['ZG'].astype(float)*.01,axis=(1,2))/1000
    near=np.flatnonzero((heights>=400)&(heights<=500));rel=pred[h,142:]/truth[h,142:]-1;logs=np.log(pred[h,142:]/truth[h,142:]);relrms=np.sqrt(np.sum(w*rel**2,axis=(1,2))/w.sum());logrms=np.sqrt(np.sum(w*logs**2,axis=(1,2))/w.sum())
    np.testing.assert_allclose(win['near400_500_mean_relative_RMS'],relrms[near].mean(),rtol=1e-12,atol=1e-15);np.testing.assert_allclose(win['near400_500_mean_log_RMS'],logrms[near].mean(),rtol=1e-12,atol=1e-15)
    checked+=171
    if model=='LogDEN':
     norm=q['pred'][0,h];tar=q['real'][0,h,:171];m=(q['climatology']-q['means'][:171])/q['stds'][:171]
     nr=np.sqrt(np.sum(w*(norm.astype(float)-tar.astype(float))**2,axis=(1,2))/w.sum());np.testing.assert_allclose(nr,q['author_normalized_rmse'][h-1],rtol=2e-5,atol=1e-25)
     ap=norm.astype(float)-m;ar=tar.astype(float)-m;na=np.sum(w*ap*ar,axis=(1,2))/np.sqrt(np.sum(w*ap**2,axis=(1,2))*np.sum(w*ar**2,axis=(1,2)));np.testing.assert_allclose(na,q['author_acc'][0,h-1],rtol=2e-5,atol=2e-6)
     dp=q['author_physical_den_pred'][h-1].astype(float);dr=q['author_physical_den_target'][h-1].astype(float);er=np.sqrt(np.sum(w*(dp-dr)**2,axis=(1,2))/w.sum());np.testing.assert_allclose(er,q['author_rmse'][0,h-1,142:],rtol=2e-5,atol=1e-25)
     native_den_max=max(native_den_max,float(np.max(abs(er-q['author_rmse'][0,h-1,142:])/er)));native_acc_max=max(native_acc_max,float(np.max(abs(na-q['author_acc'][0,h-1]))))
  # Check descriptive report statements, not model-acceptance thresholds.
  win=lambda h,m:next(x for x in a['windows'] if x['date']==day and x['hour']==h and x['model']==m)
  assert win(2,'LogDEN')['mean_DEN_layer_RMSE_kg_m3']<min(win(2,m)['mean_DEN_layer_RMSE_kg_m3'] for m in ['Direct','Flow'])
  for h in (1,2):assert win(h,'Flow')['near400_500_mean_relative_RMS']<win(h,'Direct')['near400_500_mean_relative_RMS']<win(h,'LogDEN')['near400_500_mean_relative_RMS']
 counts=dict(layers=6840,summary=240,density_layers=3480,windows=40,author_native_logden=1710,paired=60,aggregate=12,performance=15)
 for name,count in counts.items():assert len(list(csv.DictReader((ROOT/f'results/metrics/fourcastden_three_model_v1_{name}.csv').open())))==count
 paths=set(F.rglob('*'))|set(D.rglob('*'))
 for sub,pattern in [('logs','fourcastden_logden*'),('results/metrics','fourcastden_three_model*'),('results/figures','fourcastden_three_model*')]:paths.update((ROOT/sub).glob(pattern))
 files=[p for p in paths if p.is_file() and p.name not in ['delivery_audit.json','fourcastden_logden_audit.log'] and '__pycache__' not in p.parts];assert all(p.resolve().is_relative_to(ROOT) for p in files)
 size=sum(p.stat().st_size for p in files);assert size+2**20<250*2**20
 out=dict(status='PASS',protected_files_unchanged=len(protected),formal_logden_sequences=5,real_forwards=10,Direct_Flow_rerun=False,new_raw_downloads=0,tests=215,common_physical_channel_metric_checks=checked,author_native_DEN_RMSE_max_relative=native_den_max,author_native_ACC_max_absolute=native_acc_max,all_predictions_finite=True,DEN_positive_fraction=1.,all_feedback_exact=True,report_claims_verified=True,supervised_plus_compatibility_wall_s=sup['wall_s']+sup['compatibility_wall_s'],peak_RSS_bytes=sup['peak_RSS_bytes'],new_experiment_bytes_conservative=size,includes_existing_raw_symlink_target_bytes=True,budget_bytes=250*2**20,CSV_rows=counts,artifact_SHA256={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)})
 dump(F/'delivery_audit.json',out);print(json.dumps({k:v for k,v in out.items() if k!='artifact_SHA256'},indent=2))
if __name__=='__main__':main()
