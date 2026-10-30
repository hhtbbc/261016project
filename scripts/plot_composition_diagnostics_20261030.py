"""Extra visual diagnostics from immutable recomputed CSV, never alter physical results."""
from pathlib import Path
import sys
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parent))
from analyze_tiegcm_composition_root_cause_20261030 import OUT

def main():
 x=pd.read_csv(OUT/'N2_floor_leverage.csv');fig,ax=plt.subplots(1,2,figsize=(12,4))
 for k in ['relative_RMS_all','relative_RMS_non_small_diagnostic']:ax[0].plot(x.doy_seconds/86400,x[k]*100,label=k)
 ax[0].set(xlabel='2021 DOY',ylabel='N2 relative RMS (%)',title='All points retained; subgroup is diagnostic only');ax[0].legend(fontsize=7)
 ax[1].plot(x.doy_seconds/86400,x.near_small_share_of_squared_relative_error*100,label='share of squared relative error');ax[1].plot(x.doy_seconds/86400,x.near_small_share_of_failed_points*100,label='share of failed points');ax[1].set(xlabel='2021 DOY',ylabel='Share (%)',ylim=(0,100));ax[1].legend(fontsize=7)
 fig.tight_layout();fig.savefig(OUT/'N2_floor_diagnostic.png',dpi=160);plt.close(fig)
 h=pd.read_csv(OUT/'hourly_evolution.csv');fig,axes=plt.subplots(2,3,figsize=(14,7))
 for j,v in enumerate(['O1','O2','N2']):
  for case in ['7day','14day']:
   q=h[(h.case==case)&(h.variable==v)&(h.doy_seconds>=82*86400)]
   axes[0,j].plot(q.doy_seconds/86400,q.absolute_RMSE,label=case);axes[1,j].plot(q.doy_seconds/86400,q.relative_RMS*100,label=case)
  for i in range(2):axes[i,j].set(xlabel='2021 DOY',title=v,ylabel=['absolute RMS (mmr)','relative RMS (%)'][i]);axes[i,j].legend()
 fig.tight_layout();fig.savefig(OUT/'candidate_7vs14_evolution.png',dpi=160);plt.close(fig)
if __name__=='__main__':main()
