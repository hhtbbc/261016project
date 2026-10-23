"""Same-epoch A/B comparison with pre-run frozen thresholds. No simulation or training."""
from pathlib import Path
import sys,json,csv,importlib.util,time
import numpy as np
from netCDF4 import Dataset
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R/'scripts')]
from run_tiegcm_mar23_2021_longrun import stream_sha
spec=importlib.util.spec_from_file_location('legacy',R/'scripts/compare_tiegcm2023_s3_s7.py');legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
F=R/'experiments/tiegcm_2021_spinup_initial_condition_v1';A=R/'experiments/tiegcm_training_mar23_v2_2021_longrun';B=F/'B';OUT=R/'results/tiegcm_2021_spinup_initial_condition_v1/comparison'
NAMES=['DEN','TN','UN','VN','O1','O2','N2','HE','Z','ZG']
def load(directory):
 chunks={k:[] for k in NAMES};times=[];grid=None;schema=None;drivers=[]
 for p in sorted(directory.glob('secondary_*.nc')):
  with Dataset(p) as n:
   n.set_auto_mask(False);mt=np.asarray(n['mtime'][:],int);times.extend((mt[:,0]*86400+mt[:,1]*3600+mt[:,2]*60).tolist())
   g={k:np.asarray(n[k][:]) for k in ['lat','lon','lev','ilev']};sig={k:(n[k].dimensions,str(n[k].dtype),getattr(n[k],'units',None)) for k in n.variables}
   if grid is None:grid=g;schema=sig
   else:
    assert sig==schema
    for k in grid:np.testing.assert_array_equal(grid[k],g[k])
   for k in NAMES:
    v=n[k];z=np.asarray(v[:],dtype=np.float64);invalid=abs(z)>1e30
    for attr in ['missing_value','_FillValue']:
     if attr in v.ncattrs():invalid|=z==np.asarray(v.getncattr(attr),dtype=v.dtype)
    assert np.isfinite(z).all();z[invalid]=np.nan;z*= {'DEN':1000.,'Z':.01,'ZG':.01,'UN':.01,'VN':.01}.get(k,1);chunks[k].append(z)
   drivers.append(np.stack([n[k][:] for k in ['f107d','f107a','Kp','hpower','ctpoten']],axis=1))
 assert times==list(range(75*86400+3600,85*86400+1,3600))
 return {k:np.concatenate(v) for k,v in chunks.items()},np.asarray(times),grid,schema,np.concatenate(drivers)
def metrics(x,y,w,limit=None,relative=False,floor=0.,log=False):
 good=np.isfinite(x)&np.isfinite(y);u=x[good];v=y[good];weights=np.broadcast_to(w,x.shape)[good]
 if not len(u):return {'n':0,'coverage':0.,'pass_fraction':None,'passed':False,'abs_P95':None,'relative_P95':None,'RMSE':None,'max_abs':None,'max_relative':None,'log_RMSE':None}
 delta=u-v;absolute=abs(delta);relgood=abs(v)>floor;rr=abs(delta[relgood]/v[relgood]);rw=weights[relgood];err=rr if relative else absolute
 result={'n':len(u),'coverage':float(good.mean()),'relative_n':int(relgood.sum()),'bias':float(np.average(delta,weights=weights)),'RMSE':float(np.sqrt(np.average(delta**2,weights=weights))),'abs_P95':legacy.percentile(absolute,weights,.95),'max_abs':float(absolute.max()),'relative_P95':legacy.percentile(rr,rw,.95) if len(rr) else None,'max_relative':float(rr.max()) if len(rr) else None,'pass_fraction':float((err<limit).mean()) if limit is not None and len(err) else None}
 result['passed']=bool(result['pass_fraction'] is not None and result['pass_fraction']>=.95)
 if log:
  assert (u>0).all() and (v>0).all();result['log_RMSE']=float(np.sqrt(np.average(np.log(u/v)**2,weights=weights)))
 else:result['log_RMSE']=None
 return result
def csvout(path,rows):
 keys=list(dict.fromkeys(k for r in rows for k in r))
 with path.open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');w.writeheader();w.writerows(rows)
