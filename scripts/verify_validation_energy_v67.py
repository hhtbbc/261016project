"""Cross-check decomposition against separately measured verified prediction errors."""
import math
import json

from evaluate_matched_validation_v67 import OUT,LOCAL,sha,read_csv,save,need


def main():
    index={}
    files=('global_metrics.csv','cutoff_metrics.csv','layer_metrics.csv','regional_metrics.csv')
    for name in files:
        for r in read_csv(OUT/name):
            if r['mask']=='common' and r['log_rmse']:
                index[tuple(r[k] for k in ('group_key','group','lead','domain','method'))]=float(r['log_rmse'])
    rows=read_csv(OUT/'residual_energy_decomposition.csv')
    err=0.
    for r in rows:
        k=tuple(r[n] for n in ('group_key','group','lead','domain'))
        base='Persistence' if r['arm']=='P' else 'LocalTimePersistence'
        cnn=r['arm']+'-Residual-CNN'
        gain=index[(*k,base)]**2-index[(*k,cnn)]**2
        result=float(r['twice_cross'])-float(r['correction_energy'])
        error=abs(gain-result)
        need(math.isclose(gain,result,abs_tol=1e-15,rel_tol=1e-11),'Independent energy gain')
        err=max(err,error)
    locked=json.loads((OUT/'prediction_lock.json').read_text())
    for n,h in locked['cutoffs'].items():
        need(sha(LOCAL/n)==h,'Sealed cutoff')
    need(len(rows)==1188,'Expected empirical energy rows')
    save(OUT/'independent_energy_verification.json',dict(checked=len(rows),max_absolute_disagreement=err,
         compared='independently exported forecast log RMSE difference of squares vs cross-term minus energy',
         future_DEN_source_reads=0))
    print(len(rows),err)


if __name__=='__main__':
    main()
