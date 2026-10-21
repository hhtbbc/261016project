"""Float64 independent metrics on native pressure surfaces, no inference model."""
import numpy as np
NAMES=('TN','UN','VN','WN','Z','DEN')
LENGTHS=(28,28,28,29,29,29)
UNITS=('K','cm/s','cm/s','cm/s','cm','g/cm3')
SI_UNITS=('K','m/s','m/s','m/s','m','kg/m3')
SI_FACTORS=(1.,.01,.01,.01,.01,1000.)

def channel_metrics(pred,reference,climatology,lat):
    p,r,clim=map(lambda x:np.asarray(x,dtype=np.float64),(pred,reference,climatology))
    if p.shape!=r.shape or p.shape!=clim.shape or p.ndim!=3 or not np.isfinite([p,r,clim]).all():raise ValueError('Aligned finite C/lat/lon fields required')
    w=np.cos(np.deg2rad(np.asarray(lat,dtype=float)));w=w/w.mean();w=w[None,:,None]
    rmse=np.sqrt(np.mean(w*(p-r)**2,axis=(-1,-2)))
    pa,ra=p-clim,r-clim
    denom=np.sqrt(np.sum(w*pa**2,axis=(-1,-2))*np.sum(w*ra**2,axis=(-1,-2)))
    acc=np.full(len(p),np.nan);valid=np.isfinite(denom)&(denom>0)
    np.divide(np.sum(w*pa*ra,axis=(-1,-2)),denom,out=acc,where=valid)
    return rmse,acc,valid

def feedback_check(inputs,outputs,real,sw):
    if len(inputs)!=2 or len(outputs)!=2:raise ValueError('Exactly two real network calls required')
    np.testing.assert_array_equal(inputs[0][0][0,:171],real[0,:171])
    np.testing.assert_array_equal(inputs[1][0][0,:171],outputs[0][0])
    for k in range(2):
        np.testing.assert_array_equal(inputs[k][0][0,171:],real[k+1,171:])
        np.testing.assert_array_equal(inputs[k][1].reshape(-1),sw[k+1])
    return dict(passed=True,second_state_equals_first_prediction=True,physical_truth_used_after_t0=False,future_auxiliary_and_drivers_used=True)
