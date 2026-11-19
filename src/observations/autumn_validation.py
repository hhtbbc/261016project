"""V21 read-only quality/primary checks. Never computes observation residuals."""
from pathlib import Path
import re,datetime,math
import numpy as np
from netCDF4 import Dataset
from atmosphere.restart_validation import REQUIRED,inspect_restart,check_source_clock
from evaluation.swarm_density_comparison import quality_mask

def check_product_stem(stem,day):
 expected='SW_OPER_DNSAPOD_2__'+day.replace('-','')+'T000000_'+day.replace('-','')+'T235930_0301'
 if stem!=expected:raise ValueError('Wrong date/product/satellite/version')
 return expected

def check_times(times,day):
 t=np.asarray(times,dtype='datetime64[ns]')
 if len(t)!=2880 or np.isnat(t).any() or t[0]!=np.datetime64(day) or t[-1]!=np.datetime64(day+'T23:59:30') or not np.all(np.diff(t)==np.timedelta64(30,'s')):raise ValueError('CDF UTC coverage/cadence mismatch')

def source_clock(records):
 x=np.asarray(records,int)
 if x.ndim!=2 or x.shape[1]!=3:raise ValueError('Bad native mtime')
 good=x[(x[:,1]==0)&(x[:,2]==0)]
 if len(good)!=1:raise ValueError('A unique actual00:00 native record is required; no timestamp repair')
 check_source_clock([252,0,0],good[0].tolist());return good[0].tolist()

def quality_counts(a):
 q,parts=quality_mask(a['density'],a['validity_flag']);coord=np.isfinite(a['latitude'])&np.isfinite(a['longitude'])&np.isfinite(a['altitude'])&(abs(a['latitude'])<=90)&(abs(a['longitude'])<=180)&(a['altitude']>0)
 q&=coord
 return q,dict(records=len(q),flag0=int((a['validity_flag']==0).sum()),flag1=int(parts['anomalous'].sum()),unknown_flags=int(parts['unknown'].sum()),invalid_density=int(parts['invalid_density'].sum()),invalid_coordinates=int((~coord).sum()),valid=int(q.sum()))

def native_field(v):
 v.set_auto_mask(False);raw=np.asarray(v[:]);mask=abs(raw)>1e30
 if not np.isfinite(raw).all():raise ValueError('Nonfinite native state '+v.name)
 for attr in ['_FillValue','missing_value']:
  if hasattr(v,attr):mask|=raw==np.asarray(getattr(v,attr),dtype=raw.dtype)
 return raw,mask

def inspect_initial(path,reference):
 rows=[]
 with Dataset(path) as n,Dataset(reference) as ref:
  missing=[k for k in REQUIRED if k not in n.variables]
  if missing:raise ValueError('Missing complete primary states: '+','.join(missing))
  if getattr(n,'history_type',None)!='primary':raise ValueError('Not a full primary')
  records=np.asarray(n['mtime'][:],int);chosen=source_clock(records)
  for k in ['lat','lon','lev','ilev']:
   if not np.array_equal(n[k][:],ref[k][:]):raise ValueError('Grid mismatch '+k)
  for k in REQUIRED:
   v=n[k];old=ref[k]
   if v.dimensions!=old.dimensions or v.shape!=old.shape or v.dtype!=np.dtype('float64') or getattr(v,'units',None)!=getattr(old,'units',None):raise ValueError('State schema/unit/dtype mismatch '+k)
   x,mask=native_field(v);xr,mr=native_field(old)
   if k in ['TN','TN_NM','UN','UN_NM','VN','VN_NM','TI','TE']:
    if mask[:,:-1].any() or not mask[:,-1].all() or not np.array_equal(mask,mr):raise ValueError('Unknown top/below-top padding '+k)
   elif mask.any():raise ValueError('Incomplete native state '+k)
   valid=x[~mask]
   if not len(valid):raise ValueError('Empty native state '+k)
   unit=getattr(v,'units','')
   if k in ['TN','TN_NM','TLBC','TLBC_NM'] and not (valid.min()>100 and valid.max()<5000):raise ValueError('Temperature range '+k)
   if k in ['TI','TE'] and not (valid.min()>0):raise ValueError('Nonpositive plasma temperature '+k)
   if k in ['UN','UN_NM','VN','VN_NM'] and abs(valid).max()>=2e5:raise ValueError('Wind range '+k)
   if unit.lower()=='mmr' and not (valid.min()>=0 and valid.max()<=1.000001):raise ValueError('Composition range '+k)
   if k in ['OP','O2P','NE'] and valid.min()<0:raise ValueError('Negative plasma state '+k)
   if k=='Z' and not (np.diff(x,axis=1)>0).all():raise ValueError('Nonmonotonic primary Z')
   rows.append(dict(variable=k,dimensions=list(v.dimensions),shape=list(v.shape),dtype=str(v.dtype),units=unit,finite=True,masked_count=int(mask.sum()),valid_count=int((~mask).sum()),min_valid=float(valid.min()),max_valid=float(valid.max()),padding_matches_mareqx=bool(np.array_equal(mask,mr)),max_abs_state_difference_from_mareqx=float(abs(x[~mask]-xr[~mask]).max())))
  attrs={k:str(getattr(n,k,'')) for k in ['label','create_date','model_name','model_version','svn_version','history_type','run_type']};attrs_ref={k:str(getattr(ref,k,'')) for k in ['label','create_date','model_name','model_version','svn_version','history_type','run_type']}
  provenance=str(getattr(n,'source_file',''));scalars={k:np.asarray(n[k][:]).tolist() for k in ['f107d','f107a','Kp','hpower','ctpoten'] if k in n.variables};years=np.asarray(n['year'][:]).astype(int).tolist()
  result=dict(status='ENGINEERING_COMPATIBLE_CANDIDATE_NOT_SCIENCE_PASS',NetCDF_format=n.data_model,primary_records=len(records),years=years,day_values=np.asarray(n['day'][:]).tolist() if 'day' in n.variables else None,time_values=np.asarray(n['time'][:]).tolist() if 'time' in n.variables else None,time_units=getattr(n['time'],'units','') if 'time' in n.variables else None,mtime=records.tolist(),SOURCE_START=chosen,actual_calendar_records=[(datetime.datetime(int(y),1,1)+datetime.timedelta(days=int(mt[0])-1,hours=int(mt[1]),minutes=int(mt[2]))).isoformat() for y,mt in zip(years,records)],required_complete_states=len(REQUIRED),all_state_schema_and_units_match_mareqx=True,grid={k:len(n.dimensions[k]) for k in ['lat','lon','lev','ilev']},vertical_coordinates={k:np.asarray(n[k][:]).tolist() for k in ['lev','ilev']},height_structure={k:dict(dimensions=list(n[k].dimensions),units=getattr(n[k],'units','')) for k in ['Z','ZG','DEN'] if k in n.variables},attributes=attrs,mareqx_attributes=attrs_ref,source_file_basename=Path(provenance.split(' ')[0]).name,source_file_attribute_SHA256=__import__('hashlib').sha256(provenance.encode()).hexdigest(),source_scalars=scalars,mareqx_SOURCE_START=np.asarray(ref['mtime'][:]).astype(int).tolist(),seasonal_sufficiency='UNVERIFIED',restart_validated=False,state_values=rows)
 native=inspect_restart(path,chosen)
 if not native['structure_complete'] or not native['record_available']:raise ValueError('Existing strict primary inspector did not accept source')
 return result
