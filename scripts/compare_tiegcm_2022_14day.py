"""Bounded-memory reuse of frozen 2021 metrics for delta14 and same-source crosses."""
from pathlib import Path
import sys,json,argparse,time,resource
import numpy as np
from netCDF4 import Dataset,num2date
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import compare_tiegcm_2021_initial_conditions as h
from audit_tiegcm_2021_14day_acceptance import record
TAG='tiegcm_2022_spinup_14day_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG
A7=ROOT/'experiments/tiegcm_training_mar23_v2_2022_longrun';B7=ROOT/'experiments/tiegcm_2022_dual_initial_spinup_v1'
CASES={'delta14':(F/'A14',F/'B14'),'A14_A7':(A7,F/'A14'),'B14_B7':(B7,F/'B14')}

def index_checked(folder):
    out={};grid=None
    for p in sorted(folder.glob('secondary_*.nc')):
        with Dataset(p) as n:
            coords={k:np.array(n[k][:]) for k in ['lat','lon','lev','ilev']}
            if grid is None:grid=coords
            else:
                for k in grid:np.testing.assert_array_equal(grid[k],coords[k])
            assert np.all(n['year'][:]==2022)
            cf=num2date(n['time'][:],n['time'].units)
            for i,(mt,t) in enumerate(zip(n['mtime'][:],cf)):
                d,hr,mi=map(int,mt);s=d*86400+hr*3600+mi*60
                assert t.year==2022 and s==int(t.strftime('%j'))*86400+t.hour*3600+t.minute*60
                assert s not in out;out[s]=(p,i)
            assert n['DEN'].dimensions==n['ZG'].dimensions==('time','ilev','lat','lon') and n['DEN'].units=='g/cm3' and n['ZG'].units=='cm'
    return out,grid

def driver_record(item):
    p,i=item
    with Dataset(p) as n:return np.array([n[k][i] for k in ['f107d','f107a','Kp','hpower','ctpoten']],float)

