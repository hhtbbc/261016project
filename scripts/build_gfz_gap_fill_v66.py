"""Researcher-filled 2021 candidate drivers. No model execution or gate change."""
import math
from datetime import datetime,timedelta,timezone

import numpy as np
from netCDF4 import Dataset

from run_validation_events_v66 import ROOT,V62,sha,load,write_once,require,annual
from run_native_density_baselines_v59 import table
from atmosphere.tiegcm_drivers import GpiDriver
from atmosphere.autumn_gpi_validation import independent_at
from check_external_evidence_v55 import STAGING,check
import prepare_tiegcm_training_drivers as builder

OUT=ROOT/'experiments/thermosphere_gfz_gap_fill_v66'
DAY=timedelta(days=1)
ZERO=timezone.utc
D1,D2=(datetime(2021,m,d,tzinfo=ZERO) for m,d in ((5,9),(6,16)))
START=datetime(2021,5,31,tzinfo=ZERO)
END=datetime(2021,6,23,tzinfo=ZERO)


def references():
    downloads=load(OUT/'public_reference_checks.json')
    require(downloads['arrl']['http_status']=='200' and downloads['noaa_dsd']['http_status']=='200',
            'Independent document checks')
    for k in ('arrl','noaa_dsd'):
        p=OUT/'data_local'/f'{k}.body'
        require(sha(p)==downloads[k]['sha256'],'Public evidence SHA')
    body=(OUT/'data_local/arrl.body').read_text()
    require(all(s in body for s in ('76.9 at 1700 UTC','77.1 at 2300 UTC','77 as a reasonable approximation')),
            'ARRL 20Z evidence')
    noaa={}
    for line in (OUT/'data_local/noaa_dsd.body').read_text().splitlines():
        s=line.split()
        if s[:3] in (['2021','05','09'],['2021','06','16']):
            noaa['-'.join(s[:3])]=float(s[3])
    require(noaa=={'2021-05-09':76.,'2021-06-16':76.},'NOAA quarterly compilation evidence')
    evidence=dict(issuer='GFZ',document_id='V66-user-relayed-GFZ-correspondence',
                  version_or_date='User-provided V66 correspondence summary; reply date not supplied',
                  public_reference=downloads['canada']['url'],
                  dates=['2021-05-09','2021-06-16'],
                  observation_definition='Canadian Penticton unadjusted F10.7 at 20:00 UTC; GFZ republishes',
                  responder='Oliver Bronkalla',forwarded_by='Jürgen Matzka',
                  findings={'2021-05-09':'No underlying row in GFZ local Canadian snapshot',
                            '2021-06-16':'No 20Z row. 17Z observed 76.9 and 23Z observed 77.1 sfu'},
                  public_reference_candidates={'may_9':downloads['xras']['url'],'june_16':downloads['arrl']['url']},
                  NOAA_DSD_compiled_integer_sfu=noaa,public_checks=downloads,
                  states=['GFZ_MISSING_REASON_CLARIFIED','GFZ_REFERENCE_VALUES_RECEIVED',
                          'ORIGINAL_20Z_OBSERVATIONS_NOT_RECOVERED','GAP_FILL_POLICY_PENDING_REVIEW',
                          'GFZ_2021_GAP_UNRESOLVED'],
                  provenance='User relayed reply with public cross-check; no signature or GFZ data revision')
    target=STAGING/'GFZ_2021_evidence.json'
    require(STAGING.resolve()==STAGING and target.resolve()==target and not target.exists(),
            'Existing evidence staging path')
    staged={k:v for k,v in evidence.items() if k not in ('public_checks',)}
    write_once(target,staged)
    write_once(OUT/'gfz_reply_evidence.json',evidence)
    checked=check()
    require(checked['candidates'][target.name]['state']=='RECEIVED_PENDING_AUTHORITY_REVIEW','V55 contract')
    write_once(OUT/'V55_handoff_check.json',checked)


