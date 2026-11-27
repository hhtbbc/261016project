"""Select event metadata, generate GFZ-only GPI and validate input decks without launches."""
import calendar
import csv
from datetime import datetime,timedelta,timezone
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import time

from netCDF4 import Dataset
import numpy as np

from analyze_direct_event_v61 import require,sha,csvread
from build_non_target_horizon_index_v56 import ROOT,V37,pin
from design_geomagnetic_events_v61 import catalog_events,bins,matches,iso,utc,H,BIN
from run_event_baselines_v62 import OUT,LOCAL,save,table
import prepare_tiegcm_training_drivers as builder

SOURCE=LOCAL/'Kp_ap_Ap_SN_F107_since_1932.txt'
URL='https://kp.gfz.de/fileadmin/files_for_gfz_cms/Kp_ap_Ap_SN_F107_since_1932.txt'
STUDY=ROOT/'experiments/thermosphere_direct_failure_event_v61'
SEED=ROOT/'data/raw/tiegcm_2021_spinup_initial_condition_v1/tiegcm_res5.0_mareqx_smax_prim.nc'
ELF=ROOT/'experiments/tiegcm2_apex2023_v1/tiegcm2.0'
TEMPLATE=ROOT/'experiments/thermosphere_autumn_mareqx_config_v23/2022/actual_run/input.inp'
DAY=24*H
YEARS=range(2021,2026)
V58=ROOT/'experiments/thermosphere_development_feasibility_v58'
POLICY=dict(years=[2021,2025],disturbed_subclasses='moderate peak [5,7), strong peak >=7; V61 disturbed class unchanged',
    event_windows='all complete 06Z/18Z cutoffs with history t-3 through target t+6 inside the core',
    spinup_days=14,force_padding_days=2,centered_solar_days=81,candidate_max_days=29,
    pair_rank='same year/same equinox seed season; disjoint complete integrations; closest core centers; moderate preferred only as final tie breaker',
    ensemble_rank='pair then two independent quiet/moderate/strong as available; event-support spacing >=72h; no cross-role integration overlap',
    season_eligibility='MAM/SON for mareqx_smax candidate; same seed for paired runs, distinguish spinup from convergence',
    provenance='exclude whole V58 model date ranges with 72h edge, V37 dates and known FourCastDEN dates; no guaranteed absence outside indexed local history')


def stamp(year,month=1,day=1):
    return datetime(year,month,day,tzinfo=timezone.utc)


def daily(a,b):
    return [a+i*DAY for i in range((b-a).days+1)]


def annual():
    source_rows={}
    kp={}
    fobs={}
    daily_kp={}
    for line in SOURCE.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        s=line.split()
        if int(s[0]) not in range(2020,2027):
            continue
        require(len(s)==28,'GFZ annual schema')
        d=stamp(*map(int,s[:3]))
        require(d not in source_rows,'Duplicate GFZ day')
        source_rows[d]=(float(s[25]),float(s[26]),int(s[27]))
        if float(s[25])>0:
            fobs[d]=float(s[25])
        if int(s[27]) in (1,2):
            for i,v in enumerate(map(float,s[7:15])):
                if 0<=v<=9:
                    kp[d+i*BIN]=v
    for y in YEARS:
        expected=daily(stamp(y),stamp(y,12,31))
        require(all(d in source_rows for d in expected),'Annual GFZ dates incomplete')
        daily_kp[y]=dict(days=len(expected),definitive_Kp_bins=sum((d+i*BIN) in kp for d in expected for i in range(8)),
          missing_Fobs=[d.date().isoformat() for d in expected if d not in fobs],
          missing_Fadj=[d.date().isoformat() for d in expected if source_rows[d][1]<=0])
    return kp,fobs,source_rows,daily_kp


def midnight(t):
    return t.replace(hour=0,minute=0,second=0,microsecond=0)


def ceil_day(t):
    a=midnight(t)
    return a if a==t else a+DAY


def touches(a,b,x,y):
    return a<y and x<b


