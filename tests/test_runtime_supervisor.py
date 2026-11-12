"""Real short subprocess tests; all output under this project."""
import dataclasses
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from runtime.supervisor import (ROOT, Identity, Limits, ProcReader, inside,
                                limit_reason, outcome, send_verified, supervise)

BASE = ROOT/'results/tiegcm_supervision_repair_v1/tests_local'
BASE.mkdir(parents=True, exist_ok=True)
RESULTS = []
class Supervision(unittest.TestCase):
    def run_job(self, code, limits=None, **kw):
        directory = BASE/(self._testMethodName+'_'+str(time.time_ns()))
        directory.mkdir()
        result = supervise([sys.executable, '-c', code], directory,
                           limits or Limits(3, 256*2**20, 0, 8*2**20, 2**20, .02, .1), **kw)
        RESULTS.append(dict(test=self._testMethodName, **result))
        return result, directory

    def test_A_normal_exit(self):
        r,_=self.run_job("import time;print('hello',flush=True);time.sleep(.09)")
        self.assertEqual((r['returncode'],r['qualification'],r['exit_kind']),(0,'PASS','NORMAL'))
        self.assertIsNotNone(r['peak_sampled_tree_rss_bytes'])

    def test_B_nonzero(self):
        r,_=self.run_job('raise SystemExit(7)')
        self.assertEqual((r['returncode'],r['qualification'],r['exit_kind']),(7,'FAIL','NONZERO'))

    def test_C_disappearing_proc_deterministic(self):
        reader=ProcReader()
        with patch.object(reader,'names',return_value=['999999999','abc',str(os.getpid())]):
            ident,_,_=reader.read(os.getpid())
            snap=reader.sample(ident)
        self.assertEqual(snap['races'],1)
        self.assertEqual(snap['issue'],None)

    def test_C_actual_short_lived_unrelated_processes(self):
        helpers=[subprocess.Popen([sys.executable,'-c','pass'],cwd=ROOT) for _ in range(12)]
        try:
            r,_=self.run_job('import time;time.sleep(.12)')
            self.assertEqual(r['returncode'],0)
        finally:
            for p in helpers:p.wait(timeout=3)

    def test_D_timeout(self):
        r,_=self.run_job('import time;time.sleep(10)',Limits(.12,2**28,0,2**20,2**20,.01,.1))
        self.assertEqual(r['exit_kind'],'TIMEOUT');self.assertLess(r['returncode'],0)
        self.assertTrue(r['cleanup_verified']);self.assertLess(r['elapsed_s'],2)

    def test_E_resource_limits(self):
        for name,values in [('rss_limit',dict(rss_bytes=11)),('disk_floor',dict(free_disk_bytes=0)),('output_limit',dict(output_bytes=11)),('volume_limit',dict(largest_volume_bytes=11)),('total_output_limit',dict(total_output_bytes=11))]:
            with self.subTest(name=name):
                lim=Limits(2,10,1,10,10,total_output_bytes=10)
                self.assertEqual(limit_reason(values,lim),name)
        self.assertIsNone(limit_reason(dict(rss_bytes=None),Limits(1,10,0,10,10)))

    def test_E_real_small_volume(self):
        r,_=self.run_job("import time;open('test.nc','wb').write(b'x'*200);time.sleep(1)",Limits(2,2**28,0,2**20,100,.02,.1))
        self.assertEqual(r['stop_reason'],'volume_limit');self.assertTrue(r['cleanup_verified'])

    def test_F_recoverable_sampling_error(self):
        from runtime.supervisor import resource_snapshot
        count=[0]
        def sample(*args):
            count[0]+=1
            if count[0]==1:raise ProcessLookupError('injected disappearing process')
            return resource_snapshot(*args)
        r,_=self.run_job('import time;time.sleep(.14)',sampler=sample)
        self.assertEqual((r['returncode'],r['exit_kind']),(0,'NORMAL'))
        self.assertEqual(r['qualification'],'PARTIAL');self.assertEqual(len(r['gaps']),1)
        self.assertGreater(len(r['samples']),0)

    def test_F_persistent_sampling_error_fails_closed(self):
        def broken(*args):raise OSError('injected monitor unavailable')
        r,_=self.run_job('import time;time.sleep(10)',sampler=broken)
        self.assertEqual(r['stop_reason'],'monitoring_unavailable');self.assertIsNotNone(r['returncode'])
        self.assertEqual(r['qualification'],'PARTIAL');self.assertTrue(r['cleanup_verified'])

    def test_G_signal_exit(self):
        r,_=self.run_job('import os,signal;os.kill(os.getpid(),signal.SIGTERM)')
        self.assertEqual((r['exit_kind'],r['signal']),('SIGNAL',signal.SIGTERM))

    def test_G_group_kill_and_unrelated_protection(self):
        other=subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)'],cwd=ROOT,start_new_session=True)
        code="""import subprocess,sys,time,signal
p=subprocess.Popen([sys.executable,'-c','import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(10)'])
open('child.json','w').write(str(p.pid))
signal.signal(signal.SIGTERM,signal.SIG_IGN)
time.sleep(10)
"""
        try:
            r,d=self.run_job(code,Limits(.22,2**28,0,2**20,2**20,.02,.1))
            child=int((d/'child.json').read_text());self.assertIsNone(other.poll())
            try:_,state,_=ProcReader().read(child)
            except OSError:state='gone'
            self.assertIn(state,['gone','Z']);self.assertTrue(r['cleanup_verified'])
            self.assertEqual(r['returncode'],-signal.SIGKILL)
        finally:
            other.terminate();other.wait(timeout=3)

    def test_G_supervisor_receives_SIGTERM(self):
        directory=BASE/('owner_signal_'+str(time.time_ns()));directory.mkdir()
        inner=directory/'job';inner.mkdir()
        code="from runtime.supervisor import *; supervise(["+repr(sys.executable)+",'-c','import time;time.sleep(5)'],Path("+repr(str(inner))+"),Limits(2,2**28,0,2**20,2**20,.02,.1))"
        owner=subprocess.Popen([sys.executable,'-c',code],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        try:
            deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                event=inner/'events.jsonl'
                if event.exists() and '"event": "sample"' in event.read_text():break
                time.sleep(.01)
            else:self.fail('Supervisor did not enter sampling loop')
            owner.send_signal(signal.SIGTERM);owner.communicate(timeout=4)
            result=json.loads((inner/'status.json').read_text())
            self.assertEqual(result['stop_reason'],'supervisor_signal_15')
            self.assertEqual(result['returncode'],-signal.SIGTERM)
            self.assertTrue(result['cleanup_verified'])
        finally:
            if owner.poll() is None:owner.terminate();owner.communicate(timeout=4)

    def test_H_unknown_never_pass(self):
        r=outcome(None);self.assertEqual(r['exit_kind'],'UNKNOWN');self.assertIsNone(r['returncode'])
        # Non-child historical process cannot be made waitable by attaching a reader.
        with self.assertRaises(ChildProcessError):os.waitpid(os.getpid(),os.WNOHANG)

    def test_H_actual_wait_result_unavailable(self):
        original = subprocess.Popen.wait
        def lost(proc, timeout=None):
            original(proc, timeout=timeout)
            raise ChildProcessError('injected lost wait ownership after actual child reaped')
        with patch('runtime.supervisor.subprocess.Popen.wait', lost):
            r,_=self.run_job('pass')
        self.assertIsNone(r['returncode']);self.assertEqual(r['exit_kind'],'UNKNOWN')
        self.assertEqual(r['qualification'],'PARTIAL')

    def test_staged_input_and_signal_api(self):
        r,d=self.run_job("assert open('input.inp').read()=='frozen'",input_files={'input.inp':b'frozen'})
        self.assertEqual(r['returncode'],0)
        self.assertEqual((d/'input.inp').read_bytes(),b'frozen')

    def test_identity_reuse_refuses_signal(self):
        child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(3)'],cwd=ROOT,start_new_session=True)
        try:
            root,_,_=ProcReader().read(child.pid)
            fake=dataclasses.replace(root,start_ticks=root.start_ticks-1)
            with patch('runtime.supervisor.pidfd_signal') as send:
                self.assertFalse(send_verified(fake,root,signal.SIGTERM,ProcReader()));send.assert_not_called()
            self.assertIsNone(child.poll())
        finally:child.terminate();child.wait(timeout=3)

    def test_foreign_uid_refuses_signal(self):
        root=Identity(12,3,os.getuid(),12,12)
        other=dataclasses.replace(root,uid=root.uid+1)
        with patch('runtime.supervisor.pidfd_open') as opened:
            self.assertFalse(send_verified(other,root,signal.SIGTERM,ProcReader()));opened.assert_not_called()

    def test_root_birth_mismatch_rss_is_unknown(self):
        actual,_,_=ProcReader().read(os.getpid())
        fake=dataclasses.replace(actual,start_ticks=actual.start_ticks-1)
        snap=ProcReader().sample(fake)
        self.assertIsNone(snap['rss_bytes']);self.assertEqual(snap['members'],{})

    def test_unknown_target_rss_is_not_zero(self):
        root=Identity(999999999,1,os.getuid(),999999999,999999999)
        snap=ProcReader().sample(root);self.assertIsNone(snap['rss_bytes']);self.assertIsNotNone(snap['issue'])

    def test_launcher_error(self):
        d=BASE/('missing_'+str(time.time_ns()));d.mkdir()
        r=supervise([str(ROOT/'missing_executable')],d,Limits(1,2**28,0,2**20,2**20))
        self.assertEqual(r['exit_kind'],'LAUNCH_ERROR');self.assertIsNone(r['returncode'])

    def test_fatal_log_even_at_immediate_exit(self):
        r,_=self.run_job("print('ERROR injected')")
        self.assertEqual(r['returncode'],0);self.assertEqual(r['stop_reason'],'fatal_log_pattern');self.assertEqual(r['qualification'],'FAIL')

    def test_model_validator_failure_does_not_lose_wait(self):
        def invalid(*args):raise ValueError('invalid completed volume')
        r,_=self.run_job('import time;time.sleep(2)',validator=invalid)
        self.assertEqual(r['stop_reason'],'monitoring_unavailable');self.assertIsNotNone(r['returncode'])

    def test_no_overwrite_or_outside(self):
        with self.assertRaises(ValueError):inside('/tmp/not_authorized')
        r,d=self.run_job('pass')
        with self.assertRaises(FileExistsError):supervise(['false'],d,Limits(1,1,0,1,1))

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Supervision))
    (ROOT/f'results/tiegcm_supervision_repair_v1/test_runs_{time.time_ns()}.json').write_text(json.dumps(dict(success=result.wasSuccessful(),tests=result.testsRun,results=RESULTS),indent=2))
    sys.exit(not result.wasSuccessful())
