"""Independent V37 manifest checks and synthetic admission tests."""
from dataclasses import replace
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
from time import monotonic
import resource
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from evaluation import shrinkage_unseen_gate_v37 as gate
from evaluation import causal_shrinkage_v35 as v35
from atmosphere.causal_density_correction import LogMedianCorrection

OUT=ROOT/'experiments/thermosphere_shrinkage_unseen_prereg_v37'
DAY=gate.SUMMER[0]
KEY='f'*64
OPERATIONS=dict(identity='METADATA',integration='CPU_SINGLE_MODEL',history='HISTORY_ONLY',
                poison='SYNTHETIC_POISON',score='FUTURE_ONCE',verify='READONLY_VERIFY')


def scenario(phase, day=DAY, **overrides):
    data=dict(approved={(day,phase)},
            predecessors=tuple(gate.StageReceipt(day,p,KEY,'PASS')
                        for p in gate.SEQUENCE[:gate.SEQUENCE.index(phase)]),
            evidence=dict.fromkeys(gate.REQUIREMENTS[phase],True),operation=OPERATIONS[phase])
    return data | overrides


class Admission(unittest.TestCase):
    def deny(self, phase, day=DAY, **kw):
        with self.assertRaises(ValueError):
            gate.admit(day,phase,**scenario(phase,day,**kw))

    def missing(self, phase, key):
        evidence=scenario(phase)['evidence']
        evidence[key]=False
        self.deny(phase,evidence=evidence)

    def test_registered_metadata_and_synthetic_score_positive(self):
        for phase in gate.SEQUENCE:
            self.assertTrue(gate.admit(DAY,phase,**scenario(phase)))

    def test_unregistered(self):
        self.deny('identity','2021-06-22')

    def test_used_date(self):
        self.deny('identity','2021-09-23')

    def test_fixed_lambdas(self):
        pin={'algo':KEY}
        gate.verify_pins(pin,pin,dict(v35.CANDIDATES))
        for value in (.4,.51,True):
            with self.assertRaises(ValueError):
                gate.verify_pins(pin,pin,dict(v35.CANDIDATES)|{'ShrinkageHalf':value})

    def test_algorithm_changed(self):
        with self.assertRaises(ValueError):
            gate.verify_pins({'algorithm':KEY},{'algorithm':'e'*64},dict(v35.CANDIDATES))

    def test_V36_changed(self):
        with self.assertRaises(ValueError):
            gate.verify_pins({'V36 metric':KEY},{'V36 metric':'e'*64},dict(v35.CANDIDATES))

    def test_V20_changed(self):
        with self.assertRaises(ValueError):
            gate.verify_pins({'V20 criterion':KEY},{'V20 criterion':'e'*64},dict(v35.CANDIDATES))

    def test_unapproved_seed(self):
        self.missing('integration','season_seed_approved')

    def test_GFZ_gap(self):
        self.missing('integration','GFZ_complete')

    def test_Swarm_unknown(self):
        self.missing('score','Swarm_identity')

    def test_require_pair(self):
        for pair in (gate.SUMMER,gate.WINTER):
            self.assertTrue(gate.paired_complete(pair,pair))
            self.assertFalse(gate.paired_complete(pair[:1],pair))
            self.assertFalse(gate.paired_complete((pair[0],pair[0]),pair))

    def test_winter_cannot_replace_summer(self):
        self.deny('integration', gate.WINTER[0])
        self.assertTrue(gate.admit(gate.WINTER[0],'identity',**scenario('identity',gate.WINTER[0])))

    def test_year_sequence(self):
        d=gate.SUMMER[1]
        self.deny('integration',d)
        positive=scenario('integration',d)
        positive['evidence']['same_season_2021_integration_verified']=True
        self.assertTrue(gate.admit(d,'integration',**positive))

    def test_early_read(self):
        self.deny('history',operation='FUTURE_ONCE')
        self.deny('score',predecessors=scenario('score')['predecessors'][:2])

    def test_missing_separate_auth(self):
        self.deny('score',approved={(DAY,'history')})

    def test_wrong_receipt_day(self):
        rec=list(scenario('score')['predecessors'])
        rec[2]=replace(rec[2],day=gate.SUMMER[1])
        self.deny('score',predecessors=rec)

    def test_poison(self):
        for key in ('poison_06Z_pass','poison_18Z_pass','history_06Z_frozen','history_18Z_frozen'):
            self.missing('score',key)

    def test_common_ID(self):
        self.missing('score','shared_ID_verified')
        self.missing('score','both_years_history_and_poison_verified')
        self.missing('score','pair_once_claim_verified')

    def test_extrapolation(self):
        self.missing('score','no_extrapolation')

    def test_low_N(self):
        self.assertEqual(gate.joint_support({'low':29,'mid':40,'high':70}),'N/A')
        self.assertEqual(gate.joint_support({'low':30,'mid':30,'high':30}),'SUPPORTED')

    def test_once(self):
        with tempfile.TemporaryDirectory(dir=OUT) as sandbox:
            root=Path(sandbox)
            (root/DAY).mkdir()
            gate.claim_score(root,DAY,**scenario('score'))
            with self.assertRaises(FileExistsError):
                gate.claim_score(root,DAY,**scenario('score'))

    def test_global_and_Raw_scalar_parity(self):
        baseline=np.array([1.0e-13,2e-13])
        for b in (-.154,.19,0.0):
            identity=v35.FrozenGlobal('2021-03-25',6,b,360,KEY,KEY,KEY)
            for name,lmb in v35.CANDIDATES.items():
                np.testing.assert_array_equal(LogMedianCorrection(lmb*b,360).apply(baseline),
                                              v35.coefficient(identity,lmb).apply(baseline))

    def test_datum_release_forbidden(self):
        self.deny('score',operation='DATUM_RELEASE')

    def test_gpu_auto_start_concurrency_forbidden(self):
        self.deny('integration',operation='GPU')
        self.deny('integration',operation='AUTOMATIC_MODEL_START')
        self.deny('integration',active_model=True)

    def test_metadata_path_cannot_decode(self):
        with patch.object(Path,'open',side_effect=AssertionError('unexpected read')):
            self.assertTrue(gate.admit(DAY,'identity',**scenario('identity')))
            self.deny('identity',operation='HISTORY_ONLY')
            self.deny('identity',operation='FUTURE_ONCE')