def all_candidates(kp,fobs):
    v37=pin(V37)
    known=json.loads((STUDY/'event_summary.json').read_text())['FourCastDEN_archive_dates']
    history=[]
    for r in csvread(V58/'historical_data_inventory.csv'):
        if r['data_type']=='TIEGCM_SECONDARY' and r['date_start']>='2021':
            history.append((utc(r['date_start']),utc(r['date_end'])+H,r['dataset_id']))
    for date in sorted(set(v37['first_pair']+v37['later_pair']+known)):
        a=utc(date+'T00:00:00Z')
        history.append((a,a+DAY,date))
    result=[]
    for e in catalog_events(kp):
        a,b=utc(e['core_start']),utc(e['core_end_exclusive'])
        if a.year not in YEARS:
            continue
        left,right=utc(e['support_start']),utc(e['support_end_exclusive'])
        peak=max(kp[t] for t in kp if a<=t<b)
        cut=[d+i*H for d in daily(midnight(a),midnight(b)) for i in (6,18)
             if matches(e,d+(i-3)*H,d+(i+6)*H+timedelta(seconds=1))]
        first=cut[0]-3*H if cut else a
        lo=min(midnight(first)-14*DAY,midnight(left))
        hi=ceil_day(max(right,(cut[-1]+6*H) if cut else b))
        span=(hi-lo).days
        kdays=daily(lo-2*DAY,hi+2*DAY)
        solar_days=daily(kdays[0]-40*DAY,kdays[-1]+40*DAY)
        km=[iso(d+i*BIN) for d in kdays for i in range(8) if d+i*BIN not in kp]
        fm=[d.date().isoformat() for d in solar_days if d not in fobs]
        overlap=sorted({key for x,y,key in history if touches(left-72*H,right+72*H,x,y)})
        c='quiet' if e['kind']=='quiet' else 'disturbed_moderate' if peak<7 else 'disturbed_strong'
        season='MAM' if a.month in (3,4,5) else 'SON' if a.month in (9,10,11) else 'other'
        safe=e['Kp_complete'] and not overlap and not km and not fm and bool(cut) and lo.year==hi.year==a.year and span<=29
        result.append(dict(event_id=e['event_id'],class_V61=e['kind'],design_subclass=c,season=season,
         core_start=e['core_start'],core_end_exclusive=e['core_end_exclusive'],buffer_start=e['support_start'],
         buffer_end_exclusive=e['support_end_exclusive'],peak_Kp=peak,buffer_Kp_complete=e['Kp_complete'],
         prediction_cutoffs=';'.join(iso(t) for t in cut),cutoff_count=len(cut),
         model_start=iso(lo),model_end=iso(hi),integration_days=span,spinup_h_at_first_input=(first-lo)/H,
         Kp_days=span+5,missing_Kp=';'.join(km),missing_Fobs=';'.join(fm),
         Fobs_first=solar_days[0].date().isoformat(),Fobs_last=solar_days[-1].date().isoformat(),
         history_overlap=';'.join(overlap),public_lawful_source='GFZ annual combined; definitive Kp only',
         seed_eligible_for_proposal=season!='other',full_metadata_candidate=safe,
         same_seed_pair_candidate=safe and season!='other',
         dataset_state='DEN_NOT_PRODUCED_OR_AUTHORIZED'))
    return result


def separated(a,b):
    return utc(a['buffer_end_exclusive'])+72*H<=utc(b['buffer_start']) or utc(b['buffer_end_exclusive'])+72*H<=utc(a['buffer_start'])


def disjoint_runs(a,b):
    return not touches(utc(a['model_start']),utc(a['model_end']),utc(b['model_start']),utc(b['model_end']))


def first_pair(rows):
    pp=[r for r in rows if r['same_seed_pair_candidate']]
    def rank(q,s):
        return (abs((utc(q['core_start'])-utc(s['core_start'])).total_seconds()),
                q['integration_days']+s['integration_days'],s['design_subclass']!='disturbed_moderate',
                q['event_id'],s['event_id'])
    combos=sorted(((q,s) for q in pp if q['design_subclass']=='quiet' for s in pp
                  if s['class_V61']=='disturbed' and q['core_start'][:4]==s['core_start'][:4] and
                     q['season']==s['season'] and separated(q,s) and disjoint_runs(q,s)),
                 key=lambda p:rank(*p))
    require(bool(combos),'No compatible event pair')
    return combos


