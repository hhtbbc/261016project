"""Separate small-value RMS leverage from genuine bulk residual; selected raw cross checks."""
from pathlib import Path
import sys,json
import numpy as np
from netCDF4 import Dataset
sys.path.insert(0,str(Path(__file__).resolve().parent))
from analyze_tiegcm_composition_root_cause_20261030 import R,OUT,CASES,clean,relative,csvwrite

def idx(folder):
 o={}
 for p in sorted(folder.glob('secondary_*.nc')):
  with Dataset(p) as n:
   for i,m in enumerate(n['mtime'][:]):o[int(m[0])*86400+int(m[1])*3600]=(p,i)
 return o

def main():
 maps={}
 for case,folders in CASES.items():
  for g,p in zip(['A','B'],folders):maps[case+g]=idx(p)
 rows=[];checks=[]
 for t in range(82*86400,85*86400+1,3600):
  vals={}
  for name in maps:
   p,i=maps[name][t]
   with Dataset(p) as d:
    d.set_auto_mask(False);vals[name]={v:clean(d[v],i) for v in ['O1','O2','N2','HE']}
  a=vals['14dayA']['N2'];b=vals['14dayB']['N2'];r=relative(a,b);good=np.isfinite(r);near=good&(a<=2e-6);fail=good&(r>=.05)
  rows.append(dict(doy_seconds=t,near_small_fraction=float(near.sum()/good.sum()),near_small_share_of_squared_relative_error=float(np.sum(r[near]**2)/np.sum(r[good]**2)),near_small_share_of_failed_points=float((near&fail).sum()/fail.sum()),relative_RMS_all=float(np.sqrt(np.mean(r[good]**2))),relative_RMS_non_small_diagnostic=float(np.sqrt(np.mean(r[good&~near]**2))),absolute_RMSE=float(np.sqrt(np.mean((b[good]-a[good])**2)))))
  if t in [82*86400,84*86400,85*86400]:
   for left,right in [('7dayA','14dayA'),('7dayB','14dayB')]:
    for v in ['O1','O2','N2']:
     a=vals[left][v];b=vals[right][v];checks.append(dict(comparison=right+'-'+left,variable=v,doy_seconds=t,absolute_RMSE=float(np.sqrt(np.nanmean((b-a)**2))),relative_RMS=float(np.sqrt(np.nanmean(relative(a,b)**2)))))
 csvwrite(OUT/'N2_floor_leverage.csv',rows);csvwrite(OUT/'cross_raw_checkpoints.csv',checks)
 print('N2 near-small squared-relative-error share min/median/max:',np.percentile([r['near_small_share_of_squared_relative_error'] for r in rows],[0,50,100]))
 print('N2 near-small share of failures min/median/max:',np.percentile([r['near_small_share_of_failed_points'] for r in rows],[0,50,100]))
if __name__=='__main__':main()
