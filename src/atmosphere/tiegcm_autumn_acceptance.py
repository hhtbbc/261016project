"""Autumn calendar adapter for V17 strict read-only acceptance; no model launch/score."""
from pathlib import Path
import json,datetime,collections
import numpy as np
from netCDF4 import Dataset,num2date
from atmosphere.tiegcm_mar25_acceptance import parse_progress,validate_exits,inspect_density_record,driver_difference
from atmosphere.restart_validation import REQUIRED
from atmosphere.tiegcm_drivers import GpiDriver
from runtime.tiegcm_rank_exit import digest
from runtime.tiegcm_autumn_execution import ROOT,validate_binding,require

def dates(year):return datetime.datetime(year,9,9),datetime.datetime(year,9,25)
def validate_timelines(primary,secondary,year,cold_count):
    start,stop=dates(year)
    require(primary==[start+datetime.timedelta(days=i) for i in range(17)],'Primary calendar incomplete/duplicate/out of order')
    require(secondary==[start+datetime.timedelta(hours=i) for i in range(1,385)],'Secondary calendar incomplete/duplicate/out of order')
    require(cold_count==1,'Exactly one native primary cold echo required')
    return dict(primary_records=17,secondary_records=384,final_UTC=stop.isoformat()+'Z')

def field(v):
    # Same V17 explicit native cast: no warning suppression or missing-to-zero conversion.
    v.set_auto_mask(False);a=np.asarray(v[:]);require(np.isfinite(a).all(),'Nonfinite '+v.name);mask=abs(a)>1e30
    for name in ['missing_value','_FillValue']:
        if name in v.ncattrs():
            for value in np.asarray(v.getncattr(name)).reshape(-1):mask|=a==np.asarray(value,dtype=a.dtype)
    return np.ma.array(a,mask=mask)

def prognostics(n):
    if n.history_type=='primary':
        for name in REQUIRED:
            require(name in n.variables and n[name].dtype==np.dtype('float64'),'Missing/non-double primary state '+name)
            require(field(n[name]).count()>0,'Empty primary state '+name)
        return
    values={}
    for name in ['TN','UN','VN','O1','O2','N2','HE']:
        require(name in n.variables,'Missing warm prognostic '+name);v=field(n[name]);mask=np.ma.getmaskarray(v)
        if name in ['TN','UN','VN']:
            require(not mask[:,:-1].any() and mask[:,-1].all(),'Incorrect native top padding '+name)
            if name=='TN':require(v.min()>100 and v.max()<5000,'Temperature range')
            else:require(abs(v).max()<2e5,'Wind range')
        else:require(not mask.any() and v.min()>=0 and v.max()<=1.000001,'Composition range/mask '+name)
        values[name]=v
    require(abs(sum(values[k] for k in ['O1','O2','N2','HE'])-1).max()<1e-5,'Mass mixing ratios do not sum to one')

def inspect_outputs(run,p):
    y=p['year'];start,stop=dates(y);drv=GpiDriver(ROOT/p['GPI']['path']);primary=[];secondary=[];inventory=[];cold=0;worst=0.
    actual_names=sorted(q.name for q in run.glob('*.nc'));expected_names=sorted([f'primary_{i:03d}.nc' for i in range(1,18)]+[f'secondary_{i:03d}.nc' for i in range(1,17)])
    require(actual_names==expected_names,'Missing/extra native NetCDF output files')
    with Dataset(ROOT/p['source']['path']) as seed:grid={k:np.asarray(seed[k][:]) for k in ['lat','lon','lev','ilev']}
    for kind,count in [('primary',17),('secondary',16)]:
        for volume in range(1,count+1):
            path=run/f'{kind}_{volume:03d}.nc';require(path.stat().st_size<=256*2**20,'Volume budget exceeded')
            with Dataset(path) as n:
                require(n.history_type==kind and n.data_model=='NETCDF3_CLASSIC','Native format/history mismatch')
                require(len(n.dimensions['time'])==(1 if kind=='primary' else 24),'Wrong records per volume')
                require(int(np.asarray(n['timestep'][:]).item())==60 and np.all(n['calendar_advance'][:]==1),'Step/calendar mismatch')
                for k,a in grid.items():require(np.array_equal(n[k][:],a),'Grid mismatch '+k)
                tv=n['time'];require(int(tv.initial_year)==y and int(tv.initial_day)==252 and np.array_equal(tv.initial_mtime,[252,0,0]),'Native initial calendar identity mismatch')
                prognostics(n);times=[]
                for i,t in enumerate(num2date(tv[:],tv.units)):
                    t=datetime.datetime(t.year,t.month,t.day,t.hour,t.minute,t.second);times.append(t)
                    require(int(n['year'][i])==y and int(n['day'][i])==int(t.strftime('%j')) and np.array_equal(n['mtime'][i],[int(t.strftime('%j')),t.hour,t.minute]),'CF/native year/day/mtime disagree')
                    if kind=='primary' and t==start:
                        require(volume==1 and i==0 and n.run_type=='initial','Illegal cold-echo exemption');cold+=1
                    else:require(int(n['iter'][i])==252*1440+int((t-start).total_seconds()/60),'Warm iter/time mismatch')
                    if kind=='secondary':
                        inspect_density_record(n,i)
                        expected=drv.at(y*1000+int(t.strftime('%j')),t.hour*3600+t.minute*60)
                        for name,v in expected.items():worst=max(worst,driver_difference(field(n[name])[i],v))
                        require(worst<1e-10,'Actual GPI driver mismatch')
                require(all(a<b for a,b in zip(times,times[1:])),'Nonmonotonic volume time')
                (primary if kind=='primary' else secondary).extend(times)
                inventory.append(dict(file=path.name,SHA256=digest(path),bytes=path.stat().st_size,records=len(times),first_UTC=times[0].isoformat()+'Z',last_UTC=times[-1].isoformat()+'Z'))
    return dict(**validate_timelines(primary,secondary,y,cold),files=inventory,actual_GPI_max_abs_difference=worst,cold_primary_echo=cold,DEN_ZG_warm_records=384,primary_required_states=34)

