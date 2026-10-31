from pathlib import Path
import sys,unittest
import numpy as np
from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from atmosphere.provisional_event_bridge import ProvisionalEventBridge,LABEL
from atmosphere.density_interface import DensityQuery
from atmosphere.fourcastden_density import FourCastDENDensity


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.p=FourCastDENDensity(['2023-01-04T06:00:00','2023-01-04T07:00:00'],[-5,5],[-180,-90,0,90],
            np.full((2,3,2,4),1e-15),np.broadcast_to(np.array([100,450,600])[None,:,None,None]*1000,(2,3,2,4)),source='SYNTHETIC',height_source='SYNTHETIC')
        r=EarthLocation.from_geodetic(0*u.deg,0*u.deg,450000*u.m).geocentric
        self.q=DensityQuery.from_itrs(Time('2023-01-04T06:30:00'),np.array([x.to_value(u.m) for x in r]));self.logs=[]
    def test_explicit_flag_required(self):
        for flag in ('',None,'A_WGS84'):
            with self.assertRaises(ValueError):ProvisionalEventBridge(self.p,authorization_label=flag,branch_label='left',records=self.logs)
    def test_units_and_metadata(self):
        b=ProvisionalEventBridge(self.p,authorization_label=LABEL,branch_label='left',records=self.logs)
        self.assertAlmostEqual(b.density_kg_m3(self.q)/1e-12,1);self.assertEqual(self.logs[0]['branch'],'left');self.assertTrue(self.logs[0]['valid'])
    def test_no_formal_provider_release(self):
        with self.assertRaisesRegex(ValueError,'EXTERNAL_DATUM_UNVERIFIED'):self.p.density_kg_m3(self.q)
    def test_invalid_height_aborts_and_preserves_rejection(self):
        b=ProvisionalEventBridge(self.p,authorization_label=LABEL,branch_label='left',records=self.logs)
        q=DensityQuery(self.q.utc,self.q.position_itrs_m,0,0,700000)
        with self.assertRaisesRegex(ValueError,'VERTICAL_OUTSIDE'):b.density_kg_m3(q)
        self.assertFalse(self.logs[0]['valid'])
    def test_bound_left_branch_never_uses_right_epoch(self):
        b=ProvisionalEventBridge(self.p,authorization_label=LABEL,branch_label='left',records=self.logs)
        q=DensityQuery(Time('2023-01-04T07:00:01'),self.q.position_itrs_m,0,0,450000)
        with self.assertRaisesRegex(ValueError,'TIME_OUTSIDE'):b.density_kg_m3(q)


if __name__=='__main__':unittest.main()
