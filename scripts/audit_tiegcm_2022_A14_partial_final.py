"""Independent verification of actual partial evidence, not engineering promotion."""
from pathlib import Path
import sys,json,csv,time,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from prepare_fourcastden_swarm_observation_v1 import sha,dump
from audit_tiegcm_2021_14day_acceptance import index
from netCDF4 import Dataset
from PIL import Image
TAG='tiegcm_2022_spinup_14day_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG
def read(p):
 with p.open() as f:return list(csv.DictReader(f))
def interp450(path,i):
 with Dataset(path) as n:z=np.asarray(n['ZG'][i],float)*.01;rho=np.asarray(n['DEN'][i],float)*1000;lat=np.array(n['lat'][:])
 out=np.full(z.shape[1:],np.nan)
 for j in range(z.shape[1]):
  for k in range(z.shape[2]):
   v=z[:,j,k];target=450e3
   if not v[0]<=target<=v[-1]:continue
   hi=min(max(int(np.searchsorted(v,target)),1),len(v)-1);lo=hi-1;f=(target-v[lo])/(v[hi]-v[lo]);out[j,k]=np.exp((1-f)*np.log(rho[lo,j,k])+f*np.log(rho[hi,j,k]))
 return out,lat
if __name__=='__main__':
 started=time.perf_counter();p=json.loads((F/'protected_files.json').read_text())
 for name,expected in p.items():assert sha(ROOT/name)==expected,name
 audit=json.loads((F/'A14/data_audit.json').read_text());assert not audit['engineering_PASS'] and audit['data_integrity_PASS'];status=json.loads((F/'A14/run_status.json').read_text());assert status['returncode'] is None and status['normal_exit_count']==4 and not (F/'B14').exists()
 for e in audit['files']:assert sha(F/'A14'/e['file'])==e['SHA256']
 z=np.load(O/'observation_partial/aligned_local.npz');m=z['common'];truth=z['observed'][m];rows=read(O/'observation_partial/metrics.csv');count=0
 for mi,ma in enumerate('ABDE'):
  for gi,g in enumerate(['A7','B7','A14']):
   x=z['values'][mi,gi,m];d=x-truth;r=next(r for r in rows if r['mapping']==ma and r['group']==g and r['region']=='all');expected=dict(MAE=np.mean(abs(d)),RMSE=np.sqrt(np.mean(d*d)),bias=np.mean(d),relative_RMS=np.sqrt(np.mean((d/truth)**2)),relative_bias=np.mean(d/truth),Pearson=np.corrcoef(x,truth)[0,1]);assert int(r['n'])==len(truth)
   for key,value in expected.items():np.testing.assert_allclose(float(r[key]),value,rtol=2e-12,atol=1e-25)
   count+=1
 ix=index(ROOT/'experiments/tiegcm_training_mar23_v2_2022_longrun');iy=index(F/'A14');x=[];y=[]
 for t in range(82*86400,84*86400+1,3600):
  a,lat=interp450(*ix[t]);b,_=interp450(*iy[t]);x.append(a);y.append(b)
 x,y=np.stack(x),np.stack(y);good=np.isfinite(x)&np.isfinite(y);w=np.broadcast_to(np.cos(np.deg2rad(lat))[None,:,None],x.shape)[good];d=y[good]-x[good];relative=abs(d/x[good]);order=np.argsort(relative);cdf=np.cumsum(w[order]);cdf/=cdf[-1];p95=np.interp(.95,cdf,relative[order]);r=next(r for r in read(O/'A14_A7/native_ZG_density.csv') if r['height_km']=='450' and r['period']=='candidate' and r['region']=='global')
 np.testing.assert_allclose(float(r['relative_P95']),p95,rtol=1e-10);np.testing.assert_allclose(float(r['RMSE']),np.sqrt(np.average(d*d,weights=w)),rtol=1e-10)
 final=json.loads((F/'partial_finalization.json').read_text())
 for name in final['figures']:
  with Image.open(O/name) as im:im.verify()
 dump(F/'partial_independent_audit.json',dict(PASS=True,qualification='Partial data analysis verified; engineering NOT promoted; dual14 NOT complete',protected_assets=len(p),new_NetCDF_volumes=len(audit['files']),independent_observation_groups=count,common_observations=int(m.sum()),independent_450km_relative_P95=float(p95),figure_count=len(final['figures']),wall_s=time.perf_counter()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
 code=[q for q in (ROOT/'scripts').glob('*2022*14day*.py')]+[q for q in (ROOT/'scripts').glob('*2022_A14_partial*.py')]+[ROOT/'scripts/tiegcm_2022_runtime_guardian.py',ROOT/'scripts/run_tiegcm_2022_B14_guarded.py',ROOT/'tests/test_tiegcm_2022_14day.py']
 dump(F/'source_output_sha.json',dict(code={str(q.relative_to(ROOT)):sha(q) for q in code},outputs={e['file']:e['SHA256'] for e in audit['files']},figures={name:sha(O/name) for name in final['figures']}))
 print('Independent partial evidence PASS; full experiment remains PARTIAL',len(p),count)