def historical():
    august=[]
    for year in (2021,2022):
        d=ROOT/f'experiments/thermosphere_autumn_mareqx_config_v23/{year}/actual_run'
        status=json.loads((d/'status.json').read_text())
        nv=sum(p.stat().st_size for p in d.glob('*.nc'))
        august.append(dict(id=f'autumn_{year}',days=16,elapsed_s=status['elapsed_s'],nc_bytes=nv,
                           mpi_ranks=4,omp_threads=1,source=str((d/'status.json').relative_to(ROOT))))
    run=ROOT/'experiments/thermosphere_summer_seed_execution_v48/result.json'
    r=json.loads(run.read_text())
    august.append(dict(id='summer14_spinup_plus_2d',days=16,elapsed_s=r['run']['elapsed_s'],
       nc_bytes=sum(p.stat().st_size for p in (ROOT/'experiments/thermosphere_summer_seed_recovery_v47/run_B_junsol_recovery').glob('*.nc')),
       mpi_ranks=4,omp_threads=1,source=str(run.relative_to(ROOT))))
    for role,run in [('A','run_A_mareqx_add7'),('B','run_B_junsol_add7')]:
        path=ROOT/f'experiments/thermosphere_summer_spinup_add7_execution_v51/engineering_{role}.json'
        r=json.loads(path.read_text())
        folder=ROOT/'experiments/thermosphere_summer_spinup_add7_v50'/run
        august.append(dict(id=f'summer21_spinup_plus_2d_{role}',days=23,elapsed_s=r['elapsed_s'],
             nc_bytes=sum(p.stat().st_size for p in folder.glob('*.nc')),mpi_ranks=4,omp_threads=1,
             source=str(path.relative_to(ROOT))))
    require(all(r['nc_bytes']>0 for r in august),'Missing historical size')
    return august


def estimate(r,s_day,b_day):
    n=r['integration_days']
    return dict(event_id=r['event_id'],start=r['model_start'],end=r['model_end'],days=n,
       steps_60s=n*1440,primary_volumes=n+1,secondary_volumes=n,hourly_DEN_frames=n*24,
       cutoff_count=r['cutoff_count'],targets=3*r['cutoff_count'],estimated_wall_s=round(n*s_day,1),
       rank_hours_at_4=round(n*s_day*4/3600,3),estimated_native_bytes=math.ceil(n*b_day),
       estimates_only=True)


