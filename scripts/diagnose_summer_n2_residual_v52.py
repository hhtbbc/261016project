"""Read-only diagnostics for the published V51 N2 failures."""
import csv
from collections import Counter
from datetime import timedelta
import json
import subprocess

import numpy as np
from netCDF4 import Dataset

import analyze_summer_spinup_add7_v50 as v
import diagnose_summer_component_convergence_v49 as old
import execute_summer_spinup_add7_v51 as run

ROOT = v.ROOT
OUT = ROOT/'experiments/thermosphere_summer_n2_residual_v52'
V51 = run.OUT
BASE = '5c0c3e690316cb121be73132c382058b61c09210'
MODEL_FLOOR = float(np.float32(1e-6))
FLOOR_TOL = float(8*np.spacing(np.float32(MODEL_FLOOR)))
COMP = ('O1','O2','HE')


def csv_rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def save(name, rows):
    v.science.csv_save(OUT/name, rows)


def pin(path):
    expected = subprocess.check_output(['git','show',f'{BASE}:{path.relative_to(ROOT)}'],cwd=ROOT)
    if path.read_bytes() != expected:
        raise ValueError(f'Frozen asset changed: {path}')


def identity():
    manifest = V51/'publication_SHA256.json'
    pin(manifest)
    for p,digest in run.load(manifest).items():
        if run.sha(ROOT/p)!=digest:
            raise ValueError(f'V51 publication SHA changed: {p}')
    history = run.frozen()
    roots,ids = v.evidence()
    config = run.load(v.OUT/'configuration.json')
    for role,root in zip('AB',roots):
        p = run.protocol(role)
        if run.sha(root/'input.inp') != p['input']['SHA256']:
            raise ValueError('Runtime input SHA mismatch')
    return roots,dict(V50_history=history, V51_run_ids=ids,V51_native_volumes=94,
                      V51_manifest_files=len(run.load(manifest)), configuration=config['config_sha'],
                      source_sha=[p['SHA256'] for p in config['seeds']],GPI=config['GPI'],ELF=config['model'])


def gate(a,b):
    valid = np.isfinite(a)&np.isfinite(b)&(np.abs(a)>1e-8)
    delta = b-a
    relative = np.divide(np.abs(delta),np.abs(a),out=np.full(a.shape,np.nan),where=valid)
    passed = valid&(relative<.05)
    return valid,passed,relative,delta


def q(x,p):
    finite=x[np.isfinite(x)]
    return float(np.percentile(finite,p)) if len(finite) else None


def region_mask(grid, rules, region):
    low,high=rules['latitude_regions'][region]
    return (grid[0]>=low)&(grid[0]<=high)


def frame(roots,t):
    return v.read_frame(roots,t,independent=True)


def value_counts(ref,other,valid,failed):
    a=np.abs(ref-MODEL_FLOOR)<=FLOOR_TOL
    b=np.abs(other-MODEL_FLOOR)<=FLOOR_TOL
    masks={'both':a&b,'A_only':a&~b,'B_only':~a&b,'neither':~a&~b}
    return {f'{k}_{label}':int((m&subset).sum()) for k,m in masks.items()
            for label,subset in [('valid',valid),('fail',failed)]}


def step(roots,t,targets,rules):
    a,b,g=frame(roots,t)
    lat,lon,lev,ilev=g
    valid,passed,relative,delta=gate(a['N2'],b['N2'])
    out=[]
    for region,level in targets:
        m=region_mask(g,rules,region)
        va,pa,re,de=[x[level,m] for x in (valid,passed,relative,delta)]
        largest=np.unravel_index(np.nanargmax(re),re.shape) if va.any() else None
        out.append(dict(UTC=t.isoformat(),hour=int((t-v.gpi.START).total_seconds()/3600),
            region=region,level=level,n=int(va.sum()),passed=int(pa.sum()),
            fraction=float(pa.sum()/va.sum()) if va.any() else None,
            relative_P95=q(re,95),absolute_P95=q(np.where(va,abs(de),np.nan),95),
            A_median=q(a['N2'][level,m][va],50),
            worst_lat=float(lat[m][largest[0]]) if largest else None,
            worst_lon=float(lon[largest[1]]) if largest else None))
    return out


