"""One new 2021 20min versus 10+10min native-restart qualification suite.

No source patches, instrumentation, long integrations, or remote Git operations.
Each independent run is one-shot. Failure stops dependent stages.
"""
from pathlib import Path
import sys,os,re,json,hashlib,csv,time,subprocess,signal,resource,socket,getpass,shutil,datetime
import numpy as np
from netCDF4 import Dataset,num2date
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from atmosphere.restart_validation import REQUIRED,inspect_restart,compare_arrays
from atmosphere.tiegcm_drivers import GpiDriver
BASE=R/'experiments/tiegcm_2021_spinup_14day_v1'
EXE=R/'experiments/tiegcm2_apex2023_v1/tiegcm2.0'
SUITE=R/'experiments/tiegcm_runtime_restart_audit_v1'
OUT=R/'results/tiegcm_runtime_restart_audit_v1'
SEED=BASE/'A14/primary_015.nc'
GPI=R/'data/processed/tiegcm_2021_spinup_14day_v1/gpi_2021_14day.nc'
UNIT={'K':(1.,1e-8),'cm/s':(.01,1e-8),'cm':(.01,1e-5),'mmr':(1.,1e-12),'MMR':(1.,1e-12),'cm-3':(1e6,1e-6),'s-1':(1.,1e-14),'volts':(1.,1e-8),'g/cm3':(1000.,1e-25)}
CORE=['DEN','ZG','TN','UN','VN','O1','O2','N2','HE']
def inside(p):
 p=Path(p);assert p.resolve().is_relative_to(R);return p

def sha(p):
 h=hashlib.sha256()
 with inside(p).open('rb') as f:
  for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
 return h.hexdigest()

def save(p,x):
 with inside(p).open('x') as f:json.dump(x,f,indent=2);f.write('\n')

def config(stage):
 text=(BASE/'A14/input.inp').read_text()
 vals={'LABEL':"'2021 runtime restart qualification; not training data'",'START_DAY':'82','START':'82 0 0','STOP':'82 0 '+('10' if stage=='segment' else '20'),'SOURCE':f"'{SEED}'",'SOURCE_START':'82 0 0','HIST':'0 0 10','OUTPUT':"'primary.nc'",'MXHIST_PRIM':'3','SECSTART':'82 0 10','SECSTOP':'82 0 '+('10' if stage=='segment' else '20'),'SECHIST':'0 0 10','SECOUT':"'secondary.nc'",'MXHIST_SECH':'2'}
 if stage=='resumed':
  text=re.sub(r'(?m)^\s*SOURCE(?:_START)?\s*=.*\n','',text);vals.pop('SOURCE');vals.pop('SOURCE_START');vals['START']='82 0 10';vals['SECSTART']='82 0 20'
 for k,v in vals.items():
  text,n=re.subn(rf'(?m)^\s*{k}\s*=.*$',f' {k} = {v}',text);assert n==1,k
 assert not re.search(r'(?im)^\s*(F107|F107A|KP|POWER|CTPOTEN)(?:_TIME)?\s*=',text)
 return text

def rss(pid):
 table={}
 for f in Path('/proc').glob('[0-9]*/stat'):
  try:
   t=f.read_text().rsplit(')',1)[1].split();table[int(f.parent.name)]=(int(t[1]),int(t[2]),int(t[21])*os.sysconf('SC_PAGE_SIZE'))
  except (OSError,ValueError,IndexError):pass
 ids={pid}
 while True:
  q={p for p,(parent,group,_) in table.items() if parent in ids or group==pid}
  if q.issubset(ids):break
  ids|=q
 return sum(table[p][2] for p in ids if p in table)

def limits():
 resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_CPU,(60,60));resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3));resource.setrlimit(resource.RLIMIT_FSIZE,(256*1024**2,256*1024**2))

def fields(n,k,i):
 v=n[k];v.set_auto_mask(False);a=np.asarray(v[i]);mask=abs(a)>1e30
 for name in ['missing_value','_FillValue']:
  if name in v.ncattrs():mask|=a==np.asarray(v.getncattr(name),dtype=v.dtype)
 return a,mask

