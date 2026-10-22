"""Independent saved-data audit; never constructs or runs a network."""
import sys,json,csv,zlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_fourcastden_multistep import sha,dump
from fourcastden.multidate import DATES,names_for,validate_npz
from fourcastden.validation import feedback_check,SI_FACTORS,LENGTHS
from fourcastden.flow_validation import flow_feedback_check
F=ROOT/'experiments/fourcastden_multidate_v1';D=ROOT/'data/processed/fourcastden_multidate_v1';RAW=ROOT/'data/raw/fourcastden_multidate_v1'
def main():
 protected=json.loads((F/'protected.json').read_text());pre=json.loads((F/'preflight.json').read_text());rt=json.loads((F/'runtime.json').read_text());sup=json.loads((F/'supervision.json').read_text());download=json.loads((F/'download.json').read_text());a=json.loads((F/'analysis.json').read_text())
 for p,h in protected.items():assert (ROOT/p).resolve().is_relative_to(ROOT) and sha(ROOT/p)==h,p
 for p,h in pre['code_sha256'].items():assert sha(ROOT/p)==h,p
 for m,h in pre['config_sha256'].items():assert sha(F/f'{m}.yaml')==h
 assert rt['status']==sup['status']==download['status']==a['status']=='PASS'
 assert len(rt['records'])==8 and sum(r['network_calls'] for r in rt['records'])==16
 assert not rt['January_replayed'] and rt['GPU_wall_s']<600 and sup['wall_s']<600 and sup['peak_tree_RSS_bytes']<4*2**30
 assert len(download['saved'])==12 and download['transfer_body_bytes']<100*2**20 and download['conservative_reserved_bytes']<100*2**20
 assert sum(r['body_bytes_read'] for r in download['requests'])==download['transfer_body_bytes']
 for r in download['requests']:assert r['status']==206 and r['body_bytes_read']==r['requested_bytes'] and r['Content-Range']==f"bytes {r['start']}-{r['end']}/{download['archive_bytes']}"
 assert {e['name'] for e in download['saved']}=={n for d in DATES for n in names_for(d)}
 for e in download['saved']:
  p=RAW/e['name'];assert sha(p)==e['sha256'] and zlib.crc32(p.read_bytes())==e['CRC32'];validate_npz(p)
 testlog=(ROOT/'logs/fourcastden_multidate_tests.log').read_text();assert 'Ran 206 tests' in testlog and testlog.rstrip().endswith('OK')
 rows=list(csv.DictReader((ROOT/'results/metrics/fourcastden_multidate_v1_layers.csv').open()));factors=np.repeat(SI_FACTORS,LENGTHS);lat=np.load(ROOT/'data/processed/static/lat.npy');weight=np.broadcast_to(np.cos(np.deg2rad(lat))[:,None],(36,72));worst_rmse=0.;worst_acc=0.;evaluations=0
 for day in a['initial_windows']:
  for model in ['Direct','Flow']:
   if day=='2023-01-04':
    tag='fourcastden_two_step_v1' if model=='Direct' else 'fourcastden_flow_two_step_v1';p=ROOT/f'data/processed/{tag}/result.npz';expected=json.loads((ROOT/f'experiments/{tag}/runtime.json').read_text())['file_sha256']
   else:p=D/f'{day}_{model}.npz';expected=next(r for r in rt['records'] if r['date']==day and r['model']==model)['result_sha256']
   assert sha(p)==expected
   with np.load(p) as z:q={k:z[k].copy() for k in z.files}
   ins=[(q['input0'],q['scalars0']),(q['input1'],q['scalars1'])];sw=np.vstack([np.zeros(4),q['scalars0'].reshape(4),q['scalars1'].reshape(4)])
   outputs=[q['increment0'],q['increment1']] if day=='2023-01-04' and model=='Flow' else [q['out0'],q['out1']]
   if model=='Flow':flow_feedback_check(ins,outputs,q['real'][0],q['pred'][0],sw)
   else:
    feedback_check(ins,outputs,q['real'][0],sw)
    for k in range(2):np.testing.assert_array_equal(outputs[k][0],q['pred'][0,k+1])
   mean=q['means'][:171].astype(float);std=q['stds'][:171].astype(float);pred=q['pred'][0].astype(float)*std+mean;real=q['real'][0,:,:171].astype(float)*std+mean
   assert np.isfinite(pred).all() and (pred[:,142:]>0).all() and (pred[:,:28]>0).all()
   for h in (1,2):
    rmse=np.sqrt(np.sum(weight*(pred[h]-real[h])**2,axis=(1,2))/weight.sum())
    p1=pred[h]-q['climatology'];r1=real[h]-q['climatology'];den=np.sqrt(np.sum(weight*p1**2,axis=(1,2))*np.sum(weight*r1**2,axis=(1,2)));valid=den>0
    acc=np.full(171,np.nan);acc[valid]=np.sum(weight*p1*r1,axis=(1,2))[valid]/den[valid]
    np.testing.assert_allclose(rmse,q['author_rmse'][0,h-1],rtol=2e-5,atol=1e-25);np.testing.assert_allclose(acc[valid],q['author_acc'][0,h-1][valid],rtol=2e-5,atol=2e-6)
    rr=[r for r in rows if r['date']==day and r['model']==model and int(r['hour'])==h];assert len(rr)==171
    np.testing.assert_allclose([float(r['RMSE_SI']) for r in rr],rmse*factors,rtol=1e-12,atol=1e-25)
    worst_rmse=max(worst_rmse,float(np.max(abs(rmse-q['author_rmse'][0,h-1])/rmse)));worst_acc=max(worst_acc,float(np.max(abs(acc[valid]-q['author_acc'][0,h-1][valid]))));evaluations+=171
 for day in a['initial_windows']:
  win=lambda h,m:next(w for w in a['windows'] if w['date']==day and w['hour']==h and w['model']==m)
  assert win(2,'Direct')['mean_DEN_layer_RMSE_kg_m3']<win(2,'Flow')['mean_DEN_layer_RMSE_kg_m3']
  for h in (1,2):
   for key in ['upper_native_mean_relative_RMS','upper_native_mean_log_RMS','near400_500_mean_relative_RMS','near400_500_mean_log_RMS']:assert win(h,'Flow')[key]<win(h,'Direct')[key]
  assert win(2,'Flow')['upper_native_mean_relative_RMS']/win(1,'Flow')['upper_native_mean_relative_RMS']>win(2,'Direct')['upper_native_mean_relative_RMS']/win(1,'Direct')['upper_native_mean_relative_RMS']
  for model in ['Direct','Flow']:
   for name in ['TN','UN','VN','WN','Z','DEN']:
    r=[next(x for x in a['comparison'] if x['date']==day and x['variable']==name and x['hour']==h)[model] for h in (1,2)];assert r[1]>r[0]
 expected_counts=dict(layers=5130,summary=180,density_layers=2610,windows=30,drivers=15,paired=60,aggregate=12)
 for name,count in expected_counts.items():assert len(list(csv.DictReader((ROOT/f'results/metrics/fourcastden_multidate_v1_{name}.csv').open())))==count
 paths=set(F.rglob('*'))|set(D.rglob('*'))|set(RAW.rglob('*'))
 for sub in ['logs','results/metrics','results/figures']:paths.update((ROOT/sub).glob('fourcastden_multidate*'))
 files=[p for p in paths if p.is_file() and p.name not in ('delivery_audit.json','fourcastden_multidate_audit.log')]
 assert all(p.resolve().is_relative_to(ROOT) for p in files);newbytes=sum(p.stat().st_size for p in files);assert newbytes+2**20<250*2**20
 out=dict(status='PASS',protected_files_unchanged=len(protected),data_members_CRC_SHA_verified=12,new_sequences=8,new_forwards=16,January_replayed=False,tests=206,independent_channel_metric_checks=evaluations,max_RMSE_relative_discrepancy=worst_rmse,max_ACC_absolute_discrepancy=worst_acc,all_feedback_exact=True,all_predictions_finite=True,DEN_positive_fraction=1.,report_cross_window_claims_verified=True,transfer_bytes=download['transfer_body_bytes'],supervised_wall_s=sup['wall_s'],GPU_phase_wall_s=rt['GPU_wall_s'],peak_RSS_bytes=sup['peak_tree_RSS_bytes'],new_experiment_bytes=newbytes,code_docs_allowance_bytes=2**20,budget_bytes=250*2**20,CSV_rows=expected_counts,new_science_artifact_SHA256={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)})
 dump(F/'delivery_audit.json',out);print(json.dumps({k:v for k,v in out.items() if k!='new_science_artifact_SHA256'},indent=2))
if __name__=='__main__':main()
