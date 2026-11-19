"""V23 static-only configuration freeze; no execute import invocation or model subprocess."""
from pathlib import Path
import sys,json,datetime,csv,hashlib,subprocess,time,resource,re,shutil
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R)]
from runtime.tiegcm_autumn_execution import PACKAGE,SEED,SEED_SHA,GPI_SHAS,expected_input,validate_input,namelist,validate_binding,environment_review,require
from runtime.tiegcm_rank_exit import digest,write_once
from observations.autumn_validation import inspect_initial
from atmosphere.tiegcm_drivers import GpiDriver
F=PACKAGE

def entry(path):return dict(path=str(path.relative_to(R)),SHA256=digest(path))
def main():
    begin=time.monotonic();cpu=time.process_time();require(F.resolve().is_relative_to(R),'Outside root');F.mkdir(exist_ok=False)
    old={}
    for folder in ['thermosphere_autumn_gpi_seed_policy_v22','thermosphere_autumn_data_acquisition_v21','thermosphere_independent_date_validation_plan_v20']:
        for p in (R/'experiments'/folder).glob('*'):
            if p.is_file() and p.suffix in ['.json','.csv','.nc'] and not p.name.endswith('_local.json'):old[str(p.relative_to(R))]=digest(p)
    for p,h in json.loads((R/'experiments/thermosphere_autumn_gpi_seed_policy_v22/preflight.json').read_text())['protected_SHA256'].items():require(digest(R/p)==h,'Prior input changed');old[p]=h
    seed=R/SEED;require(digest(seed)==SEED_SHA,'Approved seed SHA changed')
    write_once(F/'seed_policy_receipt.json',dict(SEED_POLICY='A_MAREQX_APPROVED',authorization='Explicit V23 user instruction approves current mareqx for both autumn years; no physical integration authorization',actual_model_authorized_this_task=False,source=dict(path=SEED,SHA256=SEED_SHA),same_SHA_for_both_years=True,limitations=['AUTUMN_ADAPTATION_UNVERIFIED','FOURTEEN_DAY_SPINUP_NOT_PROVEN_CONVERGED','SEPEQX_SOURCE_NOT_ACQUIRED'],frozen_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),base_HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()))
    initial=inspect_initial(seed,seed);require(initial['SOURCE_START']==[80,0,0] and initial['years']==[2002] and initial['required_complete_states']==34,'Native source identity mismatch')
    historical=R/'experiments/tiegcm_2021_spinup_14day_v1/initial_state_audit.json';hist=json.loads(historical.read_text());require(hist['B_SHA256']==SEED_SHA and hist['B']['structure_complete'] and hist['B']['record_available'],'Historical34-state identity mismatch')
    initial.update(source_SHA256=SEED_SHA,historical_record=entry(historical),cold_start_semantics=dict(SOURCE_START=[80,0,0],target_START=[252,0,0],native_year_unchanged=2002,source_day_may_differ=True,matching_hour_minute_required=True,read_only_source_branch='rdsource.F readsource nsource==1; initial model iter from target START in init.F',no_restart=True))
    write_once(F/'initial_state_audit.json',initial)
    v20=R/'experiments/thermosphere_independent_date_validation_plan_v20/preregistered_protocol.json';require(digest(v20)=='eb27a080199d656f6018f47834cc9eaef07897009360ca184d6511e4d3aeb2c4','V20 protocol changed')
    science=json.loads(v20.read_text())
    for k in ['metric_source','latitude_source','Map_A_source','operator_source','hourly_reader_source']:
        e=science['fixed_scientific_core'][k];require(digest(R/e['path'])==e['SHA256'],'Science implementation changed')
    old[str(v20.relative_to(R))]=digest(v20)
    contracts=json.loads((R/'experiments/thermosphere_autumn_data_acquisition_v21/Swarm_contracts.json').read_text());swarm=json.loads((R/'experiments/thermosphere_autumn_data_acquisition_v21/Swarm_audit.json').read_text())
    spring=R/'experiments/tiegcm_2022_mar25_preparation_v1/run/input.inp';before=namelist(spring.read_text());diffrows=[];envs={};protocols={};schedule={}
    for y in [2021,2022]:
        folder=F/str(y);folder.mkdir();inp=folder/'input.inp';text=expected_input(y);validate_input(text,y);inp.open('x').write(text);inp.chmod(0o444)
        gpi=R/f'experiments/thermosphere_autumn_gpi_seed_policy_v22/gpi_{y}_autumn.nc';require(digest(gpi)==GPI_SHAS[y],'Approved GPI SHA changed')
        audit=json.loads((R/f'experiments/thermosphere_autumn_gpi_seed_policy_v22/gpi_audit_{y}.json').read_text());require(audit['status']=='GPI_READY' and audit['SHA256']==GPI_SHAS[y],'No valid GPI audit')
        reader=GpiDriver(gpi)
        for d,s in [(252,0),(252,43200),(266,0),(266,64800),(268,0)]:require(all(__import__('math').isfinite(v) for v in reader.at(y*1000+d,s).values()),'GPI domain failure')
        obs=swarm[str(y)]['CDF'];require(digest(R/obs['path'])==obs['SHA256'],'Observation SHA changed');hapi=next(e['hapi'] for e in contracts if e['date']==f'{y}-09-23');hapi={k:hapi[k] for k in ['path','SHA256']}
        p=dict(year=y,start_UTC=f'{y}-09-09T00:00:00Z',stop_UTC=f'{y}-09-25T00:00:00Z',target_date=f'{y}-09-23',steps=23040,step_s=60,MPI=4,OMP=1,cwd=str((folder/'actual_run').relative_to(R)),input=entry(inp),source=entry(seed),GPI=entry(gpi),executable=entry(R/'experiments/tiegcm2_apex2023_v1/tiegcm2.0'),mpirun=entry(R/'.envs/tiegcm/bin/mpirun'),observation={k:obs[k] for k in ['path','SHA256']},hapi=hapi,eligible_observations=2880,output=dict(primary_records=17,secondary_records=384,primary_volumes=17,secondary_volumes=16,NetCDF_files=33),limits=dict(model_wall_s=4800,stop_trigger_s=4770,cleanup_reserve_s=30,RSS_bytes=16*2**30,output_bytes=5*2**30,start_free_bytes=25*2**30,run_free_floor_bytes=20*2**30,postrun_wall_s=600,postrun_RSS_bytes=4*2**30,launches=1,retries=0),seed_policy_SHA256=digest(F/'seed_policy_receipt.json'),preregistered_protocol_SHA256=digest(v20),activation='source scripts/activate_tiegcm.sh',path_environment='PROJECTROOT set to actual checked project root; no underscore in variable name (Fortran delimiter rule)',actual_authorization_this_task=False,readiness='STATIC_CHECKS_PENDING_TESTS')
        validate_binding(p);write_once(folder/'launch_protocol.json',p);envs[str(y)]=environment_review(p);protocols[str(y)]=entry(folder/'launch_protocol.json')
        after=namelist(text)
        for k in before:
            # Compare resolved physical paths as well as raw input spelling.
            a=before[k];b=after[k];physical_equal=a==b.replace('$PROJECTROOT',str(R))
            diffrows.append(dict(year=y,field=k,spring=a.replace(str(R),'$PROJECTROOT'),autumn=b,changed=a!=b,physical_equal_after_path_expansion=physical_equal,expected=True,interpretation='path spelling only; same physical asset' if physical_equal and a!=b else ('calendar/driver/output identity or metadata' if a!=b else 'unchanged')))
        start=datetime.datetime(y,9,9);primary=[(start+datetime.timedelta(days=i)).isoformat()+'Z' for i in range(17)];secondary=[(start+datetime.timedelta(hours=i)).isoformat()+'Z' for i in range(1,385)]
        schedule[str(y)]=dict(primary_records=primary,secondary_records=secondary,volume_rule='MXHIST_PRIM1/HIST1day ->17 one-record primary; MXHIST_SECH24/SECHIST1hour ->16 x24 secondary; initial cold primary included, secondary first at +1hour',target_day_frames=25,candidate_spinup_days=14,spinup_convergence='UNPROVEN')
        require(not (folder/'actual_run').exists() and not (folder/'execution_claim_local.json').exists(),'Unexpected reservation')
        # Verify new directory is writable using an exclusive local probe, not model input/output.
        (folder/'writability_probe_local').open('x').close()
    with (F/'configuration_diff.csv').open('x',newline='') as h:
        w=csv.DictWriter(h,fieldnames=list(diffrows[0]),lineterminator='\n');w.writeheader();w.writerows(diffrows)
    write_once(F/'resource_preflight.json',envs);write_once(F/'expected_timelines.json',schedule)
    write_once(F/'protocol_compatibility.json',dict(status='STATIC_COMPATIBLE',V20_SHA256=digest(v20),fixed_core=science['fixed_scientific_core'],target_dates=['2021-09-23','2022-09-23'],V21_quality_evidence='experiments/thermosphere_autumn_data_acquisition_v21/Swarm_window_latitude_counts.csv',quality_counts_reused=True,autumn_density_errors_read=0,fits=0,science_scoring=0,old_protocol_changed=False))
    srcjson=json.loads((R/'experiments/tiegcm_2022_mar25_preparation_v1/source_manifest.json').read_text());assets={}
    cfg=json.loads((R/'experiments/tiegcm_2022_mar25_preparation_v1/model_configuration_manifest.json').read_text())
    for n,h in cfg['verified_assets'].items():require(digest(R/n)==h,'Old scientific asset drift');assets[n]=h
    for e in srcjson['compiled_source_inventory']+[srcjson['mpirun']]:require(digest(R/e['path'])==e['SHA256'],'Compiled source/MPI changed');assets[e['path']]=e['SHA256']
    for source in ['input.F','rdsource.F','init.F','util.F','output.F','hist.F']:
        n='third_party/TIEGCM2.0/src/'+source;assets[n]=digest(R/n)
    assets[SEED]=SEED_SHA
    for k in ['metric_source','latitude_source','Map_A_source','operator_source','hourly_reader_source']:
        e=science['fixed_scientific_core'][k];assets[e['path']]=e['SHA256']
    for name in ['src/runtime/supervisor.py','src/runtime/tiegcm_rank_exit.py','src/runtime/tiegcm_mar25_execution.py','src/runtime/readonly_audit_warning_channel.py','src/atmosphere/tiegcm_mar25_acceptance.py']:
        assets[name]=digest(R/name)
    write_once(F/'scientific_asset_manifest.json',assets)
    require(all(digest(R/n)==h for n,h in old.items()),'Historical asset modified')
    write_once(F/'protected_assets.json',old);write_once(F/'preparation_result.json',dict(model_launches=0,ACTUAL_MODEL_RUN='NOT_RUN',configuration_created=True,year_protocols=protocols,tests='PENDING',elapsed_s=time.monotonic()-begin,CPU_s=time.process_time()-cpu,max_self_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
    print('Autumn static inputs created; real model launches=0; tests/release still pending')
if __name__=='__main__':main()
