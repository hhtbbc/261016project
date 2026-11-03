"""Eight figures from actual saved 12h propagation; mark numerical failure."""
from pathlib import Path
import sys,csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_fourcastden_orbit_update_12h_v1 import F,O
from prepare_fourcastden_swarm_observation_v1 import sha
from analyze_fourcastden_swarm_observation_v1 import table
GROUPS=['B_Open','C_Updated','D_Reference'];COLORS=['tab:blue','tab:orange','tab:green']
def read(name):return list(csv.DictReader((O/name).open()))
def configure(ax,ylabel,title):
    ax.axvline(7,color='grey',ls=':',label='07UTC atmosphere update');ax.set(xlabel='2023-01-04 UTC hour',ylabel=ylabel,title=title);ax.grid(alpha=.2)
    ax.legend(fontsize=8)
def main():
    gates=json.loads((F/'analysis.json').read_text())['gates'];passed=gates['ORBIT_NUMERICAL_CONVERGENCE_READY']=='PASS';figures=[]
    def save(fig,name,source):
        path=O/(name+'.png');assert not path.exists();fig.subplots_adjust(hspace=.42,wspace=.32,top=.84,bottom=.25)
        status='Frozen numerical gates PASS' if passed else 'NUMERICAL GATE FAIL: conditional trajectories not numerically qualified'
        fig.suptitle(status,fontsize=12,color='black' if passed else 'crimson',y=.985)
        fig.text(.5,.02,'2023-01-04 | coordinate A PROVISIONAL | synthetic m400kg/A1m2/Cd2.2, zero ITRS wind | HINDCAST\nConditional model trajectory differences; D=TIE-GCM density-driven model, not observed orbit truth',ha='center',fontsize=8)
        fig.savefig(path,dpi=170,bbox_inches='tight');plt.close(fig);figures.append(dict(figure=path.name,SHA256=sha(path),source=source,UTC='2023-01-04 01:00-13:00',numerical_gate=gates['ORBIT_NUMERICAL_CONVERGENCE_READY']))
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    data={g:read(g+'_tight_samples.csv') for g in GROUPS};events={r['group']:r for r in read('event_density_drag_jump.csv') if r['mode']=='tight'}
    for field,lef,name,ylabel in [('rho_kg_m3','rho_left_kg_m3','density_12h','Density (kg/m3)'),('drag_norm_m_s2','drag_left_m_s2','drag_12h','Drag acceleration norm (m/s2)')]:
        fig,ax=plt.subplots(figsize=(12,4))
        for g,c in zip(GROUPS,COLORS):
            rr=data[g];x=np.array([1+float(r['seconds'])/3600 for r in rr]);y=np.array([float(r[field]) for r in rr])
            if g=='C_Updated':ax.plot(np.r_[x[x<7],7],np.r_[y[x<7],float(events[g][lef])],color=c,label=g+' before');ax.plot(x[x>=7],y[x>=7],color=c,ls='--',label=g+' after')
            else:ax.plot(x,y,color=c,label=g)
        if field=='rho_kg_m3':ax.text(.01,.04,'NoDrag: density not used (not a zero-density atmosphere)',transform=ax.transAxes)
        else:ax.axhline(0,color='k',lw=.6,label='NoDrag applied acceleration=0')
        configure(ax,ylabel,'Direct/reference density evaluated on each own propagated trajectory');save(fig,name,'*_tight_samples.csv;event_density_drag_jump.csv')
    curves=read('pair_curves.csv');primary=['C_Updated minus B_Open','B_Open minus D_Reference','C_Updated minus D_Reference']
    def curve(p):return [r for r in curves if r['mode']=='tight' and r['comparison']==p]
    fig,axes=plt.subplots(2,1,figsize=(12,7));rr=curve(primary[0]);x=[float(r['UTC_hour']) for r in rr]
    axes[0].plot(x,[float(r['norm_m']) for r in rr],label=primary[0]);axes[1].plot(x,[float(r['speed_norm_m_s']) for r in rr],label='Velocity difference norm')
    configure(axes[0],'Position difference (m)','Ideal update minus open-loop');configure(axes[1],'Velocity difference (m/s)','No satellite position or velocity reset');save(fig,'updated_minus_open','pair_curves.csv')
    fig,axes=plt.subplots(2,1,figsize=(12,7))
    for p,c in zip(primary[1:],['tab:blue','tab:orange']):
        rr=curve(p);x=[float(r['UTC_hour']) for r in rr];axes[0].plot(x,[float(r['norm_m']) for r in rr],label=p,color=c);axes[1].plot(x,[float(r['speed_norm_m_s']) for r in rr],label=p,color=c)
    configure(axes[0],'Position difference (m)','Differences relative to TIE-GCM conditional orbit');configure(axes[1],'Velocity difference (m/s)','Full window, no selection of favorable epochs');save(fig,'reference_orbit_differences','pair_curves.csv')
    fig,axes=plt.subplots(3,1,figsize=(12,9))
    for ax,k in zip(axes,'RAC'):
        for p,c in zip(primary,COLORS):
            rr=curve(p);ax.plot([float(r['UTC_hour']) for r in rr],[float(r['RAC_'+k+'_m']) for r in rr],label=p,color=c)
        configure(ax,k+' difference (m)','Common NoDrag RAC basis; not force-direction decomposition')
    save(fig,'RAC_12h','pair_curves.csv')
    fig,axes=plt.subplots(2,2,figsize=(12,7));rr=data['C_Updated'];x=np.array([float(r['seconds'])-21600 for r in rr]);j=events['C_Updated']
    for ax,field,left,ylabel in [(axes[0,0],'rho_kg_m3','rho_left_kg_m3','Density (kg/m3)'),(axes[0,1],'drag_norm_m_s2','drag_left_m_s2','Drag norm (m/s2)')]:
        y=np.array([float(r[field]) for r in rr]);a=(x>=-600)&(x<0);b=(x>=0)&(x<=600);ax.plot(np.r_[x[a],0],np.r_[y[a],float(j[left])],'o-',label='left state');ax.plot(x[b],y[b],'s--',label='right state');ax.axvline(0,color='grey',ls=':');ax.set(xlabel='Seconds relative to07UTC',ylabel=ylabel);ax.legend();ax.grid(alpha=.2)
    rr=curve(primary[0]);x=np.array([float(r['seconds'])-21600 for r in rr]);mask=(x>=-600)&(x<=600)
    for ax,key,label in [(axes[1,0],'norm_m','Position difference (m)'),(axes[1,1],'speed_norm_m_s','Velocity difference (m/s)')]:
        y=np.array([float(r[key]) for r in rr]);ax.plot(x[mask],y[mask],label='Updated minus Open');ax.set(xlabel='Seconds relative to07UTC',ylabel=label);ax.axvline(0,color='grey',ls=':');ax.legend();ax.grid(alpha=.2)
    axes[1,0].text(.02,.9,'Exact state handoff: position jump=0 m',transform=axes[1,0].transAxes);axes[1,1].text(.02,.9,'Exact state handoff: velocity jump=0 m/s',transform=axes[1,1].transAxes);save(fig,'event_07UTC_detail','C_Updated_tight_samples.csv;event_density_drag_jump.csv;pair_curves.csv')
    fig,axes=plt.subplots(1,2,figsize=(12,4));blocks=read('time_block_summary.csv');xx=np.arange(4)
    for i,p in enumerate(primary):
        rr=[r for r in blocks if r['mode']=='tight' and r['comparison']==p];axes[0].bar(xx+(i-1)*.24,[float(r['RMS_m']) for r in rr],width=.24,label=p,color=COLORS[i]);axes[1].bar(xx+(i-1)*.24,[float(r['max_m']) for r in rr],width=.24,label=p,color=COLORS[i])
    for ax,yl in zip(axes,['Block RMS (m)','Block maximum (m)']):ax.set(xticks=xx,xticklabels=['01-04','04-07','07-10','10-13'],xlabel='2023-01-04 UTC block',ylabel=yl);ax.legend(fontsize=7);ax.grid(axis='y',alpha=.2)
    save(fig,'time_block_statistics','time_block_summary.csv')
    fig,axes=plt.subplots(2,1,figsize=(12,7));initial=np.load(F/'initial_GCRS_local.npy')
    for g,c in zip(['A_NoDrag',*GROUPS],['black',*COLORS]):
        with np.load(F/f'{g}_base_states_local.npz') as b,np.load(F/f'{g}_tight_states_local.npz') as t:d=b['states'][:,:3]-t['states'][:,:3]
        axes[0].plot(1+np.arange(721)/60,np.linalg.norm(d,axis=1),label=g,color=c)
    axes[0].axhline(.02,color='red',ls='--',label='Frozen single-track limit0.02m');configure(axes[0],'Base/Tight position difference (m)','Single trajectory convergence')
    conv=read('numerical_convergence.csv');rr=[r for r in conv if r['type']=='pair_vector'];labels=[r['comparison'].replace('A_NoDrag','A').replace('B_Open','B').replace('C_Updated','C').replace('D_Reference','D') for r in rr]
    axes[1].bar(np.arange(6),[100*float(r['ratio']) for r in rr]);axes[1].axhline(1,color='red',ls='--',label='Frozen paired-vector limit1%');axes[1].set(xticks=np.arange(6),xticklabels=labels,ylabel='Pair-vector numerical difference / max response (%)');axes[1].legend();axes[1].grid(axis='y',alpha=.2);save(fig,'numerical_convergence','*_states_local.npz;numerical_convergence.csv')
    table(O/'figure_sources.csv',figures);print('8 actual-computation figures saved')
if __name__=='__main__':main()
