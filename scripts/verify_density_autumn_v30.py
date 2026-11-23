"""Independent V30 reconstruction and read-only arithmetic on frozen inputs."""
import csv
import datetime
import json
from pathlib import Path
import resource
import sys
import time

import numpy as np
import cdflib
from netCDF4 import Dataset
from astropy.coordinates import EarthLocation
from astropy.time import Time
import astropy.units as u

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R/'src'))
from evaluation.density_verification import (
    ATOL, RTOL, BANDS, FLAGS, WINDOWS, band, check_sha, id_sha, joint, numeric,
    prediction, require, sample_sha, statistics, window,
)
from runtime.tiegcm_rank_exit import write_once, digest as sha

F = R/'experiments/thermosphere_autumn_density_validation_v30'
P = R/'experiments/thermosphere_independent_date_validation_plan_v20/preregistered_protocol.json'
PSHA = 'eb27a080199d656f6018f47834cc9eaef07897009360ca184d6511e4d3aeb2c4'


def read(p):
    return json.loads(p.read_text())


def rows(p):
    with p.open(newline='') as f:
        return list(csv.DictReader(f))


def numeric_native(info, utc, lat, lon, height, begin, end):
    frames=[]
    for ent in info['target_models']:
        path=R/ent['path'];check_sha(path,ent['SHA256'])
        with Dataset(path) as n:
            n.set_auto_mask(False);mlat=np.asarray(n['lat'][:]);mlon=np.asarray(n['lon'][:])
            for k,(year,mt) in enumerate(zip(n['year'][:],n['mtime'][:])):
                dt=datetime.datetime(int(year),1,1)+datetime.timedelta(days=int(mt[0])-1,hours=int(mt[1]),minutes=int(mt[2]));t=np.datetime64(dt,'ns')
                if begin<=t<=end:
                    vv=[]
                    for key,unit,factor in [('ZG','cm',.01),('DEN','g/cm3',1000.)]:
                        v=n[key];require(v.dimensions==('time','ilev','lat','lon') and v.units==unit,'Native model schema mismatch');x=np.asarray(v[k]);require(np.isfinite(x).all(),'Native nonfinite data')
                        for attr in ['missing_value','_FillValue']:
                            if hasattr(v,attr):require(not (x==np.asarray(getattr(v,attr),dtype=x.dtype)).any(),'Native missing marker')
                        vv.append(x.astype(float)*factor)
                    require((vv[1]>0).all() and (np.diff(vv[0],axis=0)>0).all(),'Native physical invalidity');frames.append((t,*vv))
    frames.sort(key=lambda x:x[0]);require(np.array_equal([x[0] for x in frames],begin+np.arange(25)*np.timedelta64(1,'h')),'Target model timeline incomplete')
    # Same explicit Map-A hypothesis, independently construct the GRS80 XYZ -> WGS84 coordinates.
    grs=EarthLocation.from_geodetic(lon*u.deg,lat*u.deg,height*u.m,ellipsoid='GRS80');xyz=np.array([v.to_value(u.m) for v in grs.geocentric]);wg=EarthLocation.from_geocentric(*(v*u.m for v in xyz)).to_geodetic(ellipsoid='WGS84');glat=wg.lat.to_value(u.deg);glon=wg.lon.to_value(u.deg);gh=wg.height.to_value(u.m)
    ft=Time(np.array([x[0] for x in frames]));sec=np.asarray((ft-ft[0]).sec);obssec=np.asarray((Time(utc)-ft[0]).sec);ownraw=[]
    for point in range(len(utc)):
        xx=obssec[point];yy=glat[point];ll=(glon[point]-mlon[0])%360+mlon[0];zzh=gh[point];require(sec[0]<=xx<=sec[-1] and mlat[0]<=yy<=mlat[-1],'Model extrapolation')
        k=int(np.clip(np.searchsorted(sec,xx,side='right')-1,0,len(sec)-2));j=int(np.clip(np.searchsorted(mlat,yy,side='right')-1,0,len(mlat)-2));i=int(np.searchsorted(mlon,ll,side='right')-1);i2=(i+1)%len(mlon);right=mlon[i2]+(360 if i2==0 else 0)
        wt=(xx-sec[k])/(sec[k+1]-sec[k]);wy=(yy-mlat[j])/(mlat[j+1]-mlat[j]);wx=(ll-mlon[i])/(right-mlon[i]);values=[]
        for ki in [k,k+1]:
            for ji in [j,j+1]:
                for li in [i,i2]:
                    z=frames[ki][1][:,ji,li];rho=frames[ki][2][:,ji,li];require(z[0]<=zzh<=z[-1],'Vertical extrapolation');values.append(np.exp(np.interp(zzh,z,np.log(rho))))
        weights=np.array([1-wt,wt])[:,None,None]*np.array([1-wy,wy])[None,:,None]*np.array([1-wx,wx])[None,None,:];ownraw.append(float(np.sum(weights*np.array(values).reshape(2,2,2))))
    ownraw=np.array(ownraw)
    return ownraw