def prepare(r,kp,fobs):
    lo,hi=utc(r['model_start']),utc(r['model_end'])
    d=LOCAL/('q' if r['class_V61']=='quiet' else 'd')
    require(d.resolve()==d,'Unsafe run directory')
    d.mkdir()
    for f,dest in [(SEED,'seed.nc')]:
        shutil.copyfile(f,d/dest)
        require(sha(f)==sha(d/dest),'Seed copy mismatch')
        (d/dest).chmod(0o444)
    with Dataset(d/'seed.nc') as n:
        dims={k:len(n.dimensions[k]) for k in ('ilev','lat','lon')}
        require(dims=={'ilev':29,'lat':36,'lon':72} and
                np.any(np.all(n['mtime'][:]==[80,0,0],axis=1)),'Seed calendar or grid')
    grid,f,a,k=builder.arrays(fobs,kp,(lo-2*DAY).date(),(hi+2*DAY).date())
    gpi=d/'gpi.nc'
    builder.write_gpi(gpi,grid,f,a,k,lo.date(),hi.date())
    with Dataset(gpi) as n:
        require(n.data_model=='NETCDF3_CLASSIC','GPI file type')
        actual=n['f107a'][:]
        for idx,g in enumerate(grid):
            day=stamp(g.year,g.month,g.day)
            require(abs(actual[idx]-math.fsum(fobs[day+j*DAY] for j in range(-40,41))/81)<1e-12 and
                    np.array_equal(n['kp'][idx],np.asarray([kp[day+j*BIN] for j in range(8)])),'Independent GPI')
    gpi.chmod(0o444)
    lines=TEMPLATE.read_text()
    count=r['integration_days']
    vols=lambda tag,n:',\n           '.join(', '.join(f"'{tag}_{i:03}.nc'" for i in range(first,min(first+5,n+1)))
                                          for first in range(1,n+1,5))
    fields={'LABEL':"'V62 PROSPECTIVE EVENT HINDCAST'",'START_YEAR':str(lo.year),
            'START_DAY':lo.strftime('%j'),'SOURCE':"'seed.nc'",'START':lo.strftime('%j')+' 0 0',
            'STOP':hi.strftime('%j')+' 0 0','OUTPUT':vols('primary',count+1),
            'SECSTART':lo.strftime('%j')+' 1 0','SECSTOP':hi.strftime('%j')+' 0 0',
            'SECOUT':vols('secondary',count),'GPI_NCFILE':"'gpi.nc'"}
    for key,value in fields.items():
        lines,n=re.subn(r'^\s*'+key+r'\s*=.*$',lambda _:f' {key} = {value}',lines,flags=re.M)
        require(n==1,'Input template field not unique '+key)
    # Verify the old 120-character SOURCE path problem under absolute expansion.
    source_chars=len(os.fsencode(d/'seed.nc'))
    require(source_chars<120 and len(os.fsencode(d))<120 and len(os.fsencode(d/'gpi.nc'))<120
        and max(map(len,lines.splitlines()))<1024 and 'SOURCE_START = 80 0 0' in lines,'Fortran path/line limit')
    for g in ('gswm_diurn_5.0d_99km.nc','gswm_semi_5.0d_99km.nc'):
        require((ROOT/'data/raw/tiegcm2_support'/g).is_file(),'Missing tide forcing')
    require('HEELIS' in lines and re.search(r"'DEN'",lines),'Physics or DEN output changed')
    (d/'input.inp').write_text(lines)
    (d/'input.inp').chmod(0o444)
    return dict(event_id=r['event_id'],directory=str(d.relative_to(ROOT)),template_SHA256=sha(TEMPLATE),
        seed_original=str(SEED.relative_to(ROOT)),seed_sha256=sha(SEED),GPI_sha256=sha(gpi),
        input_sha256=sha(d/'input.inp'),model_ELF_SHA256=sha(ELF),source_path_bytes=source_chars,
        all_local_inputs_present=True,source_day80_from_equinox=True,den_fields_metadata_only=True,
        preflight='Static verified; model executable not invoked; V63 authorization and supervisor required',
        post_run_acceptance='exact registered 60s steps, exit/rank success, output cadence/shape/units/SHA and confirmed forcing; DEN sealed after indexing')


def dataset_plans(rows,pair,cost):
    allocated={'LOCKED_INDEPENDENT_TEST':list(pair),'TRAIN':[],'MODEL_SELECTION_VALIDATION':[]}
    selected=list(pair)
    for role,number in [('MODEL_SELECTION_VALIDATION',1),('TRAIN',2)]:
        for cls in ('quiet','disturbed'):
            for r in sorted((x for x in rows if x['same_seed_pair_candidate'] and x['class_V61']==cls),
                            key=lambda x:(x['integration_days'],x['core_start'])):
                if all(separated(r,x) and disjoint_runs(r,x) for x in selected):
                    allocated[role].append(r)
                    selected.append(r)
                    if sum(x['class_V61']==cls for x in allocated[role])==number:
                        break
    require(len(selected)==8,'Insufficient base roles')
    expanded={k:list(v) for k,v in allocated.items()}
    all_selected=list(selected)
    desired=[('TRAIN',12),('MODEL_SELECTION_VALIDATION',6),('LOCKED_INDEPENDENT_TEST',6)]
    for role,n in desired:
        for r in sorted((x for x in rows if x['same_seed_pair_candidate']),
                        key=lambda x:(x['class_V61']!='disturbed',x['season']=='SON',x['integration_days'],x['core_start'])):
            existing=expanded[role]
            c=r['design_subclass']
            if sum(x['class_V61']==r['class_V61'] for x in existing)>=n//2:
                continue
            if r['class_V61']=='disturbed' and sum(x['design_subclass']==c for x in existing)>=math.ceil(n/4):
                continue
            if all(separated(r,x) and disjoint_runs(r,x) for x in all_selected):
                existing.append(r)
                all_selected.append(r)
                if len(existing)==n:
                    break
    def summarize(groups):
        rr=[r for a in groups.values() for r in a]
        est=[cost[r['event_id']] for r in rr]
        return dict(roles={k:[r['event_id'] for r in a] for k,a in groups.items()},
          events=len(rr),quiet=sum(r['class_V61']=='quiet' for r in rr),disturbed=sum(r['class_V61']=='disturbed' for r in rr),
          strong=sum(r['design_subclass']=='disturbed_strong' for r in rr),
          years=sorted({r['core_start'][:4] for r in rr}),seasons=sorted({r['season'] for r in rr}),
          cutoffs=sum(r['cutoff_count'] for r in rr),targets=3*sum(r['cutoff_count'] for r in rr),
          estimated_wall_hours=sum(r['estimated_wall_s'] for r in est)/3600,
          estimated_native_GiB=sum(r['estimated_native_bytes'] for r in est)/2**30)
    return dict(A=summarize({'LOCKED_INDEPENDENT_TEST':pair}),B=summarize(allocated),C=summarize(expanded),
      C_goal='24 events; actual design availability tabulated; engineering start only, not a power claim',
      comparison=dict(A_event_cold_start='Matched physical setup and simple leakage isolation; preferred first',
        B_continuous='Only within same role; integrate gaps only when cheaper than another 14-day spin-up',
        C_extraction='Keep all native outputs initially, after acceptance store selected-hour DEN plus headers; no new continuous restart',
        D_archive='GDEX d947640 covers 2014-2024 but TIEGCM 3.0, 2.5 deg, 15 min; separate transfer study, not native 2.0 substitute'),
      statistical_contract='06Z/18Z design; optional hourly windows increase within-event correlation, never independent event n')


