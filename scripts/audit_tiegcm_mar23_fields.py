"""Read-only native field/author-grid checks; never exports training samples."""
import json,hashlib
from pathlib import Path
import numpy as np
from netCDF4 import Dataset
R=Path(__file__).resolve().parents[1];F=R/'experiments/training_window_mar23_v2'
def main():
 for y in [2021,2022]:
  folder=R/f'experiments/tiegcm_mar23_d{y}_v2';p=next(folder.glob('*sech*.nc'));fields={};grids={}
  with Dataset(p) as n:
   for k in ['TN','UN','VN','WN','Z','DEN','ZG','NE','TLBC','ULBC','VLBC','f107d','f107a','Kp']:
    v=n[k];v.set_auto_mask(False);a=np.asarray(v[:]);assert np.isfinite(a).all(),k
    mask=abs(a)>1e30
    for key in ['missing_value','_FillValue']:
     if key in v.ncattrs():
      for marker in np.asarray(v.getncattr(key)).reshape(-1):mask|=a==np.asarray(marker,dtype=a.dtype)
    valid=a[~mask];assert valid.size,k
    if k in ['TN','UN','VN']:assert not mask[:,:-1].any() and mask[:,-1].all()
    else:assert not mask.any(),k
    fields[k]={'shape':list(a.shape),'dimensions':list(v.dimensions),'unit':getattr(v,'units',None),'masked':int(mask.sum()),'min_valid':float(valid.min()),'max_valid':float(valid.max())}
   assert n['DEN'].units=='g/cm3' and (n['DEN'][:]>0).all()
   assert n['Z'].units==n['ZG'].units=='cm' and (np.diff(n['ZG'][:],axis=1)>0).all()
   for k in ['lat','lon','lev','ilev']:
    author=np.load(R/f'data/processed/static/{k}.npy');np.testing.assert_array_equal(n[k][:],author)
    grids[k]={'author_exact':True,'shape':list(author.shape),'author_SHA256':hashlib.sha256((R/f'data/processed/static/{k}.npy').read_bytes()).hexdigest()}
  out=F/f'fields_{y}.json'
  with out.open('x') as f:json.dump({'status':'PASS','year':y,'fields':fields,'coordinates':grids,'training_samples_generated':0,'all_records_NOT_TRAINING_DATA':True},f,indent=2)
if __name__=='__main__':main()
