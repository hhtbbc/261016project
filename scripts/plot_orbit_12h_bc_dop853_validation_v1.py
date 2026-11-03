"""Eight actual-data figures for B/C high-order qualification, no propagation."""
from pathlib import Path
import sys,json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_orbit_12h_bc_dop853_validation_v1 import F,O
from prepare_fourcastden_swarm_observation_v1 import sha
from analyze_fourcastden_swarm_observation_v1 import table

def read(n):return list(csv.DictReader((O/n).open()))
def main():
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False});a=json.loads((F/'analysis.json').read_text());e=json.loads((F/'effect_assessment.json').read_text());g=a['gates'];passed=all(g[k]=='PASS' for k in ['B_SINGLE_ORBIT_CONVERGENCE_READY','C_SINGLE_ORBIT_CONVERGENCE_READY','BC_PAIR_EFFECT_CONVERGENCE_READY']);sources=[]
    def save(fig,name,data):
        p=O/(name+'.png');assert not p.exists();fig.subplots_adjust(top=.84,bottom=.25,hspace=.45,wspace=.34)
        fig.suptitle('B/C DOP853 numerical gates '+('PASS' if passed else 'FAIL — unqualified result'),color='black' if passed else 'crimson',y=.985)
        fig.text(.5,.02,'2023-01-04 01-13UTC | coordinate A PROVISIONAL | synthetic400kg /1m2 /Cd2.2; zero ITRS wind\nConditional trajectory differences; old RK45 gate FAIL unchanged; high-order D not run; real Swarm validation BLOCKED',ha='center',fontsize=7)
        fig.savefig(p,dpi=170,bbox_inches='tight');plt.close(fig);sources.append(dict(figure=p.name,SHA256=sha(p),data=data,current_BC_gate='PASS' if passed else 'FAIL'))
    def setup(ax,y,label):ax.axvline(7,color='grey',ls=':');ax.set(xlabel='2023-01-04 UTC hour',ylabel=y,title=label);ax.grid(alpha=.2)
    curves=read('comparison_curves.csv')
    def curve(label):return [r for r in curves if r['comparison']==label]
    def plot(ax,label,key,scale=1.,**kw):
        v=curve(label);ax.plot([float(r['UTC_hour']) for r in v],[scale*float(r[key]) for r in v],label=label,**kw)
    fig,axes=plt.subplots(2,1,figsize=(12,7))
    for gr in ['B_Open','C_Updated']:
        label=gr+' DOP30 minus DOP15';plot(axes[0],label,'position_m');plot(axes[1],label,'velocity_m_s')
    axes[0].axhline(.02,color='red',ls='--',label='Frozen0.02m');setup(axes[0],'Position difference (m)','Single-track high-order convergence');setup(axes[1],'Velocity difference (m/s)','Velocity: descriptive, no invented acceptance threshold')
    for ax in axes:ax.legend()
    save(fig,'single_orbit_convergence','comparison_curves.csv')
    fig,axes=plt.subplots(2,1,figsize=(12,7))
    for mode,style in [('DOP30',':'),('DOP15','-'),('RK45_Tight','--')]:
        label='Updated minus Open '+mode;plot(axes[0],label,'position_m',ls=style);plot(axes[1],label,'velocity_m_s',ls=style)
    setup(axes[0],'Position effect norm (m)','Same initial satellite state; no reset at07');setup(axes[1],'Velocity effect norm (m/s)','Independent integrators for the B/C conditional effect')
    for ax in axes:ax.legend()
    save(fig,'update_effect_12h','comparison_curves.csv')
    fig,axes=plt.subplots(3,1,figsize=(12,9))
    for ax,key in zip(axes,'RAC'):
        for mode,ls in [('DOP15','-'),('RK45_Tight','--')]:plot(ax,'Updated minus Open '+mode,key+'_m',ls=ls)
        setup(ax,key+' effect (m)','Original NoDrag RK45 Tight common RAC basis')
    axes[0].legend();save(fig,'update_effect_RAC','comparison_curves.csv')
    fig,axes=plt.subplots(2,1,figsize=(12,7))
    for label in ['B_Open RK45_Tight minus DOP15','C_Updated RK45_Tight minus DOP15','BC effect RK45_Tight minus DOP15']:
        plot(axes[0],label,'position_m');plot(axes[1],label,'velocity_m_s')
    axes[0].axhline(.02,color='red',ls='--',label='0.02m per track');setup(axes[0],'Difference (m)','Old RK45 Tight versus independent high-order results');setup(axes[1],'Velocity difference (m/s)','Track errors and paired-effect error are separate quantities')
    for ax in axes:ax.legend(fontsize=8)
    save(fig,'RK45_DOP853_comparison','comparison_curves.csv')
    sample={gr:read(gr+'_DOP15_samples.csv') for gr in ['B_Open','C_Updated']};ev={r['group']:r for r in read('event_limits.csv') if r['mode']=='DOP15'}
    fig,axes=plt.subplots(2,1,figsize=(12,7))
    for gr,color in [('B_Open','tab:blue'),('C_Updated','tab:orange')]:
        rr=sample[gr];x=np.array([1+float(r['seconds'])/3600 for r in rr])
        for ax,key,left in [(axes[0],'rho_kg_m3','rho_left'),(axes[1],'drag_norm_m_s2','drag_left')]:
            y=np.array([float(r[key]) for r in rr])
            if gr=='C_Updated':ax.plot(np.r_[x[x<7],7],np.r_[y[x<7],float(ev[gr][left])],color=color,label=gr+' left');ax.plot(x[x>=7],y[x>=7],color=color,ls='--',label=gr+' right')
            else:ax.plot(x,y,color=color,label=gr)
    setup(axes[0],'Density (kg/m3)','Direct saved fields, each own propagated position');setup(axes[1],'Drag acceleration norm (m/s2)','Same frozen aerodynamics and relative velocity law')
    for ax in axes:ax.legend()
    save(fig,'density_and_drag','*_DOP15_samples.csv;event_limits.csv')
    fig,axes=plt.subplots(2,2,figsize=(12,7));rr=sample['C_Updated'];x=np.array([float(r['seconds'])-21600 for r in rr]);j=ev['C_Updated']
    for ax,key,left,label in [(axes[0,0],'rho_kg_m3','rho_left','Density (kg/m3)'),(axes[0,1],'drag_norm_m_s2','drag_left','Drag norm (m/s2)')]:
        y=np.array([float(r[key]) for r in rr]);b=(x>=-600)&(x<0);c=(x>=0)&(x<=600);ax.plot(np.r_[x[b],0],np.r_[y[b],float(j[left])],'o-',label='left atmosphere');ax.plot(x[c],y[c],'s--',label='right atmosphere');ax.axvline(0,color='grey',ls=':');ax.set(xlabel='Seconds relative to07UTC',ylabel=label);ax.legend(fontsize=8);ax.grid(alpha=.2)
    rr=curve('Updated minus Open DOP15');x=np.array([float(r['seconds'])-21600 for r in rr]);idx=abs(x)<=600
    for ax,key,ylabel in [(axes[1,0],'position_m','B/C position effect (m)'),(axes[1,1],'velocity_m_s','B/C velocity effect (m/s)')]:
        ax.plot(x[idx],np.array([float(r[key]) for r in rr])[idx]);ax.set(xlabel='Seconds relative to07UTC',ylabel=ylabel);ax.axvline(0,color='grey',ls=':');ax.grid(alpha=.2)
    axes[1,0].text(.03,.9,'State handoff: position jump0m',transform=axes[1,0].transAxes);axes[1,1].text(.03,.9,'State handoff: velocity jump0m/s',transform=axes[1,1].transAxes)
    save(fig,'event_07UTC','C_Updated_DOP15_samples.csv;comparison_curves.csv;event_limits.csv')
    fig,axes=plt.subplots(2,1,figsize=(12,7))
    for label in ['BC effect DOP30 minus DOP15','BC effect RK45_Tight minus DOP15']:
        plot(axes[0],label,'position_m');plot(axes[1],label,'velocity_m_s')
    axes[0].axhline(e['paired_gate_m'],color='red',ls='--',label='Frozen1% of maximum DOP15 effect');setup(axes[0],'Effect-vector numerical difference (m)','Vector subtraction, not subtraction of norms');setup(axes[1],'Velocity-effect numerical difference (m/s)','Absolute numerical difference also reported')
    for ax in axes:ax.legend(fontsize=8)
    save(fig,'paired_effect_convergence','comparison_curves.csv;effect_assessment.json')
    rr=read('performance.csv');labels=[r['group']+' '+r['mode'] for r in rr];fig,axes=plt.subplots(1,2,figsize=(12,4));xx=np.arange(4)
    axes[0].bar(xx,[float(r['total_s']) for r in rr]);axes[1].bar(xx,[int(r['nfev']) for r in rr])
    for ax,yl in zip(axes,['Wall seconds (includes saved-output diagnostics)','DOP853 RHS evaluation count']):ax.set(xticks=xx,xticklabels=labels,ylabel=yl);ax.tick_params(axis='x',rotation=15);ax.grid(axis='y',alpha=.2)
    save(fig,'runtime_and_evaluations','performance.csv')
    table(O/'figure_sources.csv',sources);print('8 actual-data figures saved')
if __name__=='__main__':main()
