"""Apply V51's fixed internal sensitivity contract to the new 2021 seed pair."""
from collections import Counter
from datetime import datetime,timedelta
import json
import math
import os
from pathlib import Path

import numpy as np
from netCDF4 import Dataset,num2date

import analyze_summer_spinup_add7_v50 as v51
import verify_summer_spinup_add7_v50 as v51_verify
import verify_summer_seed_sensitivity_v46 as independent
from run_summer_2021_v67 import OUT,PLAN,V51,sha,load,require,at,ROOT,write_once
from run_native_density_baselines_v59 import table,read_csv

RULES=v51.science.RULES
S=v51.science
T0=at(PLAN['start'])
END=at(PLAN['end'])
FIELDS=(*S.KEYS,'ZG')
LATE={528+i for i in range(25)}
RULE_SHA='5ea4e27db746d698f738b974fbf12ba81b09d186d94c0a9376aa2640517bb52b'


def frame(arms,t,scope):
    frames=[]
    grids=[]
    for r in sorted(arms,key=lambda r:r['arm']):
        path=ROOT/r['directory']/r['file']
        require(path.resolve()==path and path.stat().st_mode&0o777==0o400 and
                (r['arm'],r['file'],int(r['record']),r['UTC']) in scope,'DEN or field scope')
        pos=int(r['record'])
        with Dataset(path) as n:
            time=n['time']
            require(num2date(time[pos],time.units).isoformat()==t.isoformat(),'Exact UTC')
            a={}
            for k in FIELDS:
                v=n[k]
                require(v.units==('cm' if k=='ZG' else S.UNITS[k]) and
                        v.dimensions==('time','ilev' if k in ('ZG','DEN') else 'lev','lat','lon'),
                        'Native field identity')
                v.set_auto_maskandscale(False)
                orig=np.asarray(v[pos])
                bad=abs(orig)>1e30
                for f in ('missing_value','_FillValue'):
                    if f in v.ncattrs():
                        bad|=np.isin(orig,np.asarray(v.getncattr(f),dtype=v.dtype))
                a[k]=np.where(bad,np.nan,orig).astype(float)
                require(not np.isinf(a[k]).any(),'Infinite native field')
            grids.append([np.asarray(n[k][:]) for k in ('lat','lon','lev','ilev')])
            frames.append(a)
    require(len(frames)==2 and all(np.array_equal(x,y) for x,y in zip(*grids)),'Grid mismatch')
    a,b=frames
    for p in frames:
        den,zg=p['DEN'],p['ZG']
        require(np.all(den[np.isfinite(den)]>0) and
                not np.any(np.diff(zg,axis=0)[np.isfinite(np.diff(zg,axis=0))]<=0),'DEN positivity or ZG monotonicity')
    a['WIND_VECTOR']=np.zeros_like(a['UN'])
    b['WIND_VECTOR']=np.hypot(b['UN']-a['UN'],b['VN']-a['VN'])
    return a,b,grids[0][0]


def compare_stats(primary,secondary,variable):
    for k,val in secondary.items():
        actual=primary[k]
        require(actual is val if val is None else actual is not None and
                math.isclose(actual,val,rel_tol=2e-10,abs_tol=1e-26 if variable=='DEN' else 1e-12),
                'Independent numerical statistic '+k)


def independent_gate(row,x,y):
    k=row['variable']
    lim,floor=S.GATE[k]
    valid=np.isfinite(x)&np.isfinite(y)
    if floor is not None:
        valid&=abs(x)>floor
    diff=np.abs(y[valid]-x[valid])
    if floor is not None:
        diff/=abs(x[valid])
    n=int(valid.sum())
    require(row['n']==n,'Independent gate count')
    if n:
        p=np.count_nonzero(diff<lim)/n
        require(p==row['passed_fraction'] and bool(p>=.95)==row['passed'],'Independent gate result')
    else:
        require(row['passed_fraction'] is None and row['passed'] is None,'Empty gate mismatch')


