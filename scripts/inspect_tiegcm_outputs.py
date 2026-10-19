"""Inspect native TIE-GCM histories, explicitly masking typed missing values.

No interpolation, forecast validation, or assumptions that pressure is altitude.
"""
from pathlib import Path
import argparse,json,warnings
import numpy as np
from netCDF4 import Dataset,num2date
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('run_tag');args=p.parse_args()
if not args.run_tag or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in args.run_tag):raise ValueError('Bad tag')
folder=ROOT/'experiments'/args.run_tag;assert folder.resolve().is_relative_to(ROOT)
records=[]
for path in sorted(folder.glob('*.nc')):
 with Dataset(path) as ds:
  row={'file':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'fields':{}}
  for name in ['time','year','mtime','lev','ilev','lat','lon','DEN','ZG','Z','TN','UN','VN']:
   if name not in ds.variables:continue
   v=ds[name];v.set_auto_mask(False);raw=np.asarray(v[:]);mask=~np.isfinite(raw)
   for attr in ['_FillValue','missing_value']:
    if attr in v.ncattrs():
     for marker in np.asarray(v.getncattr(attr)).reshape(-1):
      # Secondary float32 marker may be stored as float64 metadata; netCDF4
      # warns/declines automatic masking. Cast to variable type deliberately.
      mask|=(raw==np.asarray(marker,dtype=raw.dtype))
   if raw.dtype.kind=='f':mask|=(abs(raw)>1e30)
   valid=np.ma.array(raw,mask=mask)
   info={'units':getattr(v,'units',None),'dimensions':list(v.dimensions),'shape':list(v.shape),'masked':int(mask.sum()),'min_valid':float(valid.min()),'max_valid':float(valid.max())}
   if name=='time':info['dates']=[str(x) for x in num2date(valid,v.units)]
   if name=='DEN':
    if v.units!='g/cm3' or v.dimensions!=('time','ilev','lat','lon'):raise ValueError('Unexpected native DEN definition')
    if np.any(valid<=0):raise ValueError('Nonpositive native density')
    info['si_min_kg_m3']=float(valid.min()*1000);info['si_max_kg_m3']=float(valid.max()*1000)
   if name=='ZG':
    if v.units!='cm':raise ValueError('Unknown ZG unit')
    if np.any(np.diff(valid,axis=1)<=0):raise ValueError('Nonmonotonic geometric height')
    info['top_height_km_range']=[float(valid[:,-1].min()/1e5),float(valid[:,-1].max()/1e5)]
   row['fields'][name]=info
  if 'DEN' in ds.variables:
   assert ds['DEN'].dimensions==ds['ZG'].dimensions
  records.append(row)
if not records:raise ValueError('No history files')
output=ROOT/'logs'/f'{args.run_tag}_netcdf_audit.json'
with output.open('x') as f:json.dump(records,f,indent=2)
print('Audited',len(records),'files ->',output)
