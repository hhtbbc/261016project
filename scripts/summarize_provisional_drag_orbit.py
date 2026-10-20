"""Offline model-difference and convergence analysis; no propagation calls."""
import argparse,csv,json,sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from astropy.time import Time,TimeDelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data,transform_state
from evaluation.orbit_data import load_sp3_reference
from evaluation.orbit_metrics import rac_errors,summarize_errors
from atmosphere.provisional_drag_provider import LABELS
TITLE=' / '.join(LABELS)

def main():
 p=argparse.ArgumentParser();p.add_argument('--run-tag',default='provisional_drag_orbit_v1');a=p.parse_args();tag=a.run_tag
 if not tag.replace('_','').isalnum():raise ValueError('Unsafe tag')
 folder=ROOT/'experiments'/tag;local=ROOT/'data/processed'/tag
 matrix=json.loads((folder/'matrix_summary.json').read_text())
 if not matrix['numerical_gate_passed']:raise RuntimeError('Numerical gate failed; interpretation blocked')
 config=json.loads((folder/'configuration.json').read_text());data={};tight={}
 for name in ['D0','D1','D2','D3','D4']:
  with np.load(local/f'{name}_states.npz') as z:data[name]={k:z[k] for k in z.files}
 for name in ['D0','D1','D2','D4']:
  with np.load(local/f'{name}_tight_states.npz') as z:tight[name]={k:z[k] for k in z.files}
 base=data['D0'];seconds=base['seconds'];times=Time(config['t0_utc'],scale='utc')+TimeDelta(seconds,format='sec')
 for d in data.values():
  np.testing.assert_array_equal(d['seconds'],seconds);np.testing.assert_array_equal(d['states'][0],base['states'][0])
 configure_time_data();reference=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))).take_exact(times)
 rg,vg=transform_state(reference.positions_m,reference.velocities_m_s,times,'ITRS','GCRS')
 pairs=[('D1','D2'),('D3','D4'),('D1','D3'),('D2','D4')]+[(name,'D0') for name in ['D1','D2','D3','D4']]
 report={'labels':LABELS,'meaning':'model position differences are sensitivities, not prediction errors','duration_s':matrix['duration_s'],'pairs':{},'exploratory_SP3_residuals':{},'density_diagnostics':{},'all_initial_states_equal':True}
 racs={};norms={}
 for left,right in pairs:
  key=left+'_'+right;delta=data[left]['states'][:,:3]-data[right]['states'][:,:3]
  rac=rac_errors(delta,base['states'][:,:3],base['states'][:,3:]);norm=np.linalg.norm(delta,axis=1)
  np.testing.assert_allclose(np.linalg.norm(rac,axis=1),norm,rtol=1e-12,atol=1e-10)
  report['pairs'][key]=summarize_errors(delta,rac);racs[key]=rac;norms[key]=norm
 for name,d in data.items():
  delta=d['states'][:,:3]-rg;rac=rac_errors(delta,rg,vg)
  report['exploratory_SP3_residuals'][name]=summarize_errors(delta,rac)
  if name!='D0':
   rho=d['density'];force=np.linalg.norm(d['drag_gcrs'],axis=1)
   relative=np.linalg.norm(d['relative_itrs'],axis=1)
   report['density_diagnostics'][name]={'density_min_kg_m3':float(rho.min()),'density_max_kg_m3':float(rho.max()),'drag_min_m_s2':float(force.min()),'drag_max_m_s2':float(force.max()),'relative_speed_min_m_s':float(relative.min()),'relative_speed_max_m_s':float(relative.max()),'max_output_log_density_step_abs':float(np.max(abs(np.diff(np.log(rho))))),'note':'60-second output path samples; internal queries separately audited'}
 old=np.load(ROOT/'experiments/rk45_j2_v1/states.npz');previous=old['B_gcrs_states'][:len(seconds)]
 report['D0_vs_preserved_J2_max_m']=float(np.max(np.linalg.norm(base['states'][:,:3]-previous[:,:3],axis=1)))
 report['convergence']=matrix['convergence'];report['numerical_gate_passed']=matrix['numerical_gate_passed']
 with (folder/'analysis.json').open('x') as f:json.dump(report,f,indent=2,allow_nan=False)
 with (ROOT/f'results/metrics/{tag}_model_differences.csv').open('x') as f:
  writer=csv.writer(f,lineterminator='\n');writer.writerow(['status','parameter_status','driver_status','utc','elapsed_s']+[k+'_'+component for k in norms for component in ['norm_m','R_m','A_m','C_m']]);writer.writerows([*LABELS,times[i].utc.isot,float(t),*[x for k in norms for x in [norms[k][i],*racs[k][i]]]] for i,t in enumerate(seconds))
 with (ROOT/f'results/metrics/{tag}_resources.csv').open('x') as f:
  writer=csv.writer(f,lineterminator='\n');writer.writerow(['status','parameter_status','driver_status','run','accepted_steps','nfev','integration_s','total_with_outputs_s','density_queries','RHS_queries','output_queries','native_density_seconds','frame_and_force_seconds','column_reads','cached_columns','peak_RSS_MiB'])
  for name,r in matrix['runs'].items():
   s=r['integration'];force=r['force'] or {};phase=force.get('phase_calls',{})
   writer.writerow([*LABELS,name,s['accepted_steps'],s['nfev'],s['elapsed_s'],r['wall_with_output_diagnostics_s'],force.get('density_queries',0),phase.get('rhs',0),phase.get('output',0),force.get('density_query_seconds',0),force.get('frame_and_drag_evaluate_seconds',0),force.get('column_reads',0),force.get('cached_columns',0),r['peak_RSS_MiB']])
 def save(fig,name):
  fig.suptitle(TITLE,fontsize=8);fig.tight_layout(rect=[0,0,1,.96]);path=ROOT/f'results/figures/{tag}_{name}.png'
  if path.exists():raise FileExistsError(path)
  fig.savefig(path,dpi=160);plt.close(fig)
 hours=seconds/3600
 fig,ax=plt.subplots(figsize=(10,5))
 for name in ['D1','D2','D3','D4']:ax.plot(hours,norms[name+'_D0'],label=name+' minus D0')
 ax.set(xlabel='Propagation time (h)',ylabel='Position difference to D0 (m)',title='Synthetic drag response; not a prediction error');ax.legend();ax.grid(alpha=.3);save(fig,'position_differences')
 fig,ax=plt.subplots(2,1,figsize=(10,7),sharex=True)
 for name in ['D1','D2','D3','D4']:
  ax[0].plot(hours,data[name]['density'],label=name)
  ax[1].plot(hours,np.linalg.norm(data[name]['drag_gcrs'],axis=1),label=name)
 ax[0].set(ylabel='Density along own propagated state (kg/m³)',title='Native density queried inside RK45; zero ITRS wind')
 ax[1].set(ylabel='Drag acceleration norm (m/s²)',xlabel='Propagation time (h)')
 for aa in ax:aa.legend();aa.grid(alpha=.3)
 save(fig,'density_drag')
 fig,ax=plt.subplots(2,1,figsize=(10,7),sharex=True)
 for pair in ['D1_D2','D3_D4']:ax[0].plot(hours,norms[pair],label=pair)
 for left,right in [('D1','D2'),('D3','D4')]:ax[1].plot(hours,(data[left]['density']/data[right]['density']-1)*100,label=left+'/'+right+' - 1')
 ax[0].set(ylabel='S3/S7 position difference (m)',title='Only density source changes within each A or B pair')
 ax[1].set(ylabel='Density difference on own paths (%)',xlabel='Propagation time (h)')
 for aa in ax:aa.legend();aa.grid(alpha=.3)
 save(fig,'source_sensitivity')
 fig,ax=plt.subplots(figsize=(10,5))
 for pair in ['D1_D3','D2_D4']:ax.plot(hours,norms[pair],label=pair)
 ax.set(xlabel='Propagation time (h)',ylabel='A/B mapping position difference (m)',title='Only mapping changes within each density-source pair');ax.legend();ax.grid(alpha=.3);save(fig,'mapping_sensitivity')
 fig,axes=plt.subplots(3,1,figsize=(10,9),sharex=True)
 for j,label in enumerate(['R outward','A = C x R','C = r x v direction']):
  for name in ['D1','D2','D3','D4']:axes[j].plot(hours,racs[name+'_D0'][:,j],label=name+' minus D0')
  axes[j].set_ylabel(label+' (m)');axes[j].legend();axes[j].grid(alpha=.3)
 axes[0].set_title('Common RAC basis from D0 GCRS state; signed perturbations');axes[-1].set_xlabel('Propagation time (h)');save(fig,'RAC_perturbations')
 fig,axes=plt.subplots(2,1,figsize=(10,7),sharex=True)
 for name in tight:
  axes[0].plot(hours,np.linalg.norm(data[name]['states'][:,:3]-tight[name]['states'][:,:3],axis=1),label=name)
 for left,right in [('D1','D2'),('D2','D4'),('D2','D0')]:
  delta=(data[left]['states'][:,:3]-data[right]['states'][:,:3])-(tight[left]['states'][:,:3]-tight[right]['states'][:,:3])
  axes[1].plot(hours,np.linalg.norm(delta,axis=1),label=left+'_'+right)
 axes[0].set(ylabel='Baseline/tight state difference (m)',title='RK45 rtol 1e-10 / 30s versus 1e-12 / 15s')
 axes[1].set(ylabel='Change in paired displacement (m)',xlabel='Propagation time (h)')
 for aa in axes:aa.legend();aa.grid(alpha=.3)
 save(fig,'convergence')
 print(json.dumps({'labels':LABELS,'pairs':report['pairs'],'convergence':report['convergence'],'D0_old_J2_difference_m':report['D0_vs_preserved_J2_max_m']},indent=2))
if __name__=='__main__':main()
