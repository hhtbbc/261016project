"""UTC-matched local transitions, diagnostic trends and figures."""
from collections import Counter
import json
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from netCDF4 import Dataset, num2date
import numpy as np

import diagnose_summer_n2_residual_v52 as d

UTC='2022-06-22T22:00:00+00:00'
REGIONS=('global','south_polar','south_mid','tropics','north_mid','north_polar')
ZH=('全球','南极','南中纬','热带','北中纬','北极')


def old_grid(utc):
    hour=d.v.utc_hour(d.v.OLD_START,utc)
    volume,index=divmod(hour-1,24)
    arrays=[]
    for path in d.old.RUNS:
        with Dataset(path/f'secondary_{volume+1:03d}.nc') as n:
            t=n['time']
            assert num2date(t[index],t.units).isoformat()==utc.replace(tzinfo=None).isoformat()
            g=d.old.schema(n)
            arrays.append({k:d.old.read(n,k,index) for k in ('N2',*d.COMP)})
    return arrays,g


def local():
    utc=datetime.fromisoformat(UTC)
    fields,g=old_grid(utc)
    a,b,grid=d.frame([d.run.run_path(k) for k in 'AB'],utc)
    for arr,k in zip(grid,('lat','lon','lev','ilev')):
        assert np.array_equal(arr,g[k])
    lat,lon=grid[:2]
    m=lat<=-60
    values=[[f['N2'][26,m] for f in group] for group in (fields,(a,b))]
    valid0,passed0,rel0,_=d.gate(*values[0])
    valid1,passed1,rel1,_=d.gate(*values[1])
    assert valid0.all() and valid1.all()
    assert passed0.sum()==392 and passed1.sum()==390
    rows=[]
    for i,j in zip(*np.where(passed0!=passed1)):
        ref,other=[x[i,j] for x in values[1]]
        rows.append(dict(UTC=UTC,lat=float(lat[m][i]),lon=float(lon[j]),
            old_pass=bool(passed0[i,j]),new_pass=bool(passed1[i,j]),A14_mmr=float(values[0][0][i,j]),
            B14_mmr=float(values[0][1][i,j]),A21_mmr=float(ref),B21_mmr=float(other),
            relative14=float(rel0[i,j]),relative21=float(rel1[i,j]),
            near21=bool(min(abs(ref-d.MODEL_FLOOR),abs(other-d.MODEL_FLOOR))<=d.FLOOR_TOL),
            **{f'delta21_{k}':float((b[k]-a[k])[26,m][i,j]) for k in d.COMP}))
    d.save('local_22Z_transitions.csv',rows)
    return rows


def resources():
    gpi=d.v.gpi
    dates=[(gpi.START-timedelta(days=49-i)).date().isoformat() for i in range(7)]
    freeze=d.run.load(d.v.OUT/'input_freeze.json')
    solar=d.ROOT/'data/raw/tiegcm_training_years_v1/2022_Fobs.json'
    raw=d.run.load(solar)
    assert d.run.sha(solar)==freeze['sources'][str(solar.relative_to(d.ROOT))]
    found={t[:10]:x for t,x in zip(raw['datetime'],raw['Fobs']) if t[:10] in dates}
    assert sorted(found)==dates and all(float(x)>0 for x in found.values())
    times=[(gpi.START-timedelta(days=9)+timedelta(hours=3*i)).isoformat() for i in range(56)]
    kp={}
    for path in (d.ROOT/'data/raw').rglob('*.json'):
        if 'kp' not in path.name.lower() or path.stat().st_size>5*2**20:
            continue
        data=json.loads(path.read_text())
        if not isinstance(data,dict) or 'Kp' not in data:
            continue
        for t,x,status in zip(data.get('datetime',[]),data['Kp'],data.get('status',[])):
            stamp=t.replace('Z','+00:00')
            if stamp in times and status=='def' and data.get('meta',{}).get('source')=='GFZ Potsdam':
                kp[stamp]=x
    receipts=[d.run.load(d.V51/f'engineering_{role}.json') for role in 'AB']
    size=31*max(f['bytes'] for r in receipts for f in r['files'] if f['file'].startswith('primary'))
    size+=30*max(f['bytes'] for r in receipts for f in r['files'] if f['file'].startswith('secondary'))
    elapsed=[r['elapsed_s']*43200/33120 for r in receipts]
    return dict(Fobs_total=115,existing_Fobs=found,Kp_total=280,additional_Kp_present=len(kp),
        additional_Kp_missing=[t for t in times if t not in kp],volume_counts=[31,30],warm_hours=720,
        forecast_seconds=elapsed,estimated_NetCDF_bytes_each=size,old_output_budget=5*2**30,old_wall_s=4800,
        prospective_budget=dict(output_GiB_each=7,wall_s=5400,cleanup_s=5370,disk_start_GiB=35,
                                disk_min_GiB=20,volume_MiB=256,MPI=4,OMP=1,RSS_GiB=16,authorization_required=True))


