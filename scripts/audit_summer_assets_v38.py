"""V38 strict read-only scientific acceptance with a sealed Swarm density field."""
from datetime import date, datetime, time, timedelta
import json
from math import isfinite
from pathlib import Path
import resource
from time import monotonic, process_time
from xml.etree import ElementTree
import zipfile

from fetch_summer_assets_v38 import ROOT, OUT, RAW, DAYS, SEED, save, history_pins
import numpy as np
from cdflib import CDF, cdfepoch
from observations.bounded_swarm_acquisition import Budget, archive_plan, extract_members, posix_cksum, sha
from observations.autumn_validation import check_product_stem, check_times, inspect_initial
from evaluation.independent_date_planning import days, support, centered
from audit_shrinkage_unseen_v37 import driving_sources

V27 = ROOT/'experiments/thermosphere_autumn_2022_execution_preparation_v27/execution_release.json'
DATA_FIELDS = ('time','latitude','longitude','altitude','validity_flag')
UNIT = {'Fobs':'sfu','Kp':'1'}


def require(ok, detail):
    if not ok:
        raise ValueError(detail)


def read_json(p):
    return json.loads(p.read_bytes())


def requested_grid(first, last, step):
    start=datetime.fromisoformat(first)
    stop=datetime.fromisoformat(last)+timedelta(days=1)
    return [start+j*step for j in range((stop-start)//step)]


def parse_gfz(payload, key, grid, *, revision_probe=False):
    require(key in UNIT and set(payload).intersection(UNIT.keys()|{'Fadj'})=={key},
            'Wrong GFZ variable identity')
    require(payload.get('meta',{}).get('source')=='GFZ Potsdam','GFZ provenance mismatch')
    units=payload.get('units', payload['meta'].get('units'))
    if isinstance(units,dict):
        units=units.get(key)
    require(units is None or units==UNIT[key], 'Wrong index unit')
    stamps=payload.get('datetime',[])
    values=payload.get(key,[])
    require(len(stamps)==len(values)==len(grid) and len(set(stamps))==len(stamps),'Missing or duplicate GFZ records')
    require(stamps==[x.isoformat()+'Z' for x in grid],'UTC grid mismatch')
    require(all(type(v) in (int,float) and isfinite(v) for v in values),'Nonfinite GFZ index')
    if key=='Kp':
        require(payload.get('status')==['def']*len(grid) and all(0<=v<=9 for v in values),
                'Invalid or nondefinitive Kp')
    elif revision_probe:
        require(len(grid)==1 and (values[0]==-1 or values[0]>0),'Invalid Fobs recheck')
    else:
        require(all(v>0 for v in values),'Nonpositive Fobs')
    return dict(zip(grid,values,strict=True))


def merge(target, new):
    conflicts=[]
    for key,value in new.items():
        if key in target and target[key]!=value:
            conflicts.append(dict(timestamp=str(key),available=target[key],additional=value))
        else:
            target[key]=value
    return conflicts


def sealed_read(cdf, name, accesses):
    require(name in DATA_FIELDS,'Sealed observation variable')
    accesses.append(name)
    return cdf.varget(name)


def verify_hdr(path, stem, day, cdf_file):
    node=ElementTree.parse(path).getroot()
    fixed=node.find('Fixed_Header')
    constants={'File_Name':stem,'Mission':'Swarm','File_Type':'DNSAPOD_2_', 'File_Version':'0301',
        'Validity_Period/Validity_Start':'UTC='+day+'T00:00:00',
        'Validity_Period/Validity_Stop':'UTC='+day+'T23:59:30'}
    require(fixed is not None and all(fixed.findtext(k)==v for k,v in constants.items()),'HDR identity mismatch')
    crc,n=posix_cksum(cdf_file)
    require(crc==int(node.findtext('Variable_Header/MPH/CRC'))
            and n==int(node.findtext('Variable_Header/MPH/Tot_Size')),'HDR POSIX CRC/length mismatch')
    return dict(version='0301',CDF_POSIX_CRC=crc,CDF_bytes=n,
                creation_UTC=fixed.findtext('Source/Creation_Date'))


def verify_cdf(path, stem, day, accesses):
    c=CDF(path)
    attrs=c.globalattsget()
    require(attrs.get('TITLE')==[stem] and attrs.get('TIME SYSTEM')==['UTC']
            and c.varinq('time').Data_Type==31,'CDF identity or UTC type mismatch')
    units={'latitude':'deg','longitude':'deg','altitude':'m','density':'kg/m3'}
    require(all(c.varattsget(k).get('UNITS')==v for k,v in units.items()),'Unexpected CDF units')
    require(all(c.varinq(k).Last_Rec==2879 for k in (*DATA_FIELDS,'density')), 'CDF variable lengths mismatch')
    a={k:sealed_read(c,k,accesses) for k in DATA_FIELDS}
    utc=cdfepoch.to_datetime(a['time'])
    check_times(utc,day)
    lat,lon,alt,flags=(a[k] for k in DATA_FIELDS[1:])
    require(all(x.shape==(2880,) for x in (lat,lon,alt,flags)),'Invalid CDF shapes')
    coords=np.isfinite(lat)&np.isfinite(lon)&np.isfinite(alt)&(abs(lat)<=90)&(abs(lon)<=180)&(alt>0)
    require(coords.all() and np.isin(flags,[0,1]).all(),'Unknown quality codes or invalid coordinates')
    return dict(records=len(utc),first_UTC=str(utc[0]),last_UTC=str(utc[-1]),cadence_seconds=30,
                unit_contract=units,valid_coordinate_records=int(coords.sum()),flag0=int((flags==0).sum()),
                flag1=int((flags==1).sum()),density_quality='NOT_TESTED_SEALED')


def entries(path):
    return dict(path=str(path.relative_to(ROOT)),SHA256=sha(path),bytes=path.stat().st_size)


def seed_inspection(path):
    reference=read_json(V27)
    ref=ROOT/reference['physical_paths']['source']
    require(sha(ref)==reference['physical_SHA256']['source'],'Reference seed changed')
    info=inspect_initial(path,ref)
    require(info['required_complete_states']==34 and info['grid']=={'lat':36,'lon':72,'lev':29,'ilev':29},
            'Junsol grid/native count mismatch')
    return info


def main():
    started,cpu=monotonic(),process_time()
    frozen=history_pins()
    downloads=read_json(OUT/'download_manifest.json')['assets']
    retry=OUT/'ESA_retry_manifest.json'
    if retry.is_file():
        more=read_json(retry)['assets']
        require(not set(downloads)&set(more),'Duplicate download evidence')
        downloads.update(more)
    for asset in downloads.values():
        path=ROOT/asset['path']
        require(path.resolve()==path and path.parent==RAW and sha(path)==asset['SHA256'],'Changed downloaded bytes')
    solar,kp,prior,conflicts=driving_sources()
    require(not conflicts,'Preexisting GFZ conflict')
    revision, parsed, failures={}, {}, []
    for key,asset in downloads.items():
        if not key.startswith(('Fobs','Kp')):
            continue
        field=key.split('_')[0]
        first,last=key.split('_')[1:]
        probe=first.startswith('2021')
        try:
            values=parse_gfz(read_json(ROOT/asset['path']),field,
                    requested_grid(first,last,timedelta(hours=24 if field=='Fobs' else 3)),revision_probe=probe)
            if probe:
                old=solar[date.fromisoformat(first)]
                value=next(iter(values.values()))
                revision[first]=dict(value=value,archive_value=old,source='GFZ Potsdam',
                     unit='sfu per GFZ index definition',explicit_units_in_response=False,
                     product_revision_in_payload=None,asset=asset,
                     status='OFFICIAL_MISSING_STILL_PRESENT' if value==-1 else 'OFFICIAL_OBSERVED_REVISION_CONFIRMED')
                if value>0:
                    # The only permitted overlay is an official positive observed value replacing old -1.
                    require(old==-1,'Official observed revision conflicts with an existing valid value')
                    solar[date.fromisoformat(first)]=value
            else:
                index=solar if field=='Fobs' else kp
                candidate={t.date():v for t,v in values.items()} if field=='Fobs' else values
                clashes=merge(index,candidate)
                conflicts.extend(clashes)
                parsed[key]=len(values) if not clashes else 0
        except (ValueError, KeyError, TypeError) as exc:
            failures.append(dict(key=key,stage='GFZ contract',reason=str(exc)))
    coverage={}
    for day in DAYS:
        r=support(day)
        f=days(date.fromisoformat(r['solar_start']),date.fromisoformat(r['solar_stop']))
        g=days(date.fromisoformat(r['raw_start']),date.fromisoformat(r['raw_stop']))
        f_gap=[str(d) for d in f if solar.get(d,0)<=0]
        stamps=[datetime.combine(d,time(h)) for d in g for h in range(0,24,3)]
        k_gap=[t.isoformat()+'Z' for t in stamps if kp.get(t) is None]
        ready={d.isoformat():centered(solar,d)[0] for d in g}
        coverage[day]=dict(status='GFZ_COMPLETE' if not f_gap and not k_gap and not conflicts else 'GFZ_BLOCKED',
             Fobs_valid=101-len(f_gap),Fobs_missing=f_gap,definitive_Kp_valid=168-len(k_gap),Kp_missing=k_gap,
             valid_centers=sum(v is not None for v in ready.values()),daily_center81_check_sfu=ready,support=r)
    for t in ('2021-05-09','2021-06-16'):
        revision.setdefault(t,dict(status='OFFICIAL_RESPONSE_UNVERIFIED',archive_value=-1))
    budget=Budget()
    obs = {}
    decompress_charge=0
    for day in DAYS:
        key=f'Swarm_{day}'
        info=dict(status='NOT_ACQUIRED',accessed_data_variables=[],target_density_decodes=0)
        obs[day]=info
        if key not in downloads:
            continue
        uri=ROOT/downloads[key]['path']
        try:
            stem=check_product_stem(uri.stem,day)
            with zipfile.ZipFile(uri) as z:
                size=sum(m.file_size for m in z.infolist())
            require(decompress_charge+3*size<=2*2**20,'Aggregate extraction/CRC budget exceeded')
            decompress_charge+=3*size
            # extract_members validates central directory and CRC, then writes only exact members.
            members=extract_members(uri,stem,budget,RAW)
            cp=RAW/(stem+'.cdf'); hp=RAW/(stem+'.HDR')
            hdr=verify_hdr(hp,stem,day,cp)
            meta=verify_cdf(cp,stem,day,info['accessed_data_variables'])
            info.update(status='METADATA_VERIFIED_DENSITY_SEALED',identity='PRODUCT_IDENTITY_VERIFIED',
                        members=members,HDR=hdr,CDF=meta,ZIP_SHA256=sha(uri))
        except (ValueError, KeyError, OSError, zipfile.BadZipFile) as exc:
            info.update(status='NOT_VERIFIED',reason=str(exc))
    seed=dict(status='JUNSOL_SEED_NOT_ACQUIRED',approval='SEASON_SEED_POLICY_PENDING')
    if 'junsol' in downloads:
        path=RAW/SEED
        seed.update(original=entries(path))
        try:
            seed.update(status='JUNSOL_SEED_STATIC_COMPATIBLE',native=seed_inspection(path))
        except (ValueError,KeyError,OSError) as exc:
            seed.update(status='JUNSOL_SEED_INCOMPATIBLE',reason=str(exc))
    save('asset_audit.json',dict(V37_SHA256=frozen,new_GFZ_counts=parsed,GFZ_rechecks=revision,GFZ=coverage,
         prior_GFZ=prior,conflicts=conflicts,validation_failures=failures,Swarm=obs,junsol=seed,
         unique_extraction_bytes=budget.extracted_bytes,conservative_decompression_bytes=decompress_charge,
         new_model_runs=0,new_GPI=0,new_formal_input=0,unseen_target_density_reads=0,new_scientific_scores=0,
         new_fits=0,GPU=0,wall_s=monotonic()-started,CPU_s=process_time()-cpu,
         peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))


if __name__=='__main__':
    main()