def main():
    require(OUT.resolve()==OUT,'Unsafe proposal directory')
    references()
    m=load(V62/'gfz_source_manifest.json')
    p=ROOT/m['stored_path']
    require(sha(p)==m['source_sha256'],'Immutable GFZ original')
    kp,observed,_,_=annual()
    require(D1 not in observed and D2 not in observed,'GFZ original gap changed')
    neighbor={d:[observed[d-DAY],observed[d+DAY]] for d in (D1,D2)}
    variants={
        'A_reference_same_day':(76.,(76.9+77.1)/2),
        'B_adjacent_observed_days':tuple(sum(neighbor[d])/2 for d in (D1,D2)),
        'A_Jun16_low':(76.,76.9),
        'A_Jun16_high':(76.,77.1),
        'A_May09_neighbor_low':(min(76.,*neighbor[D1]),77.),
        'A_May09_neighbor_high':(max(76.,*neighbor[D1]),77.),
    }
    dates=tuple(neighbor)
    variant_rows=[]
    solar={}
    nodes=[]
    for name,values in variants.items():
        solar[name]=observed | dict(zip(dates,values))
        require(set(solar[name])-set(observed)==set(dates) and all(solar[name][d]==v for d,v in observed.items()),
                'Observed row mutation')
        for d,v in zip(dates,values):
            variant_rows.append(dict(variant=name,date=d.date(),candidate_sfu=v,previous_observed=neighbor[d][0],
                                     following_observed=neighbor[d][1],source='explicit researcher estimate; see protocol'))
        # Entire interval where either missing day enters a centered average.
        for date in builder.dates((D1-40*DAY).date(),(D2+40*DAY).date()):
            d=datetime.combine(date,datetime.min.time(),ZERO)
            signal=solar[name]
            nodes.append(dict(variant=name,date=date,F107D_sfu=signal[d],F107A_sfu=math.fsum(
                        signal[d+j*DAY] for j in range(-40,41))/81,may09_in_center81=abs(d-D1)<=40*DAY,
                        jun16_in_center81=abs(d-D2)<=40*DAY))
    table(OUT/'gap_fill_candidates.csv',variant_rows)
    table(OUT/'candidate_daily_nodes.csv',nodes)
    reports={}
    candidates={}
    worst=0.
    for name,signal in solar.items():
        ds,f,a,k=builder.arrays(signal,kp,(START-2*DAY).date(),(END+2*DAY).date())
        dest=OUT/'data_local'/f'{name}_HINDCAST_RESEARCH_FILL.nc'
        builder.write_gpi(dest,ds,f,a,k,START.date(),END.date())
        with Dataset(dest,'a') as nc:
            nc.title='V66 RESEARCHER GAP-FILLED GFZ FOBS CANDIDATE / HINDCAST / RUN NOT AUTHORIZED'
            nc.gap_fill_protocol='GFZ_FOBS_GAP_FILL_V1 pending approval'
            nc.gap_fill_values='; '.join(f'{d.date()}={signal[d]} sfu estimated' for d in dates)
            nc.source_snapshot_sha256=m['source_sha256']
        dest.chmod(0o444)
        driver=GpiDriver(dest)
        points=[START+j*timedelta(minutes=1) for j in range((END-START).days*1440+1)]
        values=[]
        means={datetime.combine(d,datetime.min.time(),ZERO):float(v) for d,v in zip(ds,a)}
        for t in points:
            v=driver.at(int(t.strftime('%Y%j')),t.hour*3600+t.minute*60)
            values.append([v[key] for key in ('f107d','f107a','Kp','hpower','ctpoten')])
            if t.minute in (0,30):
                vv=independent_at(t,signal,means,kp)
                worst=max(worst,max(abs(v[k]-vv[k]) for k in v))
        candidates[name]=np.array(values)
        reports[name]=dict(file=str(dest.relative_to(OUT)),SHA256=sha(dest),
                           daily_pad=[str(ds[0]),str(ds[-1])],GPI_D_rows=len(ds),Kp_bins=int(k.size))
    require(worst<1e-10 and sha(p)==m['source_sha256'],'Independent interpolation or original drift')
    base=next(iter(candidates.values()))
    changes=[]
    for name,x in candidates.items():
        diff=x-base
        require(np.array_equal(x[:,2:],base[:,2:]),'Kp or geomagnetic derived inputs changed')
        for j,key in enumerate(('F107D','F107A')):
            a=diff[:,j]
            i=int(np.abs(a).argmax())
            changes.append(dict(variant=name,relative_to='A_reference_same_day',field=key,
                                max_abs_sfu=float(abs(a[i])),signed_at_max_sfu=float(a[i]),
                                UTC_at_max=points[i].isoformat(),min_sfu=float(a.min()),max_sfu=float(a.max()),
                                changed_minute_nodes=int(np.sum(abs(a)>1e-12))))
    table(OUT/'candidate_driver_comparison.csv',changes)
    write_once(OUT/'candidate_gap_fill_protocol.json',dict(
        protocol='GFZ_FOBS_GAP_FILL_V1',status='GAP_FILL_POLICY_PENDING_REVIEW',
        original_source_SHA256=m['source_sha256'],original_state='GFZ_2021_GAP_UNRESOLVED',
        proposal='A: May 9 76.0 corroborated by NOAA integer daily compilation; definition of XRAS reference unverified. '
                 'June 16 77.0 midpoint of same-day 17Z and 23Z measurements independently described by ARRL.',
        backup='B: interpolate both gaps linearly between immediately neighboring valid GFZ observed days',
        daily_time_model='F107D/F107A GPI nodes daily, model solar cubic interpolation around noon; evidence 20Z convention separate',
        central_81_day_affected={'May09':['2021-03-30','2021-06-18'],'Jun16':['2021-05-07','2021-07-26']},
        envelopes_note='May bounds span adjacent official observations and corroborated daily compilation; '
                       'June bounds span two same-day observations. Neither is a confidence interval.',
        Fadj='not used or modified',candidate_files=reports,minute_points=len(points),
        max_independent_check_abs=worst,Kp_hpower_ctpoten_change=0,
        real_20Z_recovered=False,model_execution=False))
    write_once(OUT/'summer_2021_execution_proposal.json',dict(
        state='PROPOSAL_ONLY_REQUIRES_FRESH_EXPLICIT_AUTHORIZATION',
        start_UTC='2021-05-31T00:00:00Z',target_UTC='2021-06-21T00:00:00Z',
        stop_UTC='2021-06-23T00:00:00Z',spinup_days=21,total_days=23,steps_60s=33120,
        match='Repeat V51 2022 21-day elapsed protocol with mareqx smax and junsol smax in same seed arms',
        primary_proposal='A_reference_same_day',backup_sensitivity='B_adjacent_observed_days',
        preferred_design='A two-seed pair first. If separate authorization, B holding seed and all other conditions fixed, '
                         'optionally both seeds for interaction. Compare model-only sensitivity before further requests.',
        estimated_wall_hours_each=23*10372.866/68/3600,estimated_raw_GiB_each=23*13.341/68,
        scientific_controls='Same dates, initial seed per contrast, model/Heelis/GSWM and scoring protocol. '
                            'No choice from withheld Swarm errors.',
        gates=['Approve versioned fill policy separate from V37 and explicit 2021 model run window/seed/forcing',
               'Explicit additional sensitivity runs if desired',
               'Keep ESA, ZG and V37 scoring gates; later separate observation/scoring authorization']))
    print('GFZ_CANDIDATES_VERIFIED',len(points),worst,flush=True)


if __name__=='__main__':
    main()
