"""Real Swarm 0301/retained prediction figures; no fitting or new forwards."""
from pathlib import Path
import csv,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
import prepare_fourcastden_swarm_observation_v1 as task
from analyze_fourcastden_swarm_observation_v1 import MODELS,FIELDS,MAPS,table
O=task.O;DAYS=('2023-01-04','2023-03-24');COLORS=dict(zip(MODELS,['tab:blue','tab:orange','tab:green','tab:red']))


def read(n):return list(csv.DictReader((O/n).open()))
def save(fig,name):
    p=task.inside(O/(name+'.png'))
    if p.exists():raise FileExistsError(p)
    fig.subplots_adjust(hspace=.48,wspace=.34,top=.86,bottom=.12)
    fig.text(.5,.01,'PROVISIONAL_OBSERVATION_COMPARISON | Swarm DNSAPOD 0301 | HINDCAST | not orbit accuracy',ha='center',fontsize=7)
    fig.savefig(p,dpi=170,bbox_inches='tight');plt.close(fig)


def main():
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    datasets={}
    for day in DAYS:
        with np.load(O/(day+'_aligned_local.npz'),allow_pickle=False) as n:datasets[day]={k:n[k].copy() for k in n.files}
    fig,axes=plt.subplots(2,1,figsize=(13,6))
    for ax,day in zip(axes,DAYS):
        d=datasets[day];h=d['hours'];obs=np.where(d['quality'],d['observed'],np.nan)
        ax.plot(h,obs/1e-12,color='black',lw=.8,label='Swarm instantaneous density, 0301')
        for mi,color in [(0,'tab:blue'),(1,'tab:orange')]:ax.plot(h,d['predictions'][mi,0]/1e-12,color=color,label='TIE-GCM reference / '+MAPS[mi])
        ax.set(title=day+'; original reference ZG, provisional coordinate mappings',ylabel='Density (1e-12 kg/m3)',xlabel='UTC hour');ax.legend(ncol=3);ax.grid(alpha=.2)
    fig.suptitle('Contemporaneous observations vs reference simulation; neither is absolute truth')
    save(fig,'Swarm_TIEGCM_reference_density')
    fig,axes=plt.subplots(2,2,figsize=(14,7))
    for row,day in enumerate(DAYS):
        d=datasets[day];h=d['hours']
        for col,scheme in enumerate(['Open','Updated']):
            ax=axes[row,col];ax.plot(h,d['observed']/1e-12,color='black',lw=.7,label='Swarm 0301')
            ax.plot(h,d['predictions'][0,0]/1e-12,color='grey',ls=':',label='TIE reference')
            for model in MODELS:ax.plot(h,d['predictions'][0,FIELDS.index(model+'_'+scheme)]/1e-12,color=COLORS[model],lw=1,label=model)
            ax.axvline(7,color='grey',ls='--');ax.set(title=day+' / '+scheme+' / mapping A',ylabel='Density (1e-12 kg/m3)',xlabel='UTC hour');ax.grid(alpha=.2)
    axes[0,0].legend(ncol=3,fontsize=8);fig.suptitle('Saved FourCastDEN fields queried along actual Swarm track; no new neural inference')
    save(fig,'four_models_alongtrack_A')
    hourly=read('hourly_metrics.csv');fig,axes=plt.subplots(2,2,figsize=(13,7),sharex=True)
    for ri,day in enumerate(DAYS):
        for ci,mp in enumerate(['A','B']):
            ax=axes[ri,ci]
            for model in MODELS:
                for scheme,ls in [('Open','-'),('Updated','--')]:
                    rows=[r for r in hourly if r['date']==day and r['mapping']==mp and r['field']==model+'_'+scheme]
                    ax.plot([int(r['hour_UTC']) for r in rows],[100*float(r['relative_RMS']) for r in rows],ls,marker='.',ms=4,color=COLORS[model],label=model+' '+scheme)
            ax.axvline(7,color='grey',ls=':');ax.set(title=day+' / hypothesis '+mp,ylabel='Relative RMS to Swarm (%)',xlabel='UTC hour bin (13: endpoint only)');ax.grid(alpha=.2)
    axes[0,0].legend(ncol=2,fontsize=7);fig.suptitle('Same common A/B sample set; 07 reset point excluded, hourly bins are correlated')
    save(fig,'observation_error_hourly_A_B')
    paired=read('paired_update_changes.csv');primary=[r for r in paired if r['domain']=='common_AB_all_models']
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for ax,day in zip(axes,DAYS):
        for mi,mp in enumerate(['A','B']):
            vals=[float(next(r for r in primary if r['date']==day and r['mapping']==mp and r['region']=='global' and r['model']==m)['relative_RMS_reduction_pct']) for m in MODELS]
            bars=ax.bar(np.arange(4)+(mi-.5)*.35,vals,.35,label=mp)
            for b,v in zip(bars,vals):ax.annotate(f'{v:.1f}',(b.get_x()+b.get_width()/2,v),ha='center',va='bottom' if v>=0 else 'top',fontsize=8)
        ax.axhline(0,color='black',lw=.8);ax.set(xticks=np.arange(4),xticklabels=MODELS,ylabel='Relative RMS reduction (%)',title=day+' 08-13 UTC');ax.legend();ax.grid(axis='y',alpha=.2)
    fig.suptitle('Ideal update improves A, but can worsen B: do not select the better mapping after seeing errors')
    save(fig,'post_update_gain_A_B')
    fig,axes=plt.subplots(2,2,figsize=(12,7))
    for ri,day in enumerate(DAYS):
        for ci,mp in enumerate(['A','B']):
            ax=axes[ri,ci]
            for mi,m in enumerate(MODELS):
                vals=[float(next(r for r in primary if r['date']==day and r['mapping']==mp and r['region']==reg and r['model']==m)['relative_RMS_reduction_pct']) for reg in ['south','north','midlow']]
                ax.bar(np.arange(3)+(mi-1.5)*.18,vals,.18,color=COLORS[m],label=m)
            ax.axhline(0,color='black',lw=.7);ax.set(xticks=np.arange(3),xticklabels=['South <=-60','North >=60','Mid/low'],ylabel='Relative RMS reduction (%)',title=day+' / '+mp);ax.grid(axis='y',alpha=.2)
    axes[0,0].legend(ncol=4,fontsize=7);fig.suptitle('08-13 UTC regional conditional observation comparison: negative = worsening')
    save(fig,'regional_observation_update_gain')
    geo=read('geometry_local.csv');fig,axes=plt.subplots(2,3,figsize=(14,7))
    for row,day in enumerate(DAYS):
        g=[r for r in geo if r['date']==day];s=read(day+'_coordinate_density_sensitivity_local.csv');good=[r for r in s if r['all_maps_reference_valid']=='True']
        axes[row,0].plot([float(r['A_height_m'])/1000 for r in g],[float(r['delta_height_m'])/1000 for r in g],'.',ms=2)
        axes[row,0].set(xlabel='Satellite WGS84 height (km)',ylabel='B-A assumed native height (km)',title=day)
        for key,label in [('latitude_only_relative','latitude only'),('height_only_relative','height only'),('combined_relative','combined')]:
            axes[row,1].plot([float(g[int(r['sample'])]['A_latitude_deg']) for r in good],[100*float(r[key]) for r in good],'.',ms=2,label=label)
        axes[row,1].set(xlabel='WGS84 latitude (deg)',ylabel='Reference density response (%)')
        axes[row,2].scatter([float(g[int(r['sample'])]['A_height_m'])/1000 for r in good],[100*float(r['combined_relative']) for r in good],s=3)
        axes[row,2].set(xlabel='Satellite WGS84 height (km)',ylabel='Reference B/A - 1 (%)')
    axes[0,1].legend(fontsize=8);fig.suptitle('Same actual track; A/B/D/E conditional sensitivities, not datum error bounds')
    save(fig,'coordinate_sensitivity_same_track')
    validity=read('query_validity.csv');fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for ax,day in zip(axes,DAYS):
        a=np.array([[100*float(next(r for r in validity if r['date']==day and r['period']=='post' and r['region']=='global' and r['mapping']==mp and r['field']==field)['valid_fraction']) for mp in ['A','B']] for field in FIELDS])
        im=ax.imshow(a,aspect='auto',vmin=0,vmax=100,cmap='YlGn');ax.set(xticks=[0,1],xticklabels=['A','B'],yticks=range(9),yticklabels=FIELDS,title=day+' 08-13UTC')
        for i in range(9):
            for j in range(2):ax.text(j,i,f'{a[i,j]:.2f}%',ha='center',va='center')
    fig.colorbar(im,ax=axes.ravel().tolist(),label='Quality-eligible query validity (%)');fig.suptitle('Rejected columns retained; primary metrics use identical intersection for every model')
    save(fig,'query_validity_by_model')
    events=read('event_07_left_right_local.csv');fig,axes=plt.subplots(2,2,figsize=(12,7))
    for ri,day in enumerate(DAYS):
        for ci,mp in enumerate(['A','B']):
            ax=axes[ri,ci];rr=[r for r in events if r['date']==day and r['mapping']==mp]
            for si,side in enumerate(['left','right']):
                vals=[float(next(r for r in rr if r['model']==m and r['event_side']==side)['rho_kg_m3'])/1e-12 for m in MODELS]
                ax.bar(np.arange(4)+(si-.5)*.32,vals,.32,label=side)
            ax.axhline(float(rr[0]['observed_density_kg_m3'])/1e-12,color='black',label='Swarm actual 07:00')
            ax.set(xticks=np.arange(4),xticklabels=MODELS,title=day+' / '+mp,ylabel='Density (1e-12 kg/m3)');ax.legend(fontsize=8)
    fig.suptitle('07 UTC actual track: distinct atmospheric limits; reset point is not forecast improvement')
    save(fig,'observation_event_seam')
    summary=read('interpolation_sensitivity_summary.csv');keys=['time_log_vs_linear_relative','horizontal_log_vs_linear_relative','vertical_linear_vs_log_relative','vertical_coarsened_log_relative','height_plus_1km_relative']
    fig,ax=plt.subplots(figsize=(12,4))
    for i,day in enumerate(DAYS):
        vals=[100*float(next(r for r in summary if r['date']==day and r['metric']==k)['absolute_P95']) for k in keys]
        ax.bar(np.arange(len(keys))+(i-.5)*.35,vals,.35,label=day)
    ax.set(xticks=range(len(keys)),xticklabels=['Time log vs linear','Horizontal log vs linear','Vertical linear vs log','Coarse vertical grid','Height +1km'],ylabel='Absolute conditional response P95 (%)')
    ax.legend();ax.grid(axis='y',alpha=.2);ax.set_title('Reference along-track sensitivity only; unknown datum/inversion/model errors NOT bounded or summed')
    save(fig,'calculable_sensitivity_budget')
    # Publication is limited to aggregate/derived indicators, not source CDF or
    # complete pointwise density/position tables.
    print('9 actual-data PNGs written')


if __name__=='__main__':main()
