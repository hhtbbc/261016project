"""Canonical POD records reusing the audited0301 reader; reserved B remains unread."""
from pathlib import Path
import re,json,hashlib
import numpy as np
from evaluation.swarm_density_comparison import quality_mask

class ReservedObservationError(ValueError):pass

def enforce_value_access(satellite):
    if satellite=='B':raise ReservedObservationError('Swarm B is reserved; metadata only in this protocol')
    if satellite not in ('A','C'):raise ValueError('Only audited Swarm A/C POD values supported')

def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()

def read_swarm_pod(path,info_path,expected_sha,*,satellite):
    enforce_value_access(satellite)  # before opening any density file
    path=Path(path);match=re.fullmatch(r'SW_OPER_DNS([ABC])POD_2__\d{8}T\d{6}_\d{8}T\d{6}_(\d{4})',path.stem)
    if not match or match.group(1)!=satellite or match.group(2)!='0301':raise ValueError('Only verified matching0301 POD supported')
    if file_sha(path)!=expected_sha:raise ValueError('Observation SHA mismatch')
    info=json.loads(Path(info_path).read_text());product=f'SW_OPER_DNS{satellite}POD_2_';params={x['name']:x for x in info['parameters']}
    if info['x_dataset']!=product or params['validity_flag']['description']!='0 = nominal data, 1 = anomalous data' or params['density']['units']!='kg/m3' or 'GRS80' not in params['Latitude_GD']['description']:raise ValueError('Product-specific metadata contract mismatch')
    # Existing reader implements CDF_EPOCH->UTC, instantaneous density/units and0301quality.
    from scripts.run_swarm_tiegcm_2022_observation import read_observation
    a,contract=read_observation(path)
    if contract['global_attributes']['TITLE']!=[path.stem]:raise ValueError('CDF identity does not match file')
    if len(a['utc'])==0 or np.isnat(a['utc']).any() or np.any(np.diff(a['utc'])<=np.timedelta64(0,'ns')):raise ValueError('Missing, duplicate or reversed UTC')
    coord=np.isfinite(a['latitude'])&np.isfinite(a['longitude'])&np.isfinite(a['altitude'])&(abs(a['latitude'])<=90)&(abs(a['longitude'])<=180)&(a['altitude']>0)
    a['quality']=a['quality']&coord
    rows=[]
    for i,t in enumerate(a['utc']):
        utc=str(t)+'Z';rows.append(dict(observation_id=f'Swarm/{satellite}/0301/{utc}',mission='Swarm',satellite=satellite,product_id=product,product_version='0301',UTC=utc,latitude=float(a['latitude'][i]),longitude=float(a['longitude'][i]),height=float(a['altitude'][i]),density_kg_m3=float(a['density'][i]),validity_flag=int(a['validity_flag'][i]),quality_valid=bool(a['quality'][i]),source_file=str(path),source_SHA256=expected_sha,coordinate_reference='GRS80 geodetic product contract; ellipsoid height m',density_retrieval_method='POD/GPS-acceleration-derived instantaneous density; not orbit mean'))
    return rows,a,contract

def calibration_time_mask(utc,cutoff_UTC,history_hours=3,*,satellite='A'):
    """Time-only leakage guard for future plans; does not fit or apply corrections."""
    enforce_value_access(satellite)
    if satellite!='A':raise ValueError('Only A is calibration input in the frozen first-stage plan')
    if not str(cutoff_UTC).endswith('Z') or history_hours<=0:raise ValueError('Explicit UTC cutoff and positive history required')
    end=np.datetime64(str(cutoff_UTC)[:-1],'ns');t=np.asarray(utc,dtype='datetime64[ns]')
    return (t>=end-np.timedelta64(int(history_hours*3600),'s'))&(t<end)