def main():
    started=monotonic()
    tests=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Admission))
    if not tests.wasSuccessful():
        raise SystemExit(1)
    asset=json.loads((OUT/'asset_audit.json').read_text())
    names=asset['historical_assets']
    for name,digest in names.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    assert [(x['date'],x['valid_Fobs'],x['valid_def_Kp'],len(x['Fobs_not_acquired']))
            for x in asset['dates']]==[
                (gate.SUMMER[0],99,168,0),(gate.SUMMER[1],31,0,70),
                (gate.WINTER[0],76,168,25),(gate.WINTER[1],16,0,85)]
    for row in asset['dates']:
        assert row['valid_Fobs']+len(row['Fobs_not_acquired'])+len(row['Fobs_invalid_or_conflict'])==101
        assert row['valid_def_Kp']+len(row['missing_or_invalid_Kp_UTC'])==168
        assert row['daily_center81_ready']==0 and row['observation']['status']=='NOT_ACQUIRED'
    # Recompute Fobs and definitive Kp support with a separate set-based reader.
    valid_daily, definitive = set(), set()
    for source in asset['driver_sources']:
        path = ROOT/source['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==source['SHA256']
        if source['index'].startswith('2021'):
            for line in path.read_text().splitlines():
                fields=line.split()
                if fields and fields[0]=='2021':
                    day=date(*map(int,fields[:3]))
                    if float(fields[25])>0:
                        valid_daily.add(day.isoformat())
                    if fields[27]=='2':
                        definitive.update(f'{day}T{3*i:02d}:00:00Z' for i,v in enumerate(fields[7:15])
                                          if 0<=float(v)<=9)
        else:
            document=json.loads(path.read_text())
            if source['index']=='Fobs':
                valid_daily.update(t[:10] for t,v in zip(document['datetime'],document['Fobs'])
                                   if np.isfinite(v) and v>0)
            else:
                definitive.update(t[:19]+'Z' for t,v,q in zip(document['datetime'],document['Kp'],document['status'])
                                  if q=='def' and 0<=v<=9)
    assert not asset['conflicts']
    for row in asset['dates']:
        q=row['support']
        span = [date.fromisoformat(q['solar_start'])+timedelta(days=i) for i in range(101)]
        missing={d.isoformat() for d in span}-valid_daily
        assert missing==set(row['Fobs_not_acquired'])|set(row['Fobs_invalid_or_conflict'])
        grid = [date.fromisoformat(q['raw_start'])+timedelta(days=i) for i in range(21)]
        assert {f'{day}T{h:02d}:00:00Z' for day in grid for h in range(0,24,3)}-definitive == set(row['missing_or_invalid_Kp_UTC'])
    assert not any(x['approved_for_summer_winter'] for x in asset['seeds'])
    assert all(asset[k]==0 for k in ('network_bytes','targets_decoded','model_runs','GPI_files_generated'))
    with (OUT/'independent_review.json').open('x') as f:
        json.dump(dict(verified=True,fixture_tests=tests.testsRun,failures=0,errors=0,
                       protected_SHA256_checks=len(names),driver_accounts=4, driver_source_SHA256_checks=len(asset['driver_sources']),
                       target_density_decodes=0,wall_seconds=monotonic()-started,
                       peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),f,indent=2)
        f.write('\n')


if __name__=='__main__':
    main()