def plots(fails,series,assoc,grid,comparison,budget,times):
    folder=d.OUT/'figures'
    folder.mkdir()
    font_manager.fontManager.addfont(d.ROOT/'data/presentation_assets/noto_sans_sc/NotoSansSC-400.ttf')
    plt.rcParams.update({'font.family':'Noto Sans SC','axes.unicode_minus':False})
    def save(fig,ax,name,title,annotation):
        ax.set_title(title)
        fig.text(.015,.015,'2022 夏季 · mareqx / junsol · HINDCAST\n'+annotation,fontsize=8)
        fig.tight_layout(rect=(0,.1,1,1))
        fig.savefig(folder/(name+'.png'),dpi=145)
        plt.close(fig)
    for i,region in enumerate(REGIONS):
        for row in fails:
            if row['region']==region:
                row['region_index']=i
    fig,ax=plt.subplots()
    h=ax.scatter([r['region_index'] for r in fails],[int(r['level']) for r in fails],
                 c=[100*float(r['fraction']) for r in fails],s=18)
    fig.colorbar(h,ax=ax,label='通过率 (%)')
    ax.set(xticks=range(6),xticklabels=ZH,ylabel='原生 lev')
    save(fig,ax,'01_space','118 个失败单元的区域与层位','06-22 00Z—06-23 00Z · 118 单元')
    fig,ax=plt.subplots()
    z=Counter((r['region'],int(r['level'])) for r in fails)
    h=ax.imshow([[z[r,k] for k in range(25,29)] for r in REGIONS],aspect='auto',vmin=0)
    fig.colorbar(h,ax=ax,label='失败时次数')
    ax.set(yticks=range(6),yticklabels=ZH,xticks=range(4),xticklabels=range(25,29),xlabel='lev')
    save(fig,ax,'02_levels','纬区和原生层失败热力图','末期 25 时次 · 118 单元')
    fig,ax=plt.subplots()
    hours=sorted({r['UTC'] for r in fails}|{t.isoformat() for t in d.v.LATE_UTC})
    ax.plot(range(25),[sum(r['UTC']==t for r in fails) for t in hours])
    ax.set(xlabel='距 06-22 00Z 小时',ylabel='失败单元数')
    save(fig,ax,'03_hourly','N2 失败单元逐时变化','末期 25 时次 · 118 单元')
    polar=[r for r in series if r['region']=='south_polar' and r['level']=='26']
    fig,ax=plt.subplots()
    ax.plot([int(r['hour'])-528 for r in polar],[100*float(r['fraction']) for r in polar],'.-')
    ax.axhline(95,color='gray',ls='--')
    ax.set(xlabel='距 06-22 00Z 小时',ylabel='通过率 (%)')
    save(fig,ax,'04_polar','南极 lev 26 通过率','每时次 n=432 · 点为真实输出')
    worst=[r for r in grid if r['UTC']=='2022-06-22T10:00:00+00:00']
    fig,ax=plt.subplots()
    h=ax.scatter([float(r['lon']) for r in worst],[float(r['lat']) for r in worst],
                 c=[int(r['failed']) for r in worst],s=8,cmap='coolwarm')
    fig.colorbar(h,ax=ax,label='失败 (1) / 通过 (0)')
    ax.set(xlabel='经度 (°)',ylabel='纬度 (°)')
    save(fig,ax,'05_worst_map','最差单元格点分布','06-22 10Z · 南极 lev 26 · n=432')
    scatter=d.csv_rows(d.OUT/'failed_points_scatter.csv')
    fig,ax=plt.subplots()
    ax.scatter([float(r['A_mmr']) for r in scatter],[100*float(r['relative']) for r in scatter],s=6,alpha=.5)
    ax.set(xscale='log',yscale='log',xlabel='A 组 N2 (mmr)',ylabel='相对绝对差 (%)')
    save(fig,ax,'06_scatter','参考浓度与相对差','末期失败格点时次 · 固定步长抽样 n='+str(len(scatter)))
    fig,ax=plt.subplots()
    diag=d.run.load(d.OUT/'diagnostics.json')
    ax.bar(['两组近下限','仅 A','仅 B','两组远离'],diag['unique_failed_grid_hours'].values())
    ax.set(ylabel='去重失败格点时次')
    save(fig,ax,'07_floor','数值下限附近的失败贡献','末期 · 5602 个去重格点时次')
    fig,ax=plt.subplots()
    keys=['O1','O2','HE','TN','UN','VN','ZG','log_DEN','residual']
    ax.boxplot([[float(r['r']) for r in assoc if r['field']==k and r['subset']=='failed' and r['r']] for k in keys])
    ax.set(xticks=range(1,len(keys)+1),xticklabels=keys,ylabel='Pearson r')
    save(fig,ax,'08_residual','失败格点的 N2 差异关联','末期 · 118 单元 · ZG/DEN 仅内插可比层')
    fig,ax=plt.subplots()
    x=np.arange(6)
    for days,offset in [(14,-.2),(21,.2)]:
        ax.bar(x+offset,[comparison['N2_regions'][r][str(days)] for r in REGIONS],.4,label=f'{days} 天')
    ax.set(xticks=x,xticklabels=ZH,ylabel='N2 失败单元数')
    ax.legend()
    save(fig,ax,'09_comparison','14 天与 21 天同 UTC 对照','末期 25 时次')
    fig,ax=plt.subplots()
    ax.plot([p['hour'] for p in times],[100*p['global_relative_P95'] for p in times],'.-')
    ax.set(xlabel='积分小时',ylabel='全球 N2 相对 P95 (%)')
    save(fig,ax,'10_trend','N2 末期差异趋势','实际 UTC 见 CSV · 每帧 n=75168 · 面积加权')
    fig,ax=plt.subplots()
    for days in ('14','21'):
        ax.plot([int(k) for k in comparison['heights_km']],
                [100*r[days]['P95_relative'] for r in comparison['heights_km'].values()],'.-',label=days+' 天')
    ax.set(xlabel='共同内部 ZG (km)',ylabel='DEN 相对 P95 (%)')
    ax.legend()
    save(fig,ax,'11_DEN','总密度有限不敏感证据','06-21 00Z · ilev 内插 · 每高度 n=2592')
    fig,axs=plt.subplots(1,2)
    avg=np.mean(budget['forecast_seconds'])/60
    axs[0].bar(['21d 实测','28d 估算'],[avg*33120/43200,avg])
    axs[1].bar(['21d 实测','28d 估算'],[4839214612/2**30,budget['estimated_NetCDF_bytes_each']/2**30])
    axs[0].set_ylabel('分钟/组')
    axs[1].set_ylabel('GiB/组')
    save(fig,axs[0],'12_cost','21 天实测与 28 天资源估算','06-21 目标 UTC 固定 · 28 天只做资源设计')



