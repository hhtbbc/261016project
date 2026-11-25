"""Read-only V46 analysis using the historical A14/B14 weighting and thresholds."""
import csv
import json
from datetime import timedelta
from pathlib import Path

from netCDF4 import Dataset
import numpy as np

from run_summer_seed_sensitivity_v46 import A, B, OUT, ROOT, START, load, require, sha

KEYS = ('DEN', 'TN', 'UN', 'VN', 'O1', 'O2', 'N2', 'HE')
COMPOSITION = ('O1', 'O2', 'N2', 'HE')
HOURS = sorted({24,72,168,336,*range(312,361),*range(361,385)})
UNITS = dict(DEN='g/cm3', TN='K', UN='cm/s', VN='cm/s', WIND_VECTOR='cm/s',
             **dict.fromkeys(COMPOSITION,'mmr'))
RULES = ROOT/'experiments/tiegcm_2021_spinup_14day_v1/frozen_comparison_rules.json'
RESULT = OUT/'comparison'
GATE = {'DEN':(.05,0), 'TN':(10,None), 'WIND_VECTOR':(2000,None),
        **{k:(.05,1e-8) for k in COMPOSITION}}


def csv_save(path, rows):
    with path.open('x',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read(hour):
    group, index = divmod(hour-1,24)
    pair = []
    schemas = []
    for name in (A,B):
        with Dataset(OUT/name/f'secondary_{group+1:03d}.nc') as n:
            day = START + timedelta(hours=hour)
            require(np.array_equal(n['mtime'][index],[day.timetuple().tm_yday,day.hour,0]), 'UTC mismatch')
            fields = {}
            schema = {}
            for key in (*KEYS,'ZG'):
                v = n[key]
                expected = ('time','ilev' if key in ('DEN','ZG') else 'lev','lat','lon')
                require(v.dimensions == expected and v.units == ('cm' if key=='ZG' else UNITS[key]), f'{key} schema mismatch')
                schema[key] = (v.dimensions, v.units)
                fields[key] = np.ma.asarray(v[index],dtype=float).filled(np.nan)
                fields[key][abs(fields[key])>1e30] = np.nan
            fields['lat'] = np.asarray(n['lat'][:])
            fields['lon'] = np.asarray(n['lon'][:])
            pair.append(fields)
            schemas.append(schema)
    require(schemas[0]==schemas[1] and all(np.array_equal(pair[0][k],pair[1][k]) for k in ('lat','lon')), 'Paired grid mismatch')
    return pair


def interpolation(height, zg, den):
    # ZG is cm, linear interpolation in log(DEN) within each native column.
    z = height*1e5
    i = np.clip((zg<=z).sum(axis=0)-1,0,zg.shape[0]-2)
    take = lambda x,j: np.take_along_axis(x,j[None],axis=0)[0]
    z0,z1 = take(zg,i),take(zg,i+1)
    x0,x1 = take(den,i),take(den,i+1)
    f = (z-z0)/(z1-z0)
    values = np.exp(np.log(x0)+f*(np.log(x1)-np.log(x0)))
    return np.where((z>=z0)&(z<=z1),values,np.nan)


def percentile(values, weights):
    index = np.argsort(values)
    cumulative = np.cumsum(weights[index])
    return float(np.interp(.95,cumulative/cumulative[-1],values[index]))


def metrics(a,b,w,floor,density=False):
    mask = np.isfinite(a)&np.isfinite(b)
    if not mask.any():
        return dict(n=0,coverage=0.,relative_n=0,bias=None,MAE=None,RMSE=None,max_abs=None,abs_P95=None,
                    relative_mean=None,relative_median=None,relative_P95=None,log_RMSE=None)
    weight=np.broadcast_to(w,a.shape)[mask]
    base=a[mask]
    comparison=b[mask]
    delta=comparison-base
    relative=abs(base)>floor
    rr=abs(delta[relative]/base[relative])
    w_r=weight[relative]
    return dict(n=int(mask.sum()),coverage=float(mask.mean()),relative_n=len(rr),
                bias=float(np.average(delta,weights=weight)),MAE=float(np.average(abs(delta),weights=weight)),
                RMSE=float(np.sqrt(np.average(delta**2,weights=weight))),max_abs=float(abs(delta).max()),
                abs_P95=percentile(abs(delta),weight),relative_mean=float(np.average(rr,weights=w_r)) if len(rr) else None,
                relative_median=float(np.median(rr)) if len(rr) else None,relative_P95=percentile(rr,w_r) if len(rr) else None,
                log_RMSE=float(np.sqrt(np.average(np.log(comparison/base)**2,weights=weight))) if density else None)


def gate_rows(rows, hours, hour, variable, region, a, b):
    if hour not in hours or variable not in GATE:
        return
    limit,floor=GATE[variable]
    mask=np.isfinite(a)&np.isfinite(b)
    delta=abs(b-a)
    if floor is not None:
        mask &= abs(a)>floor
        delta=np.divide(delta,abs(a),out=np.zeros_like(delta),where=mask)
    for i,(err,valid) in enumerate(zip(delta,mask)):
        count=int(valid.sum())
        if count:
            fraction=float(np.mean(err[valid]<limit))
            rows.append(dict(hour=hour,variable=variable,region=region,level=i,n=count,
                             passed_fraction=fraction,passed=fraction>=.95))
        else:
            rows.append(dict(hour=hour,variable=variable,region=region,level=i,n=0,
                             passed_fraction=None,passed=None))


def main():
    receipts=[load(OUT/f'{group}_acceptance.json') for group in (A,B)]
    for name,receipt in zip((A,B),receipts):
        require(receipt['overall']=='PASS', 'Engineering acceptance absent')
        for row in receipt['files']:
            require(sha(OUT/name/row['file'])==row['SHA256'], 'Output SHA mismatch')
    require(not RESULT.exists(),'Preserve original comparison')
    RESULT.mkdir()
    rules=load(RULES)
    require([rules[k] for k in ('density_relative_limit','TN_absolute_limit_K','horizontal_wind_vector_limit_m_s',
            'composition_relative_limit','minimum_fraction_within_limits','trace_reference_floor_mmr')]
            == [.05,10,20,.05,.95,1e-8], 'Historical threshold drift')
    rows=[]; levels=[]; gates=[]; heights=[]; height_gates=[]; maps=[]; local=[]
    final=range(360,385)
    for hour in HOURS:
        a,b=read(hour)
        lat=a['lat']
        w=np.cos(np.deg2rad(lat))
        regions={name:(lat>=lo)&(lat<=hi) for name,(lo,hi) in rules['latitude_regions'].items()}
        stamp=(START+timedelta(hours=hour)).isoformat()+'Z'
        a['WIND_VECTOR']=np.zeros_like(a['UN'])
        b['WIND_VECTOR']=np.hypot(b['UN']-a['UN'],b['VN']-a['VN'])
        for key in (*KEYS,'WIND_VECTOR'):
            for region,mask in regions.items():
                x,y=a[key][:,mask,:],b[key][:,mask,:]
                weights=w[None,mask,None]
                floor=1e-8 if key in COMPOSITION else 0.
                rows.append(dict(hour=hour,UTC=stamp,variable=key,units=UNITS[key],region=region,
                                 **metrics(x,y,weights,floor,key=='DEN')))
                gate_rows(gates,final,hour,key,region,x,y)
                if hour in (24,72,168,336,384):
                    for lev in range(len(x)):
                        levels.append(dict(hour=hour,UTC=stamp,variable=key,units=UNITS[key],region=region,
                             level_type='ilev' if key=='DEN' else 'lev',level=lev,
                             **metrics(x[lev],y[lev],weights[0],floor,key=='DEN')))
        for h in rules['common_native_ZG_heights_km']:
            x,y=[interpolation(h,data['ZG'],data['DEN']) for data in (a,b)]
            for region,mask in regions.items():
                heights.append(dict(hour=hour,UTC=stamp,height_km=h,region=region,units='g/cm3',
                                    **metrics(x[mask],y[mask],w[mask,None],0,True)))
                first=len(height_gates)
                gate_rows(height_gates,final,hour,'DEN',region,x[None,mask],y[None,mask])
                if len(height_gates)>first:
                    height_gates[-1]['height_km']=h
            if hour==336:
                for i,j in zip(*np.where(np.isfinite(x)&np.isfinite(y))):
                    maps.append(dict(height_km=h,latitude=float(lat[i]),longitude=float(a['lon'][j]),
                                     signed_relative=float((y[i,j]-x[i,j])/x[i,j])))
                solar_hour=((a['lon']/15)+(START+timedelta(hours=hour)).hour)%24
                for lt in range(0,24,6):
                    use=(solar_hour>=lt)&(solar_hour<lt+6)
                    local.append(dict(height_km=h,LT_start=lt,LT_stop=lt+6,
                                      **metrics(x[:,use],y[:,use],w[:,None],0,True)))
    trends=[]
    for h in rules['common_native_ZG_heights_km']:
        series=[r['log_RMSE'] for r in heights if r['height_km']==h and r['region']=='global' and r['hour'] in final]
        slope=float(np.polyfit(np.arange(len(series)),series,1)[0]) if None not in series and len(series)==25 else None
        trends.append(dict(height_km=h,last24h_log_RMSE_slope_per_hour=slope,no_growth=slope is not None and slope<=0))
    for name,data in [('hourly',rows),('levels',levels),('gates',gates),('height',heights),
                      ('height_gates',height_gates),('day14_map',maps),('day14_localtime',local),('trends',trends)]:
        csv_save(RESULT/f'{name}.csv',data)
    evaluated=[r for r in gates+height_gates if r['n']]
    adequate=all(r['log_RMSE'] is not None for r in heights if r['region']=='global')
    failed=sum(not r['passed'] for r in evaluated)
    status=('SEED_SENSITIVITY_FAIL' if failed or any(r['last24h_log_RMSE_slope_per_hour'] is not None and not r['no_growth'] for r in trends)
            else 'SEED_SENSITIVITY_LIMITED_PASS' if adequate and evaluated and all(r['no_growth'] for r in trends)
            else 'SEED_SENSITIVITY_INCONCLUSIVE')
    with (RESULT/'summary.json').open('x') as f:
        json.dump(dict(status=status, hours=HOURS, evaluated_cells=len(evaluated), failed_cells=failed,
            excluded_empty_cells=len(gates)+len(height_gates)-len(evaluated), trend=trends,
            rules_SHA256=sha(RULES), unit_note='Native units; wind vector threshold 2000 cm/s = 20 m/s.',
            reference='mareqx', no_extrapolation=True, no_observation_access=True),f,indent=2)


if __name__=='__main__':
    main()
