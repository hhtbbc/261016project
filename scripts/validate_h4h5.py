"""All independent gates before any propagation; freezes reference checks."""
import sys,json,csv,hashlib,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from orbit.gravity_degree40 import Degree40EarthGravity
from orbit.gravity_truncation import ExtendedEarthGravity
from orbit.spherical_harmonics_gravity import GcrsSphericalHarmonicsForce
from orbit.third_body_gravity import ThirdBodyGravity
from orbit.frames import configure_time_data
from astropy.time import Time,TimeDelta
from test_spherical_harmonics_gravity import external_reference
F=ROOT/'experiments/gravity_third_body_v1';configure_time_data();c=json.loads((ROOT/'experiments/gravity_truncation_v1/configuration.json').read_text());epoch=Time(c['t0_utc'],scale='utc');m=Degree40EarthGravity();rng=np.random.default_rng(4040);absdiff=[];reldiff=[];bench=[]
for _ in range(100):
 p=rng.normal(size=3);p*=rng.uniform(6578136.3,12000000)/np.linalg.norm(p);tick=time.perf_counter();a=m.acceleration_itrs(p);bench.append(time.perf_counter()-tick);b=external_reference(m,p);np.testing.assert_allclose(a,b,rtol=2e-12,atol=2e-12);absdiff.append(np.linalg.norm(a-b));reldiff.append(np.linalg.norm(a-b)/np.linalg.norm(b))
p=np.array([4e6,-3e6,5e6]);a=m.acceleration_itrs(p);fd=[]
for h in [10000.,1000.,100.]:
 g=np.array([-(m.potential_itrs(p+np.eye(3)[j]*h)-m.potential_itrs(p-np.eye(3)[j]*h))/(2*h) for j in range(3)]);fd.append(float(np.linalg.norm(a-g)/np.linalg.norm(a)))
old=GcrsSphericalHarmonicsForce(epoch,ExtendedEarthGravity(20));new=GcrsSphericalHarmonicsForce(epoch,Degree40EarthGravity(20))
with np.load(ROOT/'data/processed/gravity_truncation_v1/H3_states.npz') as z:states=z['states'];seconds=z['seconds']
for t,y in zip(seconds,states):np.testing.assert_array_equal(old(t,y[:3],y[3:]),new(t,y[:3],y[3:]))
body=ThirdBodyGravity(epoch,21600);refs={};gates={'sun':20000.,'moon':40000.}
for b in ['sun','moon']:
 folder=ROOT/'data/raw/third_body_validation';manifest=json.loads((folder/f'{b}_manifest.json').read_text());raw=(folder/f'{b}.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==manifest['sha256'];txt=json.loads(raw)['result'];assert 'GEOMETRIC' in txt and 'ICRF' in txt and 'Earth (399)' in txt
 rows=list(csv.reader(txt.split('$$SOE')[1].split('$$EOE')[0].strip().splitlines()));checks=[]
 for row,t in zip(rows,[0.,10800.,21600.]):
  rref=np.asarray([float(x) for x in row[2:5]])*1000;rprod=body.positions(t)[b];error=float(np.linalg.norm(rref-rprod));assert error<gates[b]
  # Independent direct reference expression with Horizons position, at same historical H3 state.
  r=states[int(t/60),:3];mu=body.mu[b];refa=mu*((rref-r)/np.linalg.norm(rref-r)**3-rref/np.linalg.norm(rref)**3);prod=body.components(t,r)[b]
  checks.append({'seconds':t,'horizons_jd_tdb':row[0],'requested_vs_printed_epoch_s':float((Time(float(row[0]),format='jd',scale='tdb')-(epoch+TimeDelta(t,format='sec'))).sec),'Horizons_geocentric_ICRF_m':rref.tolist(),'ERFA_leading_GCRS_geometry_m':rprod.tolist(),'position_difference_m':error,'differential_accel_difference_m_s2':float(np.linalg.norm(prod-refa)),'differential_accel_relative_difference':float(np.linalg.norm(prod-refa)/np.linalg.norm(refa))})
 refs[b]={'source':'NASA Horizons DE441 geometric ICRF geocentric; position reference only','max_position_difference_m':max(x['position_difference_m'] for x in checks),'position_gate_m':gates[b],'checks':checks,'response_sha256':manifest['sha256'],'query':manifest['query']}
assert fd[-1]<2e-8 and max(reldiff)<2e-12
out={'passed':True,'gravity40':{'max_abs_difference_m_s2':max(absdiff),'max_relative_difference':max(reldiff),'gradient_errors_10km_1km_100m':fd,'mean_pure_field_ms':float(np.mean(bench)*1000),'P95_pure_field_ms':float(np.percentile(bench,95)*1000),'coefficient_count':len(m.coefficients),'20x20_full_GCRS_force_bitwise_same_all_361_H3_states':True},'third_body':{'model':body.metadata,'GM_m3_s2':body.mu,'independent_references':refs,'scope':'Newtonian mechanism/sensitivity, not precision celestial frame/GM time-scale closure','full_6h_convergence_status':'PENDING: only 600s short base/tight planned, H4/H5 full base each once'},'thresholds':{'gravity_reference_relative':2e-12,'gravity_reference_absolute_m_s2':2e-12,'short_state_base_tight_max_m':.02,'truncation_endpoint_candidate_m':5.}}
with (F/'validation.json').open('x') as f:json.dump(out,f,indent=2)
print(json.dumps(out,indent=2))
