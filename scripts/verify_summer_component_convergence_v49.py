"""Independent bulk-read V49 verification, without using the diagnosis reader."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from netCDF4 import Dataset, num2date
import numpy as np

import preflight_summer_seed_recovery_v47 as recovery
import verify_summer_seed_sensitivity_v46 as verifier
from verify_summer_seed_execution_v48_quantile import historical_order_quantile

ROOT=recovery.ROOT
RUNS=(recovery.OLD/recovery.v46.A,recovery.RUN)
OUT=ROOT/'experiments/thermosphere_summer_component_convergence_v49'
OLD=recovery.OUT/'comparison'
RULE=ROOT/'experiments/tiegcm_2021_spinup_14day_v1/frozen_comparison_rules.json'
START=recovery.START
C=('O1','O2','N2','HE')


def table(p):
    with p.open() as f:
        return list(csv.DictReader(f))


def read_batch(run,k):
    with Dataset(run/f'secondary_{k:03d}.nc') as n:
        tv=n['time']
        times=[t.isoformat()+'Z' for t in num2date(tv[:],tv.units)]
        lat,lon,lev,ilev=(np.asarray(n[s][:],dtype=float) for s in ('lat','lon','lev','ilev'))
        data={}
        for s in (*C,'TN','UN','VN','DEN','ZG'):
            v=n[s]
            units={'TN':'K','UN':'cm/s','VN':'cm/s','DEN':'g/cm3','ZG':'cm'}
            assert v.dimensions==('time','ilev' if s in units and s in ('DEN','ZG') else 'lev','lat','lon')
            assert v.units==units.get(s,'mmr')
            v.set_auto_mask(False)
            raw=np.asarray(v[:],dtype='f8')
            missing=abs(raw)>1e30
            for key in ('missing_value','_FillValue'):
                if key in v.ncattrs():
                    missing|=np.isin(raw,np.asarray(v.getncattr(key),dtype=v.dtype))
            assert np.isfinite(raw).all(), s
            raw[missing]=np.nan
            data[s]=raw
    return times,(lat,lon,lev,ilev),data


def validate():
    proof=json.loads((OUT/'identity.json').read_text())
    for run,key in zip(RUNS,('A','B')):
        for p,h in proof[key]['inventory'].items():
            assert recovery.sha(run/p)==h
        assert recovery.load(recovery.receipt_path(run,'claim'))['run_id']==proof[key]['run_id']
    assert recovery.sha(RULE)==proof['frozen_rules_sha256']
    rules=json.loads(RULE.read_text())
    regions=rules['latitude_regions']
    refs={(int(r['hour']),r['variable'],r['region'],int(r['level'])):r for r in table(OLD/'gates.csv')}
    h_refs={(int(r['hour']),int(r['height_km']),r['region']):r for r in table(OLD/'height_gates.csv')}
    failed={(int(r['hour']),r['variable'],r['region'],int(r['level'])):r for r in table(OUT/'failed_units.csv')}
    hourlies={(int(r['hour']),r['variable'],r['region']):r for r in table(OUT/'hourly.csv')}
    geo={(int(r['hour']),r['variable'],r['region'],int(r['level']),r['field']):r
         for r in table(OUT/'associations.csv')}
    paired=defaultdict(list)
    for r in table(OUT/'hemisphere_pairs.csv'):
        paired[int(r['hour'])].append(r)
    bins={k:[] for k in C}
    hourly_count=gate_count=bin_checks=point_checks=assoc_checks=0
    reconstructed=set()
    for k in range(1,17):
        ta,ga,aa=read_batch(RUNS[0],k)
        tb,gb,bb=read_batch(RUNS[1],k)
        assert ta==tb and all(np.array_equal(x,y) for x,y in zip(ga,gb))
        lat,lon,lev,ilev=ga
        w=np.cos(lat*np.pi/180)
        for j,t in enumerate(ta):
            hour=(k-1)*24+j+1
            assert t==(START+timedelta(hours=hour)).isoformat()+'Z'
            a,b=({s:v[j] for s,v in f.items()} for f in (aa,bb))
            hourmask={}
            for var in C:
                x,y=a[var],b[var]
                valid=np.isfinite(x)&np.isfinite(y)&(x>1e-8)
                ratio=np.full_like(x,np.nan)
                ratio[valid]=np.abs(y[valid]-x[valid])/x[valid]
                pass_pt=ratio<.05
                hourmask[var]=(valid,ratio,pass_pt)
                if hour>=360:
                    bins[var].append((x[valid],(y-x)[valid],ratio[valid],pass_pt[valid]))
                for region,(lo,hi) in regions.items():
                    sel=(lat>=lo)&(lat<=hi)
                    ok=valid[:,sel]
                    rr=ratio[:,sel][ok]
                    d=y[:,sel][ok]-x[:,sel][ok]
                    ws=np.broadcast_to(w[None,sel,None],ok.shape)[ok]
                    row=hourlies[(hour,var,region)]
                    assert int(row['n'])==len(rr)
                    assert np.isclose(float(row['MAE_mmr']),np.sum(ws*abs(d))/sum(ws),rtol=5e-11,atol=1e-17)
                    assert np.isclose(float(row['relative_mean']),np.sum(ws*rr)/sum(ws),rtol=5e-11,atol=1e-14)
                    assert np.isclose(float(row['signed_mean']),np.sum(ws*d)/sum(ws),rtol=5e-11,atol=1e-16)
                    if row['relative_P95']:
                        assert np.isclose(float(row['relative_P95']),historical_order_quantile(rr,ws),rtol=5e-11)
                    assert float(row['passed_fraction'])==int(pass_pt[:,sel].sum())/len(rr)
                    hourly_count+=1
            if hour<360:
                continue
            a['WIND_VECTOR']=np.zeros_like(a['UN'])
            b['WIND_VECTOR']=np.sqrt((a['UN']-b['UN'])**2+(a['VN']-b['VN'])**2)
            for var in (*C,'DEN','TN','WIND_VECTOR'):
                for region,(lo,hi) in regions.items():
                    sel=(lat>=lo)&(lat<=hi)
                    x,y=a[var][:,sel],b[var][:,sel]
                    for z,(xx,yy) in enumerate(zip(x,y)):
                        v=np.isfinite(xx)&np.isfinite(yy)
                        if var in (*C,'DEN'):
                            v&=xx>(1e-8 if var in C else 0)
                        d=yy[v]-xx[v]
                        if var in (*C,'DEN'):
                            threshold=.05
                            error=np.abs(d/xx[v])
                        else:
                            threshold=10 if var=='TN' else 2000
                            error=np.abs(d)
                        key=(hour,var,region,z)
                        old=refs[key]
                        assert int(old['n'])==len(error)
                        gate_count+=1
                        if not len(error):
                            assert not old['passed'] and not old['passed_fraction']
                            continue
                        pn=int(np.count_nonzero(error<threshold))
                        frac=pn/len(error)
                        assert old['passed']==str(frac>=.95) and float(old['passed_fraction'])==frac
                        if frac>=.95:
                            continue
                        reported=failed[key]
                        reconstructed.add(key)
                        assert reported['UTC']==t and int(reported['passed_n'])==pn
                        assert int(reported['n'])==len(error) and float(reported['passed_fraction'])==frac
                        for col,value in {'coverage':v.mean(),'A_median':np.median(xx[v]),
                            'B_median':np.median(yy[v]),'abs_P95':np.quantile(abs(d),.95),
                            'relative_P95':np.quantile(error,.95),'signed_mean':d.mean()}.items():
                            assert np.isclose(float(reported[col]),value,rtol=2e-12,atol=1e-17)
                        if z+1<len(ilev):
                            assert ilev[z]<lev[z]<ilev[z+1]
                            l=(lev[z]-ilev[z])/(ilev[z+1]-ilev[z])
                            za,zb=[(f['ZG'][z,sel]*(1-l)+f['ZG'][z+1,sel]*l)*1e-5 for f in (a,b)]
                            assert np.isclose(float(reported['A_ZG_min_km']),za[v].min()) and np.isclose(
                                float(reported['B_ZG_max_km']),zb[v].max())
                            dx=np.log(b['DEN'][z,sel]/a['DEN'][z,sel])*(1-l)+np.log(
                                b['DEN'][z+1,sel]/a['DEN'][z+1,sel])*l
                        else:
                            assert reported['A_ZG_min_km']==reported['B_ZG_max_km']==''
                            za=zb=dx=np.full_like(xx,np.nan)
                        fields={'TN':b['TN'][z,sel]-a['TN'][z,sel],
                            'wind_vector':b['WIND_VECTOR'][z,sel]/100,
                            'UN':(b['UN'][z,sel]-a['UN'][z,sel])/100,
                            'VN':(b['VN'][z,sel]-a['VN'][z,sel])/100,
                            'ZG_km':zb-za,'log_DEN':dx}
                        for name,f in fields.items():
                            entry=geo[(*key,name)]
                            u=(yy-xx)[v&np.isfinite(f)]
                            wv=f[v&np.isfinite(f)]
                            assert int(entry['n'])==len(u)
                            u0=u-u.mean() if len(u) else u
                            w0=wv-wv.mean() if len(wv) else wv
                            norm=np.linalg.norm(u0)*np.linalg.norm(w0)
                            if norm and np.ptp(u) and np.ptp(wv):
                                assert np.isclose(float(entry['r']),np.dot(u0,w0)/norm,atol=2e-12)
                                assert np.isclose(float(entry['same_sign']),np.mean(np.sign(u)==np.sign(wv)))
                                u9,w9=np.quantile(abs(u),.9),np.quantile(abs(wv),.9)
                                assert np.isclose(float(entry['top_decile_overlap_fraction']),np.mean((abs(u)>=u9)&(abs(wv)>=w9)))
                            else:
                                assert not entry['r'],entry
                            assoc_checks+=1
            for r in paired[hour]:
                v,ratio,p=hourmask[r['variable']]
                ab=float(r['abs_lat']);z=int(r['level']);l=int(r['LT_start'])
                lt=((hour%24)+lon/15)%24
                sel=(lt>=l)&(lt<l+6)
                si,ni=np.where(lat==-ab)[0].item(),np.where(lat==ab)[0].item()
                m=v[z,si,sel]&v[z,ni,sel]
                assert int(r['n'])==m.sum()
                for k2,i in [('south',si),('north',ni)]:
                    assert int(r[k2+'_failed'])==int((~p[z,i,sel]&m).sum())
                    assert np.isclose(float(r[k2+'_P95']),np.quantile(ratio[z,i,sel][m],.95),rtol=1e-13)
                point_checks+=1
            for h in rules['common_native_ZG_heights_km']:
                x,y=[verifier.interpolate_columns(d,h) for d in (a,b)]
                for region,(lo,hi) in regions.items():
                    sel=(lat>=lo)&(lat<=hi)
                    xx,yy=x[sel],y[sel]
                    finite=np.isfinite(xx)&np.isfinite(yy)
                    old=h_refs[(hour,h,region)]
                    assert finite.sum()==int(old['n'])
                    fraction=float(np.mean(abs((yy[finite]-xx[finite])/xx[finite])<.05))
                    assert fraction==float(old['passed_fraction']) and old['passed']==str(fraction>=.95)
                    gate_count+=1
    assert reconstructed==set(failed) and len(reconstructed)==2196 and gate_count==len(refs)+len(h_refs)
    for row in table(OUT/'concentration_bins.csv'):
        k=row['variable'];lo=float(row['lo_mmr']);hi=float(row['hi_mmr']) if row['hi_mmr'] else np.inf
        ref,delta,rel,pass_flag=np.concatenate([np.vstack(z) for z in bins[k]],axis=1)
        sel=(ref>=lo)&(ref<hi);n=sel.sum()
        assert int(row['n'])==n and int(row['failed_n'])==(sel&(pass_flag==0)).sum()
        if n:
            assert float(row['passed_fraction'])==pass_flag[sel].mean()
            for col,vec,p in [('relative_P95',rel,.95),('absolute_P95',abs(delta),.95),
                              ('absolute_P50',abs(delta),.5),('relative_P50',rel,.5)]:
                assert np.isclose(float(row[col]),np.quantile(vec[sel],p),rtol=1e-13)
        bin_checks+=1
    # Negative checks lock the strict bound, floor and Greenwich LT convention.
    x=np.array([1e-8,1.00001e-8,0.5,0.5])
    y=np.array([2e-8,1.00001e-8,0.525,0.5249])
    use=x>1e-8
    assert use.tolist()==[False,True,True,True]
    assert (abs(y[use]-x[use])/x[use]<.05).tolist()==[True,False,True]
    assert ((np.array([-180,0,90,180])/15)%24).tolist()==[12,0,6,12]
    output={'state':'PASS','run_ids':[proof[k]['run_id'] for k in ('A','B')],
          'files_SHA256_verified':66,'all_frozen_cells_rechecked':gate_count,
          'failures_exactly_reproduced':len(reconstructed),'V49_hour_region_rows':hourly_count,
          'matched_hemisphere_rows':point_checks,'concentration_bins':bin_checks,'association_rows':assoc_checks,
          'strict_floor_relative_and_LT_negative_controls':'PASS','no_swarm_density':True,'new_runs':0,'GPU':0}
    with (OUT/'independent.json').open('x') as f:json.dump(output,f,indent=2)


if __name__=='__main__':
    validate()
