"""Independent completed-data scientific contracts; no model or ODE launches."""
from pathlib import Path
import sys,json,csv,unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'src')]
from analyze_orbit_12h_abcd_dop853_closure_v1 import load,PAIRS,F,O,TIMES,OLD

class CompletedDataContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.states={(g,m):load(g,m) for g in ['A_NoDrag','B_Open','C_Updated','D_Reference'] for m in ['DOP30','DOP15']}
        cls.a=json.loads((F/'analysis.json').read_text());cls.e=json.loads((F/'effect_assessment.json').read_text())
    def test_common_initial_and_finite_721(self):
        y=np.load(OLD/'initial_GCRS_local.npy')
        for x in self.states.values():
            np.testing.assert_array_equal(x[0],y);self.assertEqual(x.shape,(721,6));self.assertTrue(np.isfinite(x).all())
    def test_event_exact_handoff_and_no_pre_event_update(self):
        for m in ['DOP30','DOP15']:
            np.testing.assert_array_equal(self.states['B_Open',m][:361],self.states['C_Updated',m][:361])
            with np.load(F/f'D_Reference_{m}_states_local.npz') as n:
                np.testing.assert_array_equal(n['left_end'],n['right_start']);np.testing.assert_array_equal(n['states'][360],n['left_end'])
    def test_six_vector_identities(self):
        for x,y in PAIRS:
            d=(self.states[x,'DOP30']-self.states[y,'DOP30'])-(self.states[x,'DOP15']-self.states[y,'DOP15'])
            alt=(self.states[x,'DOP30']-self.states[x,'DOP15'])-(self.states[y,'DOP30']-self.states[y,'DOP15'])
            np.testing.assert_array_equal(d,alt)
    def test_frozen_single_and_pair_thresholds(self):
        p=json.loads((F/'protocol.json').read_text());self.assertEqual(p['single_gate_m'],.02);self.assertEqual(p['paired_gate_fraction'],.01)
        for row in self.a['pairs']:
            self.assertEqual(row['limit_m'],.01*row['max_DOP15_response_m']);self.assertEqual(row['gate']=='PASS',row['max_effect_vector_sensitivity_m']<=row['limit_m'])
    def test_whole_window_and_no_removed_worse_samples(self):
        a=self.states['B_Open','DOP15'];b=self.states['C_Updated','DOP15'];d=self.states['D_Reference','DOP15'];eo=np.linalg.norm(a[:,:3]-d[:,:3],axis=1);eu=np.linalg.norm(b[:,:3]-d[:,:3],axis=1)
        self.assertAlmostEqual(np.sqrt(np.dot(eo,eo)/721),self.e['open']['RMS_m'],places=12);self.assertEqual(self.e['closer_samples']+self.e['farther_samples']+self.e['equal_samples'],360);self.assertEqual(self.e['farther_samples'],int((eu[361:]>eo[361:]).sum()))
    def test_saved_drag_obeys_frozen_aerodynamics(self):
        for m in ['DOP30','DOP15']:
            for r in csv.DictReader((O/f'D_Reference_{m}_samples.csv').read_text().splitlines()):
                expected=.5*float(r['rho_kg_m3'])*2.2/400*float(r['relative_speed_m_s'])**2
                self.assertLess(abs(float(r['drag_norm_m_s2'])/expected-1),1e-12)
    def test_unchanged_scientific_limits(self):
        self.assertFalse(self.a['science_training']);self.assertEqual(self.a['old_RK45_gate'],'FAIL_UNCHANGED');self.assertEqual(self.a['gates']['SCIENTIFIC_REAL_ORBIT_VALIDATION_READY'],'BLOCKED');self.assertEqual(self.a['formal_external_datum'],'EXTERNAL_DATUM_UNVERIFIED')
if __name__=='__main__':unittest.main(verbosity=2)
