"""Small CPU-only catalogue, observation QA, header inventory and EOS sensitivity."""
from pathlib import Path
import sys,json,csv,re,time,resource
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np
from netCDF4 import Dataset,num2date
from prepare_fourcastden_swarm_observation_v1 import sha,dump
from observations.density_catalog import read_swarm_pod,calibration_time_mask
from atmosphere.restart_validation import inspect_restart,CURRENT,PREVIOUS,LOWER,REQUIRED
from atmosphere.dart_density_audit import helium_eos_density_ratio
from persistence_den_engineering_v3 import csvout
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
TAG='thermosphere_observation_assimilation_feasibility_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG;D=ROOT/'data/raw'/TAG

def save(fig,name):
 fig.text(.5,.012,'Actual instantaneous DNS POD0301 | UTC / GRS80 product contract | retrieval != absolute truth | no correction or assimilation',ha='center',fontsize=7);fig.tight_layout(rect=(0,.045,1,.94));fig.savefig(O/name,dpi=160);plt.close(fig)
def category(v):
 if v in LOWER:return 'lower_boundary_or_boundary_history'
 if v in PREVIOUS:return 'persisted_filtered_previous_timestep'
 if v in CURRENT:return 'stored_current_coupled_or_evolved_field' if v not in ['NE','TI','TE','O2P','OMEGA','Z','POTEN'] else 'stored_coupled_or_diagnostic_field_not_independent_state'
 if v in ['DEN','ZG','N2','WN','TEC','QJOULE','UI_ExB','VI_ExB','WI_ExB']:return 'diagnostic_not_complete_restart'
 if v in ['f107d','f107a','Kp','hpower','ctpoten']:return 'external_driver_diagnostic'
 return 'coordinate_clock_or_other_metadata'
