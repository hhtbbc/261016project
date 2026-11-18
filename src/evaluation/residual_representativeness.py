"""Descriptive diagnostics only. Future medians never generate predictions."""
import numpy as np
ELLIPSOIDS={'GRS80':(6378137.,298.257222101),'WGS84':(6378137.,298.257223563)}
OVERLAP_EDGES=np.r_[-np.inf,np.linspace(-4,4,81),np.inf]
def positive(*arrays):
 for a in arrays:
  x=np.asarray(a,float)
  if not np.isfinite(x).all() or np.any(x<=0):raise ValueError('Positive finite density required; no silent masking')
def residual(observed,model):positive(observed,model);return np.log(observed)-np.log(model)
def statistics(e,min_n=30):
 x=np.asarray(e,float)
 if not np.isfinite(x).all():raise ValueError('Invalid residual')
 n=len(x)
 if n<min_n:return dict(N=n,status='N/A_INSUFFICIENT_SAMPLES',mean=None,median=None,std=None,MAD=None,P05=None,P25=None,P75=None,P95=None,positive_fraction=None)
 med=float(np.median(x));p=np.quantile(x,[.05,.25,.75,.95],method='linear')
 return dict(N=n,status='OK',mean=float(x.mean()),median=med,std=float(x.std(ddof=0)),MAD=float(np.median(abs(x-med))),P05=float(p[0]),P25=float(p[1]),P75=float(p[2]),P95=float(p[3]),positive_fraction=float((x>0).mean()))
def overlap(x,y):
 if min(len(x),len(y))<30:return None
 a=np.histogram(x,OVERLAP_EDGES)[0]/len(x);b=np.histogram(y,OVERLAP_EDGES)[0]/len(y);return float(np.minimum(a,b).sum())
def coverage(lat,alt):
 lat=np.asarray(lat);alt=np.asarray(alt);n=len(lat)
 return dict(N=n,north_fraction=float((lat>=0).mean()) if n else None,latitude_mean=float(lat.mean()) if n else None,latitude_P05=float(np.quantile(lat,.05)) if n else None,latitude_P95=float(np.quantile(lat,.95)) if n else None,height_mean_m=float(alt.mean()) if n else None,height_P05_m=float(np.quantile(alt,.05)) if n else None,height_P95_m=float(np.quantile(alt,.95)) if n else None)
def contribution(pred,obs,group):
 positive(pred,obs);p,o=np.asarray(pred),np.asarray(obs);g=np.asarray(group,bool);e=p-o;r=e/o;n=len(o);aa=e*e;rr=r*r
 return dict(N=int(g.sum()),N_total=n,observed_mean=float(o[g].mean()) if g.any() else None,absolute_SS=float(aa[g].sum()),absolute_MSE_contribution=float(aa[g].sum()/n),absolute_SS_fraction=float(aa[g].sum()/aa.sum()) if aa.sum() else None,relative_SS=float(rr[g].sum()),relative_MSE_contribution=float(rr[g].sum()/n),relative_SS_fraction=float(rr[g].sum()/rr.sum()) if rr.sum() else None,relative_bias=float(r[g].mean()) if g.any() else None,log_RMS=float(np.sqrt(np.mean(np.log(p[g]/o[g])**2))) if g.any() else None)
def forward(lon,lat,h,ellipsoid):
 a,rf=ELLIPSOIDS[ellipsoid];f=1/rf;e2=f*(2-f);la=np.deg2rad(lat);lo=np.deg2rad(lon);N=a/np.sqrt(1-e2*np.sin(la)**2)
 return np.array([(N+h)*np.cos(la)*np.cos(lo),(N+h)*np.cos(la)*np.sin(lo),(N*(1-e2)+h)*np.sin(la)])
def inverse(xyz,ellipsoid):
 a,rf=ELLIPSOIDS[ellipsoid];f=1/rf;e2=f*(2-f);x,y,z=map(float,xyz);p=np.hypot(x,y);lon=np.arctan2(y,x)
 if p<1e-8:return float(np.rad2deg(lon)),float(np.sign(z)*90),float(abs(z)-a*(1-f))
 lat=np.arctan2(z,p*(1-e2))
 for _ in range(20):
  N=a/np.sqrt(1-e2*np.sin(lat)**2);new=np.arctan2(z+e2*N*np.sin(lat),p)
  if abs(new-lat)<1e-15:lat=new;break
  lat=new
 h=p*np.cos(lat)+z*np.sin(lat)-a*np.sqrt(1-e2*np.sin(lat)**2)
 return float(np.rad2deg(lon)),float(np.rad2deg(lat)),float(h)
def angular_difference(x,y):return float((x-y+180)%360-180)
