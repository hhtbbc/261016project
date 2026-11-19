"""Freeze the V19 read-only verification protocol; hash old assets, no metric access."""
from pathlib import Path
import sys,json,subprocess,datetime
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src')]
from evaluation.density_verification import sha,check_sha,require,write_json
F=R/'experiments/tiegcm_2022_mar25_independent_verification_v19';V18=R/'experiments/tiegcm_2022_mar25_density_validation_v18'
def load(p):return json.loads(Path(p).read_text())
def main():
 F.resolve().relative_to(R);F.mkdir(exist_ok=False)
 baseline='0c93ddcea2bef867a639a3045b5e7937d0d5fa2c';head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();require(head==baseline,'HEAD changed; inspect before verification')
 recorded=load(V18/'sha256_manifest.json')['files']
 for e in recorded:check_sha(R/e['path'],e['SHA256'])
 receipt=load(V18/'parameter_freeze_receipt.json');check_sha(V18/'correction_parameters.json',receipt['SHA256']);require(receipt['SHA256']=='743cbf099c417a4b74a530151c08c6c5a8c746cfc0ee5ae30a3ca54075521470','Unexpected frozen parameters')
 # Commit authenticates all already tracked V18 files; local full arrays had no public pre-V19 file digest.
 tracked=subprocess.check_output(['git','ls-files','-z'],cwd=R).decode().split('\0');protected={}
 for name in tracked:
  if not name or name in ['STATUS.md','WORKLOG.md','.gitignore']:continue
  p=R/name
  if p.is_file():protected[name]=sha(p)
 for name in tracked:
  if name.startswith('experiments/tiegcm_2022_mar25_density_validation_v18/'):
   actual=(R/name).read_bytes();expected=subprocess.check_output(['git','show',baseline+':'+name],cwd=R);require(actual==expected,'Committed V18 asset mismatch: '+name)
 source=load(V18/'source_manifest.json')
 for x in source['model_outputs']:check_sha(R/x['path'],x['SHA256']);protected[x['path']]=x['SHA256']
 check_sha(R/source['CDF']['path'],source['CDF']['SHA256']);protected[source['CDF']['path']]=source['CDF']['SHA256']
 # Track all local V18 evidence before/after without claiming retroactive publisher hashes.
 local=[]
 for p in V18.rglob('*'):
  if p.is_file():protected[str(p.relative_to(R))]=sha(p);local.append(str(p.relative_to(R)))
 for n,h in source['reference_2021'].items():check_sha(R/'experiments/causal_density_new_date_validation_v1'/n,h)
 require(load(R/'experiments/tiegcm_2022_mar25_postrun_acceptance_v17/result.json')['overall']=='ENGINEERING_PASS','V17 not PASS');require(load(V18/'result.json')['status']=='INCONCLUSIVE','V18 historical status changed')
 write_json(F,'asset_protection_before.json',dict(PASS=True,HEAD=head,protected_SHA256=protected,committed_V18_files_verified=True,V18_manifest_entries=len(recorded),models=35,local_V18_files=len(local),local_prior_digest_limit='matched_local.npz and common_sample_ids_local.csv were not in public V18 hash manifest. Current file digests frozen now; identity must also be independently checked against CDF, raw NetCDF, parameter sample hashes and stored coverage ID hashes. No retroactive historical SHA claim.'))
 protocol=dict(task='V19 independent verification only',original_scientific_scores=1,new_scientific_scoring_calls=0,new_fits=0,read_only=True,V18_historical_status='INCONCLUSIVE',rtol=1e-13,atol=0,zero_rule='isclose(main,independent,rtol=1e-13,atol=0); independent zero requires exactly zero, no exceptional Bias rule',C1='Diagnostic sorted median/logarithms and exp implementations only; never write parameters',C2='Build all corrected predictions only from validated stored raw queries and frozen multiplier; no exponent substitute',raw_provenance='Direct CDF exact comparison plus independent native NetCDF 25-frame eight-column query reconstruction at frozen tolerance; stored Raw is the original query numerical contract, not corrected prediction input',complete_tables=['metrics.csv','region_metrics.csv','time_block_metrics.csv','joint_assessment.csv','pointwise_diagnostics.csv','coverage.csv'],window_semantics='original half-open 06Z/18Z windows and bands, no changes',minimum_N=30,collect_all_checks=True,one_complete_verification_attempt=True,failure_no_retry=True,code_SHA256={n:sha(R/n) for n in ['src/evaluation/density_verification.py','scripts/prepare_density_verification_v19.py','scripts/verify_density_validation_v19.py','scripts/launch_density_verification_v19.py','tests/test_density_verification_v19.py']},resources=dict(wall_s=600,RSS_bytes=4*2**30,outputs_bytes=150*2**20,GPU=0,download=0,model=0),frozen_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
 write_json(F,'protocol.json',protocol);write_json(F,'commands.json',dict(prepare='python scripts/prepare_density_verification_v19.py',tests='python -m unittest discover -s tests -p test_density_verification_v19.py -v',single_readonly_verification='python scripts/launch_density_verification_v19.py',forbidden_V18_entry_not_called=True))
 (F/'tests_local').mkdir();print('V19 PROTECTION AND PROTOCOL FROZEN; NO TABLE VALUES VERIFIED YET',flush=True)
if __name__=='__main__':main()
