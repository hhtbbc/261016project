"""Aggregate V49 diagnostics and produce explanatory CPU plots."""
import csv
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from itertools import groupby
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
from netCDF4 import Dataset

import diagnose_summer_component_convergence_v49 as d

OUT=d.OUT
ROOT=d.ROOT
C=d.KEYS
BASE_DATE=datetime(2022,6,7)
GLOBAL='global'
STUDY='2022 夏季｜junsol − mareqx｜受限 HINDCAST｜'
REGION_TRANSLATION={'global':'全球','south_polar':'南极','south_mid':'南中纬',
                    'tropics':'低纬','north_mid':'北中纬','north_polar':'北极'}


def f(x):
    return float(x)


def fmt(x):
    return f'{x:.4g}'


def stats_group(failed):
    sets=defaultdict(list)
    for r in failed:
        for name,keys in [('variable',('variable',)),('region',('variable','region')),
                          ('level',('variable','region','level')),('time',('variable','hour'))]:
            sets[(name,*[r[k] for k in keys])].append(r)
    rows=[]
    for k, values in sorted(sets.items()):
        mode,var,*tail=k
        worst=min(values,key=lambda r:f(r['passed_fraction']))
        hrs=sorted(set(int(r['hour']) for r in values))
        longest=max(sum(1 for _ in batch) for _,batch in groupby(enumerate(hrs),lambda p:p[1]-p[0]))
        rows.append(dict(mode=mode,variable=var,region=tail[0] if mode in ('level','region') else '',
            level=tail[1] if mode=='level' else '',hour=tail[0] if mode=='time' else '',
            failed_units=len(values),failed_unique_hours=len(hrs),max_consecutive_failed_hr=longest,
            worst_level=worst['level'],worst_UTC=worst['UTC'],worst_fraction=f(worst['passed_fraction']),
            min_coverage=min(f(r['coverage']) for r in values),min_n=min(int(r['n']) for r in values)))
    return rows


def worst_series(failed):
    output=[]; scatter=[]; components=[]
    for key in C:
        worst=min((r for r in failed if r['variable']==key),key=lambda r:f(r['passed_fraction']))
        level=int(worst['level'])
        lo,hi=d.RANGES[worst['region']]
        n2_clipped=0;n2_fail=0;n2_abs=[]
        for volume in range(1,17):
            with Dataset(d.RUNS[0]/f'secondary_{volume:03d}.nc') as a, Dataset(d.RUNS[1]/f'secondary_{volume:03d}.nc') as b:
                lat=np.asarray(a['lat'][:]);lon=np.asarray(a['lon'][:]);sel=(lat>=lo)&(lat<=hi)
                if key=='N2' and volume>=15:
                    for n in (a,b):
                        n[key].set_auto_mask(False)
                    x=np.asarray(a[key][:],float)
                    y=np.asarray(b[key][:],float)
                    low=abs(x-1e-6)<=5e-15
                    if volume==15:
                        low[:-1]=False
                    n2_clipped+=int(low.sum());large=low&(abs(x-y)/np.maximum(x,1e-8)>=.05)
                    n2_fail+=int(large.sum())
                    if large.any():n2_abs.extend(abs(y-x)[large].tolist())
                for j in range(24):
                    hour=(volume-1)*24+j+1
                    x,y=[d.read(n,key,j)[level,sel] for n in (a,b)]
                    valid,passed,rel=d.gate(x,y)
                    v=int(valid.sum())
                    output.append(dict(variable=key,region=worst['region'],level=level,hour=hour,
                        UTC=(BASE_DATE+timedelta(hours=hour)).isoformat()+'Z',n=v,passed_n=int(passed.sum()),
                        passed_fraction=float(passed.sum()/v) if v else None,
                        P95_relative=float(np.quantile(rel[valid],.95)) if v else None,
                        median_A=float(np.median(x[valid])) if v else None,
                        mean_abs_mmr=float(np.average(abs(y-x)[valid])) if v else None))
                    if hour==int(worst['hour']):
                        for i,k in zip(*np.where(valid)):
                            scatter.append(dict(variable=key,region=worst['region'],level=level,hour=hour,
                                  UTC=worst['UTC'],latitude=float(lat[sel][i]),longitude=float(lon[k]),
                                  reference_mmr=float(x[i,k]),other_mmr=float(y[i,k]),
                                  absolute_mmr=float(abs(y[i,k]-x[i,k])), relative=float(rel[i,k])))
        if key=='N2':
            components.append(dict(native_N2_near_1e_6_tolerance=5e-15,n=n2_clipped,
                failing_n=n2_fail,failing_median_abs_mmr=float(np.median(n2_abs)) if n2_abs else None,
                source='comp.F:97,952-985 composition normalization and residual N2'))
    return output,scatter,components


