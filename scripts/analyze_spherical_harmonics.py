"""Offline audit/plots only; no new integration."""
import sys,json,csv,hashlib
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from astropy.time import Time,TimeDelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data,transform_state
from orbit.j2 import EarthFigureAxis,j2_acceleration
from orbit.two_body import central_gravity,EARTH_MU
from orbit.spherical_harmonics_gravity import SphericalHarmonicsGravity,GcrsSphericalHarmonicsForce,GM,RADIUS_M
from evaluation.orbit_data import load_sp3_reference
from evaluation.orbit_metrics import rac_errors,summarize_errors
F=ROOT/'experiments/spherical_harmonics_v1';D=ROOT/'data/processed/spherical_harmonics_v1';tag='spherical_harmonics_v1';label='PROVISIONAL / HINDCAST / NO_DRAG'
def load(p):
 with np.load(p) as z:return {k:z[k] for k in z.files}
def write(name,rows):
 with (ROOT/f'results/metrics/{tag}_{name}.csv').open('x') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
def save(fig,n):
 fig.suptitle(label,fontsize=9);fig.tight_layout(rect=[0,0,1,.95]);p=ROOT/f'results/figures/{tag}_{n}.png';assert not p.exists();fig.savefig(p,dpi=150);plt.close(fig)
def main():
 run=json.loads((F/'run_summary.json').read_text());assert run['convergence_passed'];c=json.loads((F/'configuration.json').read_text());configure_time_data()
 data={'G0':load(ROOT/'data/processed/provisional_drag_orbit_v1/D0_states.npz'),'G1':load(ROOT/'data/processed/high_order_gravity_v1/G1_states.npz'),'G2':load(ROOT/'data/processed/high_order_gravity_v1/G2_states.npz'),'H1':load(D/'H1_states.npz')}
 seconds=data['G0']['seconds'];epochs=Time(c['t0_utc'],scale='utc')+TimeDelta(seconds,format='sec');ref=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))).take_exact(epochs);r,v=transform_state(ref.positions_m,ref.velocities_m_s,epochs,'ITRS','GCRS');out={'labels':label,'residuals':{},'model_differences':{},'run':run,'coefficient_system':'EGM2008 8x8 static tide_free source GM/R, H0 nominal differs','no_new_drag_or_atmosphere_runs':True};errs={};racs={};rows=[]
 for n,z in data.items():
  np.testing.assert_array_equal(z['seconds'],seconds);np.testing.assert_array_equal(z['states'][0],data['G0']['states'][0]);delta=z['states'][:,:3]-r;rac=rac_errors(delta,r,v);err=np.linalg.norm(delta,axis=1);errs[n]=err;racs[n]=rac;out['residuals'][n]=summarize_errors(delta,rac);out['residuals'][n]['terminal_RAC_m']=rac[-1].tolist();out['residuals'][n]['hour_1_3_6_m']=[float(err[h*60]) for h in [1,3,6]]
  for i,t in enumerate(seconds):rows.append(dict(status=label,model=n,utc=epochs[i].isot,elapsed_s=t,residual_m=err[i],R_m=rac[i,0],A_m=rac[i,1],C_m=rac[i,2]))
 write('SP3_residuals',rows);rows=[];differences={}
 for n in ['G0','G1','G2']:
  delta=data['H1']['states'][:,:3]-data[n]['states'][:,:3];rac=rac_errors(delta,data['G0']['states'][:,:3],data['G0']['states'][:,3:]);differences[n]=np.linalg.norm(delta,axis=1);out['model_differences']['H1_'+n]=summarize_errors(delta,rac)
  for i,t in enumerate(seconds):rows.append(dict(status=label,pair='H1_'+n,elapsed_s=t,displacement_m=differences[n][i],R_m=rac[i,0],A_m=rac[i,1],C_m=rac[i,2]))
 write('model_differences',rows)
 state=data['H1']['states'];write('H1_states',[dict(status=label,utc=epochs[i].isot,elapsed_s=t,**dict(zip(['gcrs_x_m','gcrs_y_m','gcrs_z_m','gcrs_vx_m_s','gcrs_vy_m_s','gcrs_vz_m_s'],state[i]))) for i,t in enumerate(seconds)])
 axis=EarthFigureAxis(Time(c['t0_utc'],scale='utc'),21600);force=GcrsSphericalHarmonicsForce(Time(c['t0_utc'],scale='utc'));m=SphericalHarmonicsGravity();mono=SphericalHarmonicsGravity(0,0);zonal=SphericalHarmonicsGravity(8,0);c20=m.coefficients[2,0][0];n2=SphericalHarmonicsGravity(2,0,{(0,0):(1.,0.),(2,0):(c20,0.)});rows=[]
 for i,t in enumerate(seconds):
  p=state[i,:3];vel=state[i,3:];_,rt,vt,Q=force.frame.state_to_itrs(t,p,vel);a=m.acceleration_itrs(rt);old=central_gravity(t,p,vel)+j2_acceleration(p,axis(t));two=-GM*rt/np.linalg.norm(rt)**3+j2_acceleration(rt,mu=GM,radius_m=RADIUS_M,j2=-np.sqrt(5)*c20)
  rows.append(dict(status=label,elapsed_s=t,H1_minus_G0_accel_m_s2=np.linalg.norm(Q.T@a-old),nonzonal_m_s2=np.linalg.norm(a-zonal.acceleration_itrs(rt)),source_parameter_and_C20_change_m_s2=np.linalg.norm(Q.T@two-old),monopole_GM_change_m_s2=abs(GM-EARTH_MU)/np.linalg.norm(p)**2))
 write('common_state_accelerations',rows);out['acceleration_ranges']={k:[float(min(x[k] for x in rows)),float(max(x[k] for x in rows))] for k in rows[0] if k.endswith('m_s2')}
 tight=load(D/'H1_tight_states.npz');con=np.linalg.norm(state[:,:3]-tight['states'][:,:3],axis=1);write('convergence',[dict(status=label,elapsed_s=t,H1_base_tight_m=con[i]) for i,t in enumerate(seconds)])
 hours=seconds/3600
 fig,ax=plt.subplots(figsize=(10,4))
 for n,e in errs.items():ax.plot(hours,e,label=n)
 ax.set(xlabel='Propagation time (h)',ylabel='SP3 position residual (m)',title='Same SP3 initial state; H1 complete EGM2008 8x8, no drag');ax.legend();ax.grid();save(fig,'residuals')
 fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True)
 for j,ax in enumerate(axes):
  for n,a in racs.items():ax.plot(hours,a[:,j],label=n)
  ax.set_ylabel(['R residual (m)','A residual (m)','C residual (m)'][j]);ax.grid()
 axes[0].legend();axes[-1].set_xlabel('Propagation time (h)');save(fig,'RAC')
 fig,ax=plt.subplots(figsize=(10,4))
 for n,d in differences.items():ax.plot(hours,d,label='H1 - '+n)
 ax.set(xlabel='Propagation time (h)',ylabel='Model position difference (m)',title='Includes source GM/R/C20 changes; not density effects');ax.legend();save(fig,'differences')
 fig,ax=plt.subplots(figsize=(10,4));ax.plot(hours,con,label='H1 base/tight');ax.set(xlabel='Propagation time (h)',ylabel='Position difference (m)',title='RK45 1e-10 / 30 s vs 1e-12 / 15 s');ax.legend();save(fig,'convergence')
 fig,ax=plt.subplots(figsize=(10,4))
 for k in out['acceleration_ranges']:ax.semilogy(hours,[x[k] for x in rows],label=k)
 ax.set(xlabel='Propagation time (h)',ylabel='Acceleration difference (m/s²)',title='All accelerations evaluated at common H1 states');ax.legend(fontsize=7);save(fig,'accelerations')
 write('resources',[dict(model=n,**s) for n,s in run['runs'].items()])
 with (F/'analysis.json').open('x') as f:json.dump(out,f,indent=2,allow_nan=False)
 print(json.dumps({k:v for k,v in out.items() if k!='run'},indent=2))
if __name__=='__main__':main()
