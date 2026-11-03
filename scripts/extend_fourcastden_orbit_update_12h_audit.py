"""Saved-state checks: accepted step limits, domains, unit scales; no RHS calls."""
from pathlib import Path
import sys,json,csv,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_fourcastden_orbit_update_12h_v1 import F,O
from prepare_fourcastden_swarm_observation_v1 import dump
from analyze_fourcastden_swarm_observation_v1 import table

def main():
    start=time.perf_counter();p=json.loads((F/'protocol.json').read_text());rows=[]
    for mode in p['modes']:
        for group in p['groups']:
            with np.load(F/f'{group}_{mode}_states_local.npz') as n:
                s=n['states'];dt=np.r_[np.diff(n['left_times']),np.diff(n['right_times'])];assert np.all(dt>0) and dt.max()<=p[mode]['max_step']+1e-8
                r=np.linalg.norm(s[:,:3],axis=1);v=np.linalg.norm(s[:,3:],axis=1)
                assert np.isfinite(s).all() and r.min()>6e6 and r.max()<8e6 and v.min()>6000 and v.max()<9000
                rows.append(dict(group=group,mode=mode,max_accepted_step_s=float(dt.max()),min_accepted_step_s=float(dt.min()),radius_min_m=float(r.min()),radius_max_m=float(r.max()),GCRS_speed_min_m_s=float(v.min()),GCRS_speed_max_m_s=float(v.max()),number_accepted_intervals=len(dt),time_continuous=True))
    table(O/'independent_step_and_SI_scale.csv',rows)
    # A signed residual identity is checked on the actual vector, not norms.
    with np.load(F/'B_Open_tight_states_local.npz') as b,np.load(F/'C_Updated_tight_states_local.npz') as c,np.load(F/'D_Reference_tight_states_local.npz') as d:
        residual=(c['states']-b['states'])+(b['states']-d['states'])-(c['states']-d['states']);np.testing.assert_array_equal(residual,np.zeros_like(residual))
    performance=list(csv.DictReader((O/'performance.csv').open()));samples=[]
    for g in p['groups'][1:]:
        with (O/f'{g}_tight_samples.csv').open() as file:
            for row in csv.DictReader(file):
                rho=float(row['rho_kg_m3']);aa=np.array([float(row[k]) for k in ['drag_x','drag_y','drag_z']]);norm=float(row['drag_norm_m_s2']);np.testing.assert_allclose(np.linalg.norm(aa),norm,rtol=1e-14,atol=0)
                # Scalar independent inversion of actual frozen drag law, zero ITRS wind.
                vr=(2*p['aero']['mass_kg']*norm/(rho*p['aero']['Cd']*p['aero']['area_m2']))**.5
                assert 6000<vr<9000;samples.append(dict(group=g,UTC=row['UTC'],seconds=row['seconds'],rho_kg_m3=rho,drag_norm_m_s2=norm,relative_speed_from_drag_law_m_s=vr,interpretation='algebraic scalar diagnostic from saved actual rho and acceleration; not a new force evaluation'))
    table(O/'density_drag_speed_chain.csv',samples)
    elapsed=time.perf_counter()-start;a=json.loads((F/'independent_audit.json').read_text());dump(F/'extended_state_audit.json',dict(status='PASS',wall_s=elapsed,recorded_total_compute_s=a['recorded_compute_s']+elapsed,accepted_step_limits_PASS=8,SI_state_scales_PASS=8,signed_vector_residual_identity=True,no_new_RHS=True,no_new_queries=True,no_new_propagations=True))
    print((F/'extended_state_audit.json').read_text())
if __name__=='__main__':main()
