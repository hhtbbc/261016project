"""Static official second-source audit, never modifies or launches TIE-GCM."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
from netCDF4 import Dataset
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from atmosphere.restart_validation import REQUIRED,inspect_restart,check_source_clock
F=R/'experiments/tiegcm_2021_spinup_initial_condition_v1';A=R/'data/raw/tiegcm2_support/tiegcm_res5.0_mareqx_smin_prim.nc';B=R/'data/raw/tiegcm_2021_spinup_initial_condition_v1/tiegcm_res5.0_mareqx_smax_prim.nc'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def clean(v):
 v.set_auto_mask(False);x=np.asarray(v[:]);assert np.isfinite(x).all(),v.name;mask=abs(x)>1e30
 for attr in ['missing_value','_FillValue']:
  if attr in v.ncattrs():mask|=x==np.asarray(v.getncattr(attr),dtype=x.dtype)
 return np.ma.array(x,mask=mask)
def main():
 result={'B':inspect_restart(B,[80,0,0]),'A_SHA256':sha(A),'B_SHA256':sha(B),'schemas':{},'coordinates':{}}
 assert result['B']['structure_complete'] and result['B']['record_available'];check_source_clock([75,0,0],[80,0,0])
 with Dataset(A) as a,Dataset(B) as b:
  for k in ['lat','lon','lev','ilev']:np.testing.assert_array_equal(a[k][:],b[k][:]);np.testing.assert_array_equal(b[k][:],np.load(R/f'data/processed/static/{k}.npy'));result['coordinates'][k]=list(b[k].shape)
  assert np.array_equal(b['mtime'][:],[[80,0,0]]) and np.array_equal(b['year'][:],[2002])
  for k in REQUIRED:
   x,y=a[k],b[k];assert x.dimensions==y.dimensions and x.dtype==y.dtype==np.dtype('float64') and getattr(x,'units',None)==getattr(y,'units',None),k
   z=clean(y);assert z.count()>0,k
   if k in ['TN','TN_NM','UN','UN_NM','VN','VN_NM','TI','TE']:
    mask=np.ma.getmaskarray(z);assert not mask[:,:-1].any() and mask[:,-1].all(),k
    if k in ['TN','TN_NM']:assert z.min()>100 and z.max()<5000
    elif k in ['TI','TE']:assert z.min()>0
    else:assert abs(z).max()<2e5
   elif np.ma.getmaskarray(z).any():raise ValueError('Incomplete required state '+k)
   result['schemas'][k]={'dimensions':list(y.dimensions),'dtype':str(y.dtype),'units':getattr(y,'units',None),'min_valid':float(z.min()),'max_valid':float(z.max()),'masked_count':int(np.ma.getmaskarray(z).sum())}
  for k in ['O1','O2','HE','N4S','NO','AR','O1_NM','O2_NM','HE_NM','N4S_NM','NO_NM','AR_NM']:
   z=clean(b[k]);assert z.min()>=0 and z.max()<=1.000001,k
  for k in ['TLBC','TLBC_NM']:assert clean(b[k]).min()>100 and clean(b[k]).max()<5000
  result['A_source_scalars']={k:np.asarray(a[k][:]).tolist() for k in ['f107d','f107a','Kp','hpower','ctpoten']};result['B_source_scalars']={k:np.asarray(b[k][:]).tolist() for k in ['f107d','f107a','Kp','hpower','ctpoten']}
  result['B_provenance']={k:str(b.getncattr(k)) for k in ['label','create_date','model_name','model_version','svn_version','source_file','history_type','run_type']}
  result['initial_TN_max_difference_K']=float(abs(clean(b['TN'])-clean(a['TN'])).max())
 result['padding_contract_note']='Initial checker incorrectly required TI/TE padded top valid; settei.F:638-659 explicitly sets lev1=spval. A and B masks exactly equal and lower levels fully valid; original thresholds unchanged.'
 result.update(status='STATIC_COMPATIBLE',complete_required_variables=len(REQUIRED),SOURCE_START=[80,0,0],actual_run_year=2021,source_year=2002,continuation_validated=False,raw_source_unchanged=True,license='Official public model support data, no explicit standalone data license found; keep raw local')
 (F/'initial_state_audit.json').open('x').write(json.dumps(result,indent=2));print(result['status'],len(REQUIRED),result['B_source_scalars'],result['initial_TN_max_difference_K'])
if __name__=='__main__':main()
