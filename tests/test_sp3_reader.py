import sys,unittest,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from evaluation.sp3_reader import read_sp3
class SP3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path=sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))[0]
        cls.text=cls.path.read_text()
    def modified(self,text):
        with tempfile.TemporaryDirectory(dir=ROOT/'.tmp') as folder:
            p=Path(folder)/'sample.sp3';p.write_text(text);return read_sp3(p)
    def test_real_header_and_unit_conversion(self):
        o=read_sp3(self.path)
        self.assertEqual((o.version,o.time_system,o.frame,o.satellite_id,o.interval_s),('d','GPS','IGS20','L47',10.0))
        self.assertEqual(o.positions_m.shape,(8640,3));self.assertEqual(o.velocities_m_s.shape,(8640,3))
        self.assertAlmostEqual(o.positions_m[0,0],633643.6226,places=4)
        self.assertAlmostEqual(o.velocities_m_s[0,0],-4620.89630809,places=7)
    def test_unknown_time_system_rejected(self):
        with self.assertRaises(ValueError):self.modified(self.text.replace('%c M  cc GPS','%c M  cc XXX',1))
    def test_missing_position_rejected(self):
        line=next(x for x in self.text.splitlines() if x.startswith('PL47'))
        new='PL47'+''.join(f'{0.:14.7f}' for _ in range(3))+line[46:]
        with self.assertRaises(ValueError):self.modified(self.text.replace(line,new,1))
    def test_missing_velocity_rejected(self):
        line=next(x for x in self.text.splitlines() if x.startswith('VL47'))
        with self.assertRaises(ValueError):self.modified(self.text.replace(line+'\n','',1))
    def test_duplicate_epoch_rejected(self):
        stars=[x for x in self.text.splitlines() if x.startswith('*')]
        with self.assertRaises(ValueError):self.modified(self.text.replace(stars[1],stars[0],1))
if __name__=='__main__':unittest.main()
