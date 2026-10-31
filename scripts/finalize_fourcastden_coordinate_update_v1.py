"""Read-only result checks and final provenance, no scientific computation runs."""
from pathlib import Path
import ast,csv,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import audit_fourcastden_coordinate_update_v1 as task
from PIL import Image


def main():
    O,F=task.O,task.F
    rows=list(csv.DictReader((O/'real_event_queries.csv').open()))
    assert len(rows)==192 and all(r['exact_branch_match']=='True' for r in rows)
    for r in rows:
        a,b=r['time_bracket'].split(';');event=r['date']+'T07:00:00.000'
        assert b<=event if r['branch']=='left' else a>=event
    protected=json.loads((F/'protected_final.json').read_text())
    assert all(task.sha(ROOT/p)==h for p,h in protected.items())
    history=json.loads((F/'history_integrity.json').read_text());assert not history['changed'] and history['checked']==2346
    prior=list(csv.DictReader((ROOT/'results/fourcastden_ideal_update_6h_v1/physical_consistency.csv').open()))
    current=list(csv.DictReader((O/'flow_region_times.csv').open()))
    for r in current:
        if r['scheme']=='Reference':continue
        match=next(x for x in prior if x['date']=='2023-03-24' and x['model']=='Flow' and x['scheme']==r['scheme']
                   and x['target_hour_UTC']==r['hour_UTC'] and x['region']==r['region'])
        assert int(r['invalid_columns'])==int(match['height_invalid_columns'])
    tests=ROOT/'logs/fourcastden_coordinate_update_v1_tests_extended.log'
    assert 'Ran 17 tests' in tests.read_text() and 'OK' in tests.read_text()
    code=[ROOT/p for p in ['src/atmosphere/event_aware_density.py','src/orbit/event_segments.py','tests/test_event_aware_density.py',
        'scripts/audit_fourcastden_coordinate_update_v1.py','scripts/plot_fourcastden_coordinate_update_v1.py',
        'scripts/finalize_fourcastden_coordinate_update_v1.py']]
    for p in code:ast.parse(p.read_text())
    sources=[]
    data={'event_density_limits':'real_event_queries.csv','coordinate_single_factor_sensitivity':'coordinate_single_factor_review.csv',
          'flow_failure_time_and_map':'flow_failed_columns.csv;flow_region_times.csv','flow_vertical_error_components':'flow_layer_diagnosis.csv',
          'flow_interface_midpoint_inverse':'flow_worst_column_profile.csv','synthetic_event_RK45_convergence':'synthetic_event_convergence.csv;synthetic_event_trajectory.csv'}
    for p in sorted(O.glob('*.png')):
        with Image.open(p) as im:im.verify()
        sources.append(dict(figure=p.name,SHA256=task.sha(p),data=data[p.stem],
            generator='scripts/plot_fourcastden_coordinate_update_v1.py',labels='Native datum / conditional / synthetic as in individual title'))
    assert len(sources)==6
    task.table(O/'figure_sources.csv',sources)
    for info in json.loads((F/'official_metadata/requests.json').read_text()):
        if 'SHA256' in info:assert task.sha(ROOT/info['path'])==info['SHA256']
    info=json.loads((F/'official_metadata/data_terms_request.json').read_text());assert task.sha(ROOT/info['path'])==info['SHA256']
    manifest={str(p.relative_to(ROOT)):task.sha(p) for p in code}
    for folder in (O,F):
        for p in folder.rglob('*'):
            if p.is_file():manifest[str(p.relative_to(ROOT))]=task.sha(p)
    task.dump(F/'delivery_manifest.json',manifest)
    task.dump(F/'delivery_validation.json',dict(status='PASS',new_tests=17,real_queries=192,expected_invalid_queries=4,
        branch_stencil_respects_event=True,old_Flow_failure_counts_reproduced=True,PNG_verified=6,
        input_SHA_unchanged=len(protected),historical_SHA_unchanged=2346,
        source_SHA={str(p.relative_to(ROOT)):task.sha(p) for p in code},
        files_under_budget=sum(p.stat().st_size for d in (O,F) for p in d.rglob('*') if p.is_file())<200*2**20,
        external_registration='BLOCKED',SCIENTIFIC_TRAINING_READY=False))
    print((F/'delivery_validation.json').read_text())


if __name__=='__main__':main()
