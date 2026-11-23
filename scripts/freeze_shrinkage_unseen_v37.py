"""Publish metadata-only V37 preregistration and acquisition gap list."""
from datetime import datetime, timezone
from pathlib import Path

from audit_shrinkage_unseen_v37 import BASE, E, OUT, ROOT, V20, V36, api, gitpin, load, record, rel, sha
from evaluation.shrinkage_unseen_gate_v37 import CANDIDATES, SEQUENCE, SUMMER, WINTER, REQUIREMENTS


def main():
    audit=load(OUT/'asset_audit.json')
    independent=load(OUT/'independent_review.json')
    assert independent['verified'] and independent['fixture_tests']==25
    assert audit['targets_decoded']==0 and audit['model_runs']==0
    v20=load(V20/'preregistered_protocol.json')
    v36=load(V36/'decision.json')
    assert v36['fixed_lambda']==CANDIDATES['ShrinkageHalf']==0.5
    roles_path=E/'thermosphere_coefficient_stability_zg_audit_v32/data_roles.json'
    gap_path=OUT/'acquisition_gaps.json'
    assets=[]
    for row in audit['dates']:
        day=row['date']
        solar=row['Fobs_not_acquired']
        invalid=row['Fobs_invalid_or_conflict']
        kp=row['missing_or_invalid_Kp_UTC']
        requests=[]
        if solar:
            requests.append(dict(index='Fobs',start=solar[0],stop=solar[-1],days=len(solar),
                                 URL=api('Fobs',solar[0],solar[-1])))
        for t,value in invalid.items():
            requests.append(dict(index='Fobs',start=t,stop=t,days=1,old_value=value,
                                 URL=api('Fobs',t,t),policy='Official positive observed revision with provenance required'))
        if kp:
            requests.append(dict(index='Kp',start=kp[0][:10],stop=kp[-1][:10],buckets=len(kp),
                                 URL=api('Kp',kp[0][:10],kp[-1][:10])))
        assets.append(dict(date=day,state=row['state'],
            phase='NEXT_WITH_AUTHORIZATION' if day in SUMMER else 'DEFERRED',driver_requests=requests,
            available_asset_receipt=rel(OUT/'asset_audit.json'),
            observation=row['observation'],required_seed='junsol smax for review' if day in SUMMER else 'decsol smax for later review'))
    record(gap_path.name,dict(by_date=assets,summer_pair=SUMMER,winter_pair=WINTER,
          reusable_GFZ=audit['driver_sources'],seasonal_seed_candidates=audit['seasonal_seed_catalog'],
          summer_cached_ZIP_size_bytes=sum(r['observation']['historical_index_bytes'] for r in assets[:2]),
          summer_estimated_caps=dict(GFZ_and_ZIP_network_MiB=1,
             optional_separate_junsol_network_MiB=20,ZIP_extracted_MiB=2,cpu_seconds=600,RSS_GiB=4),
          caps_are_proposals_not_authorization=True,no_live_URL_probe_in_V37=True,
          next_action='Check 2021 observed-Fobs corrections first. If a gap remains, keep the pair blocked; bounded preparation of independent 2022 assets may still proceed if authorized.'))
    review_sources=[V36/'decision.json',V36/'descriptive_summary.json',V36/'independent_verification.json',
        V36/'publication_SHA256.json',V20/'preregistered_protocol.json',roles_path,
        ROOT/'src/evaluation/causal_shrinkage_v35.py',ROOT/'src/atmosphere/causal_density_correction.py',
        ROOT/'src/evaluation/late_day_correction.py',ROOT/'src/evaluation/causal_density_latitude.py',
        ROOT/'src/evaluation/swarm_crossyear.py',ROOT/'src/evaluation/swarm_density_comparison.py',
        ROOT/'src/atmosphere/tiegcm_density_provider.py',ROOT/'src/atmosphere/provisional_coordinate_adapter.py',
        E/'thermosphere_zg_external_datum_v34/admission.json',
        ROOT/'reports/THERMOSPHERE_ZG_EXTERNAL_DATUM_EVIDENCE_V34.md']
    ordered_stages=dict(
        identity='Check official source, ZIP/CDF metadata and hashes, time/coords/flags; no target density values. Resolve genuine drivers and approve same qualified seasonal seed hash for both years before model preparation.',
        integration='Freeze input and GPI in a separately authorized preparation stage. One authorized CPU-only run per year plus strict engineering acceptance and independent raw-file verification before history. No retries.',
        history='Authorized history-only product record-slice process. Frozen UTC and quality rules; original Global estimator, immutable b_H and all three multipliers for both cutoffs before future outcomes. No publication-time claims.',
        poison='Use isolated synthetic future values, factor 1e20, for each cutoff. Verify identical float64 historical b and candidate multipliers and archive access boundaries.',
        score='Require a complete pair of identities and verified histories/poison before unlocking any formal pair outcome. Verify aligned common UTC/product IDs and eight columns without extrapolation. Exclusive per-date claims and a pair-level once receipt. Decode future only in this phase; retain failure receipts, N/A and exclusions by rules.',
        verify='Separate read-only original CDF/NetCDF/cache reconstruction and scientific metric audit. Exact baseline identity where possible; rtol=1e-13, atol=0. Retain discrepancies, no rescoring.')
    record('preregistered_protocol.json',dict(
        state='UNSEEN_PROTOCOL_FROZEN_READY',data_state='UNSEEN_DATA_PARTIAL',run_ready=False,
        scope='DATE_HELD_OUT_PREREG / HINDCAST / PROVISIONAL Map-A / REALTIME_ASOF_UNVERIFIED',
        source_HEAD=BASE,UTC=datetime.now(timezone.utc).isoformat(),
        immutable_historical_SHA256={rel(p):gitpin(p) for p in review_sources},
        V36_publication_entries_verified=len(load(V36/'publication_SHA256.json')),
        v36_candidacy_receipt=rel(V36/'decision.json'),
        candidates=dict(CANDIDATES),unique_new_candidate='ShrinkageHalf',
        formula={'b_H':'median(log(obs)-log(Raw)), original Global fit',
                 'rho':'Raw * numpy.exp(lambda*b_H) for all three candidates'},
        numeric_primitives='Pin V35 and reuse the same original estimator and LogMedianCorrection, and require bitwise equivalence on fixtures. V35 public date guard remains intact. Future scored worker must bind this unseen registry separately.',
        roles=load(roles_path), first_pair=list(SUMMER), later_pair=list(WINTER),
        pair_order_policy='Summer first; independently verify 2021 integration before 2022 within a pair. Winter metadata only while summer is pending. A change requires prospective versioned amendment and separate authorization with all targets still sealed. Autumn remains development.',
        V20_core=v20['fixed_scientific_core'], V20_comparison=v20['comparison'],
        active_methods_only=['Raw','Global','ShrinkageHalf'],
        historical_references_only=['LatitudeAdaptive','Stale06'],
        metrics=['MAE','RMSE','Bias','Relative RMS','Relative P95','Relative Bias','Log RMS','Pearson','max_abs','N'],
        ordered_stages={k:ordered_stages[k] for k in SEQUENCE}, evidence_requirements=REQUIREMENTS,
        current_authorized_operation='METADATA_ONLY',
        sampling='Swarm A DNSAPOD_2 0301, UTC 30 s. Shared ordered product/UTC ns sample manifest with immutable SHA before future scoring. All requested quality-eligible points include eight verified Map-A columns (zero weights included). Preserve missing, unsupported and invalid cases with original IDs.',
        joint_count='6 cumulative comparisons per corrected method per day, 12 per complete two-year seasonal pair. Report separate block results; never treat nested windows as IID.',
        reporting=['Report Raw, Global and Half for every registered window and latitude band, including all negatives and N/A.',
          'Show both corrections versus Raw, Half versus Global, season pair and year-specific direction, 3–6 h reversals, P95 and low-latitude bias.',
          'Do not promote solely by joint PASS counts; keep source, spin-up, datum, POD and real-time limitations.',
          'Once any target opens, the date remains used including partial/failed runs. Never retry, retune, change dates, relax joint criteria, impute unsupported values or drop unfavorable samples.',
          'Record stage-specific failure, date, actual-access flag, input and output SHA and exclusion reason; incomplete pairs remain incomplete.'],
        next_acquisition_ARTIFACT=rel(gap_path),phase_authorizations='One explicit authorization per phase. V37 does not authorize phase 2–6.',
        gate_SHA256=sha(ROOT/'src/evaluation/shrinkage_unseen_gate_v37.py'),
        verification_SHA256=sha(OUT/'independent_review.json'),asset_SHA256=sha(OUT/'asset_audit.json'),
        integration_budget=dict(days=16,steps=23040,step_seconds=60,MPI=4,OMP=1,GPU=0,hard_wall_seconds=4800,
           RSS_GiB=16,output_GiB=5,start_free_GiB=25,running_free_GiB=20,no_retry=True,
           prior_autumn_wall_minutes_approx=40.7,estimate_only=True),
        gates=['SEED_POLICY=A_MAREQX_APPROVED historical scope only','AUTUMN_ADAPTATION_UNVERIFIED',
               'FOURTEEN_DAY_SPINUP_NOT_PROVEN_CONVERGED','EXTERNAL_DATUM_UNVERIFIED','FIXED_OFFSET_NOT_ADMITTED',
               'Restart=FAIL','SCIENCE_TRAINING_READY=False','DART=NOT_ADMITTED','REAL_ORBIT=BLOCKED'],
        target_density_decodes=0,new_fits=0,formal_scores=0,physical_runs=0,GPU_operations=0))


if __name__=='__main__':
    main()
