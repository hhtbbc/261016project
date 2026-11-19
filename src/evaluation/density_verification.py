"""Independent read-only arithmetic for a frozen prediction contract, no fitting API."""
from pathlib import Path
import csv,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
RTOL=1e-13
ATOL=0.0
BANDS=('low','mid','high')
WINDOWS={'analysis':(-3,0),'future_1h':(0,1),'future_3h':(0,3),'future_6h':(0,6),'block_0_1h':(0,1),'block_1_3h':(1,3),'block_3_6h':(3,6)}
METRICS=('MAE','RMSE','bias','relative_RMS','relative_P95','relative_bias','log_RMS','Pearson','max_abs')
FLAGS=('RMSE_BENEFIT','RELATIVE_RMS_BENEFIT','TAIL_NONWORSENED','LOW_LATITUDE_BIAS_NONWORSENED')

def require(ok,message):
    if not bool(ok):raise ValueError(message)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(2**20),b''):h.update(block)
    return h.hexdigest()

def check_sha(path,expected):require(sha(path)==expected,'SHA mismatch: '+str(path))

def write_json(directory,name,value):
    """Only the new V19 tree, exclusively; source/historical directories rejected."""
    root=ROOT/'experiments/tiegcm_2022_mar25_independent_verification_v19'
    directory=Path(directory);directory.resolve().relative_to(root.resolve())
    p=directory/name;p.resolve().relative_to(root.resolve())
    with p.open('x') as f:json.dump(value,f,indent=2,allow_nan=False)

def reserve(directory):
    p=Path(directory);p.resolve().relative_to(ROOT/'experiments/tiegcm_2022_mar25_independent_verification_v19');p.mkdir(exist_ok=False)

def band(latitude):
    a=np.asarray(latitude,float);require(np.isfinite(a).all() and (abs(a)<=90).all(),'Invalid latitude')
    return np.where(abs(a)<30,0,np.where(abs(a)<60,1,2))

def window(utc,hour,name,day='2022-03-25'):
    t=np.asarray(utc,dtype='datetime64[ns]');require(not np.isnat(t).any(),'Invalid UTC');require(hour in (6,18) and name in WINDOWS,'Unregistered window')
    lo,hi=WINDOWS[name];d=(t-np.datetime64(day+f'T{hour:02d}','ns'))/np.timedelta64(1,'h')
    return (d>=lo)&(d<hi)

def id_sha(utc):return hashlib.sha256(np.asarray(utc,dtype='datetime64[ns]').astype('<i8').tobytes()).hexdigest()

def sample_sha(utc,latitude,observed,raw):
    h=hashlib.sha256()
    for x,typ in [(np.asarray(utc,dtype='datetime64[ns]').astype('int64'),'<i8'),(latitude,'<f8'),(observed,'<f8'),(raw,'<f8')]:h.update(np.asarray(x,dtype=typ).tobytes())
    return h.hexdigest()

def require_ids(actual,expected):require(np.array_equal(np.asarray(actual),np.asarray(expected)),'Common sample identity mismatch')

def numeric(main,independent):
    a,b=float(main),float(independent);require(np.isfinite([a,b]).all(),'Nonfinite/missing metric')
    diff=abs(a-b);limit=RTOL*abs(b)+ATOL
    return dict(main=a,independent=b,absolute_difference=diff,relative_difference=diff/abs(b) if b!=0 else (0. if a==0 else None),allowed_absolute_difference=limit,rtol=RTOL,atol=ATOL,PASS=bool(np.isclose(a,b,rtol=RTOL,atol=ATOL)))

def prediction(raw,latitude,parameters,hour,method):
    """No exponent function is called here: only original frozen multipliers."""
    raw=np.asarray(raw,float);require(raw.ndim==1 and np.isfinite(raw).all() and (raw>0).all(),'Invalid raw density')
    bb=band(latitude);require(raw.shape==bb.shape,'Aligned coordinates required')
    if method=='Raw':return raw.copy(),np.ones(len(raw),bool)
    if method=='LatitudeAdaptive18':
        require(hour==18,'Unregistered method/cutoff');out=np.full(raw.shape,np.nan);support=np.zeros(len(raw),bool)
        for i,k in enumerate(BANDS):
            c=parameters['LatitudeAdaptive18'][k];m=bb==i
            if c['status']=='SUPPORTED' and c['N']>=30:
                factor=float(c['multiplier']);require(np.isfinite(factor) and factor>0,'Invalid multiplier');out[m]=raw[m]*factor;support[m]=True
        return out,support
    require((hour==6 and method=='GlobalAdaptive06') or (hour==18 and method in ('GlobalAdaptive18','Stale06')),'Unregistered method/cutoff')
    key='GlobalAdaptive06' if method=='Stale06' else method;c=parameters[key]
    require(c['status']=='SUPPORTED' and c['N']>=30,'Unsupported history');factor=float(c['multiplier']);require(np.isfinite(factor) and factor>0,'Invalid multiplier')
    return raw*factor,np.ones(len(raw),bool)

def statistics(predicted,observed):
    p,o=np.asarray(predicted,float),np.asarray(observed,float)
    require(p.ndim==1 and p.shape==o.shape,'Aligned metric vectors required');require(np.isfinite(p).all() and np.isfinite(o).all() and (p>0).all() and (o>0).all(),'Invalid metric inputs')
    if len(p)<30:return {k:None for k in METRICS}
    error=p-o;relative=error/o
    return dict(MAE=float(np.mean(abs(error))),RMSE=float(np.sqrt(np.mean(error*error))),bias=float(np.mean(error)),relative_RMS=float(np.sqrt(np.mean(relative*relative))),relative_P95=float(np.quantile(abs(relative),.95)),relative_bias=float(np.mean(relative)),log_RMS=float(np.sqrt(np.mean(np.log(p/o)**2))),Pearson=float(np.corrcoef(p,o)[0,1]) if np.std(p)>0 and np.std(o)>0 else None,max_abs=float(abs(error).max()))

def joint(raw,corrected,raw_low,corrected_low,adequate=True):
    if not adequate:return dict(**{k:None for k in FLAGS},JOINT_NO_REGRET='N/A_INSUFFICIENT_SAMPLES')
    f=dict(RMSE_BENEFIT=corrected['RMSE']<raw['RMSE'],RELATIVE_RMS_BENEFIT=corrected['relative_RMS']<raw['relative_RMS'],TAIL_NONWORSENED=corrected['relative_P95']<=raw['relative_P95'],LOW_LATITUDE_BIAS_NONWORSENED=abs(corrected_low['relative_bias'])<=abs(raw_low['relative_bias']))
    return dict(**f,JOINT_NO_REGRET='PASS' if all(f.values()) else 'FAIL')

def check_metric_fields(row):
    require(all(k in row for k in METRICS),'Missing metric field')
    if row['status']=='OK':
        for k in METRICS:
            if k=='Pearson' and row[k] in ('',None):continue
            numeric(row[k],row[k])
