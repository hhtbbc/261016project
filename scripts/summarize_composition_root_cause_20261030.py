"""Summarize only the independently recomputed diagnostics and inspect initial primary."""
import sys,json,csv
from pathlib import Path
import numpy as np
import pandas as pd
from netCDF4 import Dataset
sys.path.insert(0,str(Path(__file__).resolve().parent))
from analyze_tiegcm_composition_root_cause_20261030 import R,OUT,sha,clean,relative,csvwrite

def main():
 d=pd.read_csv(OUT/'hourly_level_region.csv');h=pd.read_csv(OUT/'hourly_evolution.csv');c=pd.read_csv(OUT/'coupling.csv');out=[]
 for (case,v,reg,level),q in d[d.doy_seconds>=82*86400].groupby(['case','variable','region','level']):
  out.append(dict(case=case,variable=v,region=reg,level=int(level),failed_hours=int((q.fraction_within_5percent<.95).sum()),mean_abs_RMSE=q.absolute_RMSE.mean(),mean_relative_RMS=q.relative_RMS.mean(),median_A=q.A_median.median(),max_abs_P95=q.absolute_P95.max(),min_mid_ZG_km=q.ZG_mid_median_km.min(),max_mid_ZG_km=q.ZG_mid_median_km.max(),mean_near_small_fraction=q.near_small_A_fraction.mean(),mean_fail_near_small_fraction=q.fail_near_small_fraction.mean()))
 csvwrite(OUT/'candidate_level_region_summary.csv',out)
 bins=[]
 for (case,v),q in h.groupby(['case','variable']):
  for lo,hi in [(75,76),(80,82),(82,83),(83,84),(84,85.00001)]:
   z=q[(q.doy_seconds>=lo*86400)&(q.doy_seconds<hi*86400)]
   if len(z):bins.append(dict(case=case,variable=v,doy_start=lo,doy_stop=hi,mean_absolute_RMSE=z.absolute_RMSE.mean(),mean_relative_RMS=z.relative_RMS.mean(),first_relative_RMS=z.relative_RMS.iloc[0],last_relative_RMS=z.relative_RMS.iloc[-1],slope_relative_RMS_per_hour=float(np.polyfit(z.doy_seconds/3600,z.relative_RMS,1)[0]) if len(z)>1 else None))
 csvwrite(OUT/'time_bin_summary.csv',bins)
 # Same SOURCE_START 80 00:00 complete official fields, including previous-time state.
 paths=[R/'data/raw/tiegcm2_support/tiegcm_res5.0_mareqx_smin_prim.nc',R/'data/raw/tiegcm_2021_spinup_initial_condition_v1/tiegcm_res5.0_mareqx_smax_prim.nc'];initial=[];audit={}
 with Dataset(paths[0]) as a,Dataset(paths[1]) as b:
  a.set_auto_mask(False);b.set_auto_mask(False);ia=[tuple(t) for t in a['mtime'][:]].index((80,0,0));ib=[tuple(t) for t in b['mtime'][:]].index((80,0,0))
  for k in ['O1','O2','HE','O1_NM','O2_NM','HE_NM']:
   x=clean(a[k],ia);y=clean(b[k],ib)
   for l in range(x.shape[0]):
    initial.append(dict(variable=k,level=l,A_mean=float(np.nanmean(x[l])) if np.isfinite(x[l]).any() else None,B_mean=float(np.nanmean(y[l])) if np.isfinite(y[l]).any() else None,absolute_RMSE=float(np.sqrt(np.nanmean((y[l]-x[l])**2))) if np.isfinite(x[l]).any() else None,relative_RMS=float(np.sqrt(np.nanmean(relative(x[l],y[l])**2))) if np.isfinite(relative(x[l],y[l])).any() else None))
  audit['source_fields']={k:{'dimensions':a[k].dimensions,'dtype':str(a[k].dtype),'units':a[k].units} for k in ['O1','O2','HE','O1_NM','O2_NM','HE_NM']}
 csvwrite(OUT/'initial_state_profiles.csv',initial)
 sources=['comp.F','comp_o2o.F','lbc.F','nchist.F','fields.F','addiag.F','diags.F','cons.F','advance.F']
 for p in paths+[R/'third_party/TIEGCM2.0/src'/s for s in sources]:audit[str(p.relative_to(R))]=sha(p)
 # Validate midpoint height construction against author ZGMID interior averaging.
 with Dataset(R/'experiments/tiegcm_2021_spinup_14day_v1/A14/secondary_001.nc') as n:
  lev=n['lev'][:];ilev=n['ilev'][:];np.testing.assert_allclose(lev[:-1],(ilev[:-1]+ilev[1:])/2,rtol=0,atol=0)
  audit['lev']=lev.tolist();audit['ilev']=ilev.tolist();audit['height_top']='top lev above final interface: physical height N/A; author ZGMID top extrapolates, this audit does not'
 audit['summaries']={}
 for v in ['O1','O2','N2']:
  q=d[(d.case=='14day')&(d.variable==v)&(d.region=='global')&(d.doy_seconds>=82*86400)]
  failed=q[q.fraction_within_5percent<.95]
  audit['summaries'][v]={'failed_levels':sorted(failed.level.unique().tolist()),'failed_cells_global':len(failed),'mean_failed_near_small_fraction':float(failed.mean_fail_near_small_fraction.mean()) if 'mean_fail_near_small_fraction' in failed else float(failed.fail_near_small_fraction.mean()),'failed_A_median_range':[float(failed.A_median.min()),float(failed.A_median.max())],'failed_abs_RMSE_range':[float(failed.absolute_RMSE.min()),float(failed.absolute_RMSE.max())]}
 (OUT/'source_and_summary_audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit['summaries'],indent=2))
if __name__=='__main__':main()
