"""Offline completion after strict bitwise-prefix diagnostic assertion; no launches.

Preserves original script/log and unchanged numeric thresholds. Non-bitwise prefix
is quantified, never promoted to bitwise PASS; overall native restart remains FAIL.
"""
from pathlib import Path
import sys,json,csv,hashlib,datetime
import numpy as np
from netCDF4 import Dataset
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import run_tiegcm_runtime_restart_audit as m
O=m.OUT;S=m.SUITE

def writecsv(name,rows):
 with (O/name).open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def compare_fields(a,b,k,ia,ib,core):
 va=a[k];vb=b[k];assert va.dimensions==vb.dimensions and va.dtype==vb.dtype and getattr(va,'units',None)==getattr(vb,'units',None)
 x,mx=m.fields(a,k,ia);y,my=m.fields(b,k,ib)
 if core:scale,atol=m.UNIT[va.units];rtol=1e-10 if va.dtype==np.dtype('float64') else 1e-6
 else:scale,atol,rtol=1.,0.,0.
 return {'variable':k,'core':core,'native_unit':getattr(va,'units','not supplied'),'scale':scale,'atol':atol,'rtol':rtol,'bitwise_values_and_masks':bool(np.array_equal(x,y,equal_nan=True) and np.array_equal(mx,my)),**m.compare_arrays(x,y,mx,my,atol=atol,rtol=rtol,scale=scale)}

