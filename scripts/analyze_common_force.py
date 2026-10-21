"""Offline analysis and conditional freeze; never propagates an orbit."""
import sys,json,csv,hashlib
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from astropy.time import Time,TimeDelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data,transform_state
from evaluation.orbit_data import load_sp3_reference
from evaluation.orbit_metrics import rac_errors,summarize_errors
from orbit.common_force_model import CommonForceModel
F=ROOT/'experiments/common_force_validation_v1';D=ROOT/'data/processed/common_force_validation_v1';tag='common_force_v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,j):
 with p.open('x') as f:json.dump(j,f,indent=2,allow_nan=False)
def write(name,rows):
 with (ROOT/f'results/metrics/{tag}_{name}.csv').open('x') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def load(path):
 with np.load(path) as z:return z['states'].copy(),z['seconds'].copy()
def save(fig,name):
 fig.suptitle('PROVISIONAL / HINDCAST / FORCE_MODEL_INCOMPLETE; ERFA ephemeris',fontsize=9);fig.tight_layout(rect=[0,0,1,.95]);p=ROOT/f'results/figures/{tag}_{name}.png';assert not p.exists();fig.savefig(p,dpi=150);plt.close(fig)
def main():
 summary=json.loads((F/'run_summary.json').read_text());assert summary['passed'];c=json.loads((F/'effective_configuration.json').read_text());configure_time_data();epoch=Time(c['t0_utc'],scale='utc');s={};tight={}
 for n,folder in [('H3','gravity_truncation_v1'),('H4','gravity_third_body_v1'),('H5','gravity_third_body_v1'),('H6','common_force_validation_v1')]:
  s[n],seconds=load(ROOT/f'data/processed/{folder}/{n}_states.npz');tf=ROOT/'data/processed/gravity_truncation_v1' if n=='H3' else D;tight[n],st=load(tf/(n+'_tight_states.npz'));np.testing.assert_array_equal(seconds,st);np.testing.assert_array_equal(s[n][0],c['initial_state'])
 times=epoch+TimeDelta(seconds,format='sec');ref=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))).take_exact(times);r,v=transform_state(ref.positions_m,ref.velocities_m_s,times,'ITRS','GCRS');out={'residuals':{},'pairs':{},'convergence':{},'labels':c['labels']};rows=[];errors={};racs={}
 for n in s:
  d=s[n][:,:3]-r;rac=rac_errors(d,r,v);norm=np.linalg.norm(d,axis=1);errors[n]=norm;racs[n]=rac;stat=summarize_errors(d,rac);stat.update(hours_1_3_6_m=[float(norm[h*60]) for h in [1,3,6]],terminal_RAC_m=rac[-1].tolist());out['residuals'][n]=stat
  for i,t in enumerate(seconds):rows.append(dict(model=n,utc=times[i].isot,elapsed_s=t,residual_m=norm[i],R_m=rac[i,0],A_m=rac[i,1],C_m=rac[i,2],status=c['labels']))
 write('SP3_residuals',rows);rows=[];pairs={};pairracs={}
 for a,b in [('H4','H3'),('H5','H3'),('H6','H3'),('H6','H4'),('H6','H5')]:
  name=a+'_'+b;d=s[a][:,:3]-s[b][:,:3];rac=rac_errors(d,s['H3'][:,:3],s['H3'][:,3:]);norm=np.linalg.norm(d,axis=1);stat=summarize_errors(d,rac);stat['terminal_RAC_m']=rac[-1].tolist();out['pairs'][name]=stat;pairs[name]=norm;pairracs[name]=rac
  for i,t in enumerate(seconds):rows.append(dict(pair=name,elapsed_s=t,difference_m=norm[i],R_m=rac[i,0],A_m=rac[i,1],C_m=rac[i,2],status=c['labels']))
 write('model_differences',rows);rows=[];convs={}
 for n in s:
  d=s[n]-tight[n];rac=rac_errors(d[:,:3],s['H3'][:,:3],s['H3'][:,3:]);norm=np.linalg.norm(d[:,:3],axis=1);vn=np.linalg.norm(d[:,3:],axis=1);convs[n]=norm;out['convergence'][n]=dict(max_position_m=float(norm.max()),rms_position_m=float(np.sqrt(np.mean(norm**2))),max_velocity_m_s=float(vn.max()),rms_velocity_m_s=float(np.sqrt(np.mean(vn**2))),max_abs_RAC_m=np.max(np.abs(rac),axis=0).tolist())
  for i,t in enumerate(seconds):rows.append(dict(model=n,elapsed_s=t,position_m=norm[i],velocity_m_s=vn[i],R_m=rac[i,0],A_m=rac[i,1],C_m=rac[i,2]))
 write('convergence',rows);rows=[]
 for a,b in [('H4','H3'),('H5','H3'),('H6','H3'),('H6','H4'),('H6','H5')]:
  d=(s[a]-s[b])-(tight[a]-tight[b]);rac=rac_errors(d[:,:3],s['H3'][:,:3],s['H3'][:,3:]);name=a+'_'+b;norm=np.linalg.norm(d[:,:3],axis=1)
  out.setdefault('paired_convergence',{})[name]=dict(max_position_m=float(norm.max()),rms_position_m=float(np.sqrt(np.mean(norm**2))),max_velocity_m_s=float(np.linalg.norm(d[:,3:],axis=1).max()),max_abs_RAC_m=np.max(np.abs(rac),axis=0).tolist())
  for i,t in enumerate(seconds):rows.append(dict(pair=name,elapsed_s=t,paired_position_m=norm[i],R_m=rac[i,0],A_m=rac[i,1],C_m=rac[i,2]))
 write('paired_convergence',rows)
 write('H6_states',[dict(utc=times[i].isot,elapsed_s=t,**dict(zip(['x_m','y_m','z_m','vx_m_s','vy_m_s','vz_m_s'],s['H6'][i])),status=c['labels']) for i,t in enumerate(seconds)])
 resources={n:json.loads((ROOT/f'experiments/{folder}/{n}.json').read_text()) for n,folder in [('H3','gravity_truncation_v1'),('H4','gravity_third_body_v1'),('H5','gravity_third_body_v1'),('H6','common_force_validation_v1')]};out['resources']=resources;write('resources',[dict(model=n,historical=n!='H6',**stats) for n,stats in resources.items()]);hours=seconds/3600
 for name,values,ylabel in [('SP3_residuals',errors,'SP3 position residual (m)'),('model_differences',pairs,'Model position difference (m)'),('convergence',convs,'Base/tight position difference (m)')]:
  fig,ax=plt.subplots(figsize=(10,4))
  for n,z in values.items():ax.plot(hours,z,label=n)
  ax.set(xlabel='Propagation time (h)',ylabel=ylabel);ax.legend();ax.grid();save(fig,name)
 for name,values in [('RAC_residuals',racs),('RAC_differences',pairracs)]:
  fig,axes=plt.subplots(3,1,sharex=True,figsize=(10,8))
  for j,ax in enumerate(axes):
   for n,z in values.items():ax.plot(hours,z[:,j],label=n)
   ax.set_ylabel(['R (m)','A (m)','C (m)'][j]);ax.grid()
  axes[0].legend();axes[-1].set_xlabel('Propagation time (h)');save(fig,name)
 fig,ax=plt.subplots(figsize=(9,4));ax.bar(list(resources),[x['elapsed_s'] for x in resources.values()]);ax.set(ylabel='Integration wall time (s)',title='Historical H3/H4/H5; current H6, same numerical settings');save(fig,'costs')
 for p,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==h,p
 out['protected_unchanged']=True;dump(F/'analysis.json',out)
 model=CommonForceModel(epoch,21600);frozen=dict(model_version='common_force_v1', schema_version=1, implementation_sha256={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'src/orbit').glob('*.py')}, reference_orbit_metadata=ref.metadata, status='FROZEN_FOR_NEXT_CONDITIONAL_EXPERIMENT_ONLY',labels=c['labels'],force_model=model.metadata,earth=dict(model='EGM2008',GM_m3_s2=c['GM'],radius_m=c['radius_m'],degree=40,order=40,norm='fully_normalized',tide_system='tide_free',source=c['source40'],coefficients_file='configs/egm2008_40x40.json',coefficients_sha256=sha(ROOT/'configs/egm2008_40x40.json')),t0_utc=c['t0_utc'],initial_state_GCRS_SI=c['initial_state'],initial_sha256=c['initial_sha256'],duration_s=21600,output_step_s=60,numerics_base=c['base'],numerics_tight=c['tight'],time_data=c['time_data'],code_sha256=c['new_code_sha256'],legacy_code_sha256=c['code_sha256'],evidence='experiments/common_force_validation_v1/run_summary.json',evidence_sha256=sha(F/'run_summary.json'),limitations=['40 degree truncation not converged','PROVISIONAL_EPHEMERIS Newtonian frame/time-scale approximations','real aero and thrust unverified','TIE external height unverified','S7 not proven initial-state independent','10 minute atmosphere output uncertainty','SRP tides relativity missing'],no_density_runs_authorized=True)
 dump(ROOT/'configs/provisional_common_force_model.json',frozen)
 print(json.dumps(out,indent=2))
if __name__=='__main__':main()