def main(kind):
    started=time.perf_counter();ap,bp=CASES[kind];ia,g=index_checked(ap);ib,gb=index_checked(bp)
    for k in g:np.testing.assert_array_equal(g[k],gb[k])
    times=sorted(set(ia)&set(ib));assert times==list(range((68 if kind=='delta14' else 75)*86400+3600,84*86400+1,3600))
    out=O/kind;out.mkdir(parents=True,exist_ok=False);rules=json.loads((F/'frozen_comparison_rules.json').read_text());lat=g['lat'];weight=np.cos(np.deg2rad(lat))[None,:,None];regions={k:(lat>=v[0])&(lat<=v[1]) for k,v in rules['latitude_regions'].items()}
    names=['DEN','TN','UN','VN','O1','O2','N2','HE','ZG'];aa={k:[] for k in names};bb={k:[] for k in names};hourly=[];height_hourly=[];ht={v:([],[]) for v in rules['common_native_ZG_heights_km']};maxdriver=0
    specs={k:(.05,True,1e-8 if k in ['O1','O2','N2','HE'] else 0) for k in ['DEN','O1','O2','N2','HE']};specs.update(TN=(10,False,0),UN=(20,False,0),VN=(20,False,0),WIND_VECTOR=(20,False,0),ZG=(None,False,0))
    for t in times:
        a,b=record(*ia[t]),record(*ib[t]);maxdriver=max(maxdriver,float(abs(driver_record(ia[t])-driver_record(ib[t])).max()));assert maxdriver<1e-10
        if t>=82*86400:
            for k in names:aa[k].append(a[k]);bb[k].append(b[k])
        wind=np.hypot(b['UN']-a['UN'],b['VN']-a['VN'])
        for k in ['DEN','TN','WIND_VECTOR','O1','O2','N2','HE','ZG']:
            x,y=(wind,np.zeros_like(wind)) if k=='WIND_VECTOR' else (b[k],a[k]);limit,relative,floor=specs[k]
            hourly.append(dict(variable=k,time_doy_seconds=t,days_since_Mar09=(t-68*86400)/86400,**h.metrics(x,y,weight,limit,relative,floor,k=='DEN')))
        for height,(xs,ys) in ht.items():
            x=h.legacy.a3.at_height(b['ZG'],b['DEN'],height*1000);y=h.legacy.a3.at_height(a['ZG'],a['DEN'],height*1000);xs.append(x);ys.append(y)
            for region,sel in regions.items():height_hourly.append(dict(height_km=height,region=region,time_doy_seconds=t,**h.metrics(x[sel],y[sel],weight[0,sel],.05,True,0,True)))
    aa={k:np.stack(v) for k,v in aa.items()};bb={k:np.stack(v) for k,v in bb.items()};tt=np.arange(82*86400,84*86400+1,3600)
    periods={'candidate':np.ones(49,bool),'last24h':tt>=83*86400,'endpoint':tt==84*86400};rows=[];profiles=[];gates={p:{} for p in periods};matrix=[];hrows=[];trends=[];small=[]
    def gate_matrix(k,x,y,period,mask,limit,relative,floor):
        gate=h.gate_cells(x,y,mask,regions,limit,relative,floor);gates[period][k]=gate
        good=np.isfinite(x)&np.isfinite(y);err=abs(x-y)
        if relative:good&=abs(y)>floor;err=np.divide(err,abs(y),out=np.full_like(err,np.nan),where=good)
        count=0
        for region,sel in regions.items():
            valid=good[mask][:,:,sel,:];n=valid.sum(axis=(2,3));frac=np.divide(((err[mask][:,:,sel,:]<limit)&valid).sum(axis=(2,3)),n,out=np.full(n.shape,np.nan),where=n>0)
            count+=int(np.sum(frac<.95))
            for lev in range(frac.shape[1]):
                v=frac[:,lev];ok=np.isfinite(v);cov=n[:,lev]/valid.shape[2]/valid.shape[3]
                matrix.append(dict(variable=k,period=period,region=region,level=lev,evaluated_hours=int(ok.sum()),failed_hours=int((v[ok]<.95).sum()),minimum_fraction=float(v[ok].min()) if ok.any() else None,coverage_min=float(cov.min()),coverage_max=float(cov.max()),PASS=bool(ok.any() and np.all(v[ok]>=.95))))
        assert count==gate['failed_cells']
    for k in names+['WIND_VECTOR']:
        x,y=(np.hypot(bb['UN']-aa['UN'],bb['VN']-aa['VN']),np.zeros_like(aa['UN'])) if k=='WIND_VECTOR' else (bb[k],aa[k]);limit,relative,floor=specs[k]
        for period,mask in periods.items():
            for region,sel in regions.items():
                xx,yy=x[mask][:,:,sel,:],y[mask][:,:,sel,:];ww=weight[:,sel]
                rows.append(dict(variable=k,period=period,region=region,**h.metrics(xx,yy,ww,limit,relative,floor,k=='DEN')))
                if k in ['DEN','TN','WIND_VECTOR','O1','O2','N2','HE']:
                    for lev in range(xx.shape[1]):profiles.append(dict(variable=k,period=period,region=region,level=lev,**h.metrics(xx[:,lev],yy[:,lev],ww[0],limit,relative,floor,k=='DEN')))
            if k in ['DEN','TN','WIND_VECTOR','O1','O2','N2','HE']:gate_matrix(k,x,y,period,mask,limit,relative,floor)
    tarr=np.array(times);candidate=tarr>=82*86400
    for height,(xs,ys) in ht.items():
        x,y=np.stack(xs)[candidate],np.stack(ys)[candidate]
        for period,mask in periods.items():
            for region,sel in regions.items():hrows.append(dict(height_km=height,period=period,region=region,**h.metrics(x[mask][:,sel,:],y[mask][:,sel,:],weight[0,sel],.05,True,0,True)))
            gate_matrix('ZG_'+str(height)+'km',x[:,None],y[:,None],period,mask,.05,True,0)
        rr=[r for r in height_hourly if r['height_km']==height and r['region']=='global' and r['time_doy_seconds']>=83*86400 and r['log_RMSE'] is not None]
        slope=float(np.polyfit(np.arange(len(rr)),[r['log_RMSE'] for r in rr],1)[0]) if len(rr)>1 else None
        trends.append(dict(height_km=height,n=len(rr),last24h_log_RMSE_slope_per_hour=slope,no_growth_pass=slope is not None and slope<=0,first6_mean=float(np.mean([r['log_RMSE'] for r in rr[:6]])) if rr else None,last6_mean=float(np.mean([r['log_RMSE'] for r in rr[-6:]])) if rr else None))
    for period,mask in periods.items():
        x,y=bb['N2'][mask],aa['N2'][mask];valid=np.isfinite(x)&np.isfinite(y)&(abs(y)>1e-8)
        for label,select in [('all',valid),('near_small_le_1e-5',valid&(y<=1e-5)),('above_1e-5',valid&(y>1e-5))]:
            if not select.any():small.append(dict(period=period,subset=label,n=0,reference_min=None,reference_max=None,max_abs=None,RMSE=None,max_relative=None,relative_P95=None,outside_5pct=0));continue
            xx,yy=x[select],y[select];d=abs(xx-yy);r=d/abs(yy);small.append(dict(period=period,subset=label,n=len(xx),reference_min=float(yy.min()),reference_max=float(yy.max()),max_abs=float(d.max()),RMSE=float(np.sqrt(np.mean(d*d))),max_relative=float(r.max()),relative_P95=float(np.percentile(r,95)),outside_5pct=int((r>=.05).sum())))
    for filename,data in [('native_summary.csv',rows),('native_profiles.csv',profiles),('native_hourly.csv',hourly),('native_ZG_density.csv',hrows),('native_ZG_density_hourly.csv',height_hourly),('last24h_trends.csv',trends),('acceptance_region_level_matrix.csv',matrix),('N2_small_diagnostics.csv',small)]:h.csvout(out/filename,data)
    with (out/'summary.json').open('x') as f:json.dump(dict(comparison=kind,full_overlap_hourly_frames=len(times),candidate_frames=49,driver_max_abs_difference=maxdriver,gates=gates,native_multivariable_pass=all(v['passed'] for p,vv in gates.items() for k,v in vv.items() if not k.startswith('ZG_')),fixed_height_pass=all(v['passed'] for p,vv in gates.items() for k,v in vv.items() if k.startswith('ZG_')),science_training_ready=False,wall_s=time.perf_counter()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024),f,indent=2)
    print('Comparison complete',kind)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--case',choices=list(CASES),required=True);main(p.parse_args().case)
