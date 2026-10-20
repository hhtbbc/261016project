"""Read-only D0--D4 reuse plus D5 analysis, audit and seven tagged figures."""
import sys,json,csv,gzip,hashlib,time,resource
from pathlib import Path
from datetime import datetime,timedelta,timezone
import numpy as np
from astropy.time import Time,TimeDelta
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data,transform_state
from orbit.drag import EarthFixedFrame
from evaluation.orbit_data import load_sp3_reference
from evaluation.orbit_metrics import rac_errors,summarize_errors
from atmosphere.provisional_drag_provider import LABELS
from atmosphere.msis_density_provider import FrozenGfzDrivers,MsisDensityProvider
TAG='msis_drag_orbit_v1';F=ROOT/'experiments'/TAG;L=ROOT/'data/processed'/TAG;OLD=ROOT/'data/processed/provisional_drag_orbit_v1';O=ROOT/'experiments/provisional_drag_orbit_v1'
TITLE='PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST'

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def writecsv(name,rows):
 with (ROOT/f'results/metrics/{TAG}_{name}.csv').open('x') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def load(name):
 folder=L if name.startswith(('D5','pre_D5')) else OLD
 with np.load(folder/f'{name}_states.npz') as z:return {k:z[k] for k in z.files}
def curve_save(fig,name):
 fig.suptitle(TITLE,fontsize=7);fig.tight_layout(rect=[0,0,1,.96]);p=ROOT/f'results/figures/{TAG}_{name}.png'
 if p.exists():raise FileExistsError(p)
 fig.savefig(p,dpi=150);plt.close(fig)
