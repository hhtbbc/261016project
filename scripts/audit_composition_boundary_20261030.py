"""Boundary residuals in native staggered geometry; diagnostic, never an acceptance change."""
from pathlib import Path
import sys,json
import numpy as np
from netCDF4 import Dataset
sys.path.insert(0,str(Path(__file__).resolve().parent))
from analyze_tiegcm_composition_root_cause_20261030 import R,OUT,CASES,clean,sha,csvwrite

def main():
 rows=[];inputs={}
 for case,paths in CASES.items():
  for group,p in zip(['A','B'],paths):
   for f in sorted(p.glob('secondary_*.nc')):
    inputs[str(f.relative_to(R))]=sha(f)
    with Dataset(f) as n:
     n.set_auto_mask(False)
     for i,mt in enumerate(n['mtime'][:]):
      t=int(mt[0])*86400+int(mt[1])*3600
      # Boundary is at ilev=-7, midpoint=-6.75. Do NOT test O1+O2=.234 at midpoint.
      x={k:clean(n[k],i) for k in ['O1','O2','HE','N2']}
      rows.append(dict(case=case,group=group,doy_seconds=t,bottom_mid_O1_mean=float(np.nanmean(x['O1'][0])),bottom_mid_O2_mean=float(np.nanmean(x['O2'][0])),bottom_mid_oxygen_sum_mean=float(np.nanmean(x['O1'][0]+x['O2'][0])),top_N2_at_small_fraction=float(np.mean(x['N2'][-1]<=1.01e-6)),top_N2_min=float(np.min(x['N2'][-1])),top_N2_median=float(np.median(x['N2'][-1]))))
 csvwrite(OUT/'boundary_adjacent_evolution.csv',rows)
 for p,h in inputs.items():assert sha(R/p)==h
 (OUT/'boundary_audit.json').write_text(json.dumps({'raw_sha':inputs,'do_not_equate_bottom_midpoint_to_boundary':True,'no_numerical_simulation':True},indent=2))
if __name__=='__main__':main()
