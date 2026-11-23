"""Independent geometry, native column reconstruction and mathematical FD checks."""
from collections import defaultdict
from contextlib import ExitStack
from itertools import product
from pathlib import Path
from types import SimpleNamespace
import math
import resource
import time

import astropy.units as u
from astropy.coordinates import EarthLocation
from astropy.time import Time
from netCDF4 import Dataset
import numpy as np

import zg_vertical_v33 as v

EPS=np.finfo(float).eps


def independent_column(ds,i,j,k):
    z=ds['ZG'];rho=ds['DEN']
    v.require(z.dimensions==rho.dimensions==('time','ilev','lat','lon')
              and z.units=='cm' and rho.units=='g/cm3','Native interface mismatch')
    result=[]
    for field,scale in ((z,.01),(rho,1000.0)):
        field.set_auto_maskandscale(False)
        raw=np.asarray(field[i,:,j,k])
        v.require(np.isfinite(raw).all() and (abs(raw)<=1e30).all(),'Nonfinite/fill column')
        for attr in ('_FillValue','missing_value'):
            if attr in field.ncattrs():
                marker=np.asarray(field.getncattr(attr),dtype=raw.dtype)
                v.require(not np.isin(raw,marker).any(),'Explicit fill column')
        result.append([float(x)*scale for x in raw])
    h,d=result
    v.require(all(b>a for a,b in zip(h,h[1:])) and min(d)>0,'Invalid native column')
    return result


def bracket(x,arr):
    v.require(arr[0]<=x<=arr[-1],'Query outside axis')
    k=min(sum(y<=x for y in arr)-1,len(arr)-2)
    return k,(x-arr[k])/(arr[k+1]-arr[k])


def test_receipts(freeze):
    checks={}
    def neg(name,func):
        try:func()
        except ValueError:checks[name]=True
        else:checks[name]=False
    z=np.array([1000.,2000.,3000.]);rho=np.array([4.,2.,1.])*1e-12
    columns=[v.section(z,rho,1500) for _ in range(8)]
    checks['negative_scale_height']=math.isclose(columns[0]['H_m'],1000/math.log(2))
    pos=v.section(z,rho[::-1],1500)
    checks['positive_scale_height_is_none']=(pos['H_m'] is None and pos['sign']=='nonnegative')
    checks['flat_scale_height_is_none']=v.section(z,np.ones(3),1500)['H_m'] is None
    neg('nonpositive_DEN',lambda:v.section(z,np.array([1.,0.,2.]),1500))
    neg('nonmonotonic_ZG',lambda:v.section(np.array([1.,3.,2.]),rho,2))
    neg('no_vertical_extrapolation',lambda:v.section(z,rho,3500))
    neg('reject_nonfinite_column',lambda:v.section(z,np.array([1.,np.nan,2.]),1600))
    neg('time_weight_outside',lambda:v.weight_vector(dict(time=1.1,latitude=.4,longitude=.4)))
    neg('horizontal_weight_outside',lambda:v.weight_vector(dict(time=.1,latitude=.4,longitude=-.4)))
    neg('not_eight_columns',lambda:v.eight(columns[:7],np.ones(8)/8))
    neg('unseen_year',lambda:v.dates(2023,6))
    neg('unregistered_cutoff',lambda:v.dates(2022,12))
    fake={'ZG':SimpleNamespace(units='cm',dimensions=('time','lev','lat','lon')),
          'DEN':SimpleNamespace(units='g/cm3',dimensions=v.SCHEMA)}
    neg('lev_schema_rejected',lambda:v.validate_schema(fake))
    wrong={'ZG':SimpleNamespace(units='m',dimensions=v.SCHEMA),
           'DEN':SimpleNamespace(units='g/cm3',dimensions=v.SCHEMA)}
    neg('wrong_units_rejected',lambda:v.validate_schema(wrong))
    checks['legal_weights_sum_one']=math.isclose(v.weight_vector(dict(time=.1,latitude=.4,longitude=.4)).sum(),1)
    checks['symmetric_steps_inside_all_brackets']=(v.math_steps(1500,columns)==[1,.5,.25])
    checks['knot_does_not_use_central_difference']=not v.math_steps(1000,[v.section(z,rho,1000)]*8)
    checks['formal_offset_not_admitted']=(freeze['physical_offset_status']=='FIXED_OFFSET_NOT_ADMITTED'
                                          and freeze['independent_height_bound'] is None)
    checks['protected_external_gate_source']=('EXTERNAL_DATUM_UNVERIFIED' in
        (v.ROOT/'src/atmosphere/tiegcm_density_provider.py').read_text())
    # At time/latitude/longitude lower corner only one weight is positive. Invalid upper
    # time columns still invalidate the unchanged native query.
    provider=SimpleNamespace(closed=False,source='CPU-only fixture',manifests={},
        epoch=Time('2022-09-23T03:00:00'),seconds=np.array([0.,3600.]),
        lat=np.array([0.,5.]),lon=np.array([0.,5.]),
        records=[(Time('2022-09-23T03:00:00'),Path('a.nc'),0),(Time('2022-09-23T04:00:00'),Path('b.nc'),0)],
        _column=lambda k,j,i:(z+2500*k,rho))
    from atmosphere.tiegcm_density_provider import TiegcmDensityProvider,DATUM
    result=TiegcmDensityProvider.query_native(provider,provider.epoch,0,0,1500,datum=DATUM)
    checks['zero_weight_still_checks_invalid_bounds']=(not result.valid and result.reason=='VERTICAL_OUTSIDE')
    checks['external_interface_rejects']=TiegcmDensityProvider.query_external(provider,None).reason=='EXTERNAL_DATUM_UNVERIFIED'
    v.require(all(checks.values()),str(checks))
    return {k:bool(x) for k,x in checks.items()}


