"""Independent physical-unit metric and causal-identity audit, no coefficient fitting changes."""
from pathlib import Path
import sys,json,csv,time,resource
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
import numpy as np,cdflib
from PIL import Image
from scripts.prepare_fourcastden_swarm_observation_v1 import sha
F=ROOT/'experiments/cross_year_causal_density_validation_v1'
def main():
 start=time.perf_counter();z=np.load(F/'matched_local.npz');source=json.loads((F/'source_manifest.json').read_text());pr=json.loads((F/'frozen_protocol.json').read_text());coef=json.loads((F/'correction_parameters.json').read_text());assert coef['protocol_SHA256']==sha(F/'frozen_protocol.json')
 with cdflib.CDF(ROOT/source['observation']['source_file']) as c:
  tt=cdflib.cdfepoch.to_datetime(c.varget('time'));dd=c.varget('density');ff=c.varget('validity_flag');lat=c.varget('latitude');height=c.varget('altitude')
  idx=np.searchsorted(tt,z['utc']);np.testing.assert_array_equal(tt[idx],z['utc']);np.testing.assert_array_equal(dd[idx],z['density']);np.testing.assert_array_equal(ff[idx],z['validity_flag']);np.testing.assert_array_equal(lat[idx],z['latitude']);np.testing.assert_array_equal(height[idx],z['altitude'])
 masks={'analysis':(z['utc']>=np.datetime64('2021-03-24T03'))&(z['utc']<np.datetime64('2021-03-24T06')),**{f'future_{h}h':(z['utc']>=np.datetime64('2021-03-24T06'))&(z['utc']<np.datetime64(f'2021-03-24T{6+h:02d}')) for h in [1,3,6]},'incremental_1_3h':(z['utc']>=np.datetime64('2021-03-24T07'))&(z['utc']<np.datetime64('2021-03-24T09')),'incremental_3_6h':(z['utc']>=np.datetime64('2021-03-24T09'))&(z['utc']<np.datetime64('2021-03-24T12'))}
 assert masks['analysis'].sum()==360 and masks['future_6h'].sum()==720
 metrics=list(csv.DictReader((F/'metrics.csv').open()));checked=0
 for case,p in coef['adaptive'].items():
  e=np.log(z['density'][masks['analysis']])-np.log(z[case+'_Raw'][masks['analysis']]);assert float(np.median(e))==p['b_2021']
  for method in ['Raw','Adaptive']+(['Transfer'] if case=='B14' else []):
   pred=z[case+'_'+method];expected=z[case+'_Raw']*(1 if method=='Raw' else (pr['transfer_multiplier'] if method=='Transfer' else p['multiplier_2021']));np.testing.assert_array_equal(pred,expected)
   for window,m in masks.items():
    x=pred[m];y=z['density'][m];err=x-y;rel=err/y;r=next(x for x in metrics if x['case']==case and x['method']==method and x['window']==window)
    for key,val in {'MAE':np.mean(abs(err)),'RMSE':np.sqrt(np.mean(err**2)),'bias':np.mean(err),'relative_RMS':np.sqrt(np.mean(rel**2)),'relative_P95':np.percentile(abs(rel),95),'relative_bias':np.mean(rel),'log_RMS':np.sqrt(np.mean(np.log(x/y)**2))}.items():assert np.isclose(float(r[key]),val,rtol=1e-13,atol=0),(case,method,window,key)
    checked+=1
  assert np.isfinite(z[case+'_Adaptive']).all() and np.all(z[case+'_Adaptive']>0)
 for p in (F/'figures').glob('*.png'):
  with Image.open(p) as im:im.verify()
 assert len(list((F/'figures').glob('*.png')))==7
 for name,h in source['protected_inputs'].items():assert sha(ROOT/name)==h,name
 out=dict(PASS=True,CDF_exactly_matched_records=len(idx),independently_recomputed_metric_rows=checked,all_adaptive_parameters_exact_history_medians=True,transfer_constant_unchanged=coef['transfer']['b_2022']==.1261252775057784,old_files_SHA_unchanged=len(source['protected_inputs']),nonpositive_corrected=0,nonfinite_corrected=0,figures=7,wall_s=time.perf_counter()-start,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024)
 with (F/'independent_verification.json').open('x') as f:json.dump(out,f,indent=2)
 print('INDEPENDENT CROSS-YEAR VERIFICATION PASS',checked,flush=True)
if __name__=='__main__':main()
