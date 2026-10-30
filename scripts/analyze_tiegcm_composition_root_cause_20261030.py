"""Read-only streamed composition diagnostics; no model imports or launch paths."""
from pathlib import Path
import csv,json,hashlib,time
from contextlib import ExitStack
import numpy as np
from netCDF4 import Dataset,num2date
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1]
OUT=R/'results/tiegcm_composition_root_cause_20261030'
CASES={'7day':(R/'experiments/tiegcm_training_mar23_v2_2021_longrun',R/'experiments/tiegcm_2021_spinup_initial_condition_v1/B'),'14day':(R/'experiments/tiegcm_2021_spinup_14day_v1/A14',R/'experiments/tiegcm_2021_spinup_14day_v1/B14')}
VARS=['O1','O2','N2'];REGIONS={'global':(-90,90),'south_polar':(-90,-60),'south_mid':(-60,-30),'tropics':(-30,30),'north_mid':(30,60),'north_polar':(60,90)}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def clean(v,i):
 x=np.asarray(v[i],dtype=float);assert np.isfinite(x).all()
 mask=abs(x)>1e30
 for k in ['missing_value','_FillValue']:
  if k in v.ncattrs():mask|=x==np.asarray(v.getncattr(k),dtype=v.dtype)
 x[mask]=np.nan;return x

def relative(a,b):
 return np.divide(abs(b-a),abs(a),out=np.full_like(a,np.nan),where=np.isfinite(a)&np.isfinite(b)&(abs(a)>1e-8))
def csvwrite(p,rows):
 with p.open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
