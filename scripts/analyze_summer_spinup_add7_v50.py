"""Future read-only native analysis using absolute UTC and the frozen V48 metric functions."""
import argparse
import csv
from datetime import timedelta, datetime
import json
import re

import numpy as np
from netCDF4 import Dataset, num2date

import preflight_summer_spinup_add7_v50 as offline
import analyze_summer_seed_sensitivity_v46 as science
import prepare_summer_gpi_extended_v50 as gpi

ROOT,OUT=gpi.ROOT,gpi.OUT
OLD_START=gpi.old.START
LATE_START=gpi.old.START+timedelta(hours=360)
LATE_UTC=[LATE_START+timedelta(hours=i) for i in range(25)]
RESULT=OUT/'future_analysis'
OLD_RESULTS=ROOT/'experiments/thermosphere_summer_seed_recovery_v47/comparison'


def utc_hour(origin, instant):
    gpi.require(origin.tzinfo is not None and instant.tzinfo is not None,
                'Timezone-aware UTC required')
    gpi.require(origin.utcoffset()==instant.utcoffset()==timedelta(0),'UTC required')
    seconds=(instant-origin).total_seconds()
    gpi.require(seconds>0 and seconds%3600==0 and instant<=gpi.STOP,'Invalid calendar or cold echo')
    return int(seconds//3600)


def alignment(instant):
    new=utc_hour(gpi.START,instant)
    old=utc_hour(OLD_START,instant) if instant>OLD_START else None
    return new,old


def coordinate(origin,instant,claimed_hour=None):
    hour=utc_hour(origin,instant)
    gpi.require(claimed_hour is None or hour==claimed_hour,'Hour belongs to different experiment or UTC')
    volume,index=divmod(hour-1,24)
    return volume+1,index


def read_frame(runs,instant,*,independent=False):
    volume,index=coordinate(gpi.START,instant)
    expected=instant.replace(tzinfo=None).isoformat()
    frames=[]
    native_grid=[]
    for root in runs:
        with Dataset(root/f'secondary_{volume:03d}.nc') as n:
            time=n['time']
            gpi.require(num2date(time[index],time.units).isoformat()==expected,'Wrong absolute UTC')
            fields={}
            for key in (*science.KEYS,'ZG'):
                v=n[key]
                gpi.require(v.units==('cm' if key=='ZG' else science.UNITS[key]) and
                    v.dimensions==('time','ilev' if key in ('DEN','ZG') else 'lev','lat','lon'),'Field schema')
                if independent:
                    v.set_auto_mask(False)
                    data=np.asarray(v[index],np.float64)
                    for tag in ('_FillValue','missing_value'):
                        if tag in v.ncattrs():
                            data[np.isin(data,np.asarray(v.getncattr(tag),dtype=v.dtype))]=np.nan
                else:
                    data=np.ma.asarray(v[index],dtype=float).filled(np.nan)
                gpi.require(not np.isinf(data).any(),'Infinite field')
                data[abs(data)>1e30]=np.nan
                fields[key]=data
            native_grid.append([np.asarray(n[x][:]) for x in ('lat','lon','lev','ilev')])
            frames.append(fields)
    gpi.require(all(np.array_equal(x,y) for x,y in zip(*native_grid)),'Different grids')
    a,b=frames
    a['WIND_VECTOR']=np.zeros_like(a['UN'])
    b['WIND_VECTOR']=np.hypot(b['UN']-a['UN'],b['VN']-a['VN'])
    return a,b,native_grid[0]


def evidence():
    config=json.loads((OUT/'configuration.json').read_text())
    ids=[]
    roots=[]
    for i,name in enumerate(offline.RUNS):
        run=OUT/name
        gpi.require(run.is_dir() and run.resolve()==run,'Future model output unavailable')
        receipt=json.loads((run/'engineering_receipt.json').read_text())
        gpi.require(receipt['engineering']=='PASS' and receipt['plan_sha256']==offline.v47.sha(offline.PLAN)
              and receipt['steps']==33120 and receipt['role']=='AB'[i] and
              receipt['secondary_hours']==552 and receipt['final_model_UTC']==gpi.STOP.isoformat() and
              receipt['rank_exit']==[0]*4 and receipt['parent_exit']==0 and
              receipt['model_sha256']==config['model']['SHA256'] and receipt['gpi_sha256']==config['GPI']['SHA256'] and
              receipt['input_sha256']==config['config_sha'][name+'.namelist'] and
              receipt['source_sha256']==config['seeds'][i]['SHA256'],'Invalid engineering receipt')
        required={f'{k}_{j:03d}.nc' for k,num in (('primary',24),('secondary',23)) for j in range(1,num+1)}
        gpi.require(set(receipt['outputs_sha256'])==required,'Future NetCDF inventory')
        for x,h in receipt['outputs_sha256'].items():
            gpi.require((run/x).resolve()==run/x and offline.v47.sha(run/x)==h,'Future data SHA mismatch')
        ids.append(receipt['run_id'])
        roots.append(run)
    prior=gpi.pin(ROOT/'experiments/thermosphere_summer_seed_execution_v48/result.json')
    forbidden={prior['original_A_id'],prior['original_B_failure_id'],prior['run']['run_id']}
    gpi.require(len(set(ids))==2 and not (set(ids)&forbidden) and
                all(re.fullmatch('[0-9a-f]{32}',x) for x in ids),'Future identity')
    return roots,ids


def samples():
    same_utc={OLD_START+timedelta(hours=h) for h in science.HOURS}
    ages={gpi.START+timedelta(days=n) for n in (1,3,7,14,21)}
    return sorted(same_utc|ages)


def main():
    runs,ids=evidence()
    gpi.require(RESULT.resolve()==RESULT and not RESULT.exists(),'Preserve original analysis')
    RESULT.mkdir()
    rules=json.loads(science.RULES.read_text())
    hourly=[]; heights=[]; native_gates=[]; height_gates=[]
    late={utc_hour(gpi.START,t) for t in LATE_UTC}
    for t in samples():
        new,old=alignment(t)
        a,b,grid=read_frame(runs,t)
        lat=grid[0]
        w=np.cos(np.deg2rad(lat))
        for region,(low,high) in rules['latitude_regions'].items():
            m=(lat>=low)&(lat<=high)
            weights=w[None,m,None]
            for k in (*science.KEYS,'WIND_VECTOR'):
                x,y=a[k][:,m],b[k][:,m]
                hourly.append(dict(UTC=t.isoformat(),hour_V50=new,hour_V48=old,
                    variable=k,region=region,units=science.UNITS[k],
                    **science.metrics(x,y,weights,1e-8 if k in science.COMPOSITION else 0,k=='DEN')))
                science.gate_rows(native_gates,late,new,k,region,x,y)
            for h in rules['common_native_ZG_heights_km']:
                x,y=[science.interpolation(h,z['ZG'],z['DEN'])[m] for z in (a,b)]
                heights.append(dict(UTC=t.isoformat(),hour_V50=new,hour_V48=old,height_km=h,region=region,
                    **science.metrics(x,y,weights[0],0,True)))
                prev=len(height_gates)
                science.gate_rows(height_gates,late,new,'DEN',region,x[None],y[None])
                if len(height_gates)>prev:height_gates[-1]['height_km']=h
    for name,data in [('hourly',hourly),('height',heights),('gates',native_gates),('height_gates',height_gates)]:
        science.csv_save(RESULT/f'{name}.csv',data)
    with (OLD_RESULTS/'hourly.csv').open() as f:
        prior={(int(row['hour']),row['variable'],row['region']):row for row in csv.DictReader(f)}
    comparable=[x for x in hourly if (x['hour_V48'],x['variable'],x['region']) in prior]
    science.csv_save(RESULT/'same_UTC.csv',[dict(UTC=x['UTC'],hour_V48=x['hour_V48'],hour_V50=x['hour_V50'],
        variable=x['variable'],region=x['region'],V48_P95=prior[x['hour_V48'],x['variable'],x['region']]['relative_P95'],
        V50_P95=x['relative_P95'],V48_RMSE=prior[x['hour_V48'],x['variable'],x['region']]['RMSE'],
        V50_RMSE=x['RMSE']) for x in comparable])
    trends={}
    for h in rules['common_native_ZG_heights_km']:
        values=[x['log_RMSE'] for x in heights if x['height_km']==h and
                x['region']=='global' and x['hour_V50'] in late]
        trends[str(h)]=float(np.polyfit(np.arange(25),values,1)[0]) if len(values)==25 and None not in values else None
    valid=[x for x in native_gates+height_gates if x['n']]
    den=[x for x in valid if x['variable']=='DEN']
    full_fail=sum(not x['passed'] for x in valid)
    no_growth=all(x is not None and x<=0 for x in trends.values())
    growth=any(x is not None and x>0 for x in trends.values())
    full='FAIL' if full_fail or growth else 'LIMITED_PASS' if valid and no_growth else 'INCONCLUSIVE'
    density='FAIL' if any(not x['passed'] for x in den) or growth else 'SUPPORTED' if den and no_growth else 'INCONCLUSIVE'
    with (RESULT/'summary.json').open('x') as f:
        json.dump(dict(FULL_STATE_SEED_SENSITIVITY=full,DENSITY_LIMITED_INSENSITIVITY=density,
            full_failed_cells=full_fail,lag_mapping='V50=V48+168h on common physical UTC',run_ids=ids,
            empty_cells=len(native_gates)+len(height_gates)-len(valid),trends=trends),f,indent=2)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.parse_args()
    main()
