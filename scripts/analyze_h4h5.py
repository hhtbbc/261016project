"""Offline H3/H4/H5 comparison, no integration and no parameter fitting."""
import sys,json,csv,hashlib
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from astropy.time import Time,TimeDelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data,transform_state
from orbit.gravity_truncation import ExtendedEarthGravity
from orbit.gravity_degree40 import Degree40EarthGravity
from orbit.spherical_harmonics_gravity import GcrsSphericalHarmonicsForce
from orbit.third_body_gravity import ThirdBodyGravity
from evaluation.orbit_data import load_sp3_reference
from evaluation.orbit_metrics import rac_errors,summarize_errors
F=ROOT/'experiments/gravity_third_body_v1';D=ROOT/'data/processed/gravity_third_body_v1';tag='gravity_third_body_v1';label='PROVISIONAL / HINDCAST / NO_DRAG / FULL6H_CONVERGENCE_PENDING'
def load(p):
 with np.load(p) as z:return {k:z[k] for k in z.files}
def write(n,rows):
 with (ROOT/f'results/metrics/{tag}_{n}.csv').open('x') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def save(fig,n):
 fig.suptitle('PROVISIONAL; H5 ERFA ephemeris; full 6h tight comparison PENDING',fontsize=9);fig.tight_layout(rect=[0,0,1,.94]);p=ROOT/f'results/figures/{tag}_{n}.png';assert not p.exists();fig.savefig(p,dpi=150);plt.close(fig)
