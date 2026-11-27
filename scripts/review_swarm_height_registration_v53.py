"""Geometry-only eight-column screening and coordinate reference review."""
from collections import Counter
import csv
from datetime import timedelta
import json
import unittest

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from netCDF4 import Dataset, num2date
import numpy as np

import admit_swarm_summer_v53 as a
import verify_swarm_summer_v53 as verify
import analyze_summer_spinup_add7_v50 as v
from atmosphere.tiegcm_density_provider import TiegcmDensityProvider


def rows(year):
    with (a.OUT/f'metadata_{year}.csv').open(newline='') as f:
        return list(csv.DictReader(f))


def read_zg(path,indices,expected):
    with Dataset(path) as n:
        t=n['time']
        found=[q.isoformat() for q in num2date(t[indices],t.units)]
        assert found==[x.replace(tzinfo=None).isoformat() for x in expected]
        z=n['ZG']
        den=n['DEN']  # Metadata only.
        assert z.dimensions==den.dimensions==('time','ilev','lat','lon')
        assert z.units=='cm' and den.units=='g/cm3'
        z.set_auto_mask(False)
        x=np.asarray(z[indices],dtype=float)
        for attr in ('_FillValue','missing_value'):
            if attr in z.ncattrs():
                x[x==np.asarray(z.getncattr(attr),dtype=z.dtype)]=np.nan
        x[abs(x)>1e30]=np.nan
        return x*.01,np.asarray(n['lat'][:]),np.asarray(n['lon'][:])


def coverage(root,track):
    t=v.gpi.TARGET
    # 00Z is the final record in volume 21. The next volume provides 01Z through next midnight.
    first,lat,lon=read_zg(root/'secondary_021.nc',[-1],[t])
    after,y,x=read_zg(root/'secondary_022.nc',list(range(24)),[t+timedelta(hours=i) for i in range(1,25)])
    assert np.array_equal(lat,y) and np.array_equal(lon,x)
    z=np.concatenate((first,after),axis=0)
    out=[]
    for r in track:
        phi,lam,h=(float(r[k]) for k in ('latitude_deg','longitude_deg','altitude_m'))
        k=int(r['UTC'][11:13])
        fraction=(int(r['UTC'][14:16])*60+int(r['UTC'][17:19]))/3600
        lo=hi=None
        if not lat[0]<=phi<=lat[-1]:
            verdict='POLAR_CAP_UNSUPPORTED'
        else:
            j=int(np.clip(np.searchsorted(lat,phi,side='right')-1,0,len(lat)-2))
            lam=(lam-lon[0])%360+lon[0]
            i=int(np.searchsorted(lon,lam,side='right')-1)
            zz=np.stack([z[kk,:,jj,ii] for kk in (k,k+1) for jj in (j,j+1) for ii in (i,(i+1)%len(lon))])
            if not np.isfinite(zz).all() or not (np.diff(zz,axis=1)>0).all():
                verdict='INVALID_ZG_COLUMN'
            else:
                lo,hi=float(zz[:,0].max()),float(zz[:,-1].min())
                verdict='PROVISIONAL_ZG_BRACKET' if lo<=h<=hi else 'VERTICAL_OUTSIDE'
        out.append(dict(sample_id=r['sample_id'],UTC=r['UTC'],flag=r['validity_flag'],
             lower_hour=k,upper_hour=k+1,time_fraction=fraction,altitude_m=h,
             lower_common_ZG_m=lo,upper_common_ZG_m=hi,verdict=verdict))
    return out,dict(lat_centers_deg=[float(lat[0]),float(lat[-1])],
        lon_centers_deg=[float(lon[0]),float(lon[-1])],grid_shape=list(z.shape),
        frames=25,first_UTC=t.isoformat(),last_UTC=(t+timedelta(hours=24)).isoformat(),
        all=dict(Counter(r['verdict'] for r in out)),nominal=dict(Counter(r['verdict'] for r in out if r['flag']=='0')))


