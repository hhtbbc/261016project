"""Independent end-of-task hash, interpolation, observation and resource checks."""
from pathlib import Path
import sys,json,csv,hashlib,re
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from prepare_fourcastden_swarm_observation_v1 import sha,dump
from audit_tiegcm_2021_14day_acceptance import index,record
from PIL import Image
TAG='tiegcm_2022_dual_initial_spinup_v1';F=ROOT/'experiments'/TAG;O=ROOT/'results'/TAG

def main():
    assert json.loads((F/'offline_status.json').read_text())['PASS']
    status=json.loads((F/'run_status.json').read_text());assert status['returncode']==0 and status['normal_exit_count']==4 and status['stop_reason'] is None
    launch=json.loads((F/'launch_once.json').read_text());assert launch['model_launches']==1 and launch['no_retry']
    protected=json.loads((F/'protected_files.json').read_text())
    for p,h in protected.items():assert sha(ROOT/p)==h,p
    audit=json.loads((F/'data_audit.json').read_text());assert audit['model_steps']==12960 and audit['primary_records']==10 and audit['secondary_records']==216
    for e in audit['files']:assert sha(F/e['file'])==e['SHA256']
    old=ROOT/'experiments/tiegcm_training_mar23_v2_2022_longrun';ia,ib=index(old),index(F);xs=[];ys=[];weights=[];interpchecks=[]
    for t in range(82*86400,84*86400+1,3600):
        a,b=record(*ia[t]),record(*ib[t]);x=[];y=[];w=[]
        for j,lat in enumerate(a['lat']):
            for k in range(a['DEN'].shape[-1]):
                za,zb=a['ZG'][:,j,k],b['ZG'][:,j,k]
                if za[0]<=450e3<=za[-1] and zb[0]<=450e3<=zb[-1]:
                    aa=float(np.exp(np.interp(450e3,za,np.log(a['DEN'][:,j,k]))));bb=float(np.exp(np.interp(450e3,zb,np.log(b['DEN'][:,j,k]))));x.append(aa);y.append(bb);w.append(np.cos(np.deg2rad(lat)))
        xs.extend(x);ys.extend(y);weights.extend(w)
    x,y,w=np.array(xs),np.array(ys),np.array(weights);rel=abs(y/x-1);order=np.argsort(rel);c=np.cumsum(w[order]);p95=float(np.interp(.95,c/c[-1],rel[order]));rmse=float(np.sqrt(np.sum(w*(y-x)**2)/w.sum()))
    rows=list(csv.DictReader((O/'comparison/native_ZG_density.csv').open()));r=next(r for r in rows if r['height_km']=='450' and r['period']=='candidate' and r['region']=='global')
    assert np.isclose(p95,float(r['relative_P95']),rtol=1e-12,atol=1e-15) and np.isclose(rmse,float(r['RMSE']),rtol=1e-12,atol=0)
    z=np.load(O/'observation/aligned_local.npz');vals=z['values'];obs=z['observed'];common=z['common']
    assert np.array_equal(common,z['quality']&np.isfinite(vals).all(axis=(0,1))&(vals>0).all(axis=(0,1)))
    rows=list(csv.DictReader((O/'observation/metrics.csv').open()))
    for ma in 'ABDE':
        for gi,g in enumerate(['A7','B7']):
            q=vals['ABDE'.index(ma),gi,common];o=obs[common];d=q-o;r=next(r for r in rows if r['mapping']==ma and r['group']==g and r['region']=='all')
            for name,v in [('RMSE',np.linalg.norm(d)/np.sqrt(len(d))),('MAE',abs(d).mean()),('bias',d.mean()),('relative_RMS',np.linalg.norm(d/o)/np.sqrt(len(d))),('relative_bias',np.mean(d/o))]:assert np.isclose(v,float(r[name]),rtol=1e-12,atol=0)
    log=ROOT/'logs'/f'{TAG}.log';suspicious=re.findall(r'(?im)^.*(?:WARNING|ERROR|\bNaN\b|\bInf\b|MPI_ABORT).*$',log.read_text());assert not suspicious,suspicious[:3]
    figures=sorted(O.rglob('*.png'))
    for p in figures:
        with Image.open(p) as im:im.verify()
    generated=sum(p.stat().st_size for d in [F,O] for p in d.rglob('*') if p.is_file())+sum(p.stat().st_size for p in (ROOT/'logs').glob('*2022*dual*log'))
    assert generated<5*2**30 and max(p.stat().st_size for p in F.glob('*.nc'))<256*2**20
    result=dict(PASS=True,protected_assets_unchanged=len(protected),new_NetCDF_SHA_verified=len(audit['files']),model_launches=1,independent_column_interpolation_weighted_450_P95=p95,independent_weighted_450_RMSE=rmse,observation_metric_sets_independently_recomputed=8,figures_verified=len(figures),log_WARNING_ERROR_NaN_Inf_count=len(suspicious),total_generated_bytes=generated,source_SHA_after=sha(ROOT/'data/raw/tiegcm_2021_spinup_initial_condition_v1/tiegcm_res5.0_mareqx_smax_prim.nc'),stdout_SHA256=sha(log),scientific_training_ready=False,formal_real_orbit='BLOCKED')
    dump(F/'delivery_audit.json',result)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
