"""Independent reproduction of the installed gpi.F interpolation convention."""
import numpy as np
from netCDF4 import Dataset

class GpiDriver:
    def __init__(self,path):
        with Dataset(path) as n:
            self.days=np.asarray(n['year_day'][:]);self.f107d=np.asarray(n['f107d'][:])
            self.f107a=np.asarray(n['f107a'][:]);self.kp=np.asarray(n['kp'][:])
            self.begin=int(n.yearday_beg);self.end=int(n.yearday_end)
        if self.kp.shape!=(len(self.days),8):raise ValueError('Invalid Kp dimensions')
    def at(self,year_day,seconds):
        if not self.begin<=year_day<=self.end or not 0<=seconds<86400:
            raise ValueError('Driver date/time outside valid domain')
        hits=np.flatnonzero(self.days==year_day)
        if len(hits)!=1:raise ValueError('Missing/duplicate day')
        i=int(hits[0]);left=i-2 if seconds<43200 else i-1
        if left<0 or left+4>len(self.days):raise ValueError('Missing solar interpolation padding')
        x=np.array([-1.,0.,1.,2.]);t=((seconds-43200)%86400)/86400
        w=np.array([np.prod([(t-x[j])/(x[k]-x[j]) for j in range(4) if j!=k]) for k in range(4)])
        f107d=float(w@self.f107d[left:left+4]);f107a=float(w@self.f107a[left:left+4])
        centers=np.r_[-5400,np.arange(8)*10800+5400,91800]
        values=np.r_[self.kp[i-1,7],self.kp[i],self.kp[i+1,0]]
        kp=float(np.interp(seconds,centers,values))
        power=float(16.82*np.exp(.32*kp)-4.86) if kp<=7 else 153.13+(kp-7)/2*(300-153.13)
        return {'f107d':f107d,'f107a':f107a,'Kp':kp,'hpower':power,'ctpoten':15+15*kp+.8*kp**2}
