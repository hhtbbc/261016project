"""Figures from completed actual H6 condition propagations only."""
from pathlib import Path
import sys,csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_fourcastden_orbit_update_event_v1 import F,O
GROUPS=['B_Open','C_Updated','D_Reference'];COLORS=['tab:blue','tab:orange','tab:green']
def read(n):return list(csv.DictReader((O/n).open()))
def save(fig,name):
    p=O/(name+'.png');p.resolve().relative_to(ROOT)
    if p.exists():raise FileExistsError(p)
    fig.subplots_adjust(hspace=.45,wspace=.35,top=.85,bottom=.14)
    fig.text(.5,.015,'Jan4 06:30-07:30 UTC | SP3-initialized virtual propagation | coordinate A / synthetic aero / HINDCAST | not real orbit accuracy',ha='center',fontsize=7)
    fig.savefig(p,dpi=170,bbox_inches='tight');plt.close(fig)


def main():
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    data={g:read(g+'_tight_samples.csv') for g in GROUPS};jump={g:next(r for r in read('event_density_drag_jump.csv') if r['group']==g and r['mode']=='tight') for g in GROUPS}
    fig,ax=plt.subplots(figsize=(12,4))
    for g,c in zip(GROUPS,COLORS):
        rr=data[g];x=np.array([float(r['seconds'])/60 for r in rr]);y=np.array([float(r['rho_kg_m3']) for r in rr])
        if g=='C_Updated':
            ax.plot(np.r_[x[x<30],30],np.r_[y[x<30],float(jump[g]['rho_left_kg_m3'])],color=c,label=g+' left')
            ax.plot(x[x>=30],y[x>=30],color=c,ls='--',label=g+' right')
        else:ax.plot(x,y,color=c,label=g)
    ax.axvline(30,color='grey',ls=':');ax.set(xlabel='Minutes since 06:30 UTC',ylabel='Density (kg/m3)',title='Each own propagated position; exact event limits retained')
    ax.text(.01,.03,'A_NoDrag does not use a density field',transform=ax.transAxes);ax.legend();ax.grid(alpha=.2)
    save(fig,'density_along_propagated_paths')
    fig,ax=plt.subplots(figsize=(12,4))
    for g,c in zip(GROUPS,COLORS):
        rr=data[g];x=np.array([float(r['seconds'])/60 for r in rr]);y=np.array([float(r['drag_norm_m_s2']) for r in rr])
        if g=='C_Updated':
            ax.plot(np.r_[x[x<30],30],np.r_[y[x<30],float(jump[g]['drag_left_norm_m_s2'])],color=c,label=g+' left');ax.plot(x[x>=30],y[x>=30],color=c,ls='--',label=g+' right')
        else:ax.plot(x,y,color=c,label=g)
    ax.axhline(0,color='black',ls=':',label='A_NoDrag: applied drag = 0');ax.axvline(30,color='grey',ls=':');ax.set(xlabel='Minutes since 06:30 UTC',ylabel='Drag acceleration norm (m/s2)',title='Same mass400kg / area1m2 / Cd2.2; zero ITRS wind');ax.legend();ax.grid(alpha=.2)
    save(fig,'drag_acceleration_paths')
    curves=read('pair_curves.csv');primary=['C_Updated minus B_Open','B_Open minus D_Reference','C_Updated minus D_Reference']
    fig,axes=plt.subplots(2,1,figsize=(12,7))
    for p,c in zip(primary,COLORS):
        rr=[r for r in curves if r['mode']=='tight' and r['comparison']==p];axes[0].plot([float(r['seconds'])/60 for r in rr],[float(r['norm_m'])*1000 for r in rr],label=p,color=c)
    for g,c in zip(GROUPS,COLORS):
        rr=[r for r in curves if r['mode']=='tight' and r['comparison']==g+' minus A_NoDrag'];axes[1].plot([float(r['seconds'])/60 for r in rr],[float(r['norm_m']) for r in rr],label=g+' minus A',color=c)
    axes[0].set(ylabel='Conditional position difference (mm)',title='Density-input trajectory differences; D is not a precision orbit truth')
    axes[1].set(ylabel='Difference to no-drag trajectory (m)',xlabel='Minutes since 06:30 UTC')
    for ax in axes:ax.axvline(30,color='grey',ls=':');ax.legend();ax.grid(alpha=.2)
    save(fig,'position_differences')
    fig,axes=plt.subplots(3,1,figsize=(12,8))
    for ax,key in zip(axes,['R_m','A_m','C_m']):
        for p,c in zip(primary,COLORS):
            rr=[r for r in curves if r['mode']=='tight' and r['comparison']==p];ax.plot([float(r['seconds'])/60 for r in rr],[float(r[key])*1000 for r in rr],label=p,color=c)
        ax.axvline(30,color='grey',ls=':');ax.set(ylabel=key[0]+' difference (mm)');ax.grid(alpha=.2)
    axes[0].legend(ncol=3,fontsize=8);axes[-1].set(xlabel='Minutes since 06:30 UTC');fig.suptitle('RAC in common A_NoDrag basis: R outward, C=r cross v, A=C cross R')
    save(fig,'RAC_differences')
    g='C_Updated';rr=data[g];x=np.array([float(r['seconds'])-1800 for r in rr]);jr=jump[g]
    fig,axes=plt.subplots(2,2,figsize=(12,7))
    for ax,field,left,label in [(axes[0,0],'rho_kg_m3','rho_left_kg_m3','Density (kg/m3)'),(axes[0,1],'drag_norm_m_s2','drag_left_norm_m_s2','Drag norm (m/s2)')]:
        y=np.array([float(r[field]) for r in rr]);before=(x>=-300)&(x<0);after=(x>=0)&(x<=300)
        ax.plot(np.r_[x[before],0],np.r_[y[before],float(jr[left])],'o-',label='left atmosphere');ax.plot(x[after],y[after],'s--',label='right atmosphere');ax.axvline(0,color='grey',ls=':');ax.set(xlabel='Seconds relative to07UTC',ylabel=label);ax.legend();ax.grid(alpha=.2)
    for ax,text in [(axes[1,0],'Stored event handoff:\nposition vector jump = (0,0,0) m\nbitwise identical left-end / right-start'),(axes[1,1],'Stored event handoff:\nvelocity vector jump = (0,0,0) m/s\nno satellite state reset')]:
        ax.axis('off');ax.text(.05,.65,text,transform=ax.transAxes,fontsize=12,va='center')
    fig.suptitle('Updated Direct: atmosphere/acceleration may jump; satellite position and velocity remain continuous')
    save(fig,'event_seam_detail')
    print('5 actual propagation figures written')


if __name__=='__main__':main()
