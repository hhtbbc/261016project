"""Independent originals-only V21 verification; no residual, fit, or model API."""
from pathlib import Path
import sys,json,csv,zipfile,zlib,subprocess,datetime,math
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src')]
import numpy as np,cdflib
from netCDF4 import Dataset
from atmosphere.restart_validation import REQUIRED
from observations.bounded_swarm_acquisition import sha

def verify(D,F,assets,zip_charge):
 observations={};drivers={};initial={};fail=[]
 request=json.loads((R/'experiments/thermosphere_independent_date_validation_plan_v20/next_acquisition_request_final.json').read_text())
 windows=list(csv.DictReader((F/'Swarm_window_latitude_counts.csv').open())) if (F/'Swarm_window_latitude_counts.csv').exists() else []
 for req in request['Swarm']:
  year=req['date'][:4];key='Swarm'+year
  if key not in assets:observations[year]=dict(PASS=False,reason='NOT_ACQUIRED');continue
  try:
   p=R/assets[key]['path'];assert sha(p)==assets[key]['SHA256'] and p.stat().st_size==int(req['cached_bytes']);stem=p.stem
   with zipfile.ZipFile(p) as z:
    infos=z.infolist();assert len(infos)==2 and {v.filename for v in infos}=={stem+'.cdf',stem+'.HDR'};n=sum(v.file_size for v in infos)
    if zip_charge+n*2>2*2**20:raise ValueError('Independent ZIP decode cap would exceed budget')
    zip_charge+=n*2;assert z.testzip() is None
    for ent in infos:
     assert Path(ent.filename).name==ent.filename and '/' not in ent.filename and '\\' not in ent.filename and not (ent.external_attr>>16)&0o170000==0o120000
     block=z.read(ent.filename);assert len(block)==ent.file_size and zlib.crc32(block)&0xffffffff==ent.CRC;assert (D/ent.filename).read_bytes()==block
   cp=D/(stem+'.cdf');hp=D/(stem+'.HDR');parts=subprocess.check_output(['cksum',str(cp)],text=True,cwd=R).split();crc,size=map(int,parts[:2]);import xml.etree.ElementTree as ET;root=ET.parse(hp).getroot();assert int(root.findtext('Variable_Header/MPH/CRC'))==crc and int(root.findtext('Variable_Header/MPH/Tot_Size'))==size;assert root.findtext('Fixed_Header/File_Name')==stem and root.findtext('Fixed_Header/File_Type')=='DNSAPOD_2_' and root.findtext('Fixed_Header/File_Version')=='0301'
   with cdflib.CDF(cp) as c:
    t=cdflib.cdfepoch.to_datetime(c.varget('time'));qflag=c.varget('validity_flag');rho=c.varget('density');lat=c.varget('latitude');lon=c.varget('longitude');alt=c.varget('altitude');assert c.globalattsget()['TITLE']==[stem] and c.globalattsget()['TIME SYSTEM']==['UTC'] and c.varinq('time').Data_Type==31;assert c.varattsget('density')['UNITS']=='kg/m3' and c.varattsget('altitude')['UNITS']=='m'
   assert len(t)==2880 and t[0]==np.datetime64(req['date']) and t[-1]==np.datetime64(req['date']+'T23:59:30') and np.all(np.diff(t)==np.timedelta64(30,'s'))
   valid=(qflag==0)&np.isfinite(rho)&(rho>0)&(rho!=9.99e32)&(rho<1e30)&np.isfinite(lat)&(abs(lat)<=90)&np.isfinite(lon)&(abs(lon)<=180)&np.isfinite(alt)&(alt>0);band=np.where(abs(lat)<30,0,np.where(abs(lat)<60,1,2));checked=0
   for w in windows:
    if w['date']!=req['date']:continue
    cut=np.datetime64(req['date']+f'T{int(w["cutoff"]):02d}');start=cut-np.timedelta64(3,'h') if w['window']=='history' else cut;stop=cut if w['window']=='history' else cut+np.timedelta64(int(w['window'].split('_')[1][:-1]),'h');m=(t>=start)&(t<stop)
    if w['region']!='all':m&=band==['low','mid','high'].index(w['region'])
    assert int(w['records'])==m.sum() and int(w['quality_valid'])==(m&valid).sum() and w['N30_supported']==str(bool((m&valid).sum()>=30));checked+=1
   assert checked==32
   observations[year]=dict(PASS=True,ZIP_SHA256=sha(p),CDF_SHA256=sha(cp),HDR_SHA256=sha(hp),ZIP_CRC_PASS=True,HDR_POSIX_CRC_independent_coreutils=crc,UTC_records=2880,valid=int(valid.sum()),flag0=int((qflag==0).sum()),flag1=int((qflag==1).sum()),unknown_flags=int((~np.isin(qflag,[0,1])).sum()),window_region_rows_independently_checked=checked,no_density_distribution_computed=True)
  except Exception as e:observations[year]=dict(PASS=False,error_type=type(e).__name__,reason=str(e).replace(str(R),'[project]'))
 # Parse driver source formats directly, without calling the main decoder/mean builder.
 for year in [2021,2022]:
  try:
   if year==2021:
    p=R/'data/raw/f107_2021_recovery_v1/gfz_year.txt';assert sha(p)=='f969f23b0b0d4aba80dca6f35d3e95c2d35a7e482457bc1812e5c0827090caae';sun={};kp={}
    for line in p.read_text().splitlines():
     parts=line.split()
     if parts and parts[0]=='2021':
      day=datetime.date(*map(int,parts[:3]));sun[day]=float(parts[25])
      for i in range(8):kp[datetime.datetime.combine(day,datetime.time(i*3))]=(float(parts[7+i]),parts[27]=='2')
   else:
    if not all(k in assets for k in ['GFZ_Fobs','GFZ_Kp']):raise ValueError('NOT_ACQUIRED')
    f=R/assets['GFZ_Fobs']['path'];k=R/assets['GFZ_Kp']['path'];assert sha(f)==assets['GFZ_Fobs']['SHA256'] and sha(k)==assets['GFZ_Kp']['SHA256'];a=json.loads(f.read_text());b=json.loads(k.read_text());assert len(a['datetime'])==101 and len(b['datetime'])==168 and len(set(a['datetime']))==101 and len(set(b['datetime']))==168;assert b['status']==['def']*168
    sun={datetime.datetime.strptime(t,'%Y-%m-%dT%H:%M:%SZ').date():float(v) for t,v in zip(a['datetime'],a['Fobs'])};kp={datetime.datetime.strptime(t,'%Y-%m-%dT%H:%M:%SZ'):(float(v),s=='def') for t,v,s in zip(b['datetime'],b['Kp'],b['status'])}
   start=datetime.date(year,7,29);need=[start+datetime.timedelta(days=i) for i in range(101)];raw=datetime.date(year,9,7);times=[datetime.datetime.combine(raw+datetime.timedelta(days=i),datetime.time(h)) for i in range(21) for h in range(0,24,3)];assert all(d in sun and math.isfinite(sun[d]) and sun[d]>0 for d in need) and all(t in kp and kp[t][1] and math.isfinite(kp[t][0]) and 0<=kp[t][0]<=9 for t in times)
   daily=[]
   for i in range(21):
    center=raw+datetime.timedelta(days=i);mean=math.fsum(sun[center+datetime.timedelta(days=j)] for j in range(-40,41))/81;daily.append(mean)
   firstrows=list(csv.DictReader((F/'center81_static_check.csv').open()));our=[x for x in firstrows if int(x['year'])==year];assert len(our)==21 and all(abs(float(r['center81_mean_sfu'])-v)<1e-12 for r,v in zip(our,daily))
   day=datetime.date(year,9,23);bins=[kp[datetime.datetime.combine(day,datetime.time(h))][0] for h in range(0,24,3)];maximum=max(bins);label='QUIET' if maximum<=2 else 'ENHANCED' if maximum>=5 else 'INTERMEDIATE';drivers[str(year)]=dict(PASS=True,Fobs_count=101,Kp_count=168,center81_means_checked=21,Fobs_target_sfu=sun[day],center81_target_sfu=math.fsum(sun[day+datetime.timedelta(days=j)] for j in range(-40,41))/81,Kp_target_max=maximum,activity=label,no_new_GPI=True)
  except Exception as e:drivers[str(year)]=dict(PASS=False,error_type=type(e).__name__,reason=str(e).replace(str(R),'[project]'))
 if 'initial' in assets:
  try:
   path=R/assets['initial']['path'];assert sha(path)==assets['initial']['SHA256'];old=R/'data/raw/tiegcm_2021_spinup_initial_condition_v1/tiegcm_res5.0_mareqx_smax_prim.nc';checked=0
   with Dataset(path) as n,Dataset(old) as ref:
    n.set_auto_mask(False);ref.set_auto_mask(False);assert n.history_type=='primary' and all(k in n.variables for k in REQUIRED);records=np.asarray(n['mtime'][:],int);chosen=[list(map(int,t)) for t in records if t[1]==t[2]==0];assert len(chosen)==1
    for coord in ['lat','lon','lev','ilev']:np.testing.assert_array_equal(n[coord][:],ref[coord][:])
    for name in REQUIRED:
     v=n[name];w=ref[name];assert v.dtype==np.dtype('float64') and v.dimensions==w.dimensions and v.shape==w.shape and getattr(v,'units',None)==getattr(w,'units',None);a=np.asarray(v[:]);assert np.isfinite(a).all();bad=abs(a)>1e30
     for attr in ['missing_value','_FillValue']:
      if hasattr(v,attr):bad|=a==np.asarray(getattr(v,attr),dtype=a.dtype)
     expected=np.zeros(a.shape,bool)
     if name in ['TN','TN_NM','UN','UN_NM','VN','VN_NM','TI','TE']:expected[:,-1]=True
     assert np.array_equal(bad,expected);good=a[~bad];assert len(good)>0
     if name in ['TN','TN_NM','TLBC','TLBC_NM']:assert good.min()>100 and good.max()<5000
     if name in ['TI','TE']:assert good.min()>0
     if name in ['UN','UN_NM','VN','VN_NM']:assert abs(good).max()<2e5
     if getattr(v,'units','').lower()=='mmr':assert good.min()>=0 and good.max()<=1.000001
     if name in ['NE','OP','O2P']:assert good.min()>=0
     if name=='Z':assert (np.diff(a,axis=1)>0).all()
     checked+=1
   initial=dict(PASS=True,SHA256=sha(path),actual_SOURCE_START=chosen[0],complete_states_checked=checked,strict_schema_padding_values=True,scientific_spinup_convergence=False,no_policy_approval=True)
  except Exception as e:initial=dict(PASS=False,error_type=type(e).__name__,reason=str(e).replace(str(R),'[project]'))
 else:initial=dict(PASS=False,reason='NOT_ACQUIRED')
 v20=R/'experiments/thermosphere_independent_date_validation_plan_v20/preregistered_protocol.json';assert sha(v20)==json.loads((v20.parent/'protocol_sha256.json').read_text())['SHA256']
 return dict(observations=observations,drivers=drivers,initial=initial,V20_protocol_unchanged=True,independent_readers=True,ZIP_upper_bound_bytes_charged=zip_charge,new_model_invocations=0,new_fits=0,new_scores=0)
