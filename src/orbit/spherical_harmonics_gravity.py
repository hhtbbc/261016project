"""Static full 8x8 EGM2008, Cartesian solid harmonics, SI physical gravity.

No spherical-coordinate divisions: exact poles are supported. Coefficients are
4pi fully normalized without Condon-Shortley phase. Includes the monopole.
"""
from pathlib import Path
from math import factorial, sqrt
import hashlib
import numpy as np
from orbit.drag import EarthFixedFrame

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'data/raw/gravity_sources/EGM2008_HEAD_PARTIAL.txt'
SOURCE_SHA = 'ce9334659955fe001e31b63f77838cd883436ee91830940a8e0836e4bdf55d1e'
GM = 3.986004415e14
RADIUS_M = 6378136.3

class SphericalHarmonicsGravity:
    """Complete static degree/order truncation; not a complete orbit force model."""
    def __init__(self, degree=8, order=8, coefficients=None, gm=GM, radius_m=RADIUS_M):
        if not isinstance(degree,int) or not isinstance(order,int) or not 0<=order<=degree<=8:
            raise ValueError('Require integer 0 <= order <= degree <= 8')
        if not np.isfinite([gm,radius_m]).all() or gm<=0 or radius_m<=0:raise ValueError('Invalid GM/R')
        self.degree,self.order,self.gm,self.radius_m=degree,order,float(gm),float(radius_m)
        if coefficients is None:
            if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('Coefficient SHA mismatch')
            coefficients={}
            for line in SOURCE.read_text().splitlines():
                p=line.split()
                if len(p)>=5 and p[0]=='gfc':
                    n,m=int(p[1]),int(p[2])
                    if n<=degree and m<=order:coefficients[n,m]=tuple(float(x.replace('d','e')) for x in p[3:5])
            # Degree one is absent by geocentric origin convention, not missing data.
            if degree >= 1:
                for m in range(min(1,order)+1):coefficients[1,m]=(0.,0.)
            for n in range(degree+1):
                for m in range(min(n,order)+1):
                    if (n,m) not in coefficients:raise ValueError('Incomplete coefficient triangle')
        self.coefficients=dict(coefficients)
        if not all(0<=m<=n<=degree and m<=order and np.isfinite(v).all() and len(v)==2 for (n,m),v in self.coefficients.items()):raise ValueError('Invalid coefficients')
        self.terms=[]
        for (n,m),(c,s) in self.coefficients.items():
            norm=sqrt((2 if m else 1)*(2*n+1)*factorial(n-m)/factorial(n+m))
            self.terms.append((n,m,c*norm,s*norm))

    def evaluate_itrs(self, position_m):
        """Return specific mechanical potential U (J/kg), and -grad U (m/s²)."""
        p=np.asarray(position_m)
        if p.shape!=(3,) or np.iscomplexobj(p) or not np.isfinite(p).all() or np.linalg.norm(p)==0:raise ValueError('Finite nonzero Cartesian position required')
        x,y,z=p/self.radius_m;d2=x*x+y*y+z*z;d=np.sqrt(d2)
        q=np.array([x,y,z]);e=np.eye(3);xy=x+1j*y;gxy=e[0]+1j*e[1]
        H={(0,0):(1.+0j,np.zeros(3,dtype=complex))}
        for m in range(self.order+1):
            if m:
                v,g=H[m-1,m-1];H[m,m]=((2*m-1)*xy*v,(2*m-1)*(gxy*v+xy*g))
            for n in range(m+1,self.degree+1):
                v,g=H[n-1,m]
                if n==m+1:H[n,m]=((2*m+1)*z*v,(2*m+1)*(e[2]*v+z*g))
                else:
                    w,h=H[n-2,m];a=2*n-1;b=n+m-1;c=n-m
                    H[n,m]=((a*z*v-b*d2*w)/c,(a*(e[2]*v+z*g)-b*(2*q*w+d2*h))/c)
        V=0.;grad=np.zeros(3,dtype=np.result_type(p,float))
        for n,m,c,s in self.terms:
            v,g=H[n,m];v=c*v.real+s*v.imag;g=c*g.real+s*g.imag
            V+=v/d**(2*n+1)
            grad+=g/d**(2*n+1)-(2*n+1)*v*q/d**(2*n+3)
        return -self.gm/self.radius_m*V,self.gm/self.radius_m**2*grad

    def acceleration_itrs(self, position_m):return self.evaluate_itrs(position_m)[1]
    def potential_itrs(self, position_m):return self.evaluate_itrs(position_m)[0]

class GcrsSphericalHarmonicsForce:
    """Exact existing ERFA c2t06a per call, frozen EOP; force rotates only."""
    def __init__(self, epoch, model=None):
        self.frame=EarthFixedFrame(epoch);self.model=model or SphericalHarmonicsGravity()
    def __call__(self, seconds, position, velocity):
        _,r,_,Q=self.frame.state_to_itrs(seconds,position,velocity)
        return Q.T@self.model.acceleration_itrs(r)