def main():
 start=time.monotonic();assert OUT.resolve().is_relative_to(R);OUT.mkdir(exist_ok=False)
 audit={'inputs':{},'schemas':{},'cases':{},'no_model_execution':True};rows=[];hourly=[];heights=[];coupling=[]
 for case,(ap,bp) in CASES.items():
  paths=[sorted(p.glob('secondary_*.nc')) for p in [ap,bp]];assert len(paths[0])==len(paths[1]);times=[];counts={v:{'candidate':0,'last24h':0,'endpoint':0} for v in VARS};closure=0.;max_driver=0.
  for pa,pb in zip(*paths):
   for p in [pa,pb]:audit['inputs'][str(p.relative_to(R))]=sha(p)
   with Dataset(pa) as a,Dataset(pb) as b:
    a.set_auto_mask(False);b.set_auto_mask(False)
    for g in ['lat','lon','lev','ilev']:np.testing.assert_array_equal(a[g][:],b[g][:])
    lat=np.array(a['lat'][:]);lev=np.array(a['lev'][:]);ilev=np.array(a['ilev'][:]);assert np.all(np.diff(lev)>0) and np.all(np.diff(ilev)>0)
    for v in VARS+['HE','Z','ZG']:
     assert a[v].dimensions==b[v].dimensions and a[v].dtype==b[v].dtype and a[v].units==b[v].units
     audit['schemas'][v]={'dimensions':a[v].dimensions,'dtype':str(a[v].dtype),'units':a[v].units}
    ta=num2date(a['time'][:],a['time'].units);tb=num2date(b['time'][:],b['time'].units);assert list(ta)==list(tb)
    for i,date in enumerate(ta):
     t=int(date.strftime('%j'))*86400+date.hour*3600;assert date.year==2021
     for n in [a,b]:assert tuple(n['mtime'][i])==(int(date.strftime('%j')),date.hour,date.minute)
     times.append(t)
     for k in ['f107d','f107a','Kp','hpower','ctpoten']:max_driver=max(max_driver,abs(float(a[k][i])-float(b[k][i])))
     aa={v:clean(a[v],i) for v in VARS+['HE']};bb={v:clean(b[v],i) for v in VARS+['HE']}
     for x in [aa,bb]:closure=max(closure,float(np.nanmax(abs(sum(x.values())-1))))
     za=clean(a['ZG'],i)*1e-5;zb=clean(b['ZG'],i)*1e-5
     # Composition is on lev, not ilev: interpolate geometry in log-pressure coordinate.
     # Highest lev lies above last ZG interface: leave unsupported height N/A, never extrapolate.
     zmid=np.full_like(za,np.nan)
     for l,z in enumerate(lev):
      if ilev[0]<=z<=ilev[-1]:
       j=min(np.searchsorted(ilev,z,side='right')-1,len(ilev)-2);f=(z-ilev[j])/(ilev[j+1]-ilev[j]);zmid[l]=(1-f)*za[j]+f*za[j+1]
     ds=[bb[v]-aa[v] for v in VARS]
     for v,d in zip(VARS,ds):
      x=aa[v];y=bb[v];rel=relative(x,y);good=np.isfinite(rel)
      hourly.append(dict(case=case,variable=v,doy_seconds=t,hours_from_start=(t-times[0])/3600+1,A_mean=float(np.nanmean(x)),B_mean=float(np.nanmean(y)),absolute_RMSE=float(np.sqrt(np.nanmean(d*d))),relative_RMS=float(np.sqrt(np.nanmean(rel*rel))),relative_P95=float(np.nanpercentile(rel,95)),absolute_P95=float(np.nanpercentile(abs(d),95))))
      for region,(lo,hi) in REGIONS.items():
       sel=(lat>=lo)&(lat<=hi)
       for l in range(len(lev)):
        g=good[l,sel];xx=x[l,sel][g];dd=d[l,sel][g];rr=rel[l,sel][g]
        if not len(xx):continue
        fraction=float(np.mean(rr<.05))
        if t>=82*86400:
         for period,yes in [('candidate',True),('last24h',t>=84*86400),('endpoint',t==85*86400)]:
          if yes:counts[v][period]+=int(fraction<.95)
        # Full hourly/level/region statistics, same frozen unweighted point-count gate.
        rows.append(dict(case=case,variable=v,doy_seconds=t,level=l,lev=float(lev[l]),region=region,n=len(xx),A_min=float(xx.min()),A_median=float(np.median(xx)),A_max=float(xx.max()),B_mean=float(np.nanmean(y[l,sel])),bias=float(dd.mean()),absolute_RMSE=float(np.sqrt(np.mean(dd*dd))),absolute_P95=float(np.percentile(abs(dd),95)),relative_RMS=float(np.sqrt(np.mean(rr*rr))),relative_P95=float(np.percentile(rr,95)),fraction_within_5percent=fraction,near_small_A_fraction=float(np.mean(xx<=2e-6)),fail_near_small_fraction=float(np.mean(xx[rr>=.05]<=2e-6)) if np.any(rr>=.05) else 0.,ZG_mid_median_km=float(np.nanmedian(zmid[l,sel])) if np.isfinite(zmid[l,sel]).any() else None))
      if t>=82*86400:
       for l in range(len(lev)):
        z=zmid[l];heights.append(dict(case=case,variable=v,doy_seconds=t,level=l,lev=float(lev[l]),A_ZG_mid_min_km=float(np.nanmin(z)) if np.isfinite(z).any() else None,A_ZG_mid_median_km=float(np.nanmedian(z)) if np.isfinite(z).any() else None,A_ZG_mid_max_km=float(np.nanmax(z)) if np.isfinite(z).any() else None))
     for l in range(len(lev)):
      x=ds[0][l].ravel();y=ds[1][l].ravel();g=np.isfinite(x)&np.isfinite(y)
      if g.any():coupling.append(dict(case=case,doy_seconds=t,level=l,O1_O2_delta_correlation=float(np.corrcoef(x[g],y[g])[0,1]) if np.std(x[g])*np.std(y[g])>0 else None,oxygen_sum_delta_RMSE=float(np.sqrt(np.mean((x[g]+y[g])**2))),N2_delta_RMSE=float(np.sqrt(np.nanmean(ds[2][l]**2)))))
   print(case,pa.name,'streamed',flush=True)
  assert np.diff(times).tolist()==[3600]*(len(times)-1);assert max_driver<1e-10
  audit['cases'][case]={'frames':len(times),'first_doy_seconds':times[0],'last_doy_seconds':times[-1],'failed_cells':counts,'composition_sum_max_abs_residual':closure,'driver_max_difference':max_driver}
 # Independently reproduce ALL old time/level/region failure counts.
 expected=json.loads((R/'results/tiegcm_2021_spinup_14day_v1/acceptance_by_period.json').read_text())
 for case in CASES:
  for v in VARS:
   for period in ['candidate','last24h','endpoint']:assert audit['cases'][case]['failed_cells'][v][period]==expected[case][period][v]['failed_cells']
 csvwrite(OUT/'hourly_level_region.csv',rows);csvwrite(OUT/'hourly_evolution.csv',hourly);csvwrite(OUT/'native_height_mapping.csv',heights);csvwrite(OUT/'coupling.csv',coupling)
 for case in CASES:
  fig,axes=plt.subplots(3,3,figsize=(14,10))
  for i,v in enumerate(VARS):
   q=[r for r in hourly if r['case']==case and r['variable']==v];t=np.array([r['doy_seconds'] for r in q])/86400
   for col,keys in enumerate([['A_mean','B_mean'],['absolute_RMSE'],['relative_RMS']]):
    for k in keys:axes[i,col].plot(t,[r[k]*(100 if col==2 else 1) for r in q],label=k)
    axes[i,col].set_title(v+' '+['mass mixing ratio','absolute RMS (mmr)','relative RMS (%)'][col]);axes[i,col].axvline(82,color='gray',ls=':');axes[i,col].legend();axes[i,col].set_xlabel('2021 day of year')
  fig.tight_layout();fig.savefig(OUT/f'{case}_evolution.png',dpi=150);plt.close(fig)
 for case in CASES:
  fig,axs=plt.subplots(1,3,figsize=(14,4))
  for ax,v in zip(axs,VARS):
   q=[r for r in rows if r['case']==case and r['variable']==v and r['region']=='global'];ts=sorted({r['doy_seconds'] for r in q});m=np.full((29,len(ts)),np.nan);ti={t:i for i,t in enumerate(ts)}
   for r in q:m[r['level'],ti[r['doy_seconds']]]=r['relative_P95']*100
   im=ax.imshow(m,aspect='auto',origin='lower',extent=[ts[0]/86400,ts[-1]/86400,0,28]);ax.set_title(v+' relative P95 (%)');ax.set_xlabel('DOY');ax.set_ylabel('native lev index (bottom → top)');fig.colorbar(im,ax=ax)
  fig.tight_layout();fig.savefig(OUT/f'{case}_level_time.png',dpi=150);plt.close(fig)
 # Regional comparison on common candidate window, diagnostic averaging not a replacement gate.
 fig,axs=plt.subplots(1,3,figsize=(15,4))
 for ax,v in zip(axs,VARS):
  for case in CASES:
   for reg in ['south_polar','tropics','north_polar']:
    q=[r for r in rows if r['case']==case and r['variable']==v and r['region']==reg and r['doy_seconds']>=82*86400];ys=[np.mean([r['relative_RMS'] for r in q if r['level']==l])*100 for l in range(28)];ax.plot(ys,range(28),label=case+' '+reg)
  ax.set_title(v);ax.set_xlabel('mean hourly relative RMS (%)');ax.set_ylabel('native lev index');ax.legend(fontsize=6)
 fig.tight_layout();fig.savefig(OUT/'regional_layer_comparison.png',dpi=160);plt.close(fig)
 # Verify all original NetCDF SHA again after read-only processing.
 for p,h in audit['inputs'].items():assert sha(R/p)==h
 audit['wall_seconds']=time.monotonic()-start;audit['historical_counts_reproduced']=True
 (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit['cases'],indent=2),flush=True)
if __name__=='__main__':main()
