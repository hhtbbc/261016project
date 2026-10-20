"""Offline, frozen-threshold S3/S7 sensitivity comparison; no model launch."""
from pathlib import Path
import sys,json,csv,importlib.util,argparse
import numpy as np
from netCDF4 import Dataset
import matplotlib.pyplot as plt
from scipy.stats import linregress
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('audit_s3',ROOT/'scripts/audit_tiegcm2023_s3.py');a3=importlib.util.module_from_spec(spec);spec.loader.exec_module(a3)
S3=ROOT/'experiments/tiegcm2023_s3_continuous_v1';S7=ROOT/'experiments/tiegcm2023_s7_continuous_v1'
NAMES=['DEN','ZG','TN','UN','VN','O1','O2','N2','HE']


def load_common(directory):
    chunks={k:[] for k in NAMES};times=[];grid=None;schema=None;expected_names=None
    for p in sorted(directory.glob('secondary_*.nc')):
        with Dataset(p) as n:
            n.set_auto_mask(False);mt=np.asarray(n['mtime'][:],int);seconds=mt[:,0]*86400+mt[:,1]*3600+mt[:,2]*60;idx=np.flatnonzero(seconds>=80*86400)
            if not len(idx):continue
            signature={k:(n[k].dimensions,str(n[k].dtype),n[k].units) for k in n.variables if k in NAMES}
            coords={k:np.asarray(n[k][:]) for k in ['lat','lon','lev','ilev']}
            if grid is None:grid=coords;schema=signature
            else:
                assert schema==signature
                for k in grid:np.testing.assert_array_equal(grid[k],coords[k])
            times.extend(seconds[idx].tolist())
            for k in NAMES:
                raw=np.asarray(n[k][idx],dtype=np.float64);raw[abs(raw)>1e30]=np.nan
                scale={'DEN':1000.,'ZG':.01,'UN':.01,'VN':.01}.get(k,1.)
                chunks[k].append(raw*scale)
    assert times==list(range(80*86400,82*86400+601,600))
    return {k:np.concatenate(v) for k,v in chunks.items()},np.asarray(times),grid,schema


def percentile(x,w,q):
    order=np.argsort(x);values=x[order];cum=np.cumsum(w[order]);cum/=cum[-1]
    return float(np.interp(q,cum,values))


def metrics(x,y,weights,limit,relative_limit=False,log_density=False,relative_floor=0.):
    """Area-weighted errors; acceptance fraction counts common-valid grid samples."""
    good=np.isfinite(x)&np.isfinite(y);w=np.broadcast_to(weights,x.shape)[good];u=x[good];v=y[good]
    if not len(u):return {'n':0,'valid_fraction':0.,'pass_fraction':None,'passed':False}
    delta=u-v;absolute=abs(delta);relative_good=abs(v)>relative_floor
    rel=delta[relative_good]/v[relative_good];rw=w[relative_good]
    err=abs(rel) if relative_limit else absolute
    result={'n':int(len(u)),'valid_fraction':float(good.mean()),'relative_n':int(relative_good.sum()),'bias':float(np.average(delta,weights=w)),'RMSE':float(np.sqrt(np.average(delta**2,weights=w))),'signed_median':percentile(delta,w,.5),'absolute_median':percentile(absolute,w,.5),'absolute_P95':percentile(absolute,w,.95),'max_absolute':float(absolute.max()),'relative_abs_P95':percentile(abs(rel),rw,.95) if len(rel) else None,'max_relative_abs':float(abs(rel).max()) if len(rel) else None,'pass_fraction':float((err<limit).mean()) if len(err) else None,'passed':bool(len(err) and (err<limit).mean()>=.95)}
    if log_density:
        assert (u>0).all() and (v>0).all();ld=np.log(u/v)
        result.update(log_bias=float(np.average(ld,weights=w)),log_RMSE=float(np.sqrt(np.average(ld**2,weights=w))),log_abs_P95=percentile(abs(ld),w,.95),log_max_absolute=float(abs(ld).max()))
    return result


