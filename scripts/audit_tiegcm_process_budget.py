"""Read-only prerequisite audit and observed net-change tables; never launches MPI."""
from pathlib import Path
import sys,json,csv,hashlib,time,resource,re
import numpy as np
from netCDF4 import Dataset,num2date
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from atmosphere.restart_validation import inspect_restart,REQUIRED
from atmosphere.tiegcm_process_budget import TERMS,require_ready
OUT=R/'results/tiegcm_2021_process_budget_v1'
ROOT=R/'experiments/tiegcm_2021_spinup_14day_v1'
INTERNAL=['PHIM3D','EPHI3D','ELAM3D','EMZ3D']
PROCESS_FIELDS=['POX1','POX2','LOX1','LOX2','LOX3','PO21','PO23','LO21','LO22','FS','HDO1','HDO2','HDHE','O1_ADVEC','O2_ADVEC','PK','QK','RK','AK','EP']
REGIONS={'global':(-90,90),'south_polar':(-90,-60),'south_mid':(-60,-30),'tropics':(-30,30),'north_mid':(30,60),'north_polar':(60,90)}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def csvout(name,rows):
 with (OUT/name).open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def field(v,i):
 v.set_auto_mask(False);x=np.asarray(v[i],float);assert np.isfinite(x).all();mask=abs(x)>1e30
 for k in ['_FillValue','missing_value']:
  if k in v.ncattrs():mask|=x==np.asarray(v.getncattr(k),dtype=v.dtype)
 x[mask]=np.nan;return x

