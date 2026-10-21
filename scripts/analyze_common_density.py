"""Offline C0-C3 comparisons, same-state density diagnosis and resource accounting."""
import sys,json,csv,gzip,time,hashlib,resource
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from astropy.time import Time,TimeDelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data,transform_state
from orbit.common_density_research import DensityResearchForce,LABELS
from evaluation.orbit_data import load_sp3_reference
from evaluation.orbit_metrics import rac_errors,summarize_errors
F=ROOT/'experiments/common_density_h6_v1';D=ROOT/'data/processed/common_density_h6_v1';tag='common_density_h6_v1'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for x in iter(lambda:f.read(4*1024*1024),b''):h.update(x)
 return h.hexdigest()
def load(p):
 with np.load(p) as z:return z['states'].copy(),z['seconds'].copy()
def write(name,rows):
 with (ROOT/f'results/metrics/{tag}_{name}.csv').open('x') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def dump(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False)
def save(fig,name):
 fig.suptitle('PROVISIONAL / SYNTHETIC_AERODYNAMIC_PARAMETERS / HINDCAST\nFORCE_MODEL_INCOMPLETE / PROVISIONAL_EPHEMERIS; TIE mappings A/B conditional',fontsize=8);fig.tight_layout(rect=[0,0,1,.91]);p=ROOT/f'results/figures/{tag}_{name}.png';assert not p.exists();fig.savefig(p,dpi=150);plt.close(fig)
