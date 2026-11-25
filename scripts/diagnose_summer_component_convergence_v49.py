"""Streaming V49 diagnostics over the two accepted TIE-GCM histories."""
import csv
from collections import defaultdict
from contextlib import ExitStack
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import re
import subprocess

from netCDF4 import Dataset, num2date
import numpy as np

import preflight_summer_seed_recovery_v47 as recovery
import analyze_summer_seed_sensitivity_v46 as frozen
from atmosphere.tiegcm_autumn_acceptance import field as native_field

ROOT = recovery.ROOT
OUT = ROOT/'experiments/thermosphere_summer_component_convergence_v49'
V48 = ROOT/'experiments/thermosphere_summer_seed_execution_v48'
COMPARE = recovery.OUT/'comparison'
RUNS = (recovery.OLD/recovery.v46.A,recovery.RUN)
BASE = '7b9e8413448215380ddc2f51fb74955039e1d625'
KEYS = ('O1','O2','N2','HE')
LIMIT, FLOOR, RATIO = .05, 1e-8, .95
EDGES = np.array([1e-8,1e-7,1e-6,1e-5,1e-4,1e-3,1e-2,1e-1,np.inf])
FIELDS = (*KEYS,'TN','UN','VN','DEN','ZG')
RANGES = json.loads(frozen.RULES.read_text())['latitude_regions']


def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def write(name, data):
    with (OUT/name).open('x', newline='') as f:
        if name.endswith('.csv'):
            w=csv.DictWriter(f,fieldnames=list(data[0]),lineterminator='\n')
            w.writeheader()
            w.writerows(data)
        else:
            json.dump(data,f,indent=2,allow_nan=False)
            f.write('\n')


def pin(path):
    expected=subprocess.check_output(['git','show',f'{BASE}:{path.relative_to(ROOT)}'],cwd=ROOT)
    assert path.read_bytes()==expected,path
    return json.loads(expected)


def gate(reference, new):
    finite=np.isfinite(reference)&np.isfinite(new)
    valid=finite&(reference>FLOOR)
    relative=np.divide(abs(new-reference),reference,out=np.full(reference.shape,np.nan),where=valid)
    return valid, relative<LIMIT, relative


def weighted95(x, weights):
    if not len(x):
        return None
    w=np.broadcast_to(weights,x.shape)
    return frozen.percentile(x.ravel(),w.ravel())


def read(n, name, i):
    v=n[name]
    data=np.asarray(v[i],dtype=float)
    for key in ('_FillValue','missing_value'):
        if key in v.ncattrs():
            flags=np.asarray(v.getncattr(key),dtype=v.dtype)
            data[np.isin(data,flags)]=np.nan
    data[abs(data)>1e30]=np.nan
    assert not np.isinf(data).any()
    return data


def schema(n):
    units={'DEN':'g/cm3','ZG':'cm','TN':'K','UN':'cm/s','VN':'cm/s'}
    for k in FIELDS:
        v=n[k]
        assert v.units==units.get(k,'mmr') and v.dimensions==('time','ilev' if k in ('DEN','ZG') else 'lev','lat','lon')
        v.set_auto_mask(False)
    return {k:np.asarray(n[k][:],dtype=float) for k in ('lat','lon','lev','ilev')}


def series(t):
    for volume in range(1,17):
        with ExitStack() as stack:
            a,b=[stack.enter_context(Dataset(p/f'secondary_{volume:03d}.nc')) for p in RUNS]
            grid=schema(a)
            assert all(np.array_equal(x,schema_b) for x,schema_b in zip(grid.values(),schema(b).values()))
            times=[]
            for n in (a,b):
                tv=n['time']
                times.append([x.isoformat() for x in num2date(tv[:],tv.units)])
            assert times[0]==times[1] and len(times[0])==24
            for i,utc in enumerate(times[0]):
                hour=(volume-1)*24+i+1
                assert utc==(recovery.START+timedelta(hours=hour)).isoformat()
                yield hour, utc+'Z', grid, {k:read(a,k,i) for k in FIELDS}, {k:read(b,k,i) for k in FIELDS}


def midpoint(v, lev, ilev, logarithmic=False):
    indices=np.searchsorted(ilev,lev,side='right')-1
    good=(indices>=0)&(indices+1<len(ilev))
    j=indices[good]
    weight=((lev[good]-ilev[j])/(ilev[j+1]-ilev[j]))[:,None,None]
    output=np.full((len(lev),*v.shape[1:]),np.nan)
    if logarithmic:
        assert np.all(v>0)
        output[good]=np.exp((1-weight)*np.log(v[j])+weight*np.log(v[j+1]))
    else:
        output[good]=(1-weight)*v[j]+weight*v[j+1]
    return output


