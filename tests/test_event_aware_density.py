"""Event routing and independent analytic drag discontinuity checks, CPU only."""
from pathlib import Path
import sys, unittest
import numpy as np
from astropy.time import Time,TimeDelta
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from atmosphere.fourcastden_density import FourCastDENDensity
from atmosphere.event_aware_density import EventAwareDensity
from atmosphere.tiegcm_density_provider import DATUM
from orbit.event_segments import propagate_event_segments


def sample(after=False, bad=False):
    epochs=[f'2023-03-24T{h:02d}:00:00' for h in (range(7,10) if after else range(5,9))]
    # Deliberately huge corrected state: leakage into 06:30 is easy to detect.
    amp=np.arange(len(epochs))+(10 if after else 1)
    den=np.broadcast_to(amp[:,None,None,None]*1e-15,(len(epochs),3,2,4)).copy()
    height=np.broadcast_to(np.array([100,200,300])[None,:,None,None]*1000,den.shape).copy()
    mask=np.ones((len(epochs),2,4),bool)
    if bad:mask[0,1,1]=False
    return FourCastDENDensity(epochs,[-5,5],[-180,-90,0,90],den,height,
        source='SYNTHETIC',height_source='SYNTHETIC',valid_columns=mask)


class EventTests(unittest.TestCase):
    def setUp(self):self.p=EventAwareDensity(sample(),sample(True),'2023-03-24T07:00:00')
    def q(self,stamp,**kw):return self.p.query_native('2023-03-24T'+stamp,0,0,200000,datum=DATUM,**kw)
    def test_pre_event_times_no_leakage(self):
        for stamp,expected in [('06:00:00',2),('06:30:00',2.5),('06:59:59',3-1/3600)]:
            r=self.q(stamp);self.assertTrue(r.valid)
            self.assertAlmostEqual(r.rho_kg_m3/1e-12,expected,places=9)
            self.assertEqual(r.metadata['event_branch'],'left')
            self.assertLessEqual(Time(r.metadata['time_utc'][-1]),self.p.event)
    def test_exact_left_right_and_default(self):
        self.assertAlmostEqual(self.q('07:00:00',event_side='left').rho_kg_m3/1e-12,3)
        self.assertAlmostEqual(self.q('07:00:00',event_side='right').rho_kg_m3/1e-12,10)
        self.assertEqual(self.q('07:00:00').rho_kg_m3,self.q('07:00:00',event_side='right').rho_kg_m3)
    def test_post_event_times(self):
        for stamp,expected in [('07:00:01',10+1/3600),('07:30:00',10.5),('08:00:00',11)]:
            r=self.q(stamp);self.assertAlmostEqual(r.rho_kg_m3/1e-12,expected,places=9)
            self.assertGreaterEqual(Time(r.metadata['time_utc'][0]),self.p.event)
    def test_non_event_side_rejected(self):
        with self.assertRaises(ValueError):self.q('06:59:59',event_side='right')
    def test_periodic_longitude(self):
        a=self.p.query_native(self.p.event,0,179,200000,datum=DATUM)
        b=self.p.query_native(self.p.event,0,-181,200000,datum=DATUM)
        self.assertEqual(a.rho_kg_m3,b.rho_kg_m3)
    def test_height_outside(self):self.assertEqual(self.p.query_native(self.p.event,0,0,300001,datum=DATUM).reason,'VERTICAL_OUTSIDE')
    def test_missing_event_frame(self):
        with self.assertRaises(ValueError):EventAwareDensity(sample(),sample(True),'2023-03-24T07:30:00')
    def test_missing_prediction_branch(self):
        with self.assertRaises(ValueError):EventAwareDensity(sample(),sample(True),'2023-03-24T09:00:00')
    def test_invalid_right_zero_weight_corner(self):
        p=EventAwareDensity(sample(),sample(True,True),'2023-03-24T07:00:00')
        self.assertTrue(p.query_native(p.event,-5,-180,200000,datum=DATUM,event_side='left').valid)
        self.assertEqual(p.query_native(p.event,-5,-180,200000,datum=DATUM).reason,'INVALID_HEIGHT_RECONSTRUCTION_COLUMN')
    def test_external_blocked(self):
        with self.assertRaisesRegex(ValueError,'EXTERNAL_DATUM'):self.p.density_kg_m3(None)
    def test_grid_mismatch(self):
        p=sample(True);p.lat=np.array([-4,5])
        with self.assertRaises(ValueError):EventAwareDensity(sample(),p,self.p.event)
    def test_post_poison_cannot_affect_pre(self):
        other=sample(True);other=FourCastDENDensity(other.epochs,other.lat,other.lon,other.rho*7/1000,
            other.height,source='POISON',height_source='SYNTHETIC')
        x=EventAwareDensity(sample(),other,self.p.event)
        for t in ['06:00:00','06:30:00','06:59:59']:
            self.assertEqual(self.q(t).rho_kg_m3,x.query_native('2023-03-24T'+t,0,0,200000,datum=DATUM).rho_kg_m3)


