"""SYNTHETIC demonstration only, never a real Swarm drag experiment."""
from pathlib import Path
import sys,json,argparse,csv
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import simpson
from astropy.time import Time,TimeDelta
from orbit.two_body import EARTH_MU,invariants,central_gravity,make_state_derivative
from orbit.rk45_propagator import propagate
from orbit.drag import DragForce,DragProperties
from atmosphere.density_interface import ConstantDensityDemo

class UniformRotationDemo:
    """SYNTHETIC constant omega frame, distinct from real EOP-based GCRS/ITRS."""
    def __init__(self):self.epoch=Time('2023-03-21T00:00:02',scale='utc');self.omega=np.array([0,0,7.292115e-5])
    def state_to_itrs(self,t,r,v):
        angle=self.omega[2]*t;c=np.cos(angle);s=np.sin(angle)
        Q=np.array([[c,s,0],[-s,c,0],[0,0,1.]])
        return self.epoch+TimeDelta(t,format='sec'),Q@r,Q@(v-np.cross(self.omega,r)),Q

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-tag',default='drag_synthetic_v1');tag=parser.parse_args().run_tag
    if not tag or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in tag):raise ValueError('Invalid tag')
    for folder in ['experiments','results/figures','results/metrics']:
        assert (ROOT/folder).resolve().is_relative_to(ROOT)
    out=ROOT/'experiments'/tag;out.mkdir(exist_ok=False)
    radius=6778137.;speed=np.sqrt(EARTH_MU/radius);period=2*np.pi*np.sqrt(radius**3/EARTH_MU)
    times=np.linspace(0,3*period,1501);r0=[radius,0,0];v0=[0,speed,0]
    props=DragProperties(100.,1.,2.2,'SYNTHETIC demonstration values, not Swarm-A')
    frame=UniformRotationDemo();force=DragForce(frame,ConstantDensityDemo(1e-12),props)
    run=propagate(make_state_derivative([central_gravity,force]),r0,v0,(0,times[-1]),times,rtol=1e-11,atol=[1e-4]*3+[1e-7]*3,max_step=20.)
    control=propagate(make_state_derivative([central_gravity]),r0,v0,(0,times[-1]),times,rtol=1e-11,atol=[1e-4]*3+[1e-7]*3,max_step=20.)
    tight=propagate(make_state_derivative([central_gravity,force]),r0,v0,(0,times[-1]),times,rtol=1e-12,atol=[1e-5]*3+[1e-8]*3,max_step=10.)
    energy,_=invariants(run.states);E0,_=invariants(control.states)
    accelerations=np.array([force(t,y[:3],y[3:]) for t,y in zip(times,run.states)])
    power=np.sum(run.states[:,3:]*accelerations,axis=1)
    work=float(simpson(power,x=times));delta=float(energy[-1]-energy[0])
    # Inertial energy need not decrease for arbitrary winds/rotation. Here
    # the synthetic prograde satellite outruns co-rotation, so v.a < 0.
    if not np.all(power<0) or delta>=0 or abs(delta-work)/abs(work)>1e-4:raise RuntimeError('Energy-work verification failed')
    summary={'status':'passed','parameters':'SYNTHETIC, not Swarm-A','mass_kg':100.,'area_m2':1.,'cd':2.2,'rho_kg_m3':1e-12,'rotation_rate_rad_s':float(frame.omega[2]),'duration_s':float(times[-1]),'initial_relative_speed_m_s':float(speed-frame.omega[2]*radius),'initial_drag_norm_m_s2':float(np.linalg.norm(accelerations[0])),'specific_energy_change_j_kg':delta,'integrated_drag_work_j_kg':work,'relative_energy_work_mismatch':float(abs(delta-work)/abs(work)),'control_specific_energy_change_j_kg':float(E0[-1]-E0[0]),'all_samples_inertial_drag_power_negative':bool(np.all(power<0)),'max_baseline_tight_position_difference_m':float(np.linalg.norm(run.states[:,:3]-tight.states[:,:3],axis=1).max()),'integration':run.statistics}
    (out/'summary.json').write_text(json.dumps(summary,indent=2));np.savez_compressed(out/'states.npz',elapsed_s=times,states=run.states,specific_energy_j_kg=energy,drag_acceleration_m_s2=accelerations,drag_power_w_kg=power)
    with (ROOT/f'results/metrics/{tag}_energy.csv').open('x',newline='') as f:
        w=csv.writer(f);w.writerow(['elapsed_s','specific_energy_change_j_kg','control_energy_change_j_kg','drag_power_w_kg']);w.writerows(zip(times,energy-energy[0],E0-E0[0],power))
    fig,axes=plt.subplots(2,1,sharex=True)
    axes[0].plot(times/3600,energy-energy[0],label='Central + synthetic co-rotating drag');axes[0].plot(times/3600,E0-E0[0],label='Central only');axes[0].set_ylabel('Specific energy change (J/kg)')
    axes[1].plot(times/3600,power,label='v dot a_drag');axes[1].set_ylabel('Specific drag power (W/kg)');axes[1].set_xlabel('Elapsed time (h)')
    for ax in axes:ax.legend(fontsize=8);ax.grid()
    fig.suptitle('SYNTHETIC demonstration; not Swarm-A parameters');fig.tight_layout();fig.savefig(ROOT/f'results/figures/{tag}_energy.png',dpi=160);plt.close(fig)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