def run():
    begin=time.perf_counter()
    f=v.load(v.OUT/'sample_freeze.json')
    receipt=v.load(v.OUT/'main_receipt.json')
    v.require(v.sha(v.OUT/'sample_freeze.json')==receipt['frozen_plan_SHA256'],'Frozen receipt changed')
    for path,digest in f['source_SHA256'].items():
        v.pin(v.ROOT/path,digest)
    tests=test_receipts(f)
    qrows={(int(r['year']),int(r['cutoff']),int(r['index'])):r for r in v.rows(v.OUT/'query_gradients.csv')}
    cr=defaultdict(list)
    for r in v.rows(v.OUT/'native_column_brackets.csv'):
        cr[int(r['year']),int(r['cutoff']),int(r['index'])].append(r)
    fd=[]
    counts=defaultdict(int)
    max_density=max_grad=0.
    def check(a,b,label,rtol=1e-13,atol=0.):
        counts[label]+=1
        v.require(math.isclose(float(a),float(b),rel_tol=rtol,abs_tol=atol),
                  f'{label} mismatch: {a} vs {b}')
    for s in f['windows']:
        year,hour=s['year'],s['cutoff']
        indices=list(range(0,360,6))
        v.require(s['indices']==indices,'Unexpected selection')
        with np.load(v.ROOT/s['history_path'],allow_pickle=False) as hist:
            utc,lat,lon,alt,raw=[hist[k][indices] for k in ('utc','latitude','longitude','altitude','raw')]
        target=np.datetime64(s['start_UTC'])+np.arange(60)*np.timedelta64(180,'s')
        v.require(np.array_equal(utc,target) and v.sample_identity(utc)==s['selected_utc_SHA256'],
                  'Independent sample UTC mismatch')
        location=EarthLocation.from_geodetic(lon*u.deg,lat*u.deg,alt*u.m,ellipsoid='GRS80')
        itrs=location.to_geocentric()
        ext=EarthLocation.from_geocentric(*itrs).to_geodetic(ellipsoid='WGS84')
        with ExitStack() as stack:
            entries=[]
            for item in s['model_volumes']:
                path=v.ROOT/item['path']
                ds=stack.enter_context(Dataset(path,'r'))
                gridlat=list(map(float,ds['lat'][:]))
                gridlon=list(map(float,ds['lon'][:]))
                for i,mt in enumerate(ds['mtime'][:]):
                    doy,hh,mm=map(int,mt)
                    if doy==266 and hour-3<=hh<=hour:
                        v.require(mm==0 and int(ds['year'][i])==year,'Wrong selected frame calendar')
                        entries.append((f'{year}-09-23T{hh:02}:00:00',path.name,ds,i))
            entries.sort(key=lambda x:x[0])
            v.require(len(entries)==4,'Wrong independent frame count')
            t0=Time(s['start_UTC'])
            tt=list((Time([x[0] for x in entries])-t0).sec)
            for k,index in enumerate(indices):
                key=year,hour,index
                qr=qrows[key]
                v.require(qr['UTC']==str(utc[k])+'Z','Stored ID differs')
                xx=float((Time(utc[k])-t0).sec)
                yy=float(ext.lat[k].deg);ll=(float(ext.lon[k].deg)-gridlon[0])%360+gridlon[0]
                height=float(ext.height[k].to_value(u.m))
                ti,wt=bracket(xx,tt)
                yi,wy=bracket(yy,gridlat)
                xi,wx=bracket(ll,gridlon+[gridlon[0]+360])
                weights=[];active=[];lows=[];tops=[]
                for i,j,m in product((0,1),repeat=3):
                    _,filename,ds,record=entries[ti+i]
                    lonidx=(xi+m)%len(gridlon)
                    z,rho=independent_column(ds,record,yi+j,lonidx)
                    n,u0=bracket(height,z)
                    low,up=z[n:n+2]
                    a,b=(math.log(x) for x in rho[n:n+2])
                    w=(wt if i else 1-wt)*(wy if j else 1-wy)*(wx if m else 1-wx)
                    row=cr[key][len(weights)]
                    v.require([row['file'],int(row['record']),int(row['lat_index']),int(row['lon_index']),int(row['bracket'])]
                              ==[filename,record,yi+j,lonidx,n],'Independent stencil/bracket indices differ')
                    derivative=(b-a)/(up-low)
                    density_log=a+u0*(b-a)
                    check(row['weight'],w,'weight',atol=8*EPS)
                    for field,value in [('lower_m',low),('upper_m',up),('bottom_m',z[0]),('top_m',z[-1]),
                                        ('dlnrho_dh_per_m',derivative),('log_rho',density_log)]:
                        check(row[field],value,field)
                    if derivative<0:
                        check(row['H_m'],-1/derivative,'column_H')
                    else:
                        v.require(not row['H_m'],'Nonnegative column force-fitted scale height')
                    weights.append(w);active.append((low,up,a,b,derivative))
                    lows.append(z[0]);tops.append(z[-1])
                check(math.fsum(weights),1,'sum',atol=8*EPS)
                def value(h):
                    v.require(all(lo<=h<=hi for lo,hi,_,_,_ in active),'FD exceeded bracket')
                    return math.fsum(w*math.exp(a+(h-lo)/(hi-lo)*(b-a))
                                     for w,(lo,hi,a,b,_) in zip(weights,active))
                total=value(height)
                slope=math.fsum(w*math.exp(a+(height-lo)/(hi-lo)*(b-a))*der
                                for w,(lo,hi,a,b,der) in zip(weights,active))/total
                check(raw[k],total,'frozen_density')
                check(qr['dlnrho_dh_per_m'],slope,'gradient')
                check(qr['common_low_m'],max(lows),'common_low')
                check(qr['common_high_m'],min(tops),'common_high')
                check(qr['bottom_margin_m'],height-max(lows),'bottom_margin')
                check(qr['top_margin_m'],min(tops)-height,'top_margin')
                max_density=max(max_density,abs(total/raw[k]-1))
                max_grad=max(max_grad,abs(float(qr['dlnrho_dh_per_m'])-slope))
                near=min(min(height-lo,hi-height) for lo,hi,*_ in active)
                step=min(1.,near/8)
                if step/4<1e-5:
                    v.require(qr['fd_applicable']=='False','Unsafe FD used')
                    fd.append(dict(year=year,cutoff=hour,index=index,status='N/A_BRACKET_BOUNDARY'))
                    continue
                v.require(qr['fd_applicable']=='True','Safe FD omitted')
                for j,dx in enumerate((step,step/2,step/4),1):
                    left,right=math.log(value(height-dx)),math.log(value(height+dx))
                    finite=(right-left)/((height+dx)-(height-dx))
                    diff=abs(finite-slope)
                    # log(sum exp(linear)) third derivative is a third central moment of slopes.
                    span=max(x[4] for x in active)-min(x[4] for x in active)
                    trunc=span**3*dx**2/6
                    rounding=128*EPS*max(abs(left),abs(right),1)/dx+16*EPS*abs(slope)*abs(height)/dx
                    v.require(diff<=trunc+rounding,'FD analytic tolerance exceeded')
                    fd.append(dict(year=year,cutoff=hour,index=index,step_number=j,status='PASS_MATH_ONLY',
                        step_m=dx,analytic_per_m=slope,finite_difference_per_m=finite,
                        absolute_error_per_m=diff,curvature_bound_per_m=trunc,roundoff_bound_per_m=rounding))
    v.table(v.OUT/'finite_difference.csv',fd)
    v.write_once(v.OUT/'independent_verification.json',dict(PASS=True,samples=len(qrows),
        independent_columns=sum(map(len,cr.values())),checks=dict(counts),tests=tests,
        positive_test_count=len(tests),maximum_frozen_density_relative_difference=max_density,
        maximum_gradient_absolute_difference_per_m=max_grad,
        finite_difference_success=sum(r['status']=='PASS_MATH_ONLY' for r in fd),
        finite_difference_not_applicable=sum(r['status']!='PASS_MATH_ONLY' for r in fd),
        fixed_offset_status='FIXED_OFFSET_NOT_ADMITTED',no_observed_density_access=True,
        wall_s=time.perf_counter()-begin,CPU_s=time.process_time(),
        peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))


if __name__=='__main__':
    run()
