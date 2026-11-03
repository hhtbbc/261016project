"""True-data figures; shared RAC basis is original NoDrag Tight throughout."""
from pathlib import Path
import sys,json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_orbit_12h_numerical_reference_v1 import F,O,GROUPS,TIMES
from analyze_fourcastden_swarm_observation_v1 import table
from prepare_fourcastden_swarm_observation_v1 import sha

def read(n):return list(csv.DictReader((O/n).open()))
def main():
    plt.rcParams.update({'font.size':9});sources=[]
    def save(fig,name,data):
        p=O/(name+'.png');assert not p.exists();fig.subplots_adjust(top=.86,bottom=.23,hspace=.45,wspace=.35)
        fig.text(.5,.02,'2023-01-04 01-13UTC | same frozen H6, synthetic virtual propagation | no real orbit accuracy claim\nOld Base/Tight overall gate remains FAIL; shared RAC basis=original A_NoDrag Tight',ha='center',fontsize=8)
        fig.savefig(p,dpi=165,bbox_inches='tight');plt.close(fig);sources.append(dict(figure=p.name,SHA256=sha(p),data=data))
    def setup(ax,y):ax.axvline(7,color='grey',ls=':');ax.set(xlabel='UTC hour',ylabel=y);ax.grid(alpha=.2)
    old=read('old_error_curves.csv');fig,axes=plt.subplots(2,1,figsize=(12,7))
    for g in GROUPS:
        rr=[r for r in old if r['group']==g];x=[float(r['UTC_hour']) for r in rr];axes[0].plot(x,[float(r['position_m']) for r in rr],label=g);axes[1].plot(x,[float(r['speed_m_s']) for r in rr],label=g)
    axes[0].axhline(.02,color='red',ls='--',label='Frozen0.02m');setup(axes[0],'Base - Tight position norm (m)');setup(axes[1],'Base - Tight velocity norm (m/s)');axes[0].legend(ncol=3);fig.suptitle('Actual original four-track numerical differences');save(fig,'old_four_track_errors','old_error_curves.csv')
    fig,axes=plt.subplots(3,1,figsize=(12,8))
    for ax,k in zip(axes,'RAC'):
        for g in GROUPS:
            rr=[r for r in old if r['group']==g];ax.plot([float(r['UTC_hour']) for r in rr],[float(r[k+'_m']) for r in rr],label=g)
        setup(ax,k+' numerical difference (m)')
    axes[0].legend(ncol=4);fig.suptitle('Old errors in one frozen RAC basis');save(fig,'old_RAC_errors','old_error_curves.csv')
    mean=read('mean_error.csv');fig,axes=plt.subplots(2,1,figsize=(12,7));x=[float(r['UTC_hour']) for r in mean]
    axes[0].plot(x,[float(r['mean_error_norm_m']) for r in mean],label='Norm of mean error vector');axes[1].plot(x,[1000*float(r['RMS_deviation_from_mean_m']) for r in mean],label='RMS group deviation from mean')
    for ax,y in zip(axes,['Common component (m)','Residual group difference (mm)']):setup(ax,y);ax.legend()
    fig.suptitle('Shared numerical sensitivity; correlation alone is not root-cause proof');save(fig,'common_error_component','mean_error.csv')
    rr=read('error_growth_blocks.csv');fig,ax=plt.subplots(figsize=(12,4))
    for i,g in enumerate(GROUPS):
        v=[r for r in rr if r['group']==g];ax.bar(np.arange(4)+(i-1.5)*.19,[float(r['RMS_m']) for r in v],width=.19,label=g)
    ax.set(xticks=np.arange(4),xticklabels=['01-04','04-07','07-10','10-13'],ylabel='Block numerical position RMS (m)',xlabel='UTC block');ax.legend();ax.grid(axis='y',alpha=.2);fig.suptitle('Original error growth before and after07 event');save(fig,'error_growth_blocks','error_growth_blocks.csv')
    pert=read('force_perturbations.csv');fig,axes=plt.subplots(1,2,figsize=(12,4))
    for t in sorted(set(r['UTC_hour'] for r in pert),key=float):
        v=[r for r in pert if r['UTC_hour']==t and r['kind']=='time_at_fixed_state'];axes[0].plot([float(r['delta']) for r in v],[float(r['central_slope_norm']) for r in v],'o-',label=t+'UTC');axes[1].plot([float(r['delta']) for r in v],[float(r['central_curvature_norm']) for r in v],'o-')
    for ax in axes:ax.set_xscale('log');ax.set(xlabel='Time perturbation (s)');ax.grid(alpha=.2)
    axes[0].set_ylabel('Central derivative norm (m/s3)');axes[1].set_ylabel('Second-difference norm (m/s4)');axes[0].legend(fontsize=6,ncol=2);fig.suptitle('Fixed-state H6 temporal probes; tiny-scale curvature may amplify rounding');save(fig,'force_time_probes','force_perturbations.csv')
    curves=read('reference_curves.csv');labels=list(dict.fromkeys(r['comparison'] for r in curves));fig,axes=plt.subplots(2,1,figsize=(12,7))
    for label in labels:
        rr=[r for r in curves if r['comparison']==label];x=[float(r['UTC_hour']) for r in rr];axes[0].plot(x,[float(r['position_m']) for r in rr],label=label);axes[1].plot(x,[float(r['speed_m_s']) for r in rr],label=label)
    axes[0].axhline(.02,color='red',ls='--',label='Original0.02m');setup(axes[0],'Difference to DOP15 (m)');setup(axes[1],'Velocity difference to DOP15 (m/s)');axes[0].legend();fig.suptitle('Same H6, independent high-order integrator comparison');save(fig,'RK45_DOP853_comparison','reference_curves.csv')
    fig,axes=plt.subplots(2,1,figsize=(12,7))
    for label in ['RK45_Tight minus DOP15','DOP30 minus DOP15']:
        rr=[r for r in curves if r['comparison']==label];x=[float(r['UTC_hour']) for r in rr];axes[0].plot(x,[float(r['position_m'])*1000 for r in rr],label=label)
    rr=[r for r in curves if r['comparison']=='DOP30 minus DOP15'];axes[1].plot([float(r['UTC_hour']) for r in rr],[float(r['position_m'])*1000 for r in rr],label='DOP30 minus DOP15')
    setup(axes[0],'Position difference (mm)');setup(axes[1],'DOP reference difference (mm)');axes[0].legend();axes[1].legend();fig.suptitle('Reference convergence and original Tight discrepancy');save(fig,'DOP_reference_convergence','reference_curves.csv')
    fig,axes=plt.subplots(3,1,figsize=(12,8))
    for ax,k in zip(axes,'RAC'):
        for label in labels:
            rr=[r for r in curves if r['comparison']==label];ax.plot([float(r['UTC_hour']) for r in rr],[float(r[k+'_m']) for r in rr],label=label)
        setup(ax,k+' difference to DOP15 (m)')
    axes[0].legend(ncol=3,fontsize=7);fig.suptitle('Independent reference differences in original frozen RAC basis');save(fig,'reference_RAC','reference_curves.csv')
    table(O/'figure_sources.csv',sources);print('8 figures saved')
if __name__=='__main__':main()
