"""Targeted CPU fixtures only; no TIE-GCM invocation or real-data scoring."""
from pathlib import Path
import sys,unittest,tempfile,json,os,warnings,subprocess,hashlib,importlib.util,ast
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R)]
import numpy as np
from netCDF4 import Dataset
from runtime.readonly_audit_warning_channel import WarningChannel,AuditWarningError,sha
from runtime.supervisor import supervise,Limits
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from atmosphere.tiegcm_mar25_acceptance import inspect_density_record,parse_progress,validate_timelines
F=R/'experiments/tiegcm_2022_mar25_postrun_acceptance_v17';BASE=F/'tests_local';READER=R/'src/atmosphere/hourly_tiegcm_observation.py'
def fixture(path,missing=1e36,fill=False):
 with Dataset(path,'w',format='NETCDF3_CLASSIC') as n:
  for k,v in [('time',2),('ilev',2),('lat',2),('lon',72),('mtimedim',3)]:n.createDimension(k,v)
  n.createVariable('time','f8',('time',))[:]=[0,1];n['time'].units='hours since 2022-03-25 00:00:00'
  n.createVariable('year','i4',('time',))[:]=[2022,2022];n.createVariable('mtime','i4',('time','mtimedim'))[:]=[[84,0,0],[84,1,0]]
  for k,v in [('ilev',[1.,2.]),('lat',[-5.,5.]),('lon',np.arange(0,360,5.))]:n.createVariable(k,'f8',(k,))[:]=v
  for k,unit in [('DEN','g/cm3'),('ZG','cm')]:
   options={'fill_value':np.float32(1e36)} if fill else {};v=n.createVariable(k,'f4',('time','ilev','lat','lon'),**options);v.units=unit;v.setncattr('missing_value',np.float64(missing));v[:]=1e-15 if k=='DEN' else np.array([10000,20000])[None,:,None,None]
def tiny_read(path):
 p=HourlyTiegcmObservation([path],{path.name:sha(path)},'2022-03-25T00:00:00','2022-03-25T01:00:00','SYNTHETIC_NUMERICAL_TEST');return p