def prepare():
 assert not SUITE.exists() and not OUT.exists();inside(SUITE);inside(OUT)
 assert inspect_restart(SEED,[82,0,0])['structure_complete'];assert shutil.disk_usage(R).free>20*1024**3
 pre=json.loads((BASE/'A14/preflight.json').read_text());assert sha(EXE)==pre['executable_sha256'];assert sha(GPI)==pre['gpi_sha256']
 build=EXE.parent;assert (build/'Make.env').read_text().find('DIRS = . '+str(R/'third_party/TIEGCM2.0/src'))>=0
 protected={}
 # Preserve all prior tracked scientific work and original source; raw focal assets separately.
 tracked=subprocess.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0')
 for k in filter(None,tracked):
  if k not in ['STATUS.md','WORKLOG.md','.gitignore'] and (R/k).is_file():protected[k]=sha(R/k)
 for p in (R/'third_party/TIEGCM2.0/src').glob('*'):
  if p.is_file():protected[str(p.relative_to(R))]=sha(p)
 for g in ['A14','B14']:
  for p in (BASE/g).glob('*.nc'):protected[str(p.relative_to(R))]=sha(p)
 old=json.loads((BASE/'A14/protected_files.json').read_text())
 for k,v in old.items():
  if 'candidates_202' in k and k.endswith('.npz'):assert sha(R/k)==v;protected[k]=v
 for p in [EXE,GPI,build/'apex.F90',build/'Make.env',build/'Make.workspace']:protected[str(p.relative_to(R))]=sha(p)
 SUITE.mkdir();OUT.mkdir()
 save(SUITE/'protected_files.json',protected)
 proto={'tag':SUITE.name,'year':2021,'start':[82,0,0],'midpoint':[82,0,10],'stop':[82,0,20],'max_launches':3,'stage_model_steps':{'continuous':20,'segment':10,'resumed':10},'MPI':4,'OMP':1,'step_s':60,'wall_per_launch_s':60,'model_wall_total_s':180,'RSS_limit_GiB':16,'new_files_limit_MiB':512,'minimum_free_GiB':20,'estimated_model_wall_total_s':10,'estimated_files_MiB':160,'existing_executable_unchanged':True,'rule_source':'experiments/tiegcm2023_continuation_v1/frozen_comparison_rules.json','supplementary_field_rule':'exact equality for all other common numeric physical fields; no invented unit-specific relaxation','on_recovery_failure':'stop stages II and III; no instrumentation build or budget runs','no_remote_sync':True,'base_git_HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()}
 save(SUITE/'protocol.json',proto)
 for stage in ['continuous','segment','resumed']:
  d=SUITE/stage;d.mkdir();(d/'input.inp').write_text(config(stage))
 oldrules=json.loads((R/proto['rule_source']).read_text());save(SUITE/'frozen_comparison_rules.json',oldrules)
 save(SUITE/'preflight.json',{'static_PASS':True,'seed_SHA256':sha(SEED),'exe_SHA256':sha(EXE),'GPI_SHA256':sha(GPI),'apex_SHA256':sha(build/'apex.F90'),'free_disk_bytes':shutil.disk_usage(R).free,'MPI_version':subprocess.check_output(['mpirun','--version'],text=True).splitlines()[0],'compiler_version':subprocess.check_output(['mpifort','--version'],text=True).splitlines()[0],'config_SHA256':{s:sha(SUITE/s/'input.inp') for s in ['continuous','segment','resumed']}})
 print('Prepared bounded 3-launch suite',flush=True)

def run(stage):
 p=SUITE/stage;pre=json.loads((SUITE/'preflight.json').read_text());assert sha(p/'input.inp')==pre['config_SHA256'][stage];assert sha(EXE)==pre['exe_SHA256'] and sha(GPI)==pre['GPI_SHA256']
 assert shutil.disk_usage(R).free>20*1024**3
 if stage=='resumed':
  source=SUITE/'segment/primary.nc';check=inspect_restart(source,[82,0,10]);assert check['structure_complete'] and check['record_available']
  with Dataset(source) as n:
   mt=np.asarray(n['mtime'][:]);assert (mt[:,0]*86400+mt[:,1]*3600+mt[:,2]*60).max()==82*86400+600
  h=sha(source);shutil.copyfile(source,p/'primary.nc');assert sha(p/'primary.nc')==h;save(p/'seed_copy_audit.json',{'source_SHA256':h,'copy_SHA256':sha(p/'primary.nc'),'future_records':False})
 save(p/'launch_once.json',{'stage':stage,'UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'no_retry':True})
 env=dict(os.environ,OMPI_ALLOW_RUN_AS_ROOT='1',OMPI_ALLOW_RUN_AS_ROOT_CONFIRM='1',OMPI_MCA_pml='ob1',OMPI_MCA_btl='self,tcp',OMPI_MCA_osc='rdma',PMIX_MCA_gds='hash',HOST=socket.gethostname(),LOGNAME=getpass.getuser(),OMP_NUM_THREADS='1',CUDA_VISIBLE_DEVICES='')
 started=time.monotonic();peak=0;reason=None;log=R/'logs'/f'tiegcm_runtime_restart_audit_v1_{stage}.log'
 with log.open('x') as f:
  proc=subprocess.Popen(['mpirun','-np','4',str(EXE),'input.inp'],cwd=p,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=limits)
  while proc.poll() is None:
   peak=max(peak,rss(proc.pid));size=sum(x.stat().st_size for x in SUITE.rglob('*') if x.is_file())
   if time.monotonic()-started>60:reason='wall_limit'
   elif peak>16*1024**3:reason='RSS_limit'
   elif size>512*1024**2:reason='output_limit'
   elif shutil.disk_usage(R).free<20*1024**3:reason='free_disk_limit'
   if reason:os.killpg(proc.pid,signal.SIGKILL);break
   time.sleep(.1)
  proc.wait()
 status={'stage':stage,'returncode':proc.returncode,'stop_reason':reason,'wall_s':time.monotonic()-started,'peak_sampled_tree_RSS_bytes':peak,'normal_exit_count':log.read_text().count('NORMAL EXIT'),'file_bytes':sum(x.stat().st_size for x in p.rglob('*') if x.is_file())}
 save(p/'run_status.json',status);print(json.dumps(status),flush=True)
 assert proc.returncode==0 and reason is None and status['normal_exit_count']==4
 statuses=[json.loads(x.read_text()) for x in SUITE.glob('*/run_status.json')];assert sum(x['wall_s'] for x in statuses)<=180

def compare():
 rows=[];fileledger=[]
 for typ in ['primary','secondary']:
  pa=SUITE/'continuous'/f'{typ}.nc';pb=SUITE/'resumed'/f'{typ}.nc'
  fileledger.append({'type':typ,'continuous_SHA256':sha(pa),'resumed_SHA256':sha(pb),'whole_file_identical':sha(pa)==sha(pb)})
  with Dataset(pa) as a,Dataset(pb) as b:
   for n in [a,b]:
    assert np.all(np.asarray(n['year'][:])==2021);assert all(str(v).startswith('2021-03-23') for v in num2date(n['time'][:],n['time'].units))
   for k in ['lon','lat','lev','ilev','mlon','mlat','mlev','imlev']:np.testing.assert_array_equal(a[k][:],b[k][:])
   ia=int(np.flatnonzero((np.asarray(a['mtime'][:])==[82,0,20]).all(axis=1))[0]);ib=int(np.flatnonzero((np.asarray(b['mtime'][:])==[82,0,20]).all(axis=1))[0])
   core=list(REQUIRED) if typ=='primary' else CORE
   additional=[k for k in a.variables if k not in core and k in b.variables and a[k].dimensions and a[k].dimensions[0]=='time' and a[k].ndim>=3 and a[k].dtype.kind in 'fi']
   for k in core+additional:
    va=a[k];vb=b[k];assert va.dimensions==vb.dimensions and va.dtype==vb.dtype and getattr(va,'units',None)==getattr(vb,'units',None)
    x,mx=fields(a,k,ia);y,my=fields(b,k,ib)
    if k in core:
     scale,atol=UNIT[va.units];rtol=1e-10 if va.dtype==np.dtype('float64') else 1e-6
    else:scale=1.;atol=0.;rtol=0.
    metric=compare_arrays(x,y,mx,my,atol=atol,rtol=rtol,scale=scale)
    rows.append({'type':typ,'variable':k,'core':k in core,'native_unit':getattr(va,'units','not supplied'),'scale_to_SI':scale,'atol_SI_or_native':atol,'rtol':rtol,'valid_data_SHA256_equal':hashlib.sha256(x[~mx].tobytes()).hexdigest()==hashlib.sha256(y[~my].tobytes()).hexdigest(),**metric})
 # Prefix of independently executed continuous/segment must be identical before split.
 prefix=[]
 with Dataset(SUITE/'continuous/primary.nc') as a,Dataset(SUITE/'segment/primary.nc') as b:
  for k in REQUIRED:
   x,mx=fields(a,k,1);y,my=fields(b,k,1);prefix.append(np.array_equal(x,y,equal_nan=True) and np.array_equal(mx,my))
 assert all(prefix)
 # Seed current/previous arrays stay intact while the independent OUTPUT copy is appended.
 with Dataset(SUITE/'segment/primary.nc') as a,Dataset(SUITE/'resumed/primary.nc') as b:
  for k in REQUIRED:
   x,mx=fields(a,k,1);y,my=fields(b,k,1);assert np.array_equal(x,y,equal_nan=True) and np.array_equal(mx,my)
 driver=GpiDriver(GPI);drivers=[]
 for stage in ['continuous','segment','resumed']:
  with Dataset(SUITE/stage/'secondary.nc') as n:
   for i,m in enumerate(n['mtime'][:]):
    expected=driver.at(2021000+int(m[0]),int(m[1])*3600+int(m[2])*60);dif=max(abs(float(n[k][i])-v) for k,v in expected.items());assert dif<1e-10;drivers.append({'stage':stage,'mtime':m.tolist(),'max_difference':dif})
 with (OUT/'variable_comparison.csv').open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 result={'RESTART_RECOVERY_READY':'PASS' if all(x['passed'] for x in rows) else 'FAIL','INSTRUMENTATION_INVARIANCE_READY':'PARTIAL','STEPWISE_BUDGET_READY':'PARTIAL','SCIENTIFIC_TRAINING_READY':'FAIL','dependent_stages_executed':False,'core_primary_failed':[x['variable'] for x in rows if x['type']=='primary' and x['core'] and not x['passed']],'core_secondary_failed':[x['variable'] for x in rows if x['type']=='secondary' and x['core'] and not x['passed']],'supplementary_failed':[x['variable'] for x in rows if not x['core'] and not x['passed']],'same_pre_split_34_fields_bitwise':all(prefix),'appended_seed_34_fields_unchanged':True,'file_SHA256':fileledger,'drivers':drivers,'missing_internal_arrays':['phim3d','ephi3d','elam3d','emz3d'],'internal_state_directly_compared':False,'rows':rows}
 save(OUT/'comparison.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['rows','drivers','file_SHA256']}),flush=True)
 # Diagnostic maps from REAL new endpoint differences only.
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,axs=plt.subplots(1,3,figsize=(15,4))
 for ax,k in zip(axs,['TN','O1','POTEN']):
  with Dataset(SUITE/'continuous/primary.nc') as a,Dataset(SUITE/'resumed/primary.nc') as b:
   x,m=fields(a,k,2);y,mb=fields(b,k,2);v=np.where(m|mb,np.nan,abs(y-x));z=np.nanmax(v,axis=2)
   im=ax.imshow(z,origin='lower',aspect='auto',extent=[-90,90,0,28]);ax.set(title=k+' max over longitude abs difference',xlabel='Geographic latitude',ylabel='Native vertical index');fig.colorbar(im,ax=ax)
 fig.tight_layout();fig.savefig(OUT/'restart_endpoint_difference.png',dpi=150);plt.close(fig)
 protected=json.loads((SUITE/'protected_files.json').read_text());changed=[k for k,v in protected.items() if sha(R/k)!=v];assert not changed,changed
 save(OUT/'integrity.json',{'protected_files_verified':len(protected),'changed':changed,'original_results_overwritten':False,'new_model_launches':3,'stage2_model_launches':0,'stage3_model_launches':0})

def main():
 prepare()
 for stage in ['continuous','segment','resumed']:run(stage)
 compare()
if __name__=='__main__':main()
