"""External reference, bitwise compatibility, gradient and CPU audit; no propagation."""
import sys,json,time,hashlib,csv
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from orbit.gravity_truncation import ExtendedEarthGravity
from orbit.spherical_harmonics_gravity import SphericalHarmonicsGravity,GcrsSphericalHarmonicsForce
from orbit.frames import configure_time_data
from astropy.time import Time
from test_spherical_harmonics_gravity import external_reference
F=ROOT/'experiments/gravity_truncation_v1';out={'degrees':{},'passed':True,'threshold_relative':2e-12,'threshold_absolute_m_s2':2e-12,'source':json.loads((ROOT/'configs/egm2008_degree20_source.json').read_text())};rng=np.random.default_rng(777)
points=rng.normal(size=(100,3));points*=rng.uniform(6578136.3,12000000,(100,1))/np.linalg.norm(points,axis=1)[:,None];forces={}
for d in [8,12,20]:
 m=ExtendedEarthGravity(d);diff=[];relative=[];tick=time.perf_counter();forces[d]=[]
 for p in points:
  a=m.acceleration_itrs(p);b=external_reference(m,p);diff.append(np.linalg.norm(a-b));relative.append(np.linalg.norm(a-b)/np.linalg.norm(b));forces[d].append(a)
  np.testing.assert_allclose(a,b,rtol=2e-12,atol=2e-12)
 bench=[]
 for p in points:
  t=time.perf_counter();m.acceleration_itrs(p);bench.append(time.perf_counter()-t)
 p=np.array([4e6,-3e6,5e6]);a=m.acceleration_itrs(p);fd=[]
 for h in [10000.,1000.,100.]:
  g=np.array([-(m.potential_itrs(p+np.eye(3)[j]*h)-m.potential_itrs(p-np.eye(3)[j]*h))/(2*h) for j in range(3)]);fd.append(float(np.linalg.norm(a-g)/np.linalg.norm(a)))
 assert max(relative)<2e-12 and fd[-1]<2e-8
 out['degrees'][str(d)]={'coefficient_pairs':len(m.coefficients),'max_absolute_difference_m_s2':max(diff),'max_relative_difference':max(relative),'gradient_relative_errors_10km_1km_100m':fd,'mean_pure_field_ms':float(np.mean(bench)*1000),'P95_pure_field_ms':float(np.percentile(bench,95)*1000)}
configure_time_data();config=json.loads((ROOT/'experiments/spherical_harmonics_v1/configuration.json').read_text());old=GcrsSphericalHarmonicsForce(Time(config['t0_utc'],scale='utc'));new=GcrsSphericalHarmonicsForce(Time(config['t0_utc'],scale='utc'),ExtendedEarthGravity(8))
with np.load(ROOT/'data/processed/spherical_harmonics_v1/H1_states.npz') as z:states=z['states'];sec=z['seconds']
for t,y in zip(sec,states):np.testing.assert_array_equal(old(t,y[:3],y[3:]),new(t,y[:3],y[3:]))
out['8x8_full_GCRS_force_bitwise_match_all_361_H1_states']=True
out['same_point_acceleration_differences']={f'{a}_{b}':{'min_m_s2':float(np.linalg.norm(np.array(forces[a])-forces[b],axis=1).min()),'max_m_s2':float(np.linalg.norm(np.array(forces[a])-forces[b],axis=1).max())} for a,b in [(12,8),(20,12),(20,8)]}
meta=json.loads((ROOT/'configs/spherical_reference.json').read_text())
for p,h in meta['binary_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
out['reference_binary_sha_verified']=True;out['preregistered_endpoint_goal_m']=5.;out['whole_path_candidate_goal_m']=5.;out['numeric_state_max_m']=.5
with (F/'validation.json').open('x') as f:json.dump(out,f,indent=2)
print(json.dumps({k:v for k,v in out.items() if k!='source'},indent=2))