def gate_cells(xx,yy,mask_time,regions,limit,relative=False,floor=0.):
 good=np.isfinite(xx)&np.isfinite(yy);err=abs(xx-yy)
 if relative:
  good&=abs(yy)>floor;err=np.divide(err,abs(yy),out=np.full_like(err,np.nan),where=good)
 fails=[];total=0;worst=1.
 for region,mask in regions.items():
  valid=good[mask_time][:,:,mask,:];e=err[mask_time][:,:,mask,:];n=valid.sum(axis=(-2,-1));frac=np.divide(((e<limit)&valid).sum(axis=(-2,-1)),n,out=np.full(n.shape,np.nan),where=n>0)
  for i,l in np.argwhere(np.isfinite(frac)):
   total+=1;worst=min(worst,float(frac[i,l]))
   if frac[i,l]<.95:fails.append({'region':region,'selected_hour_index':int(i),'level':int(l),'fraction':float(frac[i,l])})
 return {'evaluated_time_level_region_cells':total,'failed_cells':len(fails),'worst_fraction':worst,'passed':total>0 and not fails,'failures':fails}
def main():
 started=time.monotonic()
 status=json.loads((B/'run_status.json').read_text());assert status['returncode']==0 and status['normal_exit_count']==4 and status['stop_reason'] is None
 assert json.loads((B/'data_audit.json').read_text())['engineering_PASS']
 print('Loading same-epoch A/B native histories',flush=True)
 a,t,g,sa,da=load(A);b,tb,gb,sb,db=load(B)
 np.testing.assert_array_equal(t,tb);assert sa==sb
 for k in g:np.testing.assert_array_equal(g[k],gb[k])
 np.testing.assert_allclose(da,db,rtol=0,atol=1e-10)
 assert not OUT.exists();OUT.mkdir(parents=True)
 rules=json.loads((F/'frozen_comparison_rules.json').read_text())
 lat=g['lat'];w=np.cos(np.deg2rad(lat))[None,:,None]
 regions={k:(lat>=v[0])&(lat<=v[1]) for k,v in rules['latitude_regions'].items()}
 periods={'candidate':t>=82*86400,'last24h':t>=84*86400,'endpoint':t==85*86400}
 rows=[];hourly=[];gates={};profiles=[]
 vector=np.hypot(b['UN']-a['UN'],b['VN']-a['VN'])
 specs={k:(.05,True,1e-8 if k in ['O1','O2','N2','HE'] else 0.) for k in ['DEN','O1','O2','N2','HE']}
 specs.update(TN=(10.,False,0.),UN=(20.,False,0.),VN=(20.,False,0.),Z=(None,False,0.),ZG=(None,False,0.),WIND_VECTOR=(20.,False,0.))
 for k in NAMES+['WIND_VECTOR']:
  print('Native',k,flush=True)
  xx=vector if k=='WIND_VECTOR' else b[k];yy=np.zeros_like(vector) if k=='WIND_VECTOR' else a[k]
  limit,relative,floor=specs[k]
  for period,mask in periods.items():
   for region,lmask in regions.items():
    x=xx[mask][:,:,lmask,:];y=yy[mask][:,:,lmask,:];ww=w[:,lmask,:]
    rows.append(dict(variable=k,period=period,region=region,**metrics(x,y,ww,limit,relative,floor,k=='DEN')))
    if k in ['DEN','TN','WIND_VECTOR','O1','O2','N2','HE']:
     for lev in range(x.shape[1]):
      profiles.append(dict(variable=k,period=period,region=region,level=lev,**metrics(x[:,lev],y[:,lev],ww[0],limit,relative,floor,k=='DEN')))
  for i,tt in enumerate(t):
   hourly.append(dict(variable=k,time_doy_seconds=int(tt),hours_after_start=float((tt-75*86400)/3600),**metrics(xx[i],yy[i],w,limit,relative,floor,k=='DEN')))
  if k in ['DEN','TN','WIND_VECTOR','O1','O2','N2','HE']:
   gates[k]=gate_cells(xx,yy,periods['last24h'],regions,limit,relative,floor)
 csvout(OUT/'native_summary.csv',rows);csvout(OUT/'native_hourly.csv',hourly);csvout(OUT/'native_profiles.csv',profiles)
 # Native pressure groups: same pressure indices, selected independently of B.
 group_rows=[];group_hourly=[]
 groups={'upper20_28':[np.arange(20,29) for _ in t],'A_median_ZG_400_500':[np.flatnonzero((np.median(z,axis=(1,2))>=400e3)&(np.median(z,axis=(1,2))<=500e3)) for z in a['ZG']]}
 for group,indices in groups.items():
  for i,idx in enumerate(indices):
   assert len(idx), (group,i)
   group_hourly.append(dict(group=group,time_doy_seconds=int(t[i]),levels=' '.join(map(str,idx)),median_ZG_km=' '.join(f'{v:.6f}' for v in np.median(a['ZG'][i,idx],axis=(1,2))/1000),**metrics(b['DEN'][i,idx],a['DEN'][i,idx],w,.05,True,0,True)))
  for period,mask in periods.items():
   for region,lmask in regions.items():
    x=np.concatenate([b['DEN'][i,indices[i]][:,lmask,:] for i in np.flatnonzero(mask)])
    y=np.concatenate([a['DEN'][i,indices[i]][:,lmask,:] for i in np.flatnonzero(mask)])
    group_rows.append(dict(group=group,period=period,region=region,**metrics(x,y,w[:,lmask,:],.05,True,0,True)))
 csvout(OUT/'native_density_groups.csv',group_rows);csvout(OUT/'native_density_group_hourly.csv',group_hourly)
 # Both fields are interpolated on their own native ZG columns, never extrapolated.
 heights={};heightrows=[];heighthour=[];trends=[];heightgates={}
 for h in rules['common_native_ZG_heights_km']:
  print('Native ZG height',h,flush=True)
  xa=np.stack([legacy.a3.at_height(z,d,h*1000) for z,d in zip(a['ZG'],a['DEN'])]);xb=np.stack([legacy.a3.at_height(z,d,h*1000) for z,d in zip(b['ZG'],b['DEN'])]);heights[h]=(xa,xb)
  for period,mask in periods.items():
   for region,lmask in regions.items():heightrows.append(dict(height_km=h,period=period,region=region,**metrics(xb[mask][:,lmask,:],xa[mask][:,lmask,:],w[0,lmask,:],.05,True,0,True)))
  for i,tt in enumerate(t):
   for region,lmask in regions.items():heighthour.append(dict(height_km=h,region=region,time_doy_seconds=int(tt),hours_after_start=float((tt-75*86400)/3600),**metrics(xb[i,lmask,:],xa[i,lmask,:],w[0,lmask,:],.05,True,0,True)))
  heightgates[str(h)]=gate_cells(xb[:,None],xa[:,None],periods['last24h'],regions,.05,True)
  records=[r for r in heighthour if r['height_km']==h and r['region']=='global' and r['time_doy_seconds']>=84*86400]
  slope=float(np.polyfit(np.arange(len(records)),[r['log_RMSE'] for r in records],1)[0])
  trends.append(dict(height_km=h,last24h_log_RMSE_slope_per_hour=slope,no_growth_pass=slope<=0,first6_mean=float(np.mean([r['log_RMSE'] for r in records[:6]])),last6_mean=float(np.mean([r['log_RMSE'] for r in records[-6:]]))))
 csvout(OUT/'native_ZG_density.csv',heightrows);csvout(OUT/'native_ZG_density_hourly.csv',heighthour);csvout(OUT/'last24h_trends.csv',trends)
 # Geometric-height snapshots at the candidate start and end, light CSV only.
 maps=[]
 for i in [167,239]:
  xa,xb=heights[450];rel=(xb[i]-xa[i])/xa[i]
  for j in range(len(lat)):
   for l in range(len(g['lon'])):maps.append(dict(time_doy_seconds=int(t[i]),lat=float(lat[j]),lon=float(g['lon'][l]),relative_difference=float(rel[j,l])))
 csvout(OUT/'native_ZG_450km_maps.csv',maps)
 summary={'rules_SHA256':stream_sha(F/'frozen_comparison_rules.json'),'same_times_grid_schema_drivers':True,'hourly_frames':len(t),'candidate_frames':int(periods['candidate'].sum()),'last24h_frames':int(periods['last24h'].sum()),'strict_last24h_native_gates':gates,'strict_last24h_height_gates':heightgates,'no_growth':trends,'native_multivariable_pass':all(v['passed'] for v in gates.values()),'fixed_height_pass':all(v['passed'] for v in heightgates.values()),'along_track_status':'N/A_EXTERNAL_DATUM_UNVERIFIED','overall_science_spinup_ready':False,'A_is_truth':False,'comparison_wall_s':time.monotonic()-started}
 (OUT/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
 # Plots are direct transformations of the saved statistics.
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 figdir=OUT/'figures';figdir.mkdir()
 fig,axes=plt.subplots(2,2,figsize=(11,7))
 for ax,(k,col,scale) in zip(axes.flat,[('DEN','relative_P95',100),('TN','RMSE',1),('WIND_VECTOR','RMSE',1),('N2','relative_P95',100)]):
  rr=[r for r in hourly if r['variable']==k];ax.plot([r['hours_after_start']/24 for r in rr],[r[col]*scale for r in rr]);ax.axvline(7,color='gray',ls='--');ax.set(title=k,ylabel=col+(' (%)' if scale==100 else ' (SI)'),xlabel='Days from March 16')
 fig.tight_layout();fig.savefig(figdir/'native_evolution.png',dpi=140);plt.close(fig)
 fig,ax=plt.subplots(figsize=(9,4))
 for h in heights:
  rr=[r for r in heighthour if r['height_km']==h and r['region']=='global'];ax.plot([r['hours_after_start']/24 for r in rr],[100*r['relative_P95'] for r in rr],label=str(h)+' km')
 ax.axvline(7,color='gray',ls='--');ax.set(xlabel='Days from March 16',ylabel='Absolute relative difference P95 (%)',yscale='log');ax.legend(ncol=3);fig.tight_layout();fig.savefig(figdir/'native_ZG_density_evolution.png',dpi=140);plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for ax,period in zip(axes,['candidate','last24h']):
  for region in regions:
   rr=[r for r in profiles if r['variable']=='DEN' and r['period']==period and r['region']==region];ax.plot([100*r['relative_P95'] for r in rr],[r['level'] for r in rr],label=region)
  ax.axvline(5,color='gray',ls='--');ax.set(title=period,xlabel='Density relative P95 (%)',ylabel='Native pressure index')
 axes[-1].legend(fontsize=7);fig.tight_layout();fig.savefig(figdir/'density_pressure_profiles.png',dpi=140);plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for ax,i in zip(axes,[167,239]):
  xa,xb=heights[450];im=ax.pcolormesh(g['lon'],lat,100*(xb[i]-xa[i])/xa[i],shading='auto',cmap='RdBu_r');ax.set(title='March '+('23 00 UTC' if i==167 else '26 00 UTC'),xlabel='Longitude',ylabel='Latitude');fig.colorbar(im,ax=ax,label='B/A - 1 (%)')
 fig.tight_layout();fig.savefig(figdir/'native_ZG_450km_maps.png',dpi=140);plt.close(fig)
 fig,ax=plt.subplots(figsize=(8,4))
 for k in ['O1','O2','N2','HE']:
  rr=[r for r in hourly if r['variable']==k];ax.plot([r['hours_after_start']/24 for r in rr],[r['relative_P95']*100 for r in rr],label=k)
 ax.set(xlabel='Days from March 16',ylabel='Mass mixing ratio relative P95 (%)',yscale='log');ax.axvline(7,color='gray',ls='--');ax.legend();fig.tight_layout();fig.savefig(figdir/'composition_evolution.png',dpi=140);plt.close(fig)
 print(json.dumps({k:v for k,v in summary.items() if k not in ['strict_last24h_native_gates','strict_last24h_height_gates']},indent=2),flush=True)
if __name__=='__main__':main()
