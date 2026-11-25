"""Check the recovery's actual forcing and day-14 map/local-time products."""
import csv
from datetime import datetime, timedelta, timezone
import math
import re
import subprocess

from netCDF4 import Dataset, num2date
import numpy as np

import preflight_summer_seed_recovery_v47 as r
import verify_summer_seed_sensitivity_v46 as mathcheck
from verify_summer_seed_execution_v48_quantile import historical_order_quantile
from atmosphere.autumn_gpi_validation import independent_at
from prepare_summer_gpi_candidate_v43 import inputs, raw_records, DAYS

OUT = r.ROOT/'experiments/thermosphere_summer_seed_execution_v48'
COMPARISON = r.OUT/'comparison'


def main():
    r.require(r.load(COMPARISON/'independent.json')['verified'], 'Missing V47 verification')
    history = r.history()
    manifest = r.OUT/'publication_SHA256.json'
    pinned = subprocess.check_output(['git','show',f'3972b381af46d63bdaccfd3ee32fdbf00d0120df:{manifest.relative_to(r.ROOT)}'])
    r.require(pinned == manifest.read_bytes(), 'V47 history changed')
    archive = r.load(r.OUT/'archived_runtime_evidence.json')
    for name,digest in (archive | r.load(manifest)).items():
        r.v45.verify_hash(name,digest)
    left = r.a_snapshot()
    p = r.protocol()
    right = r.verify_engineering(r.RUN,p)
    claim = r.load(r.receipt_path(r.RUN,'claim'))
    auth_summary = r.load(OUT/'authorization_summary.json')
    r.require(claim['authorization_sha256'] == auth_summary['authorization_sha256'] ==
              r.sha(r.OUT/'authorization.json') and claim['attempts'] == 1, 'Authorization binding diverged')
    r.verify_diff(r.archived_protocol()[r.v46.B]['input_text'],p['input_text'])
    r.new_identity(claim['run_id'],(left['run_id'],r.original_failure()['run_id']))
    cold_checks=[]
    for rank in range(4):
        log=(r.RUN/f'rank_{rank:03d}.log').read_text()
        r.require('Reading source history from diskfile ../seed.nc:' in log and
                  bool(re.search(r'Step\s+23040 of\s+23040',log)), 'Short-path or step evidence missing')
        cold_checks.append(rank)
    source=r.load(r.v45.ROOT/'experiments/thermosphere_summer_gpi_candidate_v43/input_freeze.json')['sources']
    solar,kp=inputs(source,raw_records)
    means={d:math.fsum(solar[d+timedelta(days=j)] for j in range(-40,41))/81 for d in DAYS}
    maximum=0.
    n=0
    for i in range(1,17):
        with Dataset(r.RUN/f'secondary_{i:03d}.nc') as nc:
            tv=nc['time']
            for j,instant in enumerate(num2date(tv[:],tv.units)):
                utc=datetime.fromisoformat(instant.isoformat()).replace(tzinfo=timezone.utc)
                expected=independent_at(utc,solar,means,kp)
                maximum=max(maximum,*(abs(float(nc[k][j])-v) for k,v in expected.items()))
                n+=1
    r.require(n==384 and maximum<1e-10,'Independent physical driving failed')
    left_path=r.OLD/r.v46.A
    mathcheck.RUNS=(left_path,r.RUN)
    mathcheck.quantile=historical_order_quantile
    a,b=mathcheck.frame(336)
    lat=a['lat']
    with Dataset(left_path/'secondary_014.nc') as file:
        lon=np.asarray(file['lon'][:])
    native={}
    for h in r.load(mathcheck.RULES)['common_native_ZG_heights_km']:
        native[h]=[mathcheck.interpolate_columns(f,h) for f in (a,b)]
    maps=set()
    with (COMPARISON/'day14_map.csv').open() as f:
        for row in csv.DictReader(f):
            h=int(row['height_km'])
            i=np.where(lat==float(row['latitude']))[0].item()
            j=np.where(lon==float(row['longitude']))[0].item()
            x,y=native[h]
            key=(h,i,j)
            r.require(key not in maps and math.isclose(float(row['signed_relative']),
                      (y[i,j]-x[i,j])/x[i,j],rel_tol=2e-10,abs_tol=1e-13),'Map mismatch')
            maps.add(key)
    r.require(len(maps)==sum((np.isfinite(x)&np.isfinite(y)).sum() for x,y in native.values()),
              'Incomplete common-height map')
    local_checks=0
    with (COMPARISON/'day14_localtime.csv').open() as f:
        for row in csv.DictReader(f):
            h,lo,hi=map(int,(row['height_km'],row['LT_start'],row['LT_stop']))
            x,y=native[h]
            use=(lon/15%24>=lo)&(lon/15%24<hi)
            stats=mathcheck.row_metrics(x[:,use],y[:,use],np.cos(np.deg2rad(lat))[:,None],0.,True)
            for key,val in stats.items():
                old=row[key]
                r.require(old=='' if val is None else old!='' and math.isclose(float(old),val,
                          rel_tol=2e-10,abs_tol=1e-12 if key not in ('RMSE','MAE','bias','abs_P95','max_abs') else 1e-26),
                          f'Local time mismatch: {h}/{lo}/{key}')
                local_checks+=1
    r.write(OUT/'independent_addendum.json',{
        'verified':True,'old_history_entries':len(history),'old_archived_runtime_entries':len(archive),
        'new_run_id':right['run_id'],'A_id':left['run_id'],'netcdf_A':len(left['inventory']),
        'netcdf_B':len(right['inventory']),'rank_short_source_and_final_timestep':cold_checks,
        'B_GPI_hourly_nodes':n,'B_independent_GPI_max_abs':maximum,
        'day14_map_cells':len(maps),'local_time_metrics':local_checks,
        'unseen_density_reads':0,'GPU':0})


if __name__=='__main__':
    main()
