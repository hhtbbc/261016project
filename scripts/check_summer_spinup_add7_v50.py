"""Independent raw-data replay and CPU preparation tests; no model execution."""
from contextlib import ExitStack
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from netCDF4 import Dataset
import numpy as np

import analyze_summer_spinup_add7_v50 as alignment
import verify_summer_spinup_add7_v50 as review
import preflight_summer_spinup_add7_v50 as o
import prepare_summer_gpi_extended_v50 as g

OUT,ROOT=g.OUT,g.ROOT


def replay_input():
    raw=json.loads((OUT/'input_freeze.json').read_text())['sources']
    solar,kp={},{}
    for filename,expected in raw.items():
        path=ROOT/filename
        g.verify_sha(path,expected)
        p=json.loads(path.read_bytes(),parse_float=Decimal)
        key, = p.keys()&{'Fobs','Fadj','Kp'}
        assert key in ('Fobs','Kp') and p['meta']['source']=='GFZ Potsdam'
        u=p.get('units',p['meta'].get('units'))
        if isinstance(u,dict):u=u.get(key)
        assert u in (None,{'Fobs':'sfu','Kp':'1'}[key])
        ts=[datetime.strptime(t,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc) for t in p['datetime']]
        assert len(ts)==len(set(ts))==len(p[key])
        if key=='Kp':assert p['status']==['def']*len(ts)
        for stamp, value in zip(ts,p[key]):
            v=Decimal(value)
            assert v.is_finite() and (v>0 if key=='Fobs' else 0<=v<=9)
            target,domain=(solar,g.FGRID) if key=='Fobs' else (kp,g.KGRID)
            if stamp in domain:
                assert stamp not in target
                target[stamp]=v
    f=[g.old.stamp('2022-04-19')+timedelta(days=i) for i in range(108)]
    k=[g.old.stamp('2022-05-29')+timedelta(hours=3*i) for i in range(224)]
    assert sorted(solar)==f and sorted(kp)==k
    with Dataset(g.FILE) as c:
        assert c.data_model=='NETCDF3_CLASSIC' and len(c.dimensions['ndays'])==28 and c['kp'].shape==(28,8)
        np.testing.assert_array_equal(c['year_day'][:],[(g.old.stamp('2022-05-29')+timedelta(days=i)).year*1000+
                                    (g.old.stamp('2022-05-29')+timedelta(days=i)).timetuple().tm_yday for i in range(28)])
        np.testing.assert_array_equal(c['f107d'][:],[float(solar[t]) for t in f[40:68]])
        np.testing.assert_array_equal(c['kp'][:].ravel(),[float(kp[t]) for t in k])
        ref=np.array([float(sum(solar[t] for t in f[i:i+81])/81) for i in range(28)])
        err=float(np.max(abs(c['f107a'][:]-ref)))
        assert err<g.MEAN_ATOL
    return {k:float(v) for k,v in solar.items()},{k:float(v) for k,v in kp.items()},err


def make_fixture(folder,when):
    folder.mkdir()
    with Dataset(folder/'secondary_021.nc','w',format='NETCDF3_CLASSIC') as n:
        for k,v in [('time',24),('ilev',1),('lev',1),('lat',2),('lon',2)]:
            n.createDimension(k,v)
            t=n.createVariable(k,'f8',(k,))
            if k=='time':
                t.units='hours since 2022-05-31 00:00:00'
                t[:]=range(when-23,when+1)
            else:t[:]=0
        for k in (*alignment.science.KEYS,'ZG'):
            v=n.createVariable(k,'f8',('time','ilev' if k in ('DEN','ZG') else 'lev','lat','lon'))
            v.units='cm' if k=='ZG' else alignment.science.UNITS[k]
            v[:]=1.


