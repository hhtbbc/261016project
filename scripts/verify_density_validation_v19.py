"""Once-only V19 verification. Does not import or call any V18 scoring/fitting entry."""
from pathlib import Path
import sys,json,csv,math,datetime,time,resource,collections
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src')]
import numpy as np,cdflib
from netCDF4 import Dataset
from astropy.coordinates import EarthLocation
from astropy.time import Time
import astropy.units as u
from evaluation.density_verification import *
F=R/'experiments/tiegcm_2022_mar25_independent_verification_v19';OLD=R/'experiments/tiegcm_2022_mar25_density_validation_v18';REF=R/'experiments/causal_density_new_date_validation_v1'
def load(p):return json.loads(Path(p).read_text())
def rows(p):return list(csv.DictReader(Path(p).open()))
def output(name,x):write_json(F,name,x)
def table(name,x):
 p=F/name;p.resolve().relative_to(F)
 with p.open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(x[0]),lineterminator='\n');w.writeheader();w.writerows(x)

def main():
 started=time.perf_counter();cpu=time.process_time();checks=[]
 def eq(section,key,actual,expected):
  ok=actual==expected;checks.append(dict(section=section,key=str(key),main=str(actual),independent=str(expected),absolute_difference=None,relative_difference=None,allowed_absolute_difference=None,rtol=RTOL,atol=ATOL,PASS=bool(ok)));return ok
 def num(section,key,actual,expected):
  d=numeric(actual,expected);checks.append(dict(section=section,key=str(key),**d));return d['PASS']
 protection=load(F/'asset_protection_before.json')['protected_SHA256']
 for n,h in protection.items():check_sha(R/n,h)
 protocol=load(F/'protocol.json')
 for n,h in protocol['code_SHA256'].items():check_sha(R/n,h)
 require(load(F/'tests.json')['PASS'],'Tests not passed before table access')
 source=load(OLD/'source_manifest.json');parameters=load(OLD/'correction_parameters.json');par=parameters['parameters'];receipt=load(OLD/'parameter_freeze_receipt.json');check_sha(OLD/'correction_parameters.json',receipt['SHA256']);check_sha(OLD/'frozen_protocol.json',parameters['protocol_SHA256'])
 cached=np.load(OLD/'matched_local.npz');raw=np.asarray(cached['raw'],float)
 cp=R/source['CDF']['path'];check_sha(cp,source['CDF']['SHA256'])
 with cdflib.CDF(cp) as c:
  utc=cdflib.cdfepoch.to_datetime(c.varget('time'));observed=c.varget('density');lat=c.varget('latitude');lon=c.varget('longitude');height=c.varget('altitude');flag=c.varget('validity_flag')
  require(c.globalattsget()['TITLE']==[cp.stem] and c.globalattsget()['TIME SYSTEM']==['UTC'],'CDF product identity mismatch')
  for k,unit in [('density','kg/m3'),('latitude','deg'),('longitude','deg'),('altitude','m')]:require(c.varattsget(k)['UNITS']==unit,'CDF unit mismatch')
 quality=(flag==0)&np.isfinite(observed)&(observed>0)&(observed!=9.99e32)&(observed<1e30)&np.isfinite(lat)&(abs(lat)<=90)&np.isfinite(lon)&(abs(lon)<=180)&np.isfinite(height)&(height>0)
 require_ids(utc,cached['utc'])
 for key,values in [('density',observed),('latitude',lat),('longitude',lon),('altitude',height),('validity_flag',flag),('quality',quality)]:require(np.array_equal(values,cached[key]),'CDF/cached mismatch '+key)
 require(len(utc)==2880 and quality.all() and np.all(np.diff(utc)==np.timedelta64(30,'s')),'CDF quality/time identity mismatch')
 require(utc[0]==np.datetime64('2022-03-25') and utc[-1]==np.datetime64('2022-03-25T23:59:30'),'CDF endpoints mismatch')
 ids=['Swarm/A/0301/'+str(t)+'Z' for t in utc];full_ids=rows(OLD/'common_sample_ids_local.csv');require_ids([x['observation_id'] for x in full_ids],ids);require_ids([x['UTC'] for x in full_ids],[str(t)+'Z' for t in utc])
 for i,row in enumerate(full_ids):
  for key,value in [('latitude_deg',lat[i]),('longitude_deg',lon[i]),('GRS80_height_m',height[i]),('model_density_kg_m3',raw[i])]:require(float(row[key])==float(value),'Full ID index value mismatch')
  require(int(row['flag'])==int(flag[i]) and row['quality']=='True','Full ID quality mismatch')
 print('V19 ORIGINAL CDF AND COMMON IDS VERIFIED',flush=True)
 # Independent native model read and eight-column reconstruction; no scoring modules.
 frames=[]
 for ent in source['target_models']:
  path=R/ent['path'];check_sha(path,ent['SHA256'])
  with Dataset(path) as n:
   n.set_auto_mask(False);mlat=np.asarray(n['lat'][:]);mlon=np.asarray(n['lon'][:])
   for k,(year,mt) in enumerate(zip(n['year'][:],n['mtime'][:])):
    dt=datetime.datetime(int(year),1,1)+datetime.timedelta(days=int(mt[0])-1,hours=int(mt[1]),minutes=int(mt[2]));t=np.datetime64(dt,'ns')
    if np.datetime64('2022-03-25')<=t<=np.datetime64('2022-03-26'):
     vv=[]
     for key,unit,factor in [('ZG','cm',.01),('DEN','g/cm3',1000.)]:
      v=n[key];require(v.dimensions==('time','ilev','lat','lon') and v.units==unit,'Native model schema mismatch');x=np.asarray(v[k]);require(np.isfinite(x).all(),'Native nonfinite data')
      for attr in ['missing_value','_FillValue']:
       if hasattr(v,attr):require(not (x==np.asarray(getattr(v,attr),dtype=x.dtype)).any(),'Native missing marker')
      vv.append(x.astype(float)*factor)
     require((vv[1]>0).all() and (np.diff(vv[0],axis=0)>0).all(),'Native physical invalidity');frames.append((t,*vv))
 frames.sort(key=lambda x:x[0]);require(len(frames)==25 and np.all(np.diff([x[0] for x in frames])==np.timedelta64(1,'h')),'Target model timeline incomplete')
 # Same explicit Map-A hypothesis, independently construct the GRS80 XYZ -> WGS84 coordinates.
 grs=EarthLocation.from_geodetic(lon*u.deg,lat*u.deg,height*u.m,ellipsoid='GRS80');xyz=np.array([v.to_value(u.m) for v in grs.geocentric]);wg=EarthLocation.from_geocentric(*(v*u.m for v in xyz)).to_geodetic(ellipsoid='WGS84');glat=wg.lat.to_value(u.deg);glon=wg.lon.to_value(u.deg);gh=wg.height.to_value(u.m)
 ft=Time(np.array([x[0] for x in frames]));sec=np.asarray((ft-ft[0]).sec);obssec=np.asarray((Time(utc)-ft[0]).sec);ownraw=[]
 for point in range(len(utc)):
  xx=obssec[point];yy=glat[point];ll=(glon[point]-mlon[0])%360+mlon[0];zzh=gh[point];require(sec[0]<=xx<=sec[-1] and mlat[0]<=yy<=mlat[-1],'Model extrapolation')
  k=int(np.clip(np.searchsorted(sec,xx,side='right')-1,0,len(sec)-2));j=int(np.clip(np.searchsorted(mlat,yy,side='right')-1,0,len(mlat)-2));i=int(np.searchsorted(mlon,ll,side='right')-1);i2=(i+1)%len(mlon);right=mlon[i2]+(360 if i2==0 else 0)
  wt=(xx-sec[k])/(sec[k+1]-sec[k]);wy=(yy-mlat[j])/(mlat[j+1]-mlat[j]);wx=(ll-mlon[i])/(right-mlon[i]);values=[]
  for ki in [k,k+1]:
   for ji in [j,j+1]:
    for li in [i,i2]:
     z=frames[ki][1][:,ji,li];rho=frames[ki][2][:,ji,li];require(z[0]<=zzh<=z[-1],'Vertical extrapolation');values.append(np.exp(np.interp(zzh,z,np.log(rho))))
  weights=np.array([1-wt,wt])[:,None,None]*np.array([1-wy,wy])[None,:,None]*np.array([1-wx,wx])[None,None,:];ownraw.append(float(np.sum(weights*np.array(values).reshape(2,2,2))))
 ownraw=np.array(ownraw);require(np.all(np.isclose(raw,ownraw,rtol=RTOL,atol=ATOL)),'Independent raw/model reconstruction mismatch')
 output('raw_model_verification.json',dict(PASS=True,native_frames=25,raw_queries=2880,column_checks=23040,all_columns_including_zero_weight=True,source_SHA256=source['target_models'],max_absolute_difference=float(np.max(abs(raw-ownraw))),max_relative_difference=float(np.max(abs(raw/ownraw-1))),rtol=RTOL,atol=ATOL,stored_raw_is_original_query_numerical_contract=True,corrected_arrays_not_used_as_inputs=True,history_read_origin_addendum_unchanged=True))
 print('V19 ORIGINAL RAW QUERIES INDEPENDENTLY CHECKED',flush=True)
 # C1: sorted medians and exponential library diagnostics are not new parameters.
 bb=band(lat);coeff=[];poison=[];ulprows=[]
 for h in [6,18]:
  history=window(utc,h,'analysis')&quality;require(history.sum()==360,'Historical sample count')
  targets=[(f'GlobalAdaptive{h:02d}',par[f'GlobalAdaptive{h:02d}'],history)]
  if h==18:targets += [(key,par['LatitudeAdaptive18'][key],history&(bb==i)) for i,key in enumerate(BANDS)]
  poisoned=observed.copy();poisoned[utc>=np.datetime64(f'2022-03-25T{h:02d}')]*=1e20
  for name,c,sel in targets:
   require(sel.sum()==c['N'] and sel.sum()>=30,'Unsupported or wrong historical coefficient sample count');s=sorted(map(float,np.log(observed[sel])-np.log(raw[sel])));n=len(s);med=s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2
   num('coefficient',f'{h}/{name}/b',c['b'],med);np_exp=float(np.exp(c['b']));math_exp=math.exp(c['b']);num('coefficient',f'{h}/{name}/numpy_exp',c['multiplier'],np_exp);num('coefficient',f'{h}/{name}/math_exp_diagnostic',c['multiplier'],math_exp);require(np_exp==c['multiplier'],'Original numpy exp is not the frozen multiplier')
   digest=sample_sha(utc[sel],lat[sel],observed[sel],raw[sel]);require(digest==c['sample_SHA256'],'Frozen historical sample SHA mismatch');require(np.array_equal(observed[sel],poisoned[sel]),'Poison affects historical inputs')
   poison.append(dict(cutoff=h,coefficient=name,N=int(sel.sum()),history_SHA256=digest,historical_inputs_bitwise_unchanged=True,future_intersection_N=int((sel&(utc>=np.datetime64(f'2022-03-25T{h:02d}'))).sum()),new_parameter_files=0))
   coeff.append(dict(cutoff=h,name=name,N=n,b_frozen=c['b'],b_sorted_median_diagnostic=med,frozen_multiplier=c['multiplier'],numpy_exp=np_exp,math_exp=math_exp,difference_ULP=abs(math_exp-np_exp)/np.spacing(np_exp),numpy_exp_bitwise_matches_frozen=True,sample_SHA256=digest))
   if h==18 and name in BANDS:
    mask=bb==BANDS.index(name);d=raw[mask]*math_exp-raw[mask]*c['multiplier'];ulprows.append(dict(band=name,N=int(mask.sum()),multiplier_difference_ULP=abs(math_exp-np_exp)/np.spacing(np_exp),predictions_changed=int((d!=0).sum()),max_absolute_prediction_difference=float(np.max(abs(d))),max_relative_prediction_difference=float(np.max(abs(d)/(raw[mask]*c['multiplier'])))))
 table('coefficient_and_exp_diagnostics.csv',coeff);table('prediction_exp_perturbation.csv',ulprows)
 evidence=load(OLD/'future_poison_test.json');require(evidence['PASS'] and evidence['factor']==1e20 and evidence['parameter_SHA256']==receipt['SHA256'],'V18 poison evidence mismatch');require(parameters['protocol_SHA256']==sha(OLD/'frozen_protocol.json'),'Protocol digest mismatch');output('future_poison_audit.json',dict(PASS=True,coefficient_history_checks=poison,factor=1e20,separate_original_copy_for_each_cutoff=True,pure_input_invariance_no_formal_fit=True,Stale06_reference=par['Stale06_reference'],parameter_SHA256=receipt['SHA256'],original_poison_SHA256=sha(OLD/'future_poison_test.json')))
 # C2: factors are loaded from the frozen file, never reconstructed by exp.
 pred={};support={};array_rows=[]
 for h,methods in [(6,['Raw','GlobalAdaptive06']),(18,['Raw','GlobalAdaptive18','LatitudeAdaptive18','Stale06'])]:
  for met in methods:
   p,s=prediction(raw,lat,par,h,met);pred[h,met]=p;support[h,met]=s;original=cached[f'{h}_{met}'];ok=np.isclose(p,original,rtol=RTOL,atol=ATOL);require(ok.all(),'Frozen prediction array mismatch');array_rows.append(dict(cutoff=h,method=met,N=len(p),support_N=int(s.sum()),exact_equal=bool(np.array_equal(p,original)),max_absolute_difference=float(np.max(abs(p-original))),max_relative_difference=float(np.max(abs(p/original-1))),PASS=bool(ok.all()),rtol=RTOL,atol=ATOL))
 table('prediction_reconstruction.csv',array_rows)
 # Reproduce old failure using old exp choice only as an implementation diagnostic.
 local_math=raw.copy()
 for i,key in enumerate(BANDS):local_math[bb==i]*=math.exp(par['LatitudeAdaptive18'][key]['b'])
 hist=window(utc,18,'analysis');contract_bias=float(np.mean(pred[18,'LatitudeAdaptive18'][hist]-observed[hist]));math_bias=float(np.mean(local_math[hist]-observed[hist]));oldfailure=load(OLD/'independent_verification.json');require(contract_bias==oldfailure['main'] and math_bias==oldfailure['independent_math_exp'],'Old numerical failure not reproduced')
 output('float_roundoff_diagnosis.json',dict(old_failure_reproduced=True,contract_Bias=contract_bias,alternative_math_exp_Bias=math_bias,old_math_exp_comparison=numeric(oldfailure['main'],math_bias),frozen_contract_comparison=numeric(oldfailure['main'],contract_bias),one_ULP_mid_band=coeff[3]['difference_ULP']==1 if coeff[3]['name']=='mid' else next(x['difference_ULP']==1 for x in coeff if x['name']=='mid'),original_scoring_calls_numpy_exp_from_frozen_b=True,original_scoring_did_not_directly_use_saved_multiplier=True,all_five_original_numpy_exp_values_equal_saved_multiplier=True,near_zero_effect='Mean signed errors nearly cancel; the one-ULP multiplier change makes an absolute difference7.513900122230137e-29 in Bias, relative1.376676550535194e-13. Original strict rule rejects that alternative implementation. No tolerance or Bias exception introduced.'))
 print('V19 C1 AND C2 VERIFIED; ALL TABLE ROWS BEGIN',flush=True)
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
if __name__=='__main__':
 try:main()
 except Exception as e:
  if not (F/'result.json').exists():output('result.json',dict(status='INCONCLUSIVE',PASS=False,error_type=type(e).__name__,error=str(e),original_assets_not_modified=True,new_scoring_runs=0,new_fits=0,automatic_retries=0))
  raise
