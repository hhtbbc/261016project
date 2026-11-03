"""Exact saved-output onset and event-neighborhood descriptions; no RHS calls."""
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_orbit_12h_numerical_reference_v1 import saved,GROUPS,TIMES,O
from analyze_fourcastden_swarm_observation_v1 import table

def main():
    arr=saved();rows=[]
    for g in GROUPS:
        d=arr[g,'base']-arr[g,'tight'];norm=np.linalg.norm(d[:,:3],axis=1);cross=TIMES[norm>.02];nonzero=TIMES[norm>0]
        rows.append(dict(group=g,first_nonzero_saved_UTC_hour=1+float(nonzero[0])/3600 if len(nonzero) else None,first_exceeds_002m_UTC_hour=1+float(cross[0])/3600 if len(cross) else None,at_0659_m=float(norm[359]),at_0700_m=float(norm[360]),at_0701_m=float(norm[361]),increment_before_event_m=float(norm[360]-norm[359]),increment_after_event_m=float(norm[361]-norm[360]),max_1min_increment_m=float(np.diff(norm).max()),decreasing_saved_intervals=int(np.sum(np.diff(norm)<0)),interpretation='descriptive60s samples; not a statement about continuous substep error'))
    table(O/'error_onset_and_event.csv',rows)
if __name__=='__main__':main()
