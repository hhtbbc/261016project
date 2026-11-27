"""Isolate a synthetic prediction process from evaluator-only future labels."""
import argparse
from datetime import timedelta
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import build_non_target_horizon_index_v56 as idx
from runtime.tiegcm_rank_exit import write_once

STORE=idx.OUT/'isolation_local'
UNITS='kg/m3'


class History:
    def __init__(self,path,digest,cutoff,split):
        if path.resolve()!=path or not path.is_relative_to(STORE) or path.name!='history.json':
            raise ValueError('Predictor only accepts an explicit history snapshot')
        blob=path.read_bytes()
        if hashlib.sha256(blob).hexdigest()!=digest:
            raise ValueError('History identity mismatch')
        obj=json.loads(blob)
        self.t=idx.utc(cutoff)
        self.begin=self.t-3*idx.HOUR
        self.access=[]
        if set(obj)!={'role','cutoff','split','source','rows'} or obj['role']!='SYNTHETIC_HISTORY_ONLY' or (
                obj['cutoff'],obj['split'])!=(cutoff,split):
            raise ValueError('Wrong or mixed history-snapshot identity')
        self.data={}
        for row in obj['rows']:
            if set(row)!={'UTC','density_kg_m3'}:
                raise ValueError('Unrecognized field in history-only snapshot')
            t=idx.utc(row['UTC'])
            if not self.begin<=t<self.t or t in self.data:
                raise ValueError('Future or duplicate timestamp in history-only snapshot')
            value=row['density_kg_m3']
            if not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
                raise ValueError('Invalid synthetic history')
            self.data[t]=value
        if set(self.data)!={self.begin+n*idx.HOUR for n in range(3)}:
            raise ValueError('History not the exact hourly grid')

    def feature(self,kind,timestamps):
        requested=tuple(idx.utc(t) for t in timestamps)
        explanation=None
        if kind not in ('density_history','history_normalization','trailing_mean','lag'):
            explanation='Feature type prohibited, including opaque statistics and future drivers'
        elif not requested or any(not self.begin<=t<self.t for t in requested):
            explanation='Timestamp outside half-open history'
        elif any(q not in self.data for q in requested):
            explanation='Required frame absent'
        self.access.append(dict(feature=kind,UTC=[idx.iso(t) for t in requested],allowed=explanation is None))
        if explanation:
            raise ValueError(explanation)
        return [self.data[q] for q in requested]


def worker(path,digest,cutoff,split):
    history=History(path,digest,cutoff,split)
    ticks=[idx.iso(history.begin+n*idx.HOUR) for n in range(3)]
    values=history.feature('density_history',ticks)
    train=history.feature('history_normalization',ticks)
    mean=sum(train)/len(train)
    scale=math.sqrt(sum((v-mean)**2 for v in train)/len(train))
    x2,x3=values[-2:]
    predictions=[dict(lead=h,Persistence=x3,TwoFrameLinear=x3+(h+1)*(x3-x2)) for h in (1,3,6)]
    return dict(input_sha256=digest,normalization={'mean':mean,'scale':scale,'unit':UNITS},
                predictions=predictions,access_log=history.access)


def invoke(path,digest,cutoff,split):
    command=[sys.executable,'-B',__file__,'--predict-history',str(path),digest,cutoff,split]
    return json.loads(subprocess.check_output(command,cwd=idx.ROOT))


def value(t):
    return 1e-12*(2+.15*math.sin(t.hour*math.pi/12)+.004*t.hour*t.hour+.02*t.day)


def rejects(path,digest,cutoff,split):
    h=History(path,digest,cutoff,split)
    early=idx.iso(h.begin)
    late=idx.iso(h.t+idx.HOUR)
    operations=[
        ('full_sequence_normalization',lambda:h.feature('history_normalization',[early,late])),
        ('future_centered_rolling_mean',lambda:h.feature('trailing_mean',[early,cutoff,late])),
        ('lag_sign_error',lambda:h.feature('lag',[late])),
        ('target_time_driver',lambda:h.feature('future_driver',[late])),
        ('all_data_prefit_stats',lambda:h.feature('opaque_prefit_stats',[early])),
        ('window_crosses_cutoff',lambda:h.feature('density_history',[early,cutoff])),
        ('metadata_density_call',lambda:h.feature('density_orbitmean',[early])),
        ('outside_history_before_start',lambda:h.feature('lag',[idx.iso(h.begin-idx.HOUR)])),
        ('missing_half_hour',lambda:h.feature('lag',[idx.iso(h.begin+timedelta(minutes=30))])),
        ('cross_split_support',lambda:idx.check_split([('A',early,late),('B',cutoff,late)])),
        ('mixed_split_snapshot',lambda:History(path,digest,cutoff,split+'-other')),
        ('wrong_snapshot_hash',lambda:History(path,'0'*64,cutoff,split)),
        ('future_path',lambda:History(path.parent/'future.json',digest,cutoff,split))]
    out=[]
    for name,call in operations:
        try:
            call()
        except ValueError as e:
            out.append(dict(negative=name,error=str(e)))
        else:
            raise AssertionError(f'Negative case was admitted: {name}')
    return out,h.access


