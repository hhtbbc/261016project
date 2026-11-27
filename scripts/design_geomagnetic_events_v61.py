"""Classify existing definitive Kp and V58 model-time inventory; never opens a DEN file."""
from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone
from itertools import groupby
import json
import math
import re

from analyze_direct_event_v61 import ROOT, OUT, R60, csvread, table, save, require, sha
from build_non_target_horizon_index_v56 import V37, pin

OLD=ROOT/'experiments/thermosphere_development_feasibility_v58'
RAW=ROOT/'data/raw'
H=timedelta(hours=1)
BIN=3*H
MARGIN=24*H
RULE=dict(quiet_Kp_max=2.0,quiet_min_hours=48,disturbed_Kp_min=5.0,
          merge_disturbed_gap_hours=72,disturbed_pre_hours=24,disturbed_post_hours=48,
          minimum_between_event_supports_hours=72, minimum_elapsed_spinup_days=14,
          moderate_or_unclassified='Exclude from quiet/disturbed claims, retain metadata',
          selection='Kp and source metadata only; class thresholds fixed before new DEN decoding',
          validation_roles=['TRAIN','MODEL_SELECTION_VALIDATION','LOCKED_INDEPENDENT_TEST'],
          scientific_independence='No historical analysis or model selection exposure; whole events, runs and forcing families cannot straddle assignments')


def utc(t):
    return datetime.fromisoformat(t.replace('Z','+00:00'))


def iso(t):
    return t.isoformat().replace('+00:00','Z')


def ranges(values,step):
    for _,rows in groupby(enumerate(sorted(values)),lambda iv:iv[1]-iv[0]*step):
        part=[v for _,v in rows]
        yield part[0],part[-1]+step


