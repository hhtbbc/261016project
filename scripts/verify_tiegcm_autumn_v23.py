"""Independent static namelist/calendar audit; no model, observation density or scores."""
import sys,json,re,datetime,hashlib
from pathlib import Path
import numpy as np
from netCDF4 import Dataset
R=Path(__file__).resolve().parents[1];sys.path[:0]=[str(R/'src'),str(R)]
from runtime.tiegcm_rank_exit import write_once,digest
F=R/'experiments/thermosphere_autumn_mareqx_config_v23'
def parse(text):
    # Independent split, not the generator/launcher namelist parser.
    tokens=re.split(r'(?m)^\s*([A-Z][A-Z0-9_]*)\s*=\s*',text);result={}
    for key,val in zip(tokens[1::2],tokens[2::2]):
        if key in result:raise ValueError('Duplicate key')
        result[key]=' '.join(val.strip().removesuffix('/').strip().split())
    return result

def main():
    policy=json.loads((F/'seed_policy_receipt.json').read_text());assert policy['SEED_POLICY']=='A_MAREQX_APPROVED' and not policy['actual_model_authorized_this_task']
    src=R/policy['source']['path'];assert digest(src)==policy['source']['SHA256']
    with Dataset(src) as n:
        actual=[int(x) for x in n['mtime'][0]];assert actual==[80,0,0] and n['year'][:].tolist()==[2002]
    reference=parse((R/'experiments/tiegcm_2022_mar25_preparation_v1/run/input.inp').read_text());reports={}
    for y in [2021,2022]:
        folder=F/str(y);p=json.loads((folder/'launch_protocol.json').read_text());a=parse((folder/'input.inp').read_text());assert set(a)==set(reference)
        ints=lambda key:list(map(int,a[key].split()))
        assert ints('SOURCE_START')==actual and ints('START')==[252,0,0] and ints('STOP')==[268,0,0]
        assert ints('START_YEAR')==[y] and ints('START_DAY')==[252] and ints('STEP')==[60]
        assert ints('SECSTART')==[252,1,0] and ints('SECSTOP')==[268,0,0]
        assert ints('HIST')==[1,0,0] and ints('SECHIST')==[0,1,0] and ints('MXHIST_PRIM')==[1] and ints('MXHIST_SECH')==[24]
        assert re.findall(r"'([^']+)'",a['OUTPUT'])==[f'primary_{i:03d}.nc' for i in range(1,18)]
        assert re.findall(r"'([^']+)'",a['SECOUT'])==[f'secondary_{i:03d}.nc' for i in range(1,17)]
        start=datetime.datetime(y,1,1)+datetime.timedelta(days=251);stop=datetime.datetime(y,1,1)+datetime.timedelta(days=267)
        assert int((stop-start).total_seconds()/60)==23040 and p['start_UTC']==start.isoformat()+'Z' and p['stop_UTC']==stop.isoformat()+'Z'
        for field,asset in [('SOURCE',p['source']),('GPI_NCFILE',p['GPI'])]:
            resolved=a[field].strip("'").replace('$PROJECTROOT',str(R));assert Path(resolved).resolve()==(R/asset['path']).resolve() and digest(Path(resolved))==asset['SHA256']
        assert str(y) in Path(p['GPI']['path']).name
        changed={k for k in reference if reference[k]!=a[k].replace('$PROJECTROOT',str(R))}
        allowed={'LABEL','START_YEAR','START_DAY','START','STOP','SECSTART','SECSTOP','OUTPUT','SECOUT','GPI_NCFILE'};assert changed<=allowed
        for key in set(reference)-allowed:assert a[key].replace('$PROJECTROOT',str(R))==reference[key],key
        assert not (R/p['cwd']).exists() and str(y) in Path(p['cwd']).parts
        assert p['executable']['SHA256']=='f60832a66caf7f95d5de8e7aafa44f0b6981ae38d130fe237b9df28fdf896776'
        reports[str(y)]=dict(PASS=True,input_SHA256=digest(folder/'input.inp'),protocol_SHA256=digest(folder/'launch_protocol.json'),source_SHA256=digest(src),GPI_SHA256=p['GPI']['SHA256'],expected_changed_physical_or_metadata_fields=sorted(changed),unexpected_fields=[],steps=23040,primary_records=17,secondary_records=384,NetCDF_files=33,actual_model_run='NOT_RUN')
    old=json.loads((F/'protected_assets.json').read_text());assert all(digest(R/n)==h for n,h in old.items())
    audit=json.loads((R/'experiments/tiegcm_2022_b14_exploratory_pair_v2/B14/data_audit.json').read_text());assert audit['primary_records']==17 and audit['secondary_records']==384 and audit['model_steps']==23040
    original_output_reference=dict(path='experiments/tiegcm_2022_b14_exploratory_pair_v2/B14/data_audit.json',SHA256=digest(R/'experiments/tiegcm_2022_b14_exploratory_pair_v2/B14/data_audit.json'),same_native_16day_volume_schedule=True,not_scientific_equivalence=True,A14_engineering_status=audit['A14_engineering'])
    write_once(F/'independent_verification.json',dict(PASS=True,years=reports,old_assets_unchanged=len(old),historical_16day_schedule_evidence=original_output_reference,real_output_acceptance='NOT_RUN',density_errors_read=0,model_launches=0))
    print(json.dumps(reports,indent=2))
if __name__=='__main__':main()
