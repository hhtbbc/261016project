"""Independent coverage/provenance checks and offline fixture tests for V38."""
import ast
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import resource
import tempfile
from time import monotonic, process_time
import unittest
from unittest.mock import MagicMock, patch
import zipfile

import numpy as np

import audit_summer_assets_v38 as a
from fetch_summer_assets_v38 import BASE, DAYS, OUT, RAW, ROOT, Meter, history_pins, save
from observations.autumn_validation import REQUIRED, inspect_initial, native_field, source_clock
from observations.bounded_swarm_acquisition import archive_plan
from evaluation import shrinkage_unseen_gate_v37 as gate


def payload(key, count, step):
    start=a.datetime(2022,6,5)
    grid=[start+step*i for i in range(count)]
    data={key:[1.0]*count,'datetime':[t.isoformat()+'Z' for t in grid],'meta':{'source':'GFZ Potsdam'}}
    if key=='Kp':
        data['status']=['def']*count
    return data,grid


class Fixtures(unittest.TestCase):
    def deny_driver(self,key,edit):
        p,g=payload(key,168 if key=='Kp' else 2,timedelta(hours=3 if key=='Kp' else 24))
        edit(p)
        with self.assertRaises(ValueError):
            a.parse_gfz(p,key,g)

    def test_valid_Fobs(self):
        p,g=payload('Fobs',2,timedelta(days=1))
        self.assertEqual(a.parse_gfz(p,'Fobs',g),dict.fromkeys(g,1))

    def test_missing_sentinel(self):
        self.deny_driver('Fobs',lambda p:p['Fobs'].__setitem__(0,-1))

    def test_Fobs_gap(self):
        self.deny_driver('Fobs',lambda p:p['datetime'].pop())

    def test_Fobs_duplicate(self):
        self.deny_driver('Fobs',lambda p:p['datetime'].__setitem__(1,p['datetime'][0]))

    def test_Fadj_substitute(self):
        self.deny_driver('Fobs',lambda p:p.update(Fadj=p.pop('Fobs')))

    def test_unknown_unit(self):
        self.deny_driver('Fobs',lambda p:p.update(units='watts'))

    def test_Kp_requires_definitive(self):
        self.deny_driver('Kp',lambda p:p['status'].__setitem__(1,'pre'))

    def test_Kp_missing(self):
        self.deny_driver('Kp',lambda p:p['Kp'].pop())

    def test_Kp_duplicate(self):
        self.deny_driver('Kp',lambda p:p['datetime'].__setitem__(1,p['datetime'][0]))

    def test_Kp_shifted(self):
        self.deny_driver('Kp',lambda p:p['datetime'].__setitem__(0,'2022-06-05T00:30:00Z'))

    def test_101_day_grid(self):
        self.assertEqual(len(a.requested_grid('2022-04-26','2022-08-04',timedelta(days=1))),101)

    def test_81_day_boundaries(self):
        start=date(2022,4,26)
        samples={start+timedelta(days=i):100.0 for i in range(101)}
        self.assertEqual(a.centered(samples,date(2022,6,5)),(100.0,[]))
        self.assertEqual(a.centered(samples,date(2022,6,25)),(100.0,[]))
        del samples[date(2022,8,4)]
        self.assertEqual(a.centered(samples,date(2022,6,25)),(None,[date(2022,8,4)]))

    def test_overlap_is_immutable(self):
        had={1:70}
        self.assertEqual(len(a.merge(had,{1:71})),1)
        self.assertEqual(had,{1:70})

    def valid_stem(self):
        return 'SW_OPER_DNSAPOD_2__20210621T000000_20210621T235930_0301'

    def test_wrong_year(self):
        with self.assertRaises(ValueError):
            a.check_product_stem(self.valid_stem(),'2022-06-21')

    def test_wrong_satellite(self):
        with self.assertRaises(ValueError):
            a.check_product_stem(self.valid_stem().replace('DNSA','DNSB'),DAYS[0])

    def test_wrong_version(self):
        with self.assertRaises(ValueError):
            a.check_product_stem(self.valid_stem().replace('0301','0401'),DAYS[0])

    def write_zip(self,folder,unsafe=False):
        path=Path(folder)/'test.zip'
        stem=self.valid_stem()
        with zipfile.ZipFile(path,'x') as z:
            z.writestr(('../' if unsafe else '')+stem+'.cdf',b'payload-cdf')
            z.writestr(stem+'.HDR',b'payload-hdr')
        return path

    def test_corrupt_ZIP_CRC(self):
        with tempfile.TemporaryDirectory(dir=OUT) as d:
            p=self.write_zip(d)
            p.write_bytes(p.read_bytes().replace(b'payload-cdf',b'corrupt-cdf'))
            with self.assertRaises((ValueError,zipfile.BadZipFile)):
                archive_plan(p,self.valid_stem(),1024)

    def test_path_traversal(self):
        with tempfile.TemporaryDirectory(dir=OUT) as d:
            p=self.write_zip(d,unsafe=True)
            with self.assertRaises(ValueError):
                archive_plan(p,self.valid_stem(),1024)

    def test_wrong_HDR_CDF_identity(self):
        with tempfile.TemporaryDirectory(dir=OUT) as d:
            p=Path(d)/'bad.HDR'
            p.write_text('<root><Fixed_Header><Mission>Other</Mission></Fixed_Header></root>')
            with self.assertRaisesRegex(ValueError,'HDR identity'):
                a.verify_hdr(p,self.valid_stem(),DAYS[0],p)
        with patch.object(a,'CDF') as cdf:
            cdf.return_value.globalattsget.return_value={'TITLE':['other']}
            with self.assertRaisesRegex(ValueError,'CDF identity'):
                a.verify_cdf(p,self.valid_stem(),DAYS[0],[])
            cdf.return_value.varget.assert_not_called()

    def test_density_sealed(self):
        cdf=MagicMock()
        access=[]
        for k in ('density','density_orbitmean','mass_density'):
            with self.assertRaisesRegex(ValueError,'Sealed'):
                a.sealed_read(cdf,k,access)
        cdf.varget.assert_not_called()
        self.assertEqual(access,[])

    def test_size_limits(self):
        with self.assertRaises(ValueError):
            Meter(small=8).receive('small',9)
        with tempfile.TemporaryDirectory(dir=OUT) as d:
            with self.assertRaises(ValueError):
                archive_plan(self.write_zip(d),self.valid_stem(),1)

    def test_seed_missing_native_state(self):
        with patch('observations.autumn_validation.Dataset') as d:
            d.return_value.__enter__.return_value.variables={}
            with self.assertRaisesRegex(ValueError,'Missing complete primary states'):
                inspect_initial('seed','ref')

    def test_seed_wrong_grid(self):
        with patch('observations.autumn_validation.Dataset') as d:
            n,ref=MagicMock(),MagicMock()
            n.variables=dict.fromkeys(REQUIRED)
            n.history_type='primary'
            n.__getitem__.side_effect={'mtime':np.array([[172,0,0]]),'lat':np.array([1,2])}.__getitem__
            ref.__getitem__.side_effect={'lat':np.array([1,3])}.__getitem__
            d.side_effect=[n,ref]
            n.__enter__.return_value=n
            ref.__enter__.return_value=ref
            with self.assertRaisesRegex(ValueError,'Grid mismatch lat'):
                inspect_initial('seed','ref')

    def test_seed_wrong_clock(self):
        with self.assertRaises(ValueError):
            source_clock([[172,0,5]])

    def test_seed_nonfinite_or_native_fill(self):
        mock=MagicMock(spec=['__getitem__','set_auto_mask','name'])
        mock.__getitem__.return_value=np.array([np.nan])
        with self.assertRaises(ValueError):
            native_field(mock)
        mock.__getitem__.return_value=np.array([1e36])
        self.assertTrue(native_field(mock)[1].all())

    def test_policy_cannot_publish_config(self):
        evidence=dict.fromkeys(gate.REQUIREMENTS['integration'],True)
        evidence['season_seed_approved']=False
        with self.assertRaises(ValueError):
            gate.admit(DAYS[0],'integration',approved={(DAYS[0],'integration')},
                predecessors=(gate.StageReceipt(DAYS[0],'identity','1'*64,'PASS'),),
                evidence=evidence,operation='CPU_SINGLE_MODEL')

    def test_V37_frozen_methods_and_dates(self):
        self.assertTrue(history_pins())
        self.assertEqual(DAYS,gate.SUMMER)

    def test_no_GPI_or_input_publication_path(self):
        modules=['fetch_summer_assets_v38','retry_summer_swarm_v38','audit_summer_assets_v38']
        for module in modules:
            tree=ast.parse((ROOT/'scripts'/f'{module}.py').read_text())
            self.assertFalse({'write_gpi','write_input','generate_input'} & {
                n.id for n in ast.walk(tree) if isinstance(n,ast.Name)})

    def test_no_model_or_GPU_access(self):
        for op in ('GPU','AUTOMATIC_MODEL_START'):
            with self.assertRaises(ValueError):
                gate.admit(DAYS[0],'identity',approved={(DAYS[0],'identity')},operation=op)

    def test_score_not_authorized(self):
        with self.assertRaises(ValueError):
            gate.admit(DAYS[0],'score',approved={(DAYS[0],'identity')},operation='FUTURE_ONCE')

    def test_pinned_source_parse_metadata(self):
        p,g=payload('Fobs',2,timedelta(days=1))
        p['meta']['source']='other'
        with self.assertRaises(ValueError):
            a.parse_gfz(p,'Fobs',g)