def trends(hourly, layer):
    result=[]
    for key in C:
        for region in d.RANGES:
            values=[r for r in hourly if r['variable']==key and r['region']==region]
            values.sort(key=lambda r:int(r['hour']))
            for metric in ('MAE_mmr','relative_mean'):
                y=np.array([f(x[metric]) for x in values])
                daily=y.reshape(16,24).mean(axis=1)
                for start in (0,4,8):
                    z=daily[start:]
                    mask=z>1e-14
                    if mask.sum()<5:continue
                    t=np.arange(start+1,17)[mask]
                    log=np.log(z[mask])
                    m,b=np.polyfit(t,log,1)
                    leave=[float(np.polyfit(np.delete(t,i),np.delete(log,i),1)[0]) for i in range(len(t))]
                    result.append(dict(variable=key,region=region,metric=metric,first_day=start+1,
                        n_days=len(t),log_slope_per_day=float(m),leave_one_day_min=min(leave),leave_one_day_max=max(leave),
                        descriptive_tau_days=float(-1/m) if m<0 else None,
                        log_residual_RMS=float(np.sqrt(np.mean((log-(m*t+b))**2))),
                        mean_within_day_CV=float(np.mean(y.reshape(16,24).std(axis=1)/daily)),
                        last48_daily_ratio=float(daily[-1]/daily[-2]),last_24_hourly_positive_increments=int((np.diff(y[-25:])>0).sum())))
    layers=[]
    grouped=defaultdict(dict)
    for r in layer:
        if r['relative_mean'] and int(r['hour'])>=337:
            grouped[(r['variable'],r['region'],int(r['level']))][int(r['hour'])]=f(r['relative_mean'])
    for k,z in grouped.items():
        if len(z)==48:
            x=np.array([z[t] for t in range(337,385)])
            first=x[:24].mean();last=x[-24:].mean()
            layers.append(dict(variable=k[0],region=k[1],level=k[2],previous24_mean=float(first),
                               final24_mean=float(last),ratio=float(last/first) if first>0 else None,
                               slope_per_h=float(np.polyfit(np.arange(25),x[-25:],1)[0])))
    return result,layers


def driver_plan():
    v43=ROOT/'experiments/thermosphere_summer_gpi_candidate_v43/input_freeze.json'
    from datetime import date
    from prepare_summer_gpi_candidate_v43 import inputs,raw_records
    frozen=d.recovery.load(v43)['sources']
    maps={}
    for path in frozen:
        source=d.recovery.load(ROOT/path)
        for k in ('Fobs','Kp'):
            if k in source:
                maps.setdefault(k,set()).update(raw_records(source,k))
    result=d.recovery.load(d.V48/'result.json')
    a=next(r for r in d.recovery.load(d.recovery.OLD/'result.json')['runs'] if r['group']==d.recovery.v46.A)
    mean_minutes=(a['wall_s']+result['run']['elapsed_s'])/120
    plans=[]
    for add in (0,7,14):
        start=date(2022,6,7)-timedelta(days=add)
        end=date(2022,6,23)
        fstart=start-timedelta(days=42);fend=end+timedelta(days=42)
        kstart=start-timedelta(days=2);kend=end+timedelta(days=2)
        fr={(fstart+timedelta(days=j)).isoformat() for j in range((fend-fstart).days+1)}
        kr={(kstart+timedelta(days=j)).isoformat() for j in range((kend-kstart).days+1)}
        available=lambda k:{t.date().isoformat() for t in maps[k]}
        days=(end-start).days
        missing=sorted(kr-available('Kp'))
        plans.append(dict(scenario={0:'A_KEEP14',7:'B_ADD7',14:'C_ADD14'}[add],
            start_UTC=start.isoformat(),end_UTC=end.isoformat(),unchanged_target_date='2022-06-21',
            candidate_preheat_days=14+add,steps_each=days*1440,baseline_or_new_runs=0 if not add else 2,
            Fobs_start=fstart.isoformat(),Fobs_end=fend.isoformat(),Fobs_total=len(fr),
            new_Fobs_dates=sorted(fr-available('Fobs')),Kp_start=kstart.isoformat(),Kp_end=kend.isoformat(),
            Kp_total=8*len(kr),new_Kp_days=missing,new_Kp_buckets=8*len(missing),
            estimated_minutes_per_run=mean_minutes*days/16,
            estimated_AB_minutes_if_executed=mean_minutes*days/8,
            estimated_NetCDF_bytes_per_run=round(result['run']['netcdf_bytes']*days/16)))
    return plans