def main():
    findings=[]
    def ok(name,test=True):
        assert test,name
        findings.append(name)
    def reject(name,func):
        try:func()
        except (ValueError,KeyError,OSError):
            findings.append(name)
            return
        raise AssertionError('Unexpected acceptance '+name)
    solar,kp,error=replay_input()
    ok('Independent exact GFZ calendar and native values')
    acq=json.loads((OUT/'acquisition.json').read_text())
    raw=json.loads((ROOT/acq['raw_path']).read_text())
    parse=g.old.raw_records
    ok('56 new definitive points',set(parse(raw,'Kp'))==g.KNEW)
    reject('Nondefinitive Kp',lambda:parse(raw|{'status':['pre']*56},'Kp'))
    reject('Missing Kp',lambda:g.grid(solar,{t:x for t,x in kp.items() if t!=min(kp)}))
    reject('Duplicate Kp',lambda:parse(raw|{'datetime':[raw['datetime'][0]]*56},'Kp'))
    reject('Wrong Kp units',lambda:parse(raw|{'units':'nT'},'Kp'))
    reject('Missing Fobs',lambda:g.grid({},kp))
    reject('Adjusted flux substitution',lambda:parse({'Fadj':[100],'meta':{'source':'GFZ Potsdam'}},'Fobs'))
    with tempfile.TemporaryDirectory(dir=OUT/'tests') as work:
        stage=Path(work)
        for name in ('average','padding','dimensions'):
            path=stage/(name+'.nc')
            path.write_bytes(g.FILE.read_bytes())
            with Dataset(path,'r+') as n:
                if name=='average':n['f107a'][0]+=1.
                if name=='padding':n.yearday_beg=2022150
                if name=='dimensions':n.renameDimension('ndays','bad_dim')
            reject('Corrupt '+name,lambda:g.native(path,solar,kp))
        a,b=stage/'fake_a',stage/'fake_b'
        make_fixture(a,504); make_fixture(b,504)
        x,y,_=alignment.read_frame((a,b),g.TARGET,independent=True)
        ok('Real NetCDF synthetic V50 hour 504 passes UTC and schema',np.array_equal(x['DEN'],y['DEN']))
        norm=review.verified_stats(x['DEN'],y['DEN'],np.ones((1,2,1)),'DEN')
        ok('Independent statistic zero on synthetic identical fields',norm['RMSE']==0 and norm['relative_P95']==0)
        with Dataset(b/'secondary_021.nc','r+') as n:n['time'][-1]=336
        reject('Wrong B UTC fails',lambda:alignment.read_frame((a,b),g.TARGET))
    reject('Common UTC drift',lambda:g.compare_vectors({'f107d':100.},{'f107d':101.},'drift'))
    reject('Initial seed hash changed',lambda:g.verify_sha(OUT/'b.nc','0'*64))
    reject('Long SOURCE',lambda:o.safe_source(OUT/'probe_cwd','/'+'x'*147))
    files=[(OUT/(k+'.namelist')).read_text() for k in o.RUNS]
    template=o.v47.INPUT.read_text()
    expected=o.expected_pair(template)
    o.validate(files,expected)
    for name,x in [('Wrong SOURCE_START',files[1].replace('172 0 0','80 0 0')),
                   ('Physics drift',files[1].replace('HEELIS','OTHER')),
                   ('START_DAY drift',files[1].replace('START_DAY = 151','START_DAY = 158')),
                   ('Primary volume missing',files[1].replace(", 'primary_024.nc'",'')),
                   ('Secondary volume missing',files[1].replace(", 'secondary_023.nc'",''))]:
        reject(name,lambda:o.validate([files[0],x],expected))
    reject('Step count wrong',lambda:o.validate(files,expected,23040))
    reject('Old target index 336 in V50',lambda:alignment.coordinate(g.START,g.TARGET,336))
    ok('Same absolute target and late UTC',alignment.alignment(g.TARGET)==(504,336) and
       [alignment.alignment(x) for x in (alignment.LATE_UTC[0],alignment.LATE_UTC[-1])]==[(528,360),(552,384)])
    binding=o.v47.sha(o.PLAN)
    reject('No new launch authorization',lambda:o.next_admission(binding,'A',None,True))
    auth=dict(scope='V51 2022 add7 A then B CPU',plan_sha256=binding,attempts_each=1,approved=True,automatic_retry=False)
    o.next_admission(binding,'A',auth,True)
    ok('Synthetic next-stage receipt yes, no claim written')
    reject('A claim reused',lambda:o.next_admission(binding,'A',auth,False))
    reject('B before independent A',lambda:o.next_admission(binding,'B',auth,True))
    reject('GPU requested',lambda:o.check_gpu({'CUDA_VISIBLE_DEVICES':'0'}))
    from audit_summer_assets_v38 import sealed_read
    reject('Unseen Swarm density read',lambda:sealed_read(object(),'density',[]))
    protocol=ROOT/'experiments/thermosphere_shrinkage_unseen_prereg_v37/preregistered_protocol.json'
    frozen=g.pin(protocol)
    ok('V37 exact published protocol',frozen['candidates']['ShrinkageHalf']==.5 and frozen['first_pair']==['2021-06-21','2022-06-21'])
    reject('History corruption',lambda:g.verify_sha(protocol,'0'*64))
    original=json.loads((OUT/'input_freeze.json').read_text())['old_inventory']
    current=g.protection()
    ok('66 verified histories and V49 frozen checks match',current==original and current['V48_raw_volumes']==66)
    p=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/preflight_summer_spinup_add7_v50.py'),'--execute'],
                     cwd=ROOT,capture_output=True,text=True)
    ok('Real offline CLI refuses execution',p.returncode!=0 and 'new V51 authorization' in p.stderr)
    reject('Future science requires actual receipts',alignment.evidence)
    nxt=json.loads((OUT/'configuration.json').read_text())
    for row in nxt['Fortran_probe']:
        ok('Fortran real read '+row['role'],row['probe_exit']==0 and row['required_fields']==34 and row['source_bytes']==7)
    ok('No launch directories/claims',not any((OUT/name).exists() for name in o.RUNS))
    g.dump('independent.json',dict(state='PASS',count=len(findings),tests=findings,Decimal_mean_max_abs_sfu=error,
        raw_Fobs=len(solar),raw_Kp=len(kp),historic=current,GPI_sha256=o.v47.sha(g.FILE),new_model_runs=0,
        unseen_target_density_reads=0,GPU=0,analysis_real_future_data_not_run=True))


if __name__=='__main__':
    main()
