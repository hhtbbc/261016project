"""V23 static and ordinary MPI helper tests. Never runs TIE-GCM."""
import unittest,sys,json,copy,tempfile,concurrent.futures,subprocess,os,hashlib,fcntl
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R)]
import numpy as np
from netCDF4 import Dataset
import runtime.tiegcm_autumn_execution as e
from runtime.tiegcm_rank_exit import digest
from runtime.supervisor import supervise,Limits
from atmosphere.tiegcm_autumn_acceptance import validate_timelines,dates,inspect_outputs,accept,field
from atmosphere.tiegcm_mar25_acceptance import parse_progress,inspect_density_record,validate_exits
from atmosphere.restart_validation import inspect_restart,check_source_clock
F=e.PACKAGE;BASE=F/'tests_local'
class Autumn(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory(dir=BASE);self.d=Path(self.temp.name);self.p=json.loads((F/'2021/launch_protocol.json').read_text())
    def tearDown(self):self.temp.cleanup()
    def test_A_policy(self):
        p=json.loads((F/'seed_policy_receipt.json').read_text());self.assertEqual(p['SEED_POLICY'],'A_MAREQX_APPROVED');self.assertFalse(p['actual_model_authorized_this_task'])
    def test_seed_SHA_reject(self):
        p=copy.deepcopy(self.p);p['source']['SHA256']='0'*64
        with self.assertRaises(e.GateError):e.validate_binding(p)
    def test_GPI_SHA_reject(self):
        p=copy.deepcopy(self.p);p['GPI']['SHA256']='0'*64
        with self.assertRaises(e.GateError):e.validate_binding(p)
    def test_GPI_other_year_reject(self):
        p=copy.deepcopy(self.p);p['GPI']=json.loads((F/'2022/launch_protocol.json').read_text())['GPI']
        with self.assertRaises(e.GateError):e.validate_binding(p)
    def test_source_start_reject(self):
        with self.assertRaises(e.GateError):e.validate_input(e.expected_input(2021).replace('SOURCE_START = 80 0 0','SOURCE_START = 252 0 0'),2021)
        with self.assertRaises(ValueError):check_source_clock([252,0,0],[80,1,0])
    def test_source_actual_34(self):
        r=inspect_restart(R/e.SEED,[80,0,0]);self.assertTrue(r['structure_complete'] and r['record_available']);self.assertEqual(len(r['missing_required']),0)
    def test_date_overrun_reject(self):
        p=copy.deepcopy(self.p);p['stop_UTC']='2021-09-26T00:00:00Z'
        with self.assertRaises(e.GateError):e.validate_binding(p)
    def test_workdir_crossyear_reject(self):
        p=copy.deepcopy(self.p);p['cwd']=json.loads((F/'2022/launch_protocol.json').read_text())['cwd']
        with self.assertRaises(e.GateError):e.validate_binding(p)
    def test_old_spring_path_reject(self):
        p=copy.deepcopy(self.p);p['cwd']='experiments/tiegcm_2022_mar25_execution_review_v1/actual_run'
        with self.assertRaises(e.GateError):e.validate_binding(p)
    def test_physics_change_reject(self):
        with self.assertRaises(e.GateError):e.validate_input(e.expected_input(2021).replace("POTENTIAL_MODEL = 'HEELIS'","POTENTIAL_MODEL = 'WEIMER'"),2021)
    def test_volume_names_and_counts(self):
        for y in [2021,2022]:
            a=e.validate_input((F/str(y)/'input.inp').read_text(),y);self.assertEqual(a['SOURCE_START'],'80 0 0');self.assertEqual(a['STEP'],'60');self.assertEqual(a['OUTPUT'].count('.nc'),17);self.assertEqual(a['SECOUT'].count('.nc'),16)
    def test_atomic_thread_reservations(self):
        def attempt(_):
            try:e.claim(self.d/'reserved');return True
            except FileExistsError:return False
        with concurrent.futures.ThreadPoolExecutor(4) as pool:self.assertEqual(sum(pool.map(attempt,range(4))),1)
    def test_atomic_process_reservations(self):
        code="import sys;from pathlib import Path;from runtime.tiegcm_autumn_execution import claim\ntry:claim(Path(sys.argv[1]));print('won')\nexcept FileExistsError:print('lost')"
        env=dict(os.environ,PYTHONPATH=str(R/'src'));procs=[subprocess.Popen([sys.executable,'-c',code,str(self.d/'once')],env=env,stdout=subprocess.PIPE,text=True) for _ in range(2)]
        self.assertEqual(sorted(p.communicate(timeout=10)[0].strip() for p in procs),['lost','won'])
    def test_reservation_not_reusable(self):
        e.claim(self.d/'once')
        with self.assertRaises(FileExistsError):e.claim(self.d/'once')
    def test_global_lock_exclusive(self):
        with (self.d/'lock').open('a') as a,(self.d/'lock').open('a') as b:
            fcntl.flock(a,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):fcntl.flock(b,fcntl.LOCK_EX|fcntl.LOCK_NB)
    def test_no_authorization_no_subprocess(self):
        with patch.object(e,'supervise') as spy,patch.object(e,'verify_package') as check:
            with self.assertRaises(e.GateError):e.execute(2021,authorized=False)
            spy.assert_not_called();check.assert_not_called()
    def test_CLI_no_authorization(self):
        p=subprocess.run([sys.executable,str(R/'scripts/execute_tiegcm_autumn_v23.py'),'--year','2021'],capture_output=True,text=True,timeout=10);self.assertNotEqual(p.returncode,0);self.assertIn('authorization required',p.stderr);self.assertFalse((F/'2021/actual_run').exists())
    def test_missing_output_rejected(self):
        with self.assertRaises(e.GateError):inspect_outputs(self.d,self.p)
    def test_timelines_and_boundaries(self):
        import datetime as dt
        for y in [2021,2022]:
            s,t=dates(y);pp=[s+dt.timedelta(days=i) for i in range(17)];ss=[s+dt.timedelta(hours=i) for i in range(1,385)]
            self.assertEqual(validate_timelines(pp,ss,y,1)['secondary_records'],384)
            for bad in [ss[:-1],ss+[ss[-1]],list(reversed(ss)),ss[:2]+[ss[1]]+ss[3:]]:
                with self.assertRaises(e.GateError):validate_timelines(pp,bad,y,1)
            with self.assertRaises(e.GateError):validate_timelines(pp,ss,y,0)
    def test_progress_calendar_complete_and_failure(self):
        import datetime as dt
        start=dates(2021)[0];lines=[]
        for i in range(10,23041,10):
            t=start+dt.timedelta(minutes=i);lines.append(f'Step {i} of 23040 mtime= {int(t.strftime("%j"))} {t.hour} {t.minute}')
        text='\n'.join(lines)+'\nNORMAL EXIT\n';self.assertEqual(parse_progress(text,23040,start)['final_step'],23040)
        with self.assertRaises(ValueError):parse_progress(text.replace(lines[50],'gone'),23040,start)
    def test_release_actual_file_SHA_tamper(self):
        package=self.d/'package';package.mkdir();file=self.d/'frozen.txt';file.write_text('original')
        release=dict(static_checks_PASS=True,SHA256={str(file.relative_to(R)):digest(file)})
        (package/'execution_release.json').write_text(json.dumps(release));file.write_text('changed')
        with patch.object(e,'PACKAGE',package):
            with self.assertRaises(e.GateError):e.verify_package(2021)
    def test_static_release_incomplete_reject(self):
        package=self.d/'partial';package.mkdir();(package/'execution_release.json').write_text(json.dumps(dict(static_checks_PASS=False)))
        with patch.object(e,'PACKAGE',package):
            with self.assertRaises(e.GateError):e.verify_package(2021)
    def test_actual_native_source_grid(self):self.assertTrue(e.validate_native_source(R/e.SEED))
    def test_bad_grid_specific(self):
        p=self.d/'badgrid.nc'
        with Dataset(p,'w',format='NETCDF3_CLASSIC') as n:
            n.history_type='primary'
            for k,v in [('time',1),('mtimedim',3),('lat',1),('lon',72),('lev',29),('ilev',29)]:n.createDimension(k,v)
            n.createVariable('year','i4',('time',))[:]=[2002];n.createVariable('mtime','i4',('time','mtimedim'))[:]=[[80,0,0]]
        with self.assertRaisesRegex(e.GateError,'grid mismatch'):e.validate_native_source(p)
    def test_grid_incompatibility(self):
        from observations.autumn_validation import inspect_initial
        with Dataset(self.d/'wrong_grid.nc','w') as n:n.createDimension('lat',1)
        with self.assertRaises(ValueError):inspect_initial(self.d/'wrong_grid.nc',R/e.SEED)
    def test_actual_warning_gate_reused(self):
        source=(R/'scripts/audit_tiegcm_autumn_v23.py').read_text();self.assertIn('WarningChannel',source);self.assertNotIn('Popen(',source);self.assertNotIn('execute(',source)
    def test_protocol_SHA_unchanged(self):
        self.assertEqual(digest(R/'experiments/thermosphere_independent_date_validation_plan_v20/preregistered_protocol.json'),'eb27a080199d656f6018f47834cc9eaef07897009360ca184d6511e4d3aeb2c4')
    def test_no_actual_run_or_claim_exists(self):
        for y in [2021,2022]:self.assertFalse((F/str(y)/'actual_run').exists());self.assertFalse((F/str(y)/'execution_claim_local.json').exists())
    def test_MPI_direct_wait_success_and_failure_helpers(self):
        # Ordinary MPI C program only; never copies or calls physical binary.
        source=self.d/'ordinary_mpi.c';binary=self.d/'ordinary_mpi'
        source.write_text('#include <mpi.h>\n#include <stdio.h>\n#include <stdlib.h>\nint main(int argc,char**argv){int r,s;MPI_Init(&argc,&argv);MPI_Comm_rank(MPI_COMM_WORLD,&r);MPI_Comm_size(MPI_COMM_WORLD,&s);printf("ORDINARY_MPI_HELPER rank%d size%d\\n",r,s);int bad=getenv("HELPER_FAIL") && r==2;MPI_Finalize();return s!=4?8:(bad?7:0);}\n')
        subprocess.run([str(R/'.envs/tiegcm/bin/mpicc'),str(source),'-o',str(binary)],check=True,capture_output=True,timeout=20)
        for bad in [False,True]:
            run=e.claim(self.d/('failure' if bad else 'success'));env=e.runtime_environment()
            if bad:env['HELPER_FAIL']='yes'
            else:env.pop('HELPER_FAIL',None)
            argv=[str(R/'.envs/tiegcm/bin/mpirun'),'-np','4',sys.executable,str(R/'src/runtime/tiegcm_rank_exit.py'),'--model',str(binary),'--run-id','SYNTHETIC_MPI_HELPER_ONLY','--model-sha',digest(binary),'--input-sha',hashlib.sha256(b'fixture').hexdigest()]
            st=supervise(argv,run,Limits(20,2**30,0,5*2**20,2**20,.1,.3),env=env,input_files={'input.inp':b'fixture'});self.assertTrue(st['cleanup_verified'])
            p=dict(executable={'SHA256':digest(binary)},input={'SHA256':hashlib.sha256(b'fixture').hexdigest()})
            if bad:
                self.assertNotEqual(st['returncode'],0)
                with self.assertRaises(ValueError):validate_exits(run,'SYNTHETIC_MPI_HELPER_ONLY',p)
            else:
                self.assertEqual(st['returncode'],0);self.assertEqual(len(validate_exits(run,'SYNTHETIC_MPI_HELPER_ONLY',p)['ranks']),4)
if __name__=='__main__':unittest.main()
