"""Create source-compatible hindcast GPI; never starts the model."""
from pathlib import Path
from datetime import date, timedelta
import hashlib,json
import numpy as np
from netCDF4 import Dataset
ROOT=Path(__file__).resolve().parents[1]
def load(rel,key):
    p=ROOT/rel; d=json.loads(p.read_text())
    assert len(d['datetime'])==len(d[key])
    assert len(set(d['datetime']))==len(d[key])
    return dict(zip(d['datetime'],d[key])),d,p
def main():
    f,_,fp=load('data/raw/meeting_sources/gfz_Fobs_spinup_support.txt','Fobs')
    k,kd,kp=load('data/raw/meeting_sources/gfz_Kp_extended_support.txt','Kp')
    extra,ed,ep=load('data/raw/tiegcm2023_sources/gfz_Kp_mar25.json','Kp')
    assert all(s=='def' for s in kd['status']+ed['status'])
    for t,v in extra.items():
        assert t not in k or k[t]==v
        k[t]=v
    days=[date(2023,3,12)+timedelta(days=i) for i in range(14)]
    daily=[];average=[];ks=[]
    for d in days:
        key=lambda x:x.isoformat()+'T00:00:00Z'
        daily.append(f[key(d)])
        values=[f[key(d+timedelta(days=i))] for i in range(-40,41)]
        assert len(values)==81 and all(np.isfinite(values)) and min(values)>0
        average.append(float(np.mean(values)))
        ks.append([k[f'{d.isoformat()}T{h:02}:00:00Z'] for h in range(0,24,3)])
    ks=np.asarray(ks); assert ks.shape==(14,8) and np.isfinite(ks).all() and ((ks>=0)&(ks<=9)).all()
    out=ROOT/'data/processed/tiegcm2023';out.mkdir(exist_ok=False)
    path=out/'gpi_20230312_20230325.nc'
    yd=np.array([int(d.strftime('%Y%j')) for d in days],dtype='int32')
    with Dataset(path,'w',format='NETCDF3_CLASSIC') as nc:
        nc.createDimension('ndays',14);nc.createDimension('nkp',8)
        for name,data,dims,dtype,unit in [('year_day',yd,('ndays',),'i4','YYYYDDD'),('f107d',daily,('ndays',),'f8','sfu'),('f107a',average,('ndays',),'f8','sfu'),('kp',ks,('ndays','nkp'),'f8','1')]:
            v=nc.createVariable(name,dtype,dims);v[:]=data;v.units=unit
        nc.yearday_beg=np.int32(yd[2]);nc.yearday_end=np.int32(yd[-3])
        nc.title='GFZ observed F10.7, centered 81-day average and definitive Kp; hindcast'
        nc.time_standard='UTC';nc.hindcast='true'
        nc.kp_time_convention='API interval starts 00,03,...21 UT; TIE-GCM centers 01:30,...22:30 UT'
        nc.data_source_url='https://kp.gfz.de/en/data'
    with Dataset(path) as nc:
        assert np.array_equal(nc['year_day'][:],yd)
        assert nc['kp'].dimensions==('ndays','nkp') and nc['kp'].dtype==np.dtype('float64')
        assert np.array_equal(nc['kp'][:],ks) and np.array_equal(nc['f107a'][:],average)
    audit={'file':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'ndays':14,'kp_count':112,'valid_model_dates':['2023-03-14','2023-03-23'],'static_roundtrip_pass':True,'actual_model_consumer_test':False,'f107d_range':[min(daily),max(daily)],'f107a_range':[min(average),max(average)],'kp_range':[float(ks.min()),float(ks.max())],'solar_quality':'API has no per-record status; finite/nonmissing/continuous verified, original observatory quality not independently certified','sources':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (fp,kp,ep)},'hindcast':True}
    (ROOT/'logs/tiegcm2023_driver_audit.json').write_text(json.dumps(audit,indent=2))
    print(json.dumps(audit,indent=2))
if __name__=='__main__':main()
