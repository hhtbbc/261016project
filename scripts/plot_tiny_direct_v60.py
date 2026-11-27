"""Plot frozen metrics and one authorized native pressure-level example."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

import run_native_density_baselines_v59 as v59
from train_tiny_direct_v60 import OUT, LOCAL
from evaluate_tiny_direct_v60 import METHODS


def run():
    rows=v59.read_csv(OUT/'metrics.csv')
    lookup={(r['year'],r['horizon'],r['method'],r['ilev_index'],r['region']):r
            for r in rows if r['mask']=='common'}
    leads=['1','3','6']
    fig,axes=plt.subplots(2,2,figsize=(9,6.5),layout='constrained')
    fig.suptitle('2022 autumn engineering validation | TIE-GCM model density')
    for method in METHODS:
        for i,metric in enumerate(('rmse','log_rmse')):
            values=[float(lookup['2022',h,method,'ALL','ALL'][metric]) for h in leads]
            axes[0,i].plot(leads,values,'o-',label=method)
    axes[0,0].set(title='Global RMSE',ylabel='kg/m³',xlabel='Lead (h)')
    axes[0,1].set(title='Global log RMSE',xlabel='Lead (h)')
    axes[0,0].legend(fontsize=8)
    for h in leads:
        v=np.array([float(lookup['2022',h,METHODS[-1],str(l),'ALL']['log_rmse'])/
                   float(lookup['2022',h,METHODS[0],str(l),'ALL']['log_rmse']) for l in range(29)])
        axes[1,0].plot(range(29),v,label=f'{h} h')
    axes[1,0].axhline(1,color='black',ls=':')
    axes[1,0].set(title='Layer log RMSE ratio (Direct / Persistence)',xlabel='Native ilev index')
    axes[1,0].legend(fontsize=8)
    train=v59.read_csv(OUT/'training_log.csv')
    steps=np.array([float(r['loss']) for r in train])
    axes[1,1].plot(range(1,len(train)+1),steps,alpha=.45,label='Cutoff update')
    axes[1,1].plot(range(4,81,4),steps.reshape(-1,4).mean(1),label='Four-cutoff mean')
    axes[1,1].set(title='2021 training log-MAE',xlabel='Update')
    axes[1,1].legend(fontsize=8)
    for ax in axes.flat:
        ax.grid(alpha=.2)
    fig.savefig(OUT/'comparison_and_loss.png',dpi=153)
    plt.close(fig)

    rows=v59.read_csv(OUT/'sample_scope.csv')
    test=next(r for r in rows if r['cutoff_UTC']=='2022-09-23T06:00:00Z' and r['horizon']=='6')
    sid=test['sample_id']
    layer=10
    coords=json.loads((v59.OUT/'native_grid.json').read_text())
    truth=np.fromfile(v59.LOCAL/'targets'/(sid+'.bin'),dtype='<f8').reshape(v59.SHAPE)[layer]
    direct=np.fromfile(LOCAL/'inference'/(sid+'.bin'),dtype='<f8').reshape(v59.SHAPE)[layer]
    base=np.fromfile(v59.LOCAL/'predictions'/(sid+'.bin'),dtype='<f8').reshape(3,*v59.SHAPE)[0,layer]
    fig,axs=plt.subplots(1,4,figsize=(12,3.6),layout='constrained',sharex=True,sharey=True)
    fig.suptitle(f'TIE-GCM model density | {test["prediction_target_UTC"]} | native ilev={coords["ilev"][layer]:g}')
    dens_args=dict(vmin=min(truth.min(),direct.min()),vmax=max(truth.max(),direct.max()),cmap='viridis')
    errors=[np.log(direct/truth),np.log(base/truth)]
    lim=max(float(abs(x).max()) for x in errors)
    for i,(title,z) in enumerate([('Model target',truth),('Direct',direct),('Direct log residual',errors[0]),
                                  ('Persistence log residual',errors[1])]):
        img=axs[i].pcolormesh(coords['lon'],coords['lat'],z,**(dens_args if i<2 else
                                 dict(vmin=-lim,vmax=lim,cmap='RdBu_r')))
        axs[i].set(title=title,xlabel='Longitude (°)')
        if i in (1,3):
            fig.colorbar(img,ax=axs[i-1:i+1],label='kg/m³' if i==1 else 'ln(forecast / target)')
    axs[0].set_ylabel('Latitude (°)')
    fig.savefig(OUT/'density_and_residual.png',dpi=150)


if __name__=='__main__':
    run()
