"""Read-only ten-day audit; a single initialization cannot prove spin-up sufficiency."""
import sys,json,csv,re,importlib.util
from pathlib import Path
from datetime import datetime,timedelta,timezone
import numpy as np
from netCDF4 import Dataset,num2date
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from atmosphere.tiegcm_drivers import GpiDriver
s=importlib.util.spec_from_file_location('longrun',R/'scripts/run_tiegcm_2021_14day.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--group',choices=['A14','B14'],required=True);GROUP=parser.parse_args().group
m.GROUP=GROUP;m.s.GPI=R/'data/processed/tiegcm_2021_spinup_14day_v1/gpi_2021_14day.nc'
F=m.CASE/GROUP;RESULT=R/'results/tiegcm_2021_spinup_14day_v1'/GROUP
LABEL='INDEPENDENT_TIEGCM_DATA_GENERATION / HINDCAST / SPINUP_SUFFICIENCY_UNVERIFIED / INITIAL_CONDITION_SENSITIVITY_ONLY'
KEYS=['TN','UN','VN','WN','Z','DEN','ZG','NE','TLBC','ULBC','VLBC','f107d','f107a','Kp']
def mean(a,w):
 a=np.asarray(a);return float(np.sum(a*w)/np.broadcast_to(w,a.shape).sum())
def native450(den,zg):
 result=np.full(den.shape[1:],np.nan)
 for i in range(den.shape[1]):
  for j in range(den.shape[2]):
   z=zg[:,i,j]
   if z[0]<=450e5<=z[-1]:result[i,j]=np.exp(np.interp(450e5,z,np.log(den[:,i,j])))*1000
 return result