def plots(failed,pivots,series,scatter,plans,assoc,hemi):
    font=ROOT/'data/presentation_assets/noto_sans_sc/NotoSansSC-400.ttf'
    font_manager.fontManager.addfont(font)
    plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name()
    plt.rcParams['axes.unicode_minus']=False
    def publish(i,fig,title,caption):
        fig.suptitle(title)
        fig.text(.02,.015,STUDY+caption,fontsize=8)
        fig.tight_layout(rect=(0,.05,1,.94))
        fig.savefig(OUT/f'{i:02d}.png',dpi=135)
        plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,4))
    counts=Counter(r['variable'] for r in failed)
    ax.bar(C,[counts[k] for k in C]);ax.set_ylabel('失败验收单元')
    publish(1,fig,'组分门槛失败分布','06-22 00Z 至 06-23 00Z；区域×lev×小时；失败 2196 个')
    regs=tuple(d.RANGES)
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    totals=[sum(r['region']==k for r in failed) for k in regs]
    for ax,vals,title in zip(axes,(totals,[100*x/2900 for x in totals]),('失败单元','失败比例 (%)')):
        ax.bar([REGION_TRANSLATION[x] for x in regs],vals);ax.set_ylabel(title)
    publish(2,fig,'纬度区域的失败数量和比例','末24小时；每个区域 2900 个有效组分单元；全球与区域不可合计成物理点')
    fig,axes=plt.subplots(2,2,figsize=(10,6),sharex=True)
    for ax,key in zip(axes.ravel(),C):
        mat=np.array([[sum(r['variable']==key and r['region']==k and int(r['level'])==j for r in failed) for j in range(29)] for k in regs])
        im=ax.imshow(mat,aspect='auto',vmin=0,vmax=25);ax.set_title(key);ax.set_yticks(range(len(regs)),[REGION_TRANSLATION[k] for k in regs]);ax.set_xlabel('lev 序号');fig.colorbar(im,ax=ax)
    publish(3,fig,'按原生中点层定位失败','末24小时含两端 25 个时刻；每区域×层位最大失败计数 25')
    for i,key in enumerate(C[:3],4):
        f=[r for r in scatter if r['variable']==key]
        fig,ax=plt.subplots(figsize=(8,4));ax.scatter([x['reference_mmr'] for x in f],[100*x['relative'] for x in f],s=7,alpha=.55)
        ax.set_xscale('log');ax.axhline(5,color='firebrick',ls='--');ax.set_xlabel('mareqx 参考浓度 (mmr)');ax.set_ylabel('绝对相对差 (%)')
        publish(i,fig,key+' 参考浓度与相对差',f"{f[0]['UTC']}；{REGION_TRANSLATION[f[0]['region']]}；lev {f[0]['level']}；n={len(f)}")
    fig,axes=plt.subplots(2,1,figsize=(9,6),sharex=True)
    for k in C:
        f=[r for r in d.rows(OUT/'hourly.csv') if r['variable']==k and r['region']=='global']
        axes[0].plot([int(r['hour']) for r in f],[100*float(r['relative_P95']) for r in f],label=k)
        axes[1].plot([int(r['hour']) for r in f],[float(r['MAE_mmr']) for r in f],label=k)
    axes[0].set_ylabel('面积加权相对 P95 (%)');axes[1].set_ylabel('面积加权 MAE (mmr)');axes[1].set_xlabel('06-07 00Z 后小时')
    for a in axes:a.legend(ncol=4)
    publish(7,fig,'四种组分逐小时演化','384 小时；全球 lev；每帧至多 75168 个格点')
    fig,ax=plt.subplots(figsize=(8,4))
    bins=[(k,side) for k in C for side in ('south','north')]
    vals=[100*sum(int(x[side+'_failed']) for x in hemi if x['variable']==k)/sum(int(x['n']) for x in hemi if x['variable']==k) for k,side in bins]
    ax.bar(np.arange(8),vals,color=['#326899','#cd7742']*4)
    ax.set_xticks(range(8),[k+(' 南' if side=='south' else ' 北') for k,side in bins]);ax.set_ylabel('配对格点失败比例 (%)')
    publish(8,fig,'同绝对纬度、经度和局地时的南北对照',
            f"末24小时；每变量约 {sum(int(x['n']) for x in hemi if x['variable']=='O1'):,} 个共同有效点对")
    fig,axes=plt.subplots(2,1,figsize=(9,6),sharex=True)
    for k in C:
        f=[r for r in series if r['variable']==k and r['hour']>=360]
        axes[0].plot([r['hour']-360 for r in f],[100*r['passed_fraction'] for r in f],label=f"{k} lev{f[0]['level']} n={f[0]['n']}")
        axes[1].plot([r['hour']-360 for r in f],[r['mean_abs_mmr'] for r in f],label=k)
    axes[0].axhline(95,color='black',ls='--');axes[0].set_ylabel('格点通过率 (%)');axes[0].legend(ncol=2)
    axes[1].set_ylabel('绝对差均值 (mmr)');axes[1].set_xlabel('06-22 00Z 后小时');axes[1].set_yscale('log')
    publish(9,fig,'各组分最差区域层位的末期轨迹','25 个时刻；同一区域层位保持不变')
    fig,ax=plt.subplots(figsize=(8,4))
    vals=[[float(r['r']) for r in assoc if r['variable']==k and r['field']=='log_DEN' and r['r'] and r['region']== 'south_polar'] for k in C]
    ax.boxplot(vals,tick_labels=[f'{k} n={len(v)}' for k,v in zip(C,vals)]);ax.axhline(0,color='grey',lw=.7);ax.set_ylabel('有符号组分差与 log(DEN 比) 的 Pearson r')
    publish(10,fig,'南极失败层位的组分与密度差共变','末24小时；DEN 从 ilev 对数内插到被包围的 lev；未外推')
    fig,axes=plt.subplots(1,2,figsize=(9,4))
    scenarios=['维持14天','追加7天','追加14天']
    axes[0].bar(scenarios,[p['new_Kp_buckets'] for p in plans]);axes[0].set_ylabel('需补 3 小时 definitive Kp 桶')
    axes[1].bar(scenarios,[p['estimated_AB_minutes_if_executed'] if p['baseline_or_new_runs'] else 0 for p in plans]);axes[1].set_ylabel('预计新增 A+B 串行分钟')
    publish(11,fig,'追加预热代价估计','估算基于 V46 A 与 V48 B 实测；追加方案均未运行；目标日期保持 06-21')


def main():
    failed=d.rows(OUT/'failed_units.csv')
    hourly=d.rows(OUT/'hourly.csv')
    layers=d.rows(OUT/'layer_time.csv')
    assoc=d.rows(OUT/'associations.csv')
    hemi=d.rows(OUT/'hemisphere_pairs.csv')
    pivot=stats_group(failed)
    series,scatter,n2=worst_series(failed)
    fit,layer_trends=trends(hourly,layers)
    plans=driver_plan()
    for name,data in [('failure_pivot',pivot),('worst_layer_series',series),('worst_reference_scatter',scatter),
                      ('descriptive_decay',fit),('late_layer_trends',layer_trends)]:
        d.write(name+'.csv',data)
    d.write('future_design.json',dict(plans=plans,unchanged_target_UTC='2022-06-21',approved_new_runs=0,
            Restart='FAIL_UNVALIDATED_FOR_THIS_USE',restart_used=False,
            design='For fixed target date run new A and B from earlier common date; no automatic extension.'))
    d.write('native_N2_clamp_diagnostic.json',n2)
    plots(failed,pivot,series,scatter,plans,assoc,hemi)


if __name__=='__main__':
    main()
