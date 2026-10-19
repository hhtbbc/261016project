"""Native continuation static gates, no model execution."""
from pathlib import Path
import importlib.util,unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('continuation',ROOT/'scripts/run_tiegcm2023_continuation.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class ContinuationTests(unittest.TestCase):
    def test_no_source_or_driver_override(self):
        for stage in ['B1','B2']:
            text=c.configuration(stage);c.validate_config(text,stage)
            self.assertNotIn('SOURCE',text);self.assertIn('MXHIST_PRIM = 3',text)
    def test_mutation_rejected(self):
        with self.assertRaises(ValueError):c.validate_config(c.configuration('B1').replace('\n/',"\n SOURCE='x'\n/"),'B1')
    def test_units_and_frozen_thresholds(self):
        self.assertEqual(c.unit_rule('cm/s'),(.01,1e-8,'m/s'))
        self.assertEqual(c.unit_rule('cm-3'),(1e6,1e-6,'m-3'))
        self.assertEqual(c.unit_rule('g/cm3'),(1000.,1e-25,'kg/m3'))
        with self.assertRaises(KeyError):c.unit_rule('unknown')
    def test_reference_checkpoint_not_future_seed(self):
        good=c.inspect_seed(c.REF/'primary_002.nc',[77,23,50]);self.assertTrue(good['structure_complete'])
        with self.assertRaises(ValueError):c.inspect_seed(c.REF/'primary_003.nc',[77,23,50])
    def test_branch_duration(self):
        for spec in c.SPECS.values():self.assertEqual(c.c.seconds(spec['stop'])-c.c.seconds(spec['start']),600)
    def test_B2_blocked_when_B1_not_passed(self):
        for check in [{},{'all_gates_pass':False}]:
            with self.assertRaises(ValueError):c.require_B1_pass(check)
        c.require_B1_pass({'all_gates_pass':True})
if __name__=='__main__':unittest.main()