def main():
 run=json.loads((F/'run_summary.json').read_text());c=json.loads((F/'configuration.json').read_text());configure_time_data();epoch=Time(c['t0_utc'],scale='utc');data={'H3':load(ROOT/'data/processed/gravity_truncation_v1/H3_states.npz'),'H4':load(D/'H4_states.npz'),'H5':load(D/'H5_states.npz')};sec=data['H3']['seconds'];times=epoch+TimeDelta(sec,format='sec');hours=sec/3600
 ref=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))).take_exact(times);r,v=transform_state(ref.positions_m,ref.velocities_m_s,times,'ITRS','GCRS');out={'labels':label,'run':run,'residuals':{},'pairs':{},'short_checks':{},'full_6h_convergence_status':'PENDING: only short base/tight; no H4/H5 full tight reruns','ephemeris_status':'PROVISIONAL_EPHEMERIS; native ERFA Moon GCRS and Sun Newtonian GCRS-aligned geometry','references':ref.metadata};errs={};racs={};rows=[]
 for n,z in data.items():
  np.testing.assert_array_equal(z['seconds'],sec);np.testing.assert_array_equal(z['states'][0],data['H3']['states'][0]);delta=z['states'][:,:3]-r;rac=rac_errors(delta,r,v);norm=np.linalg.norm(delta,axis=1);errs[n]=norm;racs[n]=rac;s=summarize_errors(delta,rac);s.update(hours_1_3_6_m=[float(norm[h*60]) for h in [1,3,6]],terminal_RAC_m=rac[-1].tolist());out['residuals'][n]=s
  for i,t in enumerate(sec):rows.append(dict(status=label,model=n,utc=times[i].isot,elapsed_s=t,SP3_residual_m=norm[i],R_m=rac[i,0],A_m=rac[i,1],C_m=rac[i,2]))
 write('SP3_residuals',rows);rows=[];pairs={};pracs={}
 for n in ['H4','H5']:
  key=n+'_H3';delta=data[n]['states'][:,:3]-data['H3']['states'][:,:3];rac=rac_errors(delta,data['H3']['states'][:,:3],data['H3']['states'][:,3:]);norm=np.linalg.norm(delta,axis=1);pairs[key]=norm;pracs[key]=rac;s=summarize_errors(delta,rac);s.update(terminal_RAC_m=rac[-1].tolist(),candidate_5m_endpoint_passed=bool(norm[-1]<5));out['pairs'][key]=s
  for i,t in enumerate(sec):rows.append(dict(status=label,pair=key,utc=times[i].isot,elapsed_s=t,position_difference_m=norm[i],R_m=rac[i,0],A_m=rac[i,1],C_m=rac[i,2]))
 write('model_differences',rows)
 for n in ['H4','H5']:
  write(n+'_states',[dict(status=label,utc=times[i].isot,elapsed_s=t,**dict(zip(['gcrs_x_m','gcrs_y_m','gcrs_z_m','gcrs_vx_m_s','gcrs_vy_m_s','gcrs_vz_m_s'],data[n]['states'][i]))) for i,t in enumerate(sec)])
  out['short_checks'][n]=json.loads((F/(n+'_short_gate.json')).read_text())
 frame=GcrsSphericalHarmonicsForce(epoch).frame;low=ExtendedEarthGravity(20);high=Degree40EarthGravity(40);third=ThirdBodyGravity(epoch,21600);rows=[]
 for i,t in enumerate(sec):
  y=data['H3']['states'][i];_,rt,vt,Q=frame.state_to_itrs(t,y[:3],y[3:]);parts=third.components(t,y[:3]);rows.append(dict(status=label,elapsed_s=t,degree40_minus20_acceleration_m_s2=np.linalg.norm(high.acceleration_itrs(rt)-low.acceleration_itrs(rt)),sun_acceleration_m_s2=np.linalg.norm(parts['sun']),moon_acceleration_m_s2=np.linalg.norm(parts['moon']),combined_third_body_m_s2=np.linalg.norm(parts['sun']+parts['moon'])))
 write('common_H3_accelerations',rows);out['acceleration_ranges']={k:{'min':float(min(x[k] for x in rows)),'max':float(max(x[k] for x in rows))} for k in rows[0] if k.endswith('m_s2')}
 resources={'H3':json.loads((ROOT/'experiments/gravity_truncation_v1/H3.json').read_text()),'H4':run['runs']['H4'],'H5':run['runs']['H5']};out['resources']=resources;write('resources',[dict(model=n,historical=n=='H3',**s) for n,s in resources.items()])
 fig,ax=plt.subplots(figsize=(10,4))
 for n,a in pairs.items():ax.plot(hours,a,label=n)
 ax.axhline(5,color='gray',ls='--',label='Truncation candidate target: 5 m');ax.set(xlabel='Propagation time (h)',ylabel='Model position difference (m)',title='H4: degree change only; H5: third bodies only');ax.legend();ax.grid();save(fig,'differences')
 fig,ax=plt.subplots(figsize=(10,4))
 for n,a in errs.items():ax.plot(hours,a,label=n)
 ax.set(xlabel='Propagation time (h)',ylabel='SP3 residual (m)',title='Same SP3 initial state; residuals are not a model selection rule');ax.legend();ax.grid();save(fig,'SP3_residuals')
 for kind,values in [('RAC_differences',pracs),('RAC_residuals',racs)]:
  fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True)
  for j,ax in enumerate(axes):
   for n,a in values.items():ax.plot(hours,a[:,j],label=n)
   ax.set_ylabel(['R (m)','A (m)','C (m)'][j]);ax.grid()
  axes[0].legend();axes[0].set_title('Common H3 inertial RAC' if kind=='RAC_differences' else 'SP3 reference RAC');axes[-1].set_xlabel('Propagation time (h)');save(fig,kind)
 fig,ax=plt.subplots(figsize=(10,4))
 for k in out['acceleration_ranges']:ax.semilogy(hours,[x[k] for x in rows],label=k)
 ax.set(xlabel='Propagation time (h)',ylabel='Acceleration norm/difference (m/s²)',title='All terms evaluated at common historical H3 states');ax.legend(fontsize=8);save(fig,'accelerations')
 fig,ax=plt.subplots(figsize=(9,4));ax.bar(list(resources),[s['elapsed_s'] for s in resources.values()]);ax.set(ylabel='Integration wall time (s)',title='H3 historical timing; full frame conversion included');save(fig,'costs')
 fig,ax=plt.subplots(figsize=(9,4));shortrows=[]
 for n in ['H4','H5']:
  b=load(D/(n+'_short_states.npz'));t=load(D/(n+'_short_tight_states.npz'));e=np.linalg.norm(b['states'][:,:3]-t['states'][:,:3],axis=1);ax.plot(b['seconds']/60,e,label=n+' short base/tight')
  for i,s in enumerate(b['seconds']):shortrows.append(dict(model=n,elapsed_s=s,base_tight_position_m=e[i],scope='600s short test ONLY; not full6h'))
 write('short_convergence',shortrows);ax.set(xlabel='Short test time (min)',ylabel='Position difference (m)',title='Short tests pass; full six-hour numerical convergence remains pending');ax.legend();save(fig,'short_convergence')
 for p,h in json.loads((F/'protected.json').read_text()).items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
 out['protected_unchanged']=True
 with (F/'analysis.json').open('x') as f:json.dump(out,f,indent=2,allow_nan=False)
 print(json.dumps({k:v for k,v in out.items() if k not in ['run','references','resources']},indent=2))
if __name__=='__main__':main()
