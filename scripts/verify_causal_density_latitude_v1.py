"""Independent arithmetic audit of frozen v13-B outputs. Never fits a new model."""
from pathlib import Path
import sys,json,csv,hashlib,time,resource,math
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np
from observations.density_catalog import read_swarm_pod
from PIL import Image
F=ROOT/'experiments/causal_density_latitude_correction_v1'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def load(n):return json.loads((F/n).read_text())
def rows(n):return list(csv.DictReader((F/n).open()))
def close(a,b):assert np.isclose(float(a),float(b),rtol=1e-13,atol=0),(a,b)
def band(lat):return np.where(np.abs(lat)<30,0,np.where(np.abs(lat)<60,1,2))
def median(x):
 s=sorted(float(v) for v in x);n=len(s)
 return s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2

def main():
 start=time.perf_counter();source=load('source_manifest.json');params=load('correction_parameters.json');pr=load('frozen_protocol.json');a=np.load(F/'matched_local.npz');early=np.load(F/'early_matches_local.npz');counts=0;verified=0
 for path,h in source['protected_history_SHA256'].items():assert sha(ROOT/path)==h,path
 for path,h in pr['code_SHA256'].items():assert sha(ROOT/path)==h,path
 assert sha(F/'frozen_protocol.json')==load('protocol_sha256.json')['SHA256'];assert sha(F/'correction_parameters.json')==load('parameter_sha256.json')['SHA256']
 cdf_checks=[]
 for y in ['2021','2022']:
  s=source['CDFs'][y];assert sha(ROOT/s['file'])==s['SHA256'];_,obs,contract=read_swarm_pod(ROOT/s['file'],ROOT/source['hapi']['path'],s['SHA256'],satellite='A');t=obs['utc'];assert len(t)==2880 and np.all(np.diff(t)==np.timedelta64(30,'s'));assert t[0]==np.datetime64(y+'-03-23T00') and t[-1]==np.datetime64(y+'-03-23T23:59:30');assert obs['quality'].all() and (obs['validity_flag']==0).all()
  late=(t>=np.datetime64(y+'-03-23T15'))&(t<np.datetime64(y+'-03-24T00'));em=(t>=np.datetime64(y+'-03-23T03'))&(t<np.datetime64(y+'-03-23T06'))
  for key,k in [('density','density'),('latitude','latitude'),('utc','utc')]:assert np.array_equal(obs[key][late],a[y+'_'+k])
  for key in ['density','latitude','utc','quality']:assert np.array_equal(obs[key][em],early[y+'_'+key])
  cdf_checks.append(dict(year=y,N=2880,quality=2880,late_N=int(late.sum()),early_N=int(em.sum()),SHA_PASS=True,units=contract['variables']['density'] if 'variables' in contract else 'read_swarm_pod unit contract checked'))
  hist=a[y+'_utc']<np.datetime64(y+'-03-23T18');bb=band(a[y+'_latitude'])
  def check_coeff(c,t,lat,o,p,m):
   nonlocal counts
   assert int(m.sum())==c['N']>=30
   e=np.log(o[m])-np.log(p[m]);close(median(e),c['b']);close(math.exp(c['b']),c['multiplier'])
   h=hashlib.sha256()
   for v in [np.asarray(t[m],dtype='datetime64[ns]').astype('<i8'),np.asarray(lat[m],dtype='<f8'),np.asarray(o[m],dtype='<f8'),np.asarray(p[m],dtype='<f8')]:h.update(v.tobytes())
   assert h.hexdigest()==c['sample_SHA256'];assert str(t[m][0])+'Z'==c['first_UTC'] and str(t[m][-1])+'Z'==c['last_UTC'];counts+=1
  for case in ['B14','A7','B7']:
   ss=source['cases'][y][case];assert sha(ROOT/ss['file'])==ss['SHA256'];raw=a[f'{y}_{case}_Raw'];o=a[y+'_density'];fit=params['Global_and_Latitude'][y][case];check_coeff(fit['global_fit'],a[y+'_utc'],a[y+'_latitude'],o,raw,hist)
   for j,name in enumerate(['low','mid','high']):check_coeff(fit['latitude'][name],a[y+'_utc'],a[y+'_latitude'],o,raw,hist&(bb==j))
   close_array=lambda x,z: np.testing.assert_allclose(x,z,rtol=1e-13,atol=0)
   close_array(a[f'{y}_{case}_GlobalAdaptive18'],raw*math.exp(fit['global_fit']['b']));close_array(a[f'{y}_{case}_LatitudeAdaptive18'],raw*np.array([math.exp(fit['latitude'][['low','mid','high'][j]]['b']) for j in bb]))
   poisoned=o.copy();poisoned[~hist]*=1e20
   assert median(np.log(poisoned[hist])-np.log(raw[hist]))==fit['global_fit']['b']
   for j,name in enumerate(['low','mid','high']):
    m=hist&(bb==j);assert median(np.log(poisoned[m])-np.log(raw[m]))==fit['latitude'][name]['b']
  check_coeff(params['Stale06'][y]['coefficient'],early[y+'_utc'],early[y+'_latitude'],early[y+'_density'],early[y+'_model'],np.ones(360,bool));np.testing.assert_allclose(a[y+'_B14_Stale06'],a[y+'_B14_Raw']*math.exp(params['Stale06'][y]['coefficient']['b']),rtol=1e-13,atol=0)
 metrics=rows('metrics.csv')+rows('region_metrics.csv');lookup={}
 for r in metrics:
  y,case,method=r['year'],r['case'],r['method'];t=a[y+'_utc'];hours=(t-np.datetime64(y+'-03-23'))/np.timedelta64(1,'h');win=r['window'];bounds={'analysis':(15,18),'future_1h':(18,19),'future_3h':(18,21),'future_6h':(18,24),'block_0_1h':(18,19),'block_1_3h':(19,21),'block_3_6h':(21,24)};lo,hi=bounds[win];m=(hours>=lo)&(hours<hi)&a[y+'_common'];reg=r['region']
  if reg!='all':m&=band(a[y+'_latitude'])==['low','mid','high'].index(reg)
  assert m.sum()==int(r['n']) and a[f'{y}_{case}_{method}_support'][m].all()
  if m.sum()<30:assert r['status']=='N/A_INSUFFICIENT_SAMPLES';continue
  p,o=a[f'{y}_{case}_{method}'][m],a[y+'_density'][m];e=p-o;rel=e/o;d=dict(MAE=np.mean(abs(e)),RMSE=np.sqrt(np.mean(e**2)),relative_RMS=np.sqrt(np.mean(rel**2)),relative_P95=np.percentile(abs(rel),95),bias=np.mean(e),relative_bias=np.mean(rel),log_RMS=np.sqrt(np.mean(np.log(p/o)**2)),max_abs=abs(e).max(),Pearson=np.corrcoef(p,o)[0,1]);assert r['status']=='OK'
  for k,v in d.items():close(r[k],v)
  lookup[(y,case,win,reg,method)]=d;verified+=1
 joints=rows('joint_assessment.csv')
 for r in joints:
  y,c,w,m=r['year'],r['case'],r['window'],r['method'];raw=lookup[(y,c,w,'all','Raw')];cor=lookup[(y,c,w,'all',m)];rl=lookup[(y,c,w,'low','Raw')];cl=lookup[(y,c,w,'low',m)];flags=[cor['RMSE']<raw['RMSE'],cor['relative_RMS']<raw['relative_RMS'],cor['relative_P95']<=raw['relative_P95'],abs(cl['relative_bias'])<=abs(rl['relative_bias'])]
  for k,v in zip(['RMSE_BENEFIT','RELATIVE_RMS_BENEFIT','TAIL_NONWORSENED','LOW_LATITUDE_BIAS_NONWORSENED'],flags):assert r[k]==str(bool(v))
  assert r['JOINT_NO_REGRET']==('PASS' if all(flags) else 'FAIL');close(r['RMSE_gain_pct'],100*(1-cor['RMSE']/raw['RMSE']));close(r['relative_RMS_gain_pct'],100*(1-cor['relative_RMS']/raw['relative_RMS']))
 assert load('future_poison_test.json')['PASS'];assert load('shared_sample_identity.json')['Raw_corrected_identical_requested_IDs']
 for r in rows('coverage.csv'):assert r['N_eligible']==r['N_model_valid']==r['N_method_supported'] and float(r['query_coverage'])==1
 for f in (F/'figures').glob('*.png'):
  with Image.open(f) as im:im.verify()
 result=dict(PASS=True,independent_sorted_median_coefficients=counts,independent_metric_rows=verified,independent_joint_rows=len(joints),CDF_checks=cdf_checks,original_sources_SHA_PASS=True,protected_history_files_unchanged=len(source['protected_history_SHA256']),future_poison_PASS=True,requested_sample_identity_PASS=True,manual_prediction_and_exp_PASS=True,rtol=1e-13,atol=0,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
 with (F/'independent_verification.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result))
if __name__=='__main__':main()
