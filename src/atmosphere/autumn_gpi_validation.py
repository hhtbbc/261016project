"""V22 independent raw/calendar and cubic interpolation audit; never launches a model."""
import json, math
from datetime import datetime, timedelta, timezone
import numpy as np
from netCDF4 import Dataset
UTC=timezone.utc
MEAN_ATOL=1e-12
DRIVER_ATOL=1e-10

def stamp(year,month,day):return datetime(year,month,day,tzinfo=UTC)
def span(lo,hi,hours=24):
    return [lo+timedelta(hours=i*hours) for i in range(int((hi-lo).total_seconds()//(3600*hours))+1)]
def check_records(solar,kp,year):
    expected=span(stamp(year,7,29),stamp(year,11,6))
    if set(solar)!=set(expected):raise ValueError('Missing/extra Fobs UTC')
    expected=span(stamp(year,9,7),stamp(year,9,27)+timedelta(hours=21),3)
    if set(kp)!=set(expected):raise ValueError('Missing/extra definitive Kp UTC')
    if any(not math.isfinite(x) or x<=0 for x in solar.values()):raise ValueError('Illegal Fobs')
    if any(not math.isfinite(x) or not 0<=x<=9 for x in kp.values()):raise ValueError('Illegal Kp')

def read_raw(year,paths):
    """Separate raw parser: no builder decode/arrays or GpiDriver calls."""
    solar={};kp={}
    def add(d,k,v):
        if k in d:raise ValueError('Duplicate UTC')
        d[k]=float(v)
    if year==2021:
        for line in paths[0].read_text().splitlines():
            a=line.split()
            if not a or a[0]!='2021':continue
            t=datetime(*map(int,a[:3]),tzinfo=UTC)
            if stamp(year,7,29)<=t<=stamp(year,11,6):add(solar,t,a[25])
            if stamp(year,9,7)<=t<=stamp(year,9,27):
                if a[27]!='2':raise ValueError('Non-definitive archived Kp')
                for j in range(8):add(kp,t+timedelta(hours=j*3),a[7+j])
    else:
        for path,key,target in zip(paths,['Fobs','Kp'],[solar,kp]):
            p=json.loads(path.read_text())
            if len(p['datetime'])!=len(p[key]):raise ValueError('Length mismatch')
            if key=='Kp' and p.get('status')!=['def']*len(p[key]):raise ValueError('Non-definitive Kp')
            for t,v in zip(p['datetime'],p[key]):
                q=datetime.fromisoformat(t.replace('Z','+00:00'))
                if q.tzinfo is None or q.utcoffset()!=timedelta(0):raise ValueError('Not UTC')
                add(target,q,v)
    check_records(solar,kp,year)
    return solar,kp

def schema(path):
    with Dataset(path) as n:
        return dict(format=n.data_model,variables={k:dict(dimensions=list(v.dimensions),dtype=str(v.dtype),units=getattr(v,'units',None)) for k,v in n.variables.items()},nkp=len(n.dimensions['nkp']))

def check_file(path,solar,kp,year,template):
    if schema(path)!=schema(template):raise ValueError('Schema/unit/type differs from proven spring GPI')
    days=span(stamp(year,9,7),stamp(year,9,27))
    means={t:math.fsum(solar[t+timedelta(days=j)] for j in range(-40,41))/81 for t in days}
    with Dataset(path) as n:
        if n.averaging_window_days!=81 or n.averaging_kind!='centered' or n.time_standard!='UTC':raise ValueError('Wrong averaging/time contract')
        if (int(n.yearday_beg),int(n.yearday_end))!=(int(stamp(year,9,9).strftime('%Y%j')),int(stamp(year,9,25).strftime('%Y%j'))):raise ValueError('Wrong valid dates')
        labels=np.asarray(n['year_day'][:]);expected=np.array([int(t.strftime('%Y%j')) for t in days])
        if not np.array_equal(labels,expected):raise ValueError('Time shift/duplicate/missing')
        worst=0.
        for i,t in enumerate(days):
            if float(n['f107d'][i])!=solar[t]:raise ValueError('Fobs node mismatch')
            diff=abs(float(n['f107a'][i])-means[t]);worst=max(worst,diff)
            if not diff<MEAN_ATOL:raise ValueError('Centered81 mismatch')
            for j in range(8):
                if float(n['kp'][i,j])!=kp[t+timedelta(hours=3*j)]:raise ValueError('Kp node mismatch')
        for k in ['f107d','f107a','kp']:
            v=np.ma.asarray(n[k][:])
            if np.ma.getmaskarray(v).any() or not np.isfinite(v).all():raise ValueError('Invalid native variable')
        if (n['f107d'][:]<=0).any() or (n['f107a'][:]<=0).any() or (n['kp'][:]<0).any() or (n['kp'][:]>9).any():raise ValueError('Illegal native values')
    return means,worst

def independent_at(t,solar,means,kp):
    """UTC noon nodes, explicit cubic weights, center-bracketing Kp and scalar math."""
    day=t.replace(hour=0,minute=0,second=0,microsecond=0)
    noon=day+timedelta(hours=12)
    anchor=noon if t>=noon else noon-timedelta(days=1)
    u=(t-anchor).total_seconds()/86400
    w=(-u*(u-1)*(u-2)/6,(u+1)*(u-1)*(u-2)/2,-(u+1)*u*(u-2)/2,(u+1)*u*(u-1)/6)
    dates=[anchor.replace(hour=0)+timedelta(days=j) for j in (-1,0,1,2)]
    fd=math.fsum(weight*solar[q] for weight,q in zip(w,dates))
    fa=math.fsum(weight*means[q] for weight,q in zip(w,dates))
    # Bucket start at UTC 00/03/...; interpolation nodes at bucket center +1.5h.
    x=(t-(day+timedelta(hours=1.5))).total_seconds()/10800
    left=math.floor(x);fraction=x-left
    a=day+timedelta(hours=3*left);b=a+timedelta(hours=3)
    k=kp[a]*(1-fraction)+kp[b]*fraction
    power=16.82*math.exp(.32*k)-4.86 if k<=7 else 153.13+(k-7)*146.87/2
    return dict(f107d=fd,f107a=fa,Kp=k,hpower=power,ctpoten=15+15*k+.8*k*k)

def compare_driver(driver,solar,means,kp,year):
    start=stamp(year,9,9);end=stamp(year,9,25)
    nodes=set(span(start,end,1/60))
    for d in span(start,end):
        for s in [0,1,5399,5400,5401,10799,10800,43199,43200,43201,86399]:
            t=d+timedelta(seconds=s)
            if t<=end:nodes.add(t)
    errors={k:0. for k in ['f107d','f107a','Kp','hpower','ctpoten']};samples=[]
    for t in sorted(nodes):
        seconds=t.hour*3600+t.minute*60+t.second
        actual=driver.at(int(t.strftime('%Y%j')),seconds);expected=independent_at(t,solar,means,kp)
        for k in errors:
            delta=abs(actual[k]-expected[k]);errors[k]=max(errors[k],delta)
            if not math.isfinite(actual[k]) or not delta<DRIVER_ATOL:raise ValueError('Runtime interpolation mismatch '+k)
        if t.day in [9,23,25] and seconds in [0,5400,43199,43200,86399]:samples.append(dict(UTC=t.isoformat(),**actual))
    for yd,sec in [(year*1000+251,0),(year*1000+269,0),(year*1000+252,86400)]:
        try:driver.at(yd,sec)
        except ValueError:continue
        raise ValueError('Out-of-range query accepted')
    return dict(minute_nodes=23041,total_unique_nodes=len(nodes),max_abs_difference=errors,samples=samples,outside_domain_rejected=True)
