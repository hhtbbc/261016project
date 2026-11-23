"""Inspect ZG source identities and representative NetCDF headers only."""
import time
import numpy as np
from netCDF4 import Dataset

from stability_zg_v32 import ROOT, OUT, E, V30, baseline, load, require, sha, table, resource_log, write_once

V2=E/'tiegcm_zg_external_registration_v2'
V21=E/'tiegcm_zg_external_registration_v2_1'
SRC='third_party/TIEGCM2.0/src/'
PACKAGE=E/'thermosphere_autumn_mareqx_config_v23'
MAP='src/atmosphere/provisional_coordinate_adapter.py'
PROVIDER='src/atmosphere/tiegcm_density_provider.py'


def trusted_source(name,expected,token):
    p=ROOT/name
    require(p.resolve(strict=True)==p and sha(p)==expected,'Source SHA drift: '+name)
    require(token in p.read_text(),'Expected source definition missing: '+name)
    return expected


def header(path):
    with Dataset(path,'r') as n:
        result=dict(variables={},p0_mbar=float(n['p0'][...]),
                    p0_model_microbar=float(n['p0_model'][...]),
                    native_model_version=n.model_version,
                    lat_count=len(n.dimensions['lat']),lon_count=len(n.dimensions['lon']),
                    ilev=n['ilev'][:].tolist(),lev=n['lev'][:].tolist())
        for key in ('ZG','Z','DEN','TN','lat'):
            if key in n.variables:
                v=n[key]
                result['variables'][key]=dict(unit=v.units,dimensions=list(v.dimensions),
                                             long_name=v.long_name,dtype=str(v.dtype))
        return result


