"""Check inventory identities, proposal isolation and frozen V57 forecast coverage."""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import csv
import hashlib
import json
import math
import re
import subprocess

from netCDF4 import Dataset

from build_non_target_horizon_index_v56 import ROOT, V37, pin, sha
from inventory_historical_density_v58 import OUT, V57, BASE, save, table
from run_real_development_v57 import LOCAL, worker


def read(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit_roles(assignments, sealed_days):
    owners, support = {}, defaultdict(set)
    for row in assignments:
        split = row['split']
        start,end = (datetime.fromisoformat(row[k].replace('Z','+00:00'))
                     for k in ('input_start_UTC','target_support_end_UTC_exclusive'))
        if start>=end:
            raise ValueError('Invalid data support')
        cursor = start.date()
        while cursor<= (end-timedelta(microseconds=1)).date():
            if cursor.isoformat() in sealed_days:
                raise ValueError('Touches V37 unseen date')
            cursor+=timedelta(days=1)
        for key in ('source_run_id','forcing_family','date_block_id'):
            token = (key,row[key])
            if owners.setdefault(token,split)!=split:
                raise ValueError(f'{key} reused across partitions')
        for other, pairs in support.items():
            if other!=split and any(max(start,a)<min(end,b) for a,b in pairs):
                raise ValueError('Cross-split support overlap')
        support[split].add((start,end))


def label_access(state):
    if state!='SEPARATE_USER_AUTHORIZATION_VERIFIED':
        raise PermissionError('Proposal and metadata status do not authorize labels')


def tests(sealed):
    base = dict(split='train',source_run_id='A',forcing_family='F',date_block_id='D1',
                input_start_UTC='2020-01-01T21:00:00Z',target_support_end_UTC_exclusive='2020-01-02T01:00:01Z')
    held = dict(base,split='validation',source_run_id='B',forcing_family='G',date_block_id='D2',
                input_start_UTC='2020-02-01T03:00:00Z',target_support_end_UTC_exclusive='2020-02-01T12:00:01Z')
    audit_roles([base,held],sealed)
    negatives={}
    for key,case in {
       'same_run':dict(held,source_run_id='A'),
       'alternate_seed_shared_forcing':dict(held,forcing_family='F'),
       'shared_date_block':dict(held,date_block_id='D1'),
       'support_overlap':dict(held,input_start_UTC='2020-01-01T23:00:00Z'),
       'cross_midnight_into_unseen':dict(held,input_start_UTC='2021-06-20T21:00:00Z',
          target_support_end_UTC_exclusive='2021-06-21T01:00:01Z'),
    }.items():
        try:
            audit_roles([base,case],sealed)
        except ValueError as exc:
            negatives[key]=str(exc)
        else:
            raise AssertionError(key)
    for state in ('PROPOSED_FOR_NEW_DEVELOPMENT','ALREADY_AUTHORIZED','EXCLUDED_BY_FROZEN_PROTOCOL'):
        try:
            label_access(state)
        except PermissionError as exc:
            negatives[state]=str(exc)
        else:
            raise AssertionError(state)
    return negatives


def coverage():
    rows = read(V57/'predictions.csv')
    by = defaultdict(list)
    paired = defaultdict(dict)
    for r in rows:
        method = r['method']
        value = float(r['density_kg_m3'])
        actual = math.isfinite(value) and value>0
        require(actual==(r['valid']=='True') and r['target_status']=='SEALED','V57 validity mismatch')
        year,month,hour = r['cutoff_UTC'][:4],r['cutoff_UTC'][5:7],r['cutoff_UTC'][11:13]
        season = {'03':'March equinox','09':'September equinox'}[month]
        by[year,season,hour,r['horizon_hours'],method].append(value)
        paired[r['sample_id']][method]=actual
    require(len(rows)==96 and len(paired)==48 and all(len(m)==2 for m in paired.values()),'V57 pairing')
    summary=[]
    for (year,season,cutoff,lead,method), values in sorted(by.items()):
        valid = sum(math.isfinite(v) and v>0 for v in values)
        nonpositive = sum(math.isfinite(v) and v<=0 for v in values)
        finite = [v for v in values if math.isfinite(v)]
        summary.append(dict(year=year,season=season,cutoff_UTC_hour=cutoff,horizon_hours=lead,method=method,
             samples=len(values),valid=valid,nonpositive=nonpositive,nonpositive_fraction=nonpositive/len(values),
             nonfinite=len(values)-len(finite),coverage=valid/len(values),min_kg_m3=min(finite),max_kg_m3=max(finite)))
    table('v57_baseline_coverage.csv',summary)
    return dict(common_valid=sum(all(m.values()) for m in paired.values()),
      **{method:dict(total=sum(len(v) for k,v in by.items() if k[-1]==method),
              valid=sum(sum(math.isfinite(x) and x>0 for x in v) for k,v in by.items() if k[-1]==method),
              min_kg_m3=min(x for k,v in by.items() if k[-1]==method for x in v),
              max_kg_m3=max(x for k,v in by.items() if k[-1]==method for x in v))
              for method in ('Persistence','TwoFrameLinear')})


def main():
    manifest = json.loads((V57/'publication_SHA256.json').read_text())
    require(all(sha(ROOT/p)==h for p,h in manifest.items()),'V57 publication changed')
    for stage in ('external_evidence_handoff_v55','non_target_protocol_v56'):
        path = ROOT/f'experiments/thermosphere_{stage}/publication_SHA256.json'
        require(path.read_bytes()==subprocess.check_output(
          ['git','show',f'{BASE}:{path.relative_to(ROOT)}'],cwd=ROOT),'Historical manifest differs')
        require(all(sha(ROOT/p)==h for p,h in json.loads(path.read_text()).items()),'Historical publication differs')
    windows = json.loads((V57/'windows.json').read_text())
    require(len(windows)==16 and all(sha(LOCAL/(r['name']+'_history.csv'))==r['history_SHA256']
           and sha(LOCAL/r['name']/'anchors.txt')==r['input_SHA256'] for r in windows),
           'V57 local history or worker anchor changed')
    proto = pin(V37)
    require(proto['first_pair']==['2021-06-21','2022-06-21'] and proto['candidates']['ShrinkageHalf']==.5,'V37 changed')
    roles = {r['date']:r['role'] for r in proto['roles']['dates']}
    sealed = {d for d,role in roles.items() if role=='UNSEEN_TEST_METADATA_ONLY'}
    candidates = read(OUT/'candidate_endpoints.csv')
    proposals = {r['date']:r for r in read(OUT/'candidate_dates.csv')}
    runs = {r['run']:r for r in json.loads((OUT/'model_runs.json').read_text())}
    volumes = read(OUT/'model_volumes.csv')
    for role in 'AB':
        path = ROOT/f'experiments/thermosphere_summer_spinup_add7_execution_v51/engineering_{role}.json'
        old = json.loads(path.read_text())
        hashes = old['outputs_sha256']
        actual = {r['path'].split('/')[-1]:r['SHA256'] for r in volumes
                  if r['run'].endswith(f'run_{role}_'+('mareqx' if role=='A' else 'junsol')+'_add7')}
        expected = {p.split('/')[-1]:h for p,h in hashes.items() if p.split('/')[-1].startswith('secondary_')}
        require(len(expected)==23 and actual==expected,'V51 secondary SHA mismatch')
    group = defaultdict(list)
    volumes_by_day = defaultdict(list)
    for f in volumes:
        group[f['SHA256']].append(f['path'])
        volumes_by_day[f['run']].append(f)
    for run, receipt in runs.items():
        ordered = sorted((r['path'].split('/')[-1],r['SHA256']) for r in volumes_by_day[run])
        actual = hashlib.sha256(json.dumps(ordered,separators=(',',':')).encode()).hexdigest()
        require(actual==receipt['output_manifest_SHA256'],'Run identity')
    schedules={}
    for run in {r['source_run_id'] for r in candidates}:
        observed = set()
        for volume in volumes_by_day[run]:
            with Dataset(ROOT/volume['path']) as nc:
                t = nc['time']
                match = re.fullmatch(r'minutes since (\d+)-(\d+)-(\d+) (\d+):(\d+):(\d+)',t.units)
                require(match is not None,'Unrecognized native model clock')
                origin = datetime(*map(int,match.groups()),tzinfo=timezone.utc)
                observed.update(origin+timedelta(minutes=float(v)) for v in t[:])
        schedules[run]=observed
    expected_ids=set()
    for r in candidates:
        cut = datetime.fromisoformat(r['cutoff_UTC'].replace('Z','+00:00'))
        lead = int(r['horizon'])
        target = datetime.fromisoformat(r['prediction_target_UTC'].replace('Z','+00:00'))
        start = cut-timedelta(hours=3)
        require(cut.hour in (6,18) and lead in (1,3,6) and target-cut==timedelta(hours=lead),'Bad endpoint')
        require(r['input_start_UTC']==start.isoformat().replace('+00:00','Z') and
           r['input_end_UTC_exclusive']==r['cutoff_UTC'],'Wrong input support')
        require(r['date'] not in sealed and target.date().isoformat() not in sealed,'Unseen date selected')
        require({start,start+timedelta(hours=1),start+timedelta(hours=2),target}<=schedules[r['source_run_id']],
                'Missing independently reconstructed native timestamp')
        require(r['access_policy']=='NO_TARGET_VALUE_READ' and
          r['source_SHA256']==runs[r['source_run_id']]['output_manifest_SHA256'],'Bad role or source')
        identifier=hashlib.sha256(f"{r['source_run_id']}|{r['cutoff_UTC']}|{lead}".encode()).hexdigest()
        require(identifier==r['sample_id'] and identifier not in expected_ids,'Invalid ID')
        expected_ids.add(identifier)
    computed = Counter(r['date'] for r in candidates)
    require(all(int(r['possible_endpoints'])==computed[d] and r['real_target_access']=='NOT_AUTHORIZED'
                for d,r in proposals.items()),'Proposal counts or permission mismatch')
    require(all(proposals[d]['state']=='EXCLUDED_BY_FROZEN_PROTOCOL' for d in sealed),'V37 exclusion lost')
    split_plan = []
    for r in candidates:
        d = r['date']
        if d not in ('2021-09-23','2021-09-24','2022-09-23','2022-09-24'):
            continue
        family = runs[r['source_run_id']]['forcing_family']
        split_plan.append(dict(r,split='engineering_train_candidate' if d[:4]=='2021' else
             'engineering_validation_candidate',forcing_family=family,
             label_authorization='NOT_AUTHORIZED',independent_science_test='NO'))
    audit_roles(split_plan,sealed)
    require(Counter(r['split'] for r in split_plan)=={'engineering_train_candidate':12,
        'engineering_validation_candidate':12},'Expected two cutoff days per candidate group')
    table('prospective_mvp_split.csv',split_plan)
    mvp_sources=[]
    for name in sorted({r['source_run_id'] for r in split_plan}):
        receipt = ROOT/name/'launch_once.json'
        argv = json.loads(receipt.read_text())['argv']
        model = ROOT/name
        for field in ('--model','--model-sha','--input-sha','--run-id'):
            require(field in argv,'Missing V58 MVP launch provenance')
        executable = ROOT / argv[argv.index('--model')+1]
        elf = argv[argv.index('--model-sha')+1]
        require(executable.resolve().is_relative_to(ROOT) and sha(executable)==elf,'Model binary SHA mismatch')
        require(sha(model/'input.inp')==argv[argv.index('--input-sha')+1],'Model input SHA mismatch')
        mvp_sources.append(dict(path=name,native_run_id=argv[argv.index('--run-id')+1],
            launch_receipt_SHA256=sha(receipt),model_ELF_SHA256=elf,
            GPI_SHA256=runs[name]['local_GPI_SHA256'],
            output_manifest_SHA256=runs[name]['output_manifest_SHA256'],
            authorization='NOT_AUTHORIZED'))
    save('prospective_mvp_sources.json',mvp_sources)
    # Reuse the exact V57 confined executable to replay a read attempt on a synthetic sentinel.
    marker = LOCAL/'synthetic'/'future.csv'
    result, probe = worker(marker.parent/'jail',marker)
    require(len(result)==3 and len(probe)==10,'Synthetic isolation replay failed')
    save('independent.json',dict(V57_publication_entries=len(manifest),V51_secondary_matching=46,
        V51_primary_identity='V57 frozen receipt; primary not scanned again',
        candidate_sample_checks=len(expected_ids),prospective_support_checks=len(split_plan),exact_duplicate_volume_groups=sum(len(v)>1 for v in group.values()),
        synthetic_filesystem_probe_assertions=len(probe),synthetic_split_positive=1,negatives=tests(sealed),
        baseline=coverage(),target_label_decodes=0,new_integrations=0,GPU=0,AI_training=0))


if __name__=='__main__':
    main()