def independent():
    wall,cpu=monotonic(),process_time()
    tests=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Fixtures))
    if not tests.wasSuccessful():
        raise SystemExit(1)
    audit=a.read_json(OUT/'asset_audit.json')
    assets=a.read_json(OUT/'download_manifest.json')['assets']
    assets.update(a.read_json(OUT/'ESA_retry_manifest.json')['assets'])
    all_files=list(audit['prior_GFZ'])+list(assets.values())
    daily,bins={},{}
    def insert(series,key,value,revision=False):
        if key in series and series[key]!=value:
            assert revision and series[key]==Decimal(-1) and value>0, key
        series[key]=value
    for item in all_files:
        path=ROOT/item['path']
        body=path.read_bytes()
        assert hashlib.sha256(body).hexdigest()==item['SHA256']
        key=item.get('index')
        if key and key.startswith('2021'):
            for line in body.decode().splitlines():
                fields=line.split()
                if not fields or fields[0]!='2021':
                    continue
                d=date(*map(int,fields[:3]))
                insert(daily,str(d),Decimal(fields[25]))
                if fields[27]=='2':
                    for i,v in enumerate(fields[7:15]):
                        if 0<=Decimal(v)<=9:
                            insert(bins,f'{d}T{3*i:02d}:00:00Z',Decimal(v))
        elif key in ('Fobs','Kp') or path.name.startswith(('Fobs_','Kp_')):
            obj=json.loads(body,parse_float=Decimal)
            key=key or path.name.split('_')[0]
            assert len(obj['datetime'])==len(set(obj['datetime']))==len(obj[key])
            assert obj['meta']['source']=='GFZ Potsdam'
            for i,(t,v) in enumerate(zip(obj['datetime'],obj[key],strict=True)):
                if key=='Fobs':
                    assert t.endswith('T00:00:00Z')
                    insert(daily,t[:10],Decimal(v),path.parent==RAW and t[:4]=='2021')
                else:
                    assert obj['status'][i]=='def' and t[11:13] in ('00','03','06','09','12','15','18','21')
                    insert(bins,t,Decimal(v))
    details={}
    for day in DAYS:
        yr=int(day[:4])
        f0=date(yr,4,26)
        requested=[str(f0+timedelta(days=i)) for i in range(101)]
        missing=[d for d in requested if daily.get(d,0)<=0]
        targets=[date(yr,6,5)+timedelta(days=i) for i in range(21)]
        kb={f'{d}T{h:02d}:00:00Z' for d in targets for h in range(0,24,3)}
        found_b=sorted(kb-bins.keys())
        row=audit['GFZ'][day]
        assert row['Fobs_missing']==missing and row['Kp_missing']==found_b
        mean_count=0
        for t in targets:
            span=[daily.get(str(t+timedelta(days=j)),Decimal(-1)) for j in range(-40,41)]
            assert len(span)==81
            observed=row['daily_center81_check_sfu'][str(t)]
            if min(span)>0:
                assert np.isclose(float(sum(span)/81),observed,rtol=1e-13,atol=0)
                mean_count+=1
            else:
                assert observed is None
        assert mean_count==row['valid_centers']
        assert targets[0]==date(yr,6,7)-timedelta(days=2) and targets[-1]==date(yr,6,23)+timedelta(days=2)
        details[day]=dict(Fobs=101-len(missing),Kp=168-len(found_b),centers=mean_count)
    for day,obs in audit['Swarm'].items():
        if obs['status']=='METADATA_VERIFIED_DENSITY_SEALED':
            stem=Path(assets['Swarm_'+day]['path']).stem
            with zipfile.ZipFile(ROOT/assets['Swarm_'+day]['path']) as z:
                for m in obs['members']:
                    p=ROOT/m['path']
                    assert p.name in (stem+'.cdf',stem+'.HDR')
                    assert p.stat().st_size==z.getinfo(p.name).file_size
                    assert hashlib.sha256(p.read_bytes()).hexdigest()==m['SHA256']
            assert set(obs['accessed_data_variables'])==set(a.DATA_FIELDS) and not obs['target_density_decodes']
    seed=audit['junsol']
    if seed['status']=='JUNSOL_SEED_STATIC_COMPATIBLE':
        from netCDF4 import Dataset
        with Dataset(ROOT/seed['original']['path']) as n:
            assert len(REQUIRED)==34 and set(REQUIRED)<=set(n.variables)
            assert tuple(map(int,n['mtime'][0]))==tuple(seed['native']['SOURCE_START'])
            assert tuple(len(n.dimensions[k]) for k in ('lat','lon','lev','ilev'))==(36,72,29,29)
            assert n.history_type=='primary'
    assert all(audit[k]==0 for k in ('new_model_runs','new_GPI','new_formal_input','unseen_target_density_reads','new_scientific_scores','new_fits','GPU'))
    save('independent_review.json',dict(state='VERIFIED_ACTUAL_AVAILABLE_ASSETS',tests=tests.testsRun,
        failures=0,rehashed_originals_and_reused_sources=len(all_files),GFZ_independent=details,
        V37_pins=len(history_pins()),wall_s=monotonic()-wall,CPU_s=process_time()-cpu,
        peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))


if __name__=='__main__':
    independent()
