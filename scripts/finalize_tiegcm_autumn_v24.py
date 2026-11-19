"""Summarize already finished V24 execution/audits; never reads new density errors."""
from pathlib import Path
import sys,json,csv,datetime
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from runtime.tiegcm_rank_exit import write_once,digest
F=R/'experiments/thermosphere_autumn_2021_formal_run_v24';B=R/'experiments/thermosphere_autumn_mareqx_config_v23/2021';RUN=B/'actual_run'
def load(p,default=None):return json.loads(p.read_text()) if p.exists() else default

def main():
    if not (F/'executor_wait_local.json').exists():raise RuntimeError('Frozen entry still active or completion unknown; no finalization')
    p=load(B/'launch_protocol.json');s=load(RUN/'status.json',{});claim=load(B/'execution_claim_local.json',{});a=load(B/'postrun_audit_local/acceptance.json',{});ind=load(F/'independent_verification.json',{});isup=load(F/'independent_supervision.json',{});combined=load(F/'readonly_combined_resource.json',{})
    checks=a.get('checks',{});out=checks.get('output_files',{}).get('evidence',{});q=checks.get('target_observation_queries',{}).get('evidence',{})
    overall='ENGINEERING_PASS' if s.get('qualification')=='PASS' and s.get('returncode')==0 and a.get('overall')=='PASS' and ind.get('overall')=='ENGINEERING_PASS' and isup.get('qualification')=='PASS' and isup.get('returncode')==0 and combined.get('within_budget') else 'ENGINEERING_UNKNOWN'
    if s.get('qualification')=='FAIL' or a.get('overall')=='FAIL' or ind.get('overall')=='ENGINEERING_FAIL' or (F/'independent_failure.json').exists():overall='ENGINEERING_FAIL'
    files=out.get('files',ind.get('outputs',{}).get('files',[]));ranks=[]
    for k in range(4):
        x=load(RUN/f'rank_{k:03d}_exit.json',{});ranks.append({key:x.get(key) for key in ['rank','run_id','returncode','child_pid','wrapper_sid','child_sid','wait_source','started_unix','ended_unix','error','received_signals']})
    samples=s.get('samples',[]);free=[v['free_disk_bytes'] for v in samples if 'free_disk_bytes' in v]
    resource=dict(model_supervision_wall_s=s.get('elapsed_s'),model_minutes=s.get('elapsed_s',0)/60,peak_sampled_tree_RSS_bytes=s.get('peak_sampled_tree_rss_bytes'),children_CPU_user_s=s.get('children_cpu_user_s'),children_CPU_system_s=s.get('children_cpu_system_s'),NetCDF_files=len(files),NetCDF_logical_bytes=sum(x['bytes'] for x in files),run_logical_bytes=sum(x.stat().st_size for x in RUN.rglob('*') if x.is_file()),run_allocated_bytes=sum(x.stat().st_blocks*512 for x in RUN.rglob('*') if x.is_file()),min_sampled_free_disk_bytes=min(free) if free else None,readonly_combined=combined,independent_supervision=isup,monitoring_scope=s.get('resource_definition'),GPU=0,model_launches=1 if claim else 0,automatic_retry=False)
    source={key:p[key] for key in ['source','GPI','input','executable','mpirun','observation','hapi']}
    write_once(F/'source_manifest.json',source);write_once(F/'resource_audit.json',resource);write_once(F/'rank_exits.json',dict(run_id=claim.get('run_id'),ranks=ranks,parent_returncode=s.get('returncode'),wait_source=s.get('wait_source'),parent_identity=s.get('identity')))
    write_once(F/'main_acceptance_snapshot.json',a)
    if files:
        with (F/'model_output_manifest.csv').open('x',newline='') as h:w=csv.DictWriter(h,fieldnames=list(files[0]),lineterminator='\n');w.writeheader();w.writerows(files)
    actual_steps=ind.get('identity',{}).get('actual_steps');last=ind.get('identity',{}).get('actual_final_UTC');query=ind.get('independent_queries',{})
    result=dict(overall=overall,ACTUAL_MODEL_RUN='COMPLETED' if actual_steps==23040 else ('ATTEMPTED' if claim else 'NOT_RUN'),run_id=claim.get('run_id'),model_launches=1 if claim else 0,year=2021,steps=actual_steps,final_UTC=last,primary_records=out.get('primary_records'),secondary_records=out.get('secondary_records'),NetCDF_files=len(files),model_wall_s=s.get('elapsed_s'),rank_returncodes=[x.get('returncode') for x in ranks],main_acceptance=a.get('overall','MISSING'),independent_acceptance=ind.get('overall','MISSING'),Swarm_eligible=query.get('eligible'),Swarm_success=query.get('success'),Swarm_failed=query.get('failed'),actual_driver_max_abs=out.get('actual_GPI_max_abs_difference'),independent_GFZ_max_abs=ind.get('outputs',{}).get('actual_GFZ_max_abs_difference'),year2022_launched=False,new_scores=0,new_fits=0,scientific_gates_unchanged=True)
    write_once(F/'result.json',result)
    print(json.dumps(result,indent=2));print(json.dumps(resource,indent=2))
if __name__=='__main__':main()
