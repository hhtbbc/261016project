"""Offline SP3 residuals / zonal perturbations; no integrator is called."""
import sys,json,csv,hashlib,time
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from astropy.time import Time,TimeDelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data,transform_state
from evaluation.orbit_data import load_sp3_reference
from evaluation.orbit_metrics import rac_errors,summarize_errors
from orbit.j2 import EarthFigureAxis,j2_acceleration
from orbit.higher_order_gravity import j3_acceleration,j4_acceleration
F=ROOT/'experiments/high_order_gravity_v1';L=ROOT/'data/processed/high_order_gravity_v1';TAG='high_order_gravity_v1';LABEL='PROVISIONAL / HINDCAST / NO_DRAG'
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def csvwrite(name,rows):
 with (ROOT/f'results/metrics/{TAG}_{name}.csv').open('x') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def load(p):
 with np.load(p) as z:return {k:z[k] for k in z.files}
def figsave(fig,name):
 fig.suptitle(LABEL,fontsize=8);fig.tight_layout(rect=[0,0,1,.95]);p=ROOT/f'results/figures/{TAG}_{name}.png'
 if p.exists():raise FileExistsError(p)
 fig.savefig(p,dpi=150);plt.close(fig)
def main():
 tick=time.perf_counter();run=json.loads((F/'run_summary.json').read_text());assert run['convergence']['passed'];c=json.loads((F/'configuration.json').read_text())
 protected=json.loads((F/'protected.json').read_text())
 for p,h in protected.items():assert sha(ROOT/p)==h
 data={'G0':load(ROOT/'data/processed/provisional_drag_orbit_v1/D0_states.npz'),'G1':load(L/'G1_states.npz'),'G2':load(L/'G2_states.npz')};tight=load(L/'G2_tight_states.npz');g0tight=load(ROOT/'data/processed/provisional_drag_orbit_v1/D0_tight_states.npz')
 seconds=data['G0']['seconds'];hours=seconds/3600;t0=Time(c['t0_utc'],scale='utc');times=t0+TimeDelta(seconds,format='sec');configure_time_data()
 reference=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))).take_exact(times);rg,vg=transform_state(reference.positions_m,reference.velocities_m_s,times,'ITRS','GCRS')
 out={'labels':LABEL,'residuals':{},'perturbations':{},'convergence':run['convergence'],'resources':{},'acceleration':{},'new_real_propagations':3,'new_drag_propagations':0,'SP3_sources':reference.metadata}
 errors={};racs={};rows=[]
 for name,d in data.items():
  np.testing.assert_array_equal(d['seconds'],seconds);np.testing.assert_array_equal(d['states'][0],data['G0']['states'][0]);delta=d['states'][:,:3]-rg;rac=rac_errors(delta,rg,vg);norm=np.linalg.norm(delta,axis=1);errors[name]=norm;racs[name]=rac
  stats=summarize_errors(delta,rac);stats['terminal_RAC_m']=rac[-1].tolist();stats['hours_1_3_6']={str(h):{'norm_m':float(norm[h*60]),'RAC_m':rac[h*60].tolist()} for h in [1,3,6]};out['residuals'][name]=stats
  for i,s in enumerate(seconds):rows.append({'status':LABEL,'model':name,'utc':times[i].isot,'elapsed_s':s,'residual_m':norm[i],'R_m':rac[i,0],'A_m':rac[i,1],'C_m':rac[i,2]})
 csvwrite('SP3_residuals',rows)
 pairs={};rows=[]
 for left,right in [('G1','G0'),('G2','G1'),('G2','G0')]:
  delta=data[left]['states'][:,:3]-data[right]['states'][:,:3];rac=rac_errors(delta,data['G0']['states'][:,:3],data['G0']['states'][:,3:]);norm=np.linalg.norm(delta,axis=1);key=left+'_'+right;pairs[key]=norm
  stats=summarize_errors(delta,rac);stats['terminal_RAC_m']=rac[-1].tolist();out['perturbations'][key]=stats
  for i,s in enumerate(seconds):rows.append({'status':LABEL,'pair':key,'utc':times[i].isot,'elapsed_s':s,'displacement_m':norm[i],'R_m':rac[i,0],'A_m':rac[i,1],'C_m':rac[i,2]})
 csvwrite('model_differences',rows)
 statsrows=[]
 for name in data:
  meta=json.loads(((ROOT/'experiments/provisional_drag_orbit_v1/D0.json') if name=='G0' else F/f'{name}.json').read_text());out['resources'][name]=meta
  s=meta['integration'];statsrows.append({'status':LABEL,'model':name,'reused':name=='G0','nfev':s['nfev'],'accepted_steps':s['accepted_steps'],'integration_wall_s':s['elapsed_s'],'wall_with_output_s':meta.get('wall_with_output_s',meta.get('wall_with_output_diagnostics_s')),'cumulative_process_peak_RSS_MiB':meta['peak_RSS_MiB']})
 meta=json.loads((F/'G2_tight.json').read_text());out['resources']['G2_tight']=meta;s=meta['integration'];statsrows.append({'status':LABEL,'model':'G2_tight','reused':False,'nfev':s['nfev'],'accepted_steps':s['accepted_steps'],'integration_wall_s':s['elapsed_s'],'wall_with_output_s':meta['wall_with_output_s'],'cumulative_process_peak_RSS_MiB':meta['peak_RSS_MiB']});csvwrite('resources',statsrows)
 axis=EarthFigureAxis(t0,21600,60);acc={n:[] for n in ['J2','J3','J4']};accrows=[]
 for t,state,epoch in zip(seconds,data['G2']['states'],times):
  k=axis(t);values={n:float(np.linalg.norm(fn(state[:3],k))) for n,fn in [('J2',j2_acceleration),('J3',j3_acceleration),('J4',j4_acceleration)]}
  accrows.append({'status':LABEL,'utc':epoch.isot,'elapsed_s':t,**{n+'_norm_m_s2':v for n,v in values.items()}})
  for n,v in values.items():acc[n].append(v)
 for n,values in acc.items():out['acceleration'][n]={'min_m_s2':min(values),'max_m_s2':max(values),'median_m_s2':float(np.median(values))}
 csvwrite('acceleration_common_G2_state',accrows)
 convergence=np.linalg.norm(data['G2']['states'][:,:3]-tight['states'][:,:3],axis=1);paired=np.linalg.norm((data['G2']['states'][:,:3]-data['G0']['states'][:,:3])-(tight['states'][:,:3]-g0tight['states'][:,:3]),axis=1)
 csvwrite('convergence',[{'status':LABEL,'utc':times[i].isot,'elapsed_s':t,'G2_base_tight_position_m':convergence[i],'G2_G0_paired_displacement_change_m':paired[i]} for i,t in enumerate(seconds)])
 out['changes_from_G0']={m:{'terminal_residual_change_m':out['residuals'][m]['terminal_m']-out['residuals']['G0']['terminal_m'],'RMSE_change_m':out['residuals'][m]['rmse_3d_m']-out['residuals']['G0']['rmse_3d_m'],'terminal_change_percent':100*(out['residuals'][m]['terminal_m']/out['residuals']['G0']['terminal_m']-1),'RMSE_change_percent':100*(out['residuals'][m]['rmse_3d_m']/out['residuals']['G0']['rmse_3d_m']-1)} for m in ['G1','G2']}
 old=json.loads((ROOT/'experiments/msis_drag_orbit_v1/analysis.json').read_text());out['historical_density_scale_reference']={'D5_D0_terminal_m':old['pairs']['D5_D0']['terminal_m'],'D5_TIE_terminal_m':{k:v['terminal_m'] for k,v in old['pairs'].items() if k in ['D5_D1','D5_D2','D5_D3','D5_D4']},'meaning':'Historical J2-only gravity density sensitivities; scale reference ONLY, not a new controlled density attribution'}
 fig,ax=plt.subplots(figsize=(10,4))
 for m in data:ax.plot(hours,errors[m],label=m)
 ax.set(xlabel='Propagation time (h)',ylabel='SP3 position residual (m)',title='Same SP3 initial state; zonal gravity only, no drag');ax.legend();ax.grid(alpha=.25);figsave(fig,'SP3_residuals')
 fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True)
 for j,label in enumerate(['R outward','A = C x R','C = r_ref x v_ref direction']):
  for m in data:axes[j].plot(hours,racs[m][:,j],label=m)
  axes[j].set_ylabel(label+' (m)');axes[j].grid(alpha=.25)
 axes[0].legend(ncol=3);axes[0].set_title('Signed residuals in inertial SP3 reference RAC basis');axes[-1].set_xlabel('Propagation time (h)');figsave(fig,'RAC_residuals')
 fig,ax=plt.subplots(figsize=(10,4))
 for k,x in pairs.items():ax.plot(hours,x,label=k)
 ax.axhline(old['pairs']['D5_D0']['terminal_m'],ls='--',color='gray',label='Historical synthetic drag terminal scale (not a new controlled pair)');ax.set(xlabel='Propagation time (h)',ylabel='Model displacement (m)',title='J3/J4 perturbations vs preserved G0; density reference has old gravity');ax.legend(fontsize=8);figsave(fig,'perturbations')
 fig,ax=plt.subplots(figsize=(10,4))
 for n,x in acc.items():ax.semilogy(hours,x,label=n)
 ax.set(xlabel='Propagation time (h)',ylabel='Acceleration norm (m/s²)',title='All terms evaluated at common G2 state');ax.legend();figsave(fig,'accelerations')
 fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True);axes[0].plot(hours,convergence,label='G2 state');axes[1].plot(hours,paired,label='G2_G0 paired change')
 axes[0].set(ylabel='Base/tight position difference (m)',title='1e-10 / 30s vs 1e-12 / 15s; G0 tight reused');axes[1].set(ylabel='Paired change (m)',xlabel='Propagation time (h)')
 for ax in axes:ax.legend();ax.grid(alpha=.25)
 figsave(fig,'convergence')
 fig,ax=plt.subplots(figsize=(8,4));ax.bar([x['model'] for x in statsrows],[x['integration_wall_s'] for x in statsrows]);ax.set(ylabel='Integration wall time (s)',title='G0 historical timing; G1/G2 current; no drag/frame query inside RHS');figsave(fig,'costs')
 for p,h in protected.items():assert sha(ROOT/p)==h
 out.update(protected_unchanged=True,analysis_wall_s=time.perf_counter()-tick,initial_states_identical=True)
 with (F/'analysis.json').open('x') as f:json.dump(out,f,indent=2,allow_nan=False)
 print(json.dumps(out,indent=2))
if __name__=='__main__':main()