def main():
    from csv import DictReader
    protocol=idx.pin(idx.V37)
    core=protocol['V20_core']
    assert core['history_hours']==3 and core['future_hours']==[1,3,6]
    with (idx.OUT/'horizon_index.csv').open() as f:
        rows=list(DictReader(f))
    if STORE.resolve()!=STORE:
        raise ValueError('Unsafe local fixture location')
    STORE.mkdir()
    observations=[]
    proofs=[]
    groups={}
    for r in rows:
        groups.setdefault((r['source_identity'],r['cutoff_UTC'],r['split_identity']),[]).append(r)
    for i,((source,cutoff,split),samples) in enumerate(groups.items()):
        t=idx.utc(cutoff)
        local=STORE/f'cutoff_{i:02d}';local.mkdir()
        history=local/'history.json'
        target=local/'future.json'
        ticks=[t+idx.HOUR*j for j in range(-3,0)]
        write_once(history,dict(role='SYNTHETIC_HISTORY_ONLY',cutoff=cutoff,split=split,source=source,
            rows=[dict(UTC=idx.iso(u),density_kg_m3=value(u)) for u in ticks]))
        future=[dict(UTC=idx.iso(t+idx.HOUR*j),density_kg_m3=value(t+idx.HOUR*j)) for j in range(7)]
        write_once(target,dict(scope='SYNTHETIC_EVALUATOR_ONLY',rows=future))
        original=idx.sha(target)
        h=idx.sha(history)
        one=invoke(history,h,cutoff,split)
        # The evaluator owns both files. Neither path enters the predictor command or history snapshot.
        poisoned=local/'poisoned_future.json'
        write_once(poisoned,dict(scope='SYNTHETIC_EVALUATOR_ONLY',
             rows=[x|{'density_kg_m3':x['density_kg_m3']*1e20} for x in future]))
        # Change the actual evaluator future at its stable path, retaining both originals for audit.
        preserved=local/'baseline_future.json'
        target.rename(preserved)
        poisoned.rename(target)
        two=invoke(history,h,cutoff,split)
        assert one==two and h==idx.sha(history) and original!=idx.sha(target)
        assert all(idx.utc(q)<t and x['allowed'] for x in one['access_log'] for q in x['UTC'])
        bad,trace=rejects(history,h,cutoff,split)
        proofs.append(dict(source=source,cutoff_UTC=cutoff,history_SHA=h,split_identity=split,
             future_original_SHA=original,future_poisoned_SHA=idx.sha(target),poison_multiplier=1e20,
             causal_input_and_output_bitwise_equal=(json.dumps(one)==json.dumps(two)),
             predictor=one,negative_cases=bad,denial_trace=trace))
        bylead={x['lead']:x for x in one['predictions']}
        for r in samples:
            j=int(r['horizon_hours'])
            for name in ('Persistence','TwoFrameLinear'):
                observations.append(dict(sample_id=r['sample_id'],cutoff_UTC=cutoff,horizon_hours=j,method=name,
                    truth_kg_m3=future[j]['density_kg_m3'],prediction_kg_m3=bylead[j][name],scope='SYNTHETIC_ONLY'))
    idx.output('synthetic_baseline_pairs.csv',observations)
    summary=[]
    for cutoff in (6,18):
        for lead in (1,3,6):
            for method in ('Persistence','TwoFrameLinear'):
                selected=[x for x in observations if idx.utc(x['cutoff_UTC']).hour==cutoff and x['horizon_hours']==lead and x['method']==method]
                errors=[x['prediction_kg_m3']-x['truth_kg_m3'] for x in selected]
                n=len(errors)
                summary.append(dict(cutoff_UTC_hour=cutoff,horizon_hours=lead,method=method,n=n,
                    MAE_kg_m3=sum(map(abs,errors))/n,RMSE_kg_m3=math.sqrt(sum(e*e for e in errors)/n),
                    Bias_kg_m3=sum(errors)/n,relative_RMSE=math.sqrt(sum((e/x['truth_kg_m3'])**2
                       for e,x in zip(errors,selected))/n),scope='SYNTHETIC_DIAGNOSTIC_NOT_V37_SCORE'))
    idx.output('synthetic_baseline_metrics.csv',summary)
    write_once(idx.OUT/'isolation_results.json',dict(cutoffs=len(proofs),negative_rejections=sum(len(p['negative_cases']) for p in proofs),
        identical_under_future_poison=True,predictor_processes=2*len(proofs),actual_Swarm_density_reads=0,
        guarantees='Trusted predictor contract and separate files; not an OS sandbox for untrusted arbitrary Python',
        evidence=proofs))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--predict-history',nargs=4)
    args=p.parse_args()
    if args.predict_history:
        path,digest,cutoff,split=args.predict_history
        print(json.dumps(worker(Path(path),digest,cutoff,split),allow_nan=False,sort_keys=True))
    else:
        main()
