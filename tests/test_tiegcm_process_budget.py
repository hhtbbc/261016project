"""CPU arithmetic and fail-closed tests; no physical integration."""
import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from atmosphere.tiegcm_process_budget import require_ready,check_closure,n2_contribution,TERMS
class BudgetTests(unittest.TestCase):
 def test_complete_primary_not_enough(self):
  with self.assertRaisesRegex(ValueError,'runtime_restore_verified'):
   require_ready(structure_complete=True,runtime_restore_verified=False,process_capture_verified=False,closure_protocol_qualified=False)
 def test_missing_is_not_zero(self):
  x=check_closure(np.ones(2),{});self.assertIsNone(x['residual']);self.assertFalse(x['passed'])
 def test_algebraic_closure(self):
  a={k:np.zeros(2) for k in TERMS};a['horizontal_advection']=np.array([.1,-.2]);self.assertTrue(check_closure(a['horizontal_advection'],a)['passed'])
 def test_omitted_finite_change_fails(self):
  a={k:np.zeros(2) for k in TERMS};self.assertFalse(check_closure(np.ones(2)*1e-4,a)['passed'])
 def test_nonfinite_rejected(self):
  a={k:np.zeros(2) for k in TERMS};a['boundary'][0]=np.nan
  with self.assertRaises(ValueError):check_closure(np.zeros(2),a)
 def test_n2_derived_not_independent(self):
  np.testing.assert_allclose(n2_contribution([.1],[.2],[-.01]),[-.29])
 def test_two_time_level_memory_bridge(self):
  old=.2;current=.21;dt=60;tendency=1e-5;new=old+2*dt*tendency
  self.assertAlmostEqual(new-current,2*dt*tendency+(old-current));self.assertNotAlmostEqual(new-current,dt*tendency)
if __name__=='__main__':unittest.main()
