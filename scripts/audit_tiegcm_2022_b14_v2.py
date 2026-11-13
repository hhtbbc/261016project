"""Independent post-wait B14 audit; does not promote historical A14."""
from pathlib import Path
import sys,json,time,re,datetime
import numpy as np
from netCDF4 import Dataset,num2date
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_tiegcm_2022_b14_v2 import F,B,H,legacy_data,dump
from run_tiegcm_mar23_2021_longrun import stream_sha
from atmosphere.tiegcm_drivers import GpiDriver
if __name__=='__main__':
 start=time.perf_counter();assert json.loads((F/'B14_supervision_gate.json').read_text())['PASS'];status=json.loads((B/'status.json').read_text());assert status['returncode']==0 and status['qualification']=='PASS' and not status['gaps'] and status['cleanup_verified'];assert status['elapsed_s']<=4800
 drv=GpiDriver(legacy_data.GPI);files=[];daily=[];hours=[];stats={};maxdriver=0.
 for kind,count in [('primary',17),('secondary',16)]:
  paths=sorted(B.glob(kind+'_*.nc'));assert len(paths)==count
  for path in paths:
   legacy_data.basic_file(path)
   with Dataset(path) as n:
    assert np.all(n['year'][:]==2022) and int(n['timestep'][:])==60 and np.all(n['calendar_advance'][:]==1)
    tt=[datetime.datetime(t.year,t.month,t.day,t.hour,t.minute,t.second,tzinfo=datetime.timezone.utc) for t in num2date(n['time'][:],n['time'].units)]
    assert np.array_equal(n['mtime'][:],np.array([[int(t.strftime('%j')),t.hour,t.minute] for t in tt]));assert np.array_equal(n['day'][:],[int(t.strftime('%j')) for t in tt])
    files.append(dict(file=path.name,SHA256=stream_sha(path),bytes=path.stat().st_size,UTC=[t.isoformat() for t in tt],history_type=n.history_type,NetCDF_format=n.data_model))
    (daily if kind=='primary' else hours).extend(tt)
    for k in ['lat','lon','lev','ilev']:np.testing.assert_array_equal(n[k][:],np.load(ROOT/f'data/processed/static/{k}.npy'))
    if kind=='primary':continue
    for name,unit in [('DEN','g/cm3'),('ZG','cm'),('Z','cm'),('TN','K'),('UN','cm/s'),('VN','cm/s'),('WN','cm/s')]:assert n[name].units==unit
    assert n['DEN'].dimensions==n['ZG'].dimensions==('time','ilev','lat','lon')
    for k in ['TN','UN','VN','WN','Z','DEN','ZG','NE','TLBC','ULBC','VLBC','f107d','f107a','Kp','O1','O2','N2','HE']:
     assert k in n.variables;v=legacy_data.field(n[k]);mask=np.ma.getmaskarray(v)
     if k in ['TN','UN','VN']:assert not mask[:,:-1].any() and mask[:,-1].all()
     else:assert not mask.any(),k
     s=stats.setdefault(k,dict(units=getattr(n[k],'units',None),dimensions=n[k].dimensions,dtype=str(n[k].dtype),min=float(v.min()),max=float(v.max())))
     s['min']=min(s['min'],float(v.min()));s['max']=max(s['max'],float(v.max()))
    for i,t in enumerate(tt):
     expected=drv.at(2022000+int(t.strftime('%j')),t.hour*3600+t.minute*60)
     for k,v in expected.items():maxdriver=max(maxdriver,abs(float(n[k][i])-v))
     assert (n['DEN'][i]>0).all() and (np.diff(n['ZG'][i],axis=0)>0).all()
 assert daily==[datetime.datetime(2022,3,9,tzinfo=datetime.timezone.utc)+datetime.timedelta(days=i) for i in range(17)]
 assert hours==[datetime.datetime(2022,3,9,tzinfo=datetime.timezone.utc)+datetime.timedelta(hours=i) for i in range(1,385)];assert maxdriver<1e-10
 text=(B/'stdout.log').read_text();assert text.count('NORMAL EXIT')==4;steps=list(map(int,re.findall(r'Step\s+(\d+) of\s+23040',text)));assert max(steps)==23040
 seen=set()
 for d,h,mi,powr,ct,f107,fa in re.findall(r'GPI run: mtime=\s*(\d+)\s+(\d+)\s+(\d+) power=\s*([\d.]+) ctpoten=\s*([\d.]+) f107=\s*([\d.]+) f107a=\s*([\d.]+)',text):
  sec=int(h)*3600+int(mi)*60;seen.add(int(d)*86400+sec);expected=drv.at(2022000+int(d),sec)
  for x,k in [(powr,'hpower'),(ct,'ctpoten'),(f107,'f107d'),(fa,'f107a')]:assert abs(float(x)-expected[k])<=.000501
 assert seen==set(range(68*86400+600,84*86400+1,600))
 ncbytes=sum(e['bytes'] for e in files);assert all(e['bytes']<=256*2**20 for e in files);assert sum(p.stat().st_size for p in B.rglob('*') if p.is_file())<5*2**30
 for name,expected in json.loads((F/'protected_files.json').read_text()).items():assert stream_sha(ROOT/name)==expected,name
 dump(B/'data_audit.json',dict(engineering_PASS=True,protocol=str(F.relative_to(ROOT)),label='EXPLORATORY_V2 / HINDCAST / A14_ENGINEERING_PARTIAL',model_steps=23040,primary_records=len(daily),secondary_records=len(hours),analysis_window_records=sum(t>=datetime.datetime(2022,3,23,tzinfo=datetime.timezone.utc) for t in hours),files=files,fields=stats,NetCDF_driver_max_abs_difference=maxdriver,driver_verified_unique_minutes=len(seen),A14_engineering='PARTIAL',v1_pair_engineering='NOT_PASS',science_training_ready=False,wall_s=time.perf_counter()-start))
 dump(B/'run_status.json',dict(returncode=status['returncode'],stop_reason=status['stop_reason'],model_launches=1,normal_exit_count=4,elapsed_s=status['elapsed_s'],peak_sampled_tree_rss_bytes=status['peak_sampled_tree_rss_bytes'],netcdf_bytes=ncbytes,wait_source=status['wait_source'],raw_supervisor_status_SHA256=stream_sha(B/'status.json')))
 dump(F/'B14_engineering_gate.json',dict(PASS=True,protocol='EXPLORATORY_V2',A14_engineering='PARTIAL',historical_v1_pair_engineering='NOT_PASS',real_model_launches=1))
 print('Independent B14 engineering PASS; A14 stays PARTIAL',time.perf_counter()-start)
