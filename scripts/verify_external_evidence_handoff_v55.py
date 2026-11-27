"""Check frozen inputs and exercise V55 handoff with strictly synthetic SP3."""
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import admit_swarm_sp3_v55 as sp
import check_external_evidence_v55 as intake
import test_swarm_tiegcm_registration_v55 as kernel
import audit_swarm_external_datum_v54 as prior
from audit_2021_gfz_revision_v54 import OUT as V54
from runtime.tiegcm_rank_exit import write_once

BASE='ce3c07625a231255267569f93948c1c8dc218d21'


def verify_history():
    p=V54/'publication_SHA256.json'
    blob=subprocess.check_output(['git','show',f'{BASE}:{p.relative_to(sp.ROOT)}'],cwd=sp.ROOT)
    assert p.read_bytes()==blob
    manifest=json.loads(blob)
    for name,h in manifest.items():
        assert hashlib.sha256((sp.ROOT/name).read_bytes()).hexdigest()==h
    _,pins=prior.inputs()
    products=prior.products()
    protocol=prior.pinned(sp.ROOT/'experiments/thermosphere_shrinkage_unseen_prereg_v37/preregistered_protocol.json')
    assert protocol['first_pair']==['2021-06-21','2022-06-21'] and protocol['candidates']['ShrinkageHalf']==.5
    assert protocol['current_authorized_operation']=='METADATA_ONLY'
    return dict(V54_manifest=len(manifest),assets=pins,products=products)


def synth(path,*,span=4,clock='UTC',baseline='IGS20'):
    start=datetime(2021,6,21)
    header=f"#cV2021 06 21 00 00  0.00000000 {span:7d} ORBIT {baseline:5s} FIT V55"
    # First line fixed columns match the frozen SP3-c P/V parser.
    assert header[32:39].strip()==str(span) and header[46:51]==baseline
    rows=[header,'## 2163  86400.0 21600.0 59386 0.0','+    1   L01',f'%c cc {clock}']
    for i in range(span):
        t=start+timedelta(hours=6*i)
        rows.extend([f'*  {t:%Y %m %d %H %M}  0.00000000',
            'PL01'+''.join(f'{x:14.6f}' for x in (6828.137,0.,0.,0.)),
            'VL01'+''.join(f'{x:14.6f}' for x in (0.,75.,0.,0.))])
    path.write_text('\n'.join(rows+['EOF'])+'\n',encoding='ascii')
    return dict(source_url='https://example.invalid/V55-synthetic',sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        satellite='Swarm A',satellite_record_id='L01',time_system='UTC',filename_day_scale='UTC',
        SP3_frame_code='IGS20',frame_realization='SYNTHETIC_IGS20',frame_epoch='2015.0',
        point='COM',CDF_point='COM',reference_evidence='V55 synthetic only',
        position_unit='km',expected_interval_s=21600)


class Contracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=sp.HANDOFF,prefix='.synthetic-test-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.src=self.root/'staging'
        self.dst=self.root/'accepted'
        self.src.mkdir()
        self.dst.mkdir()
        self.name=next(iter(sp.targets()))
        self.path=self.src/self.name
        self.meta=synth(self.path)
    def test_nominal_and_geometry(self):
        orbit,t,r=sp.validate(self.path,self.meta)
        self.assertEqual(r['records'],4)
        rows=[{'sample_id':str(i), 'UTC':x.isot+'Z','latitude_deg':'0','longitude_deg':'0','altitude_m':'450000'}
              for i,x in enumerate(t)]
        found=sp.compare_geometry(orbit,t,rows)
        self.assertEqual(len(found),4)
        self.assertLess(max(abs(x['altitude_error_m']) for x in found),1e-7)
    def test_bad_version_and_date(self):
        wrong=self.path.with_name(self.name.replace('0504','0601'))
        with self.assertRaises(ValueError): sp.validate(wrong,self.meta)
        altered=self.path.read_bytes().replace(b'2021 06 21',b'2021 06 22')
        self.path.write_bytes(altered)
        with self.assertRaises(ValueError):
            sp.validate(self.path,self.meta|{'sha256':hashlib.sha256(altered).hexdigest()})
    def test_wrong_satellite(self):
        with self.assertRaises(ValueError): sp.validate(self.path,self.meta|{'satellite_record_id':'L02'})
    def test_wrong_clock(self):
        with self.assertRaises(ValueError): sp.validate(self.path,self.meta|{'time_system':'GPS'})
    def test_gps_conversion(self):
        from orbit.frames import configure_time_data
        configure_time_data()
        gps=sp.convert_clock([datetime(2021,6,21,0,0,18)],'GPS')
        self.assertEqual(gps[0].isot,'2021-06-21T00:00:00.000')
    def test_wrong_units(self):
        with self.assertRaises(ValueError): sp.validate(self.path,self.meta|{'position_unit':'m'})
    def test_wrong_sha(self):
        with self.assertRaises(ValueError): sp.validate(self.path,self.meta|{'sha256':'0'*64})
    def test_truncated(self):
        self.path.write_bytes(self.path.read_bytes()[:-5])
        with self.assertRaises(ValueError): sp.validate(self.path,self.meta)
    def test_incomplete_day(self):
        meta=synth(self.path,span=3)
        with self.assertRaises(ValueError): sp.validate(self.path,meta)
    def test_path_escape(self):
        with self.assertRaises(ValueError): sp.safe_directory(self.root/'..')
        with self.assertRaises(ValueError): sp.admit('../'+self.name)
    def test_symlink(self):
        target=self.root/'source.sp3'
        self.path.rename(target)
        self.path.symlink_to(target)
        with self.assertRaises(OSError): sp.validate(self.path,self.meta)
    def test_no_overwrite(self):
        (self.src/(self.name+'.source.json')).write_text(json.dumps(self.meta))
        with patch.object(sp,'STAGING',self.src),patch.object(sp,'ACCEPTED',self.dst):
            r=sp.admit(self.name)
            self.assertEqual(r['scope'],'SP3_BYTES_AND_STRUCTURE_ONLY')
            self.assertEqual((self.dst/self.name/self.name).stat().st_mode&0o777,0o444)
            with self.assertRaises(FileExistsError): sp.admit(self.name)
        (self.dst/self.name).chmod(0o755)
    def test_declaration_is_pending(self):
        filename='GFZ_2021_evidence.json'
        x=self.src/'source.txt'
        x.write_text('synthetic evidence')
        with patch.object(intake,'STAGING',self.src):
            doc={'issuer':'GFZ','document_id':'synthetic','version_or_date':'fixture',
                 'public_reference':'https://example.invalid/fixture','dates':['2021-05-09'],
                 'observation_definition':'fixture','attachments':[{'file':x.name,
                     'sha256':hashlib.sha256(x.read_bytes()).hexdigest()}]}
            (self.src/filename).write_text(json.dumps(doc))
            self.assertEqual(intake.declaration(filename,intake.DECLARATIONS[filename])['state'],
                             'RECEIVED_PENDING_AUTHORITY_REVIEW')
            doc['attachments'][0]['file']='../source.txt'
            (self.src/filename).write_text(json.dumps(doc))
            with self.assertRaises(ValueError): intake.declaration(filename,intake.DECLARATIONS[filename])
    def test_geometry_adjudication(self):
        with patch.object(sp,'STAGING',self.src),patch.object(sp,'ACCEPTED',self.dst):
            (self.src/(self.name+'.source.json')).write_text(json.dumps(self.meta))
            sp.admit(self.name)
            with self.assertRaises(OSError): sp.compare_accepted(self.name)
            (self.dst/self.name).chmod(0o755)


def independent_polynomial():
    # Separate evaluation using explicit multilinear monomial coefficients and a different grid of queries.
    terms=np.zeros((2,2,2))
    terms[0,0,0]=1.5
    terms[1,0,0]=.12
    terms[0,1,0]=.16
    terms[0,0,1]=.09
    terms[1,1,0]=.07
    terms[1,0,1]=.03
    terms[0,1,1]=.05
    terms[1,1,1]=.02
    errors=[]
    with tempfile.TemporaryDirectory(dir=kernel.OUT,prefix='.v55-independent-') as tmp:
        model=Path(tmp)/'fixture.nc'
        kernel.fixture(model)
        with kernel.HourlyFixtureProvider(model) as provider:
            for t in (0,30,750,1890,3570,3600):
                for phi in (-87.5,-84.32,84.9,87.5):
                    for lam in (-180.,175.01,179.99):
                        height=382123.
                        x=(lam+185)%360/5
                        polynomial=np.polynomial.polynomial.polyval3d(t/3600,phi/90,x,terms)
                        expected=1e-12*polynomial*np.exp(-.00002*(height-320000.))
                        output=kernel.native(provider,t,phi,lam,height)
                        assert output.valid
                        errors.append(abs(output.rho_kg_m3/expected-1))
    assert max(errors)<1e-11
    return dict(count=len(errors),maximum_relative=float(max(errors)))


def main():
    identity=verify_history()
    result=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Contracts))
    assert result.wasSuccessful()
    independent=independent_polynomial()
    ready=intake.check()
    numerical=json.loads((kernel.OUT/'synthetic_interpolation.json').read_text())
    assert numerical['maximum_relative']<1e-11 and numerical['sample_ids_unique']
    assert 'EXTERNAL_DATUM_UNVERIFIED' in ready['frozen_gates_unchanged']
    write_once(kernel.OUT/'handoff_status.json',ready)
    write_once(kernel.OUT/'independent.json',dict(historical=identity,SP3_handoff_tests=result.testsRun,
        numeric_positive=numerical['control_points'],numeric_negative=len(numerical['negative_cases']),
        independent_polynomial=independent,
        actual_external_materials=len([v for v in ready['candidates'].values() if v['state']!='NOT_ACQUIRED']),
        density_reads=0,new_TIEGCM_runs=0,formal_scores=0,GPU=0,external_messages=0))


if __name__=='__main__':
    main()
