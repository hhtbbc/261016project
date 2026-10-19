"""Independently recompute one-hour metrics and normalization round trips."""
from pathlib import Path
import csv,json,numpy as np
ROOT=Path(__file__).resolve().parents[1]
run=ROOT/'experiments/20261019_minimal_direct/result.npz'
with np.load(run,allow_pickle=False) as f:
    pred=f['pred'][0,1].astype(np.float64);ref=f['real'][0,1,:171].astype(np.float64)
    sigma=f['stds'][:171].astype(np.float64);mu=f['means'][:171].astype(np.float64)
    recorded_rmse=f['rmse'][0,0].astype(np.float64);recorded_acc=f['acc'][0,0].astype(np.float64)
assert pred.shape==ref.shape==(171,36,72)
lat=np.load(ROOT/'data/processed/static/lat.npy');w=np.cos(np.deg2rad(lat));w/=w.mean();w=w.reshape(1,36,1)
rmse=np.sqrt(np.mean(w*(pred-ref)**2,axis=(-1,-2)))*sigma[:,0,0]
with np.load(ROOT/'data/processed/static/time_means.npz',allow_pickle=False) as climate:
    clim=np.concatenate([climate[k] for k in ['TN','UN','VN','WN','Z','DEN']],axis=0).astype(np.float64)
clim=(clim-mu)/sigma
pa=pred-clim;ra=ref-clim
acc=np.sum(w*pa*ra,axis=(-1,-2))/np.sqrt(np.sum(w*pa**2,axis=(-1,-2))*np.sum(w*ra**2,axis=(-1,-2)))
np.testing.assert_allclose(rmse,recorded_rmse,rtol=2e-5,atol=1e-25)
np.testing.assert_allclose(acc,recorded_acc,rtol=2e-5,atol=2e-6)
physical=pred*sigma+mu;recovered=(physical-mu)/sigma
assert np.max(np.abs(recovered-pred))<1e-10
assert np.isfinite(physical).all()
lengths=[28,28,28,29,29,29];names=['TN','UN','VN','WN','Z','DEN'];units=['K','cm/s','cm/s','cm/s','cm','g/cm3']
p=ROOT/'results/metrics/20261019_direct_one_hour.csv'
with p.open('w',newline='') as out:
    writer=csv.writer(out);writer.writerow(['variable','vertical_index','unit','weighted_rmse','weighted_acc'])
    offset=0
    for name,length,unit in zip(names,lengths,units):
        for level in range(length):writer.writerow([name,level,unit,rmse[offset+level],acc[offset+level]])
        offset+=length
out={'independent_numpy_metrics_passed':True,'rmse_max_relative_difference':float(np.max(np.abs(rmse-recorded_rmse)/np.maximum(np.abs(rmse),1e-30))),'acc_max_abs_difference':float(np.max(np.abs(acc-recorded_acc))),'zscore_round_trip_max_abs_error':float(np.max(np.abs(recovered-pred))),'finite_physical_prediction':True,'den_positive_fraction':float((physical[142:171]>0).mean()),'scope':'one TIE-GCM reference hour; no observed thermosphere or orbit validation'}
(ROOT/'logs/independent_result_checks.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
