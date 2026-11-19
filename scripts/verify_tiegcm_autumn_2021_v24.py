"""V24 independent read-only review. No model API, fitting, scoring or main-PASS reuse."""
from pathlib import Path
import sys,json,re,math,time,datetime,collections,resource
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R)]
import numpy as np,cdflib
from netCDF4 import Dataset,num2date
from astropy.coordinates import EarthLocation
import astropy.units as u
from runtime.tiegcm_rank_exit import digest,write_once
from atmosphere.autumn_gpi_validation import read_raw,independent_at,stamp
F=R/'experiments/thermosphere_autumn_2021_formal_run_v24';BASE=R/'experiments/thermosphere_autumn_mareqx_config_v23/2021';RUN=BASE/'actual_run'
START=datetime.datetime(2021,9,9);STOP=datetime.datetime(2021,9,25);TARGET=datetime.datetime(2021,9,23)
def require(ok,message):
    if not ok:raise ValueError(message)
def load(p):return json.loads(Path(p).read_text())
def raw(v,i,allow_mask=False):
    v.set_auto_mask(False);a=np.asarray(v[i]);mask=abs(a)>1e30
    for key in ['missing_value','_FillValue']:
        if key in v.ncattrs():
            for z in np.asarray(v.getncattr(key)).reshape(-1):mask|=a==np.asarray(z,dtype=a.dtype)
    require(np.isfinite(a).all(),'Nonfinite native '+v.name)
    if not allow_mask:require(not mask.any(),'Fill/missing native '+v.name)
    return a.astype(float),mask

def secondary_schema(n,primary_schema):
    result={}
    for key in ['TN','UN','VN','O1','O2','N2','HE']:
        require(key in n.variables,'Missing secondary variable '+key)
        v=n[key];unit=primary_schema[key][1] if key!='N2' else 'mmr'
        require(v.dimensions==('time','lev','lat','lon') and v.dtype.kind=='f' and getattr(v,'units',None)==unit,'Secondary schema/unit/dtype mismatch '+key)
        result[key]=dict(dimensions=list(v.dimensions),units=v.units,dtype=str(v.dtype))
    return result

