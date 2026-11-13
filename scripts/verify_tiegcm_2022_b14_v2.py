"""Independent v2 numerical/asset checks after successful B14 engineering."""
from pathlib import Path
import sys,json,csv,time,resource
import numpy as np
from netCDF4 import Dataset
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_tiegcm_2022_b14_v2 import F,O,B,A,dump
from run_tiegcm_mar23_2021_longrun import stream_sha
from audit_tiegcm_2021_14day_acceptance import index

def rows(p):
 with p.open() as f:return list(csv.DictReader(f))
def manual450(path,i):
 with Dataset(path) as n:z=np.asarray(n['ZG'][i],float)*.01;r=np.asarray(n['DEN'][i],float)*1000;lat=np.array(n['lat'][:])
 result=np.full(z.shape[1:],np.nan)
 for j in range(z.shape[1]):
  for k in range(z.shape[2]):
   levels=z[:,j,k]
   if not levels[0]<=450e3<=levels[-1]:continue
   hi=min(max(int(np.searchsorted(levels,450e3)),1),len(levels)-1);lo=hi-1;f=(450e3-levels[lo])/(levels[hi]-levels[lo]);result[j,k]=np.exp((1-f)*np.log(r[lo,j,k])+f*np.log(r[hi,j,k]))
 return result,lat
if __name__=='__main__':
 start=time.perf_counter();assert json.loads((F/'B14_engineering_gate.json').read_text())['PASS'];old=json.loads((A/'run_status.json').read_text());assert old['returncode'] is None and not json.loads((A/'data_audit.json').read_text())['engineering_PASS']
 protected=json.loads((F/'protected_files.json').read_text())
 for name,expected in protected.items():assert stream_sha(ROOT/name)==expected,name
 audit=json.loads((B/'data_audit.json').read_text())
 for e in audit['files']:assert stream_sha(B/e['file'])==e['SHA256']
 z=np.load(O/'observation/aligned_local.npz');mask=z['common'];truth=z['observed'][mask];metrics=rows(O/'observation/metrics.csv');count=0
 for mi,ma in enumerate('ABDE'):
  for gi,group in enumerate(['A7','B7','A14','B14']):
   x=z['values'][mi,gi,mask];d=x-truth;row=next(r for r in metrics if r['mapping']==ma and r['group']==group and r['region']=='all');assert int(row['n'])==int(mask.sum())
   expected=dict(MAE=np.mean(abs(d)),RMSE=np.sqrt(np.mean(d*d)),bias=np.mean(d),relative_RMS=np.sqrt(np.mean((d/truth)**2)),relative_bias=np.mean(d/truth),Pearson=np.corrcoef(x,truth)[0,1])
   for key,value in expected.items():np.testing.assert_allclose(float(row[key]),value,rtol=2e-12,atol=1e-25)
   count+=1
 ix,iy=index(A),index(B);xx=[];yy=[]
 for t in range(82*86400,84*86400+1,3600):
  x,lat=manual450(*ix[t]);y,_=manual450(*iy[t]);xx.append(x);yy.append(y)
 x,y=np.stack(xx),np.stack(yy);valid=np.isfinite(x)&np.isfinite(y);w=np.broadcast_to(np.cos(np.deg2rad(lat))[None,:,None],x.shape)[valid];d=y[valid]-x[valid];rel=abs(d/x[valid]);order=np.argsort(rel);cdf=np.cumsum(w[order]);cdf/=cdf[-1];p95=np.interp(.95,cdf,rel[order]);rr=next(r for r in rows(O/'delta14/native_ZG_density.csv') if r['height_km']=='450' and r['period']=='candidate' and r['region']=='global');np.testing.assert_allclose(float(rr['relative_P95']),p95,rtol=1e-10);np.testing.assert_allclose(float(rr['RMSE']),np.sqrt(np.average(d*d,weights=w)),rtol=1e-10)
 matrix=rows(O/'delta14/acceptance_region_level_matrix.csv');summary=json.loads((O/'delta14/summary.json').read_text())
 for period,variables in summary['gates'].items():
  for variable,g in variables.items():assert sum(int(r['failed_hours']) for r in matrix if r['period']==period and r['variable']==variable)==g['failed_cells']
 final=json.loads((F/'finalization.json').read_text())
 for name in final['figures']:
  with Image.open(O/name) as image:image.verify()
 allbytes=sum(p.stat().st_size for base in [F,O] for p in base.rglob('*') if p.is_file());p=json.loads((F/'protocol.json').read_text());old_reserve=max(p['existing_A14_bytes'],old['total_generated_bytes']);assert allbytes+old_reserve<12*2**30
 dump(F/'independent_verification.json',dict(PASS=True,A14_engineering='PARTIAL',B14_engineering='PASS',v1_engineering_not_promoted=True,protected_assets=len(protected),new_NetCDF_volumes=len(audit['files']),observation_metric_groups=count,common_observations=int(mask.sum()),independent_450km_P95_pct=float(p95*100),gate_count_reconciliation=True,figure_count=len(final['figures']),combined_A14_v2_bytes=allbytes+old_reserve,combined_definition='max(frozen A14 directory bytes, previous A14 run+log bytes) + all new v2 experiments and results',wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,science_training_ready=False))
 files=list((ROOT/'scripts').glob('*tiegcm_2022_b14_v2.py'))+[ROOT/'src/runtime/supervisor.py',ROOT/'tests/test_runtime_supervisor.py']
 dump(F/'code_output_sha.json',dict(code={str(p.relative_to(ROOT)):stream_sha(p) for p in files},outputs={e['file']:e['SHA256'] for e in audit['files']},figures={name:stream_sha(O/name) for name in final['figures']}))
 print('V2 independent verification PASS',p95*100,count,len(protected))
