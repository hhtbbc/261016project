"""Physical-input contracts with isolated CDF fixtures and real Jan4 records."""
from pathlib import Path
import sys,tempfile,unittest,json
import numpy as np
from cdflib import cdfwrite,cdfepoch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from orbit.swarm_force_inputs import *
F=ROOT/'experiments/swarm_physical_force_readiness_v1'

def write_fixture(folder,kind,*,version='0601',mass_unit='kg',qdesc='Quaternion, transformation: ITRF <- S/C',data=None,gap=False):
    p=folder/(kind+'.cdf');t=cdfepoch.compute_epoch([[2023,1,4,1,0,s,0] for s in ([0,1,4,5] if gap else [0,1,2,3])]);values=dict(Timestamp=t,Flags_q=np.zeros(4),SyncStatus=np.zeros(4))
    if kind=='SC_ADYN':values.update(m_SC=np.arange(4,dtype=float)+400,Flags_Platform=np.zeros(4),dt_thr=np.zeros((4,12)),f_thr=np.zeros((4,3)),thr_set=np.ones(4))
    else:values.update(q=np.tile([0.,0.,0.,1.],(4,1)),Maneuver_Id=np.zeros(4))
    if data:values.update(data)
    c=cdfwrite.CDF(p);c.write_globalattrs({k:{0:v} for k,v in dict(File_Version=version,File_Type=kind+'_1B',Sensing_Start='UTC=2023-01-04T01:00:00.000',Software_Version='SYNTHETIC_TEST_ONLY',Proc_Time='UTC=2026-11-03').items()})
    for k,v in values.items():
        attrs={'UNITS':{'m_SC':mass_unit,'dt_thr':'s','f_thr':'mN'}.get(k,'-')}
        if k=='q':attrs['DESCRIPTION']=qdesc
        c.write_var(dict(Variable=k,Data_Type=cdfwrite.CDF.CDF_EPOCH if k=='Timestamp' else cdfwrite.CDF.CDF_DOUBLE,Num_Elements=1,Rec_Vary=True,Dim_Sizes=list(v.shape[1:])),var_attrs=attrs,var_data=v)
    c.close();return p

class ForceInputTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=F,prefix='test_fixture_');self.folder=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def make(self,dc=None,ac=None):
        d=write_fixture(self.folder,'SC_ADYN',**(dc or {}));a=write_fixture(self.folder,'STRAATT',**(ac or {}));return SwarmForceInputProvider(d,a,source_sha256={'SC_ADYN':file_sha(d),'STRAATT':file_sha(a)})
    def test_fractional_CDF_epoch_precision_preserved(self):
        base=float(cdfepoch.compute_epoch([2023,1,4,1,0,0,0]));t=cdf_epoch_utc64(np.array([base+.75]));self.assertEqual(t[0],np.datetime64('2023-01-04T01:00:00.000750000'));self.assertEqual(utc64('2023-01-04T01:00:00.000500Z'),np.datetime64('2023-01-04T01:00:00.000500000'))
    def test_time_and_mass_units(self):
        p=self.make();r=p.at('2023-01-04T01:00:01Z');self.assertEqual(r.mass.value,401);self.assertEqual(r.mass.unit,'kg')
    def test_time_scale_must_be_explicit(self):
        p=self.make()
        for t in ['2023-01-04T01:00:01','2023-01-04T01:00:01 GPS','NaTZ']:
            with self.assertRaises(ValueError):p.at(t)
    def test_no_future_mass_or_interpolation(self):
        r=self.make().at('2023-01-04T01:00:00.500Z');self.assertEqual(r.mass.value,400);self.assertEqual(r.provenance['SC_ADYN']['age_s'],.5);self.assertIn('NOT_interpolation',r.provenance['SC_ADYN']['time_method'])
    def test_no_gap_bridging(self):
        p=self.make({'gap':True},{'gap':True})
        with self.assertRaisesRegex(ValueError,'Gap'):p.at('2023-01-04T01:00:03Z')
    def test_unit_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,'units'):self.make({'mass_unit':'g'})
    def test_version_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError,'version'):self.make({'version':'0501'})
    def test_corrupt_file_rejected(self):
        d=write_fixture(self.folder,'SC_ADYN');a=write_fixture(self.folder,'STRAATT');h=file_sha(d)
        with d.open('ab') as f:f.write(b'corrupt')
        with self.assertRaisesRegex(ValueError,'SHA'):SwarmForceInputProvider(d,a,source_sha256={'SC_ADYN':h,'STRAATT':file_sha(a)})
    def test_mutation_after_load_rejected(self):
        p=self.make()
        with p.paths['SC_ADYN'].open('ab') as f:f.write(b'changed')
        with self.assertRaisesRegex(ValueError,'SHA'):p.at('2023-01-04T01:00:01Z')
    def test_direction_metadata_mismatch(self):
        with self.assertRaisesRegex(ValueError,'direction'):self.make(ac={'qdesc':'S/C <- ITRF'})
    def test_valid_CDF_wrong_vector_shape_rejected(self):
        with self.assertRaisesRegex(ValueError,'dimensions'):self.make(ac={'data':{'q':np.zeros((4,3))}})
    def test_formal_refuses_without_evidence(self):
        with self.assertRaisesRegex(ValueError,'BLOCKED'):self.make().at('2023-01-04T01:00:01Z',mode=Mode.FORMAL_VALIDATED)
    def test_boolean_not_a_gate(self):
        p=self.make()
        for mode in [True,False,'FORMAL_VALIDATED']:
            with self.assertRaisesRegex(ValueError,'enum'):p.at('2023-01-04T01:00:01Z',mode=mode)
    def test_no_area_or_cd_fallback(self):
        r=self.make().at('2023-01-04T01:00:01Z');self.assertIsNone(r.effective_area.value);self.assertIsNone(r.Cd.value);self.assertFalse(r.formal_ready)
    def test_bad_mass_not_filled(self):
        r=self.make({'data':{'m_SC':np.full(4,np.nan)}}).at('2023-01-04T01:00:01Z');self.assertIsNone(r.mass.value);self.assertEqual(r.mass.status,'INVALID')
    def test_bad_quaternion_not_filled(self):
        r=self.make(ac={'data':{'q':np.full((4,4),np.nan)}}).at('2023-01-04T01:00:01Z');self.assertIsNone(r.attitude.value);self.assertEqual(r.attitude.status,'INVALID')
    def test_nonunit_product_quaternion_rejected_numerically(self):
        q=np.tile([0.,0.,0.,2.],(4,1));r=self.make(ac={'data':{'q':q}}).at('2023-01-04T01:00:01Z');self.assertEqual(r.attitude.status,'INVALID');self.assertIsNone(r.attitude.value)
    def test_zero_nominal_force_not_no_thrust(self):
        on=np.zeros((4,12));on[1,0]=.1;r=self.make({'data':{'dt_thr':on}}).at('2023-01-04T01:00:01Z');self.assertTrue(r.thrust.value['candidate_on_time']);self.assertIsNone(r.thrust.value['actual_force_N']);self.assertEqual(r.thrust.status,'UNVERIFIED')
    def test_mN_to_N_is_explicit(self):
        r=self.make({'data':{'f_thr':np.ones((4,3))}}).at('2023-01-04T01:00:01Z');np.testing.assert_array_equal(r.thrust.value['nominal_force_N'],[.001]*3)
    def test_unknown_quality_not_silently_nominal(self):
        r=self.make({'data':{'Flags_Platform':np.full(4,255)}}).at('2023-01-04T01:00:01Z');self.assertEqual(r.quality['SC_ADYN']['Flags_Platform'],255);self.assertEqual(r.mass.status,'PARTIAL');self.assertFalse(r.formal_ready)
    def test_external_time_boundaries(self):
        p=self.make()
        for t in ['2023-01-04T00:59:59Z','2023-01-04T01:00:04Z']:
            with self.assertRaisesRegex(ValueError,'coverage'):p.at(t)
    def test_real_rotation_never_guessed(self):
        with self.assertRaisesRegex(ValueError,'UNVERIFIED'):self.make().rotation_to_itrs('2023-01-04T01:00:01Z')
    def test_synthetic_known_rotation_and_inverse(self):
        R=synthetic_quaternion_matrix_xyzw([0,0,np.sqrt(.5),np.sqrt(.5)]);np.testing.assert_allclose(R@[1,0,0],[0,1,0],atol=1e-14);np.testing.assert_allclose(R.T@R,np.eye(3),atol=1e-14);self.assertAlmostEqual(np.linalg.det(R),1);np.testing.assert_allclose(R.T@(R@[2.,3.,4.]),[2,3,4],atol=1e-14)
    def test_nonunit_synthetic_not_normalized(self):
        with self.assertRaises(ValueError):synthetic_quaternion_matrix_xyzw([0,0,0,2])
    def test_synthetic_box_projection(self):
        a=np.array([[12,0,0],[-12,0,0],[0,8,0],[0,-8,0],[0,0,6],[0,0,-6]])
        self.assertEqual(synthetic_convex_projected_area(a,[1,0,0]),12);self.assertAlmostEqual(synthetic_convex_projected_area(a,[1,1,0]),20/np.sqrt(2))
        R=synthetic_quaternion_matrix_xyzw([0,np.sqrt(.5),0,np.sqrt(.5)]);self.assertAlmostEqual(synthetic_convex_projected_area(a@R.T,R@[1,1,0]),20/np.sqrt(2))
    def test_incomplete_geometry_and_zero_flow_rejected(self):
        with self.assertRaises(ValueError):synthetic_convex_projected_area(np.eye(3),[1,0,0])
        with self.assertRaises(ValueError):synthetic_convex_projected_area(np.zeros((6,3)),[0,0,0])
    def test_provenance_retained(self):
        p=self.make();r=p.at('2023-01-04T01:00:01Z');self.assertEqual(r.provenance['SC_ADYN']['SHA256'],p.sha['SC_ADYN']);self.assertEqual(r.provenance['SC_ADYN']['version'],'0601');self.assertEqual(r.provenance['STRAATT']['record_index'],1);self.assertEqual(r.provenance['STRAATT']['quaternion_declared_frames']['to'],'ITRF');self.assertIsNone(r.provenance['STRAATT']['quaternion_declared_frames']['component_order'])
    def test_real_Jan4_records_match_CDF_and_gate(self):
        j=json.loads((F/'CDF_contracts.json').read_text());z={x['product']:x for x in j};p=SwarmForceInputProvider(ROOT/z['SC_ADYN']['path'],ROOT/z['STRAATT']['path'],source_sha256={k:v['SHA256'] for k,v in z.items()})
        for h in [1,7,13]:
            r=p.at(f'2023-01-04T{h:02d}:00:00Z');self.assertTrue(400.7<r.mass.value<400.9);self.assertIsNone(r.Cd.value);self.assertEqual(r.provenance['STRAATT']['age_s'],0);self.assertTrue(.23<r.provenance['SC_ADYN']['age_s']<.25)
if __name__=='__main__':unittest.main(verbosity=2)
