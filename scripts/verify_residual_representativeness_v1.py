"""Independent arithmetic/old-result audit, called inside the sole CPU task."""
from pathlib import Path
import sys,json,csv,time,hashlib,math
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R),str(R/'src')]
import numpy as np
import erfa
from evaluation.residual_representativeness import inverse,ELLIPSOIDS
F=R/'experiments/thermosphere_residual_representativeness_v1'
def rows(n):return list(csv.DictReader((F/n).open()))
def close(x,y):assert np.isclose(float(x),float(y),rtol=1e-13,atol=0),(x,y)
def med(x):
 a=sorted(float(v) for v in x);n=len(a);return a[n//2] if n%2 else (a[n//2-1]+a[n//2])/2

def verify():
 start=time.perf_counter();a=np.load(F/'matched_diagnostics_local.npz');index=json.loads((F/'diagnostic_case_index.json').read_text());lookup={(x['date'],x['cutoff']):x for x in index};statrows=rows('history_future_residual_statistics.csv');nc=0
 def selection(row):
  idx=lookup[(row['date'],int(row['cutoff']))];p=idx['prefix'];t=a[p+'_utc'];cut=np.datetime64(row['date']+f"T{int(row['cutoff']):02d}:00:00");hours=(t-cut)/np.timedelta64(1,'h');win=row['window'];m=(hours>=-3)&(hours<0) if win=='analysis' else (hours>=0)&(hours<int(win.split('_')[1][:-1]));lat=abs(a[p+'_latitude']);reg=row.get('region','all')
  if reg=='low':m&=lat<30
  if reg=='mid':m&=(lat>=30)&(lat<60)
  if reg=='high':m&=lat>=60
  return p,m,hours
 for r in statrows:
  p,m,_=selection(r);o=a[p+'_density'];raw=a[p+'_'+r['case']+'_Raw'];e=np.array([math.log(float(x))-math.log(float(y)) for x,y in zip(o[m],raw[m])]);assert len(e)==int(r['N'])
  if len(e)<30:assert r['status']=='N/A_INSUFFICIENT_SAMPLES';continue
  # math.log and vector log can differ in last bits; the same frozen1e-13 tolerance is used for nonzero summary values.
  e=np.log(o[m])-np.log(raw[m]);close(r['median'],med(e));close(r['MAD'],med(abs(e-med(e))));close(r['mean'],sum(map(float,e))/len(e));close(r['std'],math.sqrt(sum((float(x)-float(e.mean()))**2 for x in e)/len(e)))
  ordered=sorted(map(float,e))
  for name,q in [('P05',.05),('P25',.25),('P75',.75),('P95',.95)]:
   at=q*(len(e)-1);lo=int(math.floor(at));hi=int(math.ceil(at));close(r[name],ordered[lo]+(at-lo)*(ordered[hi]-ordered[lo]))
  nc+=1
 gaps=rows('history_future_median_gap.csv')
 for r in gaps:
  if r['status']=='OK':close(r['delta_b'],float(r['b_F'])-float(r['b_H']));assert r['future_median_used_for_prediction']=='False'
 sums={}
 for r in rows('density_error_contribution.csv'):
  p,m,h=selection(r);obs=a[p+'_density'][m];pred=a[p+'_'+r['case']+'_'+r['method']][m];ab=(pred-obs)**2;rel=((pred-obs)/obs)**2;N=len(obs);kind=r['group_type'];group=r['group'];lat=abs(a[p+'_latitude'][m]);bb=np.where(lat<30,0,np.where(lat<60,1,2));qedges=np.quantile(obs,[0,.2,.4,.6,.8,1]);bins=np.searchsorted(qedges[1:-1],obs,side='right')
  if kind=='density':g=bins==int(group[1])-1
  elif kind=='latitude':g=bb==['low','mid','high'].index(group)
  elif kind=='time':lo,hi=group[:-1].split('_');g=(h[m]>=float(lo))&(h[m]<float(hi))
  else:q,reg=group.split('_');g=(bins==int(q[1])-1)&(bb==['low','mid','high'].index(reg))
  assert g.sum()==int(r['N']);close(r['absolute_SS'],sum(map(float,ab[g])));close(r['relative_SS'],sum(map(float,rel[g])));close(r['absolute_MSE_contribution'],np.sum(ab[g])/N);close(r['relative_MSE_contribution'],np.sum(rel[g])/N)
  key=(r['date'],r['cutoff'],r['case'],r['window'],r['method'],kind);sums.setdefault(key,[0.,0.]);sums[key][0]+=float(r['absolute_MSE_contribution']);sums[key][1]+=float(r['relative_MSE_contribution'])
 for r in rows('reproduced_frozen_metrics.csv'):
  p,m,_=selection(r);o=a[p+'_density'][m];pred=a[p+'_'+r['case']+'_'+r['method']][m];diff=pred-o;rel=diff/o
  for k,value in [('RMSE',np.sqrt(np.mean(diff**2))),('relative_RMS',np.sqrt(np.mean(rel**2))),('relative_P95',np.quantile(abs(rel),.95)),('MAE',np.mean(abs(diff))),('bias',np.mean(diff)),('relative_bias',np.mean(rel))]:close(r[k],value)
  for kind in ['density','latitude','time','density_latitude']:
   x=sums[(r['date'],r['cutoff'],r['case'],r['window'],r['method'],kind)];close(x[0],np.mean(diff**2));close(x[1],np.mean(rel**2))
 # Old four criteria only; no joint score is invented for a new forecast.
 joint=[]
 for tag,day,aliases in [('causal_density_late_day_v1','24',{'Adaptive18':'GlobalAdaptive'}),('causal_density_latitude_correction_v1','23',{'GlobalAdaptive18':'GlobalAdaptive','LatitudeAdaptive18':'LatitudeAdaptive'})]:
  path=R/'experiments'/tag/'joint_assessment.csv'
  for r in csv.DictReader(path.open()):
   if not r['window'].startswith('future_') or r['case'] not in ['B14','A7','B7'] or r['method'] not in aliases:continue
   date=r['year']+'-03-'+day;new=dict(date=date,cutoff='18',window=r['window'],case=r['case']);p,m,_=selection(new);o=a[p+'_density'][m];raw=a[p+'_'+r['case']+'_Raw'][m];pred=a[p+'_'+r['case']+'_'+aliases[r['method']]][m];low=abs(a[p+'_latitude'][m])<30;er=(raw-o)/o;ec=(pred-o)/o;flags=[np.mean((pred-o)**2)<np.mean((raw-o)**2),np.mean(ec**2)<np.mean(er**2),np.quantile(abs(ec),.95)<=np.quantile(abs(er),.95),abs(np.mean(ec[low]))<=abs(np.mean(er[low]))]
   for k,v in zip(['RMSE_BENEFIT','RELATIVE_RMS_BENEFIT','TAIL_NONWORSENED','LOW_LATITUDE_BIAS_NONWORSENED'],flags):assert r[k].lower()==str(bool(v)).lower(),(tag,k)
   joint.append(dict(prior_tag=tag,date=date,case=r['case'],window=r['window'],method=r['method'],four_flags_unchanged=True,prior_JOINT=r['JOINT_NO_REGRET']))
 with (F/'legacy_joint_verification.csv').open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=joint[0],lineterminator='\n');w.writeheader();w.writerows(joint)
 coords=rows('coordinate_roundtrip_tests.csv');xyz=np.load(F/'coordinate_vectors_local.npz')['XYZ_m'];worst=0.
 for i,v in enumerate(xyz):
  for ell,code in [('GRS80',2),('WGS84',1)]:
   lon,lat,h=inverse(v,ell);lo,la,hh=erfa.gc2gd(code,v);err=abs(h-hh);assert err<=1e-5 and abs(lat-np.rad2deg(la))<=5e-10;worst=max(worst,err)
 for x in index:
  p=x['prefix'];cut=np.datetime64(x['date']+f"T{x['cutoff']:02d}:00:00");t=a[p+'_utc'];history=t<cut;future=t>=cut;assert not np.intersect1d(t[history],t[future]).size and history.sum()==360 and future.sum()==720
  if x['date'].endswith('23') and x['cutoff']==6:assert all(v==['Raw'] for v in x['methods'].values())
 from prepare_residual_representativeness_v1 import sha
 src=json.loads((F/'source_manifest.json').read_text())
 for n,h in src['protected_SHA256'].items():assert sha(R/n)==h,n
 result=dict(PASS=True,median_stat_rows=nc,median_gap_rows=len(gaps),contribution_rows=len(rows('density_error_contribution.csv')),old_joint_rows_reverified=len(joint),coordinate_rows=len(coords),coordinate_ERFA_height_crosscheck_max_m=worst,history_future_IDs_disjoint=True,no_future_median_forecast=True,no_new_correction_fit=True,old_SHA_unchanged=True,rtol=1e-13,atol=0,wall_s=time.perf_counter()-start)
 with (F/'independent_verification.json').open('x') as f:json.dump(result,f,indent=2)
 print('Independent diagnostics/identities/coordinates/old results verified.',flush=True)
if __name__=='__main__':verify()