def pearson(x,y):
    ok=np.isfinite(x)&np.isfinite(y)
    u,v=x[ok],y[ok]
    if len(u)<2 or np.ptp(u)==0 or np.ptp(v)==0:
        return len(u),None,None,None
    qx,qy=np.quantile(np.abs(u),.9),np.quantile(np.abs(v),.9)
    return len(u),float(np.corrcoef(u,v)[0,1]),float(np.mean(np.sign(u)==np.sign(v))),float(np.mean((abs(u)>=qx)&(abs(v)>=qy)))


def stats(a,b,z0,z1,rel,valid,passed,meta):
    x,y=a[valid],b[valid]
    d=y-x
    def q(x,p):
        return None if not len(x) else float(np.quantile(x,p))
    heights=[z[valid] for z in (z0,z1)]
    height_ranges=[(q(z[np.isfinite(z)],0),q(z[np.isfinite(z)],1)) for z in heights]
    return dict(**meta, n=int(valid.sum()),passed_n=int(passed.sum()),
        passed_fraction=float(passed.sum()/valid.sum()),failed_fraction=float(1-passed.sum()/valid.sum()),
        coverage=float(valid.mean()),floor_excluded=int(((a<=FLOOR)&np.isfinite(a)&np.isfinite(b)).sum()),
        near_floor_n=int((x<10*FLOOR).sum()),A_min=q(x,0),A_median=q(x,.5),A_P95=q(x,.95),
        B_median=q(y,.5),signed_mean=float(d.mean()),abs_median=q(abs(d),.5),abs_P95=q(abs(d),.95),
        relative_median=q(rel[valid],.5),relative_P95=q(rel[valid],.95),
        failing_median_ref=q(a[valid&~passed],.5),failing_median_abs=q(abs(b-a)[valid&~passed],.5),
        A_ZG_min_km=height_ranges[0][0],A_ZG_max_km=height_ranges[0][1],
        B_ZG_min_km=height_ranges[1][0],B_ZG_max_km=height_ranges[1][1])


def identity():
    manifest=pin(V48/'publication_SHA256.json')
    for name,d in manifest.items():
        assert recovery.sha(ROOT/name)==d,name
    result=pin(V48/'result.json')
    assert result['sensitivity']=='SEED_SENSITIVITY_FAIL' and result['run']['run_id']=='aff143997075432d896fe8acf88fc53e'
    a=recovery.a_snapshot()
    b=recovery.verify_engineering(recovery.RUN,recovery.protocol(),
                                 {row['file']:row['SHA256'] for row in result['run']['inventory']})
    assert a['run_id']==result['original_A_id']=='342ca7ee59a74a6aa600dd40f4459d91'
    assert b['run_id']==result['run']['run_id']
    v37=pin(ROOT/recovery.v45.V37)
    assert v37['first_pair']==['2021-06-21','2022-06-21'] and v37['candidates']['ShrinkageHalf']==.5
    rules=pin(frozen.RULES)
    assert [rules[k] for k in ('composition_relative_limit','trace_reference_floor_mmr','minimum_fraction_within_limits')]==[LIMIT,FLOOR,RATIO]
    return {'A':a,'B':b,'V48_manifest_entries':len(manifest),'GPI':result['GPI_sha256'],'ELF':result['model_sha256'],
            'historical_science':'SEED_SENSITIVITY_FAIL','frozen_rules_sha256':recovery.sha(frozen.RULES)}


