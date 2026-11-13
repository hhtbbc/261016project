"""CPU-only environment policy tests; no real CUDA initialization or model launch."""
import os,sys,unittest,subprocess,json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from runtime.gpu_environment import (visibility_snapshot,require_gpu_assignment,
 configure_determinism,assert_visibility,require_cuda)
class GPUEnvironment(unittest.TestCase):
 def subprocess_check(self,code,value):
  env=dict(os.environ)
  if value is None:env.pop('CUDA_VISIBLE_DEVICES',None)
  else:env['CUDA_VISIBLE_DEVICES']=value
  subprocess.run([sys.executable,'-c',"import sys,os;sys.path[:0]=['src','scripts'];"+code],cwd=ROOT,env=env,check=True,timeout=30)
 def test_persistence_import_all_assignments(self):
  for value in [None,'','-1','0','3','GPU-frozen-allocation']:
   self.subprocess_check("before=dict(os.environ);import persistence_den_engineering_v3;assert os.environ.get('CUDA_VISIBLE_DEVICES')==before.get('CUDA_VISIBLE_DEVICES');assert ('CUDA_VISIBLE_DEVICES' in os.environ)==('CUDA_VISIBLE_DEVICES' in before)",value)
 def test_import_orders(self):
  for order in [('persistence_den_engineering_v3','training.den_engineering'),('training.den_engineering','persistence_den_engineering_v3'),('train_den_gpu_smoke_v4','persistence_den_engineering_v3')]:
   self.subprocess_check("before=os.environ.get('CUDA_VISIBLE_DEVICES');"+';'.join('import '+x for x in order)+";assert os.environ.get('CUDA_VISIBLE_DEVICES')==before",'2')
 def test_cpu_evaluation_preserves_assignment(self):
  self.subprocess_check("import persistence_den_engineering_v3 as p;import numpy as np;from training.den_engineering import density_metrics;density_metrics(np.ones((1,2,2)),np.ones((1,2,2)),[-45,45]);assert os.environ['CUDA_VISIBLE_DEVICES']=='3'",'3')
 def test_explicitly_disabled_rejected(self):
  for value in ['','-1','NoDevFiles','0,','0,0']:
   with self.assertRaises(RuntimeError):require_gpu_assignment({'CUDA_VISIBLE_DEVICES':value})
 def test_legal_device_preserved_and_unset_preserved(self):
  for env in [{},{'CUDA_VISIBLE_DEVICES':'3'},{'CUDA_VISIBLE_DEVICES':'MIG-frozen-uuid'}]:
   before=visibility_snapshot(env);configure_determinism(env);self.assertEqual(before,visibility_snapshot(env));self.assertEqual(env['CUBLAS_WORKSPACE_CONFIG'],':4096:8')
 def test_conflicting_determinism_rejected(self):
  with self.assertRaises(RuntimeError):configure_determinism({'CUBLAS_WORKSPACE_CONFIG':':16:8'})
 def test_import_pollution_detected(self):
  with self.assertRaises(RuntimeError):assert_visibility({'present':True,'value':'3'},{'CUDA_VISIBLE_DEVICES':''})
 def test_disabled_does_not_call_cuda(self):
  mock=Mock()
  with patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':''}):
   with self.assertRaises(RuntimeError):require_cuda(mock,visibility_snapshot())
  mock.cuda.is_available.assert_not_called()
 def test_unavailable_cuda_blocks_training(self):
  mock=Mock();mock.cuda.is_available.return_value=False
  with patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':'3'}):
   with self.assertRaises(RuntimeError):require_cuda(mock,visibility_snapshot())
  mock.cuda.get_device_name.assert_not_called()
 def test_device_mock_uses_inherited_logical_zero(self):
  mock=Mock();mock.__version__='mock';mock.version.cuda='mock';mock.cuda.is_available.return_value=True;mock.cuda.device_count.return_value=1;mock.cuda.get_device_properties.return_value=SimpleNamespace(total_memory=80*2**30)
  with patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':'3'}):
   result=require_cuda(mock,visibility_snapshot());self.assertEqual(os.environ['CUDA_VISIBLE_DEVICES'],'3');self.assertEqual(result['selected_logical_device'],0)
 def test_child_configuration_independent(self):
  before=dict(os.environ);self.subprocess_check("from runtime.gpu_environment import configure_determinism;configure_determinism();assert os.environ['CUDA_VISIBLE_DEVICES']=='7'",'7');self.assertEqual(before,dict(os.environ))
if __name__=='__main__':unittest.main()
