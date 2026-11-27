"""Render light scientific figures from V59's archived fields and metrics."""
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from run_native_density_baselines_v59 import OUT, LOCAL, METHODS, LEADS, SHAPE, read_csv


def main():
    rows=read_csv(OUT/'metrics.csv')
    own={(r['year'],int(r['horizon']),r['region'],r['ilev_index'],r['method']):r
         for r in rows if r['mask']=='own'}

    def values(metric,method,year='ALL',region='ALL',layer='ALL'):
        return [float(own[year,h,region,str(layer),method][metric]) for h in LEADS]

    plt.rcParams.update({'font.size': 9})
    fig,axes=plt.subplots(2,3,figsize=(12,6.7),layout='constrained')
    fig.suptitle('TIE-GCM MODEL-DENSITY HINDCAST | Autumn 2021–2022 | Native pressure grid')
    for m in METHODS:
        axes[0,0].plot(LEADS,values('mae',m),'o-',label=m)
        axes[0,1].plot(LEADS,values('rmse',m),'o-',label=m)
        axes[0,2].plot(LEADS,values('nonpositive',m),'o-',label=m)
        for i,region in enumerate(('low','mid','polar')):
            kwargs=dict(ls=['-','--',':'][i],alpha=.85)
            axes[1,0].plot(LEADS,values('relative_rmse',m,region=region),label=f'{m} / {region}',**kwargs)
        for year,ls in [('2021','-'),('2022','--')]:
            axes[1,1].plot(LEADS,values('rmse',m,year=year),ls=ls,marker='o',label=f'{m} / {year}')
    titles=[('MAE','kg/m³'),('RMSE','kg/m³'),('Nonpositive predictions','grid-point count'),
            ('Latitude bands relative RMSE','fraction'),('Year blocks RMSE','kg/m³')]
    for ax,(title,unit) in zip(axes.flat,titles):
        ax.set(title=title,ylabel=unit,xlabel='Lead (hours)',xticks=LEADS)
        ax.grid(alpha=.24)
    axes[0,0].legend()
    axes[1,0].legend(fontsize=6,ncols=2)
    axes[1,1].legend(fontsize=6,ncols=2)
    heat=np.column_stack([values('rmse',m,layer=j) for j in range(SHAPE[0]) for m in METHODS])
    heat=np.log10(heat.reshape(3,SHAPE[0],3).transpose(1,2,0).reshape(SHAPE[0],9))
    im=axes[1,2].imshow(heat,origin='lower',aspect='auto',cmap='viridis')
    axes[1,2].set(title='Layer RMSE',ylabel='Native ilev index',
                   xticks=range(9),xticklabels=[f'{m[0:2]}{h}h' for m in METHODS for h in LEADS])
    fig.colorbar(im,ax=axes[1,2],label='log₁₀ RMSE (kg/m³)')
    fig.savefig(OUT/'baseline_comparison.png',dpi=150)
    plt.close(fig)

    data=sorted(read_csv(OUT/'sample_manifest.csv'),key=lambda r:(r['cutoff_UTC'],int(r['horizon'])))
    s=next(r for r in data if r['cutoff_UTC']=='2021-09-23T06:00:00Z' and r['horizon']=='6')
    sid=s['sample_id']
    layer=15
    y=np.fromfile(LOCAL/'targets'/(sid+'.bin'),dtype='<f8').reshape(SHAPE)[layer]
    p=np.fromfile(LOCAL/'predictions'/(sid+'.bin'),dtype='<f8').reshape(3,*SHAPE)[:,layer]
    coords=json.loads((OUT/'native_grid.json').read_text())
    fig,axes=plt.subplots(2,4,figsize=(13,6),layout='constrained',sharex=True,sharey=True)
    fig.suptitle(f'TIE-GCM MODEL-DENSITY HINDCAST | Target {s["prediction_target_UTC"]} | native ilev={coords["ilev"][layer]:g}')
    levels=np.stack([y,*p])
    lo=np.min(levels[levels>0])
    hi=np.max(levels)
    from matplotlib.colors import LogNorm
    for i,(label,z) in enumerate(zip(('Model target',*METHODS),levels)):
        m=axes[0,i].pcolormesh(coords['lon'],coords['lat'],np.ma.masked_less_equal(z,0),
                              norm=LogNorm(vmin=lo,vmax=hi),cmap='viridis')
        axes[0,i].set_title(label)
    fig.colorbar(m,ax=axes[0,:],label='Density (kg/m³)')
    span=max(np.max(np.abs(p-y)),np.finfo(float).tiny)
    axes[1,0].axis('off')
    for i,z in enumerate(p,1):
        e=axes[1,i].pcolormesh(coords['lon'],coords['lat'],z-y,cmap='RdBu_r',vmin=-span,vmax=span)
        axes[1,i].set(title='Forecast − model target',xlabel='Longitude (°)')
    for ax in axes[:,0]:
        if ax.axison:
            ax.set_ylabel('Latitude (°)')
    fig.colorbar(e,ax=axes[1,1:],label='Error (kg/m³)')
    fig.savefig(OUT/'native_field_example.png',dpi=145)
    plt.close(fig)


if __name__=='__main__':
    main()
