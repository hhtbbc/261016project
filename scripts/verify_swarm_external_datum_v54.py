"""Independent V54 numeric and evidence checks. No sealed CDF reads."""
import csv
import hashlib
import json
from pathlib import Path
import unittest

from cdflib import CDF
import erfa
from netCDF4 import Dataset
import numpy as np

import audit_swarm_external_datum_v54 as a
import audit_2021_gfz_revision_v54 as gfz
from atmosphere.tiegcm_density_provider import TiegcmDensityProvider


def inverse_iterative(xyz,a_axis,flattening):
    """Fixed-point latitude with height projected on the ellipsoid normal."""
    e2=flattening*(2-flattening)
    x,y,z=xyz.T
    p=np.hypot(x,y)
    phi=np.arctan2(z,p*(1-e2))
    for _ in range(12):
        N=a_axis/np.sqrt(1-e2*np.sin(phi)**2)
        phi=np.arctan2(z+e2*N*np.sin(phi),p)
    normal_radius=a_axis*np.sqrt(1-e2*np.sin(phi)**2)
    return np.arctan2(y,x),phi,p*np.cos(phi)+z*np.sin(phi)-normal_radius


def verify_products(rows):
    coordinates={}
    ledger=[]
    for p in rows:
        name=p['zip']
        cp=a.handoff.handoff.HOME_DIR/'accepted'/name/(Path(name).stem+'.cdf')
        cdf=CDF(cp)
        assert cdf.globalattsget()['TITLE']==[Path(name).stem]
        assert cdf.varinq('density').Last_Rec==cdf.varinq('density_orbitmean').Last_Rec==2879
        with a.handoff.sealed_access(ledger):
            lon,lat,h=[cdf.varget(k) for k in ('longitude','latitude','altitude')]
        with (a.V53/f"metadata_{p['day'][:4]}.csv").open() as f:
            published=list(csv.DictReader(f))
        for vals,name in zip((lon,lat,h),('longitude_deg','latitude_deg','altitude_m')):
            assert np.array_equal(vals,[float(r[name]) for r in published])
        xyz=erfa.gd2gce(*a.GRS80,np.deg2rad(lon),np.deg2rad(lat),h)
        lam,phi,height=inverse_iterative(xyz,*a.GRS80)
        projected=erfa.gd2gce(*a.GRS80,lam,phi,height)
        assert np.max(np.abs(height-h))<1e-7
        assert np.max(np.abs(np.rad2deg(phi)-lat))<1e-11
        assert np.max(np.abs((np.rad2deg(lam)-lon+180)%360-180))<1e-11
        errors=np.linalg.norm(projected-xyz,axis=1)
        assert errors.max()<1e-7
        yw,pw,hw=inverse_iterative(xyz,*a.WGS84)
        assert np.max(np.linalg.norm(erfa.gd2gce(*a.WGS84,yw,pw,hw)-xyz,axis=1))<1e-7
        coordinates[p['day']]=dict(max_abs_height_roundtrip_m=float(np.max(np.abs(height-h))),
           P95_XYZ_roundtrip_m=float(np.percentile(errors,95)),max_XYZ_roundtrip_m=float(errors.max()),
           samples=len(xyz),max_same_XYZ_height_parameter_change_m=float(np.max(np.abs(hw-h))))
    return coordinates,ledger


