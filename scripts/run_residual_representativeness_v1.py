"""One supervised read-only diagnostic. No fitting, new correction or datum release."""
from pathlib import Path
import sys,json,csv,time,resource,hashlib,itertools,warnings
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R),str(R/'src'),str(R/'scripts')]
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from astropy.coordinates import EarthLocation
from astropy.time import Time
import astropy.units as u
from observations.density_catalog import read_swarm_pod
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from atmosphere.causal_observation_operator import map_a_queries,observe_map_a
from atmosphere.provisional_coordinate_adapter import ProvisionalCoordinateAdapter,A_WGS84
from evaluation.late_day_correction import RollingOrigin,diagnostic_quintiles,joint_flags
from evaluation.causal_density_latitude import latitude_band
from evaluation.swarm_crossyear import metric_row
from evaluation.residual_representativeness import *
from prepare_residual_representativeness_v1 import sha
F=R/'experiments/thermosphere_residual_representativeness_v1';CASES=['B14','A7','B7'];FIELDS=['utc','density','latitude','longitude','altitude','quality','validity_flag'];BANDS=['all','low','mid','high']
def load(p):return json.loads(Path(p).read_text())
def dump(n,x):
 with (F/n).open('x') as f:json.dump(x,f,indent=2,allow_nan=False)
def table(n,rows):
 with (F/n).open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
def ids(utc):return hashlib.sha256(np.asarray(utc,dtype='datetime64[ns]').astype('<i8').tobytes()).hexdigest()
def save(fig,name,coordinate=False):
 fig.text(.5,.005,'NUMERICAL CONSISTENCY ONLY / NOT DATUM VALIDATION' if coordinate else 'PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED',ha='center',fontsize=7);fig.tight_layout(rect=(0,.035,1,.98));fig.savefig(F/'figures'/name,dpi=145);plt.close(fig)
