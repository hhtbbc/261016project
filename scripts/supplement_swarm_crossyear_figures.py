"""Additional height and normalized-trend figures from saved arrays only."""
from pathlib import Path
import sys,csv,json
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_swarm_tiegcm_2022_observation import O,F,OLD,table
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    rr=list(csv.DictReader((O/'metrics.csv').open()));figs=[]
    def save(fig,name):
        if (O/name).exists():raise FileExistsError(name)
        fig.suptitle('2021/2022 Mar24 | Map A PROVISIONAL | DNSAPOD0301 | smin, 7-day warmup',fontsize=10);fig.tight_layout(rect=[0,0,1,.95]);fig.savefig(O/name,dpi=160);plt.close(fig);figs.append(name)
    bins=[f'height_{x}_{y}km' for x,y in zip([400,430,440,450,460,470],[430,440,450,460,470,500])]
    fig,axs=plt.subplots(1,2,figsize=(12,4))
    for ax,key in zip(axs,['relative_RMS','relative_bias']):
        for y in [2021,2022]:
            rows=[next(r for r in rr if r['year']==str(y) and r['mapping']=='A' and r['region']==b) for b in bins]
            yy=[float(r[key])*100 if r[key] else np.nan for r in rows]
            ax.plot(range(len(bins)),yy,'o-',label=str(y))
            for i,r in enumerate(rows):
                if r[key]:ax.annotate('N='+r['n'],(i,yy[i]),fontsize=7)
        ax.set_xticks(range(len(bins)),[b.replace('height_','').replace('_','-') for b in bins],rotation=45);ax.set_ylabel(key+' (%)');ax.legend();ax.set_xlabel('GRS80 observed altitude (km); N<30 => N/A')
    save(fig,'height_errors.png')
    old=np.load(OLD/'aligned_local.npz');new=np.load(O/'aligned_local.npz');fig,axs=plt.subplots(2,1,figsize=(12,7))
    for ax,year,z,obs,pred,utc in [(axs[0],2021,old,old['observed'],old['values'][0,0],old['utc']),(axs[1],2022,new,new['density'],new['values'][0],new['utc'])]:
        h=(utc-utc[0])/np.timedelta64(1,'h');m=z['common']
        # Separate per-series means: this displays shape only, never replaces original metrics.
        ax.plot(h,obs/obs[m].mean(),lw=.8,label=f'{year} Swarm / its own daily mean');ax.plot(h,pred/pred[m].mean(),lw=.8,label=f'{year} simulation / its own daily mean');ax.set_ylabel('Density / own mean (dimensionless)');ax.set_xlabel('UTC hour');ax.legend()
    save(fig,'normalized_density_trends.png')
    table(O/'supplement_figure_sources.csv',[dict(figure=n,source='metrics.csv;2021 frozen aligned_local.npz;2022 aligned_local.npz',status='PROVISIONAL;normalized trends shape-only, not bias correction') for n in figs])
if __name__=='__main__':main()
