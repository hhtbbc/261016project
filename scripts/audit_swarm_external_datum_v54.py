"""Read-only Swarm provenance, coordinate controls and model datum audit."""
import csv
import json
from pathlib import Path
import re
import subprocess
from xml.etree import ElementTree

import erfa
from cdflib import CDF
from netCDF4 import Dataset
import numpy as np

import admit_swarm_summer_v53 as handoff
import diagnose_summer_n2_residual_v52 as history
from audit_2021_gfz_revision_v54 import ROOT,OUT

BASE='9d5b89b6d84b64e00b5d4d1fa82483c5de0a0bdd'
V53=handoff.OUT
GRS80=(6378137.,1/298.257222101)
WGS84=(6378137.,1/298.257223563)
MODEL_SOURCES=('addiag.F','cons.F','diags.F','lbc.F')
SP3_NAME=re.compile(r'^SW_OPER_MODA_SC_1B_(20\d{6})T000000_\1T235959_0504\.sp3$')


def pinned(path):
    blob=subprocess.check_output(['git','show',f'{BASE}:{path.relative_to(ROOT)}'],cwd=ROOT)
    if path.read_bytes()!=blob:
        raise ValueError(f'Changed frozen file: {path}')
    return json.loads(blob)


def inputs():
    hashes=pinned(V53/'publication_SHA256.json')
    for path,digest in hashes.items():
        if history.run.sha(ROOT/path)!=digest:
            raise ValueError(f'V53 SHA mismatch: {path}')
    v52=ROOT/'experiments/thermosphere_summer_n2_residual_v52/publication_SHA256.json'
    prior=pinned(v52)
    for path,digest in prior.items():
        if history.run.sha(ROOT/path)!=digest:
            raise ValueError(f'V52 SHA mismatch: {path}')
    roots,old=history.identity()
    return roots,dict(V53=len(hashes),V52=len(prior),**old)


def validate_sp3_contract(name,day,metadata):
    """Check an independently documented contract before any SP3/CDF comparison."""
    if not SP3_NAME.fullmatch(name) or SP3_NAME.fullmatch(name)[1]!=day.replace('-',''):
        raise ValueError('Wrong MODA identity, date or version')
    if metadata.get('time_system') not in ('GPS','UTC','TAI') or metadata.get('position_unit')!='km':
        raise ValueError('Unsupported clock or SP3 position unit')
    if not all(isinstance(metadata.get(k),str) and metadata[k].strip() and
               metadata[k].strip().lower() not in ('unknown','itrf','unverified','n/a')
               for k in ('frame_realization','frame_epoch','point','reference_evidence')):
        raise ValueError('Exact frame, epoch and documented point required')
    if metadata['point']!=metadata.get('CDF_point'):
        raise ValueError('Mismatched reference point; documented correction required')


def products():
    result=[]
    for name,day in handoff.PRODUCTS.items():
        stem=Path(name).stem
        folder=handoff.handoff.HOME_DIR/'accepted'/name
        receipt=history.run.load(folder/'receipt.json')
        v53=next(x for x in history.run.load(V53/'independent.json')['products'] if x['day']==day)
        assert history.run.sha(ROOT/name)==history.run.sha(folder/name)==receipt['SHA256']==v53['SHA256']
        cdf=folder/(stem+'.cdf')
        hdr=folder/(stem+'.HDR')
        for p in (cdf,hdr):
            assert history.run.sha(p)==v53['members'][p.name]['SHA256']
        tree=ElementTree.parse(hdr)
        identifiers=[x.text for x in tree.findall('.//List_of_Input_File_Names/File_Name')]
        sp3,= [x for x in identifiers if SP3_NAME.fullmatch(x or '')]
        assert SP3_NAME.fullmatch(sp3)[1]==day.replace('-','')
        attrs=CDF(cdf).globalattsget()  # No data-array calls in this path.
        assert attrs['TITLE']==[stem] and attrs['SATELLITE']==['Swarm-A']
        assert tree.findtext('Fixed_Header/File_Version')=='0301'
        result.append(dict(day=day,zip=name,SHA256=receipt['SHA256'],SP3=sp3,
            input_names=identifiers,reference=tree.findtext('.//Ref_Doc'),
            creation_UTC=tree.findtext('Fixed_Header/Source/Creation_Date'),
            header_processing_time=tree.findtext('.//MPH/Proc_Time'),
            source='OFFICIAL_PROVENANCE_UNVERIFIED',catalogue_family='ESA Swarm PDGS MODx_SC ITRF/SP3-c',
            orbit_status='SP3_EXACT_PRODUCT_NOT_ACQUIRED',SP3_FORMAT_DOCUMENTED=True,
            exact_SP3_time_system=None,exact_ITRF=None,frame_epoch=None,spacecraft_reference_point=None,
            exact_SP3_interval=None,paired_XYZ_samples=0,official_exact_checksum=None))
    return result


