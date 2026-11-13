"""CPU presentation supplements; retain every original full-range figure unchanged."""
from pathlib import Path
import sys,json,csv
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from train_den_overfit_v5 import F,O
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from finalize_den_overfit_v5 import save,read
if __name__=='__main__':
 rows=[json.loads(x) for x in (F/'updates.jsonl').read_text().splitlines()]
 fig,ax=plt.subplots(figsize=(9,4));ax.semilogy([x['step'] for x in rows],[x['loss'] for x in rows]);ax.set(xlabel='Actual optimizer update',ylabel='Normalized DEN MSE [log scale]',title='Full100-update fixed2021 curve, log scale exposes late oscillations');save(fig,'01b_loss_log_scale.png')
 comp=read(O/'fixed_AI_vs_Persistence.csv');fig,ax=plt.subplots(figsize=(10,4))
 for step in [50,100]:
  rr=sorted([x for x in comp if int(x['step'])==step and x['region']=='global' and x['group'].startswith('level_')],key=lambda x:x['group']);ax.plot(range(29),[float(x['AI_relative_RMS'])*100 for x in rr],label=f'AI step{step}')
 ax.plot(range(29),[float(x['Persistence_relative_RMS'])*100 for x in rr],ls='--',color='k',label='Persistence');ax.set(xlabel='Native ilev index',ylabel='Relative RMS [%]',title='Final-checkpoint detail; all29 layers retained, full history in figure03');ax.legend();save(fig,'03b_final_layer_detail.png')
 m=json.loads((ROOT/'experiments/fourcastden_den_engineering_v3/dataset_manifest.json').read_text())['frames']['2021']
 with np.load(ROOT/m[0]['path']) as n:p=n['DEN'][24].astype(float)*1000
 with np.load(ROOT/m[1]['path']) as n:t=n['DEN'][24].astype(float)*1000
 with np.load(O/'fixed_predictions_local.npz') as n:a=n['prediction_kg_m3'][-1,24]
 lat=np.asarray(json.loads((F/'plan.json').read_text())['training_config']['latitude_deg']);lon=np.load(ROOT/'data/processed/static/lon.npy');fig,axes=plt.subplots(1,4,figsize=(17,4));vmin=min(t.min(),p.min(),a.min());vmax=max(t.max(),p.max(),a.max())
 for i,(ax,data,title) in enumerate(zip(axes,[t,p,a,(a-t)/t*100],['TIE-GCM target','Persistence','AI step100','AI signed relative error'])):
  im=ax.pcolormesh(lon,lat,data,shading='auto',**({'vmin':vmin,'vmax':vmax} if i<3 else {'cmap':'RdBu_r'}));ax.set(title=title,xlabel='Longitude [deg]',ylabel='Latitude [deg]');fig.colorbar(im,ax=ax,label='DEN [kg/m3]' if i<3 else '%')
 fig.suptitle('2021-03-23 01 UTC, ilev24; final detail color scale excludes step0; see04 for full comparison');save(fig,'04b_fixed_final_detail.png')
