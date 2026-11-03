"""Independent numerical summary/asset verification with no force evaluation."""
from pathlib import Path
import sys,csv,json,itertools,time
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from run_orbit_12h_numerical_reference_v1 import F,O,OLD,GROUPS,TIMES,saved
from prepare_fourcastden_swarm_observation_v1 import sha,dump

def main():
    start=time.perf_counter();a=saved();rows=list(csv.DictReader((O/'reference_comparison.csv').open()));states={}
    for case in ['DOP30','DOP15']:
        with np.load(F/f'{case}_states_local.npz') as n:
            states[case]=n['states'];np.testing.assert_array_equal(n['seconds'],TIMES);np.testing.assert_array_equal(n['left_end'],n['right_start']);np.testing.assert_array_equal(n['states'][0],a['A_NoDrag','tight'][0])
    states.update({'RK45_Base':a['A_NoDrag','base'],'RK45_Tight':a['A_NoDrag','tight']})
    for row in rows:
        name=row['comparison'].split(' minus ')[0];d=states[name]-states['DOP15'];n=np.sqrt(sum(d[:,i]**2 for i in range(3)));v=np.sqrt(sum(d[:,i]**2 for i in range(3,6)))
        np.testing.assert_allclose([n.max(),n[-1],np.sqrt(np.mean(n*n)),v.max()],[float(row[k]) for k in ['max_position_m','terminal_m','RMS_m','max_speed_m_s']],rtol=1e-13,atol=1e-14)
    pair=list(csv.DictReader((O/'pair_identity.csv').open()))
    for row in pair:
        g,h=row['pair'].split(' minus ');d=(a[g,'base']-a[g,'tight'])-(a[h,'base']-a[h,'tight']);np.testing.assert_allclose(np.sqrt(np.sum(d[:,:3]**2,axis=1)).max(),float(row['max_pair_position_numerical_m']),rtol=1e-14,atol=0)
    protected=json.loads((F/'protected.json').read_text());assert all(sha(ROOT/k)==v for k,v in protected.items())
    old=json.loads((OLD/'local_output_inventory.json').read_text());assert all(sha(ROOT/r['path'])==r['SHA256'] for r in old['files'])
    assert json.loads((OLD/'analysis.json').read_text())['gates']['ORBIT_NUMERICAL_CONVERGENCE_READY']=='FAIL'
    png=list(O.glob('*.png'));assert len(png)==8
    for p in png:
        with Image.open(p) as im:im.verify()
    for row in csv.DictReader((O/'figure_sources.csv').open()):assert sha(O/row['figure'])==row['SHA256']
    sup=json.loads((F/'supervision.json').read_text());assert sup['status']=='PASS' and sup['wall_s']<3600 and sup['peak_tree_RSS_bytes']<4*2**30
    dump(F/'independent_audit.json',dict(status='PASS',new_NoDrag_trajectories=2,new_B_C_D=0,summary_comparisons_independently_verified=3,old_pair_identities=6,protected_unchanged=len(protected),original_outputs_verified=len(old['files']),old_overall_gate='FAIL_UNCHANGED',PNGs=8,wall_s=time.perf_counter()-start,no_new_force_calls=True,real_orbit_gate='BLOCKED',scientific_training_READY=False))
    print((F/'independent_audit.json').read_text())
if __name__=='__main__':main()
