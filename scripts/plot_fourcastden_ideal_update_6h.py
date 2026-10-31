"""Figures from actual saved arrays/CSV; no smoothing or extra inference."""
from pathlib import Path
import sys,csv,json
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
import run_fourcastden_ideal_update_6h as run
from fourcastden.logden import decode_physical
from fourcastden.ideal_update import improvement_percent
F,O,D=run.F,run.O,run.D


def read(name):
    with (O/name).open() as f:return list(csv.DictReader(f))
def save(fig,name,title):
    fig.suptitle(title+'\nOffline ideal TIE-GCM reference-state update at 07 UTC; HINDCAST; not observation assimilation',fontsize=11)
    fig.tight_layout(rect=[0,0,1,.92]);p=O/(name+'.png');assert not p.exists();fig.savefig(p,dpi=160);plt.close(fig)


def main():
    rows=read('metrics.csv');pair=read('paired_changes.csv');layers=read('layer_metrics.csv');cons=read('physical_consistency.csv');jump=read('jump_at_update.csv')
    def select(day,model,scheme,variable='DEN',group='near400_500',region='global'):
        return sorted([x for x in rows if x['date']==day and x['model']==model and x['scheme']==scheme and x['variable']==variable and x['group']==group and x['region']==region and x['domain']=='pressure_valid'],key=lambda x:int(x['original_lead']))
    for field,group,unit,name in [('mean_layer_relative_RMS','near400_500','Mean layer DEN relative RMS (%)','near_density_error_curves'),('mean_layer_RMSE','all','Mean layer DEN RMSE (kg/m3)','absolute_density_error_curves')]:
        fig,axs=plt.subplots(2,4,figsize=(18,8))
        for j,day in enumerate(run.DATES):
            for k,model in enumerate(run.MODELS):
                ax=axs[j,k]
                for scheme,style in [('Open','o-'),('Updated','s--')]:
                    z=select(day,model,scheme,group=group);lookup={int(x['original_lead']):float(x[field]) for x in z}
                    x=np.arange(1,13);y=[lookup.get(h,np.nan)*(100 if 'relative' in field else 1) for h in x]
                    ax.plot(x+1,y,style,label='Open-loop +1..12h' if scheme=='Open' else 'Ideal update; post-reset +1..6h')
                ax.axvline(7,color='gray',ls=':');ax.set(title=day+' '+model,xlabel='Target UTC hour',ylabel=unit,xticks=[2,4,7,10,13])
                ax.text(.02,.97,'07 reset score excluded',transform=ax.transAxes,va='top',fontsize=8)
        axs[0,0].legend(fontsize=7);save(fig,name,'DEN against TIE-GCM reference; native pressure groups (not a fixed-altitude error)')
    iv=np.load(ROOT/'data/processed/static/ilev.npy');fig,axs=plt.subplots(2,4,figsize=(18,8))
    for j,day in enumerate(run.DATES):
        for k,model in enumerate(run.MODELS):
            ax=axs[j,k]
            for scheme in ('Open','Updated'):
                z=sorted([x for x in layers if x['date']==day and x['model']==model and x['scheme']==scheme and x['variable']=='DEN' and x['region']=='global' and x['target_hour_UTC']=='13'],key=lambda x:int(x['layer_index']))
                ax.plot([100*float(x['relative_RMS']) for x in z],iv,label=scheme)
            ax.set(title=day+' '+model+' 13 UTC',xlabel='DEN relative RMS (%)',ylabel='Native ilev (not altitude)')
    axs[0,0].legend();save(fig,'density_layer_profiles_13UTC','Open +12h versus ideal-updated +6h: every original pressure interface')
    fig,axs=plt.subplots(1,2,figsize=(13,5))
    for ax,day in zip(axs,run.DATES):
        values=np.array([[float(next(x for x in pair if x['date']==day and x['model']==m and x['original_lead']=='12' and x['variable']=='DEN' and x['region']==region and x['group']=='near400_500' and x['domain']=='pressure_valid')['improvement_pct_mean_layer_relative_RMS']) for region in ('global','south','north','midlow')] for m in run.MODELS])
        scale=max(1.,abs(values).max());im=ax.imshow(values,vmin=-scale,vmax=scale,cmap='RdBu')
        for (j,k),v in np.ndenumerate(values):ax.text(k,j,f'{v:+.1f}%',ha='center',va='center',color='black' if abs(v)<.7*scale else 'white')
        ax.set(xticks=range(4),xticklabels=['Global','South >=60deg','North >=60deg','Mid/low'],yticks=range(4),yticklabels=run.MODELS,title=day+' 13 UTC');fig.colorbar(im,ax=ax,label='Relative RMS reduction (%)')
    save(fig,'regional_density_gain_13UTC','DEN reference-400-500km layer group; negative values mean deterioration')
    fig,ax=plt.subplots(figsize=(12,6));labels=[d+' '+m for d in run.DATES for m in run.MODELS]
    values=np.array([[float(next(x for x in pair if x['date']==d and x['model']==m and x['original_lead']=='12' and x['variable']==v and x['region']=='global' and x['group']=='all' and x['domain']=='pressure_valid')['improvement_pct_mean_layer_RMSE']) for v in run.NAMES] for d in run.DATES for m in run.MODELS])
    im=ax.imshow(values,cmap='RdBu',vmin=-100,vmax=100)
    for (j,k),v in np.ndenumerate(values):ax.text(k,j,f'{v:+.1f}%',ha='center',va='center')
    ax.set(xticks=range(6),xticklabels=['TN (K)','UN (m/s)','VN (m/s)','WN (m/s)','Z (m)','DEN (kg/m3)'],yticks=range(8),yticklabels=labels);fig.colorbar(im,ax=ax,label='Mean layer RMSE reduction (%)')
    save(fig,'six_variable_gain_13UTC','13 UTC: each variable evaluated separately; no sum across physical units')
    fig,axs=plt.subplots(2,6,figsize=(20,8));units=('K','m/s','m/s','m/s','m','kg/m3')
    for j,day in enumerate(run.DATES):
        for k,(var,unit) in enumerate(zip(run.NAMES,units)):
            z=[next(x for x in jump if x['date']==day and x['model']==m and x['variable']==var and x['region']=='global' and x['state_role']=='current07') for m in run.MODELS]
            axs[j,k].bar(range(4),[float(x['actual_update_RMSE']) for x in z]);axs[j,k].set(title=day+' '+var,xlabel='Model',ylabel='07 UTC jump RMS ('+unit+')',xticks=range(4),xticklabels=run.MODELS);axs[j,k].tick_params(axis='x',rotation=65)
    save(fig,'state_jump_07UTC','Actual pre-/post-update state difference; not forecast performance')
    fig,axs=plt.subplots(2,4,figsize=(18,8))
    for j,day in enumerate(run.DATES):
        for k,m in enumerate(run.MODELS):
            for scheme in ('Open','Updated'):
                z=sorted([x for x in cons if x['date']==day and x['model']==m and x['scheme']==scheme and x['region']=='global' and int(x['original_lead'])>=1],key=lambda x:int(x['original_lead']))
                axs[j,k].plot([int(x['target_hour_UTC']) for x in z],[int(x['height_invalid_columns']) for x in z],'o-' if scheme=='Open' else 's--',label=scheme)
            axs[j,k].axvline(7,color='gray',ls=':');axs[j,k].set(title=day+' '+m,xlabel='Target UTC hour',ylabel='Invalid native-height columns')
    axs[0,0].legend();save(fig,'thermodynamic_consistency','Reused fixed mass-range/monotonicity diagnostic; not negative-density counts')
    fig,axs=plt.subplots(2,2,figsize=(13,9))
    for j,day in enumerate(run.DATES):
        for k,(group,field,scale,unit) in enumerate([('near400_500','mean_layer_relative_RMS',100,'DEN relative RMS (%)'),('all','mean_layer_RMSE',1,'DEN mean layer RMSE (kg/m3)')]):
            for scheme,offset in [('Open',-.18),('Updated',.18)]:
                vals=[float(next(x for x in select(day,m,scheme,group=group) if x['target_hour_UTC']=='13')[field])*scale for m in run.MODELS]
                axs[j,k].bar(np.arange(4)+offset,vals,.36,label=scheme)
            axs[j,k].set(title=day+' 13 UTC | '+group,ylabel=unit,xticks=range(4),xticklabels=run.MODELS);axs[j,k].legend()
    save(fig,'model_effect_summary','All four models and both preselected dates; +12h open versus +6h after ideal update')
    # Absolute physical DEN and signed relative errors, all three fields shown.
    lon=np.load(ROOT/'data/processed/static/lon.npy');lat=np.load(ROOT/'data/processed/static/lat.npy')
    for day in run.DATES:
        truth=run.reference(day,13)[0][142+22]*1000
        for model in run.MODELS:
            old=run.load_old(day,model,('pred','means','stds'))
            op=decode_physical(old['pred'][0,12],old['means'][:171],old['stds'][:171],model=='LogDEN')[142+22]*1000
            with np.load(D/f'{day}_{model}.npz') as n:up=decode_physical(n['pred'][0,6],n['means'][:171],n['stds'][:171],model=='LogDEN')[142+22]*1000
            fig,axs=plt.subplots(2,3,figsize=(14,7));lo=min(v.min() for v in (truth,op,up));hi=max(v.max() for v in (truth,op,up))
            for ax,data,title in zip(axs[0],(truth,op,up),('TIE reference','Open-loop +12h','Ideal update at07; +6h')):
                im=ax.pcolormesh(lon,lat,data,shading='auto',vmin=lo,vmax=hi);ax.set(title=title,xlabel='Longitude',ylabel='Model latitude');fig.colorbar(im,ax=ax,label='DEN (kg/m3)')
            axs[1,0].axis('off');axs[1,0].text(.02,.65,'Fixed native interface index22\nNot fixed 450km\nSigned relative errors below\nReference: original author TIE-GCM',fontsize=11)
            limit=max(abs((op/truth-1)*100).max(),abs((up/truth-1)*100).max())
            for ax,v,title in zip(axs[1,1:],(op,up),('Open relative error','Updated relative error')):
                im=ax.pcolormesh(lon,lat,100*(v/truth-1),vmin=-limit,vmax=limit,cmap='RdBu_r',shading='auto');ax.set(title=title,xlabel='Longitude',ylabel='Model latitude');fig.colorbar(im,ax=ax,label='Signed DEN error (%)')
            save(fig,f'{day}_{model}_DEN13UTC_maps',day+' 13 UTC '+model+' | Native ilev index22='+str(iv[22]))
    # Preserve all aggregate deteriorations, instead of choosing favorable cells.
    adverse=[]
    for row in pair:
        if row['domain']!='pressure_valid':continue
        for field in ('mean_layer_RMSE','mean_layer_relative_RMS','relative_P95'):
            value=row['improvement_pct_'+field]
            if value and float(value)<0:
                adverse.append({k:row[k] for k in ('date','model','original_lead','target_hour_UTC','region','variable','group')}|dict(metric=field,open_value=row['open_'+field],updated_value=row['updated_'+field],change_percent=-float(value)))
    run.csvout(O/'adverse_aggregate_cases.csv',adverse)
    print('Created 16 figures; adverse aggregate metric entries:',len(adverse))


if __name__=='__main__':main()
