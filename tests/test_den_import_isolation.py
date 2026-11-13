"""Regression for the observed pre-forward GPU visibility failure; no CUDA calls."""
import os, subprocess, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ImportIsolation(unittest.TestCase):
 def test_baseline_import_preserves_device_selection(self):
  code="import os,sys;sys.path[:0]=['scripts','src'];os.environ['CUDA_VISIBLE_DEVICES']='0';import persistence_den_engineering_v3;assert os.environ['CUDA_VISIBLE_DEVICES']=='0'"
  subprocess.run([sys.executable,'-c',code],cwd=ROOT,check=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES=''))