def main():
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    require(OUT.resolve()==OUT and sha(RULES)==RULE_SHA,'Frozen V51 rules')
    rec=load(OUT/'summer_run_receipts.json')
    require(set(rec)=={'A1','A2'} and all(r['engineering']=='PASS' for r in rec.values()) and
            len({r['run_id'] for r in rec.values()})==2,'Both independent verified integrations required')
    rules=load(RULES)
    # Same month/day and hour as V51, with the identical warm age and late-window rules.
    wanted={t.replace(year=2021).replace(tzinfo=None) for t in v51.samples()}
    time_index=read_csv(OUT/'native_time_index.csv')
    checked={r['UTC']:[s for s in time_index if s['UTC']==r['UTC']] for r in time_index
             if at(r['UTC']) in wanted}
    require(set(map(at,checked))==wanted and all(len(p)==2 for p in checked.values()),'V51 paired read scope')
    frozen=[r | {'fields':';'.join(FIELDS),'role':'SAME_YEAR_INTERNAL_PHYSICS_ONLY'}
            for t,p in sorted(checked.items()) for r in p]
    inventory={ (r['arm'],r['file']):r for r in read_csv(OUT/'native_output_inventory.csv') }
    for k in {(r['arm'],r['file']) for r in frozen}:
        r=inventory[k]
        path=ROOT/r['directory']/r['file']
        require(path.resolve()==path and sha(path)==r['sha256'],'Authorized read volume identity')
    table(OUT/'initial_condition_allowed_record_manifest.csv',frozen)
    write_once(OUT/'initial_condition_read_authorization.json',dict(fields=FIELDS,UTC_hours=len(wanted),
        exact_rows_SHA256=sha(OUT/'initial_condition_allowed_record_manifest.csv'),
        Swarm_observations=False,physics_only=True,training=False,prior_2022_science_unchanged=True,
        thresholds_sha256=RULE_SHA))
    scope={(r['arm'],r['file'],int(r['record']),r['UTC']) for r in frozen}
    raw=[]; heights=[]; gates=[]; hg=[]; layer=[]; checks=0
    trend={h:[] for h in rules['common_native_ZG_heights_km']}
    for t,pair in sorted(checked.items()):
        u=at(t)
        age=int((u-T0).total_seconds()/3600)
        require(T0<u<=END,'Warm sample')
        a,b,lat=frame(pair,u,scope)
        w=np.cos(np.deg2rad(lat))
        for name,(lo,hi) in rules['latitude_regions'].items():
            keep=(lat>=lo)&(lat<=hi)
            weight=w[None,keep,None]
            for k in (*S.KEYS,'WIND_VECTOR','ZG'):
                x,y=a[k][:,keep],b[k][:,keep]
                ms=S.metrics(x,y,weight,1e-8 if k in S.COMPOSITION else 0,k=='DEN')
                raw.append(dict(UTC=t,hour=age,variable=k,region=name,units='cm' if k=='ZG' else S.UNITS[k],**ms))
                compare_stats(ms,v51_verify.verified_stats(x,y,weight,k),k)
                checks+=1
                if age in LATE:
                    prev=len(gates)
                    S.gate_rows(gates,LATE,age,k,name,x,y)
                    for row in gates[prev:]:
                        j=row['level']
                        independent_gate(row,x[j],y[j])
                        checks+=1
            for h in trend:
                x,y=[S.interpolation(h,p['ZG'],p['DEN'])[keep] for p in (a,b)]
                xi,yi=[independent.interpolate_columns(p,h)[keep] for p in (a,b)]
                require(np.allclose(x,xi,rtol=2e-12,atol=1e-30,equal_nan=True) and
                        np.allclose(y,yi,rtol=2e-12,atol=1e-30,equal_nan=True),'Independent fixed-height reconstruction')
                ms=S.metrics(x,y,weight[0],0,True)
                compare_stats(ms,v51_verify.verified_stats(xi,yi,weight[0],'DEN'),'DEN')
                heights.append(dict(UTC=t,hour=age,height_km=h,region=name,**ms))
                checks+=1
                if age in LATE:
                    S.gate_rows(hg,LATE,age,'DEN',name,x[None],y[None])
                    hg[-1]['height_km']=h
                    independent_gate(hg[-1],xi,yi)
                    if name=='global':
                        trend[h].append(ms['log_RMSE'])
                    checks+=1
        if age>=504:
            for k in (*S.KEYS,'WIND_VECTOR','ZG'):
                for j,(x,y) in enumerate(zip(a[k],b[k])):
                    layer.append(dict(UTC=t,hour=age,variable=k,level=j,**S.metrics(
                          x,y,w[:,None],1e-8 if k in S.COMPOSITION else 0,k=='DEN')))
    for name,r in [('initial_condition_sensitivity_metrics.csv',raw),('height_metrics.csv',heights),
                   ('native_gate_cells.csv',gates),('height_gate_cells.csv',hg),('native_layer_metrics.csv',layer)]:
        table(OUT/name,r)
    slopes={}
    for h,v in trend.items():
        require(len(v)==25,'Late window did not cover 25 hours')
        if None in v:
            slopes[h]=None
        else:
            slopes[h]=float(np.polyfit(range(25),v,1)[0])
            t=np.arange(25)-12
            require(math.isclose(slopes[h],float(t@np.array(v)/(t@t)),abs_tol=1e-14),
                    'Independent late slope')
    valid=[r for r in gates+hg if r['n']]
    fail=Counter(r['variable'] for r in valid if not r['passed'])
    positive=any(v is not None and v>0 for v in slopes.values())
    nongrowth=all(v is not None and v<=0 for v in slopes.values())
    full='FAIL' if fail or positive else 'LIMITED_PASS' if valid and nongrowth else 'INCONCLUSIVE'
    density='FAIL' if fail['DEN'] or positive else 'SUPPORTED' if valid and nongrowth else 'INCONCLUSIVE'
    comparator=load(V51/'future_analysis/summary.json')
    write_once(OUT/'initial_condition_summary.json',dict(FULL_STATE_SEED_SENSITIVITY=full,
        DENSITY_LIMITED_INSENSITIVITY=density,failed_cells_by_variable=dict(fail),late_slopes=slopes,
        evaluated_gate_cells=len(valid),empty_gate_cells=len(gates)+len(hg)-len(valid),
        historical_V51_2022=comparator,independent_checks=checks,nominal_ZG_external_datum='NOT_ADMITTED',
        unique_UTC=len(wanted),selector='V51 matching month/day/time and spinup hour',new_Swarm_DEN_reads=0))
    write_once(OUT/'independent_verification.json',dict(run_ids=[r['run_id'] for r in rec.values()],
        completed_runs=2,verified_volume_count=sum(r['volumes'] for r in rec.values()),expected_steps_each=33120,
        V51_metric_gate_and_ZG_checks=checks,scope_read_fields=FIELDS,actual_UTC=len(wanted),Swarm=0))
    plot(raw,heights,gates,hg,rec)
    print('SUMMER_SCIENCE_COMPLETE',full,density,flush=True)


