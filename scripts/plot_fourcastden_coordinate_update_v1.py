"""Presentation figures from measured CPU diagnostics, no prediction runs."""
from pathlib import Path
import csv,sys,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
import audit_fourcastden_coordinate_update_v1 as task
from atmosphere.fourcastden_density import reconstruct_native_zg
O=task.O


def read(name):return list(csv.DictReader((O/name).open()))
def save(fig,name):
    p=O/(name+'.png');p.resolve().relative_to(ROOT)
    if p.exists():raise FileExistsError(p)
    fig.savefig(p,dpi=170,bbox_inches='tight');plt.close(fig)


def main():
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    queries=read('real_event_queries.csv');coord=read('coordinate_single_factor_review.csv')
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    for ax,day in zip(axes,['2023-01-04','2023-03-24']):
        rows=[r for r in queries if r['date']==day and r['model']=='Direct' and r['lat']=='0']
        for branch,color in [('left','tab:blue'),('right','tab:orange')]:
            rr=[r for r in rows if r['branch']==branch]
            x=[int(r['UTC'][11:13])+int(r['UTC'][14:16])/60+int(r['UTC'][17:19])/3600 for r in rr]
            ax.plot(x,[float(r['rho_kg_m3']) for r in rr],'o-',color=color,label=branch+' branch')
        ax.axvline(7,color='grey',ls=':');ax.set(title=day+' Direct; native ZG 450 km, lat/lon 0/0',xlabel='Target UTC hour',ylabel='Density (kg/m3)');ax.legend();ax.grid(alpha=.2)
    fig.suptitle('Saved fields: distinct 07 UTC limits; no correction leaked into 06-07 UTC')
    save(fig,'event_density_limits')
    fig,axes=plt.subplots(1,3,figsize=(13,3.8))
    x=[abs(float(r['A_lat_deg'])) for r in coord]
    axes[0].scatter(x,[float(r['delta_lat_deg']) for r in coord],s=5);axes[0].set(ylabel='B-A latitude (deg)')
    axes[1].scatter(x,[float(r['delta_height_m'])/1000 for r in coord],s=5);axes[1].set(ylabel='B-A assumed height (km)')
    for key,label in [('latitude_only_relative','latitude only'),('height_only_relative','height only'),('combined_relative','combined')]:
        axes[2].scatter(x,[100*float(r[key]) for r in coord],s=5,label=label,alpha=.6)
    axes[2].set(ylabel='Conditional density difference to A (%)');axes[2].legend(fontsize=8)
    for a in axes:a.set(xlabel='Absolute WGS84 latitude (deg)');a.grid(alpha=.2)
    fig.suptitle('Existing S7/Swarm March21-23 sensitivity, 577 samples; NOT mapping error bounds')
    save(fig,'coordinate_single_factor_sensitivity')
    rows=read('flow_region_times.csv');failed=read('flow_failed_columns.csv');layer=read('flow_layer_diagnosis.csv')
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for scheme in ['Open','Updated','Reference']:
        rr=[r for r in rows if r['scheme']==scheme and r['region']=='global']
        axes[0].plot([int(r['hour_UTC']) for r in rr],[int(r['invalid_columns']) for r in rr],'o-',label=scheme)
    axes[0].set(xlabel='Mar24 target UTC hour',ylabel='Invalid native-height columns',title='Original 4-32 diagnostic unchanged');axes[0].legend();axes[0].grid(alpha=.2)
    hist=np.zeros((36,72))
    for r in failed:hist[int(round((float(r['lat'])+87.5)/5)),int(round((float(r['lon'])+180)/5))]+=1
    im=axes[1].imshow(hist,origin='lower',extent=[-182.5,177.5,-90,90],aspect='auto',vmin=0,vmax=6,cmap='magma')
    axes[1].set(xlabel='Model longitude (deg E)',ylabel='Model latitude (deg)',title='Updated 08-13UTC: count per column')
    fig.colorbar(im,ax=axes[1],label='Failed hours, out of 6')
    fig.suptitle('Flow: 337 column-times; polar concentration, not negative-density counts')
    save(fig,'flow_failure_time_and_map')
    fig,axes=plt.subplots(1,3,figsize=(12,4),sharey=True)
    for ax,key,title in zip(axes,['invalid_points','DEN_contribution_RMS','TN_contribution_RMS'],['Invalid midpoint cells','DEN component RMS (g/mol)','TN component RMS (g/mol)']):
        a=np.zeros((29,6))
        for k in range(29):
            for j,h in enumerate(range(8,14)):
                rr=[r for r in layer if r['scheme']=='Updated' and int(r['index'])==k and int(r['hour_UTC'])==h]
                a[k,j]=sum(float(r[key]) for r in rr) if key=='invalid_points' else np.sqrt(np.mean([float(r[key])**2 for r in rr]))
        im=ax.imshow(a,origin='lower',extent=[7.5,13.5,-.5,28.5],aspect='auto',cmap='viridis',vmin=0)
        ax.set(xlabel='Mar24 UTC hour',title=title);fig.colorbar(im,ax=ax,fraction=.05)
    axes[0].set(ylabel='Inferred midpoint index (28: auxiliary top)')
    fig.suptitle('Updated Flow: exact algebraic decomposition, not physical-process or neural causality')
    save(fig,'flow_vertical_error_components')
    # Independently show the full worst column, not only selected error points.
    iv=np.load(ROOT/'data/processed/static/ilev.npy');lat=np.load(ROOT/'data/processed/static/lat.npy');lon=np.load(ROOT/'data/processed/static/lon.npy')
    ph=task.load(ROOT/'data/processed/fourcastden_ideal_update_6h_v1/2023-03-24_Flow.npz','Flow')[-1:]
    ref,_,tl=task.reference('2023-03-24',13);ref=ref[None].astype(float);tl=tl[None]
    predB,pT,factor=task.mass_input(ph,tl,iv);refB,rT,_=task.mass_input(ref,tl,iv)
    _,_,pm=reconstruct_native_zg(ph[:,:28],ph[:,142:],ph[:,113:142],tl,lat,iv)
    _,_,rm=reconstruct_native_zg(ref[:,:28],ref[:,142:],ref[:,113:142],tl,lat,iv)
    j=int(np.flatnonzero(lat==-72.5)[0]);i=int(np.flatnonzero(lon==70)[0])
    cr=[dict(index=k,pred_interface_mass=predB[0,k,j,i],reference_interface_mass=refB[0,k,j,i],
        pred_mid_mass=pm[0,k,j,i],reference_mid_mass=rm[0,k,j,i]) for k in range(29)]
    task.table(O/'flow_worst_column_profile.csv',cr)
    fig,axes=plt.subplots(1,2,figsize=(10,4),sharey=True)
    for ax,suffix in zip(axes,['interface','mid']):
        for label in ['pred','reference']:
            ax.plot([r[label+'_'+suffix+'_mass'] for r in cr],range(29),'o-',ms=3,label=label)
        ax.axvline(4,color='grey',ls=':');ax.axvline(32,color='grey',ls=':');ax.set(xlabel='Inferred molar mass (g/mol)',title=suffix+' grid');ax.legend();ax.grid(alpha=.2)
    axes[0].set(ylabel='Native index');fig.suptitle('Mar24 13UTC Updated Flow; lat -72.5 / lon 70: alternating inverse response')
    save(fig,'flow_interface_midpoint_inverse')
    traj=read('synthetic_event_trajectory.csv');conv=read('synthetic_event_convergence.csv')
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for tol in ['1e-08','1e-10','1e-12']:
        rr=[r for r in traj if r['rtol']==tol]
        axes[0].plot([float(r['t_s']) for r in rr],[float(r['position_x_m'])-float(r['analytic_x_m']) for r in rr],label=tol)
    axes[0].axvline(60,color='grey',ls=':');axes[0].set(xlabel='Synthetic time (s)',ylabel='Position error to analytic solution (m)');axes[0].legend();axes[0].grid(alpha=.2)
    axes[1].plot([1,2,3],[float(r['max_position_error_m']) for r in conv],'o-');axes[1].set(yscale='log',xticks=[1,2,3],xticklabels=['base','medium','tight'],ylabel='Maximum absolute position error (m)')
    fig.suptitle('120s quadratic drag event: continuous position/velocity, acceleration x4; no H6 orbit')
    save(fig,'synthetic_event_RK45_convergence')
    print('6 actual-data figures and worst-column CSV written')


if __name__=='__main__':main()