class V17(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory(dir=BASE);self.d=Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def test_A_B_known_warning_source_preserved_valid_data(self):
  p=self.d/'tiny.nc';fixture(p);directory=self.d/'journal';directory.mkdir()
  with WarningChannel(directory,{READER:sha(READER)}) as c:
   q=tiny_read(p);self.assertTrue(np.isfinite(q.arrays[0][1]).all());q.close()
  self.assertGreater(c.count,0);self.assertIn('np.nan',(directory/'warnings_raw_local.log').read_text());rows=[json.loads(x) for x in (directory/'warning_records_local.jsonl').read_text().splitlines()];self.assertTrue(all(x['classification']=='KNOWN_NETCDF_CAST_METADATA_WARNING' for x in rows))
 def test_B_no_numerical_change_for_valid_values(self):
  p=self.d/'tiny.nc';fixture(p)
  with Dataset(p) as n:
   with warnings.catch_warnings(record=True) as caught:warnings.simplefilter('always');a=n['DEN'][:]
   n['DEN'].set_auto_mask(False);b=n['DEN'][:];self.assertGreater(len(caught),0);np.testing.assert_array_equal(a.data,b);self.assertFalse(np.ma.getmaskarray(a).any());self.assertEqual(str(n['DEN'].dtype),'float32');self.assertEqual(str(np.asarray(n['DEN'].missing_value).dtype),'float64')
 def test_C_actual_nan_inf_rejected(self):
  for value in [np.nan,np.inf,-np.inf]:
   p=self.d/('bad'+str(value)+'.nc');fixture(p)
   with Dataset(p,'a') as n:n['DEN'][0,0,0,0]=value
   with Dataset(p) as n:
    with self.assertRaises(ValueError):inspect_density_record(n,0)
 def test_D_inexact_missing_marker_automatic_mask_risk(self):
  p=self.d/'unsafe_marker.nc';fixture(p,missing=1.23456789e-15)
  with Dataset(p,'a') as n:n['DEN'][0,0,0,0]=np.float32(1.23456789e-15)
  with Dataset(p) as n:
   with warnings.catch_warnings(record=True):warnings.simplefilter('always');a=n['DEN'][:];self.assertFalse(np.ma.getmaskarray(a)[0,0,0,0])
   with self.assertRaises(ValueError):inspect_density_record(n,0)
 def test_D_fillvalue_rejected(self):
  p=self.d/'fill.nc';fixture(p,fill=True)
  with Dataset(p,'a') as n:n['DEN'][0,0,0,0]=np.float32(1e36)
  with Dataset(p) as n:
   with self.assertRaises(ValueError):inspect_density_record(n,0)
 def test_E_nonpositive_den_and_zg_order(self):
  for i,value in enumerate([0.,-1.]):
   p=self.d/f'negative{i}.nc';fixture(p)
   with Dataset(p,'a') as n:n['DEN'][0,0,0,0]=value
   with Dataset(p) as n:
    with self.assertRaises(ValueError):inspect_density_record(n,0)
  p=self.d/'badz.nc';fixture(p)
  with Dataset(p,'a') as n:n['ZG'][0,1,0,0]=0
  with Dataset(p) as n:
   with self.assertRaises(ValueError):inspect_density_record(n,0)
 def test_unknown_warning_fail_closed(self):
  d=self.d/'unknown';d.mkdir()
  with self.assertRaises(AuditWarningError):
   with WarningChannel(d,{READER:sha(READER)}):warnings.warn('Actual density NaN found',UserWarning)
 def test_warning_source_identity_cannot_be_spoofed(self):
  from runtime.readonly_audit_warning_channel import KNOWN
  d=self.d/'wrong';d.mkdir()
  with self.assertRaises(AuditWarningError):
   with WarningChannel(d,{READER:'0'*64}) as c:c.record(UserWarning(KNOWN),UserWarning,str(READER),31)
 def test_warning_handler_restored(self):
  old=warnings.showwarning;d=self.d/'restore';d.mkdir()
  with WarningChannel(d,{READER:sha(READER)}):pass
  self.assertIs(warnings.showwarning,old)
 def job(self,code,sampler=None):
  p=self.d/('job'+str(len(list(self.d.iterdir()))));p.mkdir();return supervise([sys.executable,'-c',code],p,Limits(3,2**30,0,5*2**20,2**20,.02,.1,max_sampling_failures=1),sampler=sampler),p
 def test_F_real_traceback_fails(self):
  s,p=self.job("raise ValueError('deliberate actual exception')");self.assertNotEqual(s['returncode'],0);self.assertNotEqual(s['qualification'],'PASS');self.assertIn('Traceback',(p/'stdout.log').read_text())
 def test_G_nonzero_signal_and_monitor_failure(self):
  s,_=self.job('raise SystemExit(7)');self.assertEqual(s['returncode'],7);self.assertNotEqual(s['qualification'],'PASS')
  s,_=self.job('import os,signal;os.kill(os.getpid(),signal.SIGTERM)');self.assertEqual(s['returncode'],-15);self.assertNotEqual(s['qualification'],'PASS')
  def broken(*args):raise OSError('injected monitor failure')
  s,_=self.job('import time;time.sleep(2)',sampler=broken);self.assertNotEqual(s['qualification'],'PASS');self.assertTrue(s['cleanup_verified'])
 def test_H_original_fatal_model_semantics_unchanged(self):
  for word in ['NaN','Inf','ERROR','MPI_ABORT']:
   s,_=self.job(f"import time;print({word!r},flush=True);time.sleep(.1)");self.assertNotEqual(s['qualification'],'PASS');self.assertEqual(s['stop_reason'],'fatal_log_pattern')
 def test_original_false_positive_and_narrow_new_channel(self):
  # Genuine NetCDF warning from the unchanged source, not a forged success log.
  p=self.d/'valid.nc';fixture(p);helper=self.d/'helper.py';journal=self.d/'journal';journal.mkdir()
  helper.write_text("from pathlib import Path\nfrom runtime.readonly_audit_warning_channel import WarningChannel,sha\nfrom atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation\nimport sys\np=Path(sys.argv[1]);r=Path(sys.argv[3])\nif sys.argv[2]=='new':\n with WarningChannel(Path(sys.argv[4]),{r:sha(r)}):\n  q=HourlyTiegcmObservation([p],{p.name:sha(p)},'2022-03-25T00:00:00','2022-03-25T01:00:00','SYNTHETIC_TEST');q.close()\nelse:\n q=HourlyTiegcmObservation([p],{p.name:sha(p)},'2022-03-25T00:00:00','2022-03-25T01:00:00','SYNTHETIC_TEST');q.close()\n")
  for mode in ['old','new']:
   job=self.d/mode;job.mkdir();st=supervise([sys.executable,str(helper),str(p),mode,str(READER),str(journal)],job,Limits(5,2**30,0,5*2**20,2**20,.05,.1),env=dict(os.environ,PYTHONPATH=str(R/'src')+':'+str(R)))
   if st['qualification']!=('PASS' if mode=='new' else 'FAIL'):
    import time
    (BASE/f'subprocess_{mode}_failure_{time.time_ns()}.log').write_text((job/'stdout.log').read_text())
   self.assertEqual(st['qualification'],'PASS' if mode=='new' else 'FAIL')
   if mode=='old':self.assertEqual(st['stop_reason'],'fatal_log_pattern');self.assertIn('np.nan',(job/'stdout.log').read_text())
   else:self.assertEqual(st['returncode'],0)
 def test_frozen_scientific_codes_unchanged(self):
  p=R/'experiments/tiegcm_2022_mar25_preparation_v1/frozen_evaluation_protocol.json';proto=json.loads(p.read_text());manifest=json.loads((p.parent/'sha256_manifest.json').read_text());self.assertEqual(sha(p),manifest[str(p.relative_to(R))])
  for key in ['metric_source','latitude_source','Map_A_source','operator_source','hourly_reader_source']:e=proto[key];self.assertEqual(sha(R/e['path']),e['SHA256'])
  original=json.loads((F/'protected_assets_local.json').read_text());self.assertEqual(sha(R/'src/runtime/supervisor.py'),original['src/runtime/supervisor.py'])
 def test_no_model_launch_path_in_worker(self):
  source=(R/'scripts/audit_tiegcm_v17_readonly.py').read_text();self.assertNotIn('--authorize-17day-run',source);self.assertNotIn('execute_tiegcm_2022_mar25',source);self.assertNotIn('Popen(',source)
  spec=importlib.util.spec_from_file_location('v17_launcher',R/'scripts/launch_tiegcm_v17_readonly.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);argv=m.audit_argv();self.assertEqual(Path(argv[1]).name,'audit_tiegcm_v17_readonly.py');self.assertEqual(len(argv),2)
 def test_worker_failure_never_launches_any_subprocess(self):
  spec=importlib.util.spec_from_file_location('v17_worker',R/'scripts/audit_tiegcm_v17_readonly.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.F=self.d;m.RUN=self.d/'missing_outputs'
  (self.d/'audit_protocol.json').write_text(json.dumps(dict(code_SHA256={'src/runtime/supervisor.py':sha(R/'src/runtime/supervisor.py')},frozen_reader_SHA256=sha(READER),run_id='SYNTHETIC_TEST_ONLY')))
  with patch.object(Path,'cwd',return_value=self.d),patch.object(m,'accept_run',return_value={'overall':'FAIL'}),patch('subprocess.Popen',side_effect=AssertionError('no subprocess allowed')) as launch:
   with self.assertRaises(ValueError):m.main()
   launch.assert_not_called()
 def test_no_overwrite_and_partial_output_never_pass(self):
  d=self.d/'reserved';d.mkdir();(d/'status.json').write_text('reserved')
  with self.assertRaises(FileExistsError):supervise(['never_run'],d,Limits(1,2**30,0,2**20,2**20))
  from atmosphere.tiegcm_mar25_acceptance import accept_run
  self.assertEqual(accept_run(self.d/'absent','no',{})['overall'],'NOT_RUN')
 def test_timeline_and_genuine_step_failures(self):
  import datetime
  from atmosphere.tiegcm_mar25_acceptance import START
  pp=[START+datetime.timedelta(days=i) for i in range(18)];ss=[START+datetime.timedelta(hours=i) for i in range(1,409)]
  with self.assertRaises(ValueError):validate_timelines(pp,ss[:-1],1)
  with self.assertRaises(ValueError):parse_progress('NORMAL EXIT\n')
if __name__=='__main__':unittest.main()