def main():
    t=time.monotonic()
    require(OUT.resolve()==OUT and SOURCE.resolve()==SOURCE and SOURCE.is_file(),'Unsafe/missing official driver file')
    save('event_selection_protocol.json',POLICY)
    kp,fobs,raw,annual_rows=annual()
    dated=sorted(raw)
    headers=(LOCAL/'gfz_headers.txt').read_text()
    download_date=re.findall(r'^Date: (.*)$',headers,re.M)[-1].strip()
    last_modified=re.findall(r'^Last-Modified: (.*)$',headers,re.M)[-1].strip()
    save('gfz_source_manifest.json',dict(source_URL=URL,source_sha256=sha(SOURCE),bytes=SOURCE.stat().st_size,
          stored_path=str(SOURCE.relative_to(ROOT)),server_Date=download_date,last_modified=last_modified,
          retrieval_window_UTC=['2026-11-27T07:58:20Z','2026-11-27T07:58:24Z'],
          source_format='GFZ combined ASCII snapshot; Kp DOI 10.5880/Kp.0001 V1.0; full original bytes local',
          raw_first_UT_day='1932-01-01',raw_last_UT_day=SOURCE.read_text().splitlines()[-1][:10].replace(' ','-'),
          parsed_context=[dated[0].date().isoformat(),dated[-1].date().isoformat()],
          annual=annual_rows,Kp='three-hour UTC starts, D=1/2 only',Fobs='daily observed sfu; adjusted Fadj at nominal unit distance kept separate',
          missing='-1, excluded; no correction to the V37 historical forcing'))
    rows=all_candidates(kp,fobs)
    table('geomagnetic_event_candidates.csv',rows)
    combos=first_pair(rows)
    pair=list(combos[0])
    alternative=list(combos[1]) if len(combos)>1 else []
    save('selected_event_pairs.json',dict(primary=pair,fallback=alternative,role='LOCKED_INDEPENDENT_TEST_CANDIDATE',
      counts_all_by_class={k:sum(r['design_subclass']==k for r in rows) for k in ('quiet','disturbed_moderate','disturbed_strong')},
      counts_metadata_eligible_by_class={k:sum(r['design_subclass']==k and r['full_metadata_candidate'] for r in rows)
        for k in ('quiet','disturbed_moderate','disturbed_strong')},production_or_label_authorization=False))
    measured=historical()
    s_day=max(r['elapsed_s']/r['days'] for r in measured)
    b_day=max(r['nc_bytes']/r['days'] for r in measured)
    save('historical_cost_sources.json',dict(measured=measured,estimate_wall_seconds_per_day=s_day,estimate_bytes_per_day=b_day,
      caveat='Scaling at 4 MPI ranks, OMP=1; no guarantee; 25% extra runtime and disk buffer requested'))
    estimates={r['event_id']:estimate(r,s_day,b_day) for r in rows if r['full_metadata_candidate']}
    table('simulation_cost_estimates.csv',list(estimates.values()))
    plans=dataset_plans(rows,pair,estimates)
    save('event_dataset_production_plan.json',plans)
    proofs=[prepare(r,kp,fobs) for r in pair]
    table('forcing_completeness.csv',[{k:r[k] for k in ('event_id','Kp_days','missing_Kp','missing_Fobs','Fobs_first',
     'Fobs_last','buffer_Kp_complete','spinup_h_at_first_input')} for r in pair])
    save('prepared_run_config_manifest.json',dict(preflight_runs=proofs,launch_count=0,ELF=str(ELF.relative_to(ROOT)),
       reference_seed='mareqx smax; seasonal proxy warning; identical cold start both runs; no Restart',
       limits=dict(MPI_ranks=4,OMP_threads=1,gpu=False,RSS_GiB=4,each_wall_s=6000,each_disk_GiB=8)))
    # Legacy launcher evidence. A stable archive hash is recorded separately from a native run ID.
    legacy=[]
    lookup={r['run']:r for r in json.loads((V58/'model_runs.json').read_text())}
    for d in ('experiments/tiegcm_2021_spinup_14day_v1/A14','experiments/tiegcm_2022_b14_exploratory_pair_v2/B14',
              'experiments/tiegcm_2022_mar25_execution_review_v1/actual_run'):
        f=ROOT/d
        candidates=[f/name for name in ('launch_once.json','run_status.json','status.json','runtime_environment.json') if (f/name).is_file()]
        launch=json.loads((f/'launch_once.json').read_text())
        argv=launch.get('argv',[])
        rid=argv[argv.index('--run-id')+1] if '--run-id' in argv else lookup[d].get('run_id')
        legacy.append(dict(run=d,native_run_id=rid,identity_state='VERIFIED_ARCHIVE_WITH_NATIVE_ID' if rid else 'LEGACY_LAUNCH_WITHOUT_NATIVE_ID',
            evidence={str(p.relative_to(ROOT)):sha(p) for p in candidates},archive_output_manifest_sha=lookup[d]['output_manifest_SHA256']))
    marked=json.loads((STUDY/'next_stage_authorization.json').read_text())['smallest_new_data_MVP']['train'][-2:]
    save('legacy_run_identity_recovery.json',dict(archives=legacy,resolved_missing_cutoffs=0,
         legacy_label_access='NOT_AUTHORIZED',known_Mar25=marked))
    save('next_stage_execution_authorization.json',dict(state='NOT_AUTHORIZED',requested_action='V63 one cold-start CPU launch per listed event, via audited supervisor',
        signed_config_manifest_sha256=sha(OUT/'prepared_run_config_manifest.json'),
        accepted_after_run='Seal current targets; approve DEN evaluation separately and freeze preregistered baselines',
        runs=[dict(**estimates[r['event_id']],cutoff_UTC=r['prediction_cutoffs'].split(';'),history_hours=[-3,-2,-1],
            target_hours=[1,3,6],fields=['DEN','time','lat','lon','ilev'],role='LOCKED_INDEPENDENT_TEST_CANDIDATE')
              for r in pair],parallel_development_label_request=dict(identity=legacy[-1],exact_scope=marked,
              fields=['DEN','time','lat','lon','ilev'],role='HISTORICAL_DEVELOPMENT_NOT_INDEPENDENT_TEST'),
        launcher=dict(method='Existing project audited MPI supervisor adapted to each prepared directory',
          projectroot=str(ROOT),mpi_ranks=4,omp_threads=1,cuda_visible_devices='',
          prelaunch=['Recheck GPI/seed/deck/ELF SHAs and resource availability','Gate explicit V63 approval per event',
                     'Ensure no prior launch or output; store exit/rank receipts and retain failed attempts'],
          never_automatic=True)))
    save('production_resources.json',dict(seconds=time.monotonic()-t,RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        affinity=len(os.sched_getaffinity(0)),free_disk=shutil.disk_usage(ROOT).free,new_integrations=0))
    print([r['event_id'] for r in pair],{n:plans[n]['events'] for n in ('A','B','C')})


if __name__=='__main__':
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    main()
