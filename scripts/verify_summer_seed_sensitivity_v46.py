"""Verify durable process evidence and scientific CSVs independently from the main analyzer."""
import csv
import json
from datetime import datetime,timedelta
from pathlib import Path
import math
import re

import numpy as np
from netCDF4 import Dataset, num2date

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'experiments/thermosphere_summer_seed_sensitivity_v46'
RESULT=OUT/'comparison'
START=datetime(2022,6,7)
RUNS=('run_A_mareqx','run_B_junsol')
FIELDS=('DEN','TN','UN','VN','O1','O2','N2','HE')
COMPOSITION=set(FIELDS[4:])
RULES=ROOT/'experiments/tiegcm_2021_spinup_14day_v1/frozen_comparison_rules.json'


def hash_file(path):
    import hashlib
    with path.open('rb') as f:
        d=hashlib.sha256()
        for block in iter(lambda:f.read(1<<20),b''):
            d.update(block)
    return d.hexdigest()


def read_table(name):
    with (RESULT/f'{name}.csv').open() as f:
        return list(csv.DictReader(f))


def quantile(v,w):
    if not len(v):
        return None
    order=v.argsort(kind='stable')
    cumulative=np.add.accumulate(w[order])
    target=.95*cumulative[-1]
    idx=np.searchsorted(cumulative,target)
    if idx==0:
        return v[order[0]]
    lo,hi=cumulative[idx-1:idx+1]
    a,b=v[order[idx-1:idx+1]]
    return a+(b-a)*(target-lo)/(hi-lo)


def row_metrics(x,y,w,floor,density):
    valid=np.isfinite(x)&np.isfinite(y)
    x,y,w=x[valid],y[valid],np.broadcast_to(w,valid.shape)[valid]
    vals={'n':len(x),'coverage':valid.mean(),'relative_n':0}
    measures=('bias','MAE','RMSE','max_abs','abs_P95','relative_mean','relative_median','relative_P95','log_RMSE')
    vals.update(dict.fromkeys(measures))
    if len(x):
        d=y-x
        absd=abs(d)
        relative=abs(x)>floor
        rv=abs(d[relative]/x[relative])
        rw=w[relative]
        total=w.sum()
        vals.update(relative_n=len(rv),bias=np.sum(w*d)/total,MAE=np.sum(w*absd)/total,
            RMSE=np.sqrt(np.sum(w*d*d)/total),max_abs=absd.max(),abs_P95=quantile(absd,w),
            relative_mean=np.sum(rv*rw)/rw.sum() if len(rv) else None,
            relative_median=np.median(rv) if len(rv) else None,relative_P95=quantile(rv,rw),
            log_RMSE=np.sqrt(np.sum(w*np.log(y/x)**2)/total) if density else None)
    return vals


def frame(hour):
    volume, index=divmod(hour-1,24)
    result=[]
    for run in RUNS:
        with Dataset(OUT/run/f'secondary_{volume+1:03d}.nc') as nc:
            time=nc['time']
            assert num2date(time[index],time.units).isoformat()==(START+timedelta(hours=hour)).isoformat()
            fields={}
            for key in (*FIELDS,'ZG'):
                var=nc[key]
                assert var.dimensions[1]==('ilev' if key in ('DEN','ZG') else 'lev')
                assert var.units==dict(DEN='g/cm3',ZG='cm',TN='K',UN='cm/s',VN='cm/s').get(key,'mmr')
                raw=var[index]
                fields[key]=np.ma.asarray(raw,dtype='f8').filled(np.nan)
                fields[key][abs(fields[key])>1e30]=np.nan
            fields['lat']=np.asarray(nc['lat'][:])
            result.append(fields)
    x,y=result
    x['WIND_VECTOR']=np.zeros_like(x['UN'])
    y['WIND_VECTOR']=np.sqrt((y['UN']-x['UN'])**2+(y['VN']-x['VN'])**2)
    return result


def interpolate_columns(f,h):
    z=f['ZG'].reshape(f['ZG'].shape[0],-1).T
    d=np.log(f['DEN'].reshape(f['DEN'].shape[0],-1).T)
    return np.exp([np.interp(h*100000.,a,b,left=np.nan,right=np.nan) for a,b in zip(z,d)]).reshape(f['DEN'].shape[1:])