def main():
    if OUT.resolve()!=OUT:
        raise ValueError('Unsafe output path')
    roots,ids=identity()
    run.write_once(OUT/'identity.json',ids)
    pin(v.science.RULES)
    rules=run.load(v.science.RULES)
    expected={(r['UTC'],r['region'],int(r['level'])):r for r in csv_rows(V51/'same_UTC_native_gates.csv')
              if r['variable']=='N2' and r['gate_21']=='False'}
    targets=sorted({(r,z) for _,r,z in expected})
    details=[]; assoc=[]; times=[]; points=[]; sectors=[]; unique=Counter(); worst_grid=[]
    start=v.LATE_UTC[0]
    selected={v.gpi.START+timedelta(days=i) for i in (7,14,17,19,20,21)}
    selected.update(start+timedelta(hours=i) for i in range(-48,25))
    selected.add(v.gpi.TARGET+timedelta(hours=22))
    for t in sorted(selected-set(v.LATE_UTC)):
        times.extend(step(roots,t,targets,rules))
    for t in v.LATE_UTC:
        a,b,g=frame(roots,t)
        lat,lon,lev,ilev=g
        valid,passed,relative,delta=gate(a['N2'],b['N2'])
        failed=valid&~passed
        used=np.zeros_like(failed)
        zg=[old.midpoint(x['ZG'],lev,ilev)*1e-5 for x in (a,b)]
        den=[old.midpoint(x['DEN'],lev,ilev,logarithmic=True) for x in (a,b)]
        changes={k:b[k]-a[k] for k in (*COMP,'TN','UN','VN')}
        changes.update(ZG=zg[1]-zg[0],log_DEN=np.log(den[1]/den[0]))
        pred=-sum(changes[k] for k in COMP)
        budget=sum(np.spacing(np.abs(x[k]).astype('f4')).astype(float)*.5 for x in (a,b) for k in (*COMP,'N2'))
        for region,level in targets:
            m=region_mask(g,rules,region)
            key=(t.isoformat(),region,level)
            va,pa,fa,re,de=[x[level,m] for x in (valid,passed,failed,relative,delta)]
            ar,br=[x['N2'][level,m] for x in (a,b)]
            fraction=pa.sum()/va.sum() if va.any() else np.nan
            if va.any() and fraction<.95:
                if key not in expected:
                    raise ValueError(f'Mismatched failure key {key}')
            if key not in expected:
                continue
            row=expected[key]
            assert int(row['n_21'])==va.sum() and float(row['fraction_21'])==fraction
            used[level,m] |= fa
            counts=value_counts(ar,br,va,fa)
            near=va&((abs(ar-MODEL_FLOOR)<=FLOOR_TOL)|(abs(br-MODEL_FLOOR)<=FLOOR_TOL))
            reconstruction=pred[level,m]-de
            details.append(dict(UTC=key[0],region=region,level=level,variable='N2',
                n=int(va.sum()),passed=int(pa.sum()),failed=int(fa.sum()),fraction=float(fraction),
                fraction14=float(row['fraction_14']),A_min=q(ar[va],0),A_median=q(ar[va],50),
                A_max=q(ar[va],100),B_min=q(br[va],0),B_median=q(br[va],50), B_max=q(br[va],100),
                relative_max=q(re,100),relative_P95=q(re,95),absolute_P95=q(abs(de[va]),95),
                near_relative_P95=q(re[near],95),away_relative_P95=q(re[va&~near],95),
                A_ZG_min_km=q(zg[0][level,m][va],0),A_ZG_max_km=q(zg[0][level,m][va],100),
                B_ZG_min_km=q(zg[1][level,m][va],0),B_ZG_max_km=q(zg[1][level,m][va],100),
                residual_error_max=q(abs(reconstruction[fa]),100),
                residual_within_output_rounding=int((fa&(abs(reconstruction)<=budget[level,m]+4e-15)).sum()),
                **counts))
            h=np.broadcast_to((t.hour+lon/15)%24,ar.shape)
            for lo in range(0,24,3):
                window=(h>=lo)&(h<lo+3)
                sectors.append(dict(UTC=key[0],region=region,level=level,local_solar_hour=lo,
                                    valid=int((va&window).sum()),failed=int((fa&window).sum())))
            for name,x in (changes|{'residual':pred}).items():
                d=x[level,m]
                for label,sel in [('valid',va),('failed',fa),('near_failed',fa&near),('away_failed',fa&~near)]:
                    common=sel&np.isfinite(d)
                    n,r,sign,colocation=old.pearson(de[common],d[common])
                    assoc.append(dict(UTC=key[0],region=region,level=level,field=name,subset=label,
                        n=n,r=r,same_sign=sign,top_decile_overlap=colocation,
                        delta_abs_P95=q(abs(d[common]),95)))
            if region=='south_polar' and level==26 and t.hour in (10,22):
                for i,j in zip(*np.where(va)):
                    worst_grid.append(dict(UTC=key[0],lat=float(lat[m][i]),lon=float(lon[j]),level=level,
                        A=float(ar[i,j]),B=float(br[i,j]),relative=float(re[i,j]),failed=int(fa[i,j]),
                        near_A=int(abs(ar[i,j]-MODEL_FLOOR)<=FLOOR_TOL),near_B=int(abs(br[i,j]-MODEL_FLOOR)<=FLOOR_TOL),
                        delta_N2=float(de[i,j]),delta_O1=float(changes['O1'][level,m][i,j]),
                        delta_O2=float(changes['O2'][level,m][i,j]),delta_HE=float(changes['HE'][level,m][i,j])))
        counts=value_counts(a['N2'],b['N2'],used,used)
        unique.update({k:n for k,n in counts.items() if k.endswith('_fail')})
        for i,j,k in zip(*np.where(used)):
            points.append((a['N2'][i,j,k],relative[i,j,k]))
        times.extend(step(roots,t,targets,rules))
    assert {(d['UTC'],d['region'],d['level']) for d in details}==set(expected) and len(details)==118
    for name, data in [('failures',details),('top30',sorted(details,key=lambda x:x['fraction'])[:30]),
                       ('regional_time_series',sorted(times,key=lambda x:(x['UTC'],x['region'],x['level']))),
                       ('associations',assoc),('local_time',sectors),('polar_lev26_grid',worst_grid)]:
        save(name+'.csv',data)
    # Persist a compact scatter sample on a fixed stride.
    save('failed_points_scatter.csv',[dict(A_mmr=float(x),relative=float(y)) for x,y in points[::4]])
    run.write_once(OUT/'diagnostics.json',dict(model_floor=MODEL_FLOOR,tolerance=FLOOR_TOL,
        acceptance_floor=1e-8, counts_by_region=dict(Counter(x['region'] for x in details)),
        counts_by_level=dict(Counter(x['level'] for x in details)),unique_failed_grid_hours=unique,
        total_failed_grid_hours=sum(unique.values()), region_point_instances=sum(x['failed'] for x in details),
        reconstruction_within_output_rounding=sum(x['residual_within_output_rounding'] for x in details),
        V51_science='SEED_SENSITIVITY_FAIL'))


if __name__=='__main__':
    main()