def main():
 start=time.perf_counter();cpu=time.process_time();s=load(F/'source_manifest.json');pr=load(F/'frozen_protocol.json');assert sha(F/'frozen_protocol.json')==load(F/'protocol_sha256.json')['SHA256']
 for n,h in pr['code_SHA256'].items():assert sha(R/n)==h,n
 for n,h in s['protected_SHA256'].items():assert sha(R/n)==h,n
 warnings.showwarning=lambda message,category,filename,lineno,file=None,line=None: None # only library warning text; recorded count below
 warning_records=[]
 def capture(message,category,filename,lineno,file=None,line=None):warning_records.append(dict(category=category.__name__,message=str(message),file=filename,line=lineno))
 warnings.showwarning=capture;obs={};packs={};coverage_rows=[];query_rows=[];probes=[]
 for day,src in s['observations'].items():
  _,a,_=read_swarm_pod(R/src['path'],R/s['hapi']['path'],src['SHA256'],satellite='A');assert len(a['utc'])==2880 and a['quality'].all();obs[day]=a
 tagbase=R/'experiments';latcache=np.load(tagbase/'causal_density_latitude_correction_v1/matched_local.npz');early=np.load(tagbase/'causal_density_latitude_correction_v1/early_matches_local.npz');late=np.load(tagbase/'causal_density_late_day_v1/matched_local.npz');v11=np.load(tagbase/'cross_year_causal_density_validation_v1/matched_local.npz');v10=np.load(tagbase/'causal_density_correction_v1/matched_local.npz');v10p=load(tagbase/'causal_density_correction_v1/correction_parameters.json')['parameters']
 with (F/'reconstruction_queries_local.jsonl').open('x') as trace:
  for day in pr['days']:
   y=day[:4];d=day[-2:]
   for hour in [6,18]:
    a=obs[day];masks=RollingOrigin(day,hour).masks(a['utc']);sel=masks['analysis']|masks['future_6h'];a={k:v[sel] for k,v in a.items()};assert len(a['utc'])==1080;pred={};ctx=dict(date=day,cutoff=hour)
    for case in CASES:
     if d=='24':
      c=late if hour==18 else (v11 if y=='2021' else v10);prefix=y+'_' if hour==18 else ('' if y=='2021' else 'A_')
      for k in FIELDS:assert np.array_equal(a[k],c[prefix+k])
      raw=c[f'{y}_{case}_Raw'] if hour==18 else (c[case+'_Raw'] if y=='2021' else c[case+'_A']);globalpred=c[f'{y}_{case}_Adaptive18'] if hour==18 else (c[case+'_Adaptive'] if y=='2021' else raw*v10p[case]['density_multiplier']);pred[case]={'Raw':raw,'GlobalAdaptive':globalpred};origin='frozen v12' if hour==18 else ('frozen v11' if y=='2021' else 'frozen v10');newn=0
     elif hour==18:
      for k in FIELDS:assert np.array_equal(a[k],latcache[y+'_'+k])
      pred[case]={'Raw':latcache[f'{y}_{case}_Raw'],'GlobalAdaptive':latcache[f'{y}_{case}_GlobalAdaptive18'],'LatitudeAdaptive':latcache[f'{y}_{case}_LatitudeAdaptive18']};origin='frozen v13-B';newn=0
     else:
      raw=np.full(1080,np.nan);hist=RollingOrigin(day,hour).masks(a['utc'])['analysis']
      if case=='B14':
       for k in FIELDS:assert np.array_equal(a[k][hist],early[y+'_'+k])
       raw[hist]=early[y+'_model'];need=~hist;first=6
      else:need=np.ones(1080,bool);first=3
      st=s['models'][y][case];p=R/st['files'][0]['path'];provider=HourlyTiegcmObservation([p],{p.name:st['files'][0]['SHA256']},day+f'T{first:02d}:00:00',day+'T12:00:00',day+'_'+case);assert len(provider.records)==13-first;ii=np.flatnonzero(need);queries=map_a_queries(a['utc'][need],a['latitude'][need],a['longitude'][need],a['altitude'][need]);t0=time.perf_counter()
      for qindex,(j,q) in enumerate(zip(ii,queries)):
       result,coord=observe_map_a(provider,q);assert result.valid and len(result.metadata['columns'])==8,(day,case,int(j),result.reason);raw[j]=result.rho_kg_m3;trace.write(json.dumps(dict(date=day,case=case,UTC=str(a['utc'][j]),valid=result.valid,reason=result.reason,coordinates=coord,metadata=result.metadata))+'\n')
       if qindex in [0,len(ii)//2,len(ii)-1]:
        md=result.metadata;w=md['weights'];weights=np.array([1-w['time'],w['time']])[:,None,None]*np.array([1-w['latitude'],w['latitude']])[None,:,None]*np.array([1-w['longitude'],w['longitude']])[None,None,:];values=[]
        for col in md['columns']:
         k=next(k for k,(_,pa,rec) in enumerate(provider.records) if pa.name==col['file'] and rec==col['record']);z,rho=provider._column(k,col['lat_index'],col['lon_index']);values.append(np.exp(np.interp(coord['model_zg_m'],z,np.log(rho))))
        direct=float(np.sum(weights*np.array(values).reshape(2,2,2)));assert np.isclose(direct,result.rho_kg_m3,rtol=1e-13,atol=0);probes.append(dict(date=day,case=case,index=int(j),relative_difference=abs(direct/result.rho_kg_m3-1)))
      newn=int(need.sum());query_rows.append(dict(date=day,case=case,queries=newn,valid=newn,failed=0,eight_columns=True,extrapolation=False,frames=len(provider.records),wall_s=time.perf_counter()-t0));provider.close();pred[case]={'Raw':raw};origin='B14 history frozen v13 early cache; missing future rebuilt' if case=='B14' else 'missing03-23 early history/future rebuilt';print('RECONSTRUCTION PASS',day,case,newn,flush=True)
     positive(a['density'],pred[case]['Raw']);coverage_rows.append(dict(**ctx,case=case,N=1080,history_N=360,future_6h_N=720,quality_valid=1080,query_valid=1080,coverage=1.,new_queries=newn,provenance=origin,corrected_prediction_methods=';'.join(list(pred[case])[1:]) or 'N/A_NO_FROZEN_PREDICTION'))
    packs[(day,hour)]=dict(a=a,pred=pred)
 dump('reconstruction_audit.json',dict(cases=query_rows,probes=probes,new_queries=sum(x['queries'] for x in query_rows),no_operator_changes=True,old_caches_preferred=True));table('coverage.csv',coverage_rows)
 # All requested representativeness diagnostics, without making a forecast from a median.
 stats=[];gaps=[];orbit=[];blocks=[];errors=[];metrics=[];tails=[];oldchecks=[]
 for (day,hour),pack in packs.items():
  a=pack['a'];ms=RollingOrigin(day,hour).masks(a['utc']);bb=latitude_band(a['latitude']);regions={'all':np.ones(1080,bool),**{name:bb==i for i,name in enumerate(BANDS[1:])}};cut=np.datetime64(day+f'T{hour:02d}:00:00');relhours=(a['utc']-cut)/np.timedelta64(1,'h');hist=ms['analysis'];ctx=dict(date=day,cutoff=hour)
  for case,pp in pack['pred'].items():
   e=residual(a['density'],pp['Raw']);hs={reg:statistics(e[hist&rm]) for reg,rm in regions.items()}
   for win in ['analysis','future_1h','future_3h','future_6h']:
    for reg,rm in regions.items():
     sel=ms[win]&rm;st=statistics(e[sel]);stats.append(dict(**ctx,case=case,window=win,region=reg,**st));cv=coverage(a['latitude'][sel],a['altitude'][sel]);orbit.append(dict(**ctx,case=case,window=win,region=reg,**cv,first_UTC=str(a['utc'][sel][0]) if sel.any() else None,last_UTC=str(a['utc'][sel][-1]) if sel.any() else None,sample_ID_SHA256=ids(a['utc'][sel])))
     if win!='analysis':
      h=hs[reg];ok=st['status']==h['status']=='OK';gaps.append(dict(**ctx,case=case,window=win,region=reg,history_N=h['N'],future_N=st['N'],status='OK' if ok else 'N/A_INSUFFICIENT_SAMPLES',b_H=h['median'],b_F=st['median'],delta_b=st['median']-h['median'] if ok else None,median_sign_flip=bool(h['median']*st['median']<0) if ok else None,history_std=h['std'],future_std=st['std'],history_MAD=h['MAD'],future_MAD=st['MAD'],history_positive_fraction=h['positive_fraction'],future_positive_fraction=st['positive_fraction'],histogram_overlap=overlap(e[hist&rm],e[sel]),future_median_used_for_prediction=False))
   for lo in range(-3,6):
    mask=(relhours>=lo)&(relhours<lo+1)
    for reg,rm in regions.items():blocks.append(dict(**ctx,case=case,hours_from_cutoff_start=lo,hours_from_cutoff_stop=lo+1,region=reg,**statistics(e[mask&rm])))
   for win in ['future_1h','future_3h','future_6h']:
    sel=ms[win];o=a['density'][sel];idx,edges=diagnostic_quintiles(o);latb=bb[sel];rh=relhours[sel];groups={**{('density',f'Q{i+1}'):idx==i for i in range(5)},**{('latitude',r):latb==i for i,r in enumerate(BANDS[1:])},**{('time',f'{lo}_{hi}h'):(rh>=lo)&(rh<hi) for lo,hi in [(0,1),(1,3),(3,6)]},**{('density_latitude',f'Q{i+1}_{r}'):(idx==i)&(latb==j) for i in range(5) for j,r in enumerate(BANDS[1:])}}
    for method,p in pp.items():
     score=metric_row(p,a['density'],a['quality'],np.ones(1080,bool),sel);metrics.append(dict(**ctx,case=case,window=win,method=method,**score));r=(p[sel]-o)/o;assert np.isclose(np.mean((p[sel]-o)**2),np.mean(o**2*r**2),rtol=1e-12,atol=0)
     for (kind,name),g in groups.items():errors.append(dict(**ctx,case=case,window=win,method=method,group_type=kind,group=name,small_group_note='DESCRIPTIVE_ARITHMETIC_ONLY_N_LT30' if g.sum()<30 else 'N_GE30_NOT_INDEPENDENT',**contribution(p[sel],o,g)))
     rawr=(pp['Raw'][sel]-o)/o;tail=abs(r)>=np.quantile(abs(r),.95);tails.append(dict(**ctx,case=case,window=win,method=method,N=len(o),relative_P95=float(np.quantile(abs(r),.95)),tail_N=int(tail.sum()),tail_relative_SS_fraction=float((r[tail]**2).sum()/(r*r).sum()),fraction_exceeding_Raw_P95=float((abs(r)>np.quantile(abs(rawr),.95)).mean()),tail_low_latitude_fraction=float((latb[tail]==0).mean()),tail_lowest_two_density_bins_fraction=float((idx[tail]<2).mean())))
    # Verify only forecasts already made/frozen in prior experiments, not a new method.
    if day.endswith('24'):
     tag='causal_density_late_day_v1' if hour==18 else ('cross_year_causal_density_validation_v1' if day.startswith('2021') else 'causal_density_correction_v1');aliases={'Raw':'Raw','GlobalAdaptive':'Adaptive18' if hour==18 else 'Adaptive'}
     if tag=='causal_density_correction_v1':aliases={'Raw':'raw','GlobalAdaptive':'corrected'}
    elif hour==18:tag='causal_density_latitude_correction_v1';aliases={'Raw':'Raw','GlobalAdaptive':'GlobalAdaptive18','LatitudeAdaptive':'LatitudeAdaptive18'}
    else:continue
    prior=list(csv.DictReader((tagbase/tag/'metrics.csv').open()))
    for method,alias in aliases.items():
     matches=[r for r in prior if r['case']==case and r['window']==win and r['region']=='all' and r['method']==alias and (r.get('satellite','A')=='A') and r.get('year',day[:4])==day[:4]];assert len(matches)==1,(tag,case,win,alias)
     old=matches[0];new=next(x for x in reversed(metrics) if (x['date'],x['cutoff'],x['case'],x['window'],x['method'])==(day,hour,case,win,method))
     for key in ['RMSE','relative_RMS','relative_P95','MAE','bias','log_RMS','relative_bias']:assert np.isclose(new[key],float(old[key]),rtol=1e-13,atol=0),(tag,key,new[key],old[key])
     oldchecks.append(dict(**ctx,case=case,window=win,method=method,prior_tag=tag,prior_method=alias,metrics_unchanged=True))
 table('history_future_residual_statistics.csv',stats);table('history_future_median_gap.csv',gaps);table('latitude_representativeness.csv',[x for x in gaps if x['region']!='all']);table('orbit_coverage_comparison.csv',orbit);table('time_block_residual_statistics.csv',blocks);table('density_error_contribution.csv',errors);table('reproduced_frozen_metrics.csv',metrics);table('tail_diagnostics.csv',tails);table('legacy_metric_reproduction.csv',oldchecks)
 # Preserve full paired values only in ignored local arrays for independent verification.
 arr={};index=[]
 for (day,hour),pk in packs.items():
  prefix='D'+day.replace('-','')+f'H{hour:02d}';index.append(dict(date=day,cutoff=hour,prefix=prefix,methods={c:list(p) for c,p in pk['pred'].items()}))
  for k,v in pk['a'].items():arr[prefix+'_'+k]=v
  for c,pp in pk['pred'].items():
   for method,p in pp.items():arr[prefix+'_'+c+'_'+method]=p
 np.savez_compressed(F/'matched_diagnostics_local.npz',**arr);dump('diagnostic_case_index.json',index)
 # Independent ellipsoid formulas versus existing library and actual Map-A adapt.
 cr=[];vectors=[];tol=pr['coordinate_contract']['tolerances'];samples=[]
 for lat,lon,h in itertools.product(pr['coordinate_contract']['analytic_lat'],pr['coordinate_contract']['analytic_lon'],pr['coordinate_contract']['analytic_height_m']):samples.append(('analytic',f'A{len(samples)}','2021-03-23T00:00:00',float(lon),float(lat),float(h)))
 for day,a in obs.items():
  for i in list(range(0,2880,120))+[2879]:samples.append(('satellite',day+'/'+str(i),str(a['utc'][i]),float(a['longitude'][i]),float(a['latitude'][i]),float(a['altitude'][i])))
 for kind,key,utc,lon,lat,h in samples:
  ref=EarthLocation.from_geodetic(lon*u.deg,lat*u.deg,h*u.m,ellipsoid='GRS80');xyz=np.array([x.to_value(u.m) for x in ref.geocentric]);lonw,latw,hw=ref.to_geodetic('WGS84');gc=float(np.rad2deg(np.arctan2(xyz[2],np.hypot(*xyz[:2]))));query=map_a_queries(np.array([utc],dtype='datetime64[ns]'),[lat],[lon],[h])[0];adapt=ProvisionalCoordinateAdapter(assumption=A_WGS84).adapt(query);assert np.linalg.norm(query.position_itrs_m-xyz)<=tol['XYZ_m'];vectors.append(xyz)
  for ell in ['GRS80','WGS84']:
   lo,la,ht=inverse(xyz,ell);liblo,libla,libh=ref.to_geodetic(ell);rounderr=float(np.linalg.norm(forward(lo,la,ht,ell)-xyz));liberr=float(np.linalg.norm(forward(float(liblo.deg),float(libla.deg),float(libh.to_value(u.m)),ell)-xyz));angleerr=abs(la-float(libla.deg));heighterr=abs(ht-float(libh.to_value(u.m)));pole=np.hypot(*xyz[:2])<1e-6;lonerr=None if pole else abs(angular_difference(lo,float(liblo.deg)));assert rounderr<=tol['XYZ_m'] and liberr<=tol['XYZ_m'] and angleerr<=tol['angle_deg'] and heighterr<=tol['height_m'] and (lonerr is None or lonerr<=tol['angle_deg'])
   maperr=abs(adapt.model_zg_m-float(hw.to_value(u.m)));assert maperr<=tol['height_m'] and abs(adapt.model_latitude_deg-float(latw.deg))<=tol['angle_deg'];cr.append(dict(sample_kind=kind,sample_id=key,ellipsoid=ell,roundtrip_XYZ_error_m=rounderr,library_forward_XYZ_error_m=liberr,latitude_crosscheck_error_deg=angleerr,height_crosscheck_error_m=heighterr,longitude_crosscheck_error_deg=lonerr,WGS84_minus_GRS80_height_m=float(hw.to_value(u.m))-h,WGS84_minus_GRS80_latitude_deg=float(latw.deg)-lat,GRS80_geodetic_minus_geocentric_latitude_deg=lat-gc,Map_A_height_identity_error_m=maperr,pole_longitude_NA=pole,numerical_PASS=True))
 table('coordinate_roundtrip_tests.csv',cr);np.savez_compressed(F/'coordinate_vectors_local.npz',XYZ_m=np.array(vectors));dump('coordinate_assumption_audit.json',dict(identity='NUMERICAL CONSISTENCY ONLY / NOT DATUM VALIDATION',ellipsoid_constants=pr['coordinate_contract']['ellipsoids'],tolerances_frozen_before_execution=tol,sample_points=len(samples),coordinate_test_rows=len(cr),all_PASS=True,pole_longitude_treated_as_undefined=True,original_position_vectors_preserved_local=True,Map_A_unchanged=True,XYZ_to_ellipsoid_numerical_consistency=True,ZG_ellipsoid_equivalence_proved=False,zero_surface_resolved=False,external_gate='EXTERNAL_DATUM_UNVERIFIED'))
 (F/'figures').mkdir()
 # Eight prespecified figures. No density/latitude/time selection by performance.
 fig,axs=plt.subplots(4,2,figsize=(12,12))
 for (day,hour),ax in zip(packs,axs.flat):
  pk=packs[(day,hour)];e=residual(pk['a']['density'],pk['pred']['B14']['Raw']);mask=RollingOrigin(day,hour).masks(pk['a']['utc'])
  for w in ['analysis','future_1h','future_3h','future_6h']:ax.hist(e[mask[w]],bins=np.linspace(float(e.min())-1e-8,float(e.max())+1e-8,81),histtype='step',density=True,label=w)
  # Plot limits fixed for presentation only; all values remain in statistics.
  ax.set(title=f'{day} {hour:02d}Z B14',xlabel='ln(obs/model)',ylabel='Descriptive density');ax.legend(fontsize=6)
 save(fig,'01_history_future_distribution.png')
 fig,ax=plt.subplots(figsize=(11,4));labels=[f'{d} {h:02d}Z' for d,h in packs]
 for h in [1,3,6]:ax.plot(range(8),[next(x['delta_b'] for x in gaps if x['date']==d and x['cutoff']==c and x['case']=='B14' and x['region']=='all' and x['window']==f'future_{h}h') for d,c in packs],'o-',label=f'{h}h')
 ax.axhline(0,color='k');ax.set(xticks=range(8),xticklabels=labels,ylabel='Future minus history median log residual');ax.tick_params(axis='x',rotation=25);ax.legend();save(fig,'02_median_gaps.png')
 fig,axs=plt.subplots(2,1,figsize=(12,7))
 for ax,y in zip(axs,['2021','2022']):
  dd=[(d,h) for d,h in packs if d.startswith(y)]
  for reg in BANDS[1:]:ax.plot(range(4),[next(x['delta_b'] for x in gaps if x['date']==d and x['cutoff']==h and x['case']=='B14' and x['region']==reg and x['window']=='future_6h') for d,h in dd],'o-',label=reg)
  ax.set(xticks=range(4),xticklabels=[f'{d} {h:02d}Z' for d,h in dd],ylabel='Six-hour median gap');ax.axhline(0,color='k');ax.legend()
 save(fig,'03_latitude_representativeness.png')
 fig,axs=plt.subplots(2,1,figsize=(12,7))
 for ax,key,label in zip(axs,['latitude_mean','height_mean_m'],['Mean latitude [deg]','Mean ellipsoid height [m]']):
  for win in ['analysis','future_6h']:ax.plot(range(8),[next(x[key] for x in orbit if x['date']==d and x['cutoff']==h and x['case']=='B14' and x['window']==win and x['region']=='all') for d,h in packs],'o-',label=win)
  ax.set(xticks=range(8),xticklabels=labels,ylabel=label);ax.tick_params(axis='x',rotation=20);ax.legend()
 save(fig,'04_orbit_coverage.png')
 fig,axs=plt.subplots(2,2,figsize=(12,7))
 for col,y in enumerate(['2021','2022']):
  for row,(key,label) in enumerate([('absolute_MSE_contribution','Absolute MSE contribution [(kg/m3)^2]'),('relative_MSE_contribution','Relative MSE contribution')]):
   ax=axs[row,col]
   for method in ['Raw','GlobalAdaptive','LatitudeAdaptive']:ax.plot(range(1,6),[next(x[key] for x in errors if x['date']==y+'-03-23' and x['cutoff']==18 and x['case']=='B14' and x['window']=='future_6h' and x['method']==method and x['group_type']=='density' and x['group']==f'Q{i}') for i in range(1,6)],'o-',label=method)
   ax.set(title=y+'-03-23 18Z six-hour; allbins',xlabel='Observed density quintile',ylabel=label);ax.legend(fontsize=6)
 save(fig,'05_error_contributions.png')
 fig,axs=plt.subplots(4,2,figsize=(12,12))
 for (day,hour),ax in zip(packs,axs.flat):
  for reg in BANDS:ax.plot(range(-3,6),[next(x['median'] for x in blocks if x['date']==day and x['cutoff']==hour and x['case']=='B14' and x['region']==reg and x['hours_from_cutoff_start']==lo) for lo in range(-3,6)],'o-',label=reg)
  ax.axvline(-.5,color='k',ls='--');ax.set(title=f'{day} {hour:02d}Z',xlabel='Fixed1h block start fromcutoff',ylabel='Median log residual');ax.legend(fontsize=6)
 save(fig,'06_fixed_time_blocks.png')
 sat=[x for x in cr if x['sample_kind']=='satellite' and x['ellipsoid']=='WGS84'];fig,axs=plt.subplots(2,1,figsize=(11,6));axs[0].plot([x['WGS84_minus_GRS80_height_m']*1e3 for x in sat],'.');axs[0].set(ylabel='Same-point height difference [mm]',title='Fixed25 satellite positions/day; fourdays');axs[1].plot([x['WGS84_minus_GRS80_latitude_deg'] for x in sat],'.');axs[1].set(xlabel='Fixed point index',ylabel='Latitude difference [deg]');save(fig,'07_ellipsoid_differences.png',True)
 fig,ax=plt.subplots(figsize=(11,4));ax.plot([x['GRS80_geodetic_minus_geocentric_latitude_deg'] for x in sat],'.');ax.set(xlabel='Fixed satellite point index',ylabel='Geodetic minus geocentric latitude [deg]');save(fig,'08_geodetic_geocentric.png',True)
 dump('warnings_local.json',warning_records)
 from verify_residual_representativeness_v1 import verify
 verify()
 for n,h in s['protected_SHA256'].items():assert sha(R/n)==h,n
 dump('run_result.json',dict(PASS=True,diagnostic_complete=True,new_queries=5760,new_correction_fits=0,new_forecasts=0,new_height_fits=0,coordinate_rows=len(cr),reproduced_legacy_metrics=len(oldchecks),wall_s=time.perf_counter()-start,CPU_s=time.process_time()-cpu,peak_process_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,old_assets_unchanged=True));print('READ-ONLY DIAGNOSTIC COMPLETE; no new method or datum release.',flush=True)
if __name__=='__main__':main()