def bins(kp,start,end):
    t=start.replace(hour=3*(start.hour//3),minute=0,second=0,microsecond=0)
    result=[]
    while t<end:
        result.append(kp.get(t))
        t+=BIN
    return result


def kp_catalogue():
    paths=sorted({p for pattern in ('*Kp*.json','*Kp*.txt') for p in RAW.rglob(pattern)
                  if p.is_file() and p.resolve()==p and not p.name.endswith('_source.json')})
    rows={}
    receipts=[]
    for p in paths:
        try:
            raw=json.loads(p.read_text())
        except ValueError:
            continue
        if 'Kp' not in raw:
            continue
        require(raw['meta']['source']=='GFZ Potsdam','Kp provenance')
        require(len(raw['datetime'])==len(raw['Kp'])==len(raw['status']),'Mismatched Kp arrays')
        valid=[(utc(t),float(v)) for t,v,s in zip(raw['datetime'],raw['Kp'],raw['status'])
               if s=='def' and 0<=v<=9]
        for t,v in valid:
            require(t.hour%3==0 and t.minute==t.second==0,'Kp cadence')
            require(abs(rows.setdefault(t,v)-v)<.001,'Conflicting definitive Kp')
        receipts.append(dict(source=str(p.relative_to(ROOT)),sha256=sha(p),definitive_bins=len(valid)))
    p=RAW/'f107_2021_recovery_v1/gfz_year.txt'
    known=json.loads((ROOT/'experiments/thermosphere_autumn_gpi_seed_policy_v22/gpi_audit_2021.json').read_text())
    require(sha(p)==known['input_SHA256'][str(p.relative_to(ROOT))],'GFZ 2021 frozen archive')
    count=0
    for line in p.read_text().splitlines():
        cols=line.split()
        if not cols or cols[0]!='2021' or cols[27]!='2':
            continue
        base=datetime(*map(int,cols[:3]),tzinfo=timezone.utc)
        for i,raw in enumerate(cols[7:15]):
            v=float(raw)
            if 0<=v<=9:
                t=base+i*BIN
                require(abs(rows.setdefault(t,v)-v)<.001,'Conflicting GFZ annual Kp')
                count+=1
    receipts.append(dict(source=str(p.relative_to(ROOT)),sha256=sha(p),definitive_bins=count))
    return rows,receipts


def catalog_events(kp):
    storm=[]
    for t in sorted(t for t,v in kp.items() if v>=RULE['disturbed_Kp_min']):
        if storm and t-storm[-1][1]<=RULE['merge_disturbed_gap_hours']*H:
            storm[-1][1]=t+BIN
        else:
            storm.append([t,t+BIN])
    events=[]
    for klass,runs in [('disturbed',storm),('quiet',ranges((t for t,v in kp.items() if v<=2),BIN))]:
        for a,b in runs:
            left,right=(a-24*H,b+48*H) if klass=='disturbed' else (a,b)
            if klass=='quiet' and ((b-a)<48*H or any(a<e+48*H and b>s-24*H for s,e in storm)):
                continue
            hits=bins(kp,left,right)
            events.append(dict(event_id=f'{klass}_{a:%Y%m%dT%H}',kind=klass,
              core_start=iso(a),core_end_exclusive=iso(b),support_start=iso(left),support_end_exclusive=iso(right),
              Kp_complete=all(v is not None for v in hits),peak_Kp=max(v for v in hits if v is not None)))
    return sorted(events,key=lambda e:e['core_start'])


def matches(event,lo,hi):
    return event['Kp_complete'] and utc(event['core_start'])<=lo and hi<=utc(event['core_end_exclusive'])


def launch_info(path,run):
    p=ROOT/path/'launch_once.json'
    d=json.loads(p.read_text()) if p.is_file() else {}
    argv=d.get('argv',[])
    rid=run.get('run_id') or (argv[argv.index('--run-id')+1] if '--run-id' in argv else '')
    text=''
    for f in ('input.inp','input.namelist'):
        p=ROOT/path/f
        if p.is_file() and p.resolve()==p:
            text=p.read_text()
            break
    def value(key):
        hit=re.search(r'^\s*'+key+r'\s*=\s*(.+)$',text,re.M)
        return hit.group(1).strip(" '\",") if hit else ''
    year=value('START_YEAR')
    day=value('START_DAY')
    start=datetime(int(year),1,1,tzinfo=timezone.utc)+timedelta(days=int(day)-1) if year and day else None
    model=run.get('model_sha256') or (argv[argv.index('--model-sha')+1] if '--model-sha' in argv else '')
    return rid,start,value('SOURCE'),model


def main():
    save('event_rules_frozen.json',RULE)
    kp,provenance=kp_catalogue()
    ev=catalog_events(kp)
    rows=csvread(OLD/'candidate_endpoints.csv')
    runmap={r['run']:r for r in json.loads((OLD/'model_runs.json').read_text())}
    inv={r['dataset_id']:r for r in csvread(OLD/'historical_data_inventory.csv') if r['data_type']=='TIEGCM_SECONDARY'}
    proto=pin(V37)
    sealed=set(proto['first_pair']+proto['later_pair'])
    known_fc=sorted({p.name[:10].replace('_','-') for p in RAW.glob('fourcastden*/*.npz')
                     if re.match(r'20\d\d_\d\d_\d\d_',p.name)})
    used={'2021-03-23','2021-03-24','2021-03-25','2022-03-23','2022-03-24','2022-03-25',
          '2021-09-23','2021-09-24','2022-09-23','2022-09-24',*known_fc}
    by=defaultdict(list)
    pair={}
    for r in rows:
        by[r['source_run_id'],r['cutoff_UTC']].append(r)
    for run in {r['source_run_id'] for r in rows}:
        pair[run]=launch_info(run,runmap[run])
    candidate=[]
    for (run,cut),samples in sorted(by.items()):
        samples.sort(key=lambda x:int(x['horizon']))
        times=[int(r['horizon']) for r in samples]
        start=min(utc(r['input_start_UTC']) for r in samples)
        end=max(utc(r['target_support_end_UTC_exclusive']) for r in samples)
        rid,t0,seed,model=pair[run]
        elapsed=(start-t0)/H if t0 else None
        family=runmap[run]['forcing_family']
        dates={start.date().isoformat(),end.date().isoformat()}
        blocked=family=='2022_summer_shared_forcing' or bool(dates&sealed)
        qualified=times==[1,3,6] and not blocked and elapsed is not None and elapsed>=336
        kps=bins(kp,start,end)
        complete=all(v is not None for v in kps)
        events=[e for e in ev if matches(e,start,end)] if complete else []
        # Distinct role from authorization; the entire local archive already has diagnostic exposure.
        past='V59/V60 already used' if family.startswith('autumn') and cut[:10] in used else (
             'FourCastDEN date or historical observation/development used' if dates&used else
             'Source run used in prior spinup/sensitivity or engineering studies')
        role=('D' if not qualified or not rid or not model else 'A')
        candidate.append(dict(cutoff_UTC=cut,run_id=rid or 'UNRESOLVED',run=run,
             support_start_UTC=iso(start),support_end_exclusive_UTC=iso(end),
             available_leads=';'.join(map(str,times)),sample_ids=';'.join(r['sample_id'] for r in samples),
             source_start=inv[run]['date_start'],source_end=inv[run]['date_end'],
             source_grid='29x36x72',source_resolution_s=inv[run]['sample_resolution'],
             source_longest_hourly=runmap[run]['longest_hourly_streak'],version='TIE-GCM-2.0',
             model_ELF_SHA256=model or 'UNRESOLVED',seed=seed or 'UNRESOLVED',
             warmup_hours_at_first_input=elapsed,forcing_family=family,V37_or_sealed_family=blocked,
             prior_use=past,history_access='V59/V60 only' if past=='V59/V60 already used' else 'METADATA_ONLY',
             wet14_complete=qualified,Kp_complete=complete,peak_Kp=max([v for v in kps if v is not None],default=''),
             geomagnetic_class=events[0]['kind'] if len(events)==1 else 'unclassified',
             event_id=events[0]['event_id'] if len(events)==1 else '',
             role=role,role_gate='A: provisional training extension, separate DEN authorization and identity required' if qualified else
               'D: sealed family, incomplete leads, insufficient warmup or unresolved identity',
             historical_FourCastDEN_overlap=bool(dates&set(known_fc))))
    eventcuts=defaultdict(list)
    for r in candidate:
        if r['event_id']:
            eventcuts[r['event_id']].append(r)
    eventrows=[]
    for e in ev:
        members=eventcuts[e['event_id']]
        eligible=[r for r in members if r['wet14_complete']]
        eventrows.append(dict(**e,candidate_cutoffs=len(members),warm_nonsealed_cutoffs=len(eligible),
          already_used_cutoffs=sum(r['history_access']=='V59/V60 only' for r in eligible),independent_test_eligible=0,
          runs=';'.join(sorted({r['run'] for r in members}))))
    table('candidate_cutoff_inventory.csv',candidate)
    table('candidate_event_inventory.csv',eventrows)
    v60={r['cutoff_UTC'] for r in csvread(R60/'sample_scope.csv')}
    possible=[r for r in candidate if r['wet14_complete']]
    used20=[r for r in possible if r['cutoff_UTC'] in v60]
    later=[r for r in possible if r['cutoff_UTC'] not in v60]
    train=[r for r in used20 if r['cutoff_UTC'].startswith('2021')]
    validation=[r for r in used20 if r['cutoff_UTC'].startswith('2022')]
    # Expanded training uses only spring families, never the 2022 autumn historical comparison.
    train_sources=train+[r for r in later if 'spring' in r['forcing_family']]
    for r in train_sources:
        require(not r['V37_or_sealed_family'] and r['wet14_complete'],'Proposal leakage')
        require(all(r['run']!=q['run'] and r['forcing_family']!=q['forcing_family'] and
           (r['support_end_exclusive_UTC']<=q['support_start_UTC'] or
            q['support_end_exclusive_UTC']<=r['support_start_UTC']) and
           (not r['event_id'] or r['event_id']!=q['event_id']) for q in validation),'Proposal split leakage')
    save('event_summary.json',dict(
      metadata_endpoints=len(rows),metadata_cutoffs=len(candidate),complete_three_lead_cutoffs=sum(r['available_leads']=='1;3;6' for r in candidate),
      warm_nonsealed_cutoffs=len(possible),already_authorized_diagnostic_cutoffs=len(used20),additional_candidate_cutoffs=len(later),
      warm_cutoffs_with_verified_native_identity=sum(r['role']=='A' for r in possible),
      warm_dates=len({r['cutoff_UTC'][:10] for r in possible}),
      events_with_any_model_cutoff=dict(Counter(e['kind'] for e in eventrows if e['candidate_cutoffs'])),
      events_with_warm_nonsealed_cutoff=dict(Counter(e['kind'] for e in eventrows if e['warm_nonsealed_cutoffs'])),
      classified_warm_cutoffs=dict(Counter(r['geomagnetic_class'] for r in possible)),
      proven_independent_test_events=0,FourCastDEN_archive_dates=known_fc,kp_sources=provenance,
      minimum_train_cutoffs=len(train),planned_expanded_train_cutoffs=len(train_sources),
      engineering_validation_already_used_cutoffs=len(validation)))
    mapping=lambda rr:[{k:r[k] for k in ('run_id','run','cutoff_UTC','support_start_UTC','support_end_exclusive_UTC',
                             'sample_ids','event_id','forcing_family','role')} | dict(
        history_UTC=[iso(utc(r['cutoff_UTC'])+n*H) for n in (-3,-2,-1)],
        target_UTC=[iso(utc(r['cutoff_UTC'])+n*H) for n in (1,3,6)]) for r in rr]
    doc=dict(state='PROPOSED_NOT_AUTHORIZED',minimum=dict(TRAIN=mapping(train),MODEL_SELECTION_VALIDATION=[],
             ENGINEERING_VALIDATION_ALREADY_USED=mapping(validation),LOCKED_INDEPENDENT_TEST=[]),
             expanded=dict(TRAIN=mapping(train_sources),MODEL_SELECTION_VALIDATION=[],
             ENGINEERING_VALIDATION_ALREADY_USED=mapping(validation),LOCKED_INDEPENDENT_TEST=[]),
             blockers=['Resolve legacy run identity and provenance before labels','Acquire unexposed events for selection and testing',
             'Any Kp-missing or moderate block stays unclassified','Do not promote field skill from a used archive'])
    doc['future_science_metrics']=dict(primary='event-macro log RMSE at each lead on common valid cells',
        secondary=['global absolute RMSE','relative RMSE','MAE','bias','each ilev and latitude zone'],
        safeguards=['report native-layer and hemisphere polar log RMSE at all leads',
          'low-density threshold from training target fifth percentile stratified by native ilev',
          'positive/finite coverage at least Persistence, no hidden point removal',
          'absolute RMSE alone does not satisfy skill recommendation'],
        inference='paired events, no significance claim without sufficiently many independent events',
        provenance='engineering validation remains used; separate selection and locked test events required')
    save('data_split_preregistration.json',doc)
    save('next_stage_authorization.json',dict(state='REQUEST_ONLY_NOT_GRANTED',fields=['DEN','time','lat','lon','ilev'],
       history_hours=[-3,-2,-1],label_hours=[1,3,6],requirements=['Explicit approval per run and listed UTC support',
       '2022 engineering labels only after prediction lock; all unseen and V37 labels remain closed',
       'Missing legacy run_id requires source receipt before data access',
       'Freeze model config, scalers from training history and evaluation before any independent test unlock'],
       minimal_repeat=dict(train=mapping(train),engineering_validation=mapping(validation)),
       smallest_new_data_MVP=dict(train=mapping([r for r in train_sources if r['role']=='A']),
                                 engineering_validation=mapping(validation)),
       expanded_request=dict(train=mapping(train_sources),engineering_validation=mapping(validation)),
       science_split_status='BLOCKED: no new independent test or selection block',
       budget=dict(CPU_threads=4,RSS_GiB=4,max_seconds=1800,
         minimal_float32_payload_MiB=round((len(train)+len(validation))*6*29*36*72*4/2**20,1),
         expanded_float32_payload_MiB=round((len(train_sources)+len(validation))*6*29*36*72*4/2**20,1))))


if __name__=='__main__':
    main()
