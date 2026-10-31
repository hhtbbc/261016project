"""Measured SP3/DNS geometry and cached residual-budget figures only."""
from pathlib import Path
import csv,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from prepare_swarm_coordinate_orbit_v1 import O
DAYS=('2023-01-04','2023-03-24');MODELS=('Direct','Flow','LogDEN','History')
def read(n):return list(csv.DictReader((O/n).open()))
def save(fig,name):
    p=O/(name+'.png');p.resolve().relative_to(ROOT)
    if p.exists():raise FileExistsError(p)
    fig.subplots_adjust(hspace=.45,wspace=.35,top=.86,bottom=.14)
    fig.text(.5,.01,'SP3 0203 / DNSAPOD 0301 | retrospective | nominal Earth-fixed realization / provisional model datum | not orbit prediction error',ha='center',fontsize=7)
    fig.savefig(p,dpi=170,bbox_inches='tight');plt.close(fig)


def main():
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(2,2,figsize=(13,7))
    for row,day in enumerate(DAYS):
        rr=read(day+'_geometry_local.csv');x=[1+int(r['sample'])/120 for r in rr]
        axes[row,0].plot(x,[float(r['position_difference_m']) for r in rr]);axes[row,0].set(title=day+' | SP3 minus DNS position',ylabel='3D distance (m)',xlabel='UTC hour')
        axes[row,1].plot(x,[float(r['height_difference_GRS80_m']) for r in rr]);axes[row,1].axhline(0,color='grey',lw=.6);axes[row,1].set(title=day+' | common GRS80 ellipsoid',ylabel='Signed height difference (m)',xlabel='UTC hour')
        for ax in axes[row]:ax.grid(alpha=.2)
    fig.suptitle('Contemporaneous actual products: metre-level geometry difference after explicit GPS-to-UTC conversion')
    save(fig,'DNS_SP3_geometry_alignment')
    fig,axes=plt.subplots(2,2,figsize=(13,7))
    for row,day in enumerate(DAYS):
        rr=read(day+'_geometry_local.csv');x=[1+int(r['sample'])/120 for r in rr]
        for col,key in enumerate(['latitude_difference_deg','longitude_difference_deg']):
            axes[row,col].plot(x,[float(r[key])*3600 for r in rr]);axes[row,col].set(title=day+' | '+key.split('_')[0],xlabel='UTC hour',ylabel='Angular difference (arcsec)');axes[row,col].grid(alpha=.2)
    fig.suptitle('Geodetic differences; polar longitude angle is not a direct horizontal distance')
    save(fig,'DNS_SP3_geodetic_differences')
    b=read('residual_budget.csv');fig,axes=plt.subplots(2,2,figsize=(13,7))
    for row,day in enumerate(DAYS):
        for col,mp in enumerate(['A','B']):
            ax=axes[row,col];base=[r for r in b if r['date']==day and r['mapping']==mp and r['region']=='global' and r['period']=='post']
            for j,(scheme,target,label) in enumerate([('Open','RMSE_AI_Swarm','Open vs Swarm'),('Updated','RMSE_AI_Swarm','Updated vs Swarm'),('Open','RMSE_AI_TIE','Open vs TIE'),('Updated','RMSE_AI_TIE','Updated vs TIE')]):
                vals=[float(next(r for r in base if r['scheme']==scheme and r['model']==m)[target])*1e13 for m in MODELS]
                ax.bar(np.arange(4)+(j-1.5)*.18,vals,.18,label=label)
            ax.axhline(float(base[0]['RMSE_TIE_Swarm'])*1e13,color='black',ls=':',label='TIE vs Swarm')
            ax.set(xticks=range(4),xticklabels=MODELS,ylabel='RMSE (1e-13 kg/m3)',title=day+' | mapping '+mp+' | 08-13UTC');ax.grid(axis='y',alpha=.2)
    axes[0,0].legend(ncol=2,fontsize=7);fig.suptitle('Three queried densities on identical valid observations; RMSEs are not additive')
    save(fig,'threeway_density_RMSE')
    fig,axes=plt.subplots(2,2,figsize=(12,7))
    for row,day in enumerate(DAYS):
        for col,mp in enumerate(['A','B']):
            ax=axes[row,col];rr=[next(r for r in b if r['date']==day and r['mapping']==mp and r['region']=='global' and r['period']=='post' and r['model']=='Direct' and r['scheme']==s) for s in ['Open','Updated']]
            pos=np.zeros(2);neg=np.zeros(2)
            for key,label,color in [('relative_MSE_AI_TIE','AI-TIE squared','tab:blue'),('relative_MSE_TIE_Swarm','TIE-Swarm squared','tab:orange'),('relative_cross_term','Signed cross term','tab:green')]:
                x=np.array([float(r[key])*1e4 for r in rr]);bottom=np.where(x>=0,pos,neg);ax.bar([0,1],x,bottom=bottom,label=label,color=color,width=.5)
                pos+=np.maximum(x,0);neg+=np.minimum(x,0)
            ax.scatter([0,1],[float(r['relative_MSE_AI_Swarm'])*1e4 for r in rr],color='black',zorder=5,label='Total AI-Swarm MSE')
            ax.axhline(0,color='grey',lw=.8);ax.set(xticks=[0,1],xticklabels=['Open','Updated'],ylabel='Relative MSE (% squared)',title=day+' | Direct | '+mp);ax.grid(axis='y',alpha=.2)
    axes[0,0].legend(fontsize=7,ncol=2);fig.suptitle('Exact residual identity: loss of bias cancellation can reverse observation comparison')
    save(fig,'signed_MSE_cross_term')
    blocks=read('fixed_hour_blocks.csv');acf=read('descriptive_ACF.csv');fig,axes=plt.subplots(2,2,figsize=(13,7))
    for row,day in enumerate(DAYS):
        for mp,color in [('A','tab:blue'),('B','tab:orange')]:
            for scheme,ls in [('Open','-'),('Updated','--')]:
                rr=[r for r in blocks if r['date']==day and r['model']=='Direct' and r['mapping']==mp and r['scheme']==scheme]
                axes[row,0].plot([int(r['hour_UTC']) for r in rr],[100*np.sqrt(float(r['relative_MSE_AI_Swarm'])) for r in rr],ls,marker='.',color=color,label=mp+' '+scheme)
                cc=[r for r in acf if r['date']==day and r['model']=='Direct' and r['mapping']==mp and r['scheme']==scheme]
                axes[row,1].plot([float(r['lag_seconds'])/60 for r in cc],[float(r['correlation']) for r in cc],ls,color=color,label=mp+' '+scheme)
        axes[row,0].set(title=day+' | fixed 1h UTC blocks',xlabel='UTC hour-start',ylabel='Relative RMS to Swarm (%)');axes[row,0].axvline(7,color='grey',ls=':')
        axes[row,1].set(title=day+' | 08-13UTC contiguous pairs only',xlabel='Lag (min)',ylabel='Descriptive autocorrelation');axes[row,1].axhline(np.exp(-1),color='grey',ls=':');axes[row,1].axhline(0,color='grey',lw=.5)
        for ax in axes[row]:ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=7,ncol=2);fig.suptitle('Strong serial dependence: no claim that 30-second points are independent experiments')
    save(fig,'time_blocks_and_autocorrelation')
    print('5 data-driven figures written')


if __name__=='__main__':main()
