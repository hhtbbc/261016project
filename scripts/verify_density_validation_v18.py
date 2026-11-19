"""Independent V18 arithmetic and native eight-column reconstruction, no refitting."""
from pathlib import Path
import sys,json,csv,math,hashlib,datetime,time
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R),str(R/'src'),str(R/'scripts')]
import numpy as np,cdflib
from netCDF4 import Dataset
from astropy.time import Time
from run_density_validation_v18 import F,OLD,CDF,DAY,sha,load,rows,dump

def close(x,y):assert np.isclose(float(x),float(y),rtol=1e-13,atol=0),(x,y)
def median(x):
 s=sorted(map(float,x));n=len(s);return s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2

def verify():
 start=time.perf_counter();a=np.load(F/'matched_local.npz');t=a['utc'];o=a['density'];p=a['raw'];lat=a['latitude'];bands=np.where(abs(lat)<30,0,np.where(abs(lat)<60,1,2));params=load(F/'correction_parameters.json')['parameters'];source=load(F/'source_manifest.json');checks=[]
 with cdflib.CDF(CDF) as c:
  np.testing.assert_array_equal(cdflib.cdfepoch.to_datetime(c.varget('time')),t);np.testing.assert_array_equal(c.varget('density'),o);flags=c.varget('validity_flag');assert len(o)==2880 and (flags==0).all() and np.isfinite(o).all() and (o>0).all()
 assert sha(CDF)==source['CDF']['SHA256'];assert sha(F/'correction_parameters.json')==load(F/'parameter_freeze_receipt.json')['SHA256'];assert load(F/'correction_parameters.json')['protocol_SHA256']==sha(F/'frozen_protocol.json')
 count=0
 for hour in [6,18]:
  cut=np.datetime64(DAY+f'T{hour:02d}');m=(t>=cut-np.timedelta64(3,'h'))&(t<cut);assert m.sum()==360 and not (m&(t>=cut)).any();hist=np.log(o[m])-np.log(p[m]);g=params[f'GlobalAdaptive{hour:02d}'];close(median(hist),g['b']);close(math.exp(g['b']),g['multiplier']);assert g['N']==int(m.sum());count+=1
  # Each poison copy starts with original data, independently of the other cutoff.
  poisoned=o.copy();poisoned[t>=cut]*=1e20;assert median(np.log(poisoned[m])-np.log(p[m]))==median(hist)
  if hour==18:
   for i,k in enumerate(['low','mid','high']):
    sel=m&(bands==i);g=params['LatitudeAdaptive18'][k];assert g['N']==int(sel.sum())
    if sel.sum()>=30:close(median(np.log(o[sel])-np.log(p[sel])),g['b']);close(math.exp(g['b']),g['multiplier']);assert median(np.log(poisoned[sel])-np.log(p[sel]))==median(np.log(o[sel])-np.log(p[sel]));count+=1
    else:assert g['b'] is None
 # Independent native NetCDF array access, calendar and explicit dtype sentinels.
 frames=[]
 for ent in source['target_models']:
  path=R/ent['path'];assert sha(path)==ent['SHA256']
  with Dataset(path) as n:
   n.set_auto_mask(False);gridlat=np.asarray(n['lat'][:]);gridlon=np.asarray(n['lon'][:])
   for j,(y,mt) in enumerate(zip(n['year'][:],n['mtime'][:])):
    dt=datetime.datetime(int(y),1,1)+datetime.timedelta(days=int(mt[0])-1,hours=int(mt[1]),minutes=int(mt[2]));tt=np.datetime64(dt,'ns')
    if np.datetime64(DAY)<=tt<=np.datetime64('2022-03-26'):
     zz=[]
     for key,factor in [('ZG',.01),('DEN',1000.)]:
      v=n[key];x=np.asarray(v[j]);assert v.dimensions==('time','ilev','lat','lon');assert np.isfinite(x).all()
      for attr in ['_FillValue','missing_value']:
       if hasattr(v,attr):assert not np.any(x==np.asarray(getattr(v,attr),dtype=x.dtype))
      zz.append(x.astype(float)*factor)
     assert (zz[1]>0).all() and (np.diff(zz[0],axis=0)>0).all();frames.append((tt,zz[0],zz[1]))
 frames.sort(key=lambda x:x[0]);assert len(frames)==25;assert np.all(np.diff([x[0] for x in frames])==np.timedelta64(1,'h'))
 # Coordinate values come from independently constructed queries (same frozen Map-A assumption).
 from atmosphere.causal_observation_operator import map_a_queries
 queries=map_a_queries(t,lat,a['longitude'],a['altitude']);ft=Time(np.array([x[0] for x in frames]));sec=np.array((ft-ft[0]).sec);ind=[];columns=0
 for i,q in enumerate(queries):
  xx=float((q.utc-ft[0]).sec);kk=int(np.clip(np.searchsorted(sec,xx,side='right')-1,0,23));yy=q.latitude_deg;ll=(q.longitude_deg-gridlon[0])%360+gridlon[0]
  assert gridlat[0]<=yy<=gridlat[-1] and sec[0]<=xx<=sec[-1]
  jj=int(np.clip(np.searchsorted(gridlat,yy,side='right')-1,0,len(gridlat)-2));ii=int(np.searchsorted(gridlon,ll,side='right')-1);ii%=len(gridlon);ii2=(ii+1)%len(gridlon);lon0=gridlon[ii];lon1=gridlon[ii2]+(360 if ii2==0 else 0)
  if ll<lon0:ll+=360
  wx=(ll-lon0)/(lon1-lon0);wy=(yy-gridlat[jj])/(gridlat[jj+1]-gridlat[jj]);wt=(xx-sec[kk])/(sec[kk+1]-sec[kk]);s=0.
  for ki,tw in [(kk,1-wt),(kk+1,wt)]:
   for ji,yw in [(jj,1-wy),(jj+1,wy)]:
    for li,xw in [(ii,1-wx),(ii2,wx)]:
     z=frames[ki][1][:,ji,li];rho=frames[ki][2][:,ji,li];assert z[0]<=q.height_wgs84_m<=z[-1];s+=tw*yw*xw*float(np.exp(np.interp(q.height_wgs84_m,z,np.log(rho))));columns+=1
  close(s,p[i]);ind.append(s)
 # Independent prediction arithmetic, never read the main corrected arrays as verification inputs.
 independent_predictions={}
 for h in [6,18]:
  independent_predictions[h,'Raw']=p;independent_predictions[h,f'GlobalAdaptive{h:02d}']=p*math.exp(params[f'GlobalAdaptive{h:02d}']['b'])
  if h==18:
   independent_predictions[h,'Stale06']=p*math.exp(params['GlobalAdaptive06']['b']);v=p.copy()
   for i,k in enumerate(['low','mid','high']):v[bands==i]*=math.exp(params['LatitudeAdaptive18'][k]['b'])
   independent_predictions[h,'LatitudeAdaptive18']=v
 scores={};nrows=0;bounds={'analysis':(-3,0),'future_1h':(0,1),'future_3h':(0,3),'future_6h':(0,6),'block_0_1h':(0,1),'block_1_3h':(1,3),'block_3_6h':(3,6)}
 for row in rows(F/'metrics.csv')+rows(F/'region_metrics.csv'):
  h=int(row['cutoff']);d=(t-np.datetime64(DAY+f'T{h:02d}'))/np.timedelta64(1,'h');lo,hi=bounds[row['window']];m=(d>=lo)&(d<hi)
  if row['region']!='all':m&=bands==['low','mid','high'].index(row['region'])
  assert int(m.sum())==int(row['n']);pred=independent_predictions[h,row['method']];np.testing.assert_allclose(a[f'{h}_{row["method"]}'],pred,rtol=1e-13,atol=0)
  if m.sum()<30:assert row['status']!='OK';continue
  pp=pred[m];oo=o[m];err=pp-oo;r=err/oo;v=dict(MAE=np.mean(abs(err)),RMSE=np.sqrt(np.mean(err**2)),bias=np.mean(err),relative_RMS=np.sqrt(np.mean(r**2)),relative_P95=np.quantile(abs(r),.95),relative_bias=np.mean(r),log_RMS=np.sqrt(np.mean(np.log(pp/oo)**2)),Pearson=np.corrcoef(pp,oo)[0,1],max_abs=np.max(abs(err)))
  for k,value in v.items():close(row[k],value)
  scores[h,row['window'],row['region'],row['method']]=v;nrows+=1
 nj=0
 for row in rows(F/'joint_assessment.csv'):
  h=int(row['cutoff']);w=row['window'];met=row['method'];r=scores[h,w,'all','Raw'];c=scores[h,w,'all',met];rl=scores[h,w,'low','Raw'];cl=scores[h,w,'low',met];flags=[c['RMSE']<r['RMSE'],c['relative_RMS']<r['relative_RMS'],c['relative_P95']<=r['relative_P95'],abs(cl['relative_bias'])<=abs(rl['relative_bias'])]
  for key,value in zip(['RMSE_BENEFIT','RELATIVE_RMS_BENEFIT','TAIL_NONWORSENED','LOW_LATITUDE_BIAS_NONWORSENED'],flags):assert row[key]==str(bool(value))
  assert row['JOINT_NO_REGRET']==('PASS' if all(flags) else 'FAIL');nj+=1
 cov=rows(F/'coverage.csv')
 for h in [6,18]:
  for w in bounds:
   selected=[r for r in cov if int(r['cutoff'])==h and r['window']==w];assert len(set(x['common_ID_SHA256'] for x in selected))==1
 for key,digest in source['reference_2021'].items():assert sha(OLD/key)==digest
 assert load(F/'future_poison_test.json')['PASS']
 dump('independent_verification.json',dict(PASS=True,rtol=1e-13,atol=0,CDF_direct_records=2880,quality_valid=2880,coefficients_independently_verified=count,Stale06_same_day=True,independent_future_poison=True,metric_rows=nrows,joint_rows=nj,common_ID_equal=True,model_frames_independently_read=25,model_values_independently_reconstructed=2880,column_checks=columns,query_max_relative_difference=float(np.max(abs(np.array(ind)/p-1))),reference_2021_unchanged=True,parameter_SHA_unchanged=True,wall_s=time.perf_counter()-start))
 print('V18 INDEPENDENT VERIFICATION PASS',flush=True)
if __name__=='__main__':verify()
