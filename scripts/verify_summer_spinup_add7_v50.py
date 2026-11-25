"""Independent V50 future verifier for native and fixed-height statistics and gates."""
import csv
from datetime import datetime
import json
from collections import defaultdict
import math

import numpy as np

import analyze_summer_spinup_add7_v50 as v
import verify_summer_seed_sensitivity_v46 as old
from verify_summer_seed_execution_v48_quantile import historical_order_quantile


def rows(name):
    with (v.RESULT/f'{name}.csv').open() as f:
        return list(csv.DictReader(f))


def verified_stats(reference,candidate,weights,var):
    old.quantile=historical_order_quantile
    return old.row_metrics(reference,candidate,weights,1e-8 if var in v.science.COMPOSITION else 0.,var=='DEN')


def check_row_stats(row,stats):
    for k,val in stats.items():
        there=row[k]
        assert (there=='' if val is None else there!='' and
                math.isclose(float(there),val,rel_tol=2e-10,abs_tol=1e-26 if row.get('variable','DEN')=='DEN' else 1e-12)), (k,row,val)


def main():
    runs,ids=v.evidence()
    rules=json.loads(v.science.RULES.read_text())
    grouped=defaultdict(list)
    for name in ('hourly','height'):
        for row in rows(name):grouped[datetime.fromisoformat(row['UTC'])].append((name,row))
    for name in ('gates','height_gates'):
        for row in rows(name):
            key=v.gpi.START+v.timedelta(hours=int(row['hour']))
            grouped[key].append((name,row))
    assert set(grouped)==set(v.samples())
    seen={(kind,utc,row.get('variable'),row['region'],row.get('height_km'),row.get('level'))
          for utc,group in grouped.items() for kind,row in group}
    assert len(seen)==sum(len(x) for x in grouped.values())
    regions=len(rules['latitude_regions'])
    expected={'hourly':len(v.samples())*(len(v.science.KEYS)+1)*regions,
              'height':len(v.samples())*len(rules['common_native_ZG_heights_km'])*regions,
              'gates':25*len(v.science.GATE)*regions*29,
              'height_gates':25*len(rules['common_native_ZG_heights_km'])*regions}
    assert all(sum(row[0]==key for group in grouped.values() for row in group)==n
               for key,n in expected.items())
    count=0
    slopes=defaultdict(list)
    failed=den_fail=total_valid=0
    for t,group in sorted(grouped.items()):
        a,b,grid=v.read_frame(runs,t,independent=True)
        lat=grid[0]
        weight=np.cos(np.pi*lat/180)
        heights={}
        for name,row in group:
            lo,hi=rules['latitude_regions'][row['region']]
            m=(lat>=lo)&(lat<=hi)
            variable=row.get('variable','DEN')
            if name.startswith('height'):
                h=int(row['height_km'])
                if h not in heights:
                    heights[h]=[old.interpolate_columns(f,h) for f in (a,b)]
                x,y=[z[m] for z in heights[h]]
                w=weight[m,None]
                if name=='height_gates':
                    assert row['level']=='0'
            else:
                x,y=[z[variable][:,m] for z in (a,b)]
                w=weight[None,m,None]
                if name=='gates':x,y=x[int(row['level'])],y[int(row['level'])]
            if name.endswith('gates'):
                valid=np.isfinite(x)&np.isfinite(y)
                if variable in ('DEN',*v.science.COMPOSITION):
                    valid &= abs(x)>(1e-8 if variable in v.science.COMPOSITION else 0.)
                    error=np.abs((y[valid]-x[valid])/x[valid])
                    limit=.05
                else:
                    error=np.abs(y[valid]-x[valid])
                    limit=10 if variable=='TN' else 2000
                assert len(error)==int(row['n'])
                if len(error):
                    prop=float(np.count_nonzero(error<limit)/len(error))
                    assert prop==float(row['passed_fraction']) and row['passed']==str(prop>=.95)
                    total_valid+=1
                    failed+=prop<.95
                    den_fail+=variable=='DEN' and prop<.95
                else:
                    assert row['passed_fraction']==row['passed']==''
            else:
                new,prior=v.alignment(t)
                assert int(row['hour_V50'])==new and row['hour_V48']==('' if prior is None else str(prior))
                values=verified_stats(x,y,w,variable)
                check_row_stats(row,values)
                if name=='height' and row['region']=='global' and t in v.LATE_UTC:
                    slopes[h].append(values['log_RMSE'])
            count+=1
    result=json.loads((v.RESULT/'summary.json').read_text())
    assert result['run_ids']==ids and result['full_failed_cells']==failed
    for h,vals in slopes.items():
        assert len(vals)==25
        expected=result['trends'][str(h)]
        if None not in vals:
            t=np.arange(25)-12
            assert math.isclose(np.dot(t,vals-np.mean(vals))/np.dot(t,t),expected,rel_tol=1e-8,abs_tol=1e-14)
        else:
            assert expected is None
    g=any(x is not None and x>0 for x in result['trends'].values())
    ng=all(x is not None and x<=0 for x in result['trends'].values())
    assert result['FULL_STATE_SEED_SENSITIVITY']==('FAIL' if failed or g else 'LIMITED_PASS' if total_valid and ng else 'INCONCLUSIVE')
    assert result['DENSITY_LIMITED_INSENSITIVITY']==('FAIL' if den_fail or g else 'SUPPORTED' if total_valid and ng else 'INCONCLUSIVE')
    with (v.RESULT/'independent.json').open('x') as f:
        json.dump(dict(verified=True,rows_checked=count,run_ids=ids,scope='future add7 internal engineering'),f,indent=2)


if __name__=='__main__':
    main()
