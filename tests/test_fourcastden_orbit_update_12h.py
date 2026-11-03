"""Only new 12h stage-gate tests; no replay of prior event propagation tests."""
from pathlib import Path
import sys,json,tempfile,unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_fourcastden_orbit_update_12h_v1 import validate_base
class StageGateTests(unittest.TestCase):
    def setUp(self):
        parent=ROOT/'cache';parent.mkdir(exist_ok=True);self.tmp=tempfile.TemporaryDirectory(dir=parent,prefix='stage12h_');self.p=Path(self.tmp.name);self.groups=['A_NoDrag','B_Open','C_Updated','D_Reference'];self.initial=np.arange(6.)
        for g in self.groups:
            state=np.tile(self.initial,(721,1));np.savez(self.p/f'{g}_base_states_local.npz',states=state,seconds=np.arange(0,43201,60),left_end=self.initial,right_start=self.initial,left_times=[0,21600],right_times=[21600,43200])
            (self.p/f'{g}_base_runtime.json').write_text(json.dumps(dict(all_density_queries_valid=True,actual_rhs_time_domains=[[0.,21600.],[21600.,43200.]],event_records=[dict(position_jump_m=0,velocity_jump_m_s=0)])))
    def tearDown(self):self.tmp.cleanup()
    def gate(self):return validate_base(self.p,dict(groups=self.groups),self.initial)
    def alter(self,key,fn):
        p=self.p/'B_Open_base_states_local.npz'
        with np.load(p) as n:d={k:n[k] for k in n.files}
        d[key]=fn(d[key]);np.savez(p,**d)
    def test_valid_721_frames(self):self.assertEqual(self.gate()['status'],'PASS')
    def test_missing_record_blocks_tight(self):
        self.alter('states',lambda a:a[:-1]);self.assertRaises(AssertionError,self.gate)
    def test_nan_blocks_tight(self):
        def poison(a):a[5,0]=np.nan;return a
        self.alter('states',poison);self.assertRaises(AssertionError,self.gate)
    def test_event_reset_blocks_tight(self):
        self.alter('right_start',lambda a:a+1);self.assertRaises(AssertionError,self.gate)
    def test_failed_query_blocks_tight(self):
        p=self.p/'B_Open_base_runtime.json';m=json.loads(p.read_text());m['all_density_queries_valid']=False;p.write_text(json.dumps(m));self.assertRaises(AssertionError,self.gate)
    def test_time_gap_blocks_tight(self):
        self.alter('seconds',lambda a:a+1);self.assertRaises(AssertionError,self.gate)
if __name__=='__main__':unittest.main()