def main():
 assert all(json.loads((S/g/'run_status.json').read_text())['normal_exit_count']==4 for g in ['continuous','segment','resumed'])
 rows=[];prefix=[];ledger=[]
 for typ in ['primary','secondary']:
  pa=S/'continuous'/f'{typ}.nc';pb=S/'resumed'/f'{typ}.nc';ledger.append({'type':typ,'continuous_SHA256':m.sha(pa),'resumed_SHA256':m.sha(pb),'same_file_bytes':m.sha(pa)==m.sha(pb)})
  with Dataset(pa) as a,Dataset(pb) as b:
   for n in [a,b]:assert (n['year'][:]==2021).all()
   for k in ['lat','lon','lev','ilev','mlat','mlon','mlev','imlev']:np.testing.assert_array_equal(a[k][:],b[k][:])
   ia=int(np.flatnonzero((np.asarray(a['mtime'][:])==[82,0,20]).all(axis=1))[0]);ib=int(np.flatnonzero((np.asarray(b['mtime'][:])==[82,0,20]).all(axis=1))[0])
   core=list(m.REQUIRED) if typ=='primary' else m.CORE
   extra=[k for k in a.variables if k not in core and k in b.variables and a[k].dimensions and a[k].dimensions[0]=='time' and a[k].ndim>=3 and a[k].dtype.kind in 'fi']
   for k in core+extra:rows.append({'type':typ,**compare_fields(a,b,k,ia,ib,k in core)})
 with Dataset(S/'continuous/primary.nc') as a,Dataset(S/'segment/primary.nc') as b:
  for k in m.REQUIRED:prefix.append(compare_fields(a,b,k,1,1,True))
 writecsv('pre_split_prefix.csv',prefix);writecsv('endpoint_variables.csv',rows)
 copy_ok=True
 with Dataset(S/'segment/primary.nc') as a,Dataset(S/'resumed/primary.nc') as b:
  for k in m.REQUIRED:
   x,mx=m.fields(a,k,1);y,my=m.fields(b,k,1);copy_ok&=np.array_equal(x,y,equal_nan=True) and np.array_equal(mx,my)
 assert copy_ok
 driver=m.GpiDriver(m.GPI);ds=[]
 for stage in ['continuous','segment','resumed']:
  for typ in ['primary','secondary']:
   with Dataset(S/stage/f'{typ}.nc') as n:
    for i,t in enumerate(n['mtime'][:]):
     exp=driver.at(2021000+int(t[0]),int(t[1])*3600+int(t[2])*60);err=max(abs(float(n[k][i])-v) for k,v in exp.items());assert err<1e-10;ds.append({'stage':stage,'type':typ,'mtime':t.tolist(),'maximum_absolute_driver_error':err})
 gate={'RESTART_RECOVERY_READY':'PASS' if all(r['passed'] for r in rows) else 'FAIL','INSTRUMENTATION_INVARIANCE_READY':'PARTIAL','STEPWISE_BUDGET_READY':'PARTIAL','SCIENTIFIC_TRAINING_READY':'FAIL','status_interpretation':{'PARTIAL':'static design exists; dependent numerical experiment NOT_EXECUTED; not a partial physical PASS','SCIENTIFIC_TRAINING_READY':'data-release requirements not met, not a failed actual training run'},'prefix_bitwise_fields':sum(r['bitwise_values_and_masks'] for r in prefix),'prefix_numeric_PASS':all(r['passed'] for r in prefix),'prefix_max_normalized_error':max(r['max_normalized_error'] for r in prefix),'failed_core_primary':[r['variable'] for r in rows if r['type']=='primary' and r['core'] and not r['passed']],'failed_core_secondary':[r['variable'] for r in rows if r['type']=='secondary' and r['core'] and not r['passed']],'supplementary_exact_failures':[r['variable'] for r in rows if not r['core'] and not r['passed']],'initial_appended_34_states_unchanged':bool(copy_ok),'internal_magnetic_arrays_directly_compared':False,'unobserved_internal_state':['phim3d','ephi3d','elam3d','emz3d'],'new_launches':3,'stage2_launches':0,'stage3_launches':0,'drivers':ds,'file_hashes':ledger,'rows':rows}
 m.save(O/'comparison.json',gate)
 m.save(O/'analysis_incident.json',{'original_script_SHA256':m.sha(R/'scripts/run_tiegcm_runtime_restart_audit.py'),'original_log_SHA256':m.sha(R/'logs/tiegcm_runtime_restart_audit_v1_suite.log'),'original_failure':'offline comparison asserted bitwise prefix despite inherited numerical tolerance; no model failure','resolution':'preserve bitwise=False and quantify prefix under frozen numeric tolerance in separate offline script','model_reruns':0,'physical_tolerance_changes':False,'overall_result':'FAIL; no dependence stages launched'})
 protected=json.loads((S/'protected_files.json').read_text());changed=[p for p,h in protected.items() if m.sha(R/p)!=h];assert not changed,changed
 statuses={g:json.loads((S/g/'run_status.json').read_text()) for g in ['continuous','segment','resumed']}
 m.save(O/'integrity_and_resources.json',{'protected_files_verified':len(protected),'changed':changed,'run_statuses':statuses,'model_wall_sum_s':sum(s['wall_s'] for s in statuses.values()),'new_model_output_bytes':sum(p.stat().st_size for p in S.glob('*/*.nc')),'no_original_data_overwritten':True,'no_remote_sync':True})
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,axs=plt.subplots(1,3,figsize=(15,4))
 for ax,k in zip(axs,['TN','O1','POTEN']):
  with Dataset(S/'continuous/primary.nc') as a,Dataset(S/'resumed/primary.nc') as b:
   x,mask=m.fields(a,k,2);y,mb=m.fields(b,k,2);z=np.where(mask|mb,np.nan,abs(y-x));valid=np.isfinite(z).any(axis=2);out=np.zeros(z.shape[:2]);out[valid]=np.nanmax(z[valid],axis=1);out[~valid]=np.nan
   im=ax.imshow(out,origin='lower',aspect='auto',extent=[-90,90,0,28]);ax.set(title=k+' max(abs(delta)) over longitude',xlabel='Latitude',ylabel='Native index');fig.colorbar(im,ax=ax)
 fig.tight_layout();fig.savefig(O/'restart_endpoint_difference.png',dpi=150);plt.close(fig)
 print(json.dumps({k:v for k,v in gate.items() if k not in ['rows','drivers','file_hashes']},indent=2))
if __name__=='__main__':main()
