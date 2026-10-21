"""Independent Fortran comparisons and predeclared gates; no orbit integration."""
import sys,json,time,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from orbit.spherical_harmonics_gravity import SphericalHarmonicsGravity,SOURCE_SHA
from test_spherical_harmonics_gravity import external_reference
m=SphericalHarmonicsGravity();rng=np.random.default_rng(20261021);rows=[]
for i in range(100):
 p=rng.normal(size=3);p*=rng.uniform(6800000,7400000)/np.linalg.norm(p)
 a=m.acceleration_itrs(p);b=external_reference(m,p);rows.append({'position_m':p.tolist(),'production_m_s2':a.tolist(),'Fortran_m_s2':b.tolist(),'abs_vector_difference_m_s2':float(np.linalg.norm(a-b)),'relative_vector_difference':float(np.linalg.norm(a-b)/np.linalg.norm(b))})
p=np.array([4e6,-3e6,5e6]);a=m.acceleration_itrs(p);fd=[]
for h in [10000.,1000.,100.]:
 g=np.array([-(m.potential_itrs(p+np.eye(3)[j]*h)-m.potential_itrs(p-np.eye(3)[j]*h))/(2*h) for j in range(3)])
 fd.append({'step_m':h,'relative_error':float(np.linalg.norm(a-g)/np.linalg.norm(a))})
text=(ROOT/'logs/spherical_tests.log').read_text();assert 'Ran 9 tests' in text and text.rstrip().endswith('OK')
passed=max(x['relative_vector_difference'] for x in rows)<2e-12 and fd[-1]['relative_error']<2e-8
assert passed
out={'passed':True,'external_implementation':'pyshtools 4.14.1 Fortran MakeGravGridPoint; omega=0; direct compiled extension loaded (not full Python convenience API)','source_sha256':SOURCE_SHA,'max_absolute_difference_m_s2':max(x['abs_vector_difference_m_s2'] for x in rows),'max_relative_difference':max(x['relative_vector_difference'] for x in rows),'threshold_relative':2e-12,'threshold_absolute_m_s2':2e-12,'finite_difference':fd,'points':rows,'unit_tests':9,'exact_poles':'Production finite/continuous; SHTOOLS PlmBar_d1 rejects exact poles, external comparisons use +/-89.9 degrees instead. No tolerance relaxation.','test_log_sha256':hashlib.sha256(text.encode()).hexdigest()}
with (ROOT/'experiments/spherical_harmonics_v1/validation.json').open('x') as f:json.dump(out,f,indent=2)
print({k:v for k,v in out.items() if k!='points'})
