"""Run the V47 positive and negative CPU preflight tests."""
from pathlib import Path

import verify_summer_seed_sensitivity_v46 as independent
from tempfile import TemporaryDirectory
from unittest.mock import patch
import ast
import os
import subprocess

import preflight_summer_seed_recovery_v47 as r
from analyze_summer_seed_recovery_v47 import A, B, RESULT, bind_paths
from atmosphere.restart_validation import REQUIRED, inspect_restart
from audit_summer_assets_v38 import sealed_read


def main():
    tests=[]
    def ok(name, condition):
        r.require(condition,name)
        tests.append(name)

    def reject(name,action):
        try:
            action()
        except (ValueError,OSError,KeyError):
            tests.append(name)
            return
        raise AssertionError(name)

    prepared=r.load(r.OUT/'preparation.json')
    probe=r.load(r.OUT/'tests/fortran_probe.json')
    old=r.original_failure()
    left=r.archived_protocol()[r.v46.B]
    original=r.ROOT/left['source']['path']
    structure=inspect_restart(r.SEED,[172,0,0])
    review=r.v46.resource_review(left)
    ok('Original expanded 147 bytes',probe['old_expanded_bytes']==old['expanded_bytes']==147)
    ok('Original truncated to 120 and failed',probe['diskfile_capacity']==120 and probe['old_exit']==2)
    ok('Fortran and full 34-field read',probe['short_exit']==0 and probe['required_fields_read']==len(REQUIRED)==34)
    ok('Actual wrong CWD rejected',probe['wrong_cwd_exit']==81)
    ok('Source clock matched',structure['structure_complete'] and structure['record_available']
       and probe['source_clock']==[172,0,0])
    ok('Readonly byte-identical source',r.seed_path(r.OUT/'probe_cwd',r.SOURCE)==r.SEED
       and r.sha(original)==r.sha(r.SEED)==r.v45.JUNSOL and original.stat().st_size==r.SEED.stat().st_size)
    reject('Incorrect junsol hash',lambda:r.v45.verify_hash(r.SEED,'0'*64))
    reject('Wrong source record',lambda:r.require(inspect_restart(r.SEED,[80,0,0])['record_available'],'wrong clock'))
    reject('Wrong CWD',lambda:r.seed_path(r.ROOT,r.SOURCE))
    reject('Path traversal',lambda:r.seed_path(r.OUT/'probe_cwd','../../seed.nc'))
    with TemporaryDirectory(dir=r.OUT/'tests') as work:
        from netCDF4 import Dataset
        base=Path(work)
        fake=base/'seed.nc'
        with Dataset(fake,'w') as n:
            n.history_type='primary'
        fake.chmod(0o444)
        reject('Missing required fields',lambda:r.require(inspect_restart(fake,[172,0,0])['structure_complete'],'missing'))
        cwd=base/'probe_cwd'
        cwd.mkdir()
        with patch.object(r,'OUT',base),patch.object(r,'SEED',fake):
            reject('Bad copy',lambda:r.seed_path(cwd,r.SOURCE))
        fake.rename(base/'invalid.nc')
        fake.symlink_to(r.SEED)
        with patch.object(r,'OUT',base),patch.object(r,'SEED',fake):
            reject('Symlink on approved basename',lambda:r.seed_path(cwd,r.SOURCE))
        left_fixture,right_fixture=base/'fixture_A',base/'fixture_B'
        units={'DEN':'g/cm3','ZG':'cm','TN':'K','UN':'cm/s','VN':'cm/s'}
        for group in (left_fixture,right_fixture):
            group.mkdir()
            with Dataset(group/'secondary_001.nc','w') as n:
                for key in ('time','ilev','lev','lat','lon'):
                    n.createDimension(key,1)
                n.createVariable('lat','f8',('lat',))[:]=0
                t=n.createVariable('time','f8',('time',))
                t.units='minutes since 2022-06-07 00:00:00'
                t[:]=60
                for key in (*independent.FIELDS,'ZG'):
                    v=n.createVariable(key,'f8',('time','ilev' if key in ('DEN','ZG') else 'lev','lat','lon'))
                    v.units=units.get(key,'mmr')
                    v[:]=1
        with patch.object(independent,'RUNS',(left_fixture,right_fixture)):
            ok('Synthetic paired volumes bind same first UTC',all(x['DEN'].item()==1 for x in independent.frame(1)))
            with Dataset(right_fixture/'secondary_001.nc','r+') as n:
                n['time'][:]=120
            try:
                independent.frame(1)
            except AssertionError:
                tests.append('Synthetic mismatched UTC refused')
            else:
                raise AssertionError('Mismatched UTC accepted')
    reject('Physics drift',lambda:r.verify_diff(left['input_text'],r.INPUT.read_text().replace("'HEELIS'","'OTHER'")))
    reject('GPI tamper',lambda:r.v45.verify_hash(r.v45.GPI,'0'*64))
    sample=next(iter(prepared['A']['inventory']))
    reject('A output hash tamper',lambda:r.v45.verify_hash(A/sample,'0'*64))
    ok('V46 manifest and immutable evidence',bool(r.history()) and r.sha(r.OLD/'pair_claim.json')==prepared['old_claim_sha256'])
    ok('Old failed record unchanged',old==prepared['old_B'] and old['rank_exit']==[2]*4 and old['steps']==0)
    reject('Old recovery ID reused',lambda:r.new_identity(old['run_id'],[old['run_id']]))
    reject('V46 claim cannot authorize',lambda:r.authorization(r.load(r.OLD/'pair_claim.json'),r.sha(r.OUT/'preparation.json')))
    reject('V47 no authorization',lambda:r.authorization(None,r.sha(r.OUT/'preparation.json')))
    reject('No unseen target access',lambda:sealed_read(object(),'density',[]))
    reject('Explicit GPU selection refused',lambda:r.cpu_only({'CUDA_VISIBLE_DEVICES':'0'}))
    protocol=r.load(r.ROOT/r.v45.V37)
    ok('Frozen lambda and order',protocol['candidates']['ShrinkageHalf']==.5 and protocol['first_pair']==['2021-06-21','2022-06-21'])
    ok('Proper edition binding',bind_paths(A,B,r.OUT)==(A,B,RESULT))
    reject('Old failed B disallowed in adapter',lambda:bind_paths(A,r.OLD/r.v46.B,r.OUT))
    reject('Missing recovery acceptance refuses analysis',lambda:r.verify_engineering(B,r.protocol()))
    ok('Resources and MPI',review['resource_ready'] and review['MPI_version']=='mpirun (Open MPI) 5.0.8')
    ok('No run directory or claim',r.absent(r.RUN) and r.absent(r.receipt_path(r.RUN,'claim')))
    result=subprocess.run([os.sys.executable,'-B',str(r.ROOT/'scripts/preflight_summer_seed_recovery_v47.py'),
                           '--execute'],cwd=r.ROOT,capture_output=True,text=True)
    ok('Live launch CLI gate',result.returncode!=0 and 'New V47 authorization required' in result.stderr)
    ok('Study collection untouched',r.a_snapshot()==prepared['A'])
    r.write(r.OUT/'verification.json',dict(state='V47_B_RECOVERY_READY_FOR_AUTHORIZATION',
        sensitivity='SEED_SENSITIVITY_INCONCLUSIVE',preparation_sha256=r.sha(r.OUT/'preparation.json'),
        result='PASS',tests=tests,test_count=len(tests),fortran=probe,
        launch_attempts=0,authorization=None,run_id=None,model_integration=False,
        density_reads=0,GPU=0))


if __name__=='__main__':
    main()
