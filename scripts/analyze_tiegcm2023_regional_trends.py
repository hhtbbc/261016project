"""Additional offline regional/level trends; descriptive OLS, not new simulation."""
from pathlib import Path
import importlib.util,json
import numpy as np
from scipy.stats import linregress
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('comp',ROOT/'scripts/compare_tiegcm2023_s3_s7.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

def main():
    out=ROOT/'experiments/tiegcm2023_s3_s7_comparison_v1';dest=out/'regional_trend_audit.json'
    if dest.exists():raise FileExistsError(dest)
    x,t,g,_=c.load_common(c.S3);y,ty,gy,_=c.load_common(c.S7);assert np.array_equal(t,ty)
    rules=json.loads((c.S7/'frozen_comparison_rules.json').read_text());lat=g['lat'];weights=np.broadcast_to(np.cos(np.deg2rad(lat))[:,None],(36,72));regions={k:(lat>=lo)&(lat<hi) for k,(lo,hi) in rules['latitude_regions'].items()};hours=(t-80*86400)/3600;rows=[]
    def fit_series(v,meta):
        for label,selection in [('full48h',hours<=48),('last24h',(hours>=24)&(hours<=48))]:
            sel=selection&np.isfinite(v)
            if sel.sum()<2:continue
            fit=linregress(hours[sel],v[sel]);slope=float(fit.slope);std=float(fit.stderr)
            rows.append({**meta,'period':label,'first_RMSE':float(v[sel][0]),'last_RMSE':float(v[sel][-1]),'slope_per_hour':slope,'slope_standard_error_OLS':std,'net_growth':bool(v[sel][-1]>v[sel][0]),'positive_slope':bool(slope>0),'OLS_pvalue_descriptive':float(fit.pvalue) if np.isfinite(fit.pvalue) else None})
    for name in ['DEN','TN','UN','VN','WIND_VECTOR','O1','O2','N2','HE']:
        if name=='WIND_VECTOR':err2=(x['UN']-y['UN'])**2+(x['VN']-y['VN'])**2;metric='vector_RMSE_m_s'
        elif name=='DEN':err2=np.log(x[name]/y[name])**2;metric='log_density_RMSE'
        elif name in ['O1','O2','N2','HE']:
            valid=abs(y[name])>1e-8;d=np.divide(x[name]-y[name],y[name],out=np.full_like(y[name],np.nan),where=valid);err2=d**2;metric='relative_RMSE'
        else:err2=(x[name]-y[name])**2;metric='RMSE_K' if name=='TN' else 'RMSE_m_s'
        for region,mask in regions.items():
            e=err2[:,:,mask,:];w=weights[mask,:][None,None];valid=np.isfinite(e);num=np.nansum(e*w,axis=(2,3));den=(valid*w).sum(axis=(2,3));rmse=np.sqrt(np.divide(num,den,out=np.full_like(num,np.nan),where=den>0))
            for lev in range(e.shape[1]):fit_series(rmse[:,lev],{'domain':'pressure','variable':name,'level':float(g['ilev' if name=='DEN' else 'lev'][lev]),'region':region,'metric':metric})
        print('Regional trends:',name,flush=True)
    for h in rules['common_native_ZG_heights_km']:
        xx=np.stack([c.a3.at_height(x['ZG'][i],x['DEN'][i],h*1000) for i in range(290)]);yy=np.stack([c.a3.at_height(y['ZG'][i],y['DEN'][i],h*1000) for i in range(290)])
        err2=np.log(xx/yy)**2
        for region,mask in regions.items():
            e=err2[:,mask,:];w=weights[mask,:];v=np.isfinite(e);rmse=np.sqrt(np.nansum(e*w,axis=(1,2))/(v*w).sum(axis=(1,2)));fit_series(rmse,{'domain':'native_ZG_height','variable':'DEN','level':h,'region':region,'metric':'log_density_RMSE'})
    c.dumpcsv(ROOT/'results/metrics/tiegcm2023_s3_s7_comparison_v1_regional_trends.csv',rows)
    growth=[r for r in rows if r['positive_slope'] and r['net_growth']]
    result={'rows':len(rows),'positive_slope_and_net_growth_groups':len(growth),'native_height_growth_groups':[r for r in growth if r['domain']=='native_ZG_height'],'pressure_growth_groups':growth,'note':'All OLS inference descriptive; time series autocorrelated. Variables have different units and trends must not be ranked by raw slope across units. No new model integrations.'}
    dest.write_text(json.dumps(result,indent=2)+'\n');print('Trend rows:',len(rows),'growth:',len(growth))
if __name__=='__main__':main()
