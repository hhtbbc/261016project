"""Offline truncation statistics and plots; never integrates an orbit."""
import sys,json,csv,hashlib
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from astropy.time import Time,TimeDelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data,transform_state
from orbit.gravity_truncation import ExtendedEarthGravity
from orbit.spherical_harmonics_gravity import GcrsSphericalHarmonicsForce
from evaluation.orbit_data import load_sp3_reference
from evaluation.orbit_metrics import rac_errors,summarize_errors
F=ROOT/'experiments/gravity_truncation_v1';D=ROOT/'data/processed/gravity_truncation_v1';tag='gravity_truncation_v1';label='PROVISIONAL / HINDCAST / NO_DRAG'
def load(p):
 with np.load(p) as z:return {k:z[k] for k in z.files}
def write(n,rows):
 with (ROOT/f'results/metrics/{tag}_{n}.csv').open('x') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def save(fig,n):
 fig.suptitle(label,fontsize=9);fig.tight_layout(rect=[0,0,1,.95]);p=ROOT/f'results/figures/{tag}_{n}.png';assert not p.exists();fig.savefig(p,dpi=150);plt.close(fig)
def main():
 run=json.loads((F/'run_summary.json').read_text());assert run['convergence_passed'];c=json.loads((F/'configuration.json').read_text());configure_time_data();epoch=Time(c['t0_utc'],scale='utc')
 data={'H1':load(ROOT/'data/processed/spherical_harmonics_v1/H1_states.npz'),'H2':load(D/'H2_states.npz'),'H3':load(D/'H3_states.npz')};tight=load(D/'H3_tight_states.npz');sec=data['H1']['seconds'];times=epoch+TimeDelta(sec,format='sec');hours=sec/3600
 ref=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))).take_exact(times);r,v=transform_state(ref.positions_m,ref.velocities_m_s,times,'ITRS','GCRS');out={'labels':label,'run':run,'residuals':{},'pairs':{},'common_GM_R':True,'coefficient_source_sha256':c['source20']['sha256'],'thresholds':{'endpoint_goal_m':5.,'whole_path_candidate_goal_m':5.,'numeric_state_goal_m':.5}};rows=[];errs={};racs={}
 for n,z in data.items():
  np.testing.assert_array_equal(z['seconds'],sec);np.testing.assert_array_equal(z['states'][0],data['H1']['states'][0]);delta=z['states'][:,:3]-r;rac=rac_errors(delta,r,v);norm=np.linalg.norm(delta,axis=1);errs[n]=norm;racs[n]=rac;stats=summarize_errors(delta,rac);stats.update(hours_1_3_6_m=[float(norm[h*60]) for h in [1,3,6]],terminal_RAC_m=rac[-1].tolist());out['residuals'][n]=stats
  for i,t in enumerate(sec):rows.append(dict(status=label,model=n,utc=times[i].isot,elapsed_s=t,SP3_residual_m=norm[i],R_m=rac[i,0],A_m=rac[i,1],C_m=rac[i,2]))
 write('SP3_residuals',rows);rows=[];pairs={};pairrac={}
 for a,b in [('H2','H1'),('H3','H2'),('H3','H1')]:
  key=a+'_'+b;delta=data[a]['states'][:,:3]-data[b]['states'][:,:3];rac=rac_errors(delta,data['H1']['states'][:,:3],data['H1']['states'][:,3:]);norm=np.linalg.norm(delta,axis=1);pairs[key]=norm;pairrac[key]=rac;stats=summarize_errors(delta,rac);stats.update(terminal_RAC_m=rac[-1].tolist(),endpoint_goal_passed=bool(norm[-1]<5),whole_path_goal_passed=bool(norm.max()<5));out['pairs'][key]=stats
  for i,t in enumerate(sec):rows.append(dict(status=label,pair=key,utc=times[i].isot,elapsed_s=t,position_difference_m=norm[i],R_m=rac[i,0],A_m=rac[i,1],C_m=rac[i,2]))
 write('model_differences',rows)
 for n in ['H2','H3']:
  write(n+'_states',[dict(status=label,utc=times[i].isot,elapsed_s=t,**dict(zip(['gcrs_x_m','gcrs_y_m','gcrs_z_m','gcrs_vx_m_s','gcrs_vy_m_s','gcrs_vz_m_s'],data[n]['states'][i]))) for i,t in enumerate(sec)])
 # Evaluate all gravity truncations at a common H1 state, not their different trajectories.
 frame=GcrsSphericalHarmonicsForce(epoch).frame;models={8:ExtendedEarthGravity(8),12:ExtendedEarthGravity(12),20:ExtendedEarthGravity(20)};rows=[]
 for i,t in enumerate(sec):
  y=data['H1']['states'][i];_,rt,vt,Q=frame.state_to_itrs(t,y[:3],y[3:]);acc={d:m.acceleration_itrs(rt) for d,m in models.items()}
  rows.append(dict(status=label,elapsed_s=t,**{f'a{a}_minus_a{b}_m_s2':np.linalg.norm(acc[a]-acc[b]) for a,b in [(12,8),(20,12),(20,8)]}))
 write('common_H1_accelerations',rows);out['acceleration_ranges']={k:{'min':float(min(x[k] for x in rows)),'max':float(max(x[k] for x in rows))} for k in rows[0] if k.endswith('m_s2')}
 con=np.linalg.norm(data['H3']['states'][:,:3]-tight['states'][:,:3],axis=1);write('convergence',[dict(status=label,elapsed_s=t,H3_base_tight_position_m=con[i]) for i,t in enumerate(sec)])
 meta=json.loads((ROOT/'experiments/spherical_harmonics_v1/run_summary.json').read_text());resources={'H1':meta['runs']['H1'],'H2':run['runs']['H2'],'H3':run['runs']['H3'],'H3_tight':run['runs']['H3_tight']};write('resources',[dict(model=n,historical=n=='H1',**s) for n,s in resources.items()]);out['resources']=resources
 fig,ax=plt.subplots(figsize=(10,4))
 for n,a in pairs.items():ax.plot(hours,a,label=n)
 ax.axhline(5,color='gray',ls='--',label='Candidate engineering goal: 5 m (not a universal accuracy standard)');ax.set(xlabel='Propagation time (h)',ylabel='Model position difference (m)',title='Same EGM2008 GM/R; complete degree/order truncations');ax.legend(fontsize=8);ax.grid();save(fig,'differences')
 fig,ax=plt.subplots(figsize=(10,4))
 for n,a in errs.items():ax.plot(hours,a,label=n)
 ax.set(xlabel='Propagation time (h)',ylabel='SP3 residual (m)',title='SP3 diagnostic; no drag/third bodies/SRP');ax.legend();ax.grid();save(fig,'SP3_residuals')
 for kind,values in [('RAC_differences',pairrac),('RAC_residuals',racs)]:
  fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True)
  for j,ax in enumerate(axes):
   for n,a in values.items():ax.plot(hours,a[:,j],label=n)
   ax.set_ylabel(['R (m)','A (m)','C (m)'][j]);ax.grid()
  axes[0].legend();axes[0].set_title('Common H1 RAC' if kind=='RAC_differences' else 'SP3 reference RAC');axes[-1].set_xlabel('Propagation time (h)');save(fig,kind)
 fig,ax=plt.subplots(figsize=(10,4));ax.plot(hours,con,label='H3 base/tight');ax.set(xlabel='Propagation time (h)',ylabel='Position difference (m)',title='1e-10 / 30 s vs 1e-12 / 15 s');ax.legend();save(fig,'convergence')
 fig,axes=plt.subplots(1,2,figsize=(10,4));axes[0].bar(list(resources),[x['elapsed_s'] for x in resources.values()]);axes[0].set(ylabel='Integration wall time (s)',title='Includes full frame transformations; H1 historical');bench=json.loads((F/'validation.json').read_text())['degrees'];axes[1].bar(list(bench),[x['mean_pure_field_ms'] for x in bench.values()]);axes[1].set(xlabel='Degree/order',ylabel='Mean field evaluation (ms)',title='Constructed point microbenchmark');save(fig,'costs')
 fig,ax=plt.subplots(figsize=(10,4))
 for k in out['acceleration_ranges']:ax.semilogy(hours,[x[k] for x in rows],label=k)
 ax.set(xlabel='Propagation time (h)',ylabel='Acceleration difference (m/s²)',title='All truncations at same H1 positions');ax.legend();save(fig,'accelerations')
 out['candidate_decision']={'12_to_20_endpoint_goal_passed':out['pairs']['H3_H2']['endpoint_goal_passed'],'12_to_20_whole_path_goal_passed':out['pairs']['H3_H2']['whole_path_goal_passed'],'20_to_higher_not_tested':True,'formal_density_validation_ready':False,'reason':'Truncation beyond20, third bodies, tides/time coefficients, real aerodynamic/thrust and TIE datum gates remain'}
 for p,h in json.loads((F/'protected.json').read_text()).items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
 out['protected_unchanged']=True
 with (F/'analysis.json').open('x') as f:json.dump(out,f,indent=2,allow_nan=False)
 print(json.dumps({k:v for k,v in out.items() if k not in ['run','resources']},indent=2))
if __name__=='__main__':main()