def dumpcsv(path,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(rows)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-tag',default='tiegcm2023_s3_s7_comparison_v1');args=parser.parse_args();out=ROOT/'experiments'/args.run_tag
    if out.exists():raise FileExistsError(out)
    assert out.resolve().is_relative_to(ROOT)
    for d in [S3,S7]:assert json.loads((d/'data_audit.json').read_text())['status']=='basic_engineering_audit_passed_not_spinup_convergence'
    rules=json.loads((S7/'frozen_comparison_rules.json').read_text());x,t,grid,schema=load_common(S3);y,ty,gy,sy=load_common(S7);np.testing.assert_array_equal(t,ty);assert schema==sy
    for k in grid:np.testing.assert_array_equal(grid[k],gy[k])
    # Compare all requested field schemas, not merely the nine computed fields.
    import re
    input3=(S3/'input.inp').read_text();input7=(S7/'input.inp').read_text()
    names3=re.findall("'([^']+)'",input3.split('SECFLDS =')[1].split('GSWM_')[0]);names7=re.findall("'([^']+)'",input7.split('SECFLDS =')[1].split('GSWM_')[0]);assert names3==names7 and len(names3)==26
    with Dataset(S3/'secondary_002.nc') as p,Dataset(S7/'secondary_002.nc') as q:
        for k in names3:assert p[k].dimensions==q[k].dimensions and p[k].dtype==q[k].dtype and p[k].units==q[k].units
    # Actual common-window drivers must agree exactly to numerical precision.
    drivers3={v['utc']:v for v in csv.DictReader((ROOT/'results/metrics/tiegcm2023_s3_continuous_v1_drivers.csv').open())}
    drivers7={v['utc']:v for v in csv.DictReader((ROOT/'results/metrics/tiegcm2023_s7_continuous_v1_drivers.csv').open())}
    for date in sorted(set(drivers3)&set(drivers7)):
        for k in ['f107d','f107a','Kp','hpower','ctpoten']:assert abs(float(drivers3[date][k])-float(drivers7[date][k]))<1e-10
    out.mkdir();(out/'frozen_rules_copy.json').write_text(json.dumps(rules,indent=2)+'\n')
    lat=grid['lat'];w2=np.broadcast_to(np.cos(np.deg2rad(lat))[:,None],(36,72));regions={k:(lat>=v[0])&(lat<v[1]) for k,v in rules['latitude_regions'].items()}
    rows=[];time_rows=[];heights=rules['common_native_ZG_heights_km'];fixed_x={};fixed_y={};snapshots={};last=t>=t[-1]-86400
    for h in heights:
        fixed_x[h]=np.stack([a3.at_height(x['ZG'][i],x['DEN'][i],h*1000) for i in range(290)])
        fixed_y[h]=np.stack([a3.at_height(y['ZG'][i],y['DEN'][i],h*1000) for i in range(290)])
    overall_maxima={}
    for name in ['DEN','TN','UN','VN','O1','O2','N2','HE','WIND_VECTOR']:
        if name=='WIND_VECTOR':xx=np.sqrt((x['UN']-y['UN'])**2+(x['VN']-y['VN'])**2);yy=np.zeros_like(xx)
        else:xx=x[name];yy=y[name]
        limit=.05 if name in ['DEN','O1','O2','N2','HE'] else 10. if name=='TN' else 20.
        rel=name in ['DEN','O1','O2','N2','HE'];floor=1e-8 if name in ['O1','O2','N2','HE'] else 0.
        overall_maxima[name]=float(np.nanmax(abs(xx-yy)))
        for level in range(xx.shape[1]):
            for region,mask in regions.items():
                for period,ts in [('full',np.ones(290,bool)),('last24h',last)]:
                    row={'domain':'pressure','variable':name,'SI_unit':('kg/m3' if name=='DEN' else 'K' if name=='TN' else 'm/s' if name in ['UN','VN','WIND_VECTOR'] else '1'),'native_vertical_coordinate':'ilev' if name=='DEN' else 'lev','level_index':level,'level_value':float(grid['ilev' if name=='DEN' else 'lev'][level]),'region':region,'period':period,'limit':limit,'limit_is_relative':rel}
                    row.update(metrics(xx[ts,level][:,mask,:],yy[ts,level][:,mask,:],w2[mask,:],limit,rel,name=='DEN',floor));rows.append(row)
        print('Compared pressure:',name,flush=True)
    for h in heights:
        for region,mask in regions.items():
            for period,ts in [('full',np.ones(290,bool)),('last24h',last)]:
                row={'domain':'native_ZG_height','variable':'DEN','SI_unit':'kg/m3','level_index':h,'level_value':h,'region':region,'period':period,'limit':.05,'limit_is_relative':True}
                row.update(metrics(fixed_x[h][ts][:,mask,:],fixed_y[h][ts][:,mask,:],w2[mask,:],.05,True,True));rows.append(row)
        print('Compared native height:',h,flush=True)
    for i,sec in enumerate(t):
        hour=(sec-80*86400)/3600
        for h in heights:
            m=metrics(fixed_x[h][i],fixed_y[h][i],w2,.05,True,True);time_rows.append({'hour':hour,'native_ZG_height_km':h,**m})
    # Each-time gate catches a short/local failure hidden in a pooled 48h mean.
    gates={};trend=[];sixhour=[]
    for name in ['DEN','TN','WIND_VECTOR','O1','O2','N2','HE']:
        xx=np.sqrt((x['UN']-y['UN'])**2+(x['VN']-y['VN'])**2) if name=='WIND_VECTOR' else x[name]
        yy=np.zeros_like(xx) if name=='WIND_VECTOR' else y[name]
        limit=.05 if name in ['DEN','O1','O2','N2','HE'] else 10. if name=='TN' else 20.
        errors=abs(xx-yy)
        if name in ['DEN','O1','O2','N2','HE']:
            valid=np.isfinite(xx)&np.isfinite(yy)&(abs(yy)>(1e-8 if name!='DEN' else 0))
            errors=np.divide(errors,abs(yy),out=np.full_like(errors,np.nan),where=valid)
        else:valid=np.isfinite(errors)
        failing=0;total=0;worst=1.;worst_location=None
        for reg,mask in regions.items():
            n=valid[:,:,mask,:].sum(axis=(2,3));ok=((errors[:,:,mask,:]<limit)&valid[:,:,mask,:]).sum(axis=(2,3))
            frac=np.divide(ok,n,out=np.full(n.shape,np.nan),where=n>0)
            meaningful=np.isfinite(frac[last]);failing+=int((frac[last][meaningful]<.95).sum());total+=int(meaningful.sum())
            if meaningful.any() and np.nanmin(frac[last])<worst:
                worst=float(np.nanmin(frac[last]));loc=np.unravel_index(np.nanargmin(frac[last]),frac[last].shape);worst_location={'region':reg,'hour':float((t[last][loc[0]]-80*86400)/3600),'level_index':int(loc[1])}
        gates[name]={'last24h_failed_time_level_region_cells':failing,'last24h_evaluated_cells':total,'worst_fraction_below_limit':worst,'worst_location':worst_location,'passed':failing==0 and total>0}
    height_gates={}
    for h in heights:
        failures=0;total=0;worst=1.
        relative=abs(fixed_x[h]/fixed_y[h]-1)
        for reg,mask in regions.items():
            good=np.isfinite(relative[:,mask,:]);n=good.sum(axis=(1,2));ok=((relative[:,mask,:]<.05)&good).sum(axis=(1,2))
            frac=np.divide(ok,n,out=np.full(n.shape,np.nan),where=n>0);values=frac[last];values=values[np.isfinite(values)]
            failures+=int((values<.95).sum());total+=len(values)
            if len(values):worst=min(worst,float(values.min()))
        height_gates[str(h)]={'failed_time_region_cells_last24h':failures,'evaluated_cells':total,'worst_fraction_below_limit':worst,'passed':failures==0 and total>0}
    for h in heights:
        rr=[v for v in time_rows if v['native_ZG_height_km']==h];hours=np.array([v['hour'] for v in rr]);logr=np.array([v['log_RMSE'] for v in rr])
        for label,selection in [('full',hours<=48),('last24h',(hours>=24)&(hours<=48))]:
            fit=linregress(hours[selection],logr[selection]);trend.append({'native_ZG_height_km':h,'period':label,'slope_log_RMSE_per_hour':float(fit.slope),'slope_standard_error_OLS':float(fit.stderr),'slope_pvalue_OLS':float(fit.pvalue),'first_log_RMSE':float(logr[selection][0]),'last_log_RMSE':float(logr[selection][-1]),'note':'serial correlation means OLS p-value is descriptive, not independent-sample inference'})
        for hour in range(0,48,6):
            sel=(hours>=hour)&(hours<hour+6);sixhour.append({'native_ZG_height_km':h,'start_hour':hour,'end_hour':hour+6,'mean_log_RMSE':float(np.mean(logr[sel])),'max_log_RMSE':float(np.max(logr[sel]))})
    dumpcsv(ROOT/'results/metrics'/f'{args.run_tag}_statistics.csv',rows);dumpcsv(ROOT/'results/metrics'/f'{args.run_tag}_time.csv',time_rows);dumpcsv(ROOT/'results/metrics'/f'{args.run_tag}_trend.csv',trend);dumpcsv(ROOT/'results/metrics'/f'{args.run_tag}_sixhour.csv',sixhour)
    meaningful=[v for v in rows if v['n']>0];failed=[{k:v[k] for k in ['domain','variable','level_index','region','period','pass_fraction']} for v in meaningful if not v['passed']]
    result={'comparison_sign':'S3 minus S7; S7 is sensitivity reference, not truth','frames':290,'schema_all26_equal':True,'same_grid_and_drivers':True,'native_pressure_max_absolute_differences_SI':overall_maxima,'native_height_all_common_valid':{str(h):float((np.isfinite(fixed_x[h])&np.isfinite(fixed_y[h])).mean()) for h in heights},'last24h_each_time_pressure_gates':gates,'last24h_each_time_height_gates':height_gates,'pooled_failed_groups':failed,'last24h_all_variable_pressure_gates_pass':all(v['passed'] for v in gates.values()),'along_track_log_density_gate':'not evaluated: vertical datum unresolved','overall_preregistered_gate_pass':False,'overall_gate_note':'Requires all pressure/height criteria plus no growth and along-track gate; N/A prevents complete acceptance','top_native_ZG_ranges_km':{'S3':[float(x['ZG'][:,-1].min()/1000),float(x['ZG'][:,-1].max()/1000)],'S7':[float(y['ZG'][:,-1].min()/1000),float(y['ZG'][:,-1].max()/1000)]},'trend':trend,'new_model_launches':0}
    (out/'comparison_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    def save(fig,suffix):
        fig.tight_layout();fig.savefig(ROOT/'results/figures'/f'{args.run_tag}_{suffix}.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(13,4))
    for ax,index in zip(axes,[0,288]):
        image=ax.pcolormesh(grid['lon'],grid['lat'],100*(fixed_x[450][index]/fixed_y[450][index]-1),shading='auto',cmap='coolwarm');fig.colorbar(image,ax=ax,label='100*(S3/S7 - 1) (%)');ax.set(xlabel='Model longitude (deg)',ylabel='Model latitude (deg)',title=f'Native ZG450 km; forecast hour {(t[index]-80*86400)/3600:g}')
    save(fig,'density_maps')
    fig,axes=plt.subplots(1,2,figsize=(13,4),sharey=True)
    for ax,index in zip(axes,[0,288]):
        im=ax.pcolormesh(grid['lon'],grid['lat'],100*(fixed_x[450][index]/fixed_y[450][index]-1),shading='auto',cmap='viridis',vmin=-8,vmax=0)
        ax.set(xlabel='Model longitude (deg)',ylabel='Model latitude (deg)',title=f'Native ZG450 km: S3-S7 relative density, hour {(t[index]-80*86400)/3600:g}')
    fig.subplots_adjust(right=.86,wspace=.2);box=fig.add_axes([.89,.18,.02,.66]);fig.colorbar(im,cax=box,label='100*(S3/S7 - 1) (%) ; shared scale')
    shared=ROOT/'results/figures'/f'{args.run_tag}_density_shared_scale.png'
    if shared.exists():raise FileExistsError(shared)
    fig.savefig(shared,dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5))
    for period in ['full','last24h']:
        rr=[v for v in rows if v['domain']=='native_ZG_height' and v['region']=='global' and v['period']==period];ax.plot([100*v['relative_abs_P95'] for v in rr],[v['level_value'] for v in rr],'o-',label=period)
    ax.axvline(5,color='red',linestyle='--',label='5% engineering limit');ax.set(xlabel='Area-weighted absolute relative density difference P95 (%)',ylabel='Native ZG height (km)',title='S3/S7 density sensitivity by native height');ax.legend();save(fig,'height_errors')
    fig,ax=plt.subplots(figsize=(10,5))
    height_gates={}
    for h in heights:
        failures=0;total=0;worst=1.
        relative=abs(fixed_x[h]/fixed_y[h]-1)
        for reg,mask in regions.items():
            good=np.isfinite(relative[:,mask,:]);n=good.sum(axis=(1,2));ok=((relative[:,mask,:]<.05)&good).sum(axis=(1,2))
            frac=np.divide(ok,n,out=np.full(n.shape,np.nan),where=n>0);values=frac[last];values=values[np.isfinite(values)]
            failures+=int((values<.95).sum());total+=len(values)
            if len(values):worst=min(worst,float(values.min()))
        height_gates[str(h)]={'failed_time_region_cells_last24h':failures,'evaluated_cells':total,'worst_fraction_below_limit':worst,'passed':failures==0 and total>0}
    for h in heights:
        rr=[v for v in time_rows if v['native_ZG_height_km']==h];ax.plot([v['hour'] for v in rr],[v['log_RMSE'] for v in rr],label=f'ZG {h} km')
    ax.set(xlabel='Hours since 2023-03-21 00:00 UTC',ylabel='Area-weighted RMSE of ln(S3/S7)',title='Native-height density sensitivity, 290 actual common frames');ax.legend();save(fig,'log_time')
    fig,axes=plt.subplots(1,3,figsize=(14,4))
    for ax,k in zip(axes,['TN','UN','VN']):
        im=ax.pcolormesh(grid['lon'],grid['lat'],x[k][0,-2]-y[k][0,-2],shading='auto',cmap='coolwarm');fig.colorbar(im,ax=ax,label='K' if k=='TN' else 'm/s');ax.set(xlabel='Model longitude (deg)',ylabel='Model latitude (deg)',title=f'{k}: S3-S7, native lev {grid["lev"][-2]:g}, hour0')
    save(fig,'temperature_wind')
    fig,axes=plt.subplots(1,4,figsize=(16,4))
    for ax,k in zip(axes,['O1','O2','N2','HE']):
        im=ax.pcolormesh(grid['lon'],grid['lat'],x[k][0,-2]-y[k][0,-2],shading='auto',cmap='coolwarm');fig.colorbar(im,ax=ax,label='Mass mixing ratio');ax.set(xlabel='Model longitude (deg)',ylabel='Model latitude (deg)',title=f'{k} S3-S7, lev {grid["lev"][-2]:g}, hour0')
    save(fig,'composition')
    fig,ax=plt.subplots(figsize=(10,5));hours=(t-80*86400)/3600
    for label,data in [('S3',x),('S7',y)]:ax.plot(hours,data['ZG'][:,-1].min(axis=(1,2))/1000,label=label+' min');ax.plot(hours,data['ZG'][:,-1].max(axis=(1,2))/1000,label=label+' max')
    ax.set(xlabel='Hours since 2023-03-21 00:00 UTC',ylabel='Model top native ZG (km)',title='S3/S7 model top ranges; not WGS84 altitude');ax.legend();save(fig,'top_ranges')
    print(json.dumps({k:v for k,v in result.items() if k not in ['pooled_failed_groups','trend']},indent=2))
if __name__=='__main__':main()
