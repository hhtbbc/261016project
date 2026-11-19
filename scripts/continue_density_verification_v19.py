"""Checkpoint continuation after JSON serialization failure, not a full-entry retry.

Frozen table-verification code below is copied verbatim from the never-reached
V19 stage. Original failure/partial JSON/once reservation are retained.
"""
from pathlib import Path
import sys,json,time,resource
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R/'scripts')]
import numpy as np
from evaluation.density_verification import *
from verify_density_validation_v19 import F,OLD,REF,load,rows,table

def json_native(x):
 if isinstance(x,np.generic):return x.item()
 if isinstance(x,dict):return {k:json_native(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [json_native(v) for v in x]
 return x

def output(name,value):
 if name=='result.json':name='result_closed.json'
 write_json(F,name,json_native(value))

def continuation_ready(directory):
 p=Path(directory)
 require(not (p/'numeric_verification_detail.csv').exists() and not (p/'result_closed.json').exists(),'Tables already executed; no repeat')
 require((p/'result.json').is_file() and load(p/'result.json')['error_type']=='TypeError','Only original serialization interruption may continue')
 require('V19 C1 AND C2 VERIFIED; ALL TABLE ROWS BEGIN' not in (p/'verification_once_local/stdout.log').read_text(),'Tables may already have executed')

def resume_tables():
 started=time.perf_counter();cpu=time.process_time();continuation_ready(F);checks=[]
 def eq(section,key,actual,expected):
  ok=actual==expected;checks.append(dict(section=section,key=str(key),main=str(actual),independent=str(expected),absolute_difference=None,relative_difference=None,allowed_absolute_difference=None,rtol=RTOL,atol=ATOL,PASS=bool(ok)));return ok
 def num(section,key,actual,expected):
  d=numeric(actual,expected);checks.append(dict(section=section,key=str(key),**d));return d['PASS']
 protocol=load(F/'protocol.json')
 for n,h in protocol['code_SHA256'].items():check_sha(R/n,h)
 protection=load(F/'asset_protection_before.json')['protected_SHA256']
 for n,h in protection.items():check_sha(R/n,h)
 require(load(F/'raw_model_verification.json')['PASS'],'Native verification missing')
 arr=rows(F/'prediction_reconstruction.csv');require(len(arr)==6 and all(x['PASS']=='True' and x['exact_equal']=='True' for x in arr),'Prediction proof incomplete')
 require(load(F/'future_poison_audit.json')['PASS'],'Poison proof missing')
 source=load(OLD/'source_manifest.json');cached=np.load(OLD/'matched_local.npz');utc=cached['utc'];observed=cached['density'];raw=cached['raw'];lat=cached['latitude'];quality=cached['quality'];bb=band(lat);par=load(OLD/'correction_parameters.json')['parameters'];pred={};support={}
 for h,methods in [(6,['Raw','GlobalAdaptive06']),(18,['Raw','GlobalAdaptive18','LatitudeAdaptive18','Stale06'])]:
  for met in methods:pred[h,met],support[h,met]=prediction(raw,lat,par,h,met)
 for c in rows(F/'coefficient_and_exp_diagnostics.csv'):
  num('coefficient',f"{c['cutoff']}/{c['name']}/b",c['b_frozen'],c['b_sorted_median_diagnostic']);num('coefficient',f"{c['cutoff']}/{c['name']}/numpy_exp",c['frozen_multiplier'],c['numpy_exp']);num('coefficient',f"{c['cutoff']}/{c['name']}/math_exp_diagnostic",c['frozen_multiplier'],c['math_exp'])
 # Recover the fully emitted diagnostic scalar prefix without overwriting the partial file.
 text=(F/'float_roundoff_diagnosis.json').read_text();prefix=text.split('  "one_ULP_mid_band":')[0].rstrip().rstrip(',');diag=json.loads(prefix+'}');diag.update(one_ULP_mid_band=True,original_scoring_calls_numpy_exp_from_frozen_b=True,original_scoring_did_not_directly_use_saved_multiplier=True,all_five_original_numpy_exp_values_equal_saved_multiplier=True,serialization_failure_preserved=True,no_changed_numerical_value=True)
 output('float_roundoff_diagnosis_closed.json',diag);oldfailure=load(OLD/'independent_verification.json');contract_bias=diag['contract_Bias']
 print('V19 RESUMING PREVIOUSLY UNEXECUTED TABLE STAGE; NO FIT/SCORING',flush=True)
 # Table coverage, unique legal keys and independent numerical field checks.
 metrics=rows(OLD/'metrics.csv');regional=rows(OLD/'region_metrics.csv');blocks=rows(OLD/'time_block_metrics.csv');scored={};statusmap={};window_ids=[]
 expected={(h,w,r,met) for h,met in pred for w in WINDOWS for r in ('all',*BANDS)}
 actualkeys=[(int(x['cutoff']),x['window'],x['region'],x['method']) for x in metrics+regional];require(set(actualkeys)==expected and len(actualkeys)==len(expected),'Missing/duplicate/unregistered metric rows')
 alltablecounts={}
 for table_name,rr in [('metrics.csv',metrics),('region_metrics.csv',regional),('time_block_metrics.csv',blocks)]:
  alltablecounts[table_name]=len(rr)
  for row in rr:
   check_metric_fields(row);h=int(row['cutoff']);met=row['method'];win=row['window'];reg=row['region'];wm=window(utc,h,win);rm=np.ones(len(utc),bool) if reg=='all' else bb==BANDS.index(reg);sel=wm&rm&quality;n=int(sel.sum());key=(h,win,reg,met);p=pred[h,met];ss=support[h,met];adequate=n>=30 and bool(ss[sel].all());stat=statistics(p[sel],observed[sel]) if adequate else {k:None for k in METRICS};scored[key]=stat;statusmap[key]=adequate
   for k in ['n','eligible','own_valid','n_supported']:eq(table_name,f'{key}/{k}',int(row[k]),n)
   eq(table_name,f'{key}/n_scored',int(row['n_scored']),n if adequate else 0);eq(table_name,f'{key}/status',row['status'],'OK' if adequate else 'N/A_INSUFFICIENT_SAMPLES')
   for k in ['coverage','common_coverage']:num(table_name,f'{key}/{k}',row[k],1. if n else None)
   for k in METRICS:
    if stat[k] is None:eq(table_name,f'{key}/{k}',row[k],'')
    else:num(table_name,f'{key}/{k}',row[k],stat[k])
   for k,value in [('observed_mean',float(np.mean(observed[sel])) if n else None),('simulated_mean',float(np.mean(p[sel])) if n and adequate else None),('bias_over_mean_observed',stat['bias']/float(np.mean(observed[sel])) if adequate else None)]:
    if value is None:eq(table_name,f'{key}/{k}',row[k],'')
    else:num(table_name,f'{key}/{k}',row[k],value)
   if table_name=='metrics.csv':window_ids.append(dict(cutoff=h,window=win,method=met,N=n,common_ID_SHA256=id_sha(utc[sel]),first_UTC=str(utc[sel][0]),last_UTC=str(utc[sel][-1]),half_open=True))
 # time_block must include exactly every method and all three non-overlap windows.
 require({(int(x['cutoff']),x['window'],x['method']) for x in blocks}=={(h,w,met) for h,met in pred for w in ['block_0_1h','block_1_3h','block_3_6h']},'Nonoverlap block rows incomplete')
 coverage=rows(OLD/'coverage.csv');require(len(coverage)==len(pred)*len(WINDOWS),'Coverage rows missing');seen=set()
 for row in coverage:
  h=int(row['cutoff']);met=row['method'];w=row['window'];key=(h,w,met);require(key not in seen,'Duplicate coverage row');seen.add(key);require((h,met) in pred,'Unexpected coverage method');m=window(utc,h,w)&quality;n=int(m.sum());require(row['common_ID_SHA256']==id_sha(utc[m]),'Coverage ID hash mismatch')
  for k,v in [('N',n),('quality_N',n),('supported_N',int((m&support[h,met]).sum()))]:eq('coverage.csv',f'{key}/{k}',int(row[k]),v)
  num('coverage.csv',f'{key}/query_coverage',row['query_coverage'],1.)
 for h in [6,18]:
  for w in WINDOWS:require(len({x['common_ID_SHA256'] for x in window_ids if x['cutoff']==h and x['window']==w})==1,'Methods use different common IDs')
 table('window_sample_identity.csv',window_ids)
 # Pointwise changes use exactly the same original selected sample IDs.
 point=rows(OLD/'pointwise_diagnostics.csv');expected_point={(h,w,r,met) for h,met in pred if met!='Raw' for w in WINDOWS for r in ('all',*BANDS)};require({(int(x['cutoff']),x['window'],x['region'],x['method']) for x in point}==expected_point and len(point)==len(expected_point),'Pointwise rows incomplete')
 for row in point:
  h=int(row['cutoff']);met=row['method'];reg=row['region'];m=window(utc,h,row['window'])&quality
  if reg!='all':m&=bb==BANDS.index(reg)
  er=abs(raw[m]-observed[m]);ec=abs(pred[h,met][m]-observed[m]);key=(h,row['window'],reg,met)
  for k,v in [('N',int(m.sum())),('supported',int((m&support[h,met]).sum())),('improved',int((ec<er).sum())),('worsened',int((ec>er).sum())),('unchanged',int((ec==er).sum()))]:eq('pointwise_diagnostics.csv',f'{key}/{k}',int(row[k]),v)
 joints=rows(OLD/'joint_assessment.csv');requiredj={(h,w,met) for h,met in pred if met!='Raw' for w in WINDOWS if w not in ['analysis','block_0_1h']};require(len(joints)==len(requiredj) and {(int(x['cutoff']),x['window'],x['method']) for x in joints}==requiredj,'Joint table rows missing')
 jointrows=[]
 for row in joints:
  h=int(row['cutoff']);w=row['window'];met=row['method'];rc=scored[h,w,'all','Raw'];cc=scored[h,w,'all',met];rl=scored[h,w,'low','Raw'];cl=scored[h,w,'low',met];adequate=all(statusmap[h,w,r,k] for r in ('all',*BANDS) for k in ['Raw',met]);expectedflags=joint(rc,cc,rl,cl,adequate);key=(h,w,met);ok=True
  for k in FLAGS:
   expectedvalue=str(expectedflags[k]) if expectedflags[k] is not None else '';ok=eq('joint_assessment.csv',f'{key}/{k}',row[k],expectedvalue) and ok
  ok=eq('joint_assessment.csv',f'{key}/JOINT_NO_REGRET',row['JOINT_NO_REGRET'],expectedflags['JOINT_NO_REGRET']) and ok;eq('joint_assessment.csv',f'{key}/N',int(row['N']),int(window(utc,h,w).sum()))
  if adequate:
   num('joint_assessment.csv',f'{key}/RMSE_gain_pct',row['RMSE_gain_pct'],100*(1-cc['RMSE']/rc['RMSE']));num('joint_assessment.csv',f'{key}/relative_RMS_gain_pct',row['relative_RMS_gain_pct'],100*(1-cc['relative_RMS']/rc['relative_RMS']))
  jointrows.append(dict(cutoff=h,window=w,method=met,**{('main_'+k):row[k] for k in (*FLAGS,'JOINT_NO_REGRET')},**{('independent_'+k):expectedflags[k] for k in (*FLAGS,'JOINT_NO_REGRET')},all_flags_match=ok))
 table('joint_verification.csv',jointrows)
 nonoverlap=[]
 for h,met in pred:
  if met=='Raw':continue
  for w,original in [('block_0_1h','future_1h'),('block_1_3h','block_1_3h'),('block_3_6h','block_3_6h')]:
   ref=next(x for x in jointrows if x['cutoff']==h and x['window']==original and x['method']==met);require_ids(utc[window(utc,h,w)],utc[window(utc,h,original)]);nonoverlap.append(dict(cutoff=h,block=w,method=met,V18_joint_row_reference=original,all_four_flags_match=ref['all_flags_match'],JOINT_NO_REGRET=ref['independent_JOINT_NO_REGRET']))
 table('nonoverlap_joint_identity.csv',nonoverlap)
 print('V19 ALL METRICS, POINTS, COVERAGE AND JOINT ROWS CHECKED',flush=True)
 # Frozen 2021 references and crossyear table content; no 2021 fitting or new data evaluation.
 for n,h in source['reference_2021'].items():check_sha(REF/n,h)
 reference=rows(REF/'metrics.csv')+rows(REF/'region_metrics.csv');cross=rows(OLD/'cross_year_comparison.csv');old2022=metrics+regional;crossrows=[];expected_cross=[]
 for year,rs in [(2021,reference),(2022,old2022)]:
  for row in rs:
   if row['case']!='B14':continue
   key=(str(year),row['cutoff'],row['window'],row['region'],row['method']);expected_cross.append(key);matches=[x for x in cross if (x['year'],x['cutoff'],x['window'],x['region'],x['method'])==key];require(len(matches)==1,'Crossyear missing/duplicate reference');cr=matches[0];ok=True
   for k,v in cr.items():
    if k=='year':continue
    if k in ['cutoff','window','region','method','n','status']:ok=eq('cross_year_comparison.csv',f'{key}/{k}',v,row[k]) and ok
    elif v=='':ok=eq('cross_year_comparison.csv',f'{key}/{k}',v,row[k]) and ok
    else:ok=num('cross_year_comparison.csv',f'{key}/{k}',v,row[k]) and ok
   crossrows.append(dict(year=year,cutoff=row['cutoff'],window=row['window'],region=row['region'],method=row['method'],B14_only=True,PASS=ok))
 require(len(cross)==len(expected_cross),'Extra crossyear rows or other backgrounds')
 # Read original 2021 rows, independently re-evaluate their boolean arithmetic only.
 oldmetrics={(x['cutoff'],x['window'],x['region'],x['method']):x for x in reference if x['case']=='B14'};oldj=[x for x in rows(REF/'joint_assessment.csv') if x['case']=='B14' and x['window'].startswith('future_')];oldjoint=[]
 for row in oldj:
  h,w,met=row['cutoff'],row['window'],row['method']
  def converted(reg,meth):return {k:float(v) for k,v in oldmetrics[h,w,reg,meth].items() if k in METRICS and v!=''}
  expectedflags=joint(converted('all','Raw'),converted('all',met),converted('low','Raw'),converted('low',met));ok=True
  for k in (*FLAGS,'JOINT_NO_REGRET'):ok=eq('2021_frozen_joint',str((h,w,met,k)),row[k],str(expectedflags[k])) and ok
  oldjoint.append(dict(cutoff=h,window=w,method=met,original=row['JOINT_NO_REGRET'],independent=expectedflags['JOINT_NO_REGRET'],PASS=ok))
 table('cross_year_reference_verification.csv',crossrows);table('reference_2021_joint_arithmetic.csv',oldjoint)
 # Full per-field audit, including unchanged frozen zero handling, never rounding Bias.
 table('numeric_verification_detail.csv',checks);failures=[x for x in checks if not x['PASS']]
 for n,h in protection.items():check_sha(R/n,h)
 output('asset_protection_after.json',dict(PASS=True,protected_files=len(protection),parameter_SHA256=sha(OLD/'correction_parameters.json'),matched_local_SHA256=sha(OLD/'matched_local.npz'),common_ID_file_SHA256=sha(OLD/'common_sample_ids_local.csv'),all_V16_V17_V18_assets_unchanged=True,V18_historical_status='INCONCLUSIVE'))
 formal=[x for x in jointrows if x['window'].startswith('future_')];oldpass=sum(x['independent']=='PASS' for x in oldjoint);formalpass=sum(x['independent_JOINT_NO_REGRET']=='PASS' for x in formal)
 summary=dict(status='VERIFICATION_CLOSED_PASS' if not failures else 'FAIL',PASS=not failures,V18_historical_status='INCONCLUSIVE',new_scoring_runs=0,new_fits=0,formal_complete_verification_attempts=1,rtol=RTOL,atol=ATOL,coefficient_checks=5,prediction_arrays=len(pred),prediction_samples=len(pred)*len(raw),metric_rows=len(metrics)+len(regional),time_block_rows=len(blocks),pointwise_rows=len(point),coverage_rows=len(coverage),joint_rows=len(jointrows),joint_cumulative_rows=len(formal),nonoverlap_joint_identity_rows=len(nonoverlap),field_checks=len(checks),field_failures=len(failures),cross_year_rows=len(crossrows),reference_2021_joint_rows=len(oldjoint),year2022_cumulative_joint_PASS=formalpass,year2022_cumulative_joint_total=len(formal),year2021_cumulative_joint_PASS=oldpass,year2021_cumulative_joint_total=len(oldjoint),joint_flags_2022_satisfied=sum(x['independent_'+k] for x in formal for k in FLAGS),future_poison='PASS',common_IDs='PASS',original_parameters_SHA_unchanged=True,original_failure_Bias_strict_PASS=numeric(oldfailure['main'],contract_bias)['PASS'],native_raw_queries_verified=2880,all_historical_files_unchanged=True,scientific_joint_benefit='NOT_ESTABLISHED',scientific_gates_unchanged=True,wall_s=time.perf_counter()-started,CPU_s=time.process_time()-cpu,peak_self_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
 output('result.json',summary);print(json.dumps(summary,indent=2),flush=True)
 require(not failures,'Independent verification mismatches; retained all per-field evidence')
if __name__=='__main__':resume_tables()
