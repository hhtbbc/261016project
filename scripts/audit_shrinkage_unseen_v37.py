"""Offline V37 asset audit. Never opens CDF variable data or a target model field."""
import csv
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import resource
import subprocess
import sys
from time import monotonic
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from evaluation.independent_date_planning import support, days, valid_solar, centered
from evaluation.shrinkage_unseen_gate_v37 import SUMMER, WINTER, CANDIDATES
from observations.autumn_validation import inspect_initial, REQUIRED
from netCDF4 import Dataset

E = ROOT/'experiments'
OUT = E/'thermosphere_shrinkage_unseen_prereg_v37'
V20 = E/'thermosphere_independent_date_validation_plan_v20'
V36 = E/'thermosphere_causal_shrinkage_development_v36'
BASE = '3bfe65d14dafa23ab1d12b0139b63cb1716d9183'


def rel(p):
    return str(p.relative_to(ROOT))


def load(p):
    return json.loads(p.read_text())


def rows(p):
    with p.open(newline='') as f:
        return list(csv.DictReader(f))


def record(name, value):
    with (OUT/name).open('x') as f:
        json.dump(value,f,indent=2,allow_nan=False)
        f.write('\n')


def sha(p):
    assert p.resolve(strict=True)==p and p.is_relative_to(ROOT)
    d=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):
            d.update(b)
    return d.hexdigest()


def gitpin(p):
    expected=subprocess.check_output(['git','show',f'{BASE}:{rel(p)}'],cwd=ROOT)
    assert expected==p.read_bytes(), rel(p)
    return hashlib.sha256(expected).hexdigest()


def driving_sources():
    solar,kp,provenance={}, {}, []
    conflicts=[]
    def add(target,key,new,path):
        if key not in target:
            target[key]=new
        elif target[key]!=new:
            conflicts.append(dict(UTC=str(key),source=path))
            target[key]=None
    requests=E/'f107_2021_recovery_v1/gfz_requests.json'
    gitpin(requests)
    old={r['name']:r for r in load(requests)}
    archive=ROOT/'data/raw/f107_2021_recovery_v1/gfz_year.txt'
    assert sha(archive)==old['gfz_year']['SHA256']
    for line in archive.read_text().splitlines():
        p=line.split()
        if not p or p[0]!='2021':
            continue
        d=date(*map(int,p[:3]))
        add(solar,d,float(p[25]),rel(archive))
        for h in range(8):
            v=float(p[7+h])
            add(kp,datetime.combine(d,time(h*3)),v if p[27]=='2' and 0<=v<=9 else None,rel(archive))
    provenance.append(dict(path=rel(archive),index='2021 Fobs + definitive Kp',anchor=rel(requests),
                           SHA256=old['gfz_year']['SHA256'],source_URL=old['gfz_year']['URL']))
    cache=E/'tiegcm_2022_mar25_preparation_v1/driver_source_audit.json'
    autumn=E/'thermosphere_autumn_data_acquisition_v21/GFZ2022_raw_contract_audit.json'
    previous=V20/'driver_source_inventory.json'
    for p in (cache,autumn,previous):
        gitpin(p)
    entries=[dict(x,anchor=rel(cache)) for x in load(cache)['sources']]
    for key,val in load(autumn).items():
        entries.append(dict(val['source'],key=key,anchor=rel(autumn),source_URL='https://kp.gfz.de/en/data'))
    entries.extend(dict(x,anchor=rel(previous)) for x in load(previous)['sources']
                   if x['path'].endswith('gfz_Fobs_spinup_support.txt'))
    entries.append(dict(path='data/raw/f107_2021_recovery_v1/gfz_fobs_check.txt',
                   SHA256=old['gfz_fobs_check']['SHA256'],key='Fobs',anchor=rel(requests),
                   source_URL=old['gfz_fobs_check']['URL']))
    for entry in entries:
        p=ROOT/entry['path']
        assert sha(p)==entry['SHA256']
        d=load(p)
        key=entry['key']
        stamps=d['datetime']
        assert len(stamps)==len(d[key])==len(set(stamps))
        for i,(t,v) in enumerate(zip(stamps,d[key],strict=True)):
            utc=datetime.fromisoformat(t.replace('Z','+00:00'))
            assert utc.utcoffset()==timedelta(0) and utc.minute==utc.second==0
            if key=='Fobs':
                assert utc.hour==0
                add(solar,utc.date(),float(v),entry['path'])
            else:
                assert utc.hour%3==0 and len(d['status'])==len(stamps)
                add(kp,utc.replace(tzinfo=None),float(v) if d['status'][i]=='def'
                    and 0<=float(v)<=9 else None,entry['path'])
        provenance.append(dict(path=entry['path'],SHA256=entry['SHA256'],index=key,
                              anchor=entry['anchor'],first_UTC=stamps[0],last_UTC=stamps[-1],
                              source_URL=entry['source_URL']))
    return solar,kp,provenance,conflicts