def main():
 tick=time.perf_counter();summary=json.loads((F/'run_summary.json').read_text());assert summary['numerical_gate_passed']
 config=json.loads((F/'configuration.json').read_text());data={m:load(m) for m in ['D0','D1','D2','D3','D4','D5']};base=data['D0'];seconds=base['seconds'];hours=seconds/3600
 for d in data.values():np.testing.assert_array_equal(d['seconds'],seconds);np.testing.assert_array_equal(d['states'][0],base['states'][0])
 for source in json.loads((ROOT/'logs/swarm_sp3_inspection.json').read_text())['files']:assert sha(ROOT/source['file'])==source['sha256']
 configure_time_data();t0=Time(config['t0_utc'],scale='utc');times=t0+TimeDelta(seconds,format='sec')
 ref=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))).take_exact(times)
 rg,vg=transform_state(ref.positions_m,ref.velocities_m_s,times,'ITRS','GCRS')
 own={};own['D0']=None
 for m in ['D1','D2','D3','D4']:
  own[m]={'rho':data[m]['density'],'drag':data[m]['drag_gcrs'],'relative':data[m]['relative_itrs']}
 rows=list(csv.DictReader((ROOT/f'results/metrics/{TAG}_D5_states.csv').open()))
 own['D5']={'rho':np.array([float(r['rho_kg_m3']) for r in rows]),'drag':np.array([[float(r[k]) for k in ['drag_gcrs_ax_m_s2','drag_gcrs_ay_m_s2','drag_gcrs_az_m_s2']] for r in rows]),'relative':np.array([[float(r[k]) for k in ['relative_itrs_vx_m_s','relative_itrs_vy_m_s','relative_itrs_vz_m_s']] for r in rows])}
 pairs={};racs={};series=[]
 R0=base['states'][:,:3]/np.linalg.norm(base['states'][:,:3],axis=1)[:,None]
 C0=np.cross(base['states'][:,:3],base['states'][:,3:]);C0=C0/np.linalg.norm(C0,axis=1)[:,None];A0=np.cross(C0,R0)
 orbital_phases={m:np.arctan2(np.sum(d['states'][:,:3]*A0,axis=1),np.sum(d['states'][:,:3]*R0,axis=1)) for m,d in data.items()}
 for m in ['D0','D1','D2','D3','D4','D5']:
  delta=data[m]['states'][:,:3]-base['states'][:,:3];rac=rac_errors(delta,base['states'][:,:3],base['states'][:,3:])
  key=m+'_D0';pairs[key]=summarize_errors(delta,rac);pairs[key]['terminal_RAC_m']=rac[-1].tolist();racs[key]=rac
 for m in ['D1','D2','D3','D4']:
  delta=data['D5']['states'][:,:3]-data[m]['states'][:,:3];rac=rac_errors(delta,base['states'][:,:3],base['states'][:,3:]);key='D5_'+m
  pairs[key]=summarize_errors(delta,rac);pairs[key]['terminal_RAC_m']=rac[-1].tolist();racs[key]=rac
 for key,rac in racs.items():
  for i,s in enumerate(seconds):series.append({'status':' / '.join(LABELS),'pair':key,'utc':times[i].isot,'elapsed_s':s,'norm_m':float(np.linalg.norm(rac[i])),'R_m':rac[i,0],'A_m':rac[i,1],'C_m':rac[i,2]})
 for key,v in pairs.items():
  v['RAC_mean_square_fraction']=((np.asarray(v['rac_rmse_m'])**2)/(v['rmse_3d_m']**2)).tolist() if v['rmse_3d_m'] else [0.,0.,0.]
  left,right=key.split('_');v['terminal_projected_phase_difference_microrad']=float((orbital_phases[left][-1]-orbital_phases[right][-1])*1e6)
 writecsv('model_differences',series)
 residuals={};residualrows=[];residual_curves={}
 for m,d in data.items():
  delta=d['states'][:,:3]-rg;rac=rac_errors(delta,rg,vg);residual_curves[m]=np.linalg.norm(delta,axis=1);residuals[m]=summarize_errors(delta,rac)
  for i,s in enumerate(seconds):residualrows.append({'status':' / '.join(LABELS),'model':m,'utc':times[i].isot,'elapsed_s':s,'residual_norm_m':residual_curves[m][i],'R_m':rac[i,0],'A_m':rac[i,1],'C_m':rac[i,2]})
  residuals[m]['hours_1_3_6']={str(h):{'norm_m':float(residual_curves[m][h*60]),'RAC_m':rac[h*60].tolist()} for h in [1,3,6]}
 writecsv('exploratory_SP3_residuals',residualrows)
 density={}
 for m in ['D1','D2','D3','D4','D5']:
  rho=own[m]['rho'];norm=np.linalg.norm(own[m]['drag'],axis=1);v=np.linalg.norm(own[m]['relative'],axis=1)
  density[m]={'rho_min_kg_m3':float(rho.min()),'rho_max_kg_m3':float(rho.max()),'drag_min_m_s2':float(norm.min()),'drag_max_m_s2':float(norm.max()),'relative_speed_min_m_s':float(v.min()),'relative_speed_max_m_s':float(v.max())}
  if m!='D5':
   speed_ratio=np.sum(own['D5']['relative']**2,axis=1)/np.sum(own[m]['relative']**2,axis=1)
   calculated=own['D5']['rho']/rho*speed_ratio
   actual=np.linalg.norm(own['D5']['drag'],axis=1)/norm
   density[m]['own_path_drag_density_ratio_identity_max_abs']=float(np.max(abs(actual-calculated)))
   density[m]['own_path_D5_to_TIE_density_ratio_median']=float(np.median(own['D5']['rho']/rho))
 resources=[]
 for m in data:
  meta=json.loads(((F if m=='D5' else O)/f'{m}.json').read_text());integ=meta['integration'];force=meta.get('force') or {};query=force.get('density_query_seconds',0);n=force.get('density_queries',0)
  source='NRLMSIS' if m=='D5' else ('S3' if m in ['D1','D3'] else ('S7' if m in ['D2','D4'] else 'NONE'))
  offline=0.
  if source in ['S3','S7']:offline=json.loads((ROOT/f'experiments/tiegcm2023_{source.lower()}_continuous_v1/run_status.json').read_text())['elapsed_s']
  total=meta.get('wall_with_output_diagnostics_s',meta.get('wall_with_output_diagnostics_s',0))
  resources.append({'status':' / '.join(LABELS),'model':m,'density_source':source,'offline_field_generation_s':offline,'density_queries_RHS_plus_output':n,'density_query_total_s_RHS_plus_output':query,'mean_query_ms_RHS_plus_output':query/n*1000 if n else 0,'integration_RHS_s_includes_queries':integ['elapsed_s'],'online_total_with_output_s':total,'from_scratch_generation_plus_online_s':offline+total,'nfev':integ['nfev'],'accepted_steps':integ['accepted_steps'],'cached_columns':force.get('cached_columns',0),'cached_array_bytes':force.get('cached_array_bytes',0),'process_cumulative_peak_RSS_MiB':meta['peak_RSS_MiB']})
 writecsv('resources',resources)
 # Full streaming density/force audit. Drivers independently matched by UTC bucket.
 driver=FrozenGfzDrivers(ROOT/'configs/nrlmsis2023_gfz_frozen.json');frame=EarthFixedFrame(t0);audits={}
 for runname in ['pre_D5','pre_D5_tight','D5','D5_tight']:
  counts={'rhs':0,'output':0};maxformula=0.;maxnorm=0.;maxitrs=0.;maxvelocity=0.;maxepoch=0.;boundary=[]
  with gzip.open(L/f'{runname}_queries.jsonl.gz','rt') as f:
   for j,line in enumerate(f):
    r=json.loads(line);assert tuple(r['labels'])==LABELS and not r.get('failure') and r['density_valid']
    phase=r['phase'];counts[phase]+=1
    epoch=Time(r['utc_jd1'],r['utc_jd2'],format='jd',scale='utc');s=r['seconds'];maxepoch=max(maxepoch,abs((epoch-t0).to_value('s')-s))
    # Raw independent history slices from the frozen map, not the provider.at implementation.
    dt=epoch.to_datetime(timezone=timezone.utc);bin_time=dt.replace(hour=dt.hour//3*3,minute=0,second=0,microsecond=0)
    def ap(lag):return driver._ap[(bin_time-timedelta(hours=lag)).strftime('%Y-%m-%dT%H:00:00Z')]
    expected=[driver._daily[dt.date().isoformat()],ap(0),ap(3),ap(6),ap(9),float(np.mean([ap(k) for k in range(12,34,3)])),float(np.mean([ap(k) for k in range(36,58,3)]))]
    np.testing.assert_array_equal(expected,r['drivers']['ap']);assert r['drivers']['f107_previous_day']==156.1
    assert abs(r['drivers']['f107a_centered81']-160.79135802469133)<1e-10
    assert driver.sha256 in r['drivers']['provenance']
    vr=np.array(r['relative_velocity_itrs_m_s']);ai=np.array(r['acceleration_itrs_m_s2']);ag=np.array(r['acceleration_gcrs_m_s2']);rho=r['rho_kg_m3']
    expectedforce=-.5*rho*2.2/400*np.linalg.norm(vr)*vr
    maxformula=max(maxformula,float(np.max(abs(ai-expectedforce))));maxnorm=max(maxnorm,float(abs(np.linalg.norm(ai)-np.linalg.norm(ag))));assert np.dot(vr,ai)<0
    assert 1e-15<rho<1e-9 and np.linalg.norm(ag)<1e-4
    if abs(s-10798)<40 or abs(s-21598)<40:boundary.append({'run':runname,'phase':phase,'seconds':s,'utc':epoch.isot,'ap_current':expected[1],'rho_kg_m3':rho})
    if j%251==0 or phase=='output' and counts[phase] in [1,181,361]:
     _,ri,vi,Q=frame.state_to_itrs(s,r['position_gcrs_m'],r['velocity_gcrs_m_s'])
     maxitrs=max(maxitrs,float(np.linalg.norm(ri-r['position_itrs_m'])));maxvelocity=max(maxvelocity,float(np.linalg.norm(vi-vr)))
     np.testing.assert_allclose(Q.T@ai,ag,rtol=1e-12,atol=1e-22)
  assert maxformula<1e-20 and maxnorm<1e-20 and maxitrs<1e-5 and maxvelocity<1e-6 and maxepoch<1e-6
  meta=json.loads((F/f'{runname}.json').read_text());assert counts['rhs']==meta['integration']['nfev'] and counts['output']==meta['integration']['output_samples']
  audits[runname]={'counts':counts,'max_force_formula_abs_m_s2':maxformula,'max_rotation_norm_difference_m_s2':maxnorm,'sampled_ITRS_position_difference_m':maxitrs,'sampled_relative_velocity_difference_m_s':maxvelocity,'epoch_difference_max_s':maxepoch,'boundary_records':boundary,'all_queries_valid':True}
 boundary_rows=[{**r,'status':' / '.join(LABELS)} for a in audits.values() for r in a['boundary_records']];writecsv('Ap_boundaries',boundary_rows)
 for a in audits.values():a['boundary_count']=len(a.pop('boundary_records'))
 for p,d in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==d
 # Plot 1: all six, including exact zero D0.
 fig,ax=plt.subplots(figsize=(10,4))
 for m in data:ax.plot(hours,np.linalg.norm(racs[m+'_D0'],axis=1),label=m)
 ax.set(xlabel='Time since 2023-03-21 00:00:02 UTC (h)',ylabel='Position difference to D0 (m)',title='Same initial state; 400 kg / Cd 2.2 / 1 m² / zero ITRS wind');ax.legend(ncol=6);ax.grid(alpha=.25);curve_save(fig,'position_differences')
 fig,ax=plt.subplots(figsize=(10,4));keys=['D1_D0','D2_D0','D3_D0','D4_D0','D5_D0','D5_D1','D5_D2','D5_D3','D5_D4'];ax.bar(keys,[pairs[k]['terminal_m'] for k in keys]);ax.set(ylabel='6h terminal model displacement (m)',title='TIE A/B remain provisional; these are not prediction errors');ax.tick_params(axis='x',rotation=25);curve_save(fig,'terminal_displacements')
 fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True)
 for m in own:
  if m=='D0':continue
  axes[0].plot(hours,own[m]['rho'],label=m);axes[1].plot(hours,np.linalg.norm(own[m]['drag'],axis=1),label=m)
 axes[0].set(ylabel='Density (kg/m³)',title='Queried at each model own propagated state; NRLMSIS uses WGS84')
 axes[1].set(ylabel='Drag acceleration (m/s²)',xlabel='Elapsed time (h)');axes[0].legend(ncol=5);curve_save(fig,'density_drag')
 fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True)
 for j,label in enumerate(['R outward','A = C x R','C = r x v / |r x v|']):
  for m in ['D1','D2','D3','D4','D5']:axes[j].plot(hours,racs[m+'_D0'][:,j],label=m)
  axes[j].set_ylabel(label+' (m)');axes[j].grid(alpha=.25)
 axes[0].set_title('Signed perturbations; common D0 inertial RAC basis');axes[0].legend(ncol=5);axes[-1].set_xlabel('Elapsed time (h)');curve_save(fig,'RAC')
 fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True)
 for m in data:axes[0].plot(hours,residual_curves[m],label=m)
 for m in ['D1','D2','D3','D4','D5']:axes[1].plot(hours,residual_curves[m]-residual_curves['D0'],label=m+' minus D0 residual norm')
 axes[0].set(ylabel='Exploratory SP3 residual (m)',title='Incomplete force model + synthetic parameters; no accuracy ranking');axes[0].legend(ncol=6);axes[1].set(ylabel='Residual norm difference (m)',xlabel='Elapsed time (h)');axes[1].legend(fontsize=7,ncol=2);curve_save(fig,'SP3_residuals')
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 axes[0].bar([r['model'] for r in resources],[r['integration_RHS_s_includes_queries'] for r in resources]);axes[0].set(ylabel='Historical/current integral runtime (s)',title='Online RK45 includes queries and frame transforms')
 axes[1].bar([r['model'] for r in resources],[r['offline_field_generation_s'] for r in resources]);axes[1].set(ylabel='Reusable field simulation wall time (s)',title='S3=5d10m / S7=9d10m, 4 MPI ranks; not equal tasks');curve_save(fig,'costs')
 fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True);tight=load('D5_tight');axes[0].plot(hours,np.linalg.norm(data['D5']['states'][:,:3]-tight['states'][:,:3],axis=1),label='D5 base/tight')
 for m in ['D0','D1','D2','D4']:
  oldtight=load(m+'_tight');e=(data['D5']['states'][:,:3]-data[m]['states'][:,:3])-(tight['states'][:,:3]-oldtight['states'][:,:3]);axes[1].plot(hours,np.linalg.norm(e,axis=1),label='D5_'+m)
 axes[0].set(ylabel='State difference (m)',title='Base 1e-10/30s vs tight 1e-12/15s; no D0--D4 rerun');axes[1].set(ylabel='Paired displacement change (m)',xlabel='Elapsed time (h)');axes[0].legend();axes[1].legend(ncol=4);curve_save(fig,'convergence')
 output={'labels':LABELS,'pairs':pairs,'SP3_exploratory_residuals':residuals,'density_on_own_states':density,'resources':resources,'query_audits':audits,'protected_unchanged':True,'all_initial_states_identical':True,'same_reference_trajectory_density_comparison':'Preserved results/metrics/nrlmsis2023_60s.csv; not conflated with own-state curves','analysis_wall_s':time.perf_counter()-tick,'analysis_peak_RSS_MiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'new_TIE_runs':0,'new_D0_D4_runs':0,'new_D5_runs':4}
 with (F/'analysis.json').open('x') as f:json.dump(output,f,indent=2,allow_nan=False)
 print(json.dumps({k:output[k] for k in ['pairs','density_on_own_states','analysis_wall_s']},indent=2))
if __name__=='__main__':main()
