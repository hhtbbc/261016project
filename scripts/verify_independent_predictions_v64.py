"""Fresh-process verification against locks, indexed identities, and saved bytes."""
import json
from collections import defaultdict

import numpy as np

from run_independent_predictions_v64 import (OUT,V63,METHODS,SHAPE,key,need,read_csv,sha)


def verify():
    lock=json.loads((OUT/'prediction_lock.json').read_text())
    for name,checksum in lock['artifact_SHA256'].items():
        need(sha(OUT/name)==checksum,f'Artifact changed: {name}')
    targets=read_csv(V63/'target_record_index.csv')
    labels={r['record_id']:r for r in targets}
    target_keys={key(r):r for r in targets}
    need(len(labels)==len(target_keys)==21,'Target identity')
    phase=json.loads((OUT/'phase_1_authorization.json').read_text())
    need(sha(V63/'target_record_index.csv')==phase['index_SHA256']['target'],'Target index changed')
    plans=[('approved_history_manifest.csv','history_record_index.csv','history','anchors.txt'),
           ('approved_periodic_history_manifest.csv','optional_periodic_history_index.csv','periodic','daily.bin')]
    accesses={}
    ordered=sorted(lock['cutoff_locks'].values(),key=lambda r:r['file'])
    cutoff_order={}
    cutoff_rows=[]
    for i,entry in enumerate(ordered):
        path=OUT/entry['file']
        need(sha(path)==entry['SHA256'],'Per-cutoff lock changed')
        x=json.loads(path.read_text())
        cutoff_order[x['cutoff']]=(i,x['access_through'],entry['SHA256'])
        cutoff_rows.extend(x['predictions'])
    need(len(cutoff_order)==7,'Cutoff count')
    for manifest,index,kind,filename in plans:
        rows=read_csv(OUT/manifest)
        originals=read_csv(V63/index)
        need(len(rows)==len(originals)==21 and sha(V63/index)==phase['index_SHA256'][kind],
             'History index changed')
        approved={r['record_id']:r for r in originals}
        for r in rows:
            a=approved.pop(r['record_id'])
            need(all(r[k]==v for k,v in a.items()),'History identity drift')
            i,end,_=cutoff_order[r['cutoff_id']]
            n=int(r['sequence'])
            offset=n-(end-6)-(0 if kind=='history' else 3)-1
            need(0<=offset<3 and n not in accesses,'History order changed')
            path=OUT/f'data_local/history_{i:02}/{filename}'
            with path.open('rb') as f:
                size=int(np.prod(SHAPE))*8
                f.seek(offset*size)
                from hashlib import sha256
                need(sha256(f.read(size)).hexdigest()==r['converted_slice_SHA256'],'History slice changed')
            accesses[n]=r
        need(not approved,'Missing authorized history')
    need(set(accesses)==set(range(1,43)),'History access count')
    actual=[]
    for n,r in sorted(accesses.items()):
        t=target_keys.get(key(r))
        if t:
            i,end,checksum=cutoff_order[t['cutoff_id']]
            need(end<n and i<cutoff_order[r['cutoff_id']][0] and r['stage']=='periodic','Overlap order')
            actual.append((n,checksum,t['record_id']))
    audit=json.loads((OUT/'temporal_overlap_audit.json').read_text())
    need(actual==[(r['access_sequence'],r['earlier_lock_SHA256'],r['earlier_record_id'])
                 for r in audit['overlaps']],'Overlap ledger')
    counts=defaultdict(lambda:dict(fields=0,grid=0,nonpositive=0,nonfinite=0))
    seen=set()
    rows=read_csv(OUT/'prediction_manifest.csv')
    need([{k:str(v) for k,v in r.items()} for r in cutoff_rows]==rows,'Cutoff locks and manifest differ')
    for r in rows:
        t=labels[r['record_id']]
        need(all(r[k]==t[k] for k in ('event_id','cutoff_id','cutoff_UTC','lead_hours'))
             and r['target_UTC']==t['UTC'],'Forecast/label index mismatch')
        pair=(r['record_id'],r['method'])
        need(pair not in seen,'Duplicate forecast')
        seen.add(pair)
        file=OUT/r['file']
        need(file.resolve()==file and file.stat().st_mode&0o777==0o444 and sha(file)==r['SHA256'],
             'Forecast bytes drift')
        a=np.fromfile(file,dtype='<f8')
        count=counts[r['method']]
        finite=np.isfinite(a)
        for name,n in [('grid',a.size),('nonpositive',int((finite&(a<=0)).sum())),
                       ('nonfinite',int((~finite).sum()))]:
            expect=int(r['n' if name=='grid' else name])
            need(n==expect,'Coverage disagreement')
            count[name]+=n
        count['fields']+=1
    need(seen=={(label,method) for label in labels for method in METHODS},'Incomplete forecast matrix')
    for c in counts.values():
        c['coverage']=1-(c['nonpositive']+c['nonfinite'])/c['grid']
    return dict(prediction_lock_SHA256=sha(OUT/'prediction_lock.json'),cutoffs=len(cutoff_order),
                forecasts=len(seen),history_associations=len(accesses),historical_overlaps=len(actual),
                target_scoring_reads=0,methods=counts)


if __name__=='__main__':
    print(json.dumps(verify(),indent=2))
