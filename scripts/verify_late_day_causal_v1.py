"""Independent CDF/metrics/bin/joint checks. No new model queries or fitting."""
from pathlib import Path
import sys,json,csv,time,resource
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np,cdflib
from PIL import Image
from prepare_fourcastden_swarm_observation_v1 import sha
F=ROOT/'experiments/causal_density_late_day_v1'
def main():
 start=time.perf_counter();src=json.loads((F/'source_manifest.json').read_text());params=json.loads((F/'correction_parameters.json').read_text());pr=json.loads((F/'frozen_protocol.json').read_text());assert params['protocol_SHA256']==sha(F/'frozen_protocol.json');z=np.load(F/'matched_local.npz');rows=list(csv.DictReader((F/'metrics.csv').open()));bins=list(csv.DictReader((F/'density_bin_decomposition.csv').open()));joints=list(csv.DictReader((F/'joint_assessment.csv').open()));regions=list(csv.DictReader((F/'region_metrics.csv').open()));checked=0;binchecked=0;jchecked=0;summaries=[];point=[]
 for y in ['2021','2022']:
  t=z[y+'_utc'];o=z[y+'_density'];cut=np.datetime64(y+'-03-24T18');h=(t-np.datetime64(y+'-03-24'))/np.timedelta64(1,'h');masks={'analysis':(h>=15)&(h<18),**{f'future_{n}h':(t>=cut)&(t<cut+np.timedelta64(n,'h')) for n in [1,3,6]},'block_0_1h':(h>=18)&(h<19),'block_1_3h':(h>=19)&(h<21),'block_3_6h':(h>=21)&(h<24)};assert masks['analysis'].sum()==360 and masks['future_6h'].sum()==720
  with cdflib.CDF(ROOT/src['observations'][y]['source_file']) as c:
   tt=cdflib.cdfepoch.to_datetime(c.varget('time'));idx=np.searchsorted(tt,t);np.testing.assert_array_equal(tt[idx],t)
   for name in ['density','latitude','longitude','altitude','validity_flag']:np.testing.assert_array_equal(c.varget(name)[idx],z[y+'_'+name])
  other='2022' if y=='2021' else '2021';assert params['B14_applied_b'][y]['CrossYearTransfer18']==params['adaptive18'][other]['B14']['b18'];assert params['B14_applied_b'][y]['Stale06']==pr['stale06_coefficients'][y]
  for c in ['B14','A7','B7']:
   raw=z[y+'_'+c+'_Raw'];e=np.log(o[masks['analysis']])-np.log(raw[masks['analysis']]);assert float(np.median(e))==params['adaptive18'][y][c]['b18']
   for method in ['Raw','Adaptive18']+(['Stale06','CrossYearTransfer18'] if c=='B14' else []):
    pred=z[y+'_'+c+'_'+method];b=0 if method=='Raw' else (params['adaptive18'][y][c]['b18'] if method=='Adaptive18' else params['B14_applied_b'][y][method]);np.testing.assert_array_equal(pred,raw*np.exp(b));assert np.isfinite(pred).all() and np.all(pred>0)
    for window,m in masks.items():
     obs=o[m];p=pred[m];err=p-obs;rel=p/obs-1;N=len(p);row=next(x for x in rows if x['year']==y and x['case']==c and x['method']==method and x['window']==window)
     for key,v in {'MAE':np.mean(abs(err)),'RMSE':np.sqrt(np.mean(err**2)),'bias':np.mean(err),'relative_RMS':np.sqrt(np.mean(rel**2)),'relative_P95':np.percentile(abs(rel),95),'relative_bias':np.mean(rel),'log_RMS':np.sqrt(np.mean(np.log(p/obs)**2))}.items():assert np.isclose(float(row[key]),v,rtol=1e-13,atol=0),(y,c,method,window,key)
     assert np.isclose(np.mean(err**2),np.mean(obs**2*rel**2),rtol=1e-13,atol=0);checked+=1
     if method!='Raw':
      rawrow=next(x for x in rows if x['year']==y and x['case']==c and x['method']=='Raw' and x['window']==window);lo={x['method']:x for x in regions if x['year']==y and x['case']==c and x['window']==window and x['region']=='low'};j=next(x for x in joints if x['year']==y and x['case']==c and x['method']==method and x['window']==window)
      if lo['Raw']['status']=='OK' and lo[method]['status']=='OK':
       flags=[float(row['RMSE'])<float(rawrow['RMSE']),float(row['relative_RMS'])<float(rawrow['relative_RMS']),float(row['relative_P95'])<=float(rawrow['relative_P95']),abs(float(lo[method]['relative_bias']))<=abs(float(lo['Raw']['relative_bias']))];assert (j['JOINT_NO_REGRET']=='True')==all(flags)
       for key,val in zip(['RMSE_BENEFIT','RELATIVE_RMS_BENEFIT','TAIL_NONWORSENED','LOW_LATITUDE_BIAS_NONWORSENED'],flags):assert (j[key]=='True')==val
      else:assert j['JOINT_NO_REGRET']=='False' and j['status'].startswith('N/A')
      jchecked+=1
     if window=='analysis' or window=='block_0_1h':continue
     rr=[x for x in bins if x['year']==y and x['case']==c and x['method']==method and x['window']==window];assert len(rr)==5 and sum(int(x['N']) for x in rr)==N
     assert np.isclose(sum(float(x['absolute_MSE_contribution']) for x in rr),np.mean(err**2),rtol=1e-13,atol=0);assert np.isclose(sum(float(x['relative_MSE_contribution']) for x in rr),np.mean(rel**2),rtol=1e-13,atol=0)
     for share in ['absolute_SSE_share','relative_SSE_share']:assert np.isclose(sum(float(x[share]) for x in rr),1,rtol=1e-13,atol=0)
     binchecked+=1
    if c=='B14' and method!='Raw':
     m=masks['future_6h'];a=abs(raw[m]-o[m]);b=abs(pred[m]-o[m]);point.append(dict(year=y,method=method,N=int(m.sum()),improved=int((b<a).sum()),worsened=int((b>a).sum()),unchanged=int((b==a).sum())))
  for window in ['future_1h','future_3h','future_6h','block_1_3h','block_3_6h']:
   for method in ['Adaptive18','Stale06','CrossYearTransfer18']:
    rr={int(x['quintile']):x for x in bins if x['year']==y and x['case']=='B14' and x['window']==window and x['method']=='Raw'};cc={int(x['quintile']):x for x in bins if x['year']==y and x['case']=='B14' and x['window']==window and x['method']==method};totalgain=sum(float(rr[k]['absolute_MSE_contribution'])-float(cc[k]['absolute_MSE_contribution']) for k in rr)
    for k in rr:summaries.append(dict(year=y,window=window,method=method,quintile=k,N=rr[k]['N'],observed_mean_kg_m3=rr[k]['observed_mean_kg_m3'],raw_absolute_SSE_share=rr[k]['absolute_SSE_share'],raw_relative_SSE_share=rr[k]['relative_SSE_share'],absolute_MSE_reduction=float(rr[k]['absolute_MSE_contribution'])-float(cc[k]['absolute_MSE_contribution']),fraction_of_net_absolute_MSE_reduction=(float(rr[k]['absolute_MSE_contribution'])-float(cc[k]['absolute_MSE_contribution']))/totalgain if totalgain else None,relative_MSE_increase=float(cc[k]['relative_MSE_contribution'])-float(rr[k]['relative_MSE_contribution'])))
 for p in (F/'figures').glob('*.png'):
  with Image.open(p) as im:im.verify()
 assert len(list((F/'figures').glob('*.png')))==9
 for n,h in src['protected_inputs'].items():assert sha(ROOT/n)==h,n
 with (F/'density_bin_gain_summary.csv').open('x',newline='') as out:w=csv.DictWriter(out,fieldnames=list(summaries[0]),lineterminator='\n');w.writeheader();w.writerows(summaries)
 with (F/'independent_verification.json').open('x') as out:json.dump(dict(PASS=True,exact_CDF_records=2160,metric_rows_checked=checked,bin_partitions_checked=binchecked,joint_rows_checked=jchecked,all_weight_identities_PASS=True,all_coefficients_exact_history_or_frozen_origins=True,corrected_nonpositive=0,corrected_nonfinite=0,pointwise_B14=point,old_SHA_unchanged=len(src['protected_inputs']),figures=9,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024),out,indent=2)
 print('INDEPENDENT LATE DAY PASS',checked,binchecked,jchecked,flush=True)
if __name__=='__main__':main()
