"""Independent, reversible EGM2008 degree<=20 initializer.

Uses the already validated Cartesian evaluator unchanged. No legacy file edits.
"""
import json,hashlib
from math import sqrt,factorial
import numpy as np
from orbit.spherical_harmonics_gravity import SphericalHarmonicsGravity,ROOT,GM,RADIUS_M

class ExtendedEarthGravity(SphericalHarmonicsGravity):
    def __init__(self, degree=20, order=None):
        order=degree if order is None else order
        if not isinstance(degree,int) or not isinstance(order,int) or not 0<=order<=degree<=20:
            raise ValueError('Require integer 0<=order<=degree<=20')
        meta=json.loads((ROOT/'configs/egm2008_degree20_source.json').read_text())
        p=ROOT/'data/raw/gravity_sources/EGM2008_DEG20_PREFIX.gfc';p.resolve().relative_to(ROOT)
        data=p.read_bytes()
        if hashlib.sha256(data).hexdigest()!=meta['sha256']:raise ValueError('Degree20 source SHA mismatch')
        txt=data.decode();assert 'fully_normalized' in txt and 'tide_free' in txt
        header={line.split()[0]:line.split()[1] for line in txt.split('end_of_head')[0].splitlines() if len(line.split())==2}
        if float(header['earth_gravity_constant'])!=GM or float(header['radius'])!=RADIUS_M:raise ValueError('GM/R mismatch')
        self.degree,self.order,self.gm,self.radius_m=degree,order,GM,RADIUS_M;coeff={}
        for line in txt.splitlines():
            f=line.split()
            if len(f)>=5 and f[0]=='gfc':
                n,m=map(int,f[1:3])
                if n<=degree and m<=order:
                    if (n,m) in coeff:raise ValueError('Duplicate coefficient')
                    coeff[n,m]=tuple(float(x.replace('d','e').replace('D','e')) for x in f[3:5])
        if degree>=1:
            for m in range(min(1,order)+1):coeff[1,m]=(0.,0.)
        for n in range(degree+1):
            for m in range(min(n,order)+1):
                if (n,m) not in coeff:raise ValueError(f'Missing coefficient {n},{m}')
        if not all(np.isfinite(v).all() for v in coeff.values()):raise ValueError('Nonfinite coefficients')
        self.coefficients=coeff;self.terms=[]
        for (n,m),(c,s) in coeff.items():
            norm=sqrt((2 if m else 1)*(2*n+1)*factorial(n-m)/factorial(n+m))
            self.terms.append((n,m,c*norm,s*norm))