def main():
 tick=time.perf_counter();c=json.loads((F/'configuration.json').read_text());run=json.loads((F/'run_summary.json').read_text());assert run['passed'];configure_time_data();epoch=Time(c['t0_utc'],scale='utc');states={};tight={}
 for n in ['C0','C1','C2','C3']:
  p=ROOT/'data/processed/common_force_validation_v1' if n=='C0' else D;base='H6' if n=='C0' else n;states[n],sec=load(p/(base+'_states.npz'));tight[n],st=load(p/(base+'_tight_states.npz'));np.testing.assert_array_equal(st,sec);np.testing.assert_array_equal(sec,np.arange(0,21601,60));np.testing.assert_array_equal(states[n][0],c['initial_state'])
 times=epoch+TimeDelta(sec,format='sec');reference=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))).take_exact(times);r,v=transform_state(reference.positions_m,reference.velocities_m_s,times,'ITRS','GCRS');out=dict(labels=LABELS,residuals={},pairs={},convergence={},paired_convergence={},density_on_own_trajectory={},same_position_density={},resources={},C0_reused=True);rows=[];errs={};racs={}
 for n,y in states.items():
  d=y[:,:3]-r;rac=rac_errors(d,r,v);norm=np.linalg.norm(d,axis=1);stat=summarize_errors(d,rac);stat.update(hours_1_3_6_m=[float(norm[h*60]) for h in [1,3,6]],terminal_RAC_m=rac[-1].tolist());out['residuals'][n]=stat;errs[n]=norm;racs[n]=rac
  for i,t in enumerate(sec):rows.append(dict(model=n,utc=times[i].isot,elapsed_s=t,SP3_residual_m=norm[i],R_m=rac[i,0],A_m=rac[i,1],C_m=rac[i,2],labels=' / '.join(LABELS)))
 write('SP3_residuals',rows);rows=[];paircurves={};pairRAC={}
 for a,b in [('C1','C0'),('C2','C0'),('C3','C0'),('C1','C2'),('C1','C3'),('C2','C3')]:
  n=a+'_'+b;d=states[a][:,:3]-states[b][:,:3];rac=rac_errors(d,states['C0'][:,:3],states['C0'][:,3:]);norm=np.linalg.norm(d,axis=1);s=summarize_errors(d,rac);s.update(hours_1_3_6_m=[float(norm[h*60]) for h in [1,3,6]],terminal_RAC_m=rac[-1].tolist());out['pairs'][n]=s;paircurves[n]=norm;pairRAC[n]=rac
  for i,t in enumerate(sec):rows.append(dict(pair=n,elapsed_s=t,position_difference_m=norm[i],R_m=rac[i,0],A_m=rac[i,1],C_m=rac[i,2],labels=' / '.join(LABELS)))
 write('model_differences',rows);rows=[];conv={}
 for n in states:
  d=states[n]-tight[n];rac=rac_errors(d[:,:3],states['C0'][:,:3],states['C0'][:,3:]);norm=np.linalg.norm(d[:,:3],axis=1);vn=np.linalg.norm(d[:,3:],axis=1);out['convergence'][n]=dict(max_position_m=float(norm.max()),rms_position_m=float(np.sqrt(np.mean(norm**2))),max_velocity_m_s=float(vn.max()),max_abs_RAC_m=np.max(abs(rac),axis=0).tolist());conv[n]=norm
  for i,t in enumerate(sec):rows.append(dict(model=n,elapsed_s=t,position_m=norm[i],velocity_m_s=vn[i],R_m=rac[i,0],A_m=rac[i,1],C_m=rac[i,2]))
 write('convergence',rows);rows=[]
 for a,b in [('C1','C0'),('C2','C0'),('C3','C0'),('C1','C2'),('C1','C3'),('C2','C3')]:
  delta=(states[a]-states[b])-(tight[a]-tight[b]);norm=np.linalg.norm(delta[:,:3],axis=1);rac=rac_errors(delta[:,:3],states['C0'][:,:3],states['C0'][:,3:]);out['paired_convergence'][a+'_'+b]=dict(max_position_m=float(norm.max()),rms_position_m=float(np.sqrt(np.mean(norm**2))),max_velocity_m_s=float(np.linalg.norm(delta[:,3:],axis=1).max()),max_abs_RAC_m=np.max(abs(rac),axis=0).tolist())
  for i,t in enumerate(sec):rows.append(dict(pair=a+'_'+b,elapsed_s=t,position_m=norm[i],R_m=rac[i,0],A_m=rac[i,1],C_m=rac[i,2]))
 write('paired_convergence',rows)
 online={}
 for n in ['C1','C2','C3']:
  with (ROOT/f'results/metrics/{tag}_{n}_states.csv').open() as f:online[n]=list(csv.DictReader(f))
  vals={key:np.array([float(x[key]) for x in online[n]]) for key in ['rho_kg_m3','drag_norm_m_s2','relative_speed_m_s']}
  out['density_on_own_trajectory'][n]={key:dict(min=float(a.min()),max=float(a.max()),median=float(np.median(a))) for key,a in vals.items()}
 # Same position and epoch (historical C0), strictly offline, never a dynamics input.
 rows=[];same={};same_drag={};same_stats={}
 for n in ['C1','C2','C3']:
  force=DensityResearchForce(n,epoch);values=[];acc=[]
  try:
   for i,t in enumerate(sec):
    q=force.evaluate(t,states['C0'][i,:3],states['C0'][i,3:],phase='output');values.append(q['density_kg_m3']);acc.append(np.linalg.norm(q['acceleration_gcrs_m_s2']));rows.append(dict(model=n,elapsed_s=t,utc=times[i].isot,reference='frozen C0 state, offline only',rho_kg_m3=q['density_kg_m3'],drag_norm_m_s2=acc[-1],lat_deg=q['query'].latitude_deg,height_wgs84_m=q['query'].height_wgs84_m,labels=' / '.join(LABELS)))
   same_stats[n]=force.statistics()
  finally:force.close()
  same[n]=np.array(values);same_drag[n]=np.array(acc)
 write('same_C0_density',rows);out['same_position_query_resources']=same_stats
 for a,b in [('C1','C2'),('C1','C3'),('C2','C3')]:
  ratio=same[a]/same[b];log=np.log(ratio);ar=abs(ratio-1);out['same_position_density'][a+'_'+b]=dict(ratio_median=float(np.median(ratio)),absolute_relative_p95=float(np.percentile(ar,95)),log_difference_rms=float(np.sqrt(np.mean(log**2))),same_velocity_force_ratio_max_difference=float(np.max(abs(same_drag[a]/same_drag[b]-ratio))))
 # Latitude bins use one common reference query latitude, without mixing trajectories.
 lat=np.array([x['lat_deg'] for x in rows if x['model']=='C1']);bins=[('south_polar',-90,-60),('south_mid',-60,-30),('low_latitude',-30,30),('north_mid',30,60),('north_polar',60,90)];z=[]
 for a,b in [('C1','C2'),('C1','C3'),('C2','C3')]:
  for name,lo,hi in bins:
   mask=(lat>=lo)&(lat<(hi if hi<90 else 91));ratio=same[a][mask]/same[b][mask];z.append(dict(pair=a+'_'+b,latitude_band=name,samples=int(mask.sum()),median_ratio=float(np.median(ratio)),p95_absolute_relative=float(np.percentile(abs(ratio-1),95))))
 write('latitude_density_comparison',z)
 hist=json.loads((ROOT/'experiments/common_force_validation_v1/H6.json').read_text());costrows=[dict(model='C0',historical=True,offline_field_s=0.,online_density_s=0.,query_mean_ms=0.,query_p95_ms=0.,density_queries=0,nfev=hist['nfev'],integration_s=hist['elapsed_s'],online_total_s=hist['elapsed_s'],column_reads=0,cached_columns=0,cache_hits=0)]
 offline_s7=json.loads((ROOT/'experiments/tiegcm2023_s7_continuous_v1/run_status.json').read_text())['elapsed_s']
 out['S7_generation_resource_source']='experiments/tiegcm2023_s7_continuous_v1/run_status.json'
 for n in ['C1','C2','C3']:
  s=run['runs'][n];f=s['force'];offline=0. if n=='C1' else offline_s7;costrows.append(dict(model=n,historical=False,offline_field_s=offline,online_density_s=f['instrumented_density_seconds'],query_mean_ms=f['query_mean_ms'],query_p95_ms=f['query_p95_ms'],density_queries=f['density_queries'],nfev=s['integration']['nfev'],integration_s=s['integration']['elapsed_s'],online_total_s=s['wall_with_output_s'],column_reads=f.get('column_reads',0),cached_columns=f.get('cached_columns',0),cache_hits=f.get('column_cache_hits',0)))
 for row in costrows:
  row.update(current_incremental_field_generation_s=0.,from_zero_field_plus_online_reference_s=row['offline_field_s']+row['online_total_s'],process_cumulative_peak_RSS_MiB=run['runs'][row['model']]['peak_RSS_MiB'] if row['model']!='C0' else json.loads((ROOT/'experiments/common_force_validation_v1/run_summary.json').read_text())['peak_RSS_MiB'])
 write('resources',costrows);out['resources']={x['model']:x for x in costrows};out['S7_generation_cost_note']='Historical 9d10m, four MPI, 1382.676s; generated once and shared across A/B, not added twice. Current new field generation=0. Offline/online workloads differ.'
 hours=sec/3600
 for name,curves,ylabel in [('position_differences',paircurves,'Model position difference (m)'),('SP3_residuals',errs,'SP3 position residual (m)'),('convergence',conv,'Base/tight position difference (m)')]:
  fig,ax=plt.subplots(figsize=(10,4))
  for n,z in curves.items():ax.plot(hours,z,label=n)
  ax.set(xlabel='Propagation time (h)',ylabel=ylabel);ax.legend();ax.grid();save(fig,name)
 for name,curves in [('RAC_differences',pairRAC),('RAC_residuals',racs)]:
  fig,axes=plt.subplots(3,1,sharex=True,figsize=(10,8))
  for j,ax in enumerate(axes):
   for n,z in curves.items():ax.plot(hours,z[:,j],label=n)
   ax.set_ylabel(['R (m)','A (m)','C (m)'][j]);ax.grid()
  axes[0].legend(ncol=2);axes[-1].set_xlabel('Propagation time (h)');save(fig,name)
 fig,axes=plt.subplots(2,1,sharex=True,figsize=(10,7))
 for n in ['C1','C2','C3']:
  axes[0].plot(hours,[float(x['rho_kg_m3']) for x in online[n]],label=n+' own trajectory');axes[1].plot(hours,[float(x['drag_norm_m_s2']) for x in online[n]],label=n)
 axes[0].set_ylabel('Density (kg/m³)');axes[1].set(ylabel='Drag acceleration (m/s²)',xlabel='Propagation time (h)')
 for ax in axes:ax.legend();ax.grid()
 save(fig,'density_drag')
 fig,axes=plt.subplots(2,1,sharex=True,figsize=(10,7))
 for n in same:axes[0].plot(hours,same[n],label=n+' at common C0')
 for a,b in [('C1','C2'),('C1','C3'),('C2','C3')]:axes[1].plot(hours,np.log(same[a]/same[b]),label=a+'/'+b)
 axes[0].set_ylabel('Density (kg/m³)');axes[1].set(ylabel='ln density ratio',xlabel='Propagation time (h)')
 for ax in axes:ax.legend();ax.grid()
 save(fig,'same_position_density')
 fig,ax=plt.subplots(figsize=(9,4))
 for n in same:ax.scatter(lat,same[n],s=5,label=n+' at C0')
 ax.set(xlabel='Common C0 WGS84 latitude (deg)',ylabel='Density (kg/m³)',title='Conditional density vs latitude; height/time also vary');ax.legend();ax.grid();save(fig,'latitude_density')
 fig,ax=plt.subplots(figsize=(8,4));ax.bar(['C1-C0','C2-C0','C3-C0'],[out['pairs'][n+'_C0']['terminal_m'] for n in ['C1','C2','C3']]);ax.set(ylabel='Terminal model displacement (m)',title='Same H6, synthetic m/Cd/A, zero ITRS wind');save(fig,'terminal_drag')
 fig,ax=plt.subplots(figsize=(9,4));x=np.arange(4);ax.bar(x-.2,[r['integration_s'] for r in costrows],width=.4,label='RK45 incl. RHS queries');ax.bar(x+.2,[r['online_density_s'] for r in costrows],width=.4,label='Density subset (do not add)');ax.set(xticks=x,xticklabels=['C0 historical','C1 MSIS','C2 S7/A','C3 S7/B'],ylabel='Wall time (s)');ax.legend();save(fig,'costs')
 # Historical J2 conditions are shown separately, not treated as controlled force-model comparisons.
 old=json.loads((ROOT/'experiments/msis_drag_orbit_v1/analysis.json').read_text())
 out['historical_J2_note']='Old D0-D5 only historical context; no mixed ranking or repropagation. See MSIS_DRAG_ORBIT_EXPERIMENT.'
 out['analysis_wall_s']=time.perf_counter()-tick;out['analysis_peak_RSS_MiB']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
 for p,h in json.loads((F/'protected.json').read_text()).items():assert sha(ROOT/p)==h,p
 out['protected_unchanged']=True;dump(F/'analysis.json',out);print(json.dumps(out,indent=2))
if __name__=='__main__':main()
