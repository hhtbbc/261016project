"""Independent new-date arithmetic, identity and fixed resource-budget audit."""
from pathlib import Path
import sys,csv,json,math,hashlib,time
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R),str(R/'src')]
import numpy as np,cdflib
from observations.bounded_swarm_acquisition import sha
F=R/'experiments/causal_density_new_date_validation_v1'
def rows(n):return list(csv.DictReader((F/n).open()))
def close(x,y):assert np.isclose(float(x),float(y),rtol=1e-13,atol=0),(x,y)
def med(x):
 a=sorted(map(float,x));n=len(a);return a[n//2] if n%2 else (a[n//2-1]+a[n//2])/2

def verify():
 start=time.perf_counter();a=np.load(F/'matched_local.npz');t=a['utc'];obs=a['density'];lat=abs(a['latitude']);bands=np.where(lat<30,0,np.where(lat<60,1,2));p=json.loads((F/'correction_parameters.json').read_text());audit=json.loads((F/'observation_acquisition_audit.json').read_text());protocol=json.loads((F/'frozen_protocol.json').read_text());assert p['protocol_SHA256']==sha(F/'frozen_protocol.json') and sha(F/'correction_parameters.json')==json.loads((F/'parameter_sha256.json').read_text())['SHA256']
 assert sha(R/audit['CDF']['path'])==audit['CDF']['SHA256']
 with cdflib.CDF(R/audit['CDF']['path']) as c:
  tt=cdflib.cdfepoch.to_datetime(c.varget('time'));mask=((tt>=np.datetime64('2021-03-25T03'))&(tt<np.datetime64('2021-03-25T12')))|((tt>=np.datetime64('2021-03-25T15'))&(tt<np.datetime64('2021-03-26T00')));assert np.array_equal(tt[mask],t);np.testing.assert_array_equal(c.varget('density')[mask],obs)
 coefcount=0
 for case,c in p['parameters'].items():
  raw=a[case+'_Raw'];e=np.log(obs)-np.log(raw)
  for hour in [6,18]:
   cut=np.datetime64(f'2021-03-25T{hour:02d}');hist=(t>=cut-np.timedelta64(3,'h'))&(t<cut);future=t>=cut;assert not np.intersect1d(t[hist],t[future]).size;key=f'GlobalAdaptive{hour:02d}';g=c[key];assert hist.sum()==g['N'];close(g['b'],med(e[hist]));close(g['multiplier'],math.exp(g['b']));coefcount+=1
   if hour==18:
    for j,name in enumerate(['low','mid','high']):
     m=hist&(bands==j);cf=c['LatitudeAdaptive18'][name];assert m.sum()==cf['N']
     if m.sum()>=30:close(cf['b'],med(e[m]));close(cf['multiplier'],math.exp(cf['b']));coefcount+=1
     else:assert cf['b'] is None
  np.testing.assert_array_equal(a[f'{case}_18_Stale06'],a[f'{case}_6_GlobalAdaptive06'])
 stats={};nmetric=0
 for r in rows('metrics.csv')+rows('region_metrics.csv'):
  case,method,hour=r['case'],r['method'],int(r['cutoff']);cut=np.datetime64(f'2021-03-25T{hour:02d}');hours=(t-cut)/np.timedelta64(1,'h');w=r['window'];bounds={'analysis':(-3,0),'future_1h':(0,1),'future_3h':(0,3),'future_6h':(0,6),'block_0_1h':(0,1),'block_1_3h':(1,3),'block_3_6h':(3,6)};lo,hi=bounds[w];sel=(hours>=lo)&(hours<hi);reg=r['region']
  if reg!='all':sel&=bands==['low','mid','high'].index(reg)
  pred=a[f'{case}_{hour}_{method}'];assert sel.sum()==int(r['n'])
  if r['status']!='OK':continue
  pp,oo=pred[sel],obs[sel];d=pp-oo;rel=d/oo;metrics=dict(RMSE=np.sqrt(np.mean(d*d)),MAE=np.mean(abs(d)),relative_RMS=np.sqrt(np.mean(rel*rel)),relative_P95=np.quantile(abs(rel),.95),bias=np.mean(d),relative_bias=np.mean(rel),log_RMS=np.sqrt(np.mean(np.log(pp/oo)**2)),max_abs=abs(d).max(),Pearson=np.corrcoef(pp,oo)[0,1])
  for k,v in metrics.items():close(r[k],v)
  stats[(case,hour,w,reg,method)]=metrics;nmetric+=1
 nj=0
 for r in rows('joint_assessment.csv'):
  if r['status']!='OK':continue
  c,h,w,met=r['case'],int(r['cutoff']),r['window'],r['method'];raw=stats[c,h,w,'all','Raw'];co=stats[c,h,w,'all',met];rl=stats[c,h,w,'low','Raw'];cl=stats[c,h,w,'low',met];flags=[co['RMSE']<raw['RMSE'],co['relative_RMS']<raw['relative_RMS'],co['relative_P95']<=raw['relative_P95'],abs(cl['relative_bias'])<=abs(rl['relative_bias'])]
  for k,v in zip(['RMSE_BENEFIT','RELATIVE_RMS_BENEFIT','TAIL_NONWORSENED','LOW_LATITUDE_BIAS_NONWORSENED'],flags):assert r[k]==str(bool(v))
  assert r['JOINT_NO_REGRET']==('PASS' if all(flags) else 'FAIL');nj+=1
 for r in rows('coverage.csv'):assert int(r['N_supported'])<=int(r['N']) and float(r['query_coverage'])==1
 qa=json.loads((F/'query_admission.json').read_text());assert qa['PASS'] and all(x['N_requested']==x['N_valid'] for x in qa['rows']);assert len(qa['independent_probes'])==3*len(qa['rows']);assert json.loads((F/'future_poison_test.json').read_text())['PASS']
 source=json.loads((F/'source_manifest.json').read_text())
 for case,x in source['models'].items():
  for item in x['secondary_files']+x['primary_files']:assert sha(R/item['path'])==item['SHA256']
 for n,h in source['protected_SHA256'].items():assert sha(R/n)==h,n
 expansion=json.loads((F/'expansion_audit.json').read_text());gap=rows('2022_target_gap.csv');assert sum(x['exists']=='False' for x in gap)==24;assert sum(x['exists']=='False' and x['needed_by_registered_queries']=='True' for x in gap)==20
 for b in expansion['budgets']:
  estimate=[x['actual_wall_s']/x['steps']*b['steps_per_run'] for x in expansion['historical_cost_evidence']];close(b['predicted_wall_s_max'],max(estimate));close(b['planning_wall_budget_s_per_run'],1.5*max(estimate))
 result=dict(PASS=True,CDF_direct_density_and_UTC_match=True,coefficients_independently_recomputed=coefcount,metric_rows=nmetric,joint_rows=nj,query_count=sum(x['N_valid'] for x in qa['rows']),history_future_disjoint=True,Stale06_same_day_same_background=True,future_poison_PASS=True,original_sources_and_history_SHA_unchanged=True,year2022_missing_frames=24,year2022_missing_query_frames=20,cost_estimates_recomputed=True,rtol=1e-13,atol=0,wall_s=time.perf_counter()-start)
 with (F/'independent_verification.json').open('x') as f:json.dump(result,f,indent=2)
 print('Independent new-date verification PASS.',flush=True)
if __name__=='__main__':verify()
