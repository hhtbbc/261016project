"""Read-only crossday audit; does not launch the model or branch continuation."""
from pathlib import Path
import argparse,sys,json,re,hashlib,csv
import numpy as np
from netCDF4 import Dataset,num2date
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from atmosphere.tiegcm_drivers import GpiDriver
from atmosphere.restart_validation import REQUIRED,inspect_restart

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-tag',required=True);a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+',a.run_tag):raise ValueError('Bad tag')
    out=ROOT/'experiments'/a.run_tag
    if not out.resolve().is_relative_to(ROOT):raise ValueError('Outside workspace')
    if (out/'crossday_audit.json').exists():raise FileExistsError('Audit already exists')
    driver=GpiDriver(ROOT/'data/processed/tiegcm2023/gpi_20230312_20230325.nc')
    status=json.loads((out/'run_status.json').read_text())
    assert status['returncode']==0 and status['stop_reason'] is None and status['normal_exit_count']==4
    log=(ROOT/'logs'/f'{a.run_tag}.log').read_text()
    assert 'init: iyear= 2023 iday=   77' in log and 'calling apxparm: start_year= 2023' in log
    assert 'Initial requested iyear=2023 iday= 77 iutsec=        60' in log
    assert re.search(r'Advancing day \(previous,present\)=\s*77\s*2023\s*78\s*2023',log)
    assert len(re.findall(r'nstep=\s*1450 step=\s*60',log))==4
    suspicious=re.findall(r'(?im)^.*(?:\bNaN\b|\bInf\b|WARNING|ERROR|bad isec_req).*$' ,log)
    assert not suspicious,suspicious[:5]
    expected_dates=['2023-03-18 00:00:00','2023-03-18 23:50:00','2023-03-19 00:00:00','2023-03-19 00:10:00']
    files=[];driver_rows=[];checkpoint=None
    for path in sorted(out.glob('*.nc')):
        row={'file':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,
             'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'fields':{}}
        with Dataset(path) as n:
            dates=[str(d) for d in num2date(n['time'][:],n['time'].units)];row['dates']=dates
            days=np.asarray(n['day'][:]);yrs=np.asarray(n['year'][:]);mtime=np.asarray(n['mtime'][:]);ut=np.asarray(n['ut'][:])
            assert np.all(yrs==2023) and np.array_equal(mtime[:,0],days)
            assert np.all(n['calendar_advance'][:]==1) and int(n['timestep'][:])==60
            assert np.array_equal(np.round(ut*3600).astype(int),mtime[:,1]*3600+mtime[:,2]*60)
            primary=getattr(n,'history_type','')=='primary'
            if primary:
                index=int(path.stem.split('_')[-1])-1
                assert dates==[expected_dates[index]] and len(n.dimensions['time'])==1
                assert all(v in n.variables and n[v].dtype==np.dtype('float64') for v in REQUIRED)
                row['initial_time_attributes']={k:np.asarray(n['time'].getncattr(k)).tolist() for k in ['initial_year','initial_day','initial_mtime']}
                assert row['initial_time_attributes']['initial_year']==2023
                assert row['initial_time_attributes']['initial_day']==77
                assert row['initial_time_attributes']['initial_mtime']==[77,0,0]
                if index==0:
                    row['inherited_initial_iter']=int(n['iter'][0])
                else:
                    expected_iter=int(mtime[0,0])*1440+int(mtime[0,1])*60+int(mtime[0,2])
                    assert int(n['iter'][0])==expected_iter
                    row['iter_matches_model_calendar']=True
            else:assert dates==expected_dates[1:]
            for i,date in enumerate(dates):
                if date==expected_dates[0]:
                    row['initial_driver_warning']='Inherited cold source F107/F107A70 and source iter; GPI starts at 60s';continue
                sec=int(round(float(ut[i])*3600));expected=driver.at(2023000+int(days[i]),sec)
                values={k:float(n[k][i]) for k in expected}
                errors={k:values[k]-expected[k] for k in expected}
                assert max(map(abs,errors.values()))<1e-10,errors
                driver_rows.append({'file':path.name,'utc':date,**values,**{k+'_expected':v for k,v in expected.items()},'max_absolute_error':max(map(abs,errors.values()))})
            names=set(REQUIRED if primary else ['DEN','ZG','TN','UN','VN','O1','O2','N2','HE'])
            for name in sorted(names):
                v=n[name];v.set_auto_mask(False);raw=np.asarray(v[:]);assert np.isfinite(raw).all(),name
                mask=np.zeros(raw.shape,bool)
                for attr in ['missing_value','_FillValue']:
                    if attr in v.ncattrs():
                        for marker in np.asarray(v.getncattr(attr)).reshape(-1):mask|=raw==np.asarray(marker,dtype=raw.dtype)
                mask|=abs(raw)>1e30
                value=np.ma.array(raw,mask=mask)
                assert value.count()>0,name
                row['fields'][name]={'dimensions':list(v.dimensions),'shape':list(v.shape),'dtype':str(v.dtype),
                                     'units':getattr(v,'units',None),'masked_count':int(mask.sum()),'nonfinite_count':0,
                                     'valid_fraction':float((~mask).mean()),'min_valid':float(value.min()),'max_valid':float(value.max())}
                if name in ['TN','UN','VN','TN_NM','UN_NM','VN_NM']:
                    assert not mask[:,:-1].any() and mask[:,-1].all()
                if name in ['TN','TN_NM']:assert v.units=='K' and value.min()>100 and value.max()<5000
                if name in ['UN','VN','UN_NM','VN_NM']:assert v.units=='cm/s' and abs(value).max()<2e5
                if name in ['O1','O2','N2','HE']:assert v.units=='mmr' and not mask.any() and value.min()>=0 and value.max()<=1.000001
                if name=='DEN':
                    assert not mask.any() and value.min()>0 and v.units=='g/cm3'
                    assert v.dimensions==('time','ilev','lat','lon')
                    row['density_range_kg_m3']=[float(value.min()*1000),float(value.max()*1000)]
                if name=='ZG':
                    assert v.units=='cm' and not mask.any() and (np.diff(raw,axis=1)>0).all()
                    row['top_height_km_by_time']=[[float(z.min()/1e5),float(z.max()/1e5)] for z in raw[:,-1]]
            if not primary:
                total=sum(np.asarray(n[v][:]) for v in ['O1','O2','N2','HE'])
                row['major_mass_mixing_ratio_sum_range']=[float(total.min()),float(total.max())]
                assert abs(total-1).max()<1e-5
            if primary and dates==[expected_dates[1]]:
                checkpoint=inspect_restart(path,[77,23,50]);assert checkpoint['structure_complete'] and checkpoint['record_available']
                checkpoint.update(sha256=row['sha256'],dates=dates,contains_future_records=False,
                                  native_single_record=True,all_fields_checked_finite=True,
                                  time_attributes=row['initial_time_attributes'],actual_resume_tested=False)
        files.append(row)
    assert len(files)==5 and checkpoint is not None
    # Check each sampled runtime GPI print; this is not a claim every step was logged.
    pattern=r'GPI run: mtime=\s*(\d+)\s+(\d+)\s+(\d+) power=\s*([\d.]+) ctpoten=\s*([\d.]+) f107=\s*([\d.]+) f107a=\s*([\d.]+)'
    seen=set()
    for d,h,m,power,cp,f,fa in re.findall(pattern,log):
        expected=driver.at(2023000+int(d),int(h)*3600+int(m)*60);seen.add((int(d),int(h),int(m)))
        for value,key in [(power,'hpower'),(cp,'ctpoten'),(f,'f107d'),(fa,'f107a')]:assert abs(float(value)-expected[key])<=.000501
    assert (78,0,0) in seen and (78,0,10) in seen and (77,23,50) in seen
    (out/'checkpoint_2350_audit.json').write_text(json.dumps(checkpoint,indent=2)+'\n')
    csvpath=ROOT/'results/metrics'/f'{a.run_tag}_drivers.csv'
    with csvpath.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(driver_rows[0]));w.writeheader();w.writerows(driver_rows)
    protected=json.loads((out/'protected_files.json').read_text());changed=[]
    for rel,digest in protected.items():
        path=ROOT/rel
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:changed.append(rel)
    assert not changed,changed
    result={'calendar_and_drivers_pass':True,'basic_fields_pass':True,'model_launches':1,
            'steps':1450,'files':files,'total_netcdf_bytes':sum(f['bytes'] for f in files),
            'verified_runtime_GPI_unique_times':len(seen),'checkpoint_valid_native_structure':True,
            'restart_continuation_verified':False,'spinup_converged':False,'swarm_use_validated':False,
            'protected_file_count':len(protected),'changed_protected_files':changed,'suspicious_log_lines':suspicious}
    (out/'crossday_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))
if __name__=='__main__':main()
