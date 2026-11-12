"""Recordwise acceptance for all periods; reuse frozen 2021 arithmetic."""
from pathlib import Path
import sys,json,time,resource
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import compare_tiegcm_2021_initial_conditions as h
from audit_tiegcm_2021_14day_acceptance import index,record
TAG='tiegcm_2022_dual_initial_spinup_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG;A=ROOT/'experiments/tiegcm_training_mar23_v2_2022_longrun'

def main():
    started=time.perf_counter();ai=index(A);bi=index(F);rules=json.loads((F/'frozen_comparison_rules.json').read_text());acc={};small=[];globalhour=[]
    for t in range(82*86400,84*86400+1,3600):
        a=record(*ai[t]);b=record(*bi[t]);lat=a['lat'];regions={k:(lat>=v[0])&(lat<=v[1]) for k,v in rules['latitude_regions'].items()}
        regions.update(low=abs(lat)<30,mid=(abs(lat)>=30)&(abs(lat)<60),high=abs(lat)>=60)
        periods=['candidate']+(['last24h'] if t>=83*86400 else [])+(['endpoint'] if t==84*86400 else [])
        fields={k:(b[k],a[k],.05,True,1e-8 if k in ['O1','O2','N2','HE'] else 0) for k in ['DEN','O1','O2','N2','HE']}
        fields['TN']=(b['TN'],a['TN'],10,False,0);wind=np.hypot(b['UN']-a['UN'],b['VN']-a['VN']);fields['WIND_VECTOR']=(wind,np.zeros_like(wind),20,False,0)
        for height in rules['common_native_ZG_heights_km']:
            x=h.legacy.a3.at_height(b['ZG'],b['DEN'],height*1000);y=h.legacy.a3.at_height(a['ZG'],a['DEN'],height*1000);fields[f'ZG_{height}km']=(x[None],y[None],.05,True,0)
        for k,(x,y,limit,relative,floor) in fields.items():
            good=np.isfinite(x)&np.isfinite(y);e=abs(x-y)
            if relative:good&=abs(y)>floor;e=np.divide(e,abs(y),out=np.full_like(e,np.nan),where=good)
            for region,sel in regions.items():
                g=good[:,sel,:];n=g.sum(axis=(1,2));fraction=np.divide(((e[:,sel,:]<limit)&g).sum(axis=(1,2)),n,out=np.full(n.shape,np.nan),where=n>0)
                for lev in range(len(n)):
                    for period in periods:
                        key=(k,period,region,lev);v=acc.setdefault(key,dict(evaluated_hours=0,failed_hours=0,missing_hours=0,minimum_fraction=1.,maximum_fraction=0.,coverage_min=1.,coverage_max=0.))
                        cov=float(n[lev]/g.shape[1]/g.shape[2]);v['coverage_min']=min(v['coverage_min'],cov);v['coverage_max']=max(v['coverage_max'],cov)
                        if not n[lev]:v['missing_hours']+=1;continue
                        f=float(fraction[lev]);v['evaluated_hours']+=1;v['failed_hours']+=int(f<.95);v['minimum_fraction']=min(v['minimum_fraction'],f);v['maximum_fraction']=max(v['maximum_fraction'],f)
        # Numerical-small diagnostics only; never alters relative-error acceptance mask/floor.
        y=a['N2'];x=b['N2'];good=np.isfinite(x)&np.isfinite(y)
        for label,mask in [('all',good),('near_small_le_1e-5',good&(y<=1e-5)),('above_1e-5',good&(y>1e-5))]:
            if not mask.any():continue
            xx=x[mask];yy=y[mask];delta=xx-yy
            small.append(dict(time_doy_seconds=t,subset=label,n=len(xx),reference_min=float(yy.min()),reference_max=float(yy.max()),max_abs=float(abs(delta).max()),RMSE=float(np.sqrt(np.mean(delta**2))),relative_P95=float(np.percentile(abs(delta/yy),95)),floor_unchanged=1e-8,small_documented=1e-6))
    rows=[dict(variable=k[0],period=k[1],region=k[2],level=k[3],**v,PASS=v['evaluated_hours']>0 and v['failed_hours']==0) for k,v in acc.items()]
    h.csvout(O/'acceptance_region_level_matrix.csv',rows);h.csvout(O/'N2_small_diagnostics.csv',small)
    summary={}
    for period in ['candidate','last24h','endpoint']:
        summary[period]={}
        for name in sorted({r['variable'] for r in rows}):
            rr=[r for r in rows if r['period']==period and r['variable']==name and r['evaluated_hours']>0 and r['region'] in rules['latitude_regions']]
            summary[period][name]=dict(evaluated_cells=sum(r['evaluated_hours'] for r in rr),failed_cells=sum(r['failed_hours'] for r in rr),worst_fraction=min(r['minimum_fraction'] for r in rr),PASS=all(r['PASS'] for r in rr))
    legacy=json.loads((O/'comparison/summary.json').read_text())
    for k,v in legacy['strict_last24h_native_gates'].items():assert v['failed_cells']==summary['last24h'][k]['failed_cells']
    for k,v in legacy['strict_last24h_height_gates'].items():assert v['failed_cells']==summary['last24h']['ZG_'+k+'km']['failed_cells']
    with (O/'acceptance_by_period.json').open('x') as f:json.dump(summary,f,indent=2)
    with (F/'acceptance_runtime.json').open('x') as f:json.dump(dict(wall_s=time.perf_counter()-started,peak_RSS_MiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,last24h_gate_counts_independently_match=True),f,indent=2)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
