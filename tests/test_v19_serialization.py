import unittest,sys,json
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'scripts'),str(R/'src')]
from continue_density_verification_v19 import json_native,continuation_ready
F=R/'experiments/tiegcm_2022_mar25_independent_verification_v19/tests_local'
class Serialization(unittest.TestCase):
 def test_numpy_scalar_roundtrip(self):
  v=dict(flag=np.bool_(True),value=np.float64(5.453772204284436e-16),N=np.int64(30));out=json.loads(json.dumps(json_native(v),allow_nan=False));self.assertIs(out['flag'],True);self.assertEqual(out['value'],float(v['value']));self.assertEqual(out['N'],30)
 def test_nan_still_rejected(self):
  with self.assertRaises(ValueError):json.dumps(json_native(dict(x=np.float64(np.nan))),allow_nan=False)
 def test_resume_rejects_existing_completion(self):
  p=F/'completed_checkpoint';p.mkdir();(p/'result_closed.json').write_text('{}')
  with self.assertRaises(ValueError):continuation_ready(p)
if __name__=='__main__':unittest.main()
