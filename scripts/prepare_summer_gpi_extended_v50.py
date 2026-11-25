"""V50 real driver acquisition receipt validation and isolated GPI candidate."""
import csv
from datetime import timedelta, datetime, timezone
import json
import math
from pathlib import Path
import subprocess

from netCDF4 import Dataset
import numpy as np

import prepare_summer_gpi_candidate_v43 as old
from atmosphere.autumn_gpi_validation import independent_at, schema, MEAN_ATOL, DRIVER_ATOL
from diagnose_summer_component_convergence_v49 import identity

ROOT=old.ROOT
OUT=ROOT/'experiments/thermosphere_summer_spinup_add7_v50'
FILE=OUT/'gpi_2022_summer_add7_candidate_v50.nc'
V49=ROOT/'experiments/thermosphere_summer_component_convergence_v49'
OLD=ROOT/'experiments/thermosphere_summer_gpi_candidate_v43'
BASE='16dd478b203d98f866d46fb2022e313e587b5c05'
RAW=old.stamp('2022-05-29')
START=old.stamp('2022-05-31')
STOP=old.stamp('2022-06-23')
TARGET=old.stamp('2022-06-21')
TIMES=[RAW+timedelta(days=i) for i in range(28)]
FGRID={RAW+timedelta(days=i) for i in range(-40,68)}
KGRID={day+timedelta(hours=h) for day in TIMES for h in range(0,24,3)}
KNEW={t for t in KGRID if t<old.RAW}
require=old.require


def dump(name,value):
    with (OUT/name).open('x') as f:
        json.dump(value,f,indent=2,allow_nan=False)
        f.write('\n')


def verify_sha(p,digest):
    require(old.sha(p.read_bytes())==digest,f'SHA changed: {p}')


def pin(p):
    tracked=subprocess.check_output(['git','show',f'{BASE}:{p.relative_to(ROOT)}'],cwd=ROOT)
    require(p.read_bytes()==tracked,f'Frozen Git asset changed: {p.name}')
    return json.loads(tracked)


def protection():
    manifest=pin(V49/'publication_SHA256.json')
    for k,d in (manifest | pin(V49/'result.json')['local_detail']).items():
        verify_sha(ROOT/k,d)
    histories=identity()
    pin(ROOT/'experiments/thermosphere_shrinkage_unseen_prereg_v37/preregistered_protocol.json')
    return {'V49_entries':len(manifest)+1,'V48_raw_volumes':len(histories['A']['inventory'])+
            len(histories['B']['inventory']),'raw_run_ids':[histories[k]['run_id'] for k in ('A','B')]}


def grid(solar,kp):
    require(set(solar)==FGRID and set(kp)==KGRID,'Incomplete verified driver calendar')


def audited_inputs():
    source=pin(OLD/'input_freeze.json')['sources']
    acq=json.loads((OUT/'acquisition.json').read_text())
    require(acq['HTTP']==200 and acq['URL'].startswith('https://kp.gfz.de/app/json/') and
            'index=Kp&status=def' in acq['URL'],'Wrong definitive receipt')
    require(acq['raw_path'].startswith('data/raw/thermosphere_summer_spinup_add7_v50/'),'Wrong acquisition path')
    payload=ROOT/acq['raw_path']
    require(payload.stat().st_size==acq['bytes'],'Wrong payload length')
    source[acq['raw_path']]=acq['SHA256']
    primary={'Fobs':{},'Kp':{}}
    independent={'Fobs':{},'Kp':{}}
    source_counts={}
    for name, digest in source.items():
        raw=(ROOT/name).read_bytes()
        data=old.checked(raw,digest)
        key='Kp' if Path(name).name.startswith('Kp_') else 'Fobs'
        verified=old.raw_records(data,key)
        built=old.decode(data,key)
        if key=='Kp':
            wanted=KNEW if name==acq['raw_path'] else KGRID-KNEW
            require(set(verified)==wanted,'Kp source time domain mismatch')
        domain=KGRID if key=='Kp' else FGRID
        if key=='Fobs':
            require(all(not (t.hour or t.minute or t.second) for t in verified),'Fobs not UTC midnight')
        seen=0
        for t,x in verified.items():
            if t in domain:
                require(t not in independent[key],'Overlapping source keys')
                independent[key][t]=x
                primary[key][t]=built[t]
                seen+=1
        source_counts[name]=seen
    grid(independent['Fobs'],independent['Kp'])
    return source,source_counts,primary,independent


