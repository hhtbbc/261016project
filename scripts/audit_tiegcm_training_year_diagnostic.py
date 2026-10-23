"""Read-only audit of an existing single-launch 2022 run; no model launch."""
from pathlib import Path
import argparse, importlib.util, json, re, hashlib
import numpy as np
from netCDF4 import Dataset, num2date
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('runner',ROOT/'scripts/run_tiegcm_training_year_diagnostic.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-tag',required=True);a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+',a.run_tag):raise ValueError('Invalid tag')
    folder=runner.inside(ROOT/'experiments'/a.run_tag)
    output=folder/'diagnostic_audit.json'
    if output.exists():raise FileExistsError(output)
    log=(ROOT/'logs'/f'{a.run_tag}.log').read_text()
    result={'files':[],'driver_comparisons':[],'initial_record_is_inherited':True}
    assert 'init: iyear= 2022 iday=   95' in log
    assert 'calling apxparm: start_year= 2022' in log
    assert 'Initial requested iyear=2022 iday= 95 iutsec=        60' in log
    suspicious=re.findall(r'(?im)^.*(?:\bNaN\b|\bInf\b|WARNING|ERROR|bad isec_req).*$' ,log)
    result['suspicious_log_lines']=suspicious
    assert not suspicious
    pattern=r'GPI run: mtime=\s*(\d+)\s+(\d+)\s+(\d+) power=\s*([\d.]+) ctpoten=\s*([\d.]+) f107=\s*([\d.]+) f107a=\s*([\d.]+)'
    matches=re.findall(pattern,log);seen=set()
    for day,h,m,power,cp,f,fa in matches:
        sec=int(h)*3600+int(m)*60;expected=runner.expected_drivers(sec);seen.add(sec)
        assert int(day)==95
        for v,name in [(power,'hpower'),(cp,'ctpoten'),(f,'f107d'),(fa,'f107a')]:
            assert abs(float(v)-expected[name])<=.000501
    assert seen==set(range(60,601,60))
    result['log_unique_verified_seconds']=sorted(seen)
    for path in sorted(folder.glob('*.nc')):
        item={'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,
              'sha256':runner.sha(path),'fields':{}}
        with Dataset(path) as n:
            dates=[str(t) for t in num2date(n['time'][:],n['time'].units)]
            item['dates']=dates;assert all(t.startswith('2022-04-05 ') for t in dates)
            assert np.all(n['year'][:]==2022) and np.all(n['day'][:]==95)
            assert np.all(n['calendar_advance'][:]==1) and int(n['timestep'][:])==60
            elapsed=(np.asarray(n['ut'][:])*3600).round().astype(int)
            for i,s in enumerate(elapsed):
                if s==0:
                    item['inherited_initial_drivers']={v:float(n[v][i]) for v in ['f107d','f107a','Kp','hpower','ctpoten']}
                    continue
                expected=runner.expected_drivers(int(s))
                differences={}
                for name,e in expected.items():
                    var='Kp' if name=='kp' else name
                    differences[var]=float(n[var][i])-e
                    assert abs(differences[var])<1e-10,(var,s,differences[var])
                result['driver_comparisons'].append({'seconds':int(s),'expected':expected,'actual_minus_expected':differences})
            for name in ['DEN','ZG','Z','TN','UN','VN','WN','TLBC','ULBC','VLBC','O1','O2','N2','HE']:
                if name not in n.variables:continue
                v=n[name];v.set_auto_mask(False);raw=np.asarray(v[:]);invalid=~np.isfinite(raw)
                # Nonfinite values are never excused as ordinary padding.
                assert not invalid.any(),name
                mask=np.zeros(raw.shape,dtype=bool)
                for attr in ['_FillValue','missing_value']:
                    if attr in v.ncattrs():
                        for marker in np.asarray(v.getncattr(attr)).reshape(-1):mask|=raw==np.asarray(marker,dtype=raw.dtype)
                mask|=abs(raw)>1e30
                data=np.ma.array(raw,mask=mask)
                item['fields'][name]={'units':getattr(v,'units',None),'dimensions':list(v.dimensions),
                                     'shape':list(raw.shape),'masked_count':int(mask.sum()),
                                     'min_valid':float(data.min()),'max_valid':float(data.max())}
                if name in ['TN','UN','VN','O1','O2','N2','HE']:
                    assert v.dimensions==('time','lev','lat','lon')
                if name in ['TN','UN','VN']:
                    assert not mask[:,:-1].any() and mask[:,-1].all()
                if name in ['O1','O2','N2','HE']:assert not mask.any()
                if name=='TN':assert v.units=='K' and data.min()>100 and data.max()<5000
                if name in ['UN','VN']:assert v.units=='cm/s' and abs(data).max()<2e5
                if name in ['O1','O2','N2','HE']:assert v.units=='mmr' and data.min()>=0 and data.max()<=1.000001
                if name=='DEN':
                    assert not mask.any() and data.min()>0 and v.units=='g/cm3'
                    assert v.dimensions==('time','ilev','lat','lon')
                    item['density_range_kg_m3']=[float(data.min()*1000),float(data.max()*1000)]
                if name=='ZG':
                    assert not mask.any() and v.units=='cm' and (np.diff(raw,axis=1)>0).all()
                    item['top_height_km_by_time']=[[float(x.min()/1e5),float(x.max()/1e5)] for x in raw[:,-1]]
            if all(v in n.variables for v in ['O1','O2','N2','HE']):
                total=sum(np.asarray(n[v][:])[:,:-1] for v in ['O1','O2','N2','HE'])
                item['major_mmr_sum_range']=[float(total.min()),float(total.max())]
        result['files'].append(item)
    assert len(result['files'])==2
    status=json.loads((folder/'run_status.json').read_text());assert status['normal_exit'] and status['returncode']==0
    result.update(calendar_pass=True,drivers_pass=True,basic_fields_pass=True,
                  engineering_short_startup_pass=True,spinup_complete=False,usable_for_swarm_validation=False,
                  initial_record_warning='t=0 contains inherited restart fields/scalars, GPI starts at 60 s',
                  total_netcdf_bytes=sum(x['bytes'] for x in result['files']))
    output.write_text(json.dumps(result,indent=2)+'\n');print(output)
if __name__=='__main__':main()