def verify_public():
    checked=0
    groups=('document_requests.json','catalogue_requests.json','esa_sata_requests.json',
            'exact_public_catalogue.json','level1b_request.json','level1b_entire_mission_request.json',
            'mod_entire_mission_request.json','mod_entire_mission_A_request.json','mod_archive_days.json')
    for f in groups:
        rows=a.history.run.load(a.OUT/f)
        for row in rows if isinstance(rows,list) else [rows]:
            if 'file' in row:
                assert hashlib.sha256((a.ROOT/row['file']).read_bytes()).hexdigest()==row['SHA256']
                checked+=1
    catalogue=a.history.run.load(a.OUT/'exact_public_catalogue.json')
    for product in a.products():
        name=product['zip']
        day=product['day'].replace('-','')
        listed=[x for r in catalogue for x in r.get('exact_day',[]) if x['name']==name]
        assert len(listed)==1 and listed[0]['size']==(a.ROOT/name).stat().st_size
        mod=[x for r in catalogue for x in r.get('exact_day',[]) if 'MODA_SC' in x['name'] and day in x['name']]
        assert len(mod)==1 and mod[0]['name'].endswith('_0601.ZIP')
        archive=[x for r in a.history.run.load(a.OUT/'mod_archive_days.json') for x in r['exact_day'] if day in x['name']]
        assert [x['name'] for x in archive]==[mod[0]['name']]
        assert product['orbit_status']=='SP3_EXACT_PRODUCT_NOT_ACQUIRED'
    revision=a.history.run.load(a.OUT/'gfz.json')
    prior=a.ROOT/'data/raw/thermosphere_summer_data_acquisition_v38'
    for day,r in revision['API'].items():
        raw=(a.ROOT/r['file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==r['SHA256']
        assert raw==(prior/f'Fobs_{day}_{day}.json').read_bytes()
        assert json.loads(raw)['Fobs']==[-1.]
        checked+=1
    return checked


def main():
    result=a.history.run.load(a.OUT/'external_audit.json')
    coords,ledger=verify_products(result['products'])
    verified=verify_public()
    samples=0
    for role in 'AB':
        folder=a.history.run.run_path(role)
        with Dataset(folder/'secondary_022.nc') as nc:
            assert tuple(nc['DEN'].dimensions)==tuple(nc['ZG'].dimensions)==('time','ilev','lat','lon')
            nc.set_auto_mask(False)
            x=np.asarray(nc['ZG'][:,0])
            y=np.asarray(nc['Z'][:,0])
            assert np.array_equal(x,y)
            samples+=x.size
    protocol=a.pinned(a.ROOT/'experiments/thermosphere_shrinkage_unseen_prereg_v37/preregistered_protocol.json')
    assert protocol['first_pair']==['2021-06-21','2022-06-21']
    assert protocol['current_authorized_operation']=='METADATA_ONLY'
    assert protocol['candidates']['ShrinkageHalf']==.5
    class Negative(unittest.TestCase):
        def setUp(self):
            self.name=result['products'][0]['SP3']
            self.day=result['products'][0]['day']
            self.meta={'time_system':'GPS','position_unit':'km','frame_realization':'ITRF2020',
                       'frame_epoch':'2015.0','point':'COM','CDF_point':'COM','reference_evidence':'synthetic fixture'}
        def test_baseline(self):
            with self.assertRaises(ValueError): a.validate_sp3_contract(self.name.replace('0504','0601'),self.day,self.meta)
        def test_date(self):
            with self.assertRaises(ValueError): a.validate_sp3_contract(self.name,'2022-06-21',self.meta)
        def test_clock(self):
            with self.assertRaises(ValueError): a.validate_sp3_contract(self.name,self.day,self.meta|{'time_system':'local'})
        def test_units(self):
            with self.assertRaises(ValueError): a.validate_sp3_contract(self.name,self.day,self.meta|{'position_unit':'m'})
        def test_unknown_frame(self):
            with self.assertRaises(ValueError): a.validate_sp3_contract(self.name,self.day,self.meta|{'frame_realization':'ITRF'})
        def test_point(self):
            with self.assertRaises(ValueError): a.validate_sp3_contract(self.name,self.day,self.meta|{'point':'APC'})
        def test_synthetic_contract(self):
            a.validate_sp3_contract(self.name,self.day,self.meta)
        def test_no_density(self):
            with a.handoff.sealed_access(ledger):
                for name in ('density','density_orbitmean'):
                    with self.assertRaises(ValueError): CDF.varget(object(),name)
        def test_no_external_registration(self):
            p=object.__new__(TiegcmDensityProvider)
            p.source='synthetic'
            self.assertEqual(p.query_external(object()).reason,'EXTERNAL_DATUM_UNVERIFIED')
            self.assertIsNone(result['model']['external_height_bound_m'])
            self.assertEqual(result['model']['external_control_points'],0)
        def test_no_offset_release(self):
            p=object.__new__(TiegcmDensityProvider)
            with self.assertRaisesRegex(ValueError,'EXTERNAL_DATUM_UNVERIFIED'):
                p.density_kg_m3({'height_offset_m':10000})
        def test_fadj_refused(self):
            with self.assertRaises(ValueError): gfz.observed({'Fadj':[76],'datetime':[self.day+'T00:00:00Z']},self.day)
        def test_bad_timestamp(self):
            with self.assertRaises(ValueError):
                gfz.observed({'Fobs':[76],'datetime':[self.day+'T20:00:00Z']},self.day)
        def test_preserve_missing(self):
            self.assertEqual(gfz.observed({'Fobs':[-1.],'datetime':[self.day+'T00:00:00Z']},self.day),-1.)
        def test_no_auto_GPI(self):
            state=a.history.run.load(a.OUT/'gfz.json')
            self.assertEqual((state['writes_to_GPI'],state['fill_values_substituted']),(0,0))
    suite=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Negative))
    assert suite.wasSuccessful()
    a.history.run.write_once(a.OUT/'independent.json',dict(independent_iterative=coords,
        model_bottom_cells=samples,checked_public_hashes=verified,
        test_cases=suite.testsRun,access_ledger=ledger,density_reads=0,density_orbitmean_reads=0,
        formal_scores=0,AI_training=0,GPU=0,new_model_runs=0))


if __name__=='__main__':
    main()