def terminal_audit():
    from verify_summer_n2_residual_v52 import read, independent_mask
    from verify_summer_seed_execution_v48_quantile import historical_order_quantile
    rows=d.csv_rows(d.OUT/'global_trends.csv')
    paths=[d.run.run_path(k) for k in 'AB']
    slopes={}
    last_25={}
    for r in rows:
        if int(r['hour'])<528:
            continue
        t=datetime.fromisoformat(r['UTC'])
        (a,b),lat,*_=read(paths,t)
        valid,_=independent_mask(a,b)
        rel=np.abs((b[valid]-a[valid])/a[valid])
        weights=np.broadcast_to(np.cos(np.pi*lat/180)[None,:,None],a.shape)
        value=historical_order_quantile(rel,weights[valid])
        assert np.isclose(value,float(r['global_relative_P95']),rtol=2e-10)
        last_25[t]=value
    assert len(last_25)==25
    group=[float(r['global_relative_P95']) for r in rows if int(r['hour'])>=504]
    slopes['48h_relative_P95_change']=group[-1]/group[0]-1
    values=np.array(list(last_25.values()))
    slopes.update(relative_P95_increases=int((np.diff(values)>0).sum()),
                  relative_P95_last24_slope=float(np.polyfit(range(25),values,1)[0]))
    target=[r for r in d.csv_rows(d.OUT/'regional_time_series.csv')
            if r['region']=='south_polar' and int(r['level'])==26]
    snapshots=[r for r in target if datetime.fromisoformat(r['UTC']).hour==22 and int(r['hour'])>=480]
    associations=d.csv_rows(d.OUT/'associations.csv')
    corr={}
    for field in (*d.COMP,'residual','TN','UN','VN','ZG','log_DEN'):
        corr[field]={subset:float(np.median(val)) if val else None
            for subset in ('failed','near_failed','away_failed')
            for val in [[float(r['r']) for r in associations if r['field']==field and r['subset']==subset and r['r']!='']]}
    d.run.write_once(d.OUT/'terminal_audit.json',dict(independent_global_P95_rows=len(last_25),
        slopes=slopes, polar_lev26_22Z=snapshots, median_cell_pearson=corr))


