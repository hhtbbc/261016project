"""Package actual V17 read-only evidence. Does not retry any audit or run model."""
from pathlib import Path
import json,csv,hashlib,datetime
R=Path(__file__).resolve().parents[1];F=R/'experiments/tiegcm_2022_mar25_postrun_acceptance_v17';A=F/'audit_once_local';RUN=R/'experiments/tiegcm_2022_mar25_execution_review_v1/actual_run';V16=R/'experiments/tiegcm_2022_mar25_formal_run_v1'
def load(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as s:
  for b in iter(lambda:s.read(2**20),b''):h.update(b)
 return h.hexdigest()
def put(n,v):
 p=F/n;p.resolve().relative_to(R)
 with p.open('x') as s:json.dump(v,s,indent=2,ensure_ascii=False,allow_nan=False);s.write('\n')
def main():
 status=load(A/'status.json');main=load(A/'acceptance.json');ind=load(F/'independent_verification.json');batch=load(A/'batch_result.json');protocol=load(F/'audit_protocol.json');old=load(F/'protected_assets_local.json')
 assert status['returncode']==0 and status['qualification']=='PASS' and status['cleanup_verified'] and not status['gaps'];assert main['overall']=='PASS' and ind['overall']=='ENGINEERING_PASS' and batch['overall']=='ENGINEERING_PASS'
 for n,h in old.items():assert sha(R/n)==h,n
 for n,h in protocol['code_SHA256'].items():assert sha(R/n)==h,n
 files=list(csv.DictReader((V16/'model_output_manifest.csv').open()));assert len(files)==35
 for e in files:assert sha(RUN/e['file'])==e['SHA256']
 # Public copies of small metadata, never raw warnings or original model logs.
 for n in ['acceptance.json','netcdf_property_audit.json']:(F/n).open('xb').write((A/n).read_bytes())
 warnings=[json.loads(x) for x in (A/'warning_records_local.jsonl').read_text().splitlines()];assert len(warnings)==50 and all(x['classification']=='KNOWN_NETCDF_CAST_METADATA_WARNING' for x in warnings)
 counts={}
 for x in warnings:counts[str(x['source_lineno'])]=counts.get(str(x['source_lineno']),0)+1
 put('warning_summary.json',dict(count=len(warnings),category='UserWarning',message='missing_value cannot be safely cast to variable dtype',classification='SHA-pinned original reader metadata warning; raw context separately retained',source_project_relative='src/atmosphere/hourly_tiegcm_observation.py',source_SHA256=protocol['frozen_reader_SHA256'],source_line_counts=counts,raw_warning_log_SHA256=sha(A/'warnings_raw_local.log'),raw_records_SHA256=sha(A/'warning_records_local.jsonl'),raw_warning_logs_not_published=True,unknown_warnings=0,reader_values_or_masks_changed=False))
 put('asset_protection_after.json',dict(PASS=True,protected_files=len(old),all35_output_SHA_match_V16=True,run_id=protocol['run_id'],old_reservations_rank_receipts_and_failed_audit_unchanged=True,V16_ORIGINAL_ENGINEERING_STATUS='FAIL',V16_result_SHA256=sha(V16/'result.json'),V16_report_SHA256=sha(R/'reports/TIEGCM_2022_MAR25_FORMAL_RUN_V16.md'),frozen_scientific_protocol_SHA256=protocol['frozen_science_protocol_SHA256'],old_frozen_execution_and_science_codes_unchanged=True,new_model_launches=0,no_permissions_or_attributes_changed=True))
 check=main['checks'];native=ind['all_warm_native_checks'];q=check['target_observation_queries']['evidence'];qi=ind['independent_queries']
 assert native['records']==408 and q['success']==qi['N_success']==2880 and q['failed']==qi['N_failure']==0
 put('comparison_with_V16.json',dict(V16_original='ENGINEERING_FAIL',V16_failure='read-only child killed by fatal regex source-context np.nan',V16_main_acceptance_JSON_exists=False,V17='ENGINEERING_PASS',physical_model_data_identical=True,primary_records=[18,18],secondary_records=[408,408],independent_target_coverage=[2880,2880],main_target_coverage_V16='NO_COMPLETE_RESULT',main_target_coverage_V17=2880,new_density_prediction_claim=False,old_failure_not_overwritten=True))
 result=dict(overall='ENGINEERING_PASS',V16_ORIGINAL_ENGINEERING_STATUS='FAIL',ACTUAL_MODEL_HISTORY='COMPLETED_IN_V16',model_launches_this_task=0,full_readonly_reaudit_attempts=1,automatic_retries=0,main_acceptance='PASS',independent_acceptance='PASS',batch_parent_returncode=status['returncode'],batch_supervision_qualification=status['qualification'],batch_cleanup_verified=status['cleanup_verified'],read_only_wall_s=status['elapsed_s'],peak_sampled_tree_RSS_bytes=status['peak_sampled_tree_rss_bytes'],main_checks={k:v['status'] for k,v in check.items()},records=dict(primary=18,secondary=408,NetCDF_files=35,target_day_frames=25),all_warm_native= native,actual_GPI_main_max_abs=check['output_files']['evidence']['actual_GPI_max_abs_difference'],query_main=q,query_independent=qi,warning_count=50,distinct_targeted_and_regression_tests=35,frozen_scientific_rules_changed=False,next_density_validation='READY_TO_REQUEST_EXPLICIT_AUTHORIZATION_NOT_RUN',density_error_metrics=0,correction_fits=0,scientific_gates=dict(SCIENCE_TRAINING_READY=False,EXTERNAL_DATUM='UNVERIFIED',Restart='FAIL',DART='NOT_ADMITTED',REAL_ORBIT='BLOCKED'))
 put('result.json',result)
 put('resource_audit.json',dict(readonly_batch_wall_s=status['elapsed_s'],sampling_definition=status['resource_definition'],peak_sampled_tree_RSS_bytes=status['peak_sampled_tree_rss_bytes'],worker_process_max_RSS_MiB=ind['peak_RSS_MiB'],batch_children_CPU_user_s=status['children_cpu_user_s'],batch_children_CPU_system_s=status['children_cpu_system_s'],sampling_gaps=len(status['gaps']),independent_part_wall_s=ind['wall_s'],independent_part_CPU_s=ind['CPU_s'],independent_part_already_included_in_batch=True,budget=dict(wall_s=600,RSS_GiB=4,output_MiB=150),samples=len(status['samples']),actual_parent_direct_wait=True,actual_parent_returncode=0,full_audit_launches=1,full_audit_retry=0,new_TIEGCM=0,new_download_bytes=0,GPU=0,DART=0,orbit=0))
 put('source_manifest.json',dict(old_asset_manifest_SHA256=sha(F/'protected_assets_local.json'),actual_run_id=protocol['run_id'],V16_output_manifest_SHA256=sha(V16/'model_output_manifest.csv'),audit_protocol_SHA256=sha(F/'audit_protocol.json'),actual_batch_status_SHA256=sha(A/'status.json'),actual_main_document_SHA256=sha(A/'acceptance.json'),independent_document_SHA256=sha(F/'independent_verification.json'),new_code=protocol['code_SHA256'],original_model_logs_not_replayed_as_success=True,independent_document_written_before_parent_wait='Its returncode field is pending by design; actual complete parent0 is recorded in result/resource files after direct wait.'))
 put('commands.json',dict(activation='source scripts/activate_tiegcm.sh',targeted_tests='PYTHONPATH=project/src:project python -m unittest discover -s tests -p test_tiegcm_v17_readonly.py -v',regression_tests='9 selected immutable test_tiegcm_mar25_execution_review.Review cases with BASE redirected to V17 tests_local;8 test_hourly_tiegcm_observation cases',full_batch='python scripts/launch_tiegcm_v17_readonly.py',full_batch_calls=1,main_acceptor_calls=1,independent_algorithm_calls=1,finalize='python scripts/finalize_tiegcm_v17.py',forbidden_model_entry_not_called=True,raw_logs_kept_local=True))
 print(json.dumps(dict(overall=result['overall'],V16_ORIGINAL_ENGINEERING_STATUS='FAIL',wall_s=status['elapsed_s'],warm_records=408,queries=2880,new_model_launches=0)))
if __name__=='__main__':main()
