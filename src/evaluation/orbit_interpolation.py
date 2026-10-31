"""Explicitly retrospective cubic Hermite SP3 state interpolation, SI units."""
import numpy as np
from .orbit_data import OrbitSeries


class HermiteOrbit:
    def __init__(self, series, *, expected_step_s=10.):
        self.series=series
        self.seconds=(series.times.tai-series.times[0].tai).sec
        if len(self.seconds)<2 or not np.allclose(np.diff(self.seconds),expected_step_s,rtol=0,atol=1e-6):
            raise ValueError('Continuous native P/V samples required; no gap bridging')

    def evaluate(self, times):
        if times.isscalar:raise ValueError('Ordered array of times required')
        x=np.asarray((times.tai-self.series.times[0].tai).sec)
        if not len(x) or not np.isfinite(x).all() or np.any(np.diff(x)<=0):raise ValueError('Ordered finite queries required')
        if x[0]<-1e-7 or x[-1]>self.seconds[-1]+1e-7:raise ValueError('No orbit extrapolation')
        x=np.clip(x,0,self.seconds[-1])
        k=np.clip(np.searchsorted(self.seconds,x,side='right')-1,0,len(self.seconds)-2)
        dt=self.seconds[k+1]-self.seconds[k];s=((x-self.seconds[k])/dt)[:,None];h=dt[:,None]
        p0,p1=self.series.positions_m[k],self.series.positions_m[k+1]
        v0,v1=self.series.velocities_m_s[k],self.series.velocities_m_s[k+1]
        p=(2*s**3-3*s**2+1)*p0+(s**3-2*s**2+s)*h*v0+(-2*s**3+3*s**2)*p1+(s**3-s**2)*h*v1
        v=(6*s*s-6*s)/h*p0+(3*s*s-4*s+1)*v0+(-6*s*s+6*s)/h*p1+(3*s*s-2*s)*v1
        nearest=np.minimum(abs(x-self.seconds[k]),abs(x-self.seconds[k+1]))
        return OrbitSeries(times.utc,p,v,self.series.frame,{**self.series.metadata,
            'interpolation':'cubic Hermite native SI P/V, TAI seconds',
            'future_bracket_max_s':float(np.max(np.where(nearest<1e-7,0,self.seconds[k+1]-x))),
            'initialization_label':'POSTPROCESSED_RETROSPECTIVE; interpolated non-native t0 uses later state',
            'brackets_lower':k.tolist(),'brackets_upper':(k+1).tolist()})


def signed_density_budget(ai, reference, observation):
    a,r,o=[np.asarray(x,float) for x in (ai,reference,observation)]
    if a.ndim!=1 or a.shape!=r.shape or a.shape!=o.shape or not len(a):raise ValueError('Same nonempty sample vector required')
    if not np.isfinite(np.r_[a,r,o]).all() or np.any(o<=0):raise ValueError('Explicit valid samples required')
    x=a-r;y=r-o;z=a-o
    return dict(n=len(a),signed_identity_max_abs=float(abs(z-x-y).max()),
        RMSE_AI_Swarm=float(np.sqrt(np.mean(z*z))),RMSE_AI_TIE=float(np.sqrt(np.mean(x*x))),RMSE_TIE_Swarm=float(np.sqrt(np.mean(y*y))),
        MSE_AI_Swarm=float(np.mean(z*z)),MSE_AI_TIE=float(np.mean(x*x)),MSE_TIE_Swarm=float(np.mean(y*y)),cross_term=float(2*np.mean(x*y)),
        MSE_closure=float(np.mean(z*z)-np.mean(x*x)-np.mean(y*y)-2*np.mean(x*y)),
        relative_MSE_AI_Swarm=float(np.mean((z/o)**2)),relative_MSE_AI_TIE=float(np.mean((x/o)**2)),
        relative_MSE_TIE_Swarm=float(np.mean((y/o)**2)),relative_cross_term=float(2*np.mean(x*y/o**2)),
        relative_RMS_AI_TIE_with_reference_denominator=float(np.sqrt(np.mean((x/r)**2))) if np.all(r>0) else None,
        bias_AI_Swarm=float(z.mean()),bias_AI_TIE=float(x.mean()),bias_TIE_Swarm=float(y.mean()))


def contiguous_lag_correlation(values, indices, max_lag=120):
    """Descriptive correlations using only uninterrupted original sample pairs.

    No effective sample size/CI is inferred from a nonstationary short window.
    Missing samples are never joined by compressing the sample axis.
    """
    x=np.asarray(values,float);i=np.asarray(indices,int)
    if x.ndim!=1 or x.shape!=i.shape or not np.isfinite(x).all() or np.any(np.diff(i)<=0):raise ValueError('Ordered explicit sample IDs required')
    lookup={int(k):j for j,k in enumerate(i)};rows=[]
    for lag in range(1,max_lag+1):
        pairs=[(j,lookup[int(k)+lag]) for j,k in enumerate(i) if int(k)+lag in lookup
               and lookup[int(k)+lag]-j==lag]
        if len(pairs)<3:continue
        a=np.array([x[j] for j,k in pairs]);b=np.array([x[k] for j,k in pairs])
        corr=float(np.corrcoef(a,b)[0,1]) if a.std()>0 and b.std()>0 else None
        rows.append(dict(lag_samples=lag,pairs=len(pairs),correlation=corr))
    return rows
