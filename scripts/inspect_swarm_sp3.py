"""Audit downloaded real Swarm SP3 data; create an Earth-fixed overview only."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from evaluation.sp3_reader import read_sp3
import matplotlib.pyplot as plt
rows=[];orbits=[]
for p in sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3')):
    o=read_sp3(p);orbits.append(o)
    radius=np.linalg.norm(o.positions_m,axis=1);speed=np.linalg.norm(o.velocities_m_s,axis=1)
    fd=(o.positions_m[2:]-o.positions_m[:-2])/(2*o.interval_s)
    residual=np.linalg.norm(fd-o.velocities_m_s[1:-1],axis=1)
    assert 6e6<radius.min()<radius.max()<8e6
    assert 6000<speed.min()<speed.max()<9000
    assert residual.max()<1 # finite-difference truncation at 10 s, not precise velocity validation
    rows.append({'file':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'format':o.version,'time_system':o.time_system,'frame':o.frame,'satellite_id':o.satellite_id,'epochs':len(o.epochs),'first_epoch_native':o.epochs[0].isoformat(),'last_epoch_native':o.epochs[-1].isoformat(),'interval_s':o.interval_s,'radius_m_min':float(radius.min()),'radius_m_max':float(radius.max()),'ecef_speed_m_s_min':float(speed.min()),'ecef_speed_m_s_max':float(speed.max()),'pv_central_difference_max_m_s':float(residual.max()),'maneuver_flag_available':any(x['maneuver'] is not None for x in o.orbit_flags)})
assert len(orbits)==3
for a,b in zip(orbits,orbits[1:]):assert (b.epochs[0]-a.epochs[-1]).total_seconds()==10
fig,axes=plt.subplots(2,1,figsize=(10,6),constrained_layout=True)
for o in orbits:
    t=np.array([(x-orbits[0].epochs[0]).total_seconds()/3600 for x in o.epochs])
    axes[0].plot(t,np.linalg.norm(o.positions_m,axis=1)/1000,lw=.6)
    pick=slice(None,None,30);axes[1].plot(o.positions_m[pick,0]/1000,o.positions_m[pick,1]/1000,lw=.5)
axes[0].set(xlabel='Hours since 2023-03-21 00:00:00 GPS',ylabel='Geocentric radius (km)',title='Real Swarm-A precise orbit, IGS20, SP3-d (overview)')
axes[1].set(xlabel='Earth-fixed X (km)',ylabel='Earth-fixed Y (km)');axes[1].set_aspect('equal')
fig.savefig(ROOT/'results/figures/20261019_swarm_a_sp3_overview.png',dpi=150);plt.close(fig)
out={'files':rows,'contiguous_72h_native_grid':True,'epochs_total':sum(len(o.epochs) for o in orbits),'time_scale_conversion_performed':False,'frame_transformation_performed':False,'orbit_prediction_performed':False,'note':'GPS labels retained; radius is not ellipsoidal altitude; flag omission cannot establish no maneuvers.'}
(ROOT/'logs/swarm_sp3_inspection.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