def verify_year(year, audits, details):
    day=f'{year}-09-23'
    begin=np.datetime64(day,'ns')
    end=begin+np.timedelta64(1,'D')
    source=read(F/'source_manifest.json')
    info=source['years'][str(year)]
    parfile=F/f'{year}_parameters.json'
    receipt=read(F/'dual_freeze_receipt.json')
    check_sha(parfile,receipt['parameter_SHA256'][str(year)])
    frozen=read(parfile)
    require(frozen['protocol_SHA256']==PSHA and frozen['date']==day
            and frozen['observation_SHA256']==info['CDF']['SHA256'], 'Parameter source binding')
    check_sha(F/'source_manifest.json',frozen['source_manifest_SHA256'])
    score=read(F/f'{year}_score_receipt.json')
    require(score['attempts']==1 and score['PASS'] and score['parameter_SHA256']==sha(parfile),
            'Scoring receipt mismatch')
    for name,wanted in score['outputs_SHA256'].items():
        check_sha(F/name,wanted)
    params=frozen['parameters']
    path=R/info['CDF']['path']
    check_sha(path,info['CDF']['SHA256'])
    with cdflib.CDF(path) as c:
        utc=cdflib.cdfepoch.to_datetime(c.varget('time')).astype('datetime64[ns]')
        o,lat,lon,height,flag=[c.varget(k) for k in ('density','latitude','longitude','altitude','validity_flag')]
        require(c.globalattsget()['TITLE']==[path.stem] and c.globalattsget()['TIME SYSTEM']==['UTC'],
                'Independent CDF identity')
    quality=(flag==0)&np.isfinite(o)&(o>0)&(o!=9.99e32)&(o<1e30)&np.isfinite(lat)&(abs(lat)<=90)
    quality &= np.isfinite(lon)&(abs(lon)<=180)&np.isfinite(height)&(height>0)
    require(quality.all() and np.array_equal(utc,begin+np.arange(2880)*np.timedelta64(30,'s')),
            'Independent CDF grid or quality')
    raw_own=numeric_native(info,utc,lat,lon,height,begin,end)
    with np.load(F/f'{year}_matched_local.npz') as cache:
        raw=cache['raw']
        for key,val in dict(utc=utc,density=o,latitude=lat,longitude=lon,altitude=height,
                            validity_flag=flag,quality=quality).items():
            require(np.array_equal(cache[key],val),'CDF aligned sample mismatch '+key)
        require(len(raw_own)==2880 and np.isclose(raw,raw_own,rtol=RTOL,atol=ATOL).all(),
                'Independent raw model query comparison exceeded tolerance')
        methods={0:('Raw',),6:('Raw','GlobalAdaptive06'),
                 18:('Raw','GlobalAdaptive18','LatitudeAdaptive18','Stale06')}
        pred={(h,m):prediction(raw,lat,params,h,m) for h,ms in methods.items() for m in ms}
        for (_,method),(p,_) in pred.items():
            if method!='Raw':
                require(np.array_equal(cache[method],p,equal_nan=True),'Frozen multiplier prediction differs '+method)
    # Use the original, independently verified raw values as the arithmetic contract.
    # This prevents coordinate-interpolation roundoff from perturbing near-zero Bias.
    regions={'all':quality,**{k:band(lat)==j for j,k in enumerate(BANDS)}}
    windows={(0,'full_day'):quality,**{(h,w):window(utc,h,w,day) for h in (6,18) for w in WINDOWS}}
    coeffs=[]
    for h in (6,18):
        hist=windows[h,'analysis']
        require(hist.sum()==360 and id_sha(utc[hist])==frozen['history'][str(h)]['utc_ID_SHA256'],
                'Frozen history IDs')
        poisoned=o.astype(float).copy()
        poisoned[utc>=np.datetime64(day+f'T{h:02d}')]*=1e20
        candidates=[('global',params[f'GlobalAdaptive{h:02d}'],hist)]
        if h==18:
            candidates.extend((r,params['LatitudeAdaptive18'][r],hist&regions[r]) for r in BANDS)
        for name,co,mask in candidates:
            n=int(mask.sum())
            require(n==co['N'] and sample_sha(utc[mask],lat[mask],o[mask],raw[mask])==co['sample_SHA256']
                    and np.array_equal(o[mask],poisoned[mask]),'Coefficient input or poison mismatch')
            if n<30:
                require(co['b'] is None and co['multiplier'] is None,'Unsupported coefficient filled')
                continue
            sorted_r=sorted(np.log(o[mask].astype(float))-np.log(raw[mask]))
            independent_b=float(sorted_r[n//2] if n%2 else (sorted_r[n//2-1]+sorted_r[n//2])/2)
            compare(details,year,('coefficient',h,name),'b',co['b'],independent_b)
            require(co['multiplier']==float(np.exp(co['b'])),'Frozen NumPy exponential mismatch')
            coeffs.append(dict(cutoff=h,region=name,N=n,numpy_exp_exact=True))
    rr=rows(F/f'{year}_metrics.csv')
    require(rows(F/f'{year}_raw.csv')==[row for row in rr if row['method']=='Raw'],'Raw persisted tables disagree')
    want={(h,w,m,r) for (h,w) in windows for m in methods[h] for r in regions}
    observed={}
    for row in rr:
        h,w,m,r=key=(int(row['cutoff']),row['window'],row['method'],row['region'])
        require(key in want and key not in observed,'Duplicate/extra metric row')
        sel=windows[h,w]&regions[r]
        p,sup=pred[h,m]
        n=int(sel.sum())
        ns=int((sel&sup).sum())
        status='N/A_UNSUPPORTED_INSUFFICIENT_HISTORY' if ns!=n else ('OK' if n>=30 else 'N/A_INSUFFICIENT_SAMPLES')
        good=status=='OK'
        require(row['status']==status,'Unsupported metric status')
        result=statistics(p[sel],o[sel]) if good else {k:None for k in
            ('MAE','RMSE','bias','relative_RMS','relative_P95','relative_bias','log_RMS','Pearson','max_abs')}
        means=dict(observed_mean=float(np.mean(o[sel].astype(float))) if n else None,
                   simulated_mean=float(np.mean(p[sel])) if n and n==ns else None,
                   bias_over_mean_observed=result['bias']/float(np.mean(o[sel].astype(float))) if good else None)
        for k,v in dict(**result,**means,n=n,eligible=n,n_supported=ns,own_valid=ns,
                        n_scored=n if good else 0,coverage=ns/n if n else None,
                        common_coverage=ns/n if n else None).items():
            compare(details,year,key,k,row[k],v)
        observed[key]=(result,good)
    require(set(observed)==want,'Missing metric row')
    identity={}
    for row in rows(F/f'{year}_common_ids.csv'):
        h,w,m,r=key=(int(row['cutoff']),row['window'],row['method'],row['region'])
        require(key in want and key not in identity,'Duplicate/extra ID reference')
        sel=windows[h,w]&regions[r]
        identity[key]=id_sha(utc[sel])
        require(identity[key]==row['utc_ID_SHA256'] and int(sel.sum())==int(row['N'])
                and int((sel&pred[h,m][1]).sum())==int(row['supported_N']),'Common ID/size mismatch')
    require(set(identity)==want,'Missing common ID reference')
    joint_rows=rows(F/f'{year}_joint.csv')
    expected_joint={(h,w,m) for (h,w) in windows if h and w!='analysis' for m in methods[h] if m!='Raw'}
    seen=set()
    for row in joint_rows:
        h,w,m=key=(int(row['cutoff']),row['window'],row['method'])
        require(key in expected_joint and key not in seen,'Duplicate/extra joint row')
        seen.add(key)
        a={r:observed[h,w,'Raw',r][0] for r in regions}
        c={r:observed[h,w,m,r][0] for r in regions}
        good=all(observed[h,w,method,r][1] for method in ('Raw',m) for r in regions)
        flags=joint(a['all'],c['all'],a['low'],c['low'],good)
        for k,v in flags.items():
            require(row[k]==('' if v is None else str(v)),'Independent joint mismatch '+k)
        require(int(row['N'])==int(windows[h,w].sum()),'Joint N mismatch')
        for metric,label in [('RMSE','RMSE_delta_kg_m3'),('relative_RMS','relative_RMS_delta'),
                             ('relative_P95','relative_P95_delta'),('relative_bias','relative_bias_delta')]:
            x,y=c['all'][metric],a['all'][metric]
            compare(details,year,key,label,row[label],x-y if x is not None and y is not None else None)
        for metric,label in [('RMSE','RMSE_gain_pct'),('relative_RMS','relative_RMS_gain_pct')]:
            x,y=c['all'][metric],a['all'][metric]
            compare(details,year,key,label,row[label],100*(1-x/y) if x is not None else None)
        lc,lr=c['low']['relative_bias'],a['low']['relative_bias']
        compare(details,year,key,'abs_low_relative_bias_delta',row['abs_low_relative_bias_delta'],
                abs(lc)-abs(lr) if lc is not None and lr is not None else None)
    require(seen==expected_joint,'Missing joint row')
    audits[str(year)]=dict(independent_original_CDF=2880,native_frames=25,independent_queries=2880,
        column_checks=23040,max_relative_query_difference=float(np.max(abs(raw/raw_own-1))),
        metric_rows=len(rr),joint_rows=len(joint_rows),common_ID_rows=len(identity),
        coefficients=coeffs,numpy_frozen_multiplier_contract=True)


def compare(details,year,key,field,observed,expected):
    if expected is None:
        details.append(dict(year=year,key=str(key),field=field,main=observed,independent='',
                            absolute_difference='',allowed_absolute_difference='',PASS=observed in ('',None)))
    else:
        r=numeric(observed,expected)
        details.append(dict(year=year,key=str(key),field=field,main=r['main'],independent=r['independent'],
                            absolute_difference=r['absolute_difference'],
                            allowed_absolute_difference=r['allowed_absolute_difference'],PASS=r['PASS']))


def main():
    start=time.perf_counter()
    check_sha(P,PSHA)
    require(F.resolve()==F,'Unexpected V30 output location')
    s=read(F/'source_manifest.json')
    for name,h in s['previous_SHA256'].items():
        check_sha(R/name,h)
    for item in s['science_sources'].values():
        check_sha(R/item['path'],item['SHA256'])
    for info in s['years'].values():
        for entry in info['full_model']:
            path=R/entry['path']
            require(path.stat().st_size==int(entry['bytes']),'Volume size changed')
            check_sha(path,entry['SHA256'])
        for key in ('input','source','GPI','observation','hapi','executable'):
            entry=info['frozen_inputs'][key]
            check_sha(R/entry['path'],entry['SHA256'])
    poison=read(F/'future_poison_test.json')
    require(poison['PASS'] and poison['factor']==1e20 and len(poison['checks'])==4
            and all(row['PASS'] for row in poison['checks']),'Poison receipt incomplete')
    details=[];audits={}
    try:
        for year in (2021,2022):
            verify_year(year,audits,details)
    except Exception as error:
        write_once(F/'independent_exception.json',dict(error=type(error).__name__,reason=str(error),years=audits))
        raise
    with (F/'independent_numeric_checks.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(details[0]),lineterminator='\n')
        w.writeheader()
        w.writerows(details)
    fails=[x for x in details if not x['PASS']]
    write_once(F/'independent_verification.json',dict(PASS=not fails,rtol=RTOL,atol=ATOL,
        field_checks=len(details),failures=fails,years=audits,model_volumes_rehashed=66,
        protected_files=len(s['previous_SHA256']),peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        wall_s=time.perf_counter()-start,CPU_s=time.process_time()))
    require(not fails,'Independent numeric comparison did not close')


if __name__=='__main__':
    main()