def query_coverage(run,p,inventory):
    from observations.density_catalog import read_swarm_pod
    from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
    from atmosphere.causal_observation_operator import map_a_queries,observe_map_a
    for e in [p['observation'],p['hapi']]:require(digest(ROOT/e['path'])==e['SHA256'],'Original observation/contract changed')
    _,obs,_=read_swarm_pod(ROOT/p['observation']['path'],ROOT/p['hapi']['path'],p['observation']['SHA256'],satellite='A')
    eligible=obs['quality'];require(len(eligible)==2880 and int(eligible.sum())==p['eligible_observations'],'Original observation quality count changed')
    lo=f"{p['year']}-09-23T00:00:00";hi=f"{p['year']}-09-24T00:00:00"
    entries=[e for e in inventory['files'] if e['file'].startswith('secondary_') and e['last_UTC']>=lo+'Z' and e['first_UTC']<=hi+'Z']
    expected={e['file']:e['SHA256'] for e in entries};reader=HourlyTiegcmObservation([run/e['file'] for e in entries],expected,lo,hi,f"{p['year']} autumn mareqx restricted")
    success=0;reasons=collections.Counter()
    try:
        for q in map_a_queries(obs['utc'][eligible],obs['latitude'][eligible],obs['longitude'][eligible],obs['altitude'][eligible]):
            r,_=observe_map_a(reader,q)
            if r.valid and len(r.metadata.get('columns',[]))==8:success+=1
            else:reasons[r.reason or 'INCOMPLETE_EIGHT_COLUMNS']+=1
    finally:reader.close()
    evidence=dict(eligible=int(eligible.sum()),success=success,failed=int(eligible.sum())-success,reasons=dict(reasons),zero_weight_columns_checked=True,extrapolation=False,no_density_error_metrics=True)
    require(success==int(eligible.sum()),'Incomplete full-day Map-A coverage '+json.dumps(evidence));return evidence

def accept(run,run_id,p):
    validate_binding(p);run=Path(run);require(run.resolve()==(ROOT/p['cwd']).resolve(),'Wrong run path/year')
    names=['supervision','MPI_rank_exits','step_logs','output_files','target_observation_queries'];checks={k:dict(status='NOT_RUN') for k in names}
    result=dict(ACTUAL_MODEL_RUN='NOT_RUN',overall='NOT_RUN',year=p['year'],run_id=run_id,checks=checks,scientific_gates_unchanged=True)
    if not (run/'status.json').exists():
        if run.exists():result.update(ACTUAL_MODEL_RUN='UNKNOWN',overall='FAIL');checks['supervision']=dict(status='FAIL',reason='Reserved/partial run has no direct-wait status')
        return result
    result['ACTUAL_MODEL_RUN']='ATTEMPTED'
    def check(name,fun):
        try:checks[name]=dict(status='PASS',evidence=fun());return True
        except Exception as e:checks[name]=dict(status='FAIL',error_type=type(e).__name__,reason=str(e).replace(str(ROOT),'$PROJECT'));return False
    def supervision():
        s=json.loads((run/'status.json').read_text());require(s['returncode']==0 and s['qualification']=='PASS' and not s['gaps'] and s['cleanup_verified'] and s['wait_source']=='direct subprocess.Popen.wait' and s['elapsed_s']<=4800,'MPI parent wait/monitoring failed')
        require(digest(run/'input.inp')==p['input']['SHA256'],'Staged input changed')
        for e in [p['input'],p['GPI'],p['source'],p['executable']]:require(digest(ROOT/e['path'])==e['SHA256'],'Input provenance changed')
        return dict(returncode=0,status_SHA256=digest(run/'status.json'),wait_source=s['wait_source'])
    if not check('supervision',supervision):result['overall']='FAIL';return result
    if check('MPI_rank_exits',lambda:validate_exits(run,run_id,p)):
        check('step_logs',lambda:dict(per_rank=[parse_progress((run/f'rank_{i:03d}.log').read_text(),steps=23040,start=dates(p['year'])[0]) for i in range(4)]))
    if check('output_files',lambda:inspect_outputs(run,p)):
        check('target_observation_queries',lambda:query_coverage(run,p,checks['output_files']['evidence']))
    result['overall']='PASS' if all(x['status']=='PASS' for x in checks.values()) else 'FAIL'
    return result
