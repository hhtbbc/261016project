"""Bounded GFZ hindcast acquisition and source-compatible GPI, never starts TIE-GCM."""
import sys,json,hashlib,argparse,urllib.request
from pathlib import Path
from datetime import date,datetime,timedelta,timezone
import numpy as np
from netCDF4 import Dataset
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from atmosphere.tiegcm_drivers import GpiDriver
F=ROOT/'experiments/tiegcm_training_years_v1';RAW=ROOT/'data/raw/tiegcm_training_years_v1';OUT=ROOT/'data/processed/tiegcm_training_years_v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2,allow_nan=False)
def dates(a,b):
 if a>b:raise ValueError('Reversed interval')
 return [a+timedelta(days=i) for i in range((b-a).days+1)]
def decode(payload,key):
 ts=payload['datetime'];values=payload[key]
 if len(ts)!=len(values) or len(set(ts))!=len(ts):raise ValueError('Length/duplicate timestamp')
 if key=='Kp' and payload.get('status')!=['def']*len(ts):raise ValueError('Kp must be definitive')
 result={datetime.fromisoformat(t.replace('Z','+00:00')):float(v) for t,v in zip(ts,values)}
 if any(t.tzinfo is None or t.utcoffset()!=timedelta(0) for t in result) or not all(np.isfinite(list(result.values()))):raise ValueError('Invalid time/value')
 if key=='Fobs' and any(v<=0 for v in result.values()):raise ValueError('Invalid Fobs')
 if key=='Kp' and any(not 0<=v<=9 for v in result.values()):raise ValueError('Invalid Kp')
 return result

def arrays(solar,kp,raw_start,raw_end):
 daylist=dates(raw_start,raw_end);f=[];a=[];k=[]
 for d in daylist:
  t=datetime.combine(d,datetime.min.time(),timezone.utc)
  f.append(solar[t]);samples=[solar[t+timedelta(days=j)] for j in range(-40,41)]
  a.append(float(np.mean(samples)));k.append([kp[t+timedelta(hours=h)] for h in range(0,24,3)])
 return daylist,np.asarray(f),np.asarray(a),np.asarray(k)

def write_gpi(path,daylist,flux,average,kp,valid_start,valid_end):
 if path.exists():raise FileExistsError(path)
 if kp.shape!=(len(daylist),8) or any(x.shape!=(len(daylist),) for x in [flux,average]) or not all(np.isfinite(x).all() for x in [flux,average,kp]):raise ValueError('Invalid arrays')
 if valid_start not in daylist[2:-2] or valid_end not in daylist[2:-2]:raise ValueError('Insufficient interpolation padding')
 yd=np.array([int(d.strftime('%Y%j')) for d in daylist],dtype='int32')
 with Dataset(path,'w',format='NETCDF3_CLASSIC') as n:
  n.createDimension('ndays',len(daylist));n.createDimension('nkp',8)
  for name,value,dims,dtype,unit in [('year_day',yd,('ndays',),'i4','YYYYDDD'),('f107d',flux,('ndays',),'f8','sfu'),('f107a',average,('ndays',),'f8','sfu'),('kp',kp,('ndays','nkp'),'f8','1')]:v=n.createVariable(name,dtype,dims);v[:]=value;v.units=unit
  n.yearday_beg=np.int32(valid_start.strftime('%Y%j'));n.yearday_end=np.int32(valid_end.strftime('%Y%j'));n.title='INDEPENDENT_TIEGCM_DATA_GENERATION / GFZ historical observed flux / HINDCAST';n.data_source_url='https://kp.gfz.de/en/data';n.license='CC BY 4.0 (GFZ source metadata)';n.averaging_window_days=81;n.averaging_kind='centered';n.time_standard='UTC';n.kp_convention='GFZ starts 00/03/...; model centers 01:30/04:30/...; linear interpolation'

