"""Independent paired metric recomputation and bounded derived summaries."""
from pathlib import Path
import csv,json,sys,time,resource,zipfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import prepare_fourcastden_swarm_observation_v1 as task
from analyze_fourcastden_swarm_observation_v1 import table,MAPS,MODELS,FIELDS
F,O,D=task.F,task.O,task.D


def main():
    begin=time.perf_counter();metrics=list(csv.DictReader((O/'metrics.csv').open()));checks=[];summary=[]
    for day in ('2023-01-04','2023-03-24'):
        with np.load(O/(day+'_aligned_local.npz'),allow_pickle=False) as n:
            values=n['predictions'];valid=n['valid'];obs=n['observed'];h=n['hours'];good=n['quality'];co=n['coordinates']
        common=good&np.logical_and.reduce(valid[:2].reshape(-1,len(obs)),axis=0)
        for r in metrics:
            if r['date']!=day:continue
            mi=MAPS.index(r['mapping']);idx=MODELS.index(r['model']);a,b=1+2*idx,2+2*idx
            pm={'pre':(h>=1)&(h<7),'post':(h>=8)&(h<=13),'transition':(h>7)&(h<8),'all_forecast':(h>=1)&(h<=13)&(h!=7)}[r['period']]
            la=co[:,0,0];rm={'global':np.ones(len(h),bool),'south':la<=-60,'north':la>=60,'midlow':abs(la)<60}[r['region']]
            mask=pm&rm&good&valid[mi,0]&valid[mi,a]&valid[mi,b]
            if r['domain']=='common_AB_all_models':mask&=common
            fi={'Reference':0,'Open':a,'Updated':b}[r['scheme']];p=values[mi,fi,mask];o=obs[mask]
            assert len(p)==int(r['n'])
            if len(p):
                e=p-o;v=dict(RMSE=np.linalg.norm(e)/np.sqrt(len(e)),MAE=np.add.reduce(abs(e))/len(e),bias=np.add.reduce(e)/len(e),
                    relative_RMS=np.linalg.norm(e/o)/np.sqrt(len(e)),relative_P95=np.quantile(abs(e/o),.95),
                    log_RMS=np.linalg.norm(np.log(p)-np.log(o))/np.sqrt(len(e)),max_abs=abs(e).max())
                for k,x in v.items():np.testing.assert_allclose(x,float(r[k]),rtol=3e-12,atol=1e-25 if k in ('RMSE','MAE','bias','max_abs') else 1e-14)
            checks.append(dict(date=day,mapping=r['mapping'],model=r['model'],scheme=r['scheme'],period=r['period'],region=r['region'],domain=r['domain'],n=len(p),all_metrics_PASS=True))
        cm=good&valid[:,0].all(axis=0)
        sens={key:np.full(len(h),np.nan) for key in ['combined','latitude_only','height_only','interaction']}
        aa,bb,dd,ee=values[:,0]
        sens.update(combined=bb/aa-1,latitude_only=dd/aa-1,height_only=ee/aa-1,interaction=(bb-dd-ee+aa)/aa)
        for period,pm in [('all',np.ones(len(h),bool)),('post',(h>=8)&(h<=13))]:
            for region,rm in [('global',np.ones(len(h),bool)),('south',co[:,0,0]<=-60),('north',co[:,0,0]>=60),('midlow',abs(co[:,0,0])<60)]:
                mask=cm&pm&rm
                for name,x in sens.items():
                    x=x[mask];summary.append(dict(date=day,period=period,region=region,metric=name,n=len(x),minimum=float(x.min()),maximum=float(x.max()),
                        absolute_relative_P95=float(np.quantile(abs(x),.95)),mean=float(x.mean())))
    table(O/'independent_metric_checks.csv',checks);table(O/'coordinate_sensitivity_summary.csv',summary)
    post=[r for r in metrics if r['period']=='post' and r['region']=='global' and r['mapping'] in ('A','B') and r['domain']=='common_AB_all_models']
    table(O/'post_global_all_metrics.csv',post)
    interpolation=list(csv.DictReader((O/'interpolation_sensitivity_local.csv').open()));ints=[]
    fields=['time_log_vs_linear_relative','horizontal_log_vs_linear_relative','vertical_linear_vs_log_relative','vertical_coarsened_log_relative','height_plus_1km_relative','height_minus_1km_relative']
    for day in ('2023-01-04','2023-03-24'):
        for name in fields:
            v=np.array([float(r[name]) for r in interpolation if r['date']==day and r[name]!=''])
            ints.append(dict(date=day,metric=name,n=len(v),minimum=float(v.min()),maximum=float(v.max()),absolute_P95=float(np.quantile(abs(v),.95))))
    table(O/'interpolation_sensitivity_summary.csv',ints)
    manifest=json.loads((F/'download_manifest.json').read_text())
    for item in manifest:
        assert task.sha(ROOT/item['path'])==item['SHA256']
        with zipfile.ZipFile(ROOT/item['path']) as z:
            assert z.testzip() is None
            for member in item['members']:
                p=ROOT/member['path'];assert task.sha(p)==member['SHA256'];assert p.read_bytes()==z.read(p.name)
    protected=json.loads((F/'protected.json').read_text());assert all(task.sha(ROOT/p)==h for p,h in protected.items())
    # Historic manifest excludes live STATUS/WORKLOG, retains all old datasets.
    old=json.loads((ROOT/'experiments/tiegcm_runtime_restart_audit_v1/protected_files.json').read_text())
    changed=[p for p,h in old.items() if task.sha(ROOT/p)!=h];assert not changed
    task.dump(F/'independent_validation.json',dict(metric_rows_verified=len(checks),scalar_metrics_verified=sum(7 for r in checks if r['n']),
        task_assets_SHA_unchanged=len(protected),historical_assets_SHA_unchanged=len(old),changed=changed,
        new_forward=0,new_TIE=0,new_orbit=0,independent_wall_s=time.perf_counter()-begin,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))
    print((F/'independent_validation.json').read_text())


if __name__=='__main__':main()
