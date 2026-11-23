"""V29 read-only reconstruction, adapted from the frozen V24 independent review."""
from pathlib import Path
import sys,json,re,math,time,datetime,collections,resource
R=Path(__file__).resolve().parents[2];sys.path[:0]=[str(R/'src'),str(R)]
import numpy as np,cdflib
from netCDF4 import Dataset,num2date
from astropy.coordinates import EarthLocation
import astropy.units as u
from runtime.tiegcm_rank_exit import digest,write_once
from atmosphere.autumn_gpi_validation import read_raw,independent_at,stamp
F=Path(__file__).resolve().parent
BASE=R/'experiments/thermosphere_autumn_mareqx_config_v23/2022'
RUN=BASE/'actual_run'
V27=R/'experiments/thermosphere_autumn_2022_execution_preparation_v27'
MAIN=V27/'postrun_v27_local/acceptance.json'
RELEASE_SHA='f994a9ce2814044af7b6d473f884ab078fddb3e1fbd252cbd659f38f9a0c9bb0'
V24=R/'experiments/thermosphere_autumn_2021_formal_run_v24'
V28=R/'experiments/thermosphere_autumn_2022_formal_run_v28'
GFZ=R/'experiments/thermosphere_autumn_gpi_seed_policy_v22/input_sources_2022.json'
OLD_RUN_ID='18726974f5d3450ba61f82c23c8da3a0'
START=datetime.datetime(2022,9,9);STOP=datetime.datetime(2022,9,25);TARGET=datetime.datetime(2022,9,23)
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
    require(RUN.resolve(strict=True)==RUN, 'Unexpected run path')
    require(digest(V27/'execution_release.json')==RELEASE_SHA, 'Changed V27 release')
    require(re.fullmatch('[0-9a-f]{32}', claim['run_id']) and claim['run_id']!=OLD_RUN_ID
            and claim['release_SHA256']==RELEASE_SHA, 'Invalid V29 run identity')
    require(digest(BASE/'launch_protocol.json')=='450d7b4830c8433112350aee53ba90bb1e279fd179957001370619f9c428f928',
            'Changed 2022 launch protocol')
    require(p['cwd']==str(RUN.relative_to(R)) and p['target_date']=='2022-09-23',
            'Wrong 2022 protocol binding')
    require(int(p['steps'])==23040 and p['MPI']==4, 'Wrong frozen step or MPI count')
    input_file=RUN/'input.inp'
    require(digest(input_file)==p['input']['SHA256'], 'Staged input mismatch')
    text=input_file.read_text()
    require(re.findall(r"(?m)^\s*SOURCE\s*=\s*'([^']+)'\s*$", text)
            ==['$PROJECTROOT/'+p['source']['path']]
            and re.findall(r'(?m)^\s*SOURCE_START\s*=([^\n]*)$',text)[0].split()==['80','0','0'],
            'Independent explicit cold-source identity mismatch')
    for key in ('source','GPI','executable'):
        item=p[key]
        require(digest(R/item['path'])==item['SHA256'], 'Frozen V27 '+key+' changed')
    output_binding = str(MAIN.relative_to(R))
    require(MAIN.resolve(strict=True)==MAIN and load(MAIN)['overall']=='PASS', 'Main audit prerequisite absent')
    main_digest=digest(MAIN)
    require(p['year']==claim['year']==2022 and claim['attempts']==1 and not claim['automatic_retry'],'Wrong year/launch claim')
    require(status['returncode']==0 and status['qualification']=='PASS' and status['cleanup_verified'] and not status['gaps'] and status['wait_source']=='direct subprocess.Popen.wait','MPI parent/supervision not complete')
    require(status['stop_reason'] is None and status['elapsed_s']<=4800,'Model resource/stop failure')
    events=[json.loads(l) for l in (RUN/'events.jsonl').read_text().splitlines()];wait=[a for a in events if a['event']=='child_wait_final'];launched=[a for a in events if a['event']=='launched']
    require(len(wait)==len(launched)==1 and wait[0]['returncode']==0 and wait[0]['cleanup_verified'] and launched[0]['identity']==status['identity'],'Direct wait journal mismatch')
    once=load(RUN/'launch_once.json');argv=once['argv']
    require(once['launch_count']==1 and argv[argv.index('--run-id')+1]==claim['run_id']
            and argv[argv.index('--model-sha')+1]==p['executable']['SHA256']
            and argv[argv.index('--input-sha')+1]==p['input']['SHA256'],
            'One-time launch not bound to rank receipts')
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
    require('output_hist: copied source history structure sh to' in (RUN/'rank_000.log').read_text(),
            'Missing native source echo evidence')
    notes['identity']=dict(run_id=claim['run_id'],parent_returncode=0,session=status['identity']['sid'],ranks=ranks,progress_records_per_rank=2304,actual_steps=23040,actual_final_UTC=STOP.isoformat()+'Z',direct_wait_journal_verified=True)
    gfz=load(GFZ)['files'];protected=load(V24/'protected_assets.json')
    for path,expected in gfz.items():
        require(protected[path]==expected and digest(R/path)==expected,'Changed 2022 GFZ original')
    solar,kp=read_raw(2022,[R/'data/raw/thermosphere_autumn_data_acquisition_v21'/name for name in
        ('GFZ_Fobs_20220729_20221106.json','GFZ_Kp_def_20220907_20220927.json')])
    means={t:math.fsum(solar[t+datetime.timedelta(days=j)] for j in range(-40,41))/81 for t in [stamp(2022,9,7)+datetime.timedelta(days=i) for i in range(21)]}
    primary=[];secondary=[];inventory=[];warm=0;driver_max={k:0. for k in ['f107d','f107a','Kp','hpower','ctpoten']};arrays={};physical=[];cold=0
    # Read primary schemas from original source, not main acceptance's verdict.
    from atmosphere.restart_validation import REQUIRED
    with Dataset(R/p['source']['path']) as source:
        require(source.history_type=='primary' and len(source.dimensions['time'])==1
                and int(source['year'][0])==2002 and int(source['day'][0])==80
                and list(source['mtime'][0])==[80,0,0], 'Mareqx source record mismatch')
        seed_iter=int(source['iter'][0])
        require(seed_iter==115200, 'Mareqx inherited iter mismatch')
        grid={k:np.asarray(source[k][:]) for k in ['lat','lon','lev','ilev']}
        schemas={k:(source[k].dimensions,getattr(source[k],'units',None)) for k in REQUIRED}
    expected_names=sorted([f'primary_{i:03d}.nc' for i in range(1,18)]+[f'secondary_{i:03d}.nc' for i in range(1,17)])
    require(sorted(x.name for x in RUN.glob('*.nc'))==expected_names,'Incorrect33-file set')
    for name in expected_names:
        path=RUN/name;kind=name.split('_')[0]
        require(path.resolve(strict=True)==path, 'Noncanonical original output path')
        before=path.stat()
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
                require(int(n['year'][i])==2022 and int(n['day'][i])==int(t.strftime('%j')) and list(n['mtime'][i])==[int(t.strftime('%j')),t.hour,t.minute],'Native CF/year/day/mtime mismatch')
                tv=n['time']
                require(int(tv.initial_year)==2022 and int(tv.initial_day)==252
                        and list(tv.initial_mtime)==[252,0,0], 'Initial calendar mismatch')
                if kind=='primary' and t==START:
                    cold+=1
                    require(i==0 and name=='primary_001.nc' and n.run_type in ('','initial')
                            and list(n.source_mtime)==[80,0,0] and int(n['iter'][i])==seed_iter,
                            'Unregistered 2022 cold echo')
                else:
                    require(n.run_type=='initial' and int(n['iter'][i])==252*1440+int((t-START).total_seconds()/60),
                            'Warm identity or iter/calendar mismatch')
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
            file_sha=digest(path);after=path.stat()
            require((before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)
                    ==(after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),
                    'Output changed during independent review')
            inventory.append(dict(file=name,SHA256=file_sha,bytes=after.st_size,records=len(times),
                                  first_UTC=times[0].isoformat()+'Z',last_UTC=times[-1].isoformat()+'Z'))
    require(primary==[START+datetime.timedelta(days=i) for i in range(17)] and secondary==[START+datetime.timedelta(hours=i) for i in range(1,385)],'Independent full timeline incomplete')
    require(cold==1 and warm==384 and len(arrays)==25,'Missing cold/warm/target-day frame identity')
    notes['outputs']=dict(secondary_schema=native_secondary_schema,primary_records=len(primary),secondary_records=len(secondary),files=inventory,NetCDF_files=len(inventory),NetCDF_bytes=sum(a['bytes'] for a in inventory),all_warm_DEN_ZG_records=warm,cold_primary_echo=cold,actual_GFZ_max_abs_difference=driver_max,original_GPI_SHA256=digest(R/p['GPI']['path']),physical_fixed_samples=physical)
    require(digest(R/p['observation']['path'])==p['observation']['SHA256'],'Swarm CDF SHA changed')
    with cdflib.CDF(R/p['observation']['path']) as c:
        utc=cdflib.cdfepoch.to_datetime(c.varget('time'));rho=np.asarray(c.varget('density'));flags=np.asarray(c.varget('validity_flag'));olat=np.asarray(c.varget('latitude'));olon=np.asarray(c.varget('longitude'));alt=np.asarray(c.varget('altitude'));require(c.varattsget('density')['UNITS']=='kg/m3','CDF density unit')
    quality=(flags==0)&np.isfinite(rho)&(rho>0)&(rho!=9.99e32)&(rho<1e30)&np.isfinite(olat)&(abs(olat)<=90)&np.isfinite(olon)&(abs(olon)<=180)&np.isfinite(alt)&(alt>0)
    require(len(utc)==2880 and int(quality.sum())==2880 and utc[0]==np.datetime64('2022-09-23T00') and utc[-1]==np.datetime64('2022-09-23T23:59:30') and np.all(np.diff(utc)==np.timedelta64(30,'s')),'Independent CDF quality/time count')
    location=EarthLocation.from_geodetic(olon*u.deg,olat*u.deg,alt*u.m,ellipsoid='GRS80');geo=location.to_geodetic(ellipsoid='WGS84');mlat=geo.lat.to_value(u.deg);mlon=geo.lon.to_value(u.deg);height=geo.height.to_value(u.m)
    zs=np.stack([arrays[TARGET+datetime.timedelta(hours=i)][0] for i in range(25)]);rs=np.stack([arrays[TARGET+datetime.timedelta(hours=i)][1] for i in range(25)]);lat=grid['lat'];lon=grid['lon'];success=0;reasons=collections.Counter();columns=0
    for index in np.flatnonzero(quality):
        h=float((utc[index]-np.datetime64('2022-09-23T00'))/np.timedelta64(1,'h'))
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
    # Reconcile the independent outputs only after reconstructing them.
    require(digest(MAIN)==main_digest,'Main acceptance changed during review')
    main=load(MAIN)
    require(main['run_id']==claim['run_id'] and main['overall']=='PASS','Main run identity differs')
    compare=lambda rows: {e['file']:(e['SHA256'],e['bytes'],e['records'],e['first_UTC'],e['last_UTC'])
                          for e in rows}
    require(compare(main['outputs']['files'])==compare(inventory),'Independent file SHA/volume mismatch')
    require(main['Map_A']['success']==success and main['Map_A']['eligible']==2880
            and main['Map_A']['failed']==0,'Independent query count mismatch')
    for name,sha in protected.items():
        require(digest(R/name)==sha,'Original asset changed '+name)
    for item in [p['source'],p['input'],p['GPI'],p['executable'],p['observation'],p['hapi']]:
        require(digest(R/item['path'])==item['SHA256'],'Frozen V27 input changed')
    require(digest(RUN/'input.inp')==p['input']['SHA256'],'Staged input mismatch')
    prior=load(F/'prior_evidence_SHA256.json')
    for name,sha in prior.items():
        require(digest(R/name)==sha,'Prior V24/V26/V27/V28 evidence changed '+name)
    notes.update(overall='ENGINEERING_PASS',independent_raw_checks='PASS',ACTUAL_MODEL_RUN='COMPLETED',
                 main_acceptance_path=output_binding,main_acceptance_SHA256=main_digest,
                 new_density_scores=0,model_launches_this_verifier=0,
                 protected_original_files=len(protected),prior_pins=len(prior),GFZ_SHA256=gfz,
                 verifier_SHA256=digest(Path(__file__)),wall_s=time.perf_counter()-wall,
                 CPU_s=time.process_time()-cpu,self_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return notes


def main():
    require(F.resolve()==F and not (F/'independent_review.json').exists()
            and not (F/'independent_failure.json').exists(),'Independent output already present')
    try:
        result=review()
        write_once(F/'independent_review.json',result)
        print(json.dumps({key:result[key] for key in ('overall','wall_s','CPU_s','self_peak_RSS_KiB')}))
    except Exception as error:
        write_once(F/'independent_failure.json',dict(overall='FAIL',error_type=type(error).__name__,
                                                     reason=str(error).replace(str(R),'$PROJECT')))
        raise


if __name__=='__main__':
    main()