def source_audit():
    from verify_summer_handoff_v39 import Handoff,V38Fixtures
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(k) for k in (Handoff,V38Fixtures))
    result=unittest.TextTestRunner().run(suite)
    if not result.wasSuccessful():
        raise ValueError('Frozen synthetic fixture failure')
    # The density query methods reject before inspecting input/provider state.
    provider=object.__new__(TiegcmDensityProvider)
    provider.source='synthetic no field access'
    assert provider.query_external(object()).reason=='EXTERNAL_DATUM_UNVERIFIED'
    try:
        provider.density_kg_m3(object())
    except ValueError as exc:
        assert 'EXTERNAL_DATUM_UNVERIFIED' in str(exc)
    else:
        raise AssertionError('External provider unexpectedly admitted')
    protocol=a.ROOT/'experiments/thermosphere_shrinkage_unseen_prereg_v37/preregistered_protocol.json'
    from diagnose_summer_n2_residual_v52 import pin
    pin(protocol)
    rules=json.loads(protocol.read_text())
    assert rules['first_pair']==['2021-06-21','2022-06-21'] and rules['candidates']['ShrinkageHalf']==.5
    return result.testsRun


def main():
    import execute_summer_spinup_add7_v51 as run
    tracks={y:rows(y) for y in ('2021','2022')}
    model={}
    for role in 'AB':
        scan,model[role]=coverage(run.run_path(role),tracks['2022'])
        verify.save(f'provisional_ZG_coverage_{role}.csv',scan)
    tests=source_audit()
    a.write_once(a.OUT/'geometry_and_admission.json',dict(
        screening_status='PROVISIONAL_RAW_GEODETIC_NUMBERS_AS_NATIVE_NO_OFFSET_ZG_ONLY',
        model_2022=model,model_2021='BLOCKED_FOBS',Swarm_coordinates=dict(latitude='geodetic degrees',
        longitude='geodetic degrees UTC product',altitude='Altitude m, GRS80 ellipsoidal interpretation supported by product family; exact 0301 datum implementation, reference point and uncertainty unverified'),
        EXTERNAL_DATUM_UNVERIFIED=True,FIXED_OFFSET_NOT_ADMITTED=True,TARGET_DENSITY_SEALED=True,
        V37_FORMAL_SCORING_NOT_AUTHORIZED=True,formal_order=['2021','2022'],fobs_2021_missing=['2021-05-09','2021-06-16'],
        legacy_V51_science='SEED_SENSITIVITY_FAIL',density_limited='SUPPORTED',
        missing=['authenticated product provenance record','approved paired model/seed protocol',
                 'complete 2021 official drives and 2021 independently accepted model run',
                 'independent 0301 orbit frame and external-to-ZG registration',
                 'authorized history-only freeze at both cutoffs and synthetic poison verification',
                 'paired common identities and separate formal unlock/scoring authorization'],
        frozen_fixture_tests=tests,external_provider_negative_tests=2,
        target_density_reads=0,model_DEN_reads=0,model_runs=0,GPU=0,formal_scores=0))
    out=a.OUT/'figures'
    out.mkdir()
    font_manager.fontManager.addfont(a.ROOT/'data/presentation_assets/noto_sans_sc/NotoSansSC-400.ttf')
    plt.rcParams.update({'font.family':'Noto Sans SC','axes.unicode_minus':False})
    fig,ax=plt.subplots(2,2,figsize=(11,7))
    for i,(year,track) in enumerate(tracks.items()):
        lat,lon,h=[[float(r[k]) for r in track] for k in ('latitude_deg','longitude_deg','altitude_m')]
        ax[i,0].scatter(lon,lat,s=1)
        ax[i,0].set(title=f'{year}-06-21 大地坐标地面轨迹',xlabel='经度 (°)',ylabel='纬度 (°)')
        ax[i,1].plot(np.arange(len(h))/120,np.asarray(h)/1000,linewidth=.7)
        ax[i,1].set(title='产品原生轨道高度',xlabel='UTC 小时',ylabel='产品 altitude (km)')
    fig.text(.02,.01,'Swarm A DNSAPOD_2 0301 · 每日 n=2880 · 仅轨道几何与 UTC 元数据',fontsize=9)
    fig.tight_layout(rect=(0,.05,1,1))
    fig.savefig(out/'swarm_geometry.png',dpi=150)
    plt.close(fig)


if __name__=='__main__':
    main()