def forward(lon,lat,height,ellipsoid):
    a,f=ellipsoid
    e2=f*(2-f)
    phi,lam=np.deg2rad(lat),np.deg2rad(lon)
    N=a/np.sqrt(1-e2*np.sin(phi)**2)
    return np.stack(((N+height)*np.cos(phi)*np.cos(lam),(N+height)*np.cos(phi)*np.sin(lam),
                     (N*(1-e2)+height)*np.sin(phi)),axis=-1)


def quantify(lon,lat,h):
    xyz=forward(lon,lat,h,GRS80)
    a,f=GRS80
    u,v,w=erfa.gc2gde(a,f,xyz)
    erfa_xyz=erfa.gd2gce(a,f,np.deg2rad(lon),np.deg2rad(lat),h)
    ww,ff=WGS84
    _,lat_w,h_w=erfa.gc2gde(ww,ff,xyz)
    gc=np.rad2deg(np.arctan2(xyz[:,2],np.hypot(xyz[:,0],xyz[:,1])))
    def summary(x):
        x=np.abs(x)
        return dict(max=float(x.max()),P95=float(np.percentile(x,95)))
    return dict(samples=len(h),forward_disagreement_m=summary(np.linalg.norm(xyz-erfa_xyz,axis=1)),
        roundtrip_XYZ_m=summary(np.linalg.norm(xyz-forward(np.rad2deg(u),np.rad2deg(v),w,GRS80),axis=1)),
        roundtrip_lat_deg=summary(np.rad2deg(v)-lat),
        roundtrip_lon_deg=summary((np.rad2deg(u)-lon+180)%360-180),
        roundtrip_height_m=summary(w-h),same_XYZ_GRS80_to_WGS84_height_m=summary(h_w-h),
        same_XYZ_GRS80_to_WGS84_lat_deg=summary(np.rad2deg(lat_w)-lat),
        geocentric_vs_geodetic_lat_deg=summary(gc-lat))


def geodesy():
    tracks={}
    for year in (2021,2022):
        with (V53/f'metadata_{year}.csv').open(newline='') as f:
            rows=list(csv.DictReader(f))
        tracks[str(year)]=quantify(*[np.array([float(x[key]) for x in rows])
            for key in ('longitude_deg','latitude_deg','altitude_m')])
    return dict(CDF_geometry_as_GRS80_assumption=tracks,independent_SP3_control_points=0,
        synthetic=quantify(np.array([0.,180.,-179.,51.,-90.]),np.array([0.,90.,-80.,43.,-90.]),
                           np.array([0.,700000.,435000.,450000.,499000.])),
        error_bound_scope='numerical calculation only; external datum/realization error unbounded')


def model(roots):
    preflight=ROOT/'experiments/thermosphere_summer_seed_policy_config_v45/preflight.json'
    baseline=pinned(preflight)['critical_assets']
    hashes={}
    for name in MODEL_SOURCES:
        p=f'third_party/TIEGCM2.0/src/{name}'
        hashes[p]=history.run.sha(ROOT/p)
        assert hashes[p]==baseline[p]
    anchors={}
    for role,root in zip('AB',roots):
        paths=[(root/'secondary_021.nc',[-1]),(root/'secondary_022.nc',list(range(24)))]
        bottom=[]
        for path,ii in paths:
            with Dataset(path) as n:
                z,zg,den=[n[k] for k in ('Z','ZG','DEN')]
                assert z.dimensions==zg.dimensions==den.dimensions==('time','ilev','lat','lon')
                assert (z.units,zg.units,den.units)==('cm','cm','g/cm3')
                z.set_auto_mask(False)
                zg.set_auto_mask(False)
                lower=np.asarray(z[ii,0],dtype=float)
                assert np.isfinite(lower).all() and (abs(lower)<1e30).all()
                assert np.array_equal(lower,zg[ii,0])
                bottom.append(lower*.01)
        samples=np.concatenate(bottom)
        lat=np.asarray([-87.5,0.,87.5])
        c2=np.cos(2.*1.74533e-2*lat)
        r0=2*980.616*(1-.0026373*c2)/(3.085462e-6+2.27e-9*c2)
        anchors[role]=dict(anchor_hours=len(samples),points=int(samples.size),max_Z_ZG_difference_m=0,
            bottom_min_m=float(samples.min()),bottom_max_m=float(samples.max()),
            gravity_radius_km_at_latitude=list(r0/1e5))
    return dict(source_SHA256=hashes,anchor=anchors,external_control_points=0,external_height_bound_m=None,
        registration='EXTERNAL_DATUM_UNVERIFIED',DEN_values_read=0)


def main():
    assert OUT.resolve()==OUT
    roots,evidence=inputs()
    history.run.write_once(OUT/'external_audit.json',dict(historical=evidence,products=products(),geodesy=geodesy(),
        model=model(roots),product_access='STOPPED_BEFORE_DOWNLOAD_AT_ESA_TERMS',
        Swarm_density_reads=0,Swarm_density_orbitmean_reads=0,new_model_runs=0,GPU=0,formal_scores=0))


if __name__=='__main__':
    main()