def main():
 started=time.monotonic();assert OUT.resolve().is_relative_to(R);OUT.mkdir(exist_ok=False)
 ledger={};audit={'new_model_launches':0,'groups':{},'decision':'BLOCKED_RUNTIME_RESTORE_AND_PROCESS_CAPTURE','closure_status':'NOT_EVALUABLE','science_training_ready':False};raw={};dates={};grids={}
 for group in ['A14','B14']:
  p=ROOT/group/'primary_015.nc';ledger[str(p.relative_to(R))]=sha(p);info=inspect_restart(p,[82,0,0]);assert info['structure_complete'] and info['record_available']
  with Dataset(p) as n:
   assert int(n['year'][0])==2021;assert tuple(n['mtime'][0])==(82,0,0)
   info['missing_runtime_arrays']=[k for k in INTERNAL if k not in {s.upper() for s in n.variables}]
   info['present_geometry_arrays']=[k for k in ['e1','e2','h1','h2','alfac'] if k in n.variables]
   info['grid']={k:np.asarray(n[k][:]).tolist() for k in ['lat','lon','lev','ilev','mlat','mlon','mlev','imlev']}
   info['required_schema']={k:{'dimensions':n[k].dimensions,'dtype':str(n[k].dtype),'units':n[k].units} for k in REQUIRED}
   for k in REQUIRED:
    q=field(n[k],0);assert np.isfinite(q).any()
   info['time_UTC']=str(num2date(n['time'][0],n['time'].units));info['iter']=int(n['iter'][0]);info['timestep_s']=int(n['timestep'][0]);assert info['timestep_s']==60
  ti={}
  for p in sorted((ROOT/group).glob('secondary_*.nc')):
   with Dataset(p) as n:
    for i,m in enumerate(n['mtime'][:]):
     t=int(m[0])*86400+int(m[1])*3600
     if 82*86400<=t<=82*86400+6*3600:ti[t]=(p,i)
  assert len(ti)==7
  raw[group]=[];dates[group]=[];d=[]
  for t,(p,i) in sorted(ti.items()):
   ledger[str(p.relative_to(R))]=sha(p)
   with Dataset(p) as n:
    z={k:field(n[k],i) for k in ['O1','O2','N2','HE','ZG']};raw[group].append(z)
    date=num2date(n['time'][i],n['time'].units);assert date.year==2021 and date.month==3 and date.day==23
    assert int(date.strftime('%j'))*86400+date.hour*3600==t;dates[group].append(str(date))
    grid={k:np.array(n[k][:]) for k in ['lat','lon','lev','ilev']}
    if group in grids:
     for k in grid:np.testing.assert_array_equal(grid[k],grids[group][k])
    grids[group]=grid
    d.append([float(n[k][i]) for k in ['f107d','f107a','Kp','hpower','ctpoten']])
    info['missing_process_fields']=[k for k in PROCESS_FIELDS if k not in {s.upper() for s in n.variables}]
  info['drivers']=d;audit['groups'][group]=info
 assert dates['A14']==dates['B14']
 assert audit['groups']['A14']['required_schema']==audit['groups']['B14']['required_schema']
 assert audit['groups']['A14']['grid']==audit['groups']['B14']['grid']
 for k in grids['A14']:np.testing.assert_array_equal(grids['A14'][k],grids['B14'][k])
 np.testing.assert_array_equal(audit['groups']['A14']['drivers'],audit['groups']['B14']['drivers']);audit['driver_max_AB_difference']=0
 ta=(ROOT/'A14/input.inp').read_text();tb=(ROOT/'B14/input.inp').read_text();strip=lambda s:'\n'.join(l for l in s.splitlines() if not re.match(r'^\s*SOURCE\s*=',l));assert strip(ta)==strip(tb);audit['original_namelists_same_except_source']=True
 # The inherited prior failure is evidence against assuming restoration, NOT a new 2021 test.
 audit['inherited_restart_evidence']='reports/TIEGCM2023_CONTINUATION_VALIDATION.md: 28/34 primary and 9/9 secondary failed frozen prefix tolerances'
 try:require_ready(structure_complete=True,runtime_restore_verified=False,process_capture_verified=False,closure_protocol_qualified=False)
 except ValueError as e:audit['launch_gate_reason']=str(e)
 else:raise AssertionError('Unsafe launch gate')
 rows=[];closure=[];lat=grids['A14']['lat'];lev=grids['A14']['lev'];ilev=grids['A14']['ilev']
 for group in raw:
  q0=raw[group][0]
  for hour,q in enumerate(raw[group]):
   # Algebraic diagnostic identity; explicitly not a physical process budget.
   dq={v:q[v]-q0[v] for v in ['O1','O2','HE','N2']};r=sum(dq.values());closure.append(dict(group=group,hour=hour,status='ALGEBRAIC_N2_IDENTITY_ONLY',max_absolute_residual=float(np.nanmax(abs(r))),RMS=float(np.sqrt(np.nanmean(r*r))),physical_budget_status='NOT_EVALUABLE'))
   for v in ['O1','O2','N2']:
    for reg,(lo,hi) in REGIONS.items():
     sel=(lat>=lo)&(lat<=hi)
     for l in range(29):
      x=q[v][l,sel];d=dq[v][l,sel];assert np.isfinite(x).all()
      z=None
      if ilev[0]<=lev[l]<=ilev[-1]:
       j=min(np.searchsorted(ilev,lev[l],side='right')-1,27);f=(lev[l]-ilev[j])/(ilev[j+1]-ilev[j]);z=float(np.median(((1-f)*q['ZG'][j,sel]+f*q['ZG'][j+1,sel])*1e-5))
      rows.append(dict(group=group,hour=hour,UTC=dates[group][hour],variable=v,level=l,region=reg,n=x.size,mean_q=float(x.mean()),net_delta_mean=float(d.mean()),net_delta_RMS=float(np.sqrt(np.mean(d*d))),median_ZG_mid_km=z,unit='mmr',status='OBSERVED_NET_CHANGE_NOT_PROCESS_ATTRIBUTION'))
 csvout('observed_net_change.csv',rows);csvout('N2_algebraic_identity.csv',closure)
 unavailable=[dict(group=g,variable=v,term=t,cumulative_delta_mmr=None,status='NOT_OBSERVED_IN_EXISTING_OUTPUT',reason='runtime restoration unverified; no process instrumentation data') for g in raw for v in ['O1','O2','N2'] for t in TERMS]
 csvout('process_budget_status.csv',unavailable)
 csvout('budget_closure_status.csv',[dict(group=g,variable=v,delta_source='existing continuous trajectory',sum_process_delta=None,residual_R=None,status='NOT_EVALUABLE',passed=False) for g in raw for v in ['O1','O2','N2']])
 pair=[]
 for h in range(7):
  for v in ['O1','O2','N2']:
   for l in range(29):
    for reg,(lo,hi) in REGIONS.items():
     m=(lat>=lo)&(lat<=hi);a=raw['A14'][h][v][l,m];b=raw['B14'][h][v][l,m]
     pair.append(dict(hour=h,variable=v,level=l,region=reg,AB_bias=float((b-a).mean()),AB_RMS=float(np.sqrt(np.mean((b-a)**2))),unit='mmr'))
 csvout('AB_observed_difference.csv',pair)
 for v in ['O1','O2','N2']:
  fig,axs=plt.subplots(1,2,figsize=(12,4))
  for group in raw:
   q=[r for r in rows if r['group']==group and r['variable']==v and r['region']=='global']
   axs[0].plot(range(7),[np.mean([r['mean_q'] for r in q if r['hour']==h]) for h in range(7)],label=group)
   axs[1].plot(range(7),[np.sqrt(np.mean([r['net_delta_RMS']**2 for r in q if r['hour']==h])) for h in range(7)],label=group)
  axs[0].set_title(v+' native-level mean state (not mass weighted)');axs[1].set_title('Observed cumulative change RMS; no process attribution')
  for ax in axs:ax.set_xlabel('Hours after 2021-03-23 00 UTC');ax.set_ylabel('mass mixing ratio');ax.legend()
  fig.tight_layout();fig.savefig(OUT/f'{v}_observed_change.png',dpi=150);plt.close(fig)
 fig,axs=plt.subplots(1,3,figsize=(13,4))
 for ax,v in zip(axs,['O1','O2','N2']):
  for g in raw:
   for reg in ['south_polar','tropics','north_polar']:
    q=[r for r in rows if r['group']==g and r['variable']==v and r['region']==reg and r['hour']==6]
    ax.plot([r['net_delta_RMS'] for r in q],range(29),label=g+' '+reg)
  ax.set(title=v+' +6h net-change RMS',xlabel='mmr',ylabel='native midpoint index');ax.legend(fontsize=6)
 fig.tight_layout();fig.savefig(OUT/'net_change_region_level.png',dpi=150);plt.close(fig)
 fig,ax=plt.subplots(figsize=(8,4))
 for g in raw:
  z=[r for r in closure if r['group']==g];ax.plot([r['hour'] for r in z],[r['max_absolute_residual'] for r in z],label=g)
 ax.set(title='N2 algebraic identity residual ONLY (not process closure)',xlabel='Hour',ylabel='mmr');ax.legend();fig.tight_layout();fig.savefig(OUT/'N2_algebraic_identity.png',dpi=150);plt.close(fig)
 # Match primary/source data to previously audited identities; never change original files.
 prev=json.loads((ROOT/'delivery_audit.json').read_text())['outputs'];known={(r['group'],r['file']):r['SHA256'] for r in prev}
 for rel,h in ledger.items():
  p=R/rel;assert sha(p)==h;assert known[(p.parent.name,p.name)]==h
 for name in ['comp.F','comp_o2o.F','lbc.F','cons.F','smooth.F','hdif.F','dynamics.F','advance.F','pdynamo.F','rdsource.F','nchist.F','fields.F','addiag.F','diags.F','input.F']:
  p=R/'third_party/TIEGCM2.0/src'/name;ledger[str(p.relative_to(R))]=sha(p)
 audit['inputs_SHA256']=ledger;audit['wall_seconds']=time.monotonic()-started;audit['python_peak_RSS_MiB']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024
 audit['budget_qualified']=False;audit['original_candidates_modified']=False;audit['planned_window_UTC']=['2021-03-23T00:00:00Z','2021-03-23T06:00:00Z'];audit['process_fields_read']=0
 (OUT/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps({k:v for k,v in audit.items() if k not in ['groups','inputs_SHA256']},indent=2))
if __name__=='__main__':main()