def fetch(key,start,end,path):
 url=f'https://kp.gfz.de/app/json/?start={start.isoformat()}T00:00:00Z&end={end.isoformat()}T23:59:59Z&index={key}'+('&status=def' if key=='Kp' else '')
 if path.exists():raise FileExistsError(path)
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Satellite-AI-hindcast-audit/1.0'}),timeout=30) as r:
  body=r.read(2**20+1);assert r.status==200 and len(body)<=2**20
 with path.open('xb') as f:f.write(body)
 payload=json.loads(body);parsed=decode(payload,key);expected={datetime.combine(d,datetime.min.time(),timezone.utc)+timedelta(hours=h) for d in dates(start,end) for h in ([0] if key=='Fobs' else range(0,24,3))};assert set(parsed)==expected,'Missing/extra time samples';path.chmod(0o444)
 return parsed,dict(URL=url,HTTP=200,bytes=len(body),SHA256=sha(path),path=str(path.relative_to(ROOT)),requested_dates=[start.isoformat(),end.isoformat()],actual_first=min(parsed).isoformat(),actual_last=max(parsed).isoformat(),count=len(parsed),missing=0,license=payload.get('meta',{}).get('license'),quality='all def' if key=='Kp' else 'no per-record quality flag exposed; finite/positive/continuous only',source_meta=payload.get('meta',{}))

def main():
 p=argparse.ArgumentParser();p.add_argument('--year',type=int,choices=[2021,2022],required=True);p.add_argument('--valid-start');p.add_argument('--valid-end');args=p.parse_args();year=args.year
 start=date.fromisoformat(args.valid_start) if args.valid_start else date(year,3,29);end=date.fromisoformat(args.valid_end) if args.valid_end else date(year,4,8 if year==2021 else 7)
 assert start.year==end.year==year and start<=date(year,4,5)<=end
 F.mkdir(exist_ok=True);RAW.mkdir(exist_ok=True);OUT.mkdir(exist_ok=True);folder=F/str(year);folder.mkdir(exist_ok=False);lo=start-timedelta(days=2);hi=end+timedelta(days=2)
 sources=[]
 try:
  solar,r=fetch('Fobs',lo-timedelta(days=40),hi+timedelta(days=40),RAW/f'{year}_Fobs.json');sources.append(r);kp,r=fetch('Kp',lo,hi,RAW/f'{year}_Kp.json');sources.append(r)
  ds,f,a,k=arrays(solar,kp,lo,hi);path=OUT/f'gpi_{year}_training_candidate.nc';write_gpi(path,ds,f,a,k,start,end)
  # Independent Python list lookup / fsum, no NumPy mean reuse.
  import math
  errors=[]
  for i,d in enumerate(ds):
   t=datetime.combine(d,datetime.min.time(),timezone.utc);independent=math.fsum(solar[t+timedelta(days=j)] for j in range(-40,41))/81;errors.append(abs(independent-a[i]));assert abs(independent-a[i])<1e-12
  with Dataset(path) as n:
   assert n.data_model=='NETCDF3_CLASSIC';assert n['kp'].dimensions==('ndays','nkp') and n['kp'].shape==(len(ds),8);assert n['year_day'].dtype==np.dtype('int32');assert all(n[v].dtype==np.dtype('float64') for v in ['f107d','f107a','kp']);np.testing.assert_array_equal(n['f107a'][:],a)
  driver=GpiDriver(path);day=int(date(year,4,5).strftime('%Y%j'));expected={str(s):driver.at(day,s) for s in range(0,601,60)}
  audit=dict(status='PASS',label='INDEPENDENT_TIEGCM_DATA_GENERATION / HINDCAST',year=year,file=str(path.relative_to(ROOT)),SHA256=sha(path),raw_dates=[lo.isoformat(),hi.isoformat()],valid_dates=[start.isoformat(),end.isoformat()],ndays=len(ds),kp_count=k.size,solar_fsum_max_difference=max(errors),sources=sources,diagnostic_expected_drivers=expected,generated_arrays=dict(year_day=[int(d.strftime('%Y%j')) for d in ds],f107d=f.tolist(),f107a=a.tolist(),kp=k.tolist()),source_2023_reused=False)
  dump(folder/'driver_audit.json',audit);print(json.dumps({key:value for key,value in audit.items() if key!='generated_arrays'},indent=2))
 except Exception as e:dump(folder/'failure.json',dict(error=str(e),sources_completed=sources));raise
if __name__=='__main__':main()