def native(path,solar,kp):
    require(schema(path)==schema(ROOT/old.V22/'gpi_2022_autumn.nc'),'Invalid native schema')
    means={t:math.fsum(solar[t+timedelta(days=i)] for i in range(-40,41))/81 for t in TIMES}
    with Dataset(path,'r') as n:
        require(n.data_model=='NETCDF3_CLASSIC' and len(n.dimensions['ndays'])==28 and len(n.dimensions['nkp'])==8,'Wrong dimensions')
        require((n.yearday_beg,n.yearday_end)==(2022151,2022174) and n.averaging_window_days==81
            and n.averaging_kind=='centered' and n.time_standard=='UTC','Wrong GPI padding or convention')
        data={}
        for k in ('year_day','f107d','f107a','kp'):
            a=n[k][:]
            require(not np.ma.getmaskarray(a).any() and np.isfinite(a).all(),'Fill or nonfinite')
            data[k]=np.asarray(a)
        require(np.array_equal(data['year_day'],[int(t.strftime('%Y%j')) for t in TIMES]),'UTC node mismatch')
        require(np.array_equal(data['f107d'],[solar[t] for t in TIMES]),'Fobs mismatch')
        require(np.array_equal(data['kp'].ravel(),[kp[t] for t in sorted(KGRID)]),'Kp mismatch')
        diff=float(max(abs(data['f107a']-list(means.values()))))
        require(diff<MEAN_ATOL,'Centered 81-day average mismatch')
    return means,{'schema':schema(path),'calendar':data['year_day'].tolist(),'F107a_sfu':data['f107a'].tolist(),
                 '81_day_max_abs':diff,'ranges':{k:[float(v.min()),float(v.max())] for k,v in data.items()}}


def compare_vectors(a,b,name):
    errors={k:abs(a[k]-b[k]) for k in a}
    require(all(v<DRIVER_ATOL for v in errors.values()),name)
    return errors


def verify_queries(path,solar,kp,means):
    new=old.GpiDriver(path)
    verify_sha(OLD/'gpi_2022_summer_candidate_v43.nc',pin(OLD/'verification.json')['sha256'])
    previous=old.GpiDriver(OLD/'gpi_2022_summer_candidate_v43.nc')
    regular={START+timedelta(minutes=i) for i in range(33121)}
    boundary={d+timedelta(seconds=s) for d in TIMES[2:-2]
              for h in range(0,24,3) for s in (h*3600-1,h*3600,h*3600+1,h*3600+5399,h*3600+5400,h*3600+5401)
              if START<=d+timedelta(seconds=s)<=STOP}
    differences={}
    overlap={}
    samples={}
    common=0
    for t in sorted(regular|boundary):
        yd=int(t.strftime('%Y%j'))
        seconds=t.hour*3600+t.minute*60+t.second
        got=new.at(yd,seconds)
        for k,v in compare_vectors(got,independent_at(t,solar,means,kp),'GPI interpolation differs').items():
            differences[k]=max(differences.get(k,0.),v)
        if old.START<=t<=STOP:
            common+=1
            for k,v in compare_vectors(got,previous.at(yd,seconds),'Original shared UTC drive differs').items():
                overlap[k]=max(overlap.get(k,0.),v)
        if t in {START,TARGET,STOP}:
            samples[t.isoformat()]=got
    return dict(minute_nodes=len(regular),additional_boundary_nodes=len(boundary-regular),
                common_nodes=common,all_node_max_abs=differences,old_common_max_abs=overlap,samples=samples)


def main():
    require(OUT.resolve()==OUT and not FILE.exists(),'Do not overwrite candidate')
    history=protection()
    sources,counts,primary,verified=audited_inputs()
    creator=ROOT/'scripts/prepare_summer_gpi_extended_v50.py'
    frozen_sources=pin(OLD/'input_freeze.json')
    for path,expected in frozen_sources['algorithm_sha256'].items(): verify_sha(ROOT/path,expected)
    dump('input_freeze.json',{'sources':sources,'source_counts':counts,'Fobs':108,'Kp':224,'new_Kp':56,
        'model_interval':[START.isoformat(),STOP.isoformat()],'STEP':60,'steps':33120,'old_inventory':history,
        'frozen_algorithm_sha256':frozen_sources['algorithm_sha256'],'generator_sha256':old.sha(creator.read_bytes())})
    with (OUT/'definitive_Kp_56.csv').open('x',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['UTC','Kp','status','units'])
        for day in sorted(KNEW): w.writerow([day.isoformat(),verified['Kp'][day],'def','1'])
    built=old.arrays(primary['Fobs'],primary['Kp'],TIMES[0].date(),TIMES[-1].date())
    old.write_gpi(FILE,*built,START.date(),STOP.date())
    with Dataset(FILE,'r+') as n:
        n.engineering_status='GPI_ADD7_ENGINEERING_CANDIDATE'
        n.authorized_for_model_run='NO'
    FILE.chmod(0o444)
    means,evidence=native(FILE,verified['Fobs'],verified['Kp'])
    dt=verify_queries(FILE,verified['Fobs'],verified['Kp'],means)
    dump('GPI_verification.json',dict(state='GPI_ADD7_CANDIDATE_VERIFIED',numeric='GPI_NUMERIC_VERIFIED',
         runtime='GPI_RUNTIME_NOT_RUN',candidate_state='GPI_ADD7_ENGINEERING_CANDIDATE',
         SHA256=old.sha(FILE.read_bytes()),bytes=FILE.stat().st_size,
         created_UTC=datetime.now(timezone.utc).isoformat(), tolerance={'mean':MEAN_ATOL,'driver':DRIVER_ATOL},
         native=evidence,**dt))


if __name__=='__main__':
    main()
