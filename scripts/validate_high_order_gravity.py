"""Numerical values for independent synthetic validation; not a Swarm propagation."""
import sys,json,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from orbit.higher_order_gravity import *
from orbit.j2 import j2_acceleration,j2_potential
from orbit.two_body import central_gravity,make_state_derivative
from orbit.rk45_propagator import propagate
from test_higher_order_gravity import spherical_reference

def main():
 p=ROOT/'logs/high_order_gravity_independent_validation.json'
 if p.exists():raise FileExistsError(p)
 start=time.perf_counter();out={'labels':['SYNTHETIC_VALIDATION','NO_SWARM_PROPAGATION'],'parameters':json.loads((ROOT/'configs/higher_order_gravity.json').read_text()),'terms':{},'fixed_axis_conservation':{}}
 point=np.array([4e6,-2e6,5e6]);radius=6850000.
 for n,j,cb,fn in [(3,J3,CBAR30,j3_acceleration),(4,J4,CBAR40,j4_acceleration)]:
  analytic=fn(point);gradient=[]
  for h in [10000.,1000.,100.]:
   g=np.array([-(zonal_potential(point+np.eye(3)[i]*h,n,j)-zonal_potential(point-np.eye(3)[i]*h,n,j))/(2*h) for i in range(3)])
   gradient.append({'step_m':h,'relative_error':float(np.linalg.norm(g-analytic)/np.linalg.norm(analytic))})
  cs=np.array([-np.imag(zonal_potential(point+1e-10j*np.eye(3)[i],n,j))/1e-10 for i in range(3)])
  error_ref=[];rng=np.random.default_rng(20261020)
  for _ in range(100):
   r=rng.normal(size=3);r=r/np.linalg.norm(r)*rng.uniform(6.8e6,7e6);error_ref.append(float(np.linalg.norm(fn(r)-spherical_reference(r,n,cb))/np.linalg.norm(fn(r))))
  assert max(error_ref)<2e-12 and np.linalg.norm(cs-analytic)/np.linalg.norm(analytic)<2e-12
  assert gradient[1]['relative_error']<gradient[0]['relative_error']/50 and gradient[2]['relative_error']<gradient[1]['relative_error']/50 and gradient[-1]['relative_error']<2e-7
  out['terms'][str(n)]={'independent_spherical_max_relative_error':max(error_ref),'complex_gradient_relative_error':float(np.linalg.norm(cs-analytic)/np.linalg.norm(analytic)),'finite_difference':gradient}
 k=np.array([0.,0.,1.]);rhs=make_state_derivative([central_gravity,lambda t,r,v:j2_acceleration(r,k),HigherOrderZonalForce(lambda t:k,include_j3=True,include_j4=True)])
 states={}
 for label,rtol,atol,maxstep in [('base',1e-11,[1e-4]*3+[1e-7]*3,20),('tight',1e-12,[1e-5]*3+[1e-8]*3,10)]:
  z=propagate(rhs,[radius,0,0],[0,5400,5400],(0,6000),np.arange(0,6001,60.),rtol=rtol,atol=atol,max_step=maxstep);states[label]=z.states
  energy=np.sum(z.states[:,3:]**2,axis=1)/2-EARTH_MU/np.linalg.norm(z.states[:,:3],axis=1)
  energy+=np.array([j2_potential(r)+zonal_potential(r,3,J3)+zonal_potential(r,4,J4) for r in z.states[:,:3]])
  hz=np.cross(z.states[:,:3],z.states[:,3:])@k
  out['fixed_axis_conservation'][label]={'specific_energy_max_relative_drift':float(np.max(abs(energy/energy[0]-1))),'axial_angular_momentum_max_relative_drift':float(np.max(abs(hz/hz[0]-1))),'integration':z.statistics}
 for key in ['specific_energy_max_relative_drift','axial_angular_momentum_max_relative_drift']:
  assert out['fixed_axis_conservation']['tight'][key]<out['fixed_axis_conservation']['base'][key]<1e-8
 out['fixed_axis_state_difference_max_m']=float(np.linalg.norm(states['base'][:,:3]-states['tight'][:,:3],axis=1).max());assert out['fixed_axis_state_difference_max_m']<.05
 typical=[]
 for name,r in [('equator',[radius,0,0]),('north_pole',[0,0,radius]),('south_pole',[0,0,-radius]),('midlatitude',np.array([radius/np.sqrt(2),0,radius/np.sqrt(2)]))]:
  a2=j2_acceleration(r);a3=j3_acceleration(r);a4=j4_acceleration(r)
  typical.append({'location':name,'position_m':np.asarray(r).tolist(),'central_m_s2':float(np.linalg.norm(central_gravity(0,r,None))),'J2_m_s2':float(np.linalg.norm(a2)),'J3_m_s2':float(np.linalg.norm(a3)),'J4_m_s2':float(np.linalg.norm(a4)),'J3_vector':a3.tolist(),'J4_vector':a4.tolist()})
 out.update(typical=typical,passed=True,validation_wall_s=time.perf_counter()-start)
 p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