def main():
    old_new=d.run.load(d.V51/'science_comparison.json')
    all_rows=d.csv_rows(d.V51/'same_UTC_native_gates.csv')
    old_new['N2_regions']={r:{str(t):sum(x['variable']=='N2' and x['region']==r and x[f'gate_{t}']=='False'
                                         for x in all_rows) for t in (14,21)} for r in REGIONS}
    roots=[d.run.run_path(k) for k in 'AB']
    hours=sorted({7*24,14*24,17*24,19*24,20*24,21*24}|set(range(480,553)))
    global_rows=[]
    for h in hours:
        t=d.v.gpi.START+timedelta(hours=h)
        a,b,g=d.frame(roots,t)
        valid,passed,rel,delta=d.gate(a['N2'],b['N2'])
        weight=np.broadcast_to(np.cos(np.deg2rad(g[0]))[None,:,None],rel.shape)
        global_rows.append(dict(UTC=t.isoformat(),hour=h,n=int(valid.sum()),
            global_relative_P95=d.v.science.percentile(rel[valid],weight[valid]),
            global_absolute_P95=d.q(abs(delta[valid]),95)))
    transitions=local()
    budget=resources()
    d.save('global_trends.csv',global_rows)
    d.run.write_once(d.OUT/'decision.json',dict(decision='EXTEND_28D_NOT_RECOMMENDED',preferred='C',
        evidence=['NUMERICAL_FLOOR_ASSOCIATION','RESIDUAL_PROPAGATION_SUPPORTED',
                  'SLOW_ADJUSTMENT_SUPPORTED','MECHANISM_INCONCLUSIVE'],
        local_new_fail=sum(not r['new_pass'] for r in transitions),
        local_recovered=sum(r['new_pass'] for r in transitions),regional_N2=old_new['N2_regions'],
        engineering28=budget,authorized_new_model_runs=0))
    terminal_audit()
    plots(d.csv_rows(d.OUT/'failures.csv'),d.csv_rows(d.OUT/'regional_time_series.csv'),
          d.csv_rows(d.OUT/'associations.csv'),d.csv_rows(d.OUT/'polar_lev26_grid.csv'),old_new,budget,global_rows)


if __name__=='__main__':
    main()
