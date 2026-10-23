"""Versioned March windows; both source gates must pass before either GPI is written."""
import importlib.util,json,math,sys,argparse
from pathlib import Path
from datetime import date,datetime,timedelta,timezone
import numpy as np
from netCDF4 import Dataset
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
spec=importlib.util.spec_from_file_location('original_builder',ROOT/'scripts/prepare_tiegcm_training_drivers.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
F=ROOT/'experiments/training_window_mar23_v2';RAW=ROOT/'data/raw/training_window_mar23_v2';OUT=ROOT/'data/processed/training_window_mar23_v2'
def utc(d):return datetime.combine(d,datetime.min.time(),timezone.utc)
def source(p):return dict(path=str(p.relative_to(ROOT)),SHA256=old.sha(p),bytes=p.stat().st_size)
def inputs(year,fetch=False):
 protocol=json.loads((ROOT/'configs/training_windows/training_window_mar23_v2.json').read_text())['years'][str(year)]
 lo=date.fromisoformat(protocol['raw_gpi_start']);hi=date.fromisoformat(protocol['raw_gpi_end']);sl=date.fromisoformat(protocol['solar_start']);sh=date.fromisoformat(protocol['solar_end']);sources=[]
 if year==2021:
  path=ROOT/'data/raw/f107_2021_recovery_v1/gfz_year.txt';solar={};kp={}
  for line in path.read_text().splitlines():
   a=line.split()
   if not a or a[0]!='2021':continue
   d=date(*map(int,a[:3]));t=utc(d)
   if sl<=d<=sh:
    assert t not in solar;solar[t]=float(a[25])
   if lo<=d<=hi:
    assert a[27] in ['1','2'],'Non-definitive Kp'
    for j in range(8):kp[t+timedelta(hours=3*j)]=float(a[7+j])
  sources.append(dict(**source(path),URL='ftp://ftp.gfz-potsdam.de/pub/home/obs/Kp_ap_Ap_SN_F107/Kp_ap_Ap_SN_F107_2021.txt',reuse=True,license='CC BY 4.0 for Fobs/Kp; SN not extracted'))
 else:
  solarfile=ROOT/'data/raw/tiegcm_training_years_v1/2022_Fobs.json';kpfile=ROOT/'data/raw/tiegcm_training_years_v1/2022_Kp.json'
  solar=old.decode(json.loads(solarfile.read_text()),'Fobs');kp=old.decode(json.loads(kpfile.read_text()),'Kp')
  sources.extend([dict(**source(p),reuse=True) for p in [solarfile,kpfile]])
  for key,a,b,target in [('Fobs',sl,date(year,2,14),solar),('Kp',lo,date(year,3,26),kp)]:
   p=RAW/f'{year}_{key}_additional.json'
   if fetch:
    data,meta=old.fetch(key,a,b,p);old.dump(RAW/f'{year}_{key}_additional_source.json',meta)
   else:data=old.decode(json.loads(p.read_text()),key);meta=json.loads((RAW/f'{year}_{key}_additional_source.json').read_text())
   assert not set(target)&set(data),'Duplicate source timestamps';target.update(data);sources.append(meta)
  solar={t:v for t,v in solar.items() if utc(sl)<=t<=utc(sh)};kp={t:v for t,v in kp.items() if utc(lo)<=t<utc(hi+timedelta(days=1))}
 assert set(solar)=={utc(d) for d in old.dates(sl,sh)}
 assert set(kp)=={utc(d)+timedelta(hours=j) for d in old.dates(lo,hi) for j in range(0,24,3)}
 assert all(np.isfinite(v) and v>0 for v in solar.values()),'Missing/invalid Fobs'
 assert all(np.isfinite(v) and 0<=v<=9 for v in kp.values())
 return protocol,solar,kp,sources

def independent(gpi,day,seconds):
 # Independent polynomial coefficient fit, with actual noon UTC offsets.
 with Dataset(gpi) as n:
  days=list(n['year_day'][:]);i=days.index(day);left=i-2 if seconds<43200 else i-1
  anchors=np.array([((left+j)-i)*86400+43200 for j in range(4)],dtype=float)/86400
  result={k:float(np.polynomial.polynomial.polyval(seconds/86400,np.polynomial.polynomial.polyfit(anchors,n[k][left:left+4],3))) for k in ['f107d','f107a']}
  centers=np.arange(-1,9)*10800+5400;values=np.r_[n['kp'][i-1,7],n['kp'][i],n['kp'][i+1,0]]
  j=int(np.searchsorted(centers,seconds,side='right'))-1;weight=(seconds-centers[j])/10800
  k=float(values[j]*(1-weight)+values[j+1]*weight);result.update(Kp=k,hpower=16.82*math.exp(.32*k)-4.86 if k<=7 else 153.13+(k-7)/2*(300-153.13),ctpoten=15+15*k+.8*k*k)
  return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--fetch',action='store_true');p.add_argument('--build',action='store_true');args=p.parse_args()
 both={};audits={}
 for y in [2021,2022]:
  protocol,solar,kp,sources=inputs(y,args.fetch);both[y]=(protocol,solar,kp,sources)
  audits[y]=dict(status='PASS',protocol=protocol,Fobs_count=len(solar),Kp_count=len(kp),missing=0,duplicates=0,sources=sources,Fobs_range=[min(solar.values()),max(solar.values())],Kp_range=[min(kp.values()),max(kp.values())],quality='Kp definitive; Fobs no per-record quality flag, finite positive continuous only',license='GFZ CC BY 4.0',adjusted_flux_used=False)
 old.dump(F/'completeness.json',audits)
 if not args.build:return
 # This point is unreachable unless BOTH years passed complete source validation.
 for y,(protocol,solar,kp,sources) in both.items():
  lo=date.fromisoformat(protocol['raw_gpi_start']);hi=date.fromisoformat(protocol['raw_gpi_end']);ds,f,a,k=old.arrays(solar,kp,lo,hi);path=OUT/f'gpi_{y}_mar23_v2.nc'
  independent_mean=np.array([math.fsum(solar[utc(d)+timedelta(days=j)] for j in range(-40,41))/81 for d in ds]);assert max(abs(independent_mean-a))<1e-12
  old.write_gpi(path,ds,f,a,k,date.fromisoformat(protocol['model_start']),date.fromisoformat(protocol['model_end']))
  driver=old.GpiDriver(path);errors=[]
  for d in old.dates(date.fromisoformat(protocol['model_start']),date.fromisoformat(protocol['model_end'])):
   day=int(d.strftime('%Y%j'))
   for sec in [0,60,300,600,5399,5400,10800,43199,43200,86399]:
    first=driver.at(day,sec);second=independent(path,day,sec);errors.extend(abs(first[key]-second[key]) for key in first)
  assert max(errors)<1e-10
  with Dataset(path) as n:
   assert n.data_model=='NETCDF3_CLASSIC' and n['kp'].shape==(len(ds),8)
   assert n['year_day'].dtype==np.dtype('int32') and all(n[v].dtype==np.dtype('float64') for v in ['f107d','f107a','kp'])
   assert list(n['year_day'][:])==[int(d.strftime('%Y%j')) for d in ds]
  old.dump(F/f'gpi_{y}_audit.json',dict(status='PASS',year=y,file=str(path.relative_to(ROOT)),SHA256=old.sha(path),protocol=protocol,ndays=len(ds),nkp=8,independent_mean_max_difference=float(max(abs(independent_mean-a))),independent_interpolation_max_difference=max(errors),diagnostic_expected_drivers={str(s):driver.at(y*1000+82,s) for s in range(0,601,60)},arrays=dict(year_day=[int(d.strftime('%Y%j')) for d in ds],f107d=f.tolist(),f107a=a.tolist(),kp=k.tolist()),sources=sources,label='INDEPENDENT_TIEGCM_DATA_GENERATION / HINDCAST'))
  print(y,'GPI PASS',old.sha(path),flush=True)
if __name__=='__main__':main()
