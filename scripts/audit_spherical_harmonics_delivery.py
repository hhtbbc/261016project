"""Independent lightweight delivery recomputation and protected-file checks."""
import json,sys,hashlib,csv
from pathlib import Path
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from orbit.frames import configure_time_data,transform_state
from evaluation.orbit_data import load_sp3_reference
from astropy.time import Time,TimeDelta
F=ROOT/'experiments/spherical_harmonics_v1';D=ROOT/'data/processed/spherical_harmonics_v1';a=json.loads((F/'analysis.json').read_text());c=json.loads((F/'configuration.json').read_text());configure_time_data()
with np.load(D/'H1_states.npz') as z:y=z['states'];seconds=z['seconds']
epoch=Time(c['t0_utc'],scale='utc')+TimeDelta(seconds,format='sec');ref=load_sp3_reference(sorted((ROOT/'data/raw/orbits/swarm_a/extracted').glob('*.sp3'))).take_exact(epoch);r,v=transform_state(ref.positions_m,ref.velocities_m_s,epoch,'ITRS','GCRS');delta=y[:,:3]-r;norm=np.sqrt(np.sum(delta*delta,axis=1));R=r/np.linalg.norm(r,axis=1)[:,None];C=np.cross(r,v);C/=np.linalg.norm(C,axis=1)[:,None];A=np.cross(C,R);rac=np.stack([np.sum(delta*b,axis=1) for b in [R,A,C]],axis=1)
np.testing.assert_allclose(a['residuals']['H1']['terminal_m'],norm[-1],rtol=0,atol=1e-9);np.testing.assert_allclose(a['residuals']['H1']['rmse_3d_m'],np.sqrt(np.mean(norm**2)),rtol=0,atol=1e-9);np.testing.assert_allclose(a['residuals']['H1']['rac_rmse_m'],np.sqrt(np.mean(rac**2,axis=0)),rtol=0,atol=1e-9)
for p,h in json.loads((F/'protected.json').read_text()).items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
for p,h in c['code_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
plot=ROOT/'results/figures/spherical_harmonics_v1_costs.png'
if not plot.exists():
 run=a['run'];fig,axes=plt.subplots(1,2,figsize=(10,4));names=list(run['runs']);axes[0].bar(names,[run['runs'][n]['elapsed_s'] for n in names]);axes[0].set(ylabel='Integration wall time (s)',title='Includes full frame transformations');axes[1].bar(names,[run['runs'][n]['nfev'] for n in names]);axes[1].set(ylabel='RHS evaluations',title='Same model, tighter tolerance');fig.suptitle('PROVISIONAL / HINDCAST / NO_DRAG',fontsize=9);fig.tight_layout();fig.savefig(plot,dpi=150);plt.close(fig)
files=list(F.glob('*.json'))+list(ROOT.glob('results/metrics/spherical_harmonics_v1_*.csv'))+list(ROOT.glob('results/figures/spherical_harmonics_v1_*.png'))
out={'passed':True,'independent_metric_recomputation':True,'protected_unchanged':True,'source_code_matches_preflight':True,'new_runs':['H1_short','H1','H1_tight'],'no_new_drag_runs':True,'artifacts':[{'file':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in files]}
with (F/'delivery_audit.json').open('x') as f:json.dump(out,f,indent=2)
print('Delivery passed',len(files),'lightweight artifacts')