def main():
    assert OUT.resolve()==OUT
    evidence=identity()
    write('identity.json',evidence)
    expected={(int(r['hour']),r['variable'],r['region'],int(r['level'])):r
              for r in rows(COMPARE/'gates.csv') if r['variable'] in KEYS}
    failed=[]; hourly=[]; profiles=[]; space=[]; associations=[]; paired=[]; scatter=[]; key_series=[]
    concentration=defaultdict(list)
    bin_contribution=defaultdict(lambda:[0,0,0])
    hot={(r['variable'],r['region'],int(r['level'])) for r in
         sorted((r for r in expected.values() if r['passed']=='False'),key=lambda r:float(r['passed_fraction']))[:20]}
    count=0
    for hour,utc,g,a,b in series(None):
        lat,lon,lev,ilev=(g[k] for k in ('lat','lon','lev','ilev'))
        cos=np.cos(np.deg2rad(lat))
        region_masks={k:(lat>=lo)&(lat<=hi) for k,(lo,hi) in RANGES.items()}
        era=hour>=360
        if era:
            heights=[midpoint(f['ZG'],lev,ilev)*1e-5 for f in (a,b)]
            den=[midpoint(f['DEN'],lev,ilev,True) for f in (a,b)]
            other={'TN':b['TN']-a['TN'],'wind_vector':np.hypot(b['UN']-a['UN'],b['VN']-a['VN'])/100,
                   'UN':(b['UN']-a['UN'])/100,'VN':(b['VN']-a['VN'])/100,
                   'ZG_km':heights[1]-heights[0],'log_DEN':np.log(den[1]/den[0])}
            lt=((hour%24)+lon/15)%24
        for key in KEYS:
            x,y=a[key],b[key]
            valid,passed,rel=gate(x,y)
            bins=np.digitize(x,EDGES)-1
            if era:
                z=valid
                concentration[key].append((x[z],(y-x)[z],rel[z],passed[z]))
            for region, mask in region_masks.items():
                sx,sy=x[:,mask],y[:,mask]
                sv,sp,sr=valid[:,mask],passed[:,mask],rel[:,mask]
                delta=sy-sx
                normal=np.broadcast_to(cos[None,mask,None],sx.shape)
                vnum=sv.sum(axis=(1,2)); pnum=sp.sum(axis=(1,2))
                n=int(sv.sum())
                mean_abs=float(np.average(abs(delta[sv]),weights=normal[sv]))
                hourly.append(dict(hour=hour,UTC=utc,variable=key,region=region,n=n,
                     signed_mean=float(np.average(delta[sv],weights=normal[sv])),MAE_mmr=mean_abs,
                     relative_mean=float(np.average(sr[sv],weights=normal[sv])),passed_fraction=float(sp.sum()/n),
                     relative_P95=weighted95(sr[sv],normal[sv]) if region=='global' or era else None,
                     abs_P95_mmr=weighted95(abs(delta[sv]),normal[sv]) if region=='global' else None))
                weights=np.where(sv,normal,0.)
                dsum=weights.sum(axis=(1,2))
                mr=np.divide(np.nansum(np.where(sv,sr*normal,0),axis=(1,2)),dsum,
                             out=np.full(len(lev),np.nan),where=dsum>0)
                ab=np.divide(np.nansum(np.where(sv,abs(delta)*normal,0),axis=(1,2)),dsum,
                             out=np.full(len(lev),np.nan),where=dsum>0)
                for i in range(len(lev)):
                    total,pn=int(vnum[i]),int(pnum[i])
                    frac=pn/total if total else None
                    if era:
                        old=expected[(hour,key,region,i)]
                        assert int(old['n'])==total and (old['passed_fraction']=='' if frac is None else
                             float(old['passed_fraction'])==frac and (old['passed']=='True')==(frac>=RATIO))
                        count+=1
                    if hour in (24,72,168,336) or hour>=337:
                        profiles.append(dict(hour=hour,UTC=utc,variable=key,region=region,level=i,lev_zp=lev[i],
                                             n=total,passed_n=pn,fraction=frac,
                                             MAE_mmr=float(ab[i]) if total else None,
                                             relative_mean=float(mr[i]) if total else None))
                    if (key,region,i) in hot:
                        key_series.append(dict(hour=hour,UTC=utc,variable=key,region=region,level=i,n=total,
                                               fraction=frac,MAE_mmr=float(ab[i]) if total else None,
                                               relative_mean=float(mr[i]) if total else None))
                    if not era or frac is None or frac>=RATIO:
                        continue
                    tag=dict(variable=key,UTC=utc,hour=hour,region=region,level=i,
                             lev_zp=lev[i],pressure_Pa=float(5e-5*np.exp(-lev[i])))
                    row=stats(sx[i],sy[i],heights[0][i,mask],heights[1][i,mask],sr[i],sv[i],sp[i],tag)
                    failed.append(row)
                    lab=bins[i,mask]
                    for k in range(len(EDGES)-1):
                        pts=(lab==k)&sv[i]
                        bad=pts&~sp[i]
                        v=bin_contribution[(key,k)]
                        v[0]+=int(pts.sum()); v[1]+=int(bad.sum()); v[2]+=int(bad.any())
                    for name, field in other.items():
                        num,corr,signed,colocated=pearson(np.where(sv[i],delta[i],np.nan),field[i,mask])
                        associations.append(dict(**tag,field=name,n=num,r=corr,same_sign=signed,
                                                 top_decile_overlap_fraction=colocated))
                    if region!='global':
                        for start in range(0,24,6):
                            lo=(lt>=start)&(lt<start+6)
                            masklt=sv[i][:,lo]; countlt=int(masklt.sum())
                            if countlt:
                                space.append(dict(**tag,LT_start=start,n=countlt,
                                                  failed_n=int((masklt&~sp[i][:,lo]).sum())))
                    if (key,region,i) in hot and key!='HE':
                        for j,k in np.argwhere(sv[i])[::17]:
                            scatter.append(dict(**tag,latitude=lat[mask][j],longitude=lon[k],
                                  A_mmr=sx[i,j,k],B_mmr=sy[i,j,k],absolute_mmr=abs(delta[i,j,k]),relative=sr[i,j,k]))
        if era:
            for key in KEYS:
                valid,passed,rel=gate(a[key],b[key])
                for latitude in lat[lat>0]:
                    for start in range(0,24,6):
                        sl=(lt>=start)&(lt<start+6)
                        si=np.where(lat==-latitude)[0].item()
                        ni=np.where(lat==latitude)[0].item()
                        sv,nv=valid[:,si,sl],valid[:,ni,sl]
                        m=sv&nv
                        for z in range(len(lev)):
                            nn=int(m[z].sum())
                            if nn:
                                paired.append(dict(hour=hour,UTC=utc,variable=key,abs_lat=latitude,LT_start=start,
                                    level=z,n=nn,south_P95=float(np.quantile(rel[z,si,sl][m[z]],.95)),
                                    north_P95=float(np.quantile(rel[z,ni,sl][m[z]],.95)),
                                    south_failed=int((~passed[z,si,sl]&m[z]).sum()),
                                    north_failed=int((~passed[z,ni,sl]&m[z]).sum())))
    assert len(failed)==2196 and count==len(expected)
    concentration_rows=[]; bins_units=[]
    for key, values in concentration.items():
        x,d,rel,p=np.concatenate([np.asarray(v) for v in values],axis=1)
        for i in range(len(EDGES)-1):
            subset=(x>=EDGES[i])&(x<EDGES[i+1])
            n=int(subset.sum())
            bad=subset&(p==0)
            quant=lambda z,r: float(np.quantile(z,r)) if len(z) else None
            concentration_rows.append(dict(variable=key,lo_mmr=EDGES[i],hi_mmr=None if np.isinf(EDGES[i+1]) else EDGES[i+1],
                n=n,failed_n=int(bad.sum()),passed_fraction=float(p[subset].mean()) if n else None,
                absolute_P50=quant(abs(d[subset]),.5),absolute_P95=quant(abs(d[subset]),.95),
                relative_P50=quant(rel[subset],.5),relative_P95=quant(rel[subset],.95),
                bad_median_abs=quant(abs(d[bad]),.5),signed_bias_mmr=float(d[subset].mean()) if n else None))
            pts,errors,units=bin_contribution[(key,i)]
            bins_units.append(dict(variable=key,lo_mmr=EDGES[i],hi_mmr=None if np.isinf(EDGES[i+1]) else EDGES[i+1],
                                  point_memberships=pts,failed_point_memberships=errors,failed_units_with_points=units))
    for name,data in [('failed_units',failed),('top20',sorted(failed,key=lambda x:x['passed_fraction'])[:20]),
                      ('hourly',hourly),('layer_time',profiles),('key_series',key_series),('failure_local_time',space),
                      ('associations',associations),('concentration_bins',concentration_rows),('bins_in_failed_units',bins_units),
                      ('concentration_scatter',scatter),('hemisphere_pairs',paired)]:
        write(name+'.csv',data)
    write('summary.json',dict(frozen_gate_result='SEED_SENSITIVITY_FAIL',reconstructed_component_units=count,
           failed_units=len(failed),diagnostics='EXPLORATORY_DIAGNOSTIC_RESULT',hours=384,window_inclusive=[360,384],
           floor=FLOOR,strict_threshold=LIMIT,min_pass_fraction=RATIO,
           units='composition mmr; midpoint internal ZG km; pressure Pa',
           midpoint='Interpolate within adjacent ilev in log-pressure coordinate; lev 28 unbracketed, no extrapolation.',
           significance='Associations only, no causal identification.',new_model_runs=0,unseen_target_density_reads=0,GPU=0))


if __name__=='__main__':
    main()
