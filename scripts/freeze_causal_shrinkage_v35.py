"""Publish the fixed V36 design from verified V35 evidence without scoring."""
import hashlib
from pathlib import Path
import subprocess
import zipfile

import numpy as np

from verify_causal_shrinkage_v35 import BASE, OUT, ROOT, frozen, v35


def pin(path):
    name = str(path.relative_to(ROOT))
    expected = hashlib.sha256(subprocess.check_output(
        ['git', 'show', f'{BASE}:{name}'], cwd=ROOT)).hexdigest()
    assert frozen.sha(path) == expected, f'Frozen input changed: {name}'
    return expected


def rel(path):
    return str(path.relative_to(ROOT))


def main():
    root = frozen.E
    verification = frozen.load(OUT/'verification.json')
    assert verification['fixture_tests'] == 25 and not verification['failures'] and not verification['errors']
    assert all(x['bitwise_same_history_and_multipliers'] for x in verification['poison'])
    roles_path = frozen.OUT/'data_roles.json'
    availability = frozen.OUT/'information_availability.csv'
    audit34 = root/'thermosphere_zg_external_datum_v34'
    sources = {
        rel(p): pin(p) for p in (
            roles_path, availability, frozen.OUT/'history_freeze.json', frozen.PROTOCOL,
            audit34/'admission.json', audit34/'evidence_matrix.csv',
            ROOT/'reports/THERMOSPHERE_ZG_EXTERNAL_DATUM_EVIDENCE_V34.md',
            ROOT/'reports/THERMOSPHERE_COEFFICIENT_STABILITY_AND_ZG_AUDIT_V32.md',
            ROOT/'reports/THERMOSPHERE_AUTUMN_DENSITY_VALIDATION_V30.md',
            ROOT/'reports/THERMOSPHERE_SPRING_AUTUMN_FAILURE_MECHANISM_V31.md',
            ROOT/'src/evaluation/causal_density_latitude.py',
            ROOT/'src/evaluation/swarm_crossyear.py',
            ROOT/'src/evaluation/late_day_correction.py',
            ROOT/'src/atmosphere/causal_density_correction.py',
            ROOT/'src/atmosphere/provisional_coordinate_adapter.py',
            ROOT/'src/atmosphere/tiegcm_density_provider.py',
            ROOT/'scripts/density_autumn_v30.py')
    }
    core = frozen.load(frozen.PROTOCOL)['fixed_scientific_core']
    for key in ('metric_source', 'latitude_source', 'Map_A_source', 'operator_source', 'hourly_reader_source'):
        source = core[key]
        assert pin(ROOT/source['path']) == source['SHA256']
        sources[source['path']] = source['SHA256']

    for version in (frozen.V30, frozen.V31, frozen.OUT,
                    root/'thermosphere_zg_vertical_sensitivity_v33'):
        publication = version/'publication_SHA256.json'
        sources[rel(publication)] = pin(publication)
        for name, sha in frozen.load(publication).items():
            assert (ROOT/name).resolve() == ROOT/name and frozen.sha(ROOT/name) == sha, name
            sources[name] = sha
    assert frozen.load(audit34/'admission.json')['external_datum'] == 'EXTERNAL_DATUM_UNVERIFIED'
    guards = (
        'experiments/thermosphere_autumn_2021_formal_run_v24',
        'experiments/thermosphere_autumn_2021_postrun_closure_v26',
        'experiments/thermosphere_autumn_2022_formal_run_v29',
        'experiments/thermosphere_independent_date_validation_plan_v20',
        *(rel(p) for p in (frozen.V30, frozen.V31, frozen.OUT,
                           root/'thermosphere_zg_vertical_sensitivity_v33', audit34)),
    )
    subprocess.run(['git', 'diff', '--quiet', BASE, '--', *guards], check=True, cwd=ROOT)

    for folder in (frozen.V30, frozen.V18, frozen.SPRING21):
        source_manifest = folder/'source_manifest.json'
        sources[rel(source_manifest)] = pin(source_manifest)

    legacy = frozen.V1/'coverage.csv'
    sources[rel(legacy)] = pin(legacy)
    legacy_index = {(x['date'], int(x['cutoff'])): x for x in frozen.rows(legacy) if x['case'] == 'B14'}
    layouts = {
        '2021-03-25': (frozen.SPRING21/'coverage.csv', 'sample_ID_SHA256',
                       frozen.SPRING21/'matched_local.npz', 'B14_{hour}_Raw'),
        '2022-03-25': (frozen.V18/'coverage.csv', 'common_ID_SHA256',
                       frozen.V18/'matched_local.npz', 'raw'),
        **{f'{year}-09-23': (frozen.V30/f'{year}_common_ids.csv', 'utc_ID_SHA256',
                            frozen.V30/f'{year}_matched_local.npz', 'raw') for year in (2021, 2022)},
    }
    admission = []
    survey = []
    expected_ns = dict(future_1h=120, future_3h=360, future_6h=720,
                       block_0_1h=120, block_1_3h=240, block_3_6h=360)
    for item in verification['windows']:
        day, hour_text = item['key'].split('/')
        hour = int(hour_text)
        h = dict(date=day, cutoff=hour, history_observable=True, frozen_background=True,
                 history_quality_N=item['N'], used_in_development=True,
                 history_path=item['source'], history_cache_SHA256=item['source_SHA256'])
        if not item['original_global']:
            old = legacy_index[day, hour]
            assert int(old['future_6h_N']) == 720 and float(old['coverage']) == 1
            survey.append(dict(h, future_common_Raw_N=720, old_parameter_state=old['corrected_prediction_methods'],
                               admissible_common_comparison=False,
                               scope='V1 diagnostic only; no supported harmonized parameter/ID receipt'))
            continue
        coverage, id_field, matched, raw_field = layouts[day]
        frozen_id_rows = {
            (x['window'], x['method']): x for x in frozen.rows(coverage)
            if int(x['cutoff']) == hour and x.get('case', 'B14') == 'B14'
            and x.get('region', 'all') == 'all'
        }
        windows = {}
        for window, expected in expected_ns.items():
            raw = frozen_id_rows[window, 'Raw']
            old = frozen_id_rows[window, f'GlobalAdaptive{hour:02d}']
            assert int(raw['N']) == int(old['N']) == expected and raw[id_field] == old[id_field]
            windows[window] = dict(N=expected, original_ID_SHA256=raw[id_field])
        # Verify only the UTC index. No observed or model values are decoded in this stage.
        with zipfile.ZipFile(matched) as archive:
            utc = frozen.read_member(archive, 'utc', None)
            assert raw_field.format(hour=hour) + '.npy' in archive.namelist()
        origin = v35.RollingOrigin(day, hour)
        masks = origin.masks(utc)
        masks['block_0_1h'] = masks['future_1h']
        for name, window in windows.items():
            selected = np.asarray(utc[masks[name]], dtype='datetime64[ns]')
            assert len(selected) == window['N']
            assert v35.utc_sha(selected) == window['original_ID_SHA256']
        matched_sha = frozen.sha(matched)
        if day.endswith('09-23'):
            receipt = frozen.V30/f'{day[:4]}_score_receipt.json'
            sources[rel(receipt)] = pin(receipt)
            assert matched_sha == frozen.load(receipt)['outputs_SHA256'][matched.name]
        elif day == '2021-03-25':
            assert matched_sha == item['source_SHA256']
        sources[rel(coverage)] = pin(coverage)
        sources[item['global_parameter_path']] = pin(ROOT/item['global_parameter_path'])
        assert sources[item['global_parameter_path']] == item['global_parameter_SHA256']
        admission.append(dict(h, original_global_path=item['global_parameter_path'],
                              original_global_SHA256=item['global_parameter_SHA256'],
                              history_sample_SHA256=item['history_sample_SHA256'],
                              history_UTC_SHA256=item['history_UTC_SHA256'],
                              future_cache_path=rel(matched), future_cache_SHA256=matched_sha,
                              future_cache_identity=('V35 byte pin of existing V18 cache' if day=='2022-03-25'
                                                     else 'matches prior receipt'),
                              future_background_field=raw_field.format(hour=hour),
                              background_provenance_manifest=rel(coverage.parent/'source_manifest.json'),
                              original_common_ID_manifest=rel(coverage), original_ID_field=id_field,
                              future_windows=windows))
        survey.append(dict(h, future_common_Raw_N=720, old_parameter_state='SUPPORTED and byte/sample pinned',
                           admissible_common_comparison=True, scope='V36 exploratory comparison only'))

    sources[rel(frozen.V1/'source_manifest.json')] = pin(frozen.V1/'source_manifest.json')
    v35_receipt = dict(
        state='SHRINKAGE_DESIGN_FROZEN_READY', source_HEAD=BASE,
        methods=dict(v35.CANDIDATES), new_fixed_parameters=1,
        formula='b_H=median(log(obs)-log(raw)); b_shrink=lambda*b_H; corrected=raw*np.exp(b_shrink)',
        lambda_choice='0.5 is an a priori midpoint contrast; no future outcomes used for selection',
        temporal_identity=['HINDCAST_HISTORY_AVAILABLE', 'REALTIME_ASOF_UNVERIFIED'],
        map_identity='PROVISIONAL Map-A / EXTERNAL_DATUM_UNVERIFIED / FIXED_OFFSET_NOT_ADMITTED',
        roles=frozen.load(roles_path), availability_matrix=rel(availability),
        eligibility_survey=survey, eligible_windows=admission,
        V20_core=core, future_scores=0, formal_test_access=0,
        output_directory='experiments/thermosphere_causal_shrinkage_development_v36/',
        authorization='V36 exploration requires a separate user authorization',
        workflow=[
            'Before future outcome access, verify entire V35 release, date/cutoff/asset pins and one frozen b_H per cutoff',
            'Only the four admitted dates; enforce one complete same-product UTC/observation-ID manifest per cutoff from frozen quality and Raw admissibility, independent of method outcomes',
            'Use dataset identity Swarm/A/0301 + ordered UTC ns; legacy ID digest is SHA256 of signed little-endian int64 UTC nanoseconds; join against the same ordered IDs with no silent intersection',
            'Separate background/ID-only panel from post-freeze observed outcome reader; new multiplier and candidate selection have no outcome input',
            'Read only admitted future slices, preserve out-of-range/duplicate/missing-query failures; do not shrink the sample set to get supported numbers',
            'Use V20 frozen metrics, latitude groups and N=30; report joint flags by cumulative window and separate block metrics; unsupported windows are N/A and never PASS',
            'List all date/cutoff/window results, including harms; stop on pin mismatch, duplicate/unaligned IDs or leak, with no replacement dates or lambda retuning',
            'Any optional whole-day leave-out diagnostic holds both cutoffs and all future overlaps together; there is no cross-day training or performance-based parameter selection',
            'Later unseen validation requires a separate preregistration/authorization; no holdout values, errors, or candidate selection in this release',
        ],
        historical_references={'18Z': ['LatitudeAdaptive18', 'Stale06'], 'shrinkage_versions': False},
        frozen_sources=sources,
        V35_SHA256={rel(p): frozen.sha(p) for p in (
            Path(v35.__file__), ROOT/'scripts/verify_causal_shrinkage_v35.py',
            Path(__file__), OUT/'verification.json')},
    )
    assert len(admission) == 8 and len(survey) == 16
    frozen.write_once(OUT/'v36_development_release.json', v35_receipt)


if __name__ == '__main__':
    main()