def main():
 start=time.perf_counter();assert not (F/'analysis_started.json').exists();dump(F/'analysis_started.json',dict(new_model_launches=0,correction_fit=False,DART_execution=False,Swarm_B_values_read=False))
 collections=[];samples=[];index=[];allrows=[]
 for sat,year,folder in [('A',2021,ROOT/'data/raw/swarm_tiegcm_2021_spinup_observation_v1'),('A',2022,ROOT/'data/raw/swarm_tiegcm_2022_observation_v1'),('C',2022,D)]:
  path=next(folder.glob('*.cdf'));info=D/'official'/f'SW_OPER_DNS{sat}POD_2__info.json';expected=sha(path)
  if sat=='A':
   prior=json.loads((ROOT/f'experiments/swarm_tiegcm_{year}_observation_v1/downloads.json').read_text());assert any(x['path']==str(path.relative_to(ROOT)) and x['SHA256']==expected for x in prior['members'])
  else:
   prior=json.loads((F/'Swarm_C_download_complete.json').read_text());assert any(x['path']==str(path.relative_to(ROOT)) and x['SHA256']==expected for x in prior['members'])
  rows,a,contract=read_swarm_pod(path,info,expected,satellite=sat);assert len(rows)==2880;assert str(a['utc'][0]).startswith(f'{year}-03-24T00:00') and str(a['utc'][-1]).startswith(f'{year}-03-24T23:59:30');cad=np.diff(a['utc'])/np.timedelta64(1,'s');assert np.all(cad==30)
  for r in rows:r['source_file']=str(path.relative_to(ROOT))
  allrows+=rows;mask=a['quality'];collections.append((sat,year,a));u,c=np.unique(a['validity_flag'],return_counts=True)
  summary=dict(mission='Swarm',satellite=sat,year=year,product_id=rows[0]['product_id'],product_version='0301',records=len(rows),valid=int(mask.sum()),valid_fraction=float(mask.mean()),flags={str(k):int(v) for k,v in zip(u,c)},UTC_start=rows[0]['UTC'],UTC_stop=rows[-1]['UTC'],cadence_seconds=float(np.median(cad)),missing_slots=int(((a['utc'][-1]-a['utc'][0])/np.timedelta64(30,'s'))+1-len(rows)),density_min_kg_m3=float(a['density'][mask].min()),density_max_kg_m3=float(a['density'][mask].max()),height_min_km=float(a['altitude'][mask].min()/1000),height_max_km=float(a['altitude'][mask].max()/1000),latitude_min_deg=float(a['latitude'][mask].min()),latitude_max_deg=float(a['latitude'][mask].max()),source_file=str(path.relative_to(ROOT)),source_SHA256=expected,coordinate_reference=rows[0]['coordinate_reference'],metadata_height_description_typo=next(p['description'] for p in json.loads(info.read_text())['parameters'] if p['name']=='Height_GD'),C_SP3_geometry_independently_verified=False if sat=='C' else 'prior2023 alignment does not prove2021/2022 same-date SP3')
  samples.append(summary);index.append({k:summary[k] for k in ['satellite','year','product_id','product_version','records','valid','UTC_start','UTC_stop','cadence_seconds','source_file','source_SHA256','coordinate_reference']})
  dump(F/f'{sat}_{year}_CDF_contract_local.json',contract)
 csvout(O/'unified_observations_local.csv',allrows);csvout(O/'observation_file_index.csv',index);dump(F/'observation_quality.json',samples)
 # Time-only anti-leakage guard, no residual values estimated or model queries.
 aa=next(a for s,y,a in collections if s=='A' and y==2022);mask=calibration_time_mask(aa['utc'],'2022-03-24T06:00:00Z');assert mask.sum()==360 and np.all(aa['utc'][mask]<np.datetime64('2022-03-24T06:00'));dump(F/'causal_split_dryrun.json',dict(PASS=True,cutoff='2022-03-24T06:00:00Z',history_hours=3,calibration_times_only=int(mask.sum()),C_development=True,B_reserved=True,no_fitting=True,no_model_density_queries=True))
 # Catalogue records expose metadata only, not reserved B density values.
 catalog=[]
 availability=json.loads((F/'product_availability.json').read_text())
 for path in sorted((D/'official').glob('*_info.json')):
  j=json.loads(path.read_text());product=j['x_dataset'];parameters={p['name']:p for p in j['parameters']};sat=product[11] if product.startswith('SW_OPER_DNS') else ''
  catalog.append(dict(product_id=product,coverage_start=j['startDate'],coverage_stop=j['stopDate'],cadence=j.get('cadence'),fields=' '.join(parameters),density_units=parameters['density']['units'],coordinates=parameters.get('Latitude_GD',{}).get('description','UNKNOWN')+'; '+parameters.get('Height_GD',{}).get('description','UNKNOWN'),flag_definition=parameters.get('validity_flag',{}).get('description','NO FLAG exposed; do not infer all valid'),source=j.get('resourceURL'),retrieval=j.get('description'),role='RESERVED_B_METADATA_ONLY' if product.startswith('SW_OPER_DNSB') else 'A_CALIBRATION_CANDIDATE' if product=='SW_OPER_DNSAPOD_2_' else 'C_DEVELOPMENT' if product=='SW_OPER_DNSCPOD_2_' else 'FUTURE_CROSS_ALTITUDE_OR_LEGACY',version='0301 exact target files verified' if 'POD' in product else 'NOT_CONFIRMED: no raw product downloaded',specific_target_day_existence='C/B POD exact files listed in product_availability.json' if 'POD' in product and sat in ['C','B'] else 'A POD locally present' if product=='SW_OPER_DNSAPOD_2_' else 'NOT_VERIFIED from catalogue range alone',metadata_SHA256=sha(path)))
 csvout(O/'product_catalog.csv',catalog)
 # Audit source/warm primary + diagnostic secondary, read-only.
 inventory=[];statefiles=[];sources=[('official_smin',ROOT/'data/raw/tiegcm2_support/tiegcm_res5.0_mareqx_smin_prim.nc'),('official_smax',ROOT/'data/raw/tiegcm_2021_spinup_initial_condition_v1/tiegcm_res5.0_mareqx_smax_prim.nc'),('2021_B14_warm',ROOT/'experiments/tiegcm_2021_spinup_14day_v1/B14/primary_015.nc'),('2022_B14_warm',ROOT/'experiments/tiegcm_2022_b14_exploratory_pair_v2/B14/primary_015.nc'),('2021_B14_secondary',ROOT/'experiments/tiegcm_2021_spinup_14day_v1/B14/secondary_015.nc'),('2022_B14_secondary',ROOT/'experiments/tiegcm_2022_b14_exploratory_pair_v2/B14/secondary_015.nc')]
 eos=[]
 for label,path in sources:
  digest=sha(path)
  with Dataset(path) as n:
   mt=np.asarray(n['mtime'][:]).astype(int);clock=mt[0].tolist();audit=inspect_restart(path,clock);times=[str(t) for t in num2date(n['time'][:],n['time'].units)]
   statefiles.append(dict(label=label,file=str(path.relative_to(ROOT)),SHA256=digest,bytes=path.stat().st_size,history_type=getattr(n,'history_type',None),run_type=getattr(n,'run_type',None),model_version=getattr(n,'model_version',None),source_file=getattr(n,'source_file',None),dimensions={k:len(v) for k,v in n.dimensions.items()},UTC_from_time_units=times,mtime=mt.tolist(),structure_audit=audit))
   for v in n.variables:
    q=n[v];inventory.append(dict(file_label=label,variable=v,category=category(v),required_primary=v in REQUIRED,dimensions=' '.join(q.dimensions),dtype=str(q.dtype),units=getattr(q,'units','UNSPECIFIED'),long_name=getattr(q,'long_name',''),file_SHA256=digest))
   if label.endswith('_warm'):
    a,b,h=[np.asarray(n[k][0],float) for k in ['O1','O2','HE']];valid=np.isfinite(a)&np.isfinite(b)&np.isfinite(h)&(a>=0)&(b>=0)&(h>=0)&(a+b+h<=1)
    ratio=np.full(a.shape,np.nan);ratio[valid]=helium_eos_density_ratio(a[valid],b[valid],h[valid])
    for lev in range(a.shape[0]):
     rr=ratio[lev][valid[lev]];eos.append(dict(case=label,native_lev_index=lev,valid=int(valid[lev].sum()),total=int(valid[lev].size),He_mass_fraction_max=float(h[lev][valid[lev]].max()) if len(rr) else None,rho_four_species_over_three_median=float(np.median(rr)) if len(rr) else None,conditional_absolute_relative_P95=float(np.percentile(abs(rr-1),95)) if len(rr) else None,meaning='same P/T ideal EOS He sensitivity only; NOT DART vs nativeDEN error; ignores Ar/other species'))
 csvout(O/'actual_variable_inventory.csv',inventory);dump(F/'initial_and_warm_state_metadata.json',statefiles);csvout(O/'DART_He_EOS_sensitivity.csv',eos)
 # Namelist provenance for every existing trajectory.
 cases={'2021_A7':'tiegcm_training_mar23_v2_2021_longrun','2021_B7':'tiegcm_2021_spinup_initial_condition_v1/B','2021_A14':'tiegcm_2021_spinup_14day_v1/A14','2021_B14':'tiegcm_2021_spinup_14day_v1/B14','2022_A7':'tiegcm_training_mar23_v2_2022_longrun','2022_B7':'tiegcm_2022_dual_initial_spinup_v1','2022_A14':'tiegcm_2022_spinup_14day_v1/A14','2022_B14':'tiegcm_2022_b14_exploratory_pair_v2/B14'};case_rows=[]
 for case,folder in cases.items():
  path=ROOT/'experiments'/folder/'input.inp';text=path.read_text();values={k:v.strip() for k,v in re.findall(r'^\s*(\w+)\s*=\s*(.*?)\s*$',text,re.M)};source=Path(values['SOURCE'].strip("'"));gpi=Path(values['GPI_NCFILE'].strip("'"));case_rows.append(dict(case=case,input=str(path.relative_to(ROOT)),input_SHA256=sha(path),source=str(source.relative_to(ROOT)),source_SHA256=sha(source),SOURCE_START=values['SOURCE_START'],START_YEAR=values['START_YEAR'],START=values['START'],STOP=values['STOP'],STEP=values['STEP'],GPI=str(gpi.relative_to(ROOT)),GPI_SHA256=sha(gpi),POTENTIAL_MODEL=values['POTENTIAL_MODEL'],CALC_HELIUM=values['CALC_HELIUM'],engineering='PARTIAL' if case=='2022_A14' else 'prior audit PASS; not re-executed'))
 csvout(O/'eight_trajectory_provenance.csv',case_rows)
 # Four mandatory scientific plots, no model/correction curve added.
 fig,axes=plt.subplots(2,1,figsize=(12,7))
 for sat,year,a in collections:axes[0 if year==2021 else 1].plot(a['utc'][a['quality']],a['density'][a['quality']],label=f'Swarm {sat} {year} ({int(a["quality"].sum())} valid)')
 for ax,year in zip(axes,[2021,2022]):ax.set(ylabel='Instantaneous density [kg/m3]',xlabel='UTC',title=f'{year}-03-24');ax.legend()
 save(fig,'01_observation_density_UTC.png')
 fig,axes=plt.subplots(2,1,figsize=(12,7))
 for sat,year,a in collections:axes[0 if year==2021 else 1].plot(a['utc'],a['altitude']/1000,label=f'Swarm {sat}, N={len(a["utc"])}')
 for ax,year in zip(axes,[2021,2022]):ax.set(ylabel='GRS80 product ellipsoid height [km]',xlabel='UTC',title=f'{year}-03-24');ax.legend()
 save(fig,'02_actual_height_UTC.png')
 fig,axes=plt.subplots(1,2,figsize=(12,4))
 for sat,year,a in collections:axes[0 if year==2021 else 1].scatter(a['latitude'][a['quality']],a['density'][a['quality']],s=2,label=f'{sat}, N={int(a["quality"].sum())}')
 for ax,year in zip(axes,[2021,2022]):ax.set(xlabel='GRS80 geodetic latitude [deg]',ylabel='Density [kg/m3]',title=f'{year}-03-24');ax.legend()
 save(fig,'03_latitude_density.png')
 fig,axes=plt.subplots(1,2,figsize=(12,4));labels=[f'{s["year"]} {s["satellite"]}' for s in samples];ix=np.arange(3);lo=[s['height_min_km'] for s in samples];hi=[s['height_max_km'] for s in samples];axes[0].errorbar(ix,(np.array(lo)+hi)/2,yerr=(np.array(hi)-lo)/2,fmt='o',capsize=6);axes[0].set_xticks(ix,labels);axes[0].set(ylabel='Actual observed height range [km]');axes[1].bar(ix,[s['valid_fraction']*100 for s in samples]);axes[1].set_xticks(ix,labels);axes[1].set(ylabel='Product quality-valid records [%]',ylim=(0,105));fig.suptitle('Coverage comparison only; not an accuracy ranking across satellite heights');save(fig,'04_satellite_height_coverage.png')
 protected=json.loads((F/'protected_inputs.json').read_text())
 for p,h in protected.items():assert sha(ROOT/p)==h,p
 dump(F/'analysis_complete.json',dict(PASS=True,real_observation_records=len(allrows),sources=len(samples),figures=4,prior_assets_unchanged=len(protected),state_files_read=len(sources),variables_inventory_rows=len(inventory),new_model_launches=0,corrections_fitted=0,DART_runs=0,GPU_tasks=0,Swarm_B_values_read=False,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024));print('OBSERVATION/STATE AUDIT COMPLETE',json.dumps(samples),time.perf_counter()-start)
if __name__=='__main__':main()