def api(index, first, last):
    args=dict(start=str(first)+'T00:00:00Z',end=str(last)+'T23:59:59Z',index=index)
    if index=='Kp':
        args['status']='def'
    return 'https://kp.gfz.de/app/json/?'+urlencode(args)


def audit():
    started=monotonic()
    publication=V36/'publication_SHA256.json'
    protocol=V20/'preregistered_protocol.json'
    design=E/'thermosphere_causal_shrinkage_design_v35/v36_development_release.json'
    roles=E/'thermosphere_coefficient_stability_zg_audit_v32/data_roles.json'
    pins={rel(p):gitpin(p) for p in (publication,protocol,design,roles)}
    for name,digest in load(publication).items() | load(design)['V35_SHA256'].items():
        assert sha(ROOT/name)==digest
        pins[name]=digest
    base=load(protocol)
    assert load(design)['V20_core']==base['fixed_scientific_core']
    assert load(design)['methods']==dict(CANDIDATES)
    for key in ('metric_source','latitude_source','Map_A_source','operator_source','hourly_reader_source'):
        source=base['fixed_scientific_core'][key]
        assert sha(ROOT/source['path'])==source['SHA256']
        pins[source['path']]=source['SHA256']
    v36=load(V36/'decision.json')
    assert v36['fixed_lambda']==.5 and v36['candidate_decision']=='CANDIDATE_FOR_UNSEEN_VALIDATION'
    assert load(V36/'independent_verification.json')['verified']
    assert {x['date'] for x in load(roles)['dates'] if x['role']=='UNSEEN_TEST_METADATA_ONLY'}==set(SUMMER+WINTER)
    solar,kp,provenance,conflicts=driving_sources()
    index=V20/'observation_data_requirements.csv'
    gitpin(index)
    old_obs={x['date']:x for x in rows(index)}
    seed_index=V20/'seasonal_initial_asset_requirements.csv'
    gitpin(seed_index)
    original_archive=ROOT/'data/raw/meeting_sources/tiegcm_data_index.txt'
    search_roots=[ROOT/p for p in ('data','experiments','third_party')]
    files=[p for root in search_roots for p in root.rglob('*') if p.is_file()
           and (p.name.startswith('SW_OPER_DNSAPOD') or re.search(r'_(mareqx|junsol|decsol|sepeqx)_.*\.nc$',p.name))]
    asset=[]
    for candidate in SUMMER+WINTER:
        q=support(candidate)
        ss,se=map(date.fromisoformat,(q['solar_start'],q['solar_stop']))
        lo,hi=map(date.fromisoformat,(q['raw_start'],q['raw_stop']))
        sun=days(ss,se)
        gpi=days(lo,hi)
        f_gap=[d for d in sun if not valid_solar(solar.get(d))]
        absent=[d for d in f_gap if d not in solar]
        invalid=[d for d in f_gap if d in solar]
        k_gap=[datetime.combine(d,time(h)) for d in gpi for h in range(0,24,3)
               if kp.get(datetime.combine(d,time(h))) is None]
        entry=old_obs[candidate]
        stem=entry['product'][:-4]
        actual=[dict(path=rel(p),bytes=p.stat().st_size,SHA256=sha(p)) for p in files
                if p.stem==stem and p.suffix.lower() in ('.cdf','.zip','.hdr')]
        asset.append(dict(date=candidate,support=q,valid_Fobs=len(sun)-len(f_gap),
                Fobs_not_acquired=[str(d) for d in absent],
                Fobs_invalid_or_conflict={str(d):solar[d] for d in invalid},
                valid_def_Kp=8*len(gpi)-len(k_gap),missing_or_invalid_Kp_UTC=[d.isoformat()+'Z' for d in k_gap],
                daily_center81_ready=sum(centered(solar,d)[0] is not None for d in gpi),
                target_center81_gap=[str(d) for d in centered(solar,date.fromisoformat(candidate))[1]],
                official_GFZ_query=dict(Fobs_full=api('Fobs',ss,se),Kp_def_full=api('Kp',lo,hi)),
                observation=dict(product=entry['product'],status='NOT_ACQUIRED' if not actual else 'NOT_VERIFIED',
                    local=actual,expected_products=[stem+f'.{suffix}' for suffix in ('ZIP','CDF','HDR')],
                    historical_index_bytes=int(entry['cached_bytes']),historical_index_URL=entry['official_download_URL'],
                    current_remote_status='NOT_VERIFIED_NO_NETWORK',quality='NOT_VERIFIED'),
                matched_target_model='NOT_VERIFIED_NO_QUALIFIED_RELEASE_FOUND',
                seed_policy='NOT_APPROVED',state='ASSET_PARTIAL'))
    v27=E/'thermosphere_autumn_2022_execution_preparation_v27/execution_release.json'
    pins[rel(v27)]=gitpin(v27)
    design27=load(v27)
    elf=ROOT/design27['physical_paths']['executable']
    expected=design27['physical_SHA256']['executable']
    assert sha(elf)==expected and elf.stat().st_mode & 0o111
    with elf.open('rb') as f:
        assert f.read(4)==b'\x7fELF'
    ref=ROOT/design27['physical_paths']['source']
    assert sha(ref)==design27['physical_SHA256']['source']
    seeds=[]
    for p in sorted(set(files)):
        if not re.search(r'_(mareqx|junsol|decsol|sepeqx)_.*\.nc$',p.name):
            continue
        try:
            info=inspect_initial(p,ref)
        except (ValueError, OSError) as exc:
            with Dataset(p) as n:
                seeds.append(dict(path=rel(p),SHA256=sha(p),bytes=p.stat().st_size,
                    model_version=str(getattr(n,'model_version','')),
                    mtime=n['mtime'][:].tolist(), year=n['year'][:].tolist(),
                    grid={k:len(n.dimensions[k]) for k in ('lat','lon','lev','ilev')},
                    state_names_present=sum(k in n.variables for k in REQUIRED),
                    schema_compatible=False,strict_error=str(exc),approved_for_summer_winter=False))
            continue
        seeds.append(dict(path=rel(p),SHA256=sha(p),bytes=p.stat().st_size,
             grid=info['grid'],model_version=info['attributes']['model_version'],
             year=info['years'],SOURCE_START=info['SOURCE_START'],
             complete_native_states=info['required_complete_states'],actual_records=info['actual_calendar_records'],
             provenance=info['source_file_basename'],season='March equinox' if '_mareqx_' in p.name else p.name,
             schema_compatible=True,approved_for_summer_winter=False))
    catalog=[]
    for record_ in rows(seed_index):
        if record_['season'] not in ('summer','winter'):
            continue
        name=record_['product']
        catalog.append(dict(season=record_['season'],name=name,URL=record_['URL'],
                            cached_index_attested=f'href="{name}"' in original_archive.read_text(),
                            index_SHA256=sha(original_archive),indexed_size='~16 MiB estimated',
                            local_paths=[rel(p) for p in files if p.name==name],
                            actual_identity='NOT_ACQUIRED' if not any(p.name==name for p in files) else 'NOT_VERIFIED',
                            approved=False))
    record('asset_audit.json',dict(UTC=datetime.now(timezone.utc).isoformat(),data_state='UNSEEN_DATA_PARTIAL',
         dates=asset,driver_sources=provenance,conflicts=conflicts,seeds=seeds,seasonal_seed_catalog=catalog,
         executable=dict(path=rel(elf),SHA256=expected,bytes=elf.stat().st_size,identity='ASSET_READY_ELF_SHA_ONLY'),
         historical_assets=pins,targets_decoded=0,network_bytes=0,model_runs=0,GPI_files_generated=0,
         read_scope=[rel(x) for x in search_roots],wall_seconds=monotonic()-started,
         peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))


if __name__=='__main__':
    audit()
