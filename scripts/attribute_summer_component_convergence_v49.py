"""Summarize V49 evidence and independently check secondary products."""
from collections import Counter,defaultdict
from datetime import timedelta
import math

import numpy as np

import diagnose_summer_component_convergence_v49 as d
import verify_summer_component_convergence_v49 as v

OUT=d.OUT


def table(name):
    return d.rows(OUT/(name+'.csv'))



def longitude_strata(output):
    counts=defaultdict(lambda:[0,0])
    for volume in (15,16):
        ta,ga,aa=v.read_batch(v.RUNS[0],volume)
        tb,_,bb=v.read_batch(v.RUNS[1],volume)
        lat,lon,_,_=ga
        assert ta==tb
        for i in range(24):
            if (volume-1)*24+i+1<360:
                continue
            for key, entry in output.items():
                w=entry['worst']
                level=int(w['level'])
                low,high=d.RANGES[w['region']]
                sel=(lat>=low)&(lat<=high)
                a,b=aa[key][i,level,sel],bb[key][i,level,sel]
                valid,passed,_=d.gate(a,b)
                for band in range(0,360,60):
                    lm=((lon%360)>=band)&((lon%360)<band+60)
                    vv=valid[:,lm]
                    counter=counts[(key,w['region'],level,band)]
                    counter[0]+=int(vv.sum())
                    counter[1]+=int((vv&~passed[:,lm]).sum())
    return [dict(variable=k,region=r,level=l,east_longitude_start=lo,east_longitude_end=lo+60,
            n=n,failed_n=f,failed_fraction=f/n) for (k,r,l,lo),(n,f) in counts.items()]


