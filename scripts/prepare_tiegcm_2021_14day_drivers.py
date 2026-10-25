"""Bounded, versioned extended 2021 GPI; reuse verified GFZ raw observations."""
from pathlib import Path
import sys,json,importlib.util,math
from datetime import date,datetime,timedelta,timezone
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'scripts'),str(R/'src')]
import prepare_tiegcm_training_drivers as old
from prepare_tiegcm_mar23_drivers import independent,utc
C=R/'experiments/tiegcm_2021_spinup_14day_v1';OUT=R/'data/processed/tiegcm_2021_spinup_14day_v1'
def support():
 start=date(2021,3,9);end=date(2021,3,26);lo=start-timedelta(days=2);hi=end+timedelta(days=2)
 return start,end,lo,hi,lo-timedelta(days=40),hi+timedelta(days=40)
def main():
 C.mkdir(exist_ok=False);OUT.mkdir(exist_ok=False);start,end,lo,hi,sl,sh=support();source=R/'data/raw/f107_2021_recovery_v1/gfz_year.txt';solar={};kp={};quality={}
 try:
  for line in source.read_text().splitlines():
   a=line.split()
   if not a or a[0]!='2021':continue
   d=date(*map(int,a[:3]));t=utc(d)
   if sl<=d<=sh:
    assert t not in solar;solar[t]=float(a[25])
   if lo<=d<=hi:
    assert a[27]=='2','Definitive archived Kp required';quality[t.isoformat()]=a[27]
    for j in range(8):assert t+timedelta(hours=3*j) not in kp;kp[t+timedelta(hours=3*j)]=float(a[7+j])
  assert set(solar)=={utc(d) for d in old.dates(sl,sh)} and all(np.isfinite(v) and v>0 for v in solar.values())
  assert set(kp)=={utc(d)+timedelta(hours=h) for d in old.dates(lo,hi) for h in range(0,24,3)} and all(np.isfinite(v) and 0<=v<=9 for v in kp.values())
  ds,f,a,k=old.arrays(solar,kp,lo,hi);ref=np.array([math.fsum(solar[utc(d)+timedelta(days=j)] for j in range(-40,41))/81 for d in ds]);assert max(abs(a-ref))<1e-12
  p=OUT/'gpi_2021_14day.nc';old.write_gpi(p,ds,f,a,k,start,end);driver=old.GpiDriver(p);errors=[]
  for d in old.dates(start,end):
   for sec in [0,60,5399,5400,10800,43199,43200,86399]:
    x=driver.at(int(d.strftime('%Y%j')),sec);y=independent(p,int(d.strftime('%Y%j')),sec);errors.extend(abs(x[q]-y[q]) for q in x)
  assert max(errors)<1e-10
  # Common old/new domain must be identical, independently of the extended boundaries.
  previous=old.GpiDriver(R/'data/processed/training_window_mar23_v2/gpi_2021_mar23_v2.nc');common=[]
  for absolute in range(75*86400,85*86400+1,60):
   d,s=divmod(absolute,86400);x=driver.at(2021000+d,s);y=previous.at(2021000+d,s);common.extend(abs(x[q]-y[q]) for q in x)
  assert max(common)<1e-10
  audit=dict(status='PASS',model_dates=[str(start),str(end)],raw_dates=[str(lo),str(hi)],solar_dates=[str(sl),str(sh)],Fobs_count=len(solar),Kp_count=len(kp),missing=0,duplicates=0,estimated_or_adjusted_used=False,quality='Fobs valid observed archive values; no per-record solar flag; Kp column28=2 definitive',source={'path':str(source.relative_to(R)),'SHA256':old.sha(source),'URL':'ftp://ftp.gfz-potsdam.de/pub/home/obs/Kp_ap_Ap_SN_F107/Kp_ap_Ap_SN_F107_2021.txt','license':'GFZ CC BY 4.0; raw reused unchanged'},file=str(p.relative_to(R)),SHA256=old.sha(p),ndays=len(ds),nkp=8,independent_mean_max_difference=float(max(abs(a-ref))),independent_interpolation_max_difference=max(errors),common_14401_minute_nodes_max_difference=max(common),arrays={'year_day':[int(d.strftime('%Y%j')) for d in ds],'f107d':f.tolist(),'f107a':a.tolist(),'kp':k.tolist()})
  old.dump(C/'driver_audit.json',audit);p.chmod(0o444);print('Extended GPI PASS',audit['SHA256'])
 except Exception as e:old.dump(C/'driver_failure.json',{'error':repr(e)});raise
if __name__=='__main__':main()