def main():
 assert not (F/'data_audit.json').exists()
 status=json.loads((F/'run_status.json').read_text());assert status['returncode']==0 and status['stop_reason'] is None and status['normal_exit_count']==4
 RESULT.mkdir(parents=True,exist_ok=False);drv=GpiDriver(m.s.GPI);files=[];hours=[];daily=[];rows=[];fieldstats={};zgprofiles=[];largest_driver=0
 for kind,count in [('primary',18),('secondary',17)]:
  paths=sorted(F.glob(kind+'_*.nc'));assert len(paths)==count
  for path in paths:
   m.basic_file(path)
   with Dataset(path) as n:
    ts=[datetime(t.year,t.month,t.day,t.hour,t.minute,t.second,tzinfo=timezone.utc) for t in num2date(n['time'][:],n['time'].units)]
    assert (n['year'][:]==2021).all();assert np.array_equal(n['day'][:],np.array([int(t.strftime('%j')) for t in ts]))
    assert int(n['timestep'][:])==60 and (n['calendar_advance'][:]==1).all()
    files.append({'file':path.name,'SHA256':m.s.sha(path),'bytes':path.stat().st_size,'UTC':[t.isoformat() for t in ts],'NetCDF_format':n.data_model,'history_type':n.history_type})
    if kind=='primary':daily.extend(ts);continue
    hours.extend(ts)
    for k in ['lat','lon','lev','ilev']:np.testing.assert_array_equal(n[k][:],np.load(R/f'data/processed/static/{k}.npy'))
    lat=n['lat'][:];w=np.cos(np.deg2rad(lat))[:,None]
    for name in KEYS:
     assert name in n.variables;v=m.field(n[name]);mask=np.ma.getmaskarray(v)
     if name in ['TN','UN','VN']:
      assert not mask[:,:-1].any() and mask[:,-1].all()
     else:assert not mask.any(),name
     if name=='NE':assert v.min()>=0
     st=fieldstats.setdefault(name,{'unit':getattr(n[name],'units',None),'dimensions':list(n[name].dimensions),'dtype':str(n[name].dtype),'min':float(v.min()),'max':float(v.max()),'masked':0})
     st['min']=min(st['min'],float(v.min()));st['max']=max(st['max'],float(v.max()));st['masked']+=int(mask.sum())
    for k,u in [('DEN','g/cm3'),('Z','cm'),('ZG','cm'),('TN','K'),('UN','cm/s'),('VN','cm/s'),('WN','cm/s')]:assert n[k].units==u
    tn_all=m.field(n['TN']);un_all=m.field(n['UN']);vn_all=m.field(n['VN'])
    for i,t in enumerate(ts):
     yd=2021000+int(t.strftime('%j'));sec=t.hour*3600+t.minute*60;expected=drv.at(yd,sec)
     for name,value in expected.items():
      e=abs(float(n[name][i])-value);largest_driver=max(e,largest_driver);assert e<1e-10,(t,name,e)
     den=np.asarray(n['DEN'][i]);zg=np.asarray(n['ZG'][i]);assert (den>0).all() and (np.diff(zg,axis=0)>0).all()
     rho=native450(den,zg);valid=np.isfinite(rho);assert valid.any()
     def regional(a,select):
      mask=valid & select[:,None];weights=np.broadcast_to(w,mask.shape)*mask
      return float(np.nansum(a*weights)/weights.sum()) if weights.sum()>0 else None
     tn=tn_all[i,:-1];un=un_all[i,:-1];vn=vn_all[i,:-1];wn=np.asarray(n['WN'][i])
     row=dict(UTC=t.isoformat(),stage='ANALYSIS_WINDOW_ONLY' if t>=datetime(2021,3,23,tzinfo=timezone.utc) else 'SPINUP_ONLY',DEN_native_all_level_mean_kg_m3=mean(den*1000,w),DEN450_mean_kg_m3=regional(rho,np.ones(len(lat),bool)),DEN450_coverage=float(valid.mean()),DEN450_low_kg_m3=regional(rho,abs(lat)<30),DEN450_mid_kg_m3=regional(rho,(abs(lat)>=30)&(abs(lat)<60)),DEN450_polar_kg_m3=regional(rho,abs(lat)>=60),DEN450_p95_kg_m3=float(np.nanpercentile(rho,95)),TN_mean_K=mean(tn,w),TN_min_K=float(tn.min()),TN_max_K=float(tn.max()),horizontal_wind_RMS_m_s=np.sqrt(mean((un*0.01)**2+(vn*0.01)**2,w)),WN_absmax_m_s=float(abs(wn).max()*0.01),ZG_top_min_km=float(zg[-1].min()/1e5),ZG_top_max_km=float(zg[-1].max()/1e5),**expected)
     polar=(abs(lat)>=60);pv=rho[polar];row.update(DEN450_polar_min_kg_m3=float(np.nanmin(pv)),DEN450_polar_max_kg_m3=float(np.nanmax(pv)),TN_polar_min_K=float(tn[:,polar].min()),TN_polar_max_K=float(tn[:,polar].max()),polar_horizontal_wind_absmax_m_s=float(np.sqrt((un[:,polar]*.01)**2+(vn[:,polar]*.01)**2).max()))
     for k in ['O1','O2','N2','HE']:row[k+'_mean_mmr']=mean(n[k][i,:-1],w)
     rows.append(row);zgprofiles.append(np.median(zg,axis=(1,2))/1e5)
 assert daily==[datetime(2021,3,9,tzinfo=timezone.utc)+timedelta(days=i) for i in range(18)]
 assert hours==[datetime(2021,3,9,tzinfo=timezone.utc)+timedelta(hours=i) for i in range(1,409)]
 assert sum(r['stage']=='ANALYSIS_WINDOW_ONLY' for r in rows)==73
 text=(R/'logs'/f'tiegcm_2021_14day_{GROUP}.log').read_text();matches=re.findall(r'GPI run: mtime=\s*(\d+)\s+(\d+)\s+(\d+) power=\s*([\d.]+) ctpoten=\s*([\d.]+) f107=\s*([\d.]+) f107a=\s*([\d.]+)',text);seen=set()
 for day,h,minute,power,cp,flux,average in matches:
  sec=int(h)*3600+int(minute)*60;absolute=int(day)*86400+sec;seen.add(absolute);e=drv.at(2021000+int(day),sec)
  for value,key in [(power,'hpower'),(cp,'ctpoten'),(flux,'f107d'),(average,'f107a')]:assert abs(float(value)-e[key])<=.000501
 assert seen==set(range(68*86400+600,85*86400+1,600))
 steps=re.findall(r'Step\s+(\d+) of\s+24480',text);assert max(map(int,steps))==24480
 with (RESULT/'hourly_diagnostics.csv').open('x',newline='') as f:wri=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');wri.writeheader();wri.writerows(rows)
 np.savetxt(RESULT/'median_ZG_profiles_km.csv',np.array(zgprofiles),delimiter=',')
 # Temporal state change, explicitly NOT same-time initialization sensitivity.
 windows={}
 for name,lo,hi in [('first14days','2021-03-09','2021-03-23'),('last48hours','2021-03-24','2021-03-26'),('training_start_plusminus12h','2021-03-22T12','2021-03-23T12')]:
  a=[r for r in rows if datetime.fromisoformat(lo).replace(tzinfo=timezone.utc)<=datetime.fromisoformat(r['UTC'])<=datetime.fromisoformat(hi).replace(tzinfo=timezone.utc)]
  windows[name]={k:{'first':a[0][k],'last':a[-1][k],'min':min(r[k] for r in a),'max':max(r[k] for r in a)} for k in ['DEN450_mean_kg_m3','TN_mean_K','horizontal_wind_RMS_m_s']}
 result=dict(label=LABEL,engineering_PASS=True,primary_records=len(daily),secondary_records=len(hours),analysis_window_records=73,model_steps=24480,driver_verified_unique_minutes=len(seen),actual_driver_log_interval_seconds=600,expected_driver_static_minute_nodes=24481,NetCDF_driver_max_abs_difference=largest_driver,files=files,fields=fieldstats,temporal_changes_not_spinup_convergence=windows,spinup_status='SPINUP_SUFFICIENCY_UNVERIFIED',training_approved=False,initial_primary_record='inherited cold initialization; diagnostics may be N/A',grid_author_exact=True)
 (F/'data_audit.json').write_text(json.dumps(result,indent=2,allow_nan=False));print('AUDIT PASS',len(rows))
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 h=np.arange(1,409)
 groups=[('density',['DEN_native_all_level_mean_kg_m3','DEN450_mean_kg_m3'],['kg/m3','kg/m3']),('latitude_bands',['DEN450_low_kg_m3','DEN450_mid_kg_m3','DEN450_polar_kg_m3'],['kg/m3']*3),('temperature_wind',['TN_mean_K','horizontal_wind_RMS_m_s','WN_absmax_m_s'],['K','m/s','m/s']),('drivers',['f107d','f107a','Kp'],['sfu','sfu','1']),('composition',['O1_mean_mmr','O2_mean_mmr','N2_mean_mmr','HE_mean_mmr'],['mmr']*4)]
 for title,keys,units in groups:
  fig,axes=plt.subplots(len(keys),1,figsize=(9,2.1*len(keys)),sharex=True,squeeze=False)
  for ax,k,u in zip(axes[:,0],keys,units):ax.plot(h,[r[k] for r in rows]);ax.axvline(336,color='r',ls='--');ax.set_ylabel(u);ax.set_title(k,fontsize=9);ax.grid(alpha=.25)
  axes[-1,0].set_xlabel('Hours since 2021-03-09 00 UTC; red = candidate boundary');fig.suptitle('INDEPENDENT / HINDCAST / SPINUP UNVERIFIED',fontsize=10);fig.tight_layout();fig.savefig(RESULT/f'{title}.png',dpi=130);plt.close(fig)
 fig,ax=plt.subplots(figsize=(9,4));mesh=ax.pcolormesh(h,np.arange(29),np.array(zgprofiles).T,shading='auto');fig.colorbar(mesh,label='Median native ZG (km)');ax.set(xlabel='Hours since 2021-03-09 00 UTC',ylabel='Native ilev index',title='ZG structure / SPINUP UNVERIFIED');fig.tight_layout();fig.savefig(RESULT/'ZG_structure.png',dpi=130);plt.close(fig)
if __name__=='__main__':main()
