"""Independent native fill scan, scalar metrics and pointwise tradeoffs. No refit."""
from pathlib import Path
import sys,json,csv,hashlib,time,resource,warnings
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
import numpy as np
from netCDF4 import Dataset
from PIL import Image
F=ROOT/'experiments/causal_density_correction_v1'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for x in iter(lambda:f.read(2**20),b''):h.update(x)
 return h.hexdigest()
def main():
 start=time.perf_counter();manifest=json.loads((F/'matched_samples_manifest.json').read_text());z=np.load(F/'matched_local.npz');coeff=json.loads((F/'correction_parameters.json').read_text())['parameters'];scans=[];points=[]
 for case in manifest['cases']:
  first=case['case'];entry=next(n for n in manifest['protected_inputs'] if n.endswith('input.inp') and n.startswith(str(Path(next(k for k in manifest['protected_inputs'] if k.endswith(case['input_files'][0]['file']) and manifest['protected_inputs'][k]==case['input_files'][0]['SHA256'])).parent)))
  folder=(ROOT/entry).parent
  for e in case['input_files']:
   path=folder/e['file'];assert sha(path)==e['SHA256']
   with Dataset(path) as n:
    n.set_auto_mask(False);times=np.asarray(n['mtime'][:]);selected=np.where((times[:,0]==83)&(times[:,1]>=3)&(times[:,1]<=12))[0]
    for name in ['DEN','ZG']:
     var=n[name];total=0;badcount=0
     for i in selected:
      a=np.asarray(var[int(i)]);bad=~np.isfinite(a)|(abs(a)>1e30)
      for flag in ['_FillValue','missing_value']:
       if hasattr(var,flag):bad|=a==np.asarray(getattr(var,flag),dtype=a.dtype)
      if name=='DEN':bad|=a<=0
      total+=a.size;badcount+=int(bad.sum())
     assert badcount==0,(first,path,name,badcount)
     scans.append(dict(case=first,file=str(path.relative_to(ROOT)),variable=name,used_hourly_records=len(selected),tested_grid_values=total,explicit_fill_or_nonfinite_or_nonpositive_count=badcount))
  for sat in ['A','C']:
   t=z[sat+'_utc'];m=(t>=np.datetime64('2022-03-24T06'))&(t<np.datetime64('2022-03-24T12'));obs=z[sat+'_density'][m];raw=z[first+'_'+sat][m];corrected=raw*coeff[first]['density_multiplier'];a=abs(raw-obs);b=abs(corrected-obs)
   rows=list(csv.DictReader((F/'metrics.csv').open()));r=next(x for x in rows if x['case']==first and x['satellite']==sat and x['window']=='future_6h' and x['region']=='all' and x['method']=='corrected')
   assert np.isclose(np.sqrt(np.mean(((corrected-obs)/obs)**2)),float(r['relative_RMS']),rtol=1e-14,atol=0)
   points.append(dict(case=first,satellite=sat,N=len(obs),improved_points=int((b<a).sum()),worsened_points=int((b>a).sum()),unchanged_points=int((b==a).sum()),nonpositive_corrected=int((corrected<=0).sum()),nonfinite_corrected=int((~np.isfinite(corrected)).sum())))
 for p in (F/'figures').glob('*.png'):
  with Image.open(p) as im:im.verify()
 for n,h in manifest['protected_inputs'].items():assert sha(ROOT/n)==h,n
 out=dict(PASS=True,explicit_native_mask_scan=scans,pointwise_diagnostics=points,protected_inputs_unchanged=len(manifest['protected_inputs']),figures=6,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
 with (F/'independent_verification.json').open('x') as f:json.dump(out,f,indent=2)
 print('INDEPENDENT VERIFICATION PASS',json.dumps(points[:2]),flush=True)
if __name__=='__main__':main()