def analytic_drag(times, k=(1e-7,4e-7)):
    # Synthetic quadratic drag, no gravitational acceleration. Units: k m^-1.
    out=[]
    for t in times:
        v=7500.;x=0.
        for dt,c in [(min(t,60),k[0]),(max(0,t-60),k[1])]:
            x+=np.log1p(c*v*dt)/c;v/=1+c*v*dt
        out.append([x,0,0,v,0,0])
    return np.asarray(out)


def run_drag(rtol, maxstep):
    calls=[[],[]];ks=(1e-7,4e-7)
    def factory(i):
        def rhs(t,y):
            calls[i].append(t)
            return np.r_[y[3:],-ks[i]*np.linalg.norm(y[3:])*y[3:]]
        return rhs
    times=np.arange(121.)
    result=propagate_event_segments(factory,[0,0,0],[7500,0,0],(0,120),times,[60],
        rtol=rtol,atol=(1e-8,)*3+(1e-11,)*3,max_step=maxstep)
    return result,calls


class IntegrationTests(unittest.TestCase):
    def test_actual_event_provider_bound_to_ODE_segments(self):
        event=EventAwareDensity(sample(),sample(True),'2023-03-24T07:00:00')
        origin=Time('2023-03-24T06:59:00');endpoints={}
        def factory(i):
            provider=event.before if i==0 else event.after
            def rhs(t,y):
                result=provider.query_native(origin+TimeDelta(t,format='sec'),0,0,200000,datum=DATUM)
                if not result.valid:raise ValueError(result.reason)
                if t==60:endpoints[i]=result.rho_kg_m3
                return np.r_[y[3:],-1e5*result.rho_kg_m3*np.linalg.norm(y[3:])*y[3:]]
            return rhs
        p=propagate_event_segments(factory,[0,0,0],[7500,0,0],(0,120),[0,60,120],[60],max_step=20)
        self.assertAlmostEqual(endpoints[0]/1e-12,3)
        self.assertAlmostEqual(endpoints[1]/1e-12,10)
        self.assertEqual(p.event_records[0]['position_jump_m'],0)
    def test_density_failure_aborts_without_fallback(self):
        def factory(i):
            def rhs(t,y):
                if i==1:raise ValueError('INVALID_HEIGHT_RECONSTRUCTION_COLUMN')
                return np.r_[y[3:],np.zeros(3)]
            return rhs
        with self.assertRaisesRegex(ValueError,'INVALID_HEIGHT'):
            propagate_event_segments(factory,[0]*3,[7500,0,0],(0,120),[0,60,120],[60])
    def test_analytic_discontinuous_drag(self):
        result,calls=run_drag(1e-10,10)
        error=np.abs(result.states-analytic_drag(result.times_s))
        self.assertLess(error[:,:3].max(),.001)
        self.assertLess(error[:,3:].max(),1e-5)
        e=result.event_records[0]
        self.assertEqual(e['position_jump_m'],0);self.assertEqual(e['velocity_jump_m_s'],0)
        self.assertAlmostEqual(e['acceleration_right'][0]/e['acceleration_left'][0],4)
        self.assertEqual(max(calls[0]),60);self.assertEqual(min(calls[1]),60)
        np.testing.assert_array_equal(result.segments[0].states[-1],result.segments[1].states[0])
    def test_convergence(self):
        a,_=run_drag(1e-8,20);b,_=run_drag(1e-12,5)
        ea=np.max(abs(a.states-analytic_drag(a.times_s)));eb=np.max(abs(b.states-analytic_drag(b.times_s)))
        self.assertLess(eb,ea);self.assertLess(eb,1e-6)
    def test_invalid_events(self):
        for events in ([0],[120],[70,60],[60,60],[np.nan]):
            with self.assertRaises(ValueError):propagate_event_segments(lambda i:lambda t,y:y,[0]*3,[1]*3,(0,120),[0,120],events)


if __name__=='__main__':unittest.main()
