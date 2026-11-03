"""Saved-vector event/period sensitivity; no force or density evaluation."""
from pathlib import Path
import sys,json,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_orbit_12h_bc_dop853_validation_v1 import F,O,TIMES,GROUPS
from analyze_fourcastden_swarm_observation_v1 import table
from prepare_fourcastden_swarm_observation_v1 import dump

def main():
    start=time.perf_counter();s={}
    for g in GROUPS:
        for m in ['DOP30','DOP15']:
            with np.load(F/f'{g}_{m}_states_local.npz') as n:s[g,m]=n['states']
    e30=s['C_Updated','DOP30']-s['B_Open','DOP30'];e15=s['C_Updated','DOP15']-s['B_Open','DOP15'];d=e30-e15;pn=np.linalg.norm(e15[:,:3],axis=1);dn=np.linalg.norm(d[:,:3],axis=1)
    time_rows=[]
    for i,t in enumerate(TIMES):time_rows.append(dict(seconds=int(t),UTC_hour=1+t/3600,effect_norm_m=float(pn[i]),paired_difference_m=float(dn[i]),pointwise_relative_difference=float(dn[i]/pn[i]) if pn[i]>0 else None,zero_effect_denominator_not_replaced=True))
    table(O/'per_time_effect_sensitivity.csv',time_rows);period=[]
    for g in GROUPS:
        d=s[g,'DOP30']-s[g,'DOP15'];pn2=np.linalg.norm(d[:,:3],axis=1)
        for lo,hi,label in [(0,21600,'before_including_event'),(21600,22200,'first10min'),(21600,43200,'post_including_event')]:
            ix=(TIMES>=lo)&(TIMES<=hi);period.append(dict(group=g,period=label,from_seconds=lo,to_seconds=hi,maximum_position_difference_m=float(pn2[ix].max()),RMS_position_difference_m=float(np.sqrt(np.mean(pn2[ix]**2))),maximum_velocity_difference_m_s=float(np.linalg.norm(d[ix,3:],axis=1).max())))
    table(O/'period_sensitivity.csv',period)
    event=[]
    for off in [-60,0,60,300,600,1800,3600,21600]:
        i=(21600+off)//60;event.append(dict(seconds_after07=off,effect_m=float(pn[i]),effect_velocity_m_s=float(np.linalg.norm(e15[i,3:])),paired_numerical_m=float(dn[i]),pointwise_relative=float(dn[i]/pn[i]) if pn[i]>0 else None))
    table(O/'event_response_checkpoints.csv',event)
    dump(F/'sensitivity_extension.json',dict(status='PASS',no_new_query=True,no_new_force=True,no_new_integration=True,wall_s=time.perf_counter()-start,zero_effect_no_percentage=True,first60s_post_event=event[2],last_checkpoint=event[-1]))
    print((F/'sensitivity_extension.json').read_text())
if __name__=='__main__':main()
