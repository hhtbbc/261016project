"""All fixtures SIMULATED_TEST_ONLY. Never invoke the formal model entry."""
from pathlib import Path
import sys,json,os,unittest,tempfile,concurrent.futures,subprocess,hashlib
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
import numpy as np
from netCDF4 import Dataset
from runtime.tiegcm_mar25_execution import claim,execute,GateError,verify_preparation
from runtime.tiegcm_rank_exit import digest
from runtime.supervisor import supervise,Limits
from atmosphere.tiegcm_mar25_acceptance import accept_run,parse_progress,inspect_density_record,validate_exits,cold_identity
BASE=ROOT/'experiments/tiegcm_2022_mar25_execution_review_v1/tests_local'
class Review(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory(dir=BASE);self.d=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def test_no_authorization_never_reaches_supervisor(self):
  with patch('runtime.tiegcm_mar25_execution.supervise') as spy:
   with self.assertRaises(GateError):execute(False)
   spy.assert_not_called()
 def test_atomic_concurrent_claim(self):
  def attempt(i):
   try:claim(self.d/'once');return True
   except FileExistsError:return False
  with concurrent.futures.ThreadPoolExecutor(2) as pool:out=list(pool.map(attempt,range(2)))
  self.assertEqual(sum(out),1)
 def test_two_processes_share_one_atomic_claim(self):
  code="from pathlib import Path;import sys;from runtime.tiegcm_mar25_execution import claim\ntry:claim(Path(sys.argv[1]));print('won')\nexcept FileExistsError:print('lost')"
  target=str(self.d/'process_once');children=[subprocess.Popen([sys.executable,'-c',code,target],stdout=subprocess.PIPE,text=True) for _ in range(2)]
  results=[p.communicate(timeout=10)[0].strip() for p in children];self.assertEqual(sorted(results),['lost','won']);self.assertTrue(all(p.returncode==0 for p in children))
 def test_interrupted_claim_no_retry(self):
  claim(self.d/'once')
  with self.assertRaises(FileExistsError):claim(self.d/'once')
 def test_nonempty_supervisor_contract_and_correct_staging(self):
  run=claim(self.d/'run');st=supervise([sys.executable,'-c',"from pathlib import Path;assert Path('input.inp').read_bytes()==b'frozen'"],run,Limits(5,2**30,0,2**20,2**20,.05,.2),input_files={'input.inp':b'frozen'})
  self.assertEqual(st['returncode'],0);self.assertEqual((run/'input.inp').read_bytes(),b'frozen')
  with self.assertRaises(FileExistsError):supervise([sys.executable,'-c','pass'],run,Limits(1,2**30,0,2**20,2**20))
 def test_old_nonempty_directory_reproduces_bug(self):
  (self.d/'input.inp').write_text('not empty')
  with self.assertRaises(FileExistsError):supervise(['not_launched'],self.d,Limits(1,2**30,0,2**20,2**20))
 def test_manifest_tamper_refused(self):
  prep=self.d/'prep';review=self.d/'review';prep.mkdir();review.mkdir();m=prep/'sha256_manifest.json';m.write_text('{}');(review/'execution_overlay.json').write_text(json.dumps(dict(preparation_manifest_SHA256='0'*64)))
  with self.assertRaises(GateError):verify_preparation(prep,review)
 def test_not_run_is_not_pass(self):
  r=accept_run(self.d/'missing','NONE',{});self.assertEqual(r['ACTUAL_MODEL_RUN'],'NOT_RUN');self.assertTrue(all(v['status']=='NOT_RUN' for v in r['checks'].values()))
 def test_reserved_run_without_wait_is_unknown(self):
  result=accept_run(self.d,'test',{});self.assertEqual(result['ACTUAL_MODEL_RUN'],'UNKNOWN');self.assertEqual(result['overall'],'FAIL')
 def test_invalid_model_driver_cannot_hide_in_max_nan(self):
  from atmosphere.tiegcm_mar25_acceptance import driver_difference
  for value in [np.nan,np.inf,-np.inf,np.ma.masked]:
   with self.assertRaises(ValueError):driver_difference(value,1.)
  self.assertEqual(driver_difference(2.,1.),1.)
 def test_registered_calendar_gaps_duplicates_and_boundary(self):
  import datetime
  from atmosphere.tiegcm_mar25_acceptance import START,validate_timelines
  pp=[START+datetime.timedelta(days=i) for i in range(18)];ss=[START+datetime.timedelta(hours=i) for i in range(1,409)]
  self.assertEqual(validate_timelines(pp,ss,1)['secondary_records'],408)
  for bad in [ss[:-1],ss+[ss[-1]],ss[:10]+[ss[9]]+ss[11:],list(reversed(ss))]:
   with self.assertRaises(ValueError):validate_timelines(pp,bad,1)
  with self.assertRaises(ValueError):validate_timelines(pp[:-1],ss,1)
  with self.assertRaises(ValueError):validate_timelines(pp,ss,0)
 def test_missing_outputs_refused(self):
  from atmosphere.tiegcm_mar25_acceptance import inspect_outputs
  with self.assertRaises(ValueError):inspect_outputs(self.d)
 def test_parent_exit0_without_evidence_fails(self):
  (self.d/'status.json').write_text(json.dumps(dict(returncode=0,qualification='PASS',gaps=[],cleanup_verified=True,wait_source='direct subprocess.Popen.wait',elapsed_s=1)))
  r=accept_run(self.d,'NONE',{});self.assertEqual(r['overall'],'FAIL')
 def test_nonzero_supervision_stops_before_nc(self):
  (self.d/'status.json').write_text(json.dumps(dict(returncode=7,qualification='FAIL',gaps=[],cleanup_verified=True)))
  r=accept_run(self.d,'NONE',{});self.assertEqual(r['checks']['supervision']['status'],'FAIL');self.assertEqual(r['checks']['output_files']['status'],'NOT_RUN')
 def test_normal_exit_lines_do_not_prove_rank_exit(self):
  (self.d/'stdout.log').write_text('NORMAL EXIT\n'*4)
  with self.assertRaises(ValueError):validate_exits(self.d,'test',{})
 def test_step_completion_and_calendar(self):
  txt='Step 1 of 2 mtime= 68 0 1\nStep 2 of 2 mtime= 68 0 2\nNORMAL EXIT\n';self.assertEqual(parse_progress(txt,steps=2)['final_step'],2)
  for bad in [txt.replace('Step 2','Step 1'),txt.replace('68 0 2','68 0 3'),txt.replace('Step 2 of 2 mtime= 68 0 2\n',''),txt+'ERROR injected\n',txt+'NORMAL EXIT\n']:
   with self.assertRaises(ValueError):parse_progress(bad,steps=2)
 def density_file(self):
  p=self.d/'tiny.nc'
  with Dataset(p,'w') as n:
   for k,v in [('time',1),('ilev',2),('lat',1),('lon',1)]:n.createDimension(k,v)
   for k,u in [('DEN','g/cm3'),('ZG','cm')]:v=n.createVariable(k,'f8',('time','ilev','lat','lon'),fill_value=9.99e32);v.units=u;v[:]=np.array([1,2]).reshape(1,2,1,1)
  return p
 def test_tiny_density_schema_and_failures(self):
  p=self.density_file()
  with Dataset(p) as n:self.assertTrue(inspect_density_record(n,0)['valid'])
  for name,value in [('DEN',np.nan),('DEN',np.inf),('DEN',0),('DEN',-1),('DEN',9.99e32),('ZG',9.99e32)]:
   with Dataset(p,'a') as n:n[name][0,0,0,0]=value
   with Dataset(p) as n:
    with self.assertRaises(ValueError):inspect_density_record(n,0)
   with Dataset(p,'a') as n:n[name][0,0,0,0]=1
  with Dataset(p,'a') as n:n['DEN'].units='kg/m3'
  with Dataset(p) as n:
   with self.assertRaises(ValueError):inspect_density_record(n,0)
 def test_zg_not_monotonic(self):
  p=self.density_file()
  with Dataset(p,'a') as n:n['ZG'][0,1,0,0]=0
  with Dataset(p) as n:
   with self.assertRaises(ValueError):inspect_density_record(n,0)
 def test_existing_one_hour_warm_record_only(self):
  p=ROOT/'experiments/tiegcm_2022_b14_exploratory_pair_v2/B14/secondary_001.nc'
  with Dataset(p) as n:self.assertTrue(inspect_density_record(n,0)['valid'])
 def test_existing_native_cold_echo_only(self):
  from atmosphere.tiegcm_mar25_acceptance import START
  p=ROOT/'experiments/tiegcm_2022_b14_exploratory_pair_v2/B14/primary_001.nc'
  with Dataset(p) as n:self.assertTrue(cold_identity(n,START,0));self.assertFalse('DEN' in n.variables)
  p=self.density_file()
  with Dataset(p) as n:
   with self.assertRaises(ValueError):cold_identity(n,START,0)
 def test_rank_wrapper_real_MPI_initialization_CPU_only(self):
  # Existing compiler; tiny MPI_Init/Finalize program, NOT TIE-GCM or fabricated log.
  source=self.d/'mpi_hello.c';binary=self.d/'mpi_hello'
  source.write_text('#include <mpi.h>\n#include <stdio.h>\nint main(int argc,char**argv){int rank,size;MPI_Init(&argc,&argv);MPI_Comm_rank(MPI_COMM_WORLD,&rank);MPI_Comm_size(MPI_COMM_WORLD,&size);printf("ordinary MPI C helper rank%d size%d\\n",rank,size);MPI_Finalize();return size==4?0:8;}\n')
  subprocess.run([str(ROOT/'.envs/tiegcm/bin/mpicc'),str(source),'-o',str(binary)],check=True,capture_output=True,text=True,timeout=15)
  run=claim(self.d/'real_mpi');env=dict(os.environ,OMPI_ALLOW_RUN_AS_ROOT='1',OMPI_ALLOW_RUN_AS_ROOT_CONFIRM='1',OMPI_MCA_pml='ob1',OMPI_MCA_btl='self,tcp',OMPI_MCA_osc='rdma',PMIX_MCA_gds='hash')
  cmd=[str(ROOT/'.envs/tiegcm/bin/mpirun'),'-np','4',sys.executable,str(ROOT/'src/runtime/tiegcm_rank_exit.py'),'--model',str(binary),'--run-id','ORDINARY_MPI_INIT_TEST_ONLY','--model-sha',digest(binary),'--input-sha',hashlib.sha256(b'frozen').hexdigest()]
  st=supervise(cmd,run,Limits(15,2**30,0,5*2**20,2**20,.1,.3),env=env,input_files={'input.inp':b'frozen'});self.assertEqual(st['returncode'],0);self.assertTrue(st['cleanup_verified'])
  for rank in range(4):
   receipt=json.loads((run/f'rank_{rank:03d}_exit.json').read_text());self.assertEqual(receipt['returncode'],0);self.assertEqual(receipt['wrapper_sid'],st['identity']['sid']);self.assertEqual(receipt['child_sid'],st['identity']['sid'])
 def test_safe_rank_wrapper_MPI_helpers(self):
  # Two ordinary MPI helper jobs: normal and one failing rank; never physical model.
  helper=self.d/'helper';helper.write_text('#!'+sys.executable+'\nimport os,sys\nprint("ordinary CPU helper",flush=True)\nsys.exit(7 if os.getenv("INJECT_FAIL")=="yes" and os.getenv("OMPI_COMM_WORLD_RANK")=="2" else 0)\n');helper.chmod(0o700)
  for fail in [False,True]:
   run=claim(self.d/('bad' if fail else 'good'));env=dict(os.environ,OMPI_ALLOW_RUN_AS_ROOT='1',OMPI_ALLOW_RUN_AS_ROOT_CONFIRM='1',OMPI_MCA_pml='ob1',OMPI_MCA_btl='self,tcp',OMPI_MCA_osc='rdma',PMIX_MCA_gds='hash',INJECT_FAIL='yes' if fail else 'no')
   cmd=[str(ROOT/'.envs/tiegcm/bin/mpirun'),'-np','4',sys.executable,str(ROOT/'src/runtime/tiegcm_rank_exit.py'),'--model',str(helper),'--run-id','SIMULATED_TEST_ONLY','--model-sha',digest(helper),'--input-sha',hashlib.sha256(b'frozen').hexdigest()]
   st=supervise(cmd,run,Limits(15,2**30,0,5*2**20,2**20,.1,.3),env=env,input_files={'input.inp':b'frozen'});self.assertTrue(st['cleanup_verified'])
   receipts=[json.loads(p.read_text()) for p in sorted(run.glob('rank_*_exit.json'))]
   if fail:
    self.assertNotEqual(st['returncode'],0);self.assertEqual(next(x for x in receipts if x['rank']==2)['returncode'],7)
    # MPI may abort peers before their final receipt; missing ranks are never inferred0.
    with self.assertRaises(ValueError):validate_exits(run,'SIMULATED_TEST_ONLY',dict(executable={'SHA256':digest(helper)},input={'SHA256':hashlib.sha256(b'frozen').hexdigest()}))
   else:self.assertEqual(len(receipts),4);self.assertEqual(st['returncode'],0);self.assertTrue(all(x['returncode']==0 for x in receipts))
if __name__=='__main__':unittest.main()
