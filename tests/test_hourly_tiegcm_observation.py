import unittest
import numpy as np
from atmosphere.tiegcm_density_provider import DATUM
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from evaluation.swarm_density_comparison import paired_valid_mask,compare_density,quality_mask
from astropy.time import Time,TimeDelta
class TestHourly(unittest.TestCase):
    def provider(self):
        p=object.__new__(HourlyTiegcmObservation);p.source='synthetic';p.closed=False;p.manifests={};p.epoch=Time('2021-03-24');p.seconds=np.array([0.,3600.]);p.lat=np.array([-5.,5.]);p.lon=np.arange(0,360,5.);p.records=[(p.epoch,None,0),(p.epoch+TimeDelta(3600,format="sec"),None,1)]
        from pathlib import Path
        p.records=[(t,Path('synthetic.nc'),i) for t,_,i in p.records]
        p.arrays=[(np.broadcast_to(np.array([100.,200.])[:,None,None],(2,2,72)),np.full((2,2,72),r)) for r in [1e-12,3e-12]];return p
    def test_hourly_midpoint(self):
        p=self.provider();r=p.query_native('2021-03-24T00:30',0,359,150,datum=DATUM);self.assertTrue(r.valid);self.assertAlmostEqual(r.rho_kg_m3/1e-12,2)
    def test_periodic(self):
        p=self.provider();a=p.query_native('2021-03-24',0,-1,150,datum=DATUM);b=p.query_native('2021-03-24',0,359,150,datum=DATUM);self.assertEqual(a.rho_kg_m3,b.rho_kg_m3)
    def test_no_extrapolation(self):
        p=self.provider();self.assertFalse(p.query_native('2021-03-24',0,0,201,datum=DATUM).valid)
    def test_formal_gate(self):
        self.assertEqual(self.provider().query_external(None).reason,'EXTERNAL_DATUM_UNVERIFIED')
    def test_all_eight(self):
        p=self.provider();p.arrays[1][1][0,0,0]=np.nan;self.assertFalse(p.query_native('2021-03-24',-5,0,150,datum=DATUM).valid)
    def test_common(self):
        np.testing.assert_array_equal(paired_valid_mask([1,1],[1,np.nan],[2,3]),[True,False])
    def test_metrics(self):
        m=compare_density(np.array([2.,4.]),np.array([1.,2.]));self.assertEqual(m['relative_RMS'],1);self.assertEqual(m['bias'],1.5)
    def test_quality(self):
        m,_=quality_mask([1,1,1],[0,1,9]);np.testing.assert_array_equal(m,[1,0,0])
if __name__=='__main__':unittest.main()
