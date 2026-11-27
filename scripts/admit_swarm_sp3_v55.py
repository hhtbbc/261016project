"""Accept an exact, documented MODA 0504 candidate without releasing science gates."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile

import erfa
import numpy as np
from astropy.time import Time

from audit_swarm_external_datum_v54 import GRS80, ROOT, V53, validate_sp3_contract
from audit_2021_gfz_revision_v54 import OUT as V54
from evaluation.sp3_reader import read_sp3
from import_summer_handoff_v39 import open_bounded, snapshot
from orbit.frames import configure_time_data, gps_calendar_to_time
from runtime.tiegcm_rank_exit import write_once

HANDOFF=ROOT/'data/raw/thermosphere_external_handoff_v55'
STAGING=HANDOFF/'staging'
ACCEPTED=HANDOFF/'accepted'
CAP=20*2**20


def targets():
    rows=json.loads((V54/'external_audit.json').read_text())['products']
    return {r['SP3']:r['day'] for r in rows}


def safe_directory(directory):
    if not directory.is_dir() or directory.resolve(strict=True)!=directory or not directory.is_relative_to(HANDOFF):
        raise ValueError(f'Unsafe handoff directory: {directory}')
    return directory


def bounded_json(path):
    safe_directory(path.parent)
    s,_=open_bounded(path,64*1024)
    with s:
        return json.load(s)


def convert_clock(labels,system):
    if system=='GPS':
        return gps_calendar_to_time(labels)
    if system not in ('UTC','TAI'):
        raise ValueError('Unknown time system')
    return Time(labels,format='datetime',scale=system.lower()).utc


def validate(path,meta,*,check_time_data=True):
    expected=targets()
    if path.name not in expected:
        raise ValueError('Only the exact HDR-referenced 0504 names are allowed')
    safe_directory(path.parent)
    validate_sp3_contract(path.name,expected[path.name],meta)
    if meta.get('satellite')!='Swarm A' or not isinstance(meta.get('satellite_record_id'),str):
        raise ValueError('Documented Swarm A satellite identifier required')
    if not meta.get('reference_evidence') or not meta.get('source_url'):
        raise ValueError('Source and reference evidence required')
    from urllib.parse import urlsplit
    url=urlsplit(meta['source_url'])
    if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('Use a public HTTPS description without credentials or query')
    s,size=open_bounded(path,CAP)
    with s:
        raw=s.read(CAP+1)
    if len(raw)!=size or not raw.rstrip().endswith(b'EOF'):
        raise ValueError('Truncated or changing SP3')
    sha=hashlib.sha256(raw).hexdigest()
    if meta.get('sha256')!=sha:
        raise ValueError('Declared SHA and file bytes disagree')
    orbit=read_sp3(path)
    if (orbit.version,orbit.satellite_id,orbit.time_system,orbit.frame)!=(
            'c',meta['satellite_record_id'],meta['time_system'],meta.get('SP3_frame_code')):
        raise ValueError('SP3 header and documented contract differ')
    header=raw.decode('ascii').splitlines()
    fields=header[0][3:31].split()
    from datetime import timedelta
    header_start=datetime(*map(int,fields[:5]))+timedelta(seconds=float(fields[5]))
    sat_lines=[row for row in header if row.startswith('+') and not row.startswith('++')]
    declared=[row[i:i+3].strip() for row in sat_lines for i in range(9,len(row),3)]
    if (header_start!=orbit.epochs[0] or not sat_lines or int(sat_lines[0][3:6])!=1
            or [x for x in declared if x not in ('','0')]!=[orbit.satellite_id]):
        raise ValueError('First epoch or satellite list inconsistent with records')
    first=datetime.fromisoformat(expected[path.name])
    step=orbit.interval_s
    if not np.isfinite(step) or step<=0 or not np.isclose(86400%step,0,atol=1e-8):
        raise ValueError('Unsupported sampling interval')
    if not isinstance(meta.get('expected_interval_s'),(int,float)) or step!=meta['expected_interval_s']:
        raise ValueError('Sampling interval differs from documented contract')
    mode=meta.get('filename_day_scale')
    if mode not in ('UTC',orbit.time_system):
        raise ValueError('Documented filename calendar scale required')
    if check_time_data:
        configure_time_data()
    utc=convert_clock(orbit.epochs,orbit.time_system)
    origin=convert_clock([first],mode)[0]
    relative=(utc-origin).sec
    if len(relative)!=round(86400/step) or not np.allclose(relative,np.arange(len(relative))*step,rtol=0,atol=2e-6):
        raise ValueError('Incomplete named day in the documented filename calendar')
    if np.any(np.linalg.norm(orbit.positions_m,axis=1)<6e6):
        raise ValueError('Position inconsistent with a Swarm orbit in kilometres')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
        raise ValueError('SP3 bytes changed during reading')
    return orbit,utc,dict(file=path.name,bytes=size,SHA256=sha,frame_code=orbit.frame,
        time_system=orbit.time_system,interval_s=step,records=len(utc),first_UTC=utc[0].isot+'Z',
        last_UTC=utc[-1].isot+'Z',declared_frame=meta['frame_realization'],declared_point=meta['point'],
        scope='SP3_BYTES_AND_STRUCTURE_ONLY',official_provenance='UNVERIFIED',geometry='NOT_AUTHORIZED_BY_INGEST')


def compare_geometry(orbit,utc,rows):
    """Exact UTC intersection, for already adjudicated same-frame reference points."""
    if not rows:
        raise ValueError('No CDF geometry rows')
    from audit_swarm_external_datum_v54 import forward
    from verify_swarm_external_datum_v54 import inverse_iterative
    from astropy import units as u
    t=Time([r['UTC'].removesuffix('Z') for r in rows],format='isot',scale='utc')
    delta=(utc-utc[0]).to_value(u.s)
    queries=(t-utc[0]).to_value(u.s)
    nn=np.searchsorted(delta,queries-1e-6)
    indices=np.minimum(nn,len(delta)-1)
    matched=(nn<len(delta))&(np.abs(delta[indices]-queries)<1e-6)
    if not matched.any():
        raise ValueError('No exact-UTC intersection; interpolation not implied')
    chosen=np.flatnonzero(matched)
    xyz=orbit.positions_m[indices[matched]]
    lam,phi,h=erfa.gc2gde(*GRS80,xyz)
    independent=inverse_iterative(xyz,*GRS80)
    if np.max(np.abs(h-independent[2]))>1e-6:
        raise ValueError('Independent coordinate computation disagrees')
    back=forward(np.rad2deg(lam),np.rad2deg(phi),h,GRS80)
    out=[]
    for k,i in enumerate(chosen):
        item=rows[i]
        out.append(dict(sample_id=item['sample_id'],UTC=item['UTC'],
            dt_s=float(delta[indices[i]]-queries[i]),
            latitude_error_deg=float(np.rad2deg(phi[k])-float(item['latitude_deg'])),
            longitude_error_deg=float((np.rad2deg(lam[k])-float(item['longitude_deg'])+180)%360-180),
            altitude_error_m=float(h[k]-float(item['altitude_m'])),
            XYZ_roundtrip_m=float(np.linalg.norm(back[k]-xyz[k]))))
    return out


def admit(name):
    if name not in targets() or Path(name).name!=name:
        raise ValueError('Use exact basename from the accepted HDR')
    safe_directory(STAGING)
    safe_directory(ACCEPTED)
    source=STAGING/name
    destination=ACCEPTED/name
    if os.path.lexists(destination):
        raise FileExistsError(f'Accepted name already exists: {destination}')
    meta=bounded_json(STAGING/(name+'.source.json'))
    lock=ACCEPTED/('.lock-'+name)
    lock.mkdir()
    try:
        with tempfile.TemporaryDirectory(dir=ACCEPTED,prefix='.v55-') as tmp:
            stage=Path(tmp)
            staged=stage/name
            _,sha=snapshot(source,staged,CAP)
            _,_,receipt=validate(staged,meta)
            if receipt['SHA256']!=sha:
                raise ValueError('Snapshot mismatch')
            write_once(stage/'receipt.json',receipt)
            write_once(stage/'source_claim.json',meta)
            for path in stage.iterdir():
                path.chmod(0o444)
            if os.path.lexists(destination):
                raise FileExistsError(str(destination))
            os.rename(stage,destination)
            destination.chmod(0o555)
    finally:
        lock.rmdir()
    return receipt


def compare_accepted(name):
    """Compare geometry after separate adjudication of frame and spacecraft point."""
    if name not in targets():
        raise ValueError('Unknown geometry target')
    folder=safe_directory(ACCEPTED/name)
    sidecar=bounded_json(folder/'source_claim.json')
    orbit,clock,receipt=validate(folder/name,sidecar)
    if bounded_json(folder/'receipt.json')!=receipt:
        raise ValueError('Accepted receipt does not match the present bytes')
    approval=bounded_json(STAGING/(name+'.geometry_review.json'))
    day=targets()[name]
    from audit_swarm_external_datum_v54 import pinned
    product=next(p for p in json.loads((V54/'external_audit.json').read_text())['products'] if p['day']==day)
    required={'scope':'V55_GEOMETRY_ONLY','approved':True,'SP3_SHA256':receipt['SHA256'],
              'CDF_zip_SHA256':product['SHA256'],'same_frame_and_epoch':True,
              'same_spacecraft_point':True,'input_ellipsoid':'GRS80'}
    if any(approval.get(k)!=value for k,value in required.items()) or not approval.get('independent_evidence_ref'):
        raise ValueError('Independent same-frame/point geometry adjudication required')
    table=V53/f'metadata_{day[:4]}.csv'
    manifest=pinned(V53/'publication_SHA256.json')
    if hashlib.sha256(table.read_bytes()).hexdigest()!=manifest[str(table.relative_to(ROOT))]:
        raise ValueError('Frozen CDF geometry manifest hash mismatch')
    with table.open(newline='') as f:
        points=compare_geometry(orbit,clock,list(csv.DictReader(f)))
    numeric=[k for k in points[0] if k not in ('UTC','sample_id')]
    return dict(kind='SOURCE_SIDE_ONLY', control_points=len(points), rows=points,
                statistics={k:dict(max_abs=float(np.max(np.abs([p[k] for p in points]))),
                      p95_abs=float(np.percentile(np.abs([p[k] for p in points]),95))) for k in numeric},
                gates_automatically_released=0,density_reads=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name',choices=tuple(targets()))
    parser.add_argument('--compare-accepted',action='store_true',help='Read-only geometry after separate adjudication')
    args=parser.parse_args()
    out=compare_accepted(args.name) if args.compare_accepted else admit(args.name)
    print(json.dumps(out,indent=2))


if __name__=='__main__':
    main()