def review():
    start=time.perf_counter()
    require(OUT.resolve()==OUT,'Unexpected output path')
    pins={}
    for p in [*V2.glob('*.json'),*V2.glob('*.csv'),*V21.glob('*.json'),*(V21/'external_share').glob('*'),
              ROOT/'reports/TIEGCM_ZG_EXTERNAL_REGISTRATION_PACKAGE_V2.md',
              ROOT/'reports/TIEGCM_ZG_EXTERNAL_REGISTRATION_PACKAGE_V2_1.md',
              ROOT/'docs/TIEGCM_ZG_EXTERNAL_REGISTRATION_REQUEST_V2.md',
              ROOT/'docs/TIEGCM_ZG_EXTERNAL_REGISTRATION_REQUEST_V2_1.md']:
        if p.is_file() and '_local' not in p.name:
            pins[str(p.relative_to(ROOT))]=baseline(p)
    release=PACKAGE/'execution_release.json'
    pins[str(release.relative_to(ROOT))]=baseline(release)
    frozen=load(release)['scientific_asset_SHA256']
    excerpts={r['file']:r['SHA256'] for r in __import__('csv').DictReader((V2/'source_chain_excerpts.csv').read_text().splitlines())
              if r['file'].startswith(SRC)}
    specs=[
        ('pressure_vertical_coordinate',SRC+'cons.F','init_cons; official grid altitude notes',
         'P0 = 5x10-4 dyn/cm2; Zp=ln(P0/P); interface spacing 0.5','dimensionless',
         'P0 pressure reference; no physical height zero follows','SOURCE_CONFIRMED',
         'Pressure indices cannot be equated to orbit altitude','Version-matched official mapping', 'zbound'),
        ('ZG_definition',SRC+'addiag.F','calczg, lines 221–282',
         'ZG(lev0)=Z(lev0); integrate kT dz/(mean particle mass*g); top linear extension','cm on ilev',
         'Lower anchor inherited from Z; external zero absent','SOURCE_CONFIRMED',
         'Use variable-gravity geometric diagnostic; Z is separate constant-gravity height',
         'External zero reference and latitude-specific registration','Geometric Height ZG'),
        ('DEN_registration',SRC+'diags.F','diags registration lines 72–76',
         'Total Density registered directly at interface levels','g/cm3 on ilev',
         'Co-layer with ZG; kg/m3 requires ×1000','SOURCE_CONFIRMED','No midpoint conversion by assumption',
         'Confirm external ZG placement independently',"diags(n)%short_name = 'DEN'"),
        ('lower_boundary_reference',SRC+'cons.F','init_cons line 315',
         'zbound=136.291/sqrt(2)*1e5; default roughly 96.37229 km','cm',
         'Background Z boundary; geodetic surface unspecified','SOURCE_CONFIRMED',
         'Do not treat default height as spatially invariant or zero definition','Absolute reference surface','136.291/sqrt'),
        ('GSWM_boundary',SRC+'lbc.F','lbc lines 105–159',
         'When ibgrddata=0 initialize z_lbc=zbound; configured tidal terms add perturbations','cm',
         'Background Z plus tides; follows lower boundary physics','SOURCE_CONFIRMED',
         'Instantaneous boundary can vary in time and horizontal space',
         'Independent datum documentation including tidal linkage',' = zbound'),
        ('gravity_radius',SRC+'addiag.F','calczg lines 249–268',
         'g0=980.616(1−0.0026373 cos(2glat)); r0 fit to gravity gradient; inverse square update','cm/s2; cm',
         'Effective radius used for gravity, independent ellipsoid registration not given','SOURCE_CONFIRMED',
         'Using r0 as an Earth ellipsoid semimajor axis would change physical meaning',
         'Explicit version-specific connection to terrestrial ellipsoid','effective earth radius'),
        ('model_latitude_mapping',SRC+'getapex.F','getapex lines 124–145',
         'glat=ylatg*rtd; pass to apex_mall at hs=130 km','degrees; km',
         'Magnetic auxiliary convention; model geographic-latitude registration is inferred',
         'INFERRED_ONLY','Potential geodetic/geocentric distinction affects neighbors',
         'Authoritative model-grid latitude convention separate from apex','glat = ylatg'),
        ('external_zero',SRC+'addiag.F','calczg',
         'No version-specific relation of native ZG zero to GRS80/WGS84 established','cm versus m',
         'External datum unverified','EXTERNAL_UNVERIFIED','Vertical offset can affect log-density interpolation',
         'Version-specific zero, ellipsoid or geopotential definition, scope and independent anchor','zg(lev0,i,j) = z(lev0,i,j)'),
        ('Map_A',MAP,'ProvisionalCoordinateAdapter coordinates/query',
         'GRS80 to XYZ to WGS84; assume WGS84 geodetic lat and ellipsoid h match native model coordinates',
         'degrees and metres','Numerical hypothesis only; offset 0 conditional',
         'INTERNAL_NUMERIC_CONFIRMED','Prior 2880 eight-column queries per year confirmed domain only',
         'Independent datum/latitude relation and error bound','height + self.height_offset_m'),
        ('provider_external_gate',PROVIDER,'external query and native query',
         'Reject external coordinate calls until datum validation','m','External identity denied',
         'EXTERNAL_UNVERIFIED','Formal routing remains blocked','Version and bounded physical mapping before new interface',
         'EXTERNAL_DATUM_UNVERIFIED'),
    ]
    matrix=[]
    for key,name,fn,formula,units,surface,level,impact,gap,token in specs:
        expected=frozen.get(name,excerpts.get(name))
        if expected is None:expected=baseline(ROOT/name)
        digest=trusted_source(name,expected,token);pins[name]=digest
        matrix.append(dict(field=key,source_path=name,function=fn,source_SHA256=digest,formula=formula,
            native_units=units,reference_surface=surface,evidence_level=level,impact=impact,needed=gap))
    for ref in load(V2/'official_source_inventory.json')['sources']:
        cached=ref.get('cached')
        if ref['id'] in ('NCAR_GRID','NCAR_ALTITUDE_PDF') and cached:
            require(sha(ROOT/cached['path'])==cached['SHA256'],'Changed cached official evidence')
            pins[cached['path']]=cached['SHA256']
    source=load(V30/'source_manifest.json')['years']
    native={}
    for key,info in source.items():
        warm=next(a for a in info['full_model'] if a['file']=='secondary_015.nc')
        item=info['frozen_inputs']['source']
        for label,entry in [('seed',item),('warm',warm)]:
            path=ROOT/entry['path']
            if entry['path'] not in pins:
                require(sha(path)==entry['SHA256'],'Changed sampled NetCDF')
                pins[entry['path']]=entry['SHA256']
            native[f'{key}_{label}']=dict(path=entry['path'],SHA256=entry['SHA256'],**header(path))
        a,b=native[f'{key}_seed'],native[f'{key}_warm']
        require(a['lev']==b['lev'] and a['ilev']==b['ilev'] and a['p0_mbar']==b['p0_mbar'],
                'Seed/warm pressure grid mismatch')
        require('ZG' not in a['variables'] and a['variables']['Z']['unit']=='cm',
                'Unexpected seed height inventory')
        require(b['variables']['ZG']['unit']=='cm' and b['variables']['DEN']['unit']=='g/cm3'
                and b['variables']['DEN']['dimensions']==b['variables']['ZG']['dimensions']==['time','ilev','lat','lon'],
                'Native ZG/DEN mismatch')
        for pathkey in ('input','hapi'):
            ent=info['frozen_inputs'][pathkey];p=ROOT/ent['path']
            require(sha(p)==ent['SHA256'],'Changed input/observation contract')
            pins[ent['path']]=ent['SHA256']
        require("GSWM" in (ROOT/info['frozen_inputs']['input']['path']).read_text(),'Missing frozen GSWM input')
    hapi=source['2022']['hapi']
    c=load(ROOT/hapi['path'])
    require(c['x_dataset']=='SW_OPER_DNSAPOD_2_' and any('GRS80' in f.get('description','') for f in c['parameters']),
            'Wrong HAPI GRS80 contract')
    matrix.append(dict(field='Swarm_GRS80',source_path=hapi['path'],function='VirES HAPI contract; V21 CDF 0301',
        source_SHA256=hapi['SHA256'],formula='GRS80 product latitude/longitude/ellipsoid height',
        native_units='degrees / m',reference_surface='GRS80 product convention; exact frame realization and retrieval uncertainty unresolved',
        evidence_level='SOURCE_CONFIRMED',impact='Observation coordinate contract does not assign TIE-GCM ZG zero',
        needed='Product uncertainty, detailed realization and independent model registration'))
    table(OUT/'zg_evidence_matrix.csv',matrix)
    write_once(OUT/'zg_native_headers.json',native)
    write_once(OUT/'zg_review_receipt.json',dict(status='ZG_EVIDENCE_REVIEW_COMPLETE',
        external_datum='EXTERNAL_DATUM_UNVERIFIED',new_coordinate_tests=0,model_queries=0,
        files_rechecked=pins,representative_warm_headers=2,distinct_seed_headers=1,
        no_external_contact=True,resource=resource_log(start)))


if __name__=='__main__':
    review()