def review():
    wall=time.perf_counter();cpu=time.process_time();notes={};p=load(BASE/'launch_protocol.json');claim=load(BASE/'execution_claim_local.json');status=load(RUN/'status.json')
    main=load(BASE/'postrun_audit_local/acceptance.json') if (BASE/'postrun_audit_local/acceptance.json').exists() else None
    require(p['year']==claim['year']==2021 and claim['attempts']==1 and not claim['automatic_retry'],'Wrong year/launch claim')
    require(status['returncode']==0 and status['qualification']=='PASS' and status['cleanup_verified'] and not status['gaps'] and status['wait_source']=='direct subprocess.Popen.wait','MPI parent/supervision not complete')
    require(status['stop_reason'] is None and status['elapsed_s']<=4800,'Model resource/stop failure')
    events=[json.loads(l) for l in (RUN/'events.jsonl').read_text().splitlines()];wait=[a for a in events if a['event']=='child_wait_final'];launched=[a for a in events if a['event']=='launched']
    require(len(wait)==len(launched)==1 and wait[0]['returncode']==0 and wait[0]['cleanup_verified'] and launched[0]['identity']==status['identity'],'Direct wait journal mismatch')
    once=load(RUN/'launch_once.json');require(once['launch_count']==1,'More than one model launch')
    ranks=[]
    for rank in range(4):
        a=load(RUN/f'rank_{rank:03d}_started.json');b=load(RUN/f'rank_{rank:03d}_exit.json')
        require(b['run_id']==claim['run_id'] and b['rank']==rank and b['size']==4 and all(b[k]==v for k,v in a.items()),'Rank identity mismatch')
        require(b['returncode']==0 and b['error'] is None and not b['received_signals'] and b['wrapper_sid']==b['child_sid']==status['identity']['sid'],'Rank actual exit/session failed')
        require(b['wait_source']=='direct subprocess.Popen.wait' and b['model_SHA256']==p['executable']['SHA256'] and b['input_SHA256']==p['input']['SHA256'],'Rank direct wait/input mismatch')
        text=(RUN/f'rank_{rank:03d}.log').read_text();logs=re.findall(r'^Step\s+(\d+) of\s+(\d+) mtime=\s*(\d+)\s+(\d+)\s+(\d+)',text,re.M)
        require([int(a[0]) for a in logs]==list(range(10,23041,10)) and all(int(a[1])==23040 for a in logs),'Missing/repeated/misordered progress')
        for step,total,d,h,m in logs:
            t=START+datetime.timedelta(minutes=int(step));require([int(d),int(h),int(m)]==[int(t.strftime('%j')),t.hour,t.minute],'Independent step/UTC mismatch')
        require(list(map(int,logs[-1][2:]))==[268,0,0] and len(re.findall(r'^NORMAL EXIT\s*$',text,re.M))==1,'Final model log time/exit mismatch')
        require(not re.search(r'\b(?:NaN|Inf|ERROR)\b|MPI_ABORT|bad isec_req',text,re.I),'Fatal actual model log')
        ranks.append(dict(rank=rank,returncode=b['returncode'],child_pid=b['child_pid'],started_unix=b['started_unix'],ended_unix=b['ended_unix'],receipt_SHA256=digest(RUN/f'rank_{rank:03d}_exit.json')))
    require(len({a['child_pid'] for a in ranks})==4,'Repeated model rank PID')
    notes['identity']=dict(run_id=claim['run_id'],parent_returncode=0,session=status['identity']['sid'],ranks=ranks,progress_records_per_rank=2304,actual_steps=23040,actual_final_UTC=STOP.isoformat()+'Z',direct_wait_journal_verified=True)
    solar,kp=read_raw(2021,[R/'data/raw/f107_2021_recovery_v1/gfz_year.txt'])
    means={t:math.fsum(solar[t+datetime.timedelta(days=j)] for j in range(-40,41))/81 for t in [stamp(2021,9,7)+datetime.timedelta(days=i) for i in range(21)]}
    primary=[];secondary=[];inventory=[];warm=0;driver_max={k:0. for k in ['f107d','f107a','Kp','hpower','ctpoten']};arrays={};physical=[];cold=0
    # Read primary schemas from original source, not main acceptance's verdict.
    from atmosphere.restart_validation import REQUIRED
    with Dataset(R/p['source']['path']) as source:
        grid={k:np.asarray(source[k][:]) for k in ['lat','lon','lev','ilev']}
        schemas={k:(source[k].dimensions,getattr(source[k],'units',None)) for k in REQUIRED}
    expected_names=sorted([f'primary_{i:03d}.nc' for i in range(1,18)]+[f'secondary_{i:03d}.nc' for i in range(1,17)])
    require(sorted(x.name for x in RUN.glob('*.nc'))==expected_names,'Incorrect33-file set')
    for name in expected_names:
        path=RUN/name;kind=name.split('_')[0]
        with Dataset(path) as n:
            require(n.data_model=='NETCDF3_CLASSIC' and n.history_type==kind,'Output format/history type')
            require(len(n.dimensions['time'])==(1 if kind=='primary' else 24),'Records per volume mismatch')
            require(int(np.asarray(n['timestep'][:]).item())==60 and np.all(n['calendar_advance'][:]==1),'Output STEP/calendar mismatch')
            for key,a in grid.items():require(np.array_equal(n[key][:],a),'Grid mismatch '+key)
            times=[datetime.datetime(t.year,t.month,t.day,t.hour,t.minute,t.second) for t in num2date(n['time'][:],n['time'].units)]
            (primary if kind=='primary' else secondary).extend(times)
            if kind=='primary':
                for key in REQUIRED:
                    require(key in n.variables and n[key].dtype==np.dtype('float64') and (n[key].dimensions,getattr(n[key],'units',None))==schemas[key],'Primary schema/unit/dtype mismatch '+key)
                    a,mask=raw(n[key],0,allow_mask=True);require((~mask).any(),'Empty primary state '+key)
            if kind=='secondary':native_secondary_schema=secondary_schema(n,schemas)
            for i,t in enumerate(times):
                require(int(n['year'][i])==2021 and int(n['day'][i])==int(t.strftime('%j')) and list(n['mtime'][i])==[int(t.strftime('%j')),t.hour,t.minute],'Native CF/year/day/mtime mismatch')
                if kind=='primary' and t==START:
                    cold+=1;tv=n['time'];require(i==0 and name=='primary_001.nc' and int(tv.initial_year)==2021 and int(tv.initial_day)==252 and list(tv.initial_mtime)==[252,0,0],'Unregistered cold echo')
                else:require(int(n['iter'][i])==252*1440+int((t-START).total_seconds()/60),'Warm iter/calendar mismatch')
                if kind=='secondary':
                    for key,units in [('DEN','g/cm3'),('ZG','cm')]:require(n[key].dimensions==('time','ilev','lat','lon') and n[key].units==units and n[key].dtype.kind=='f','DEN/ZG native schema')
                    den,_=raw(n['DEN'],i);z,_=raw(n['ZG'],i);require((den>0).all() and (np.diff(z,axis=0)>0).all(),'Nonpositive density/nonmonotonic ZG');warm+=1
                    components=[]
                    for key in ['TN','UN','VN','O1','O2','N2','HE']:
                        a,mask=raw(n[key],i,allow_mask=True)
                        if key in ['TN','UN','VN']:
                            require(not mask[:-1].any() and mask[-1].all(),'Incorrect prognostic top padding')
                            good=a[~mask]
                            if key=='TN':require(good.min()>100 and good.max()<5000,'TN bounds')
                            else:require(abs(good).max()<2e5,'Wind bounds')
                        else:require(not mask.any() and a.min()>=0 and a.max()<=1.000001,'Composition bounds/mask');components.append(a)
                    require(np.max(np.abs(sum(components)-1))<1e-5,'Composition closure')
                    expected=independent_at(t.replace(tzinfo=datetime.timezone.utc),solar,means,kp)
                    for key,val in expected.items():
                        observed,_=raw(n[key],i);error=abs(float(observed)-val);driver_max[key]=max(driver_max[key],error);require(error<1e-10,'Independent actual GFZ driver mismatch')
                    if TARGET<=t<=TARGET+datetime.timedelta(days=1):arrays[t]=(z*.01,den*1000.)
                    if t in [TARGET,TARGET+datetime.timedelta(hours=12),STOP]:physical.append(dict(UTC=t.isoformat()+'Z',DEN_min_kg_m3=float(den.min()*1000),DEN_max_kg_m3=float(den.max()*1000),ZG_min_m=float(z.min()*.01),ZG_max_m=float(z.max()*.01)))
            inventory.append(dict(file=name,SHA256=digest(path),bytes=path.stat().st_size,records=len(times),first_UTC=times[0].isoformat()+'Z',last_UTC=times[-1].isoformat()+'Z'))
    require(primary==[START+datetime.timedelta(days=i) for i in range(17)] and secondary==[START+datetime.timedelta(hours=i) for i in range(1,385)],'Independent full timeline incomplete')
    require(cold==1 and warm==384 and len(arrays)==25,'Missing cold/warm/target-day frame identity')
    notes['outputs']=dict(secondary_schema=native_secondary_schema,primary_records=len(primary),secondary_records=len(secondary),files=inventory,NetCDF_files=len(inventory),NetCDF_bytes=sum(a['bytes'] for a in inventory),all_warm_DEN_ZG_records=warm,cold_primary_echo=cold,actual_GFZ_max_abs_difference=driver_max,original_GPI_SHA256=digest(R/p['GPI']['path']),physical_fixed_samples=physical)
    require(digest(R/p['observation']['path'])==p['observation']['SHA256'],'Swarm CDF SHA changed')
    with cdflib.CDF(R/p['observation']['path']) as c:
        utc=cdflib.cdfepoch.to_datetime(c.varget('time'));rho=np.asarray(c.varget('density'));flags=np.asarray(c.varget('validity_flag'));olat=np.asarray(c.varget('latitude'));olon=np.asarray(c.varget('longitude'));alt=np.asarray(c.varget('altitude'));require(c.varattsget('density')['UNITS']=='kg/m3','CDF density unit')
    quality=(flags==0)&np.isfinite(rho)&(rho>0)&(rho!=9.99e32)&(rho<1e30)&np.isfinite(olat)&(abs(olat)<=90)&np.isfinite(olon)&(abs(olon)<=180)&np.isfinite(alt)&(alt>0)
    require(len(utc)==2880 and int(quality.sum())==2880 and utc[0]==np.datetime64('2021-09-23T00') and utc[-1]==np.datetime64('2021-09-23T23:59:30') and np.all(np.diff(utc)==np.timedelta64(30,'s')),'Independent CDF quality/time count')
    location=EarthLocation.from_geodetic(olon*u.deg,olat*u.deg,alt*u.m,ellipsoid='GRS80');geo=location.to_geodetic(ellipsoid='WGS84');mlat=geo.lat.to_value(u.deg);mlon=geo.lon.to_value(u.deg);height=geo.height.to_value(u.m)
    zs=np.stack([arrays[TARGET+datetime.timedelta(hours=i)][0] for i in range(25)]);rs=np.stack([arrays[TARGET+datetime.timedelta(hours=i)][1] for i in range(25)]);lat=grid['lat'];lon=grid['lon'];success=0;reasons=collections.Counter();columns=0
    for index in np.flatnonzero(quality):
        h=float((utc[index]-np.datetime64('2021-09-23T00'))/np.timedelta64(1,'h'))
        if not 0<=h<24:reasons['TIME_OUTSIDE']+=1;continue
        if not lat[0]<=mlat[index]<=lat[-1]:reasons['LAT_OUTSIDE_NATIVE_DOMAIN']+=1;continue
        k=int(math.floor(h));j=min(max(int(np.searchsorted(lat,mlat[index],side='right'))-1,0),len(lat)-2);x=(mlon[index]-lon[0])%360+lon[0];i=int(np.searchsorted(lon,x,side='right'))-1;i2=(i+1)%len(lon);right=lon[i2] if i2 else lon[0]+360
        wt=[1-(h-k),h-k];wy=(mlat[index]-lat[j])/(lat[j+1]-lat[j]);wx=(x-lon[i])/(right-lon[i]);value=0.;valid=True
        for a in [0,1]:
            for b in [0,1]:
                for cc,ii in enumerate([i,i2]):
                    z=zs[k+a,:,j+b,ii];r=rs[k+a,:,j+b,ii];columns+=1
                    if not (np.isfinite(z).all() and np.isfinite(r).all() and (r>0).all() and (np.diff(z)>0).all() and z[0]<=height[index]<=z[-1]):valid=False;continue
                    value+=wt[a]*[1-wy,wy][b]*[1-wx,wx][cc]*np.exp(np.interp(height[index],z,np.log(r)))
        if valid and np.isfinite(value) and value>0:success+=1
        else:reasons['INVALID_COLUMN_OR_VERTICAL_OUTSIDE']+=1
    notes['independent_queries']=dict(total=len(utc),eligible=int(quality.sum()),success=success,failed=int(quality.sum())-success,reasons=dict(reasons),column_checks=columns,zero_weight_columns_checked=True,no_extrapolation=True,no_error_metrics=True,method='Independent CDF/geodetic conversion and neighbor/time/log-vertical reconstruction; not main PASS fields',identity='PROVISIONAL Map-A / HINDCAST / NOT_BLIND / EXTERNAL_DATUM_UNVERIFIED')
    require(success==2880 and columns==23040,'Independent target-day coverage failure')
    # Compare numbers and hashes only after obtaining independent raw evidence.
    agreement=False
    if main:
        require(main['run_id']==claim['run_id'],'Primary audit run ID differs')
        o=main['checks'].get('output_files',{})
        if o.get('status')=='PASS':
            prior={e['file']:e for e in o['evidence']['files']};require(all(prior[e['file']]['SHA256']==e['SHA256'] for e in inventory),'Main/independent file SHA disagreement')
        q=main['checks'].get('target_observation_queries',{})
        if q.get('status')=='PASS':require(q['evidence']['success']==success and q['evidence']['eligible']==2880 and q['evidence']['failed']==0,'Main/independent query-count disagreement')
        agreement=main['overall']=='PASS'
    protected=load(F/'protected_assets.json')
    for name,sha in protected.items():require(digest(R/name)==sha,'Original asset changed '+name)
    for item in [p['source'],p['input'],p['GPI'],p['executable'],p['observation'],p['hapi']]:require(digest(R/item['path'])==item['SHA256'],'Frozen input changed')
    require(digest(RUN/'input.inp')==p['input']['SHA256'],'Staged input mismatch')
    notes.update(PASS=True,independent_raw_checks='PASS',main_acceptance_status=main['overall'] if main else 'MISSING',main_and_independent_agreement=agreement,overall='ENGINEERING_PASS' if agreement else 'ENGINEERING_FAIL',ACTUAL_MODEL_RUN='COMPLETED',model_launches_this_verifier=0,actual_physical_model_launches=1,new_density_scores=0,new_fits=0,protected_original_files=len(protected),wall_s=time.perf_counter()-wall,CPU_s=time.process_time()-cpu,self_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return notes

def main():
    try:
        result=review();write_once(F/'independent_verification.json',result);print(json.dumps({k:result[k] for k in ['PASS','overall','wall_s','CPU_s','self_peak_RSS_KiB']}),flush=True)
        raise SystemExit(0 if result['overall']=='ENGINEERING_PASS' else 2)
    except Exception as e:
        write_once(F/'independent_failure.json',dict(PASS=False,error_type=type(e).__name__,error=str(e).replace(str(R),'$PROJECT'),model_retried=False));raise
if __name__=='__main__':main()
