"""Ten figures from completed trajectories; no dynamics or density queries."""
from pathlib import Path
import sys,json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_orbit_12h_abcd_dop853_closure_v1 import F,O
from analyze_orbit_12h_abcd_dop853_closure_v1 import BO
from prepare_fourcastden_swarm_observation_v1 import sha
from analyze_fourcastden_swarm_observation_v1 import table

def read(p):return list(csv.DictReader(p.open()))
def main():
    status=json.loads((F/'analysis.json').read_text())['gates']['IDEAL_UPDATE_ORBIT_EFFECT_VALIDATED'];effect=json.loads((F/'effect_assessment.json').read_text());curves=read(O/'comparison_curves.csv');sources=[]
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    def save(fig,name,source):
        path=O/(name+'.png');assert not path.exists();fig.subplots_adjust(top=.84,bottom=.24,hspace=.42,wspace=.33)
        fig.suptitle('Four-group high-order conditional comparison: '+status,y=.99,color='black' if status=='PASS' else 'crimson')
        fig.text(.5,.02,'2023-01-04 UTC | ideal full-state atmospheric update at07UTC | PROVISIONAL_COORDINATE_A\nVirtual conditional trajectories; synthetic400kg /1m2 /Cd2.2; TIE-GCM conditional reference is NOT a true orbit\nOld RK45 Base/Tight FAIL preserved; real satellite validation BLOCKED',ha='center',fontsize=7)
        fig.savefig(path,dpi=170,bbox_inches='tight');plt.close(fig);sources.append(dict(figure=path.name,SHA256=sha(path),source=source,numerical_gate=status))
    def setup(ax,y,title):ax.set(xlabel='2023-01-04 UTC hour',ylabel=y,title=title);ax.axvline(7,color='grey',ls=':');ax.grid(alpha=.2)
    def plot(ax,label,key='position_m',scale=1,**kwargs):
        rr=[r for r in curves if r['comparison']==label];ax.plot([float(r['UTC_hour']) for r in rr],[scale*float(r[key]) for r in rr],label=label,**kwargs)
    samples={g:read((O if g=='D_Reference' else BO)/(g+'_DOP15_samples.csv')) for g in ['B_Open','C_Updated','D_Reference']}
    ev=json.loads((ROOT/'experiments/orbit_12h_bc_dop853_validation_v1/C_Updated_DOP15_runtime.json').read_text())['event_limits']
    for key,name,unit,title in [('rho_kg_m3','density_12h','Density (kg/m3)','NoDrag: density not used, not a zero-density field'),('drag_norm_m_s2','drag_acceleration_12h','Drag acceleration norm (m/s2)','Same synthetic aerodynamics; each propagated path')]:
        fig,ax=plt.subplots(figsize=(12,5))
        for g,rr in samples.items():
            x=np.array([1+float(r['seconds'])/3600 for r in rr]);y=np.array([float(r[key]) for r in rr])
            if g=='C_Updated':
                left=ev[0]['rho_kg_m3' if key=='rho_kg_m3' else 'drag_norm_m_s2'];ax.plot(np.r_[x[x<7],7],np.r_[y[x<7],left],label=g+' left');ax.plot(x[x>=7],y[x>=7],label=g+' right')
            else:ax.plot(x,y,label=g)
        setup(ax,unit,title);ax.legend();save(fig,name,'B/C saved DOP15 samples; new D DOP15 samples; C event_limits')
    fig,ax=plt.subplots(figsize=(12,5))
    for g in ['B_Open','C_Updated']:plot(ax,g+' minus D_Reference DOP15')
    setup(ax,'Conditional position difference (m)','Open versus Updated relative to the TIE-GCM conditional trajectory');ax.legend();save(fig,'relative_reference_12h','comparison_curves.csv')
    fig,ax=plt.subplots(figsize=(10,5));x=np.arange(3);width=.35
    for i,(key,label) in enumerate([('open','Open-loop'),('updated','Ideal Update')]):ax.bar(x+(i-.5)*width,[effect[key][k] for k in ['terminal_m','RMS_m','post6h_RMS_m']],width,label=label)
    ax.set(xticks=x,xticklabels=['12h endpoint','Full-window RMS','Post-update6h RMS'],ylabel='Conditional position difference (m)',title='Endpoint and whole-window conclusions reported separately');ax.legend();save(fig,'endpoint_and_RMS','effect_assessment.json')
    rr=read(O/'update_benefit_timeseries.csv');x=np.array([float(r['UTC_hour']) for r in rr]);y=np.array([float(r['reduction_m']) for r in rr]);fig,axes=plt.subplots(2,1,figsize=(12,7))
    for ax in axes:ax.plot(x,y);ax.axhline(0,color='black',lw=.6);ax.fill_between(x,0,y,where=y>=0,color='teal',alpha=.3,label='Updated closer');ax.fill_between(x,0,y,where=y<0,color='crimson',alpha=.5,label='Updated farther');setup(ax,'Open-to-D minus Updated-to-D (m)','Signed conditional improvement; no unfavorable samples deleted')
    axes[1].set_xlim(6.98,7.5);axes[1].set_ylim(min(y[(x>7)&(x<7.5)])*1.2,max(y[(x>7)&(x<7.5)])*1.2);axes[0].legend();save(fig,'improvement_and_worsening','update_benefit_timeseries.csv')
    fig,axes=plt.subplots(3,1,figsize=(12,9))
    for ax,k in zip(axes,'RAC'):
        for g in ['B_Open','C_Updated']:plot(ax,g+' minus D_Reference DOP15',k+'_m')
        plot(ax,'C_Updated minus B_Open DOP15',k+'_m',ls='--');setup(ax,k+' position difference (m)','Common frozen original NoDrag RK45 Tight RAC basis')
    axes[0].legend(fontsize=8);save(fig,'RAC_differences','comparison_curves.csv')
    fig,axes=plt.subplots(2,2,figsize=(12,7));rr=samples['C_Updated'];x=np.array([1+float(r['seconds'])/3600 for r in rr]);mask=(x>=6.9)&(x<=7.2)
    for ax,key,title in [(axes[0,0],'rho_kg_m3','Updated density (kg/m3)'),(axes[0,1],'drag_norm_m_s2','Updated drag (m/s2)')]:
        y=np.array([float(r[key]) for r in rr]);left=ev[0]['rho_kg_m3' if key=='rho_kg_m3' else 'drag_norm_m_s2'];ax.plot(np.r_[x[mask&(x<7)],7],np.r_[y[mask&(x<7)],left],'o-');ax.plot(x[mask&(x>=7)],y[mask&(x>=7)],'s--');setup(ax,title,'Left/right atmosphere preserved separately')
    for ax,key,unit in [(axes[1,0],'position_m','Position effect (m)'),(axes[1,1],'velocity_m_s','Velocity effect (m/s)')]:plot(ax,'C_Updated minus B_Open DOP15',key);ax.set_xlim(6.9,7.2);local=[float(v[key]) for v in curves if v['comparison']=='C_Updated minus B_Open DOP15' and 6.9<=float(v['UTC_hour'])<=7.2];ax.set_ylim(0,max(local)*1.1);setup(ax,unit,'Event P/V handoff exactly continuous')
    save(fig,'event_07UTC','C saved samples and event limits; comparison_curves.csv')
    fig,axes=plt.subplots(2,1,figsize=(12,7));plot(axes[0],'D_Reference DOP30 minus DOP15');axes[0].axhline(.02,color='red',ls='--',label='Frozen0.02m gate');plot(axes[1],'D_Reference DOP30 minus DOP15','velocity_m_s');setup(axes[0],'Position difference (m)','D independent step-size sensitivity');setup(axes[1],'Velocity difference (m/s)','D velocity sensitivity: descriptive');axes[0].legend();save(fig,'D_single_convergence','comparison_curves.csv')
    rr=read(O/'pair_convergence.csv');fig,ax=plt.subplots(figsize=(12,5));x=np.arange(len(rr));ax.bar(x,[100*float(r['relative_sensitivity_fraction']) for r in rr]);ax.axhline(1,color='red',ls='--',label='Frozen1% gate');ax.set(xticks=x,xticklabels=[r['comparison'].replace(' minus ',' − ') for r in rr],ylabel='Effect-vector numerical sensitivity (%)',title='Vector differences before norms; six paired responses');ax.tick_params(axis='x',labelsize=7);ax.legend();save(fig,'six_pair_convergence','pair_convergence.csv')
    fig,axes=plt.subplots(2,1,figsize=(12,7));plot(axes[0],'D_Reference RK45_Tight minus DOP15');axes[0].axhline(.02,color='red',ls='--',label='0.02m reference range');setup(axes[0],'Position difference (m)','Old D RK45 Tight versus independent DOP15')
    for g,old in [('B_Open',9.177625127182976),('C_Updated',4.4824348326751995)]:
        new=effect['open' if g=='B_Open' else 'updated']['terminal_m'];axes[1].plot(['RK45 Tight','DOP15'],[old,new],'o-',label=g+' minus D endpoint')
    axes[1].set(ylabel='Conditional endpoint difference (m)',title='Historical result versus high-order closure');axes[0].legend();axes[1].legend();save(fig,'RK45_DOP853_comparison','comparison_curves.csv; effect_assessment.json')
    table(O/'figure_sources.csv',sources)
if __name__=='__main__':main()
