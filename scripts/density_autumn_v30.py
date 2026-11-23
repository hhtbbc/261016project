"""V30 daily admission, history-only freeze, isolated poison and exclusive scoring."""
import csv
import datetime as dt
import hashlib
import json
import resource
from pathlib import Path
import subprocess
import sys
import time

import cdflib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from atmosphere.causal_observation_operator import map_a_queries, observe_map_a
from atmosphere.hourly_tiegcm_observation import HourlyTiegcmObservation
from evaluation.causal_density_latitude import (
    BANDS, apply_global, apply_latitude, assess_joint, fit_global_history, fit_history,
    latitude_band, supported_metric,
)
from evaluation.late_day_correction import RollingOrigin
from evaluation.swarm_density_comparison import quality_mask
from runtime.readonly_audit_warning_channel import WarningChannel
from runtime.tiegcm_rank_exit import digest as sha, write_once

EXP = ROOT / 'experiments'
OUT = EXP / 'thermosphere_autumn_density_validation_v30'
PROTOCOL = EXP / 'thermosphere_independent_date_validation_plan_v20/preregistered_protocol.json'
PROTOCOL_SHA = 'eb27a080199d656f6018f47834cc9eaef07897009360ca184d6511e4d3aeb2c4'
V21 = EXP / 'thermosphere_autumn_data_acquisition_v21'
V23 = EXP / 'thermosphere_autumn_mareqx_config_v23'
V24 = EXP / 'thermosphere_autumn_2021_formal_run_v24'
V26 = EXP / 'thermosphere_autumn_2021_postrun_closure_v26'
V29 = EXP / 'thermosphere_autumn_2022_formal_run_v29'
SPRING = {2021: EXP / 'causal_density_new_date_validation_v1',
          2022: EXP / 'tiegcm_2022_mar25_density_validation_v18'}
BASE = 'f42cb5e3954147b037fd8183424e83bc25ef17f4'
YEARS = (2021, 2022)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(p):
    return json.loads(p.read_text())


def rows(p):
    with p.open(newline='') as f:
        return list(csv.DictReader(f))


def table(path, data):
    with path.open('x', newline='') as f:
        keys = list(dict.fromkeys(key for row in data for key in row))
        writer = csv.DictWriter(f, fieldnames=keys, lineterminator='\n')
        writer.writeheader()
        writer.writerows(data)


def pin(path, wanted):
    require(path.resolve(strict=True) == path and sha(path) == wanted, f'SHA or path drift: {path.name}')


def git_pin(path):
    name = str(path.relative_to(ROOT))
    wanted = hashlib.sha256(subprocess.check_output(['git', 'show', f'{BASE}:{name}'], cwd=ROOT)).hexdigest()
    pin(path, wanted)
    return wanted


def day(year):
    return f'{year}-09-23'


def cutoff(year, h):
    return np.datetime64(f'{day(year)}T{h:02d}:00:00', 'ns')


def ids(utc):
    return hashlib.sha256(utc.astype('datetime64[ns]').astype('<i8').tobytes()).hexdigest()


def masks(year, hour, utc):
    windows = RollingOrigin(day(year), hour).masks(utc)
    windows['block_0_1h'] = windows['future_1h']
    return windows


