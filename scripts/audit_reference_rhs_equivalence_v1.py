"""Eight direct H6 calls check old composition and new NoDrag RHS bitwise."""
from pathlib import Path
import sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from run_orbit_12h_numerical_reference_v1 import F,saved,TIMES
from prepare_fourcastden_swarm_observation_v1 import dump
from orbit.frames import configure_time_data
from orbit.common_force_model import CommonForceModel
from orbit.two_body import make_state_derivative
from astropy.time import Time

def main():
    start=time.perf_counter();configure_time_data();force=CommonForceModel(Time('2023-01-04T01:00:00'),43200);old_rhs=make_state_derivative([force]);s=saved()['A_NoDrag','tight'];records=[]
    for i in [0,180,360,720]:
        y=s[i];t=float(TIMES[i]);new=np.r_[y[3:],force(t,y[:3],y[3:])];old=old_rhs(t,y);np.testing.assert_array_equal(new,old);records.append(dict(seconds=t,bitwise_identical=True,max_abs_difference=float(abs(new-old).max())))
    dump(F/'RHS_equivalence.json',dict(status='PASS',records=records,H6_calls=8,new_integrations=0,wall_s=time.perf_counter()-start,old_path='make_state_derivative([CommonForceModel])',new_path='concatenate(v,CommonForceModel(t,r,v))'))
    print((F/'RHS_equivalence.json').read_text())
if __name__=='__main__':main()
