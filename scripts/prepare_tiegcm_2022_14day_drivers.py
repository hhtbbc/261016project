"""Extend 2022 GFZ sources without changing any historical values or GPI."""
from pathlib import Path
import sys,json,math,time
from datetime import date,timedelta
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import prepare_tiegcm_training_drivers as old
from prepare_tiegcm_mar23_drivers import inputs,independent,utc
from run_tiegcm_mar23_2021_longrun import stream_sha
TAG='tiegcm_2022_spinup_14day_v1';F=ROOT/'experiments'/TAG;RAW=ROOT/'data/raw'/TAG;OUT=ROOT/'data/processed'/TAG

def support():
    a=date(2022,3,9);b=date(2022,3,25);lo=a-timedelta(days=2);hi=b+timedelta(days=2)
    return a,b,lo,hi,lo-timedelta(days=40),hi+timedelta(days=40)
def main():
    started=time.perf_counter()
    for p in [F,RAW,OUT]:p.resolve().relative_to(ROOT);p.mkdir(exist_ok=False)
    prior=ROOT/'data/processed/training_window_mar23_v2/gpi_2022_mar23_v2.nc';prior_sha=stream_sha(prior)
    a,b,lo,hi,sl,sh=support();protocol,solar,kp,sources=inputs(2022,False)
    missing_s=[d for d in old.dates(sl,sh) if utc(d) not in solar]
    missing_k=[utc(d)+timedelta(hours=h) for d in old.dates(lo,hi) for h in range(0,24,3) if utc(d)+timedelta(hours=h) not in kp]
    old.dump(F/'driver_plan.json',dict(model_dates=[str(a),str(b)],raw_dates=[str(lo),str(hi)],solar_dates=[str(sl),str(sh)],Fobs_required=(sh-sl).days+1,Kp_required=((hi-lo).days+1)*8,missing_Fobs=[str(d) for d in missing_s],missing_Kp=[t.isoformat() for t in missing_k],download_limit_bytes=2*2**20,prior_GPI_SHA256=prior_sha))
    downloaded=[]
    try:
        for key,missing,target in [('Fobs',missing_s,solar),('Kp',missing_k,kp)]:
            if not missing:continue
            first=missing[0] if key=='Fobs' else missing[0].date();last=missing[-1] if key=='Fobs' else missing[-1].date()
            values,meta=old.fetch(key,first,last,RAW/f'{key}_extension.json')
            assert not set(values)&set(target),'Unexpected source overlap; cannot overwrite old observations'
            target.update(values);sources.append(meta);downloaded.append(meta);old.dump(F/f'{key}_extension_source.json',meta)
        assert set(solar)=={utc(d) for d in old.dates(sl,sh)} and set(kp)=={utc(d)+timedelta(hours=h) for d in old.dates(lo,hi) for h in range(0,24,3)}
        assert len(solar)==101 and len(kp)==168 and all(np.isfinite(v) and v>0 for v in solar.values()) and all(np.isfinite(v) and 0<=v<=9 for v in kp.values())
        ds,f,avg,k=old.arrays(solar,kp,lo,hi);check=np.array([math.fsum(solar[utc(d)+timedelta(days=j)] for j in range(-40,41))/81 for d in ds]);assert max(abs(avg-check))<1e-12
        p=OUT/'gpi_2022_14day.nc';old.write_gpi(p,ds,f,avg,k,a,b);driver=old.GpiDriver(p);errors=[]
        for day in old.dates(a,b):
            for sec in [0,60,5399,5400,10800,43199,43200,86399]:
                x=driver.at(int(day.strftime('%Y%j')),sec);y=independent(p,int(day.strftime('%Y%j')),sec);errors.extend(abs(x[q]-y[q]) for q in x)
        assert max(errors)<1e-10
        previous=old.GpiDriver(prior);common=[]
        for absolute in range(75*86400,84*86400+1,60):
            d,s=divmod(absolute,86400);x=driver.at(2022000+d,s);y=previous.at(2022000+d,s);common.extend(abs(x[q]-y[q]) for q in x)
        assert max(common)<1e-10 and stream_sha(prior)==prior_sha
        for absolute in range(68*86400,84*86400+1,60):
            d,s=divmod(absolute,86400);v=driver.at(2022000+d,s);assert all(np.isfinite(z) for z in v.values())
        result=dict(status='PASS',file=str(p.relative_to(ROOT)),SHA256=stream_sha(p),model_dates=[str(a),str(b)],raw_dates=[str(lo),str(hi)],solar_dates=[str(sl),str(sh)],Fobs_count=len(solar),Kp_count=len(kp),missing=0,estimated_or_adjusted_used=False,sources=sources,downloaded_sources=downloaded,download_bytes=sum(x['bytes'] for x in downloaded),independent_mean_max_difference=float(max(abs(avg-check))),independent_interpolation_max_difference=max(errors),common_12961_minute_nodes_max_difference=max(common),static_minute_nodes=23041,prior_GPI_unchanged=True,prior_GPI_SHA256=prior_sha,arrays=dict(year_day=[int(d.strftime('%Y%j')) for d in ds],f107d=f.tolist(),f107a=avg.tolist(),kp=k.tolist()),wall_s=time.perf_counter()-started)
        old.dump(F/'driver_audit.json',result);p.chmod(0o444);print('Extended 2022 GPI PASS',result['SHA256'],result['download_bytes'])
    except Exception as e:
        old.dump(F/'driver_failure.json',dict(error=repr(e),completed_downloads=downloaded,model_launches=0));raise
if __name__=='__main__':main()