def resources(start):
    return dict(wall_s=time.perf_counter()-start, CPU_s=time.process_time(),
                peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def cdf_data(entry, year, h=None, density=True):
    path = ROOT / entry['path']
    pin(path, entry['SHA256'])
    with cdflib.CDF(path) as c:
        utc = cdflib.cdfepoch.to_datetime(c.varget('time')).astype('datetime64[ns]')
        require(np.array_equal(utc, cutoff(year, 0) + np.arange(2880)*np.timedelta64(30,'s')),
                'Wrong CDF UTC grid')
        require('DNSAPOD_2__' in path.name and path.stem.endswith('_0301')
                and c.globalattsget()['TITLE']==[path.stem]
                and c.globalattsget()['TIME SYSTEM']==['UTC'] and c.varinq('time').Data_Type==31,
                'Wrong CDF product or time system')
        for name,units in [('density','kg/m3'),('latitude','deg'),('longitude','deg'),('altitude','m')]:
            require(c.varattsget(name)['UNITS']==units, f'Wrong {name} CDF units')
        indices = np.flatnonzero((utc>=cutoff(year,h)-np.timedelta64(3,'h')) & (utc<cutoff(year,h))) if h else np.arange(2880)
        a = dict(utc=utc[indices])
        fields = ['latitude','longitude','altitude','validity_flag'] + (['density'] if density else [])
        for key in fields:
            a[key] = c.varget(key,startrec=int(indices[0]),endrec=int(indices[-1]))
    coord = np.isfinite(a['latitude']) & np.isfinite(a['longitude']) & np.isfinite(a['altitude'])
    coord &= (abs(a['latitude'])<=90) & (abs(a['longitude'])<=180) & (a['altitude']>0)
    a['quality'] = coord & (quality_mask(a['density'],a['validity_flag'])[0] if density else a['validity_flag']==0)
    require(a['quality'].all(), 'Unexpected quality or coordinate exclusion')
    return a


def native_queries(a, info, year, start, stop, label):
    files = [ROOT / x['path'] for x in info['target_models']]
    expected = {path.name: row['SHA256'] for path,row in zip(files,info['target_models'])}
    warnings = OUT / f'{label}_warnings_local'
    warnings.mkdir()
    reader = ROOT / 'src/atmosphere/hourly_tiegcm_observation.py'
    with WarningChannel(warnings, {reader:info['reader_SHA256']}) as channel:
        provider = HourlyTiegcmObservation(files,expected,str(start),str(stop),info['run_id'])
        pred = []
        try:
            for q in map_a_queries(a['utc'],a['latitude'],a['longitude'],a['altitude']):
                result,_ = observe_map_a(provider,q)
                require(result.valid and len(result.metadata['columns'])==8,'Map-A admission failed')
                pred.append(result.rho_kg_m3)
        finally:
            provider.close()
    return np.array(pred),dict(samples=len(pred),column_checks=8*len(pred),
                               extrapolation=False,zero_weight_columns_checked=True,warnings=channel.count)


def prepare():
    require(OUT.resolve()==OUT and ROOT==Path.cwd().resolve(), 'Wrong project location')
    OUT.mkdir()
    start=time.perf_counter()
    pin(PROTOCOL,PROTOCOL_SHA)
    v20=load(PROTOCOL)
    core=v20['fixed_scientific_core']
    source_pins={key:item for key,item in core.items() if key.endswith('_source')}
    for item in source_pins.values():
        pin(ROOT/item['path'],item['SHA256'])
    for name in ('src/evaluation/late_day_correction.py','src/evaluation/swarm_density_comparison.py',
                 'src/atmosphere/causal_density_correction.py','src/atmosphere/tiegcm_density_provider.py'):
        source_pins[name]=dict(path=name,SHA256=git_pin(ROOT/name))
    v21_audit=V21/'Swarm_audit.json'
    evidence={str(p.relative_to(ROOT)):git_pin(p) for p in (
        v21_audit,V21/'activity_conditions.csv',V23/'seed_policy_receipt.json',
        V26/'closure_release.json',V26/'formal_once/main_acceptance.json',
        V26/'independent_recovery_once/independent_review.json',V26/'independent_recovery_once/result.json',
        V29/'result.json',V29/'main_acceptance_snapshot.json',V29/'independent_review.json',
    )}
    require(load(V23/'seed_policy_receipt.json')['SEED_POLICY']=='A_MAREQX_APPROVED', 'Seed policy missing')
    sources={}
    for year,run_id,directory in [(2021,'18726974f5d3450ba61f82c23c8da3a0',V24),
                                  (2022,'4a89e99eaee548f28240ea47f4b98e47',V29)]:
        v26=load(V26/'closure_release.json')
        result=load(V26/'independent_recovery_once/result.json' if year==2021 else V29/'result.json')
        main=load(V26/'formal_once/main_acceptance.json' if year==2021 else V29/'main_acceptance_snapshot.json')
        ind=load(V26/'independent_recovery_once/independent_review.json' if year==2021 else V29/'independent_review.json')
        state=result.get('V26_POSTRUN_VERIFICATION',result.get('overall'))
        require(state=='ENGINEERING_PASS' and main['overall']=='PASS' and ind['independent_raw_checks']=='PASS'
                and main['run_id']==ind['identity']['run_id']==run_id and (year==2022 or v26['run_id']==run_id)
                and ind['identity']['actual_steps']==23040,'Engineering evidence mismatch')
        require(ind['independent_queries']['success']==2880 and ind['independent_queries']['column_checks']==23040
                and ind['independent_queries']['no_extrapolation'],'Prior query evidence mismatch')
        base=V23/str(year);run=base/'actual_run'
        proto=base/'launch_protocol.json'
        evidence[str(proto.relative_to(ROOT))]=git_pin(proto)
        p=load(proto)
        require(p['year']==year and p['target_date']==day(year) and ROOT/p['cwd']==run,'Wrong run')
        require(load(base/'execution_claim_local.json')['run_id']==run_id,'Wrong original claim')
        for key in ('input','source','GPI','executable','hapi','observation'):
            pin(ROOT/p[key]['path'],p[key]['SHA256'])
        pin(run/'input.inp',p['input']['SHA256'])
        cdf=load(v21_audit)[str(year)]['CDF']
        require({k:cdf[k] for k in ('path','SHA256')}==p['observation'],'V21 CDF mismatch')
        contract=load(ROOT/p['hapi']['path'])
        require(contract['x_dataset']=='SW_OPER_DNSAPOD_2_' and any('GRS80' in x.get('description','')
                for x in contract['parameters']),'GRS80 contract mismatch')
        meta=cdf_data(cdf,year,density=False)
        manifest=directory/'model_output_manifest.csv'
        evidence[str(manifest.relative_to(ROOT))]=git_pin(manifest)
        vols=rows(manifest)
        require(len(vols)==len({row['file'] for row in vols})==33
                and {row['file'] for row in vols}=={x.name for x in run.glob('*.nc')},
                'Unexpected model volumes')
        verified=[]
        for row in vols:
            path=run/row['file']
            pin(path,row['SHA256'])
            require(path.stat().st_size==int(row['bytes']), 'Volume byte count mismatch')
            verified.append(dict(row,path=str(path.relative_to(ROOT))))
        contract_index=lambda data: {x['file']:(x['SHA256'],int(x['bytes']),int(x['records']),
                                             x['first_UTC'],x['last_UTC']) for x in data}
        require(contract_index(verified)==contract_index(ind['outputs']['files']), 'Engineering manifest does not bind all volumes')
        target=[x for x in verified if x['file'].startswith('secondary')
                and x['last_UTC']>=day(year)+'T00:00:00Z'
                and x['first_UTC']<=f'{year}-09-24T00:00:00Z']
        require(len(target)==2,'Wrong target interpolation volumes')
        sources[str(year)]=dict(run_id=run_id,CDF=cdf,hapi=p['hapi'],frozen_inputs=p,
            full_model=verified,target_models=target,reader_SHA256=core['hourly_reader_source']['SHA256'],
            engineering_status=state,prior_eight_column_coverage=2880,metadata_nominal=len(meta['utc']))
    for directory in SPRING.values():
        for name in ('metrics.csv','region_metrics.csv','joint_assessment.csv','correction_parameters.json'):
            p=directory/name
            evidence[str(p.relative_to(ROOT))]=git_pin(p)
    write_once(OUT/'source_manifest.json',dict(years=sources,science_sources=source_pins,previous_SHA256=evidence))
    write_once(OUT/'admission.json',dict(PASS=True,protocol_SHA256=PROTOCOL_SHA,identity=v20['identity'],
        seed_policy='A_MAREQX_APPROVED',metadata_only=True,verified_model_volumes=66,
        prior_quality_and_coverage_reused=True,resource=resources(start)))


def fit(a,p,year,h):
    if h==6:
        f,_=fit_global_history(a['utc'],a['latitude'],a['density'],p,a['quality'],day=day(year),hour=h)
        return {'GlobalAdaptive06':f}
    f,_=fit_history(a['utc'],a['latitude'],a['density'],p,a['quality'],day=day(year),hour=h)
    return {'GlobalAdaptive18':f['global_fit'],'LatitudeAdaptive18':f['latitude']}


def history():
    start=time.perf_counter()
    require(load(OUT/'admission.json')['PASS'], 'Admission incomplete')
    source=load(OUT/'source_manifest.json')
    frozen={}
    for year in YEARS:
        info=source['years'][str(year)]
        settings={};support={}
        for hour in (6,18):
            a=cdf_data(info['CDF'],year,hour)
            require(len(a['utc'])==360, 'Incorrect historical record count')
            t=cutoff(year,hour)
            p,e=native_queries(a,info,year,t-np.timedelta64(3,'h'),t,f'{year}_{hour}_history')
            settings.update(fit(a,p,year,hour))
            support[str(hour)]=dict(**e,interval=[str(t-np.timedelta64(3,'h')),str(t)],
                                    utc_ID_SHA256=ids(a['utc']))
            with (OUT/f'{year}_{hour}_history_local.npz').open('xb') as f:
                np.savez_compressed(f,**a,raw=p)
        path=OUT/f'{year}_parameters.json'
        write_once(path,dict(date=day(year),parameters=settings,Stale06='same date GlobalAdaptive06',
                             observation_SHA256=info['CDF']['SHA256'],source_manifest_SHA256=sha(OUT/'source_manifest.json'),
                             target_models=info['target_models'],history=support,protocol_SHA256=PROTOCOL_SHA,
                             future_density_read=False))
        frozen[str(year)]=sha(path)
    write_once(OUT/'dual_freeze_receipt.json',dict(PASS=True,parameter_SHA256=frozen,
        protocol_SHA256=PROTOCOL_SHA,future_scores_computed=0,UTC=dt.datetime.now(dt.timezone.utc).isoformat(),
        resource=resources(start)))


def parameters(year, receipt):
    path=OUT/f'{year}_parameters.json'
    pin(path,receipt['parameter_SHA256'][str(year)])
    return load(path)['parameters']


def poison():
    start=time.perf_counter()
    receipt=load(OUT/'dual_freeze_receipt.json')
    source=load(OUT/'source_manifest.json')
    checks=[]
    for year in YEARS:
        par=parameters(year,receipt)
        fresh=cdf_data(source['years'][str(year)]['CDF'],year)
        for hour in (6,18):
            a=dict(fresh,density=fresh['density'].copy().astype(float))
            m=masks(year,hour,a['utc'])['analysis']
            with np.load(OUT/f'{year}_{hour}_history_local.npz') as h:
                np.testing.assert_array_equal(h['utc'],a['utc'][m])
                np.testing.assert_array_equal(h['density'],a['density'][m])
                p=np.full(len(m),np.nan);p[m]=h['raw']
            a['density'][a['utc']>=cutoff(year,hour)]*=1e20
            got=fit(a,p,year,hour)
            require(got=={key:par[key] for key in got},'Future poison changed frozen fit')
            checks.append(dict(year=year,cutoff=hour,PASS=True,separate_source_copy=True,
                               exact_coefficient_equality=True,same_date_Stale06=True,
                               parameter_SHA256=receipt['parameter_SHA256'][str(year)]))
    write_once(OUT/'future_poison_test.json',dict(PASS=True,factor=1e20,checks=checks,
        scores_started=False,dual_freeze_SHA256=sha(OUT/'dual_freeze_receipt.json'),resource=resources(start)))


def score(year):
    start=time.perf_counter()
    receipt=load(OUT/'dual_freeze_receipt.json')
    poison_result=load(OUT/'future_poison_test.json')
    require(poison_result['PASS'] and len(poison_result['checks'])==4
            and poison_result['dual_freeze_SHA256']==sha(OUT/'dual_freeze_receipt.json'),'Poison gate incomplete')
    for y in YEARS:
        parameters(y,receipt)
    par=parameters(year,receipt)
    write_once(OUT/f'{year}_scoring_once.json',dict(year=year,attempts=1,parameter_SHA256=receipt['parameter_SHA256'][str(year)]))
    info=load(OUT/'source_manifest.json')['years'][str(year)]
    a=cdf_data(info['CDF'],year)
    end=cutoff(year,0)+np.timedelta64(1,'D')
    p,e=native_queries(a,info,year,cutoff(year,0),end,f'{year}_full')
    write_once(OUT/f'{year}_query_admission.json',dict(PASS=True,**e,quality_N=2880))
    for h in (6,18):
        mask=masks(year,h,a['utc'])['analysis']
        with np.load(OUT/f'{year}_{h}_history_local.npz') as historical:
            np.testing.assert_array_equal(historical['density'],a['density'][mask])
            np.testing.assert_allclose(historical['raw'],p[mask],rtol=1e-13,atol=0)
            p[mask]=historical['raw']
    q=a['quality']
    bands=latitude_band(a['latitude'])
    regions={'all':q,**{name:bands==j for j,name in enumerate(BANDS)}}
    metrics=[];coverage=[];joints=[];index={}
    def evaluate(h,method,pred,support,windows):
        for w,wm in windows.items():
            for region,rm in regions.items():
                data=supported_metric(pred,a['density'],q,q,wm&rm,support)
                row=dict(year=year,cutoff=h,window=w,method=method,region=region,**data)
                metrics.append(row);index[h,w,method,region]=row
                coverage.append(dict(year=year,cutoff=h,window=w,method=method,region=region,
                    N=int((wm&rm).sum()),supported_N=int((wm&rm&support).sum()),utc_ID_SHA256=ids(a['utc'][wm&rm])))
    evaluate(0,'Raw',p,q,{'full_day':q})
    for h in (6,18):
        evaluate(h,'Raw',p,q,masks(year,h,a['utc']))
    table(OUT/f'{year}_raw.csv',metrics)
    preds={}
    for h in (6,18):
        windows=masks(year,h,a['utc'])
        methods={f'GlobalAdaptive{h:02d}':(apply_global(p,par[f'GlobalAdaptive{h:02d}']),q)}
        if h==18:
            methods.update(LatitudeAdaptive18=apply_latitude(p,a['latitude'],par['LatitudeAdaptive18']),
                           Stale06=(apply_global(p,par['GlobalAdaptive06']),q))
        for method,(pred,support) in methods.items():
            evaluate(h,method,pred,support,windows)
            preds[method]=pred
            for w,wm in windows.items():
                if w=='analysis':
                    continue
                raw={reg:index[h,w,'Raw',reg] for reg in regions}
                cor={reg:index[h,w,method,reg] for reg in regions}
                flags=assess_joint(raw['all'],cor['all'],raw,cor,bool(support[wm].all()))
                raw_a,cor_a=raw['all'],cor['all']
                gain=lambda key:100*(1-cor_a[key]/raw_a[key]) if cor_a[key] is not None else None
                delta=lambda a,b:a-b if a is not None and b is not None else None
                low_raw,low_cor=raw['low']['relative_bias'],cor['low']['relative_bias']
                joints.append(dict(year=year,cutoff=h,window=w,method=method,
                   N=raw_a['n'],RMSE_gain_pct=gain('RMSE'),relative_RMS_gain_pct=gain('relative_RMS'),
                   RMSE_delta_kg_m3=delta(cor_a['RMSE'],raw_a['RMSE']),
                   relative_RMS_delta=delta(cor_a['relative_RMS'],raw_a['relative_RMS']),
                   relative_P95_delta=delta(cor_a['relative_P95'],raw_a['relative_P95']),
                   relative_bias_delta=delta(cor_a['relative_bias'],raw_a['relative_bias']),
                   abs_low_relative_bias_delta=delta(abs(low_cor),abs(low_raw)) if low_cor is not None and low_raw is not None else None,
                   **flags))
    table(OUT/f'{year}_metrics.csv',metrics)
    table(OUT/f'{year}_common_ids.csv',coverage)
    table(OUT/f'{year}_joint.csv',joints)
    with (OUT/f'{year}_matched_local.npz').open('xb') as f:
        np.savez_compressed(f,**a,raw=p,**preds)
    outputs={name:sha(OUT/name) for name in (f'{year}_raw.csv',f'{year}_metrics.csv',f'{year}_common_ids.csv',
        f'{year}_joint.csv',f'{year}_matched_local.npz',f'{year}_query_admission.json')}
    write_once(OUT/f'{year}_score_receipt.json',dict(PASS=True,attempts=1,outputs_SHA256=outputs,
        parameter_SHA256=receipt['parameter_SHA256'][str(year)],resource=resources(start)))


if __name__=='__main__':
    phase=sys.argv[1]
    if phase=='score':
        score(int(sys.argv[2]))
    else:
        {'prepare':prepare,'history':history,'poison':poison}[phase]()