def main():
    failed=table('failed_units')
    bands=table('concentration_bins')
    frame=table('hemisphere_pairs')
    trends=table('descriptive_decay')
    layer=table('late_layer_trends')
    series=table('worst_layer_series')
    assoc=table('associations')
    lt=table('failure_local_time')
    pivot=table('failure_pivot')
    output={}
    hemi=[]
    loc=[]
    for key in d.KEYS:
        items=[x for x in failed if x['variable']==key]
        worst=min(items,key=lambda x:float(x['passed_fraction']))
        rs=[x for x in bands if x['variable']==key]
        sets=Counter(x['region'] for x in items)
        heights=[x for x in items if x['A_ZG_min_km']]
        hot={(x['region'],x['level']) for x in items}
        ltr=[x for x in layer if x['variable']==key and (x['region'],x['level']) in hot and x['ratio']]
        slowest=max(ltr,key=lambda x:float(x['ratio']))
        w=[x for x in series if x['variable']==key and int(x['hour'])>=360]
        band=[x for x in frame if x['variable']==key]
        total=sum(int(x['n']) for x in band)
        south=sum(int(x['south_failed']) for x in band); north=sum(int(x['north_failed']) for x in band)
        output[key]=dict(failures=len(items),regional_failures=dict(sets),worst=worst,
            failed_layers_range=[min(int(x['level']) for x in items),max(int(x['level']) for x in items)],
            bracketed_A_height_range_km=[min(float(x['A_ZG_min_km']) for x in heights),max(float(x['A_ZG_max_km']) for x in heights)],
            unbracketed_failed_units=len(items)-len(heights),min_coverage=min(float(x['coverage']) for x in items),
            concentration_point_total=sum(int(x['n']) for x in rs),
            failing_points_sum=sum(int(x['failed_n']) for x in rs),
            point_failures_at_or_above_0_01=sum(int(x['failed_n']) for x in rs if float(x['lo_mmr'])>=.01),
            points_within_factor10_floor=int(rs[0]['n']),slowest_failing_region_level=slowest,
            failing_region_layers_rising_last24_vs_previous24=sum(float(x['ratio'])>1 for x in ltr),
            failing_region_layers_near_flat_last24_vs_previous24=sum(.97<=float(x['ratio'])<=1.03 for x in ltr),
            worst_location_start_end_relative_P95=[float(w[0]['P95_relative']),float(w[-1]['P95_relative'])],
            worst_location_start_end_pass_fraction=[float(w[0]['passed_fraction']),float(w[-1]['passed_fraction'])],
            worst_location_late_hour_count_under_gate=sum(float(x['passed_fraction'])<.95 for x in w),
            region_gate_persistence=[r for r in pivot if r['variable']==key and r['mode']=='region'],
            globals_24h_mean_ratio=float(next(x['last48_daily_ratio'] for x in trends if
                x['variable']==key and x['region']=='global' and x['metric']=='relative_mean')),
            absolute_vs_relative_fit=[r for r in trends if r['variable']==key and r['region']=='global'],
            matched_south_fail_fraction=south/total,matched_north_fail_fraction=north/total,
            south_polar_association_median={k:float(np.median([float(x['r']) for x in assoc if
                x['region']=='south_polar' and x['field']==k and x['variable']==key and x['r']]))
                for k in ('TN','UN','VN','wind_vector','log_DEN','ZG_km')})
        for lab,criteria in [('polar',lambda x:float(x['abs_lat'])>=60),
                             ('mid',lambda x:30<=float(x['abs_lat'])<60),
                             ('low',lambda x:float(x['abs_lat'])<30),
                             ('all',lambda x:True)]:
            h=[x for x in band if criteria(x)]
            n=sum(int(x['n']) for x in h)
            for side in ('south','north'):
                fail=sum(int(x[side+'_failed']) for x in h)
                hemi.append(dict(variable=key,abs_lat_band=lab,hemisphere=side,n=n,failed_n=fail,fraction=fail/n))
        for region in ('south_polar','south_mid','tropics'):
            for hour in (0,6,12,18):
                z=[x for x in lt if x['variable']==key and x['region']==region and int(x['LT_start'])==hour]
                nn=sum(int(x['n']) for x in z); f=sum(int(x['failed_n']) for x in z)
                loc.append(dict(variable=key,region=region,LT_start=hour,n=nn,failed_n=f,
                                fraction=f/nn if nn else None))
    # Re-read the raw arrays for local-time / worst-layer rollups and exploratory symmetric denominator.
    wanted={(x['variable'],x['region'],int(x['level'])) for x in series}
    keys={(int(x['hour']),x['variable']):x for x in series}
    local={(int(x['hour']),x['variable'],x['region'],int(x['level']),int(x['LT_start'])):x for x in lt}
    symmetric=defaultdict(lambda:[0,0,0])
    checked_series=checked_lt=0
    for volume in range(1,17):
        ta,ga,aa=v.read_batch(v.RUNS[0],volume)
        tb,gb,bb=v.read_batch(v.RUNS[1],volume)
        assert ta==tb
        lat,lon,_,_=ga
        for i in range(24):
            hour=(volume-1)*24+i+1
            for key,region,z in wanted:
                lo,hi=d.RANGES[region]
                mask=(lat>=lo)&(lat<=hi)
                a,b=aa[key][i,z,mask],bb[key][i,z,mask]
                valid=(a>1e-8)&np.isfinite(a)&np.isfinite(b)
                dif=np.abs(a[valid]-b[valid])
                rel=dif/a[valid]
                entry=keys[(hour,key)]
                assert (entry['UTC'],entry['region'],int(entry['level']))==(ta[i],region,z)
                assert int(entry['n'])==len(dif) and int(entry['passed_n'])==np.count_nonzero(rel<.05)
                assert np.isclose(float(entry['mean_abs_mmr']),dif.mean())
                assert np.isclose(float(entry['P95_relative']),np.quantile(rel,.95))
                checked_series+=1
            if hour<360:
                continue
            true_lt=(hour+lon/15)%24
            for key in d.KEYS:
                a,b=aa[key][i],bb[key][i]
                valid=np.isfinite(a)&np.isfinite(b)&(a>1e-8)
                x,y=a[valid],b[valid]
                ab=np.abs(y-x)
                counter=symmetric[key]
                counter[0]+=len(ab);counter[1]+=int((ab/x>=.05).sum())
                counter[2]+=int((2*ab/(x+y)>=.05).sum())
            for (h,key,region,z,k),entry in local.items():
                if h!=hour:continue
                lo,hi=d.RANGES[region]
                lsel=(lat>=lo)&(lat<=hi);q=(true_lt>=k)&(true_lt<k+6)
                a=aa[key][i,z,lsel][:,q];b=bb[key][i,z,lsel][:,q]
                valid=np.isfinite(a)&np.isfinite(b)&(a>1e-8)
                assert valid.sum()==int(entry['n'])
                assert np.count_nonzero(abs(a[valid]-b[valid])/a[valid]>=.05)==int(entry['failed_n'])
                checked_lt+=1
    assert checked_lt==len(local) and checked_series==len(series)
    # Independent centered-dot slope from verified hourly rows, no polyfit call.
    rows=table('hourly')
    by=defaultdict(list)
    for row in rows: by[row['variable'],row['region']].append(row)
    for row in trends:
        ss=sorted(by[row['variable'],row['region']],key=lambda x:int(x['hour']))
        vv=np.array([float(x[row['metric']]) for x in ss]).reshape((16,24)).mean(axis=1)
        y=np.log(vv[int(row['first_day'])-1:])
        x=np.arange(len(y)); x=x-x.mean()
        slope=float(np.dot(x,y-y.mean())/np.dot(x,x))
        assert math.isclose(slope,float(row['log_slope_per_day']),rel_tol=1e-10)
    d.write('hemisphere_summary.csv',hemi)
    d.write('localtime_summary.csv',loc)
    d.write('worst_layer_longitude.csv',longitude_strata(output))
    d.write('diagnostic_attribution.json',dict(variables=output,
        symmetric_denominator={'definition':'2*abs(B-A)/(A+B), original valid point set, all unique grid points in window',
            'counts':{k:dict(valid=v[0],frozen_point_failures=v[1],exploratory_point_failures=v[2]) for k,v in symmetric.items()},
            'replaces_frozen_gate':False},
        checks={'worst_layer_series':checked_series,'local_time_rows':checked_lt,'decay_regressions':len(trends)},
        labels=['DENSITY_LIMITED_INSENSITIVITY_SUPPORTED','COMPONENT_SLOW_ADJUSTMENT_SUPPORTED','MECHANISM_INCONCLUSIVE']))


if __name__=='__main__':
    main()