def engineering():
    plan=json.loads((OUT/'frozen_pair.json').read_text())
    a,b=[plan['protocols'][k] for k in RUNS]
    assert a['GPI']==b['GPI'] and a['executable']==b['executable'] and a['mpirun']==b['mpirun']
    assert [x.split('=')[0].strip() for x,y in zip(a['input_text'].splitlines(),b['input_text'].splitlines(),strict=True)
            if x!=y]==['SOURCE','SOURCE_START']
    infos=[]
    raw_times=[]
    for name in RUNS:
        p=plan['protocols'][name]
        run=OUT/name
        claim=json.loads((OUT/f'{name}_claim.json').read_text())
        status=json.loads((run/'status.json').read_text())
        assert status['returncode']==0 and status['cleanup_verified'] and not status['gaps']
        events=[json.loads(line) for line in (run/'events.jsonl').read_text().splitlines()]
        assert sum(e['event']=='launched' for e in events)==1
        assert [e['returncode'] for e in events if e['event']=='child_wait_final']==[0]
        assert hash_file(run/'input.inp')==p['input']['SHA256']==claim['input_sha256']
        for key in ('source','GPI','executable','mpirun'):
            assert hash_file(ROOT/p[key]['path'])==p[key]['SHA256']
        ranks=[]
        for idx in range(4):
            receipt=json.loads((run/f'rank_{idx:03d}_exit.json').read_text())
            assert receipt['run_id']==claim['run_id'] and receipt['rank']==idx and receipt['returncode']==0
            assert receipt['input_SHA256']==p['input']['SHA256'] and receipt['error'] is None
            log=(run/f'rank_{idx:03d}.log').read_text()
            step=[tuple(map(int,m)) for m in re.findall(r'Step\s+(\d+) of\s+(\d+) mtime=\s*(\d+)\s+(\d+)\s+(\d+)',log)]
            assert len(step)==2304 and len(re.findall(r'(?m)^NORMAL EXIT\s*$',log))==1
            for i,(elapsed,total,day,hour,minute) in enumerate(step,1):
                t=START+timedelta(minutes=elapsed)
                assert elapsed==i*10 and total==23040 and [day,hour,minute]==[t.timetuple().tm_yday,t.hour,t.minute]
            ranks.append({'rank':idx,'steps':step[-1][0],'start_unix':receipt['started_unix'],'end_unix':receipt['ended_unix']})
        audit=json.loads((OUT/f'{name}_acceptance.json').read_text())
        seen={'primary':[],'secondary':[]}
        for kind,num,records in [('primary',17,1),('secondary',16,24)]:
            for index in range(1,num+1):
                file=f'{kind}_{index:03d}.nc'
                path=run/file
                expected=next(row for row in audit['files'] if row['file']==file)
                assert hash_file(path)==expected['SHA256'] and path.stat().st_size==expected['bytes']
                with Dataset(path) as n:
                    time=n['time']
                    dates=[t.isoformat() for t in num2date(time[:],time.units)]
                    assert len(dates)==records and n.history_type==kind
                    seen[kind].extend(dates)
        assert seen['primary']==[(START+timedelta(days=d)).isoformat() for d in range(17)]
        assert seen['secondary']==[(START+timedelta(hours=h)).isoformat() for h in range(1,385)]
        raw_times.append(seen)
        infos.append(dict(run=name,run_id=claim['run_id'],parent_exit=0,ranks=ranks,netcdf_verified=33))
    assert raw_times[0]==raw_times[1] and infos[0]['run_id']!=infos[1]['run_id']
    return infos


def main():
    sources=engineering()
    rules=json.loads(RULES.read_text())
    blocks={}
    tables=['hourly','levels','height','gates','height_gates']
    for table in tables:
        for row in read_table(table):
            blocks.setdefault(int(row['hour']),[]).append((table,row))
    count=0
    max_relative=0.
    trend={}
    for hour,rows in sorted(blocks.items()):
        a,b=frame(hour)
        lat=a['lat']
        cosine=np.cos(lat*math.pi/180.)
        heights={}
        for table,row in rows:
            region=row['region']
            lo,hi=rules['latitude_regions'][region]
            sel=(lat>=lo)&(lat<=hi)
            is_height=table in ('height','height_gates')
            key='DEN' if is_height else row['variable']
            if is_height:
                h=int(row['height_km'])
                if h not in heights:
                    heights[h]=tuple(interpolate_columns(f,h) for f in (a,b))
                va,vb=heights[h]
                x,y=va[sel],vb[sel]
            else:
                x,y=a[key][:,sel],b[key][:,sel]
                if table in ('levels','gates'):
                    x,y=x[int(row['level'])],y[int(row['level'])]
            if table.endswith('gates'):
                valid=np.isfinite(x)&np.isfinite(y)
                d=abs(y-x)
                if key in COMPOSITION or key=='DEN':
                    valid &= abs(x)>(1e-8 if key in COMPOSITION else 0.)
                    d=d[valid]/abs(x[valid])
                    limit=.05
                else:
                    d=d[valid]
                    limit=10 if key=='TN' else 2000
                n=len(d)
                assert n==int(row['n']), (table,row)
                if n:
                    f=np.count_nonzero(d<limit)/n
                    assert f==float(row['passed_fraction']) and str(f>=.95)==row['passed'],(table,row)
                else:
                    assert row['passed']==row['passed_fraction']==''
                count+=3
                continue
            stats=row_metrics(x,y,cosine[sel,None],1e-8 if key in COMPOSITION else 0.,key=='DEN')
            for col,v in stats.items():
                old=row[col]
                if v is None:
                    assert old=='',(table,row,col)
                else:
                    assert old!='' and math.isclose(v,float(old),rel_tol=2e-10,abs_tol=1e-12 if key!='DEN' else 1e-26),(table,row,col,v)
                    if float(old) and v:
                        max_relative=max(max_relative,abs(v/float(old)-1))
                count+=1
            if is_height and region=='global' and hour>=360:
                trend.setdefault(h,[]).append(stats['log_RMSE'])
    for row in read_table('trends'):
        v=np.array(trend[int(row['height_km'])],float)
        x=np.arange(len(v))-np.arange(len(v)).mean()
        if np.isfinite(v).all():
            slope=np.dot(x,v-v.mean())/np.dot(x,x)
            assert math.isclose(slope,float(row['last24h_log_RMSE_slope_per_hour']),rel_tol=1e-8,abs_tol=1e-14)
            assert str(slope<=0)==row['no_growth']
        else:
            assert row['last24h_log_RMSE_slope_per_hour']==''
        count+=2
    with (RESULT/'independent.json').open('x') as f:
        json.dump({'verified':True,'independent_checks':count,'max_numeric_relative_difference_nonzero':max_relative,
                   'run_receipts':sources,'tolerance':'rtol=2e-10; atol=1e-26 DEN or 1e-12 other native units',
                   'no_swarm_density_read':True},f,indent=2)


if __name__=='__main__':
    main()
