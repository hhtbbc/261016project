"""V47 B-only recovery preparation and explicitly authorized once-only execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import uuid
from datetime import timedelta

from netCDF4 import Dataset, num2date

import run_summer_seed_sensitivity_v46 as v46
import preflight_summer_config_v45 as v45

ROOT = v46.ROOT
OLD = v46.OUT
OUT = ROOT / 'experiments/thermosphere_summer_seed_recovery_v47'
RUN = OUT / 'run_B_junsol_recovery'
SEED = OUT / 'seed.nc'
SOURCE = '../seed.nc'
INPUT = OUT / 'recovery_input.namelist'
BASE = 'b2f3bf47fcf5c2d9feaba2e16d3ae11df765b00c'
START = v46.START
require = v46.require
sha = v46.sha
load = v46.load
write = v46.write_once


def absent(path):
    return not os.path.lexists(path)


def history():
    path = OLD / 'publication_SHA256.json'
    original = subprocess.check_output(['git','show',f'{BASE}:{path.relative_to(ROOT)}'],cwd=ROOT)
    require(original == path.read_bytes(), 'V46 manifest drift')
    checks = json.loads(original)
    for name, expected in checks.items():
        v45.verify_hash(name, expected)
    for name, expected in load(OLD/'analysis_contract.json')['files_sha256'].items():
        v45.verify_hash(name, expected)
    return checks


def archived_protocol():
    return load(OLD/'frozen_pair.json')['protocols']


def receipt_path(run, suffix):
    return run.with_name(run.name + '_' + suffix + '.json')


def original_failure():
    b = OLD/v46.B
    p = archived_protocol()[v46.B]
    path = str(ROOT/p['source']['path'])
    status = load(b/'status.json')
    claim = load(receipt_path(b,'claim'))
    require(len(path.encode()) == 147 and not Path(path[:120]).exists() and
            status['returncode'] == 2 and status['cleanup_verified'] and not list(b.glob('*.nc')),
            'Unexpected old B failure')
    for rank in range(4):
        log = (b/f'rank_{rank:03d}.log').read_text()
        exit = load(b/f'rank_{rank:03d}_exit.json')
        require(f'Found file {path}' in log and f'disk file is {path[:120]})' in log and
                'nchist.F' in log and 'End of record' in log and not re.search(r'Step\s+\d+ of',log)
                and exit['run_id'] == claim['run_id'] and exit['returncode'] == 2,
                'Old B failure evidence mismatch')
    return {'run_id':claim['run_id'],'input_sha256':sha(b/'input.inp'),'expanded_bytes':147,
            'diskfile_bytes':120,'rank_exit':[2]*4,'steps':0,'volumes':0}


def verify_engineering(run, p, expected_inventory=None):
    claim = load(receipt_path(run,'claim'))
    audit = load(receipt_path(run,'acceptance'))
    require(audit['overall'] == 'PASS' and claim['run_id'] == audit['run_id']
            and sha(run/'input.inp') == p['input']['SHA256'], 'Wrong run/input identity')
    status = load(run/'status.json')
    require(status['returncode'] == 0 and status['qualification'] == 'PASS'
            and status['cleanup_verified'] and not status['gaps']
            and status['wait_source'] == 'direct subprocess.Popen.wait', 'Bad direct MPI wait')
    require(load(run/'launch_once.json')['argv'] == v46.model_argv(p,claim['run_id']),
            'Wrong once-only command')
    ranks = v46.checks.validate_exits(run,claim['run_id'],p)
    for i in range(4):
        v46.checks.parse_progress((run/f'rank_{i:03d}.log').read_text(),steps=23040,start=START)
    for key in ('source','GPI','executable','mpirun'):
        v45.verify_hash(p[key]['path'],p[key]['SHA256'])
    inventory = {r['file']:r['SHA256'] for r in audit['files']}
    if expected_inventory is not None:
        require(inventory == expected_inventory, 'A inventory diverged from V46 published bytes')
    require(len(inventory) == 33 and set(inventory) == {x.name for x in run.glob('*.nc')}, 'Missing volumes')
    for kind, volumes, records in [('primary',17,1),('secondary',16,24)]:
        for i in range(volumes):
            name = f'{kind}_{i+1:03d}.nc'
            expected = [(START+timedelta(hours=i*24+(j+1 if records==24 else 0))).isoformat()
                        for j in range(records)]
            path = run/name
            require(path.resolve() == path and sha(path) == inventory[name], 'Output SHA mismatch')
            with Dataset(path) as n:
                time = n['time']
                require(n.history_type == kind and [t.isoformat() for t in num2date(time[:],time.units)] == expected,
                        'Timeline mismatch')
    return {'run_id':claim['run_id'],'ranks':ranks,'inventory':inventory,'primary':17,'secondary':384}


def a_snapshot():
    a = OLD/v46.A
    r = next(x for x in load(OLD/'result.json')['runs'] if x['group']==v46.A)
    result = verify_engineering(a,archived_protocol()[v46.A],{f['file']:f['SHA256'] for f in r['inventory']})
    require(result['run_id']==r['run_id'],'A ID changed')
    return result


def recovery_input(old):
    old_source, = re.findall(r"(?m)^ SOURCE = '(.*)'$",old)
    updated = old.replace(f" SOURCE = '{old_source}'",f" SOURCE = '{SOURCE}'",1)
    verify_diff(old,updated)
    return updated, old_source


def verify_diff(old,new):
    old_lines, new_lines = old.splitlines(),new.splitlines()
    changes = [(a,b) for a,b in zip(old_lines,new_lines,strict=True) if a!=b]
    require(len(changes)==1 and changes[0][0].startswith(" SOURCE = '$PROJECTROOT/")
            and changes[0][1]==f" SOURCE = '{SOURCE}'" and ' SOURCE_START = 172 0 0' in new_lines,
            'Non-path configuration drift')
    return changes[0]


def seed_path(cwd,value):
    require(cwd in (RUN,OUT/'probe_cwd') and cwd.resolve()==cwd and value==SOURCE,
            'Unapproved working directory or SOURCE')
    p = cwd / value
    require(p.resolve(strict=True)==SEED and SEED.resolve()==SEED and not SEED.is_symlink(),
            'Unbound seed path')
    st = SEED.stat()
    require(stat.S_ISREG(st.st_mode) and not st.st_mode & 0o222 and st.st_nlink == 1
            and sha(SEED)==v45.JUNSOL, 'Seed copy bytes, ownership or permission changed')
    return SEED


def pins(b):
    freeze = load(v45.OUT/'preflight.json')
    for k, expected in freeze['critical_assets'].items():
        v45.verify_hash(k,expected)
    for k, expected in v45.v43_sources().items():
        v45.verify_hash(k,expected)
    for key in ('executable','mpirun','GPI','source'):
        v45.verify_hash(b[key]['path'],b[key]['SHA256'])
    status = v46.resource_review(b)
    require(status['resource_ready'],'Resource or concurrent model gate')
    return status


def protocol():
    return archived_protocol()[v46.B] | {
        'input':v46.entry(INPUT.relative_to(ROOT),sha(INPUT)),
        'source':v46.entry(SEED.relative_to(ROOT),v45.JUNSOL),
        'input_text':INPUT.read_text()}


def authorization(receipt, binding):
    require(receipt is not None,'New V47 authorization required')
    require(receipt == {'approved':True,'scope':'V47 B only','attempts':1,
                       'preparation_sha256':binding},'Authorization not bound to V47 recovery')


def prepare():
    require(OUT.resolve()==OUT and OUT.is_dir() and absent(RUN),'Unsafe or occupied recovery directory')
    checks = history()
    old = original_failure()
    a = a_snapshot()
    proto = archived_protocol()[v46.B]
    resources = pins(proto)
    source = ROOT/proto['source']['path']
    require(source.resolve()==source and not source.stat().st_mode&0o222,'Uncontrolled source')
    before = source.stat()
    require(absent(SEED) and absent(INPUT),'Original recovery artifacts already exist')
    import tempfile
    with tempfile.TemporaryDirectory(dir=OUT,prefix='.seed-') as area:
        temp = Path(area)/'seed.nc'
        shutil.copyfile(source,temp)
        temp.chmod(0o444)
        after = source.stat()
        require((before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==
                (after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
                and sha(source)==sha(temp)==v45.JUNSOL and temp.stat().st_size==before.st_size,
                'Copy identity mismatch')
        os.link(temp,SEED)
    new,_ = recovery_input(proto['input_text'])
    with INPUT.open('x') as f:
        f.write(new)
    write(OUT/'preparation.json',{'A':a,'old_B':old,
        'old_V46_publication_sha256':sha(OLD/'publication_SHA256.json'),'V46_manifest_entries':len(checks),
        'old_claim_sha256':sha(OLD/'pair_claim.json'),'new_input_sha256':sha(INPUT),
        'new_seed_sha256':sha(SEED),'seed_size':SEED.stat().st_size,'seed_origin':proto['source']['path'],
        'source_diff':verify_diff(proto['input_text'],new),'resources':resources,
        'run_path':str(RUN.relative_to(ROOT)),'launch_limit':1,'retries':False,
        'authorized':False,'launches':0,'new_run_id':None})


def cpu_only(environ):
    require(environ.get('CUDA_VISIBLE_DEVICES', '') == '' and
            environ.get('OMP_NUM_THREADS','1') == '1', 'V47 requires GPU hidden and OMP=1')


def new_identity(value, previous):
    require(re.fullmatch(r'[0-9a-f]{32}',value) and value not in previous,'Invalid or recycled recovery identity')


def launch():
    cpu_only(os.environ)
    preparation = OUT/'preparation.json'
    auth = OUT/'authorization.json'
    require(auth.is_file() and auth.resolve()==auth,'New V47 authorization required')
    authorization(load(auth),sha(preparation))
    require((OUT/'verification.json').resolve()==OUT/'verification.json','Unexpected review path')
    manifest = OUT/'publication_SHA256.json'
    committed = subprocess.check_output(['git','show',f'HEAD:{manifest.relative_to(ROOT)}'],cwd=ROOT)
    require(manifest.read_bytes()==committed,'Recovery publication differs from Git')
    for path, expected in json.loads(committed).items():
        v45.verify_hash(path,expected)
    for path, expected in load(OUT/'archived_runtime_evidence.json').items():
        v45.verify_hash(path,expected)
    review = load(OUT/'verification.json')
    require(review['state']=='V47_B_RECOVERY_READY_FOR_AUTHORIZATION' and
            review['preparation_sha256']==sha(preparation),'Preflight evidence missing')
    with v46.execution_lock(v46.env.PACKAGE/'autumn_execution_lock_local'):
        claim = receipt_path(RUN,'claim')
        require(absent(RUN) and absent(claim),'Recovery already attempted')
        history()
        old_id = original_failure()['run_id']
        a_id = a_snapshot()['run_id']
        p = protocol()
        require(p['input']['SHA256']==load(preparation)['new_input_sha256'],'Input drift')
        verify_diff(archived_protocol()[v46.B]['input_text'],p['input_text'])
        seed_path(OUT/'probe_cwd',SOURCE)
        pins(archived_protocol()[v46.B])
        run_id = uuid.uuid4().hex
        new_identity(run_id,(old_id,a_id))
        write(claim,{'run_id':run_id,'UTC':v46.now(),'input_sha256':p['input']['SHA256'],
              'authorization_sha256':sha(auth),'attempts':1,'auto_retry':False})
        RUN.mkdir()
        seed_path(RUN,SOURCE)
        s = v46.supervise(v46.model_argv(p,run_id),RUN,
              v46.Limits(4770,16*2**30,20*2**30,5*2**30,256*2**20,total_output_bytes=5*2**30),
              env=v46.env.runtime_environment(),total_dir=RUN,input_files={'input.inp':INPUT.read_bytes()})
        require(s['qualification']=='PASS' and s['returncode']==0,'Recovery failed; claim preserved')
        write(receipt_path(RUN,'acceptance'),v46.validate(RUN,p,run_id))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true')
    mode.add_argument('--execute',action='store_true')
    opts = parser.parse_args()
    (prepare if opts.prepare else launch)()
