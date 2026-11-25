"""Summarize independently checked internal fields on the same physical UTC."""
from collections import Counter
import csv

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

import analyze_summer_spinup_add7_v50 as v
from execute_summer_spinup_add7_v51 import OUT, ROOT, load, require, write_once
from verify_summer_spinup_add7_v50 import check_row_stats, verified_stats
import diagnose_summer_component_convergence_v49 as history

COMP = ('O1', 'O2', 'N2', 'HE')
REGIONS = ('global', 'south_polar', 'south_mid', 'tropics', 'north_mid', 'north_polar')
ZH = ('全球', '南极', '南中纬', '热带', '北中纬', '北极')
TARGET = v.gpi.TARGET.isoformat()
FIGURES = OUT/'figures'


def table(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def keyed(rows, offset, height=False):
    return {(int(r['hour'])+offset, r.get('variable', 'DEN'), r['region'],
             int(r['height_km'] if height else r['level'])): r for r in rows}


def numbers(row, variable):
    return {'n': int(row['n']), 'P95_relative': float(row['relative_P95']) if row['relative_P95'] else None,
            'RMSE': float(row['RMSE'])/(100 if variable=='WIND_VECTOR' else 1)}


def summarize_gates(old, new):
    require(old.keys() == new.keys(), 'Same-UTC gate inventory changed')
    cells = []
    worst = {14:{}, 21:{}}
    for key, before in old.items():
        after = new[key]
        t, variable, region, level = key
        cells.append(dict(UTC=(v.gpi.START+v.timedelta(hours=t)).isoformat(),
                          hour_14=t-168, hour_21=t, variable=variable, region=region, level=level,
                          n_14=before['n'], n_21=after['n'],
                          fraction_14=before['passed_fraction'], fraction_21=after['passed_fraction'],
                          gate_14=before['passed'], gate_21=after['passed']))
        for days in (14,21):
            prop = cells[-1][f'fraction_{days}']
            selected = worst[days].get(variable)
            if prop and (selected is None or float(prop) < float(selected[f'fraction_{days}'])):
                worst[days][variable] = cells[-1]
    counts = {}
    for variable in (*COMP, 'DEN', 'TN', 'WIND_VECTOR'):
        selected = [x for x in cells if x['variable']==variable]
        counts[variable] = {f'fail_{d}': sum(x[f'gate_{d}']=='False' for x in selected) for d in (14,21)}
        counts[variable]['new_failures'] = sum(x['gate_14']=='True' and x['gate_21']=='False' for x in selected)
        counts[variable]['still_failing'] = sum(x['gate_14']==x['gate_21']=='False' for x in selected)
        counts[variable]['worsened_while_failing'] = sum(
            x['fraction_14'] != '' and x['gate_21']=='False' and
            float(x['fraction_21']) < float(x['fraction_14']) for x in selected)
        counts[variable].update({f'worst_{d}':worst[d].get(variable) for d in (14,21)})
    return cells, counts


def independent_target(new_rows, new_height, runs):
    """Check published target comparison directly in historical and new native volumes."""
    old_rows = {r['variable']:r for r in table(v.OLD_RESULTS/'hourly.csv')
                if r['hour']=='336' and r['region']=='global'}
    old_height = {r['height_km']:r for r in table(v.OLD_RESULTS/'height.csv')
                  if r['hour']=='336' and r['region']=='global'}
    _, _, grid, a, b = next(row for row in history.series(336) if row[0]==336)
    a['WIND_VECTOR'] = np.zeros_like(a['UN'])
    b['WIND_VECTOR'] = np.hypot(b['UN']-a['UN'], b['VN']-a['VN'])
    x, y, new_grid = v.read_frame(runs, v.gpi.TARGET, independent=True)
    require(all(np.array_equal(grid[k], value) for k,value in zip(('lat','lon','lev','ilev'),new_grid)),
            'Historical and new native grids differ')
    weight = np.cos(np.deg2rad(grid['lat']))
    for rows, first, second in ((old_rows,a,b),(new_rows,x,y)):
        for name, row in rows.items():
            check_row_stats(row, verified_stats(first[name],second[name],weight[None,:,None],name))
    from verify_summer_seed_sensitivity_v46 import interpolate_columns
    for rows, first, second in ((old_height,a,b),(new_height,x,y)):
        for h,row in rows.items():
            den = [interpolate_columns(field,int(h)) for field in (first,second)]
            check_row_stats(row, verified_stats(*den,weight[:,None],'DEN'))
    return {k: {str(d): numbers(r[k],k) for d,r in ((14,old_rows),(21,new_rows))}
            for k in old_rows}, {h:{str(d):numbers(r[h],'DEN') for d,r in ((14,old_height),(21,new_height))}
                                 for h in old_height}


def plots(cells, counts, target, heights, hourly, resources):
    font_manager.fontManager.addfont(ROOT/'data/presentation_assets/noto_sans_sc/NotoSansSC-400.ttf')
    plt.rcParams.update({'font.family':'Noto Sans SC','axes.unicode_minus':False})
    FIGURES.mkdir()
    baseline = '2022 夏季 · mareqx / junsol · HINDCAST · 同 UTC 对照'
    def save(fig, filename, caption):
        fig.text(.02,.015,f'{baseline}\n{caption}',fontsize=8)
        fig.tight_layout(rect=(0,.09,1,1))
        fig.savefig(FIGURES/(filename+'.png'),dpi=150)
        plt.close(fig)

    fig, ax = plt.subplots()
    ax.bar(['14 天','21 天'],[100*target['DEN'][d]['P95_relative'] for d in ('14','21')])
    ax.set(title='目标日原生等压界面总密度差异',ylabel='面积加权相对 P95 (%)')
    save(fig,'01_density','2022-06-21 00Z · ilev · n='+str(target['DEN']['21']['n']))
    for i,k in enumerate(COMP,2):
        fig, ax = plt.subplots()
        ax.bar(['14 天','21 天'],[counts[k][f'fail_{d}'] for d in (14,21)])
        ax.set(title=f'{k} 末期失败单元',ylabel='纬区 × lev × 时次')
        save(fig,f'0{i}_{k.lower()}_fail','2022-06-22 00Z 至 06-23 00Z · 各组端点共 25 时次')
    fig, ax = plt.subplots()
    for k in COMP:
        series = [r for r in hourly if r['variable']==k and r['region']=='global' and
                  int(r['hour_V50']) in (24,72,168,336,504)]
        ax.plot([int(r['hour_V50'])/24 for r in series],
                [100*float(r['relative_P95']) for r in series],marker='o',label=k)
    ax.set(title='21 天方案组分差异演化',xlabel='积分日龄',ylabel='面积加权相对 P95 (%)')
    ax.legend()
    save(fig,'06_component_age','2022-05-31 00Z 起 · 全球 lev · 按冻结有效样本定义')
    fig, ax = plt.subplots()
    x = np.arange(len(REGIONS))
    for offset,d in ((-.2,14),(.2,21)):
        ax.bar(x+offset,[sum(c['region']==r and c[f'gate_{d}']=='False' for c in cells) for r in REGIONS],
               width=.4,label=f'{d} 天')
    ax.set(xticks=x,xticklabels=ZH,ylabel='失败单元数',title='末期南北半球与纬区分布')
    ax.legend()
    save(fig,'07_hemispheres','2022-06-22 00Z 至 06-23 00Z · 所有冻结变量与层位')
    fig, axs = plt.subplots(2,2,figsize=(10,6))
    for ax,k in zip(axs.ravel(),COMP):
        counter = Counter((c['region'],c['level']) for c in cells if c['variable']==k and c['gate_21']=='False')
        im=ax.imshow([[counter[r,z] for z in range(29)] for r in REGIONS],aspect='auto',vmin=0,vmax=25)
        ax.set(title=k,yticks=np.arange(6),yticklabels=ZH,xlabel='原生 lev 索引')
        fig.colorbar(im,ax=ax,label='失败时次数')
    save(fig,'08_failed_levels','2022-06-22 00Z 至 06-23 00Z · 每个纬区/层位最多 25 时次')
    fig, ax = plt.subplots()
    for k in COMP:
        series = [r for r in hourly if r['variable']==k and r['region']=='global' and int(r['hour_V50'])>=528]
        ax.plot([int(r['hour_V50'])-528 for r in series],
                [100*float(r['relative_P95']) for r in series],label=k)
    ax.set(title='组分差异末期变化',xlabel='距 2022-06-22 00Z 的小时',ylabel='相对 P95 (%)')
    ax.legend()
    save(fig,'09_terminal','全球原生 lev · 25 时次 · 2022-06-23 00Z 收尾')
    fig, ax = plt.subplots()
    for d in ('14','21'):
        ax.plot([int(h) for h in heights],[100*heights[h][d]['P95_relative'] for h in heights],
                marker='o',label=d+' 天')
    ax.set(title='目标日共同高度总密度差异',xlabel='模型内部 ZG (km)',ylabel='面积加权相对 P95 (%)')
    ax.legend()
    save(fig,'10_common_height','2022-06-21 00Z · 仅在两组共同高度域内插 · 每个时次最多 2592 列')
    fig, ax = plt.subplots()
    passed = {k:sum(c['variable']==k and c['gate_21']=='True' for c in cells) for k in counts}
    ax.bar(passed.keys(),[100*n/(n+counts[k]['fail_21']) for k,n in passed.items()])
    ax.set(title='21 天预热各变量有效验收单元通过率',ylabel='通过单元 (%)',ylim=(0,105))
    save(fig,'11_pass_fractions','2022-06-22 00Z 至 06-23 00Z · 无效空单元分别记录')
    fig, axs = plt.subplots(1,3,figsize=(9,4))
    for ax,field,scale,unit in zip(axs,('elapsed_s','peak_RSS_bytes','NetCDF_bytes'),(60,2**30,2**30),
                                 ('墙钟 (min)','采样树 RSS (GiB)','NetCDF (GiB)')):
        ax.bar(('A','B'),[r[field]/scale for r in resources])
        ax.set_ylabel(unit)
    save(fig,'12_resources','积分 UTC 2022-05-31 00Z 至 06-23 00Z · 每组 4 rank / 47 卷')


def main():
    review = load(v.RESULT/'independent.json')
    require(review['verified'], 'Independent numeric review required')
    runs,ids = v.evidence()
    require(review['run_ids']==ids,'Independent review and native files mismatch')
    old = keyed(table(v.OLD_RESULTS/'gates.csv'),168)
    new = keyed(table(v.RESULT/'gates.csv'),0)
    cells, counts = summarize_gates(old,new)
    require(sum(x['fail_14'] for x in counts.values())==2196,'Historic failure count changed')
    height_gates,_ = summarize_gates(keyed(table(v.OLD_RESULTS/'height_gates.csv'),168,True),
                                    keyed(table(v.RESULT/'height_gates.csv'),0,True))
    hourly = table(v.RESULT/'hourly.csv')
    target_cols = {r['variable']:r for r in hourly if r['UTC']==TARGET and r['region']=='global'}
    target_native = {r['height_km']:r for r in table(v.RESULT/'height.csv')
                     if r['UTC']==TARGET and r['region']=='global'}
    target, heights = independent_target(target_cols,target_native,runs)
    rules = load(v.science.RULES)
    concentrations = {}
    for variable in COMP:
        group = counts[variable]['worst_21']
        t = v.gpi.START+v.timedelta(hours=group['hour_21'])
        a,_,grid = v.read_frame(runs,t,independent=True)
        low,high = rules['latitude_regions'][group['region']]
        x = a[variable][group['level'],(grid[0]>=low)&(grid[0]<=high)]
        x = x[np.isfinite(x)&(np.abs(x)>rules['trace_reference_floor_mmr'])]
        bound = [float(y) for y in np.quantile(x,[0,.5,1])] if len(x) else []
        concentrations[variable] = dict(n=len(x), min_median_max_mmr=bound)
    trends = {}
    old_hourly = table(v.OLD_RESULTS/'hourly.csv')
    for k in COMP:
        trends[k] = {}
        for d, data, index, first in ((14,old_hourly,'hour',360),(21,hourly,'hour_V50',528)):
            r = {int(x[index]):float(x['relative_P95']) for x in data if
                 x['variable']==k and x['region']=='global' and first<=int(x[index])<=first+24}
            require(set(r)==set(range(first,first+25)),'Missing hourly composition statistics')
            values = [r[t] for t in sorted(r)]
            trends[k][str(d)] = dict(start=values[0],end=values[-1],
                                      slope_per_hour=float(np.polyfit(range(25),values,1)[0]))
    summary = load(v.RESULT/'summary.json')
    height_failures = {f'fail_{d}':sum(x[f'gate_{d}']=='False' for x in height_gates) for d in (14,21)}
    require(sum(x['fail_21'] for x in counts.values())+height_failures['fail_21']==summary['full_failed_cells'],
            'New failure inventory differs from independent V50 result')
    resources = [load(OUT/f'engineering_{role}.json') for role in ('A','B')]
    require([r['run_id'] for r in resources]==ids,'Cross-run engineering identity mismatch')
    v.science.csv_save(OUT/'same_UTC_native_gates.csv',cells)
    v.science.csv_save(OUT/'same_UTC_height_gates.csv',height_gates)
    write_once(OUT/'science_comparison.json',dict(target_UTC=TARGET, target=target, heights_km=heights,
        native_gate_counts=counts, common_height_gate_counts=height_failures, worst_cell_reference_mmr=concentrations,
        terminal_global_P95_trends=trends, regions={r:{f'fail_{d}':sum(c['region']==r and
            c[f'gate_{d}']=='False' for c in cells) for d in (14,21)} for r in REGIONS},
        valid={str(d):sum(c[f'gate_{d}']!='' for c in cells+height_gates) for d in (14,21)},
        independent=review, frozen=summary))
    plots(cells,counts,target,heights,hourly,resources)


if __name__ == '__main__':
    main()
