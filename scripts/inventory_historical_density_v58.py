"""Inventory native histories and bounded observation metadata without density decoding."""
from collections import Counter, defaultdict
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

from cdflib import CDF, cdfepoch
from netCDF4 import Dataset, num2date
import numpy as np

from build_non_target_horizon_index_v56 import ROOT, V37, iso, pin, sha
from check_external_evidence_v55 import check

OUT = ROOT/'experiments/thermosphere_development_feasibility_v58'
V57 = ROOT/'experiments/thermosphere_real_development_v57'
BASE = '0cb3d5c50e530cf25487eedb1c53908b2a74e4d9'
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)
NATIVE = re.compile(r'(?:secondary(?:_\d+)?|branch_secondary_\d+|tiegcm.*_sech(?:_\d+)?)\.nc',re.I)
SWARM = re.compile(r'SW_OPER_DNS([AC])POD_2__(\d{8})T\d{6}_\d{8}T\d{6}_(\d{4})\.cdf',re.I)


def table(path, rows):
    with (OUT/path).open('x',newline='') as f:
        w = csv.DictWriter(f,list(rows[0]),lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def save(path, value):
    with (OUT/path).open('x') as f:
        json.dump(value,f,indent=2,allow_nan=False)
        f.write('\n')


def files(folder, pattern):
    return sorted(p for p in (ROOT/folder).rglob(pattern)
                  if p.is_file() and not p.is_symlink() and p.resolve()==p)


def field(dataset_id,path,digest,start,end,kind,step,meta,grid,role,access,target,eligible,duplicate,missing):
    return dict(dataset_id=dataset_id,source_path=str(path.relative_to(ROOT)),source_SHA256=digest,
                date_start=start,date_end=end,data_type=kind,sample_resolution=step,
                variables_metadata=meta,model_grid=grid,scientific_role=role,allowed_access=access,
                target_access=target,validation_eligibility=eligible,duplicate_group=duplicate,missing_records=missing)


def native_times(path):
    with Dataset(path) as nc:
        den,zg,t = (nc[k] for k in ('DEN','ZG','time'))
        if den.dimensions != zg.dimensions or den.dimensions != ('time','ilev','lat','lon'):
            raise ValueError(f'DEN/ZG grid mismatch: {path}')
        times = [datetime.fromisoformat(d.isoformat()).replace(tzinfo=timezone.utc) for d in
                 num2date(t[:],t.units,getattr(t,'calendar','standard'))]
        dims = {k:len(nc.dimensions[k]) for k in ('lat','lon','lev','ilev') if k in nc.dimensions}
        grid = dict(dims, coordinate_SHA256={k:hashlib.sha256(np.asarray(nc[k][:],dtype='<f8').tobytes()).hexdigest()
                                                for k in dims if k in nc.variables})
        meta = {k:dict(dimensions=nc[k].dimensions,units=getattr(nc[k],'units',None)) for k in ('DEN','ZG')}
    if not times:
        raise ValueError(f'Empty time axis: {path}')
    return times,grid,meta


def family(path):
    match = re.search(r'(tiegcm_20\d\d|mar23_v2_20\d\d|mar25|/20\d\d/|summer|2023|restart)',path)
    if 'summer' in path:
        return '2022_summer_shared_forcing'
    if 'autumn' in path:
        return 'autumn_'+next(p for p in path.split('/') if re.fullmatch(r'20\d\d',p))
    if '2023' in path:
        return '2023_march_shared_forcing_or_startup'
    if match:
        return 'spring_'+('2022' if 'mar25' in path or '2022' in path else '2021')
    return path


def receipt(folder):
    result = {}
    for name in ('engineering_receipt.json','run_receipt.json','preflight.json','launch_once.json','data_audit.json'):
        p = folder/name
        if p.is_file() and p.resolve()==p:
            raw = json.loads(p.read_text())
            for key in ('run_id','model_sha256','elf_sha256','gpi_sha256','model_ELF_SHA256','GPI_SHA256'):
                if raw.get(key):
                    result[key] = raw[key]
    for name in ('input.inp','input.namelist'):
        p = folder/name
        if not p.is_file() or p.resolve()!=p:
            continue
        result['input_SHA256'] = sha(p)
        m = re.search(r"GPI_NCFILE\s*=\s*['\"]([^'\"]+)",p.read_text(),re.I)
        if m:
            g = Path(m[1].replace('$PROJECTROOT',str(ROOT)))
            g = g if g.is_absolute() else folder/g
            g = g.resolve()
            if g.is_relative_to(ROOT) and g.is_file():
                result['local_GPI_SHA256'] = sha(g)
                result['local_GPI_path'] = str(g.relative_to(ROOT))
        break
    return result


def scan_models():
    files_by_run = defaultdict(list)
    for p in files('experiments','*.nc'):
        if NATIVE.fullmatch(p.name):
            files_by_run[p.parent].append(p)
    inventories, volumes, groups, timelines = [], [], [], {}
    all_hours, all_dates, dated_hours, dated_dates = set(),set(),set(),set()
    for folder, paths in sorted(files_by_run.items()):
        run = str(folder.relative_to(ROOT))
        hashes, frames = [], []
        grid_contract = None
        for p in paths:
            times, grid, meta = native_times(p)
            if grid_contract is None:
                grid_contract = (grid,meta)
            if grid_contract != (grid,meta):
                raise ValueError(f'Grid or field metadata drift: {p}')
            digest = sha(p)
            hashes.append((p.name,digest))
            frames.extend(times)
            volumes.append(dict(run=run,path=str(p.relative_to(ROOT)),SHA256=digest,frames=len(times),
                                first=iso(min(times)),last=iso(max(times))))
        ts = sorted(set(frames))
        steady = [t for t in ts if t.minute==t.second==t.microsecond==0]
        gaps = Counter(int((b-a).total_seconds()) for a,b in zip(ts,ts[1:]))
        resolution = min(gaps, key=lambda d:(-gaps[d],d)) if gaps else None
        hourly = resolution == 3600
        missing = (int((ts[-1]-ts[0])/HOUR)+1-len(ts)) if hourly else None
        key = hashlib.sha256(json.dumps(hashes,separators=(',',':')).encode()).hexdigest()
        stamp = {t.date().isoformat() for t in ts}
        all_dates.update(stamp)
        all_hours.update(steady)
        if ts[-1].year >= 2021:
            dated_dates.update(stamp)
            dated_hours.update(steady)
        streak = longest_hourly(steady)
        ids = receipt(folder)
        groups.append(dict(run=run,forcing_family=family(run),output_manifest_SHA256=key,
                           **ids,volumes=len(paths),frames=len(frames),unique_UTC=len(ts),
                           cadence_seconds=dict(sorted(gaps.items())),whole_hour_frames=len(steady),
                           longest_hourly_streak=streak,missing_modal_hourly_records=missing))
        timelines[run] = set(steady)
        inventories.append(field(run,folder,key,iso(ts[0]),iso(ts[-1]),'TIEGCM_SECONDARY',
                    resolution,json.dumps(meta),json.dumps(grid),'HINDCAST_ENGINEERING_OR_DIAGNOSTIC',
                    'TIME_GRID_AND_UNITS_ONLY','NOT_AUTHORIZED','DEVELOPMENT_CANDIDATE_ONLY',family(run),missing))
    exact = defaultdict(list)
    for volume in volumes:
        exact[volume['SHA256']].append(volume['path'])
    return inventories, volumes, groups, timelines, dict(total_model_days=len(all_dates),
        dated_model_days_2021_plus=len(dated_dates),whole_hour_UTC_union=len(all_hours),
        dated_whole_hour_UTC_union=len(dated_hours),longest_global_consecutive_hours=longest_hourly(sorted(all_hours)),
        longest_single_run_hours=max(r['longest_hourly_streak'] for r in groups),
        total_native_frames=sum(r['frames'] for r in groups),model_groups=len(groups),volumes=len(volumes),
        byte_duplicate_volume_groups=[p for p in exact.values() if len(p)>1])


def longest_hourly(times):
    longest = count = 0
    previous = None
    for time in times:
        count = count+1 if previous is not None and time-previous==HOUR else 1
        longest = max(longest,count)
        previous = time
    return longest


def scan_observations(roles):
    result = []
    for path in files('data/raw','*.cdf'):
        match = SWARM.fullmatch(path.name)
        if not match:
            continue
        sat, compact, version = match.groups()
        date = datetime.strptime(compact,'%Y%m%d').date().isoformat()
        cdf = CDF(path)
        clock = cdfepoch.to_datetime(cdf.varget('time')).astype('datetime64[s]')
        expected = np.datetime64(date,'s')+np.arange(2880)*np.timedelta64(30,'s')
        missing = len(np.setdiff1d(expected,clock))
        if missing or len(clock)!=2880 or not np.array_equal(clock,expected):
            serial = 'IRREGULAR_OR_INCOMPLETE_UTC'
        else:
            serial = 30
        role = roles.get(date,{}).get('role','UNASSIGNED_METADATA_ONLY') if sat=='A' else 'OTHER_SATELLITE_METADATA_ONLY'
        fields = {k:dict(records=cdf.varinq(k).Last_Rec+1,units=cdf.varattsget(k).get('UNITS'))
                  for k in ('time','density','density_orbitmean','validity_flag') if k in cdf.cdf_info().zVariables}
        result.append(field(f'Swarm-{sat}-{date}-{version}',path,sha(path),str(clock[0])+'Z',str(clock[-1])+'Z',
           'SWARM_'+sat+'_DNSPOD',serial,json.dumps(fields),'ALONG_TRACK',role,
           'V37_CUTOFF_HISTORY_ELIGIBLE' if role=='DEVELOPMENT_SOURCE' else 'METADATA_ONLY',
           'SEALED','NONE_FOR_NEW_EXPERIMENT',f'Swarm-{sat}-{date}-{version}',missing))
    return result


def endpoints(available, roles):
    indexed, proposals = [], []
    frozen = {d for d,r in roles.items() if r['role']=='UNSEEN_TEST_METADATA_ONLY'}
    for day in sorted(available):
        midnight = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
        eligible = []
        for h in (6,18):
            cutoff = midnight+h*HOUR
            for lead in (1,3,6):
                start = cutoff-3*HOUR
                target = cutoff+lead*HOUR
                support_dates = {x.date().isoformat() for x in (start,cutoff,target)}
                if support_dates & frozen:
                    continue
                matching = [run for run,times in available[day].items()
                            if {start,start+HOUR,start+2*HOUR,target}<=times]
                if not matching:
                    continue
                run = sorted(matching)[0]
                eligible.append((h,lead))
                indexed.append(dict(sample_id=hashlib.sha256(f'{run}|{iso(cutoff)}|{lead}'.encode()).hexdigest(),
                    source_run_id=run,date_block_id=day[:7],cutoff_UTC=iso(cutoff),input_start_UTC=iso(start),
                    input_end_UTC_exclusive=iso(cutoff),prediction_target_UTC=iso(target),
                    target_support_start_UTC=iso(target),target_support_end_UTC_exclusive=iso(target+timedelta(seconds=1)),
                    horizon=lead,spatial_target_definition='native ilev/lat/lon TIEGCM DEN endpoint',
                    data_role='METADATA_ONLY_CANDIDATE',access_policy='NO_TARGET_VALUE_READ',date=day))
        proposals.append(dict(date=day,state='ALREADY_AUTHORIZED' if roles.get(day,{}).get('role')=='DEVELOPMENT_SOURCE'
            else 'EXCLUDED_BY_FROZEN_PROTOCOL' if day in frozen else 'PROPOSED_FOR_NEW_DEVELOPMENT' if eligible else 'DATA_INCOMPLETE',
            possible_endpoints=len(eligible),runs=len(available[day]),real_target_access='NOT_AUTHORIZED'))
    return indexed,proposals


def main():
    assert OUT.resolve()==OUT
    protocol = pin(V37)
    roles = {r['date']:r for r in protocol['roles']['dates']}
    receipt_path = V57/'publication_SHA256.json'
    assert receipt_path.read_bytes()==subprocess.check_output(['git','show',f'{BASE}:{receipt_path.relative_to(ROOT)}'],cwd=ROOT)
    ledger = json.loads(receipt_path.read_text())
    assert all(sha(ROOT/p)==digest for p,digest in ledger.items())
    old = json.loads((V57/'independent.json').read_text())
    observations = scan_observations(roles)
    with (V57/'availability.csv').open() as f:
        fixed = {r['CDF']:r['source_SHA256'] for r in csv.DictReader(f)}
    assert all(r['source_SHA256']==fixed[r['source_path']] for r in observations if r['scientific_role']=='DEVELOPMENT_SOURCE')
    models, volumes, groups, times, totals = scan_models()
    available = defaultdict(dict)
    for run, stamps in times.items():
        if len(stamps)<24:
            continue
        for day in {x.date().isoformat() for x in stamps}:
            if day>='2021':
                available[day][run] = stamps
    for row in observations:
        available[row['date_start'][:10]]
    for day in roles:
        available[day]
    indexed, proposals = endpoints(available,roles)
    keys = {r['run']:r['output_manifest_SHA256'] for r in groups}
    for row in indexed:
        row['source_SHA256'] = keys[row['source_run_id']]
    drivers = []
    for path in files('data/raw','*.json'):
        if not re.search(r'Fobs|(?:^|_)Kp(?:_|\b)|definitive',path.name,re.I) or path.stat().st_size>20_000_000:
            continue
        raw = json.loads(path.read_text())
        stamps = raw.get('datetime',[]) if isinstance(raw,dict) else []
        keys = [k for k in ('Fobs','Kp') if isinstance(raw,dict) and k in raw]
        if not stamps or not keys:
            continue
        values = raw[keys[0]]
        drivers.append(field(path.stem,path,sha(path),stamps[0],stamps[-1],'GFZ_DRIVER','native',
              ','.join(keys),'','HISTORICAL_DRIVER_ARCHIVE_QUALITY_PER_RECEIPT','ARCHIVED_DRIVER_VALUES','N/A',
              'HINDCAST_NOT_ASOF',keys[0],sum(v is None or str(v)=='-1' or str(v)=='-1.0' for v in values)))
    aggregates=[]
    for folder,name in [('thermosphere_causal_shrinkage_development_v36','metrics.csv'),
                        ('thermosphere_autumn_density_validation_v30','cross_season_metrics.csv'),
                        ('thermosphere_real_development_v57','predictions.csv')]:
        p=ROOT/'experiments'/folder/name
        aggregates.append(field(folder,p,sha(p),'','','FROZEN_DERIVED_RESULTS','original sample identity',
             name,'','HISTORICAL_DEVELOPMENT','PUBLISHED_ONLY','NO_NEW_LABEL','NO_V58_SCORE',folder,''))
    archive = []
    for path in files('data/raw','*.npz'):
        match = re.fullmatch(r'(20\d{2})_(\d{2})_(\d{2})_(\d{6})\.npz',path.name)
        if not match or 'fourcastden' not in str(path.parent):
            continue
        y,m,d,clock = match.groups()
        stamp = f'{y}-{m}-{d}T{clock[:2]}:{clock[2:4]}:{clock[4:]}Z'
        archive.append(field(path.stem,path,sha(path),stamp,stamp,'FOURCASTDEN_ARCHIVED_FRAME',
            'file timestamp','Arrays sealed; author package archive','see author manifest',
            'HISTORICAL_BENCHMARK_ONLY','PATH_AND_SHA_ONLY','NOT_AUTHORIZED',
            'NO_RECLASSIFICATION',stamp,''))
    table('historical_data_inventory.csv',models+observations+drivers+aggregates+archive)
    table('model_volumes.csv',volumes)
    table('candidate_endpoints.csv',indexed)
    table('candidate_dates.csv',proposals)
    save('model_runs.json',groups)
    save('handoff.json',check())
    save('inventory_summary.json',dict(**totals,swarm_A_days=len({r['date_start'][:10] for r in observations
        if r['data_type']=='SWARM_A_DNSPOD'}),swarm_all_product_days=len(observations),
        GFZ_response_files=len(drivers),FourCastDEN_raw_archive_files=len(archive),
        FourCastDEN_raw_unique_timestamps=len({r["date_start"] for r in archive}),V57_release_entries=len(ledger),
        historical_authorized_observations=old['nominal_observations'],V37_development_days=len(fixed),
        V37_endpoint_candidates=sum(r['possible_endpoints'] for r in proposals if r['state']=='ALREADY_AUTHORIZED'),
        metadata_endpoint_candidates=len(indexed),supervised_train=0,supervised_validation=0,supervised_test=0,
        target_density_decodes=0,model_DEN_reads=0))


if __name__=='__main__':
    main()
