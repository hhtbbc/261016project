"""Bounded H4/H5 tight and H6 validation, with no retry/old-data mutation."""
import sys,json,time,hashlib,resource,shutil
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from astropy.time import Time
from orbit.frames import configure_time_data
from orbit.common_force_model import CommonForceModel
from orbit.rk45_propagator import propagate
from orbit.two_body import make_state_derivative
F=ROOT/'experiments/common_force_validation_v1';D=ROOT/'data/processed/common_force_validation_v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,j):
 with p.open('x') as f:json.dump(j,f,indent=2,allow_nan=False)
def load(p):
 with np.load(p) as z:return z['states'].copy()
def main():
 F.resolve().relative_to(ROOT);D.resolve().relative_to(ROOT);F.mkdir(exist_ok=False);D.mkdir(exist_ok=False)
 c=json.loads((ROOT/'experiments/gravity_third_body_v1/configuration.json').read_text())
 for p,h in c['code_sha256'].items():assert sha(ROOT/p)==h,p
 protected=json.loads((ROOT/'experiments/gravity_third_body_v1/protected.json').read_text())
 for folder in ['experiments/gravity_third_body_v1','data/processed/gravity_third_body_v1']:
  for p in (ROOT/folder).glob('*'):
   if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
 for p,h in protected.items():assert sha(ROOT/p)==h,p
 configure_time_data();epoch=Time(c['t0_utc'],scale='utc');y=np.array(c['initial_state']);assert hashlib.sha256(y.astype('<f8').tobytes()).hexdigest()==c['initial_sha256']
 assert 'Ran 181 tests' in (ROOT/'logs/common_force_tests_pass.log').read_text() and (ROOT/'logs/common_force_tests_pass.log').read_text().rstrip().endswith('OK')
 assert shutil.disk_usage(ROOT).free>20*2**30
 assert sha(ROOT/'data/raw/gravity_sources/EGM2008_DEG40_PREFIX.gfc')==c['source40']['sha256']
 dump(F/'protected.json',protected);c.update(single_gate_m=.5,paired_gate_m=.1,short_gate_m=.02,labels='PROVISIONAL / HINDCAST / FORCE_MODEL_INCOMPLETE',new_code_sha256={p:sha(ROOT/p) for p in ['src/orbit/common_force_model.py','scripts/run_common_force_validation.py','docs/H6_VALIDATION_DESIGN.md']});dump(F/'configuration.json',c)
 dump(F/'preflight.json',dict(passed=True,estimated_with_25percent_margin_s=1515,wall_limit_s=1800,free_disk_GiB=shutil.disk_usage(ROOT).free/2**30,initial_sha256=c['initial_sha256'],historical_files=len(protected)))
 historical={'H3':ROOT/'data/processed/gravity_truncation_v1','H4':ROOT/'data/processed/gravity_third_body_v1','H5':ROOT/'data/processed/gravity_third_body_v1'}
 states={n:load(p/(n+'_states.npz')) for n,p in historical.items()};states['H3_tight']=load(historical['H3']/'H3_tight_states.npz')
 for a in states.values():np.testing.assert_array_equal(a[0],y)
 start=time.perf_counter();out={'runs':{},'gates':{},'labels':c['labels']}
 def guard():
  if time.perf_counter()-start>1800 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>2*1024**2 or shutil.disk_usage(ROOT).free<20*2**30:raise RuntimeError('Resource limit')
 def run(name,dur,degree=40,third=True,tight=False):
  guard();dump(F/(name+'_launch_once.json'),dict(utc=Time.now().utc.isot,duration_s=dur,tight=tight))
  model=CommonForceModel(epoch,21600,degree=degree,third_bodies=third);rhs=make_state_derivative([model])
  def guarded(t,state):guard();return rhs(t,state)
  print('START',name,flush=True);z=propagate(guarded,y[:3],y[3:],(0,dur),np.arange(0,dur+1,60),**c['tight' if tight else 'base']);np.testing.assert_array_equal(z.states[0],y);assert np.isfinite(z.states).all()
  states[name]=z.states;out['runs'][name]=z.statistics;dump(F/(name+'.json'),z.statistics);np.savez_compressed(D/(name+'_states.npz'),states=z.states,seconds=z.times_s,internal_times=z.internal_times_s);print('END',name,z.statistics,flush=True)
 def gate(name,a,b,limit):
  d=a-b;n=np.linalg.norm(d[:,:3],axis=1);s=dict(max_position_m=float(n.max()),rms_position_m=float(np.sqrt(np.mean(n*n))),max_velocity_m_s=float(np.linalg.norm(d[:,3:],axis=1).max()),threshold_m=limit,passed=bool(n.max()<limit));out['gates'][name]=s;dump(F/(name+'_gate.json'),s)
  if not s['passed']:raise RuntimeError(name+' convergence gate failed')
 try:
  for n,degree,third in [('H4',40,False),('H5',20,True)]:
   run(n+'_tight',21600,degree,third,True);gate(n,states[n],states[n+'_tight'],.5);gate(n+'_H3_pair',states[n]-states['H3'],states[n+'_tight']-states['H3_tight'],.1)
  run('H6_short',600);run('H6_short_tight',600,tight=True);gate('H6_short',states['H6_short'],states['H6_short_tight'],.02)
  estimate=sum(out['runs'][n]['elapsed_s']/out['runs'][n]['nfev']*calls for n,calls in [('H6_short',4346),('H6_short_tight',8666)])*1.25;remaining=1800-(time.perf_counter()-start);dump(F/'runtime_budget.json',dict(predicted_remaining_s=estimate,remaining_s=remaining,passed=estimate<remaining))
  if estimate>=remaining:raise RuntimeError('Remaining runtime forecast exceeds budget')
  run('H6',21600);run('H6_tight',21600,tight=True);gate('H6',states['H6'],states['H6_tight'],.5)
  for n in ['H3','H4','H5']:gate('H6_'+n+'_pair',states['H6']-states[n],states['H6_tight']-states[n+'_tight'],.1)
  for p,h in protected.items():assert sha(ROOT/p)==h,p
  out.update(passed=True,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,protected_unchanged=True,actual_six_hour_runs=4,actual_short_runs=2);dump(F/'run_summary.json',out);print(json.dumps(out),flush=True)
 except Exception as e:dump(F/'failure.json',dict(reason=str(e),completed=list(out['runs']),wall_s=time.perf_counter()-start));raise
if __name__=='__main__':main()