def plot(raw,heights,gates,hg,rec):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from netCDF4 import Dataset

    folder=OUT/'figures'
    folder.mkdir()

    def save(f,name):
        f.tight_layout()
        f.savefig(folder/f'{name}.png',dpi=105,bbox_inches='tight')
        plt.close(f)

    fig,axs=plt.subplots(3,1,figsize=(8,7),sharex=True)
    with Dataset(OUT/'data_local/gpi.nc') as n:
        day=n['year_day'][:]%1000
        for ax,k in zip(axs,('f107d','f107a','kp')):
            ax.plot(day,n[k][:] if k!='kp' else n[k][:].max(axis=1))
            ax.set_ylabel(k if k!='kp' else 'Daily max Kp')
        axs[0].set_title('2021 A-fill research HINDCAST GPI')
        axs[-1].set_xlabel('2021 day of year')
    save(fig,'actual_driver')
    fig,axs=plt.subplots(1,3,figsize=(9,3.5))
    for ax,k,d,unit in zip(axs,('elapsed_s','peak_RSS_bytes','native_bytes'),(60,2**20,2**30),
                            ('Wall min','Sampled tree RSS MiB','NetCDF GiB')):
        ax.bar(list(rec),[r[k]/d for r in rec.values()])
        ax.set_ylabel(unit)
    save(fig,'summer_resources')
    fig,axs=plt.subplots(1,2,figsize=(10,4))
    s=[r for r in raw if r['variable']=='DEN' and r['region']=='global' and r['hour']>=504]
    axs[0].plot([r['hour'] for r in s],[100*r['relative_P95'] for r in s],label='Native DEN')
    axs[0].set(xlabel='Hours from initial condition',ylabel='Global DEN P95 (%)')
    for z in (200,300,450,500):
        s=[r for r in heights if r['height_km']==z and r['region']=='global' and r['hour']>=504]
        axs[1].plot([r['hour'] for r in s],[r['log_RMSE'] for r in s],label=f'{z} km native ZG')
    axs[1].set(xlabel='Hours from initial condition',ylabel='Global log density RMSE')
    axs[1].legend(fontsize=8)
    save(fig,'seed_density_difference')
    fig,axs=plt.subplots(2,2,figsize=(9,7))
    for ax,key in zip(axs.flat,('TN','N2','O1','ZG')):
        s=[r for r in raw if r['variable']==key and r['region']=='global' and r['hour']>=504]
        ax.plot([r['hour'] for r in s],[r['RMSE']*(.01 if key=='ZG' else 1) for r in s])
        ax.set(xlabel='Hours from initial condition',ylabel=f"{key} RMSE ({'m' if key=='ZG' else S.UNITS[key]})")
    save(fig,'seed_multifield_difference')


if __name__=='__main__':
    main()
