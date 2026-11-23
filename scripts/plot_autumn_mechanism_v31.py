"""Chinese V31 figures rendered solely from aggregate diagnostic tables."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

from diagnose_autumn_v31 import ROOT, OUT, rows, table, load

CASES=[
    (2021,6,'GlobalAdaptive06','future_3h','2021 06Z 全局'),
    (2022,6,'GlobalAdaptive06','future_6h','2022 06Z 全局'),
    (2022,18,'Stale06','future_6h','2022 18Z 沿用06Z'),
    (2022,18,'LatitudeAdaptive18','future_6h','2022 18Z 纬区'),
]
ABS='绝对 MSE / $10^{-28}$ (kg m$^{-3}$)$^2$'
REL='相对 MSE / $10^{-3}$'


def main():
    assert OUT.resolve()==OUT and load(OUT/'independent_verification.json')['PASS']
    font=ROOT/'data/presentation_assets/noto_sans_sc/NotoSansSC-400.ttf'
    font_manager.fontManager.addfont(font)
    plt.rcParams.update({'font.family':font_manager.FontProperties(fname=font).get_name(),
                         'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False})
    out=OUT/'figures'
    out.mkdir()
    caps=[]
    def save(fig,n,title,caption):
        fig.suptitle(title,fontsize=14)
        fig.text(.5,.012,'冻结 B14 / TIE-GCM × Swarm A 0301 · UTC · 事后探索性诊断',ha='center',fontsize=8)
        fig.tight_layout(rect=(0,.05,1,.95))
        fig.savefig(out/n,dpi=185,bbox_inches='tight',facecolor='white')
        plt.close(fig)
        caps.append(dict(file='figures/'+n,title_zh=title,caption_zh=caption))
    data=rows(OUT/'four_date_raw_frozen.csv')
    dates=('2021-03-25','2021-09-23','2022-03-25','2022-09-23')
    raw={(r['date'],r['cutoff']):r for r in data if r['window']=='future_6h' and r['region']=='all'}
    fig,axs=plt.subplots(1,2,figsize=(11,4.3))
    for ax,metric,scale,label in zip(axs,('RMSE','relative_RMS'),(1e14,100),('Raw RMSE / $10^{-14}$ kg m$^{-3}$','Raw Relative RMS / %')):
        for j,h in enumerate(('6','18')):
            ax.bar(np.arange(4)+(j-.5)*.35,[float(raw[d,h][metric])*scale for d in dates],width=.33,label=h.zfill(2)+'Z')
        ax.set(xticks=range(4),xticklabels=dates,ylabel=label,ylim=(0,None))
        ax.legend()
    save(fig,'01_four_dates_raw.png','四日期原始绝对与相对误差','同一截点后累计6小时；春季只引用冻结值。')

    drift=rows(OUT/'autumn_residual_drift.csv')
    d={(int(r['year']),int(r['cutoff']),r['window'],r['region']):r for r in drift}
    fig,axs=plt.subplots(2,2,figsize=(11,7),sharex=True)
    for i,year in enumerate((2021,2022)):
        for j,h in enumerate((6,18)):
            ax=axs[i,j]; x=np.arange(-3,6)
            group=[d[year,h,f'hour_{k}','all'] for k in x]
            ax.fill_between(x+.5,[float(r['P05']) for r in group],[float(r['P95']) for r in group],alpha=.2,label='P05–P95')
            ax.plot(x+.5,[float(r['P50']) for r in group],'o-',label='逐小时 P50')
            ax.axhline(float(group[0]['b_H']),color='#d05b39',ls='--',label='历史三小时中位数')
            ax.axvline(0,c='#586579',lw=.8)
            ax.axhline(0,c='#aaa',lw=.6)
            ax.set(title=f'{year}-09-23 · {h:02d}Z',ylabel='ln(观测/Raw)',xlabel='相对截点 / h')
            ax.legend(fontsize=8)
    save(fig,'02_residual_drift.png','秋季历史与未来逐小时残差变化','固定一小时块；未来中位数与分位数只用于事后诊断。')

    group=rows(OUT/'stratified_contributions.csv')
    idx={(int(r['year']),int(r['cutoff']),r['method'],r['window'],r['axis'],r['level']):r for r in group}
    fig,axs=plt.subplots(2,4,figsize=(14,6))
    for k,(y,h,m,w,title) in enumerate(CASES):
        q=[idx[y,h,m,w,'density',f'Q{i}'] for i in range(1,6)]
        for i,(key,scale,lab) in enumerate([('delta_abs',1e28,ABS),('delta_rel',1e3,REL)]):
            vals=[float(r[key])*scale for r in q]
            ax=axs[i,k]
            ax.bar(range(5),vals,color=['#c6614b' if v>0 else '#248789' for v in vals])
            ax.axhline(0,color='#555',lw=.7)
            ax.set(title=title if i==0 else '',ylabel=lab if k==0 else '',
                   xticks=range(5),xticklabels=['Q1','Q2','Q3','Q4','Q5'])
    save(fig,'03_density_contributions.png','观测密度五分位的两类误差贡献','全窗口N分母，负为改善。案例依次为+3/+6/+6/+6小时，各箱独立于其他窗口定义。')

    par={y:load(ROOT/f'experiments/thermosphere_autumn_density_validation_v30/{y}_parameters.json')['parameters'] for y in (2021,2022)}
    fig,ax=plt.subplots(figsize=(9,4))
    for j,y in enumerate((2021,2022)):
        a=par[y]
        values=[a['GlobalAdaptive06']['multiplier'],a['GlobalAdaptive18']['multiplier'],
                *[a['LatitudeAdaptive18'][r]['multiplier'] for r in ('low','mid','high')]]
        ax.bar(np.arange(5)+(j-.5)*.36,values,width=.34,label=f'{y}-09-23')
    ax.axhline(1,c='#444',ls='--',lw=.8)
    ax.set(xticks=range(5),xticklabels=['06Z 全局','18Z 全局','18Z 低纬','18Z 中纬','18Z 高纬'],
           ylabel='冻结密度乘数（无量纲）',ylim=(0,None))
    ax.legend()
    save(fig,'04_coefficient_shift.png','同日 06Z 与 18Z 的冻结校正幅度','过去3小时 log 残差中位数取指数；未拟合新预测系数。')

    dec=rows(OUT/'window_decomposition.csv')
    dm={(int(r['year']),int(r['cutoff']),r['method'],r['window']):r for r in dec}
    fig,axs=plt.subplots(2,2,figsize=(11,7))
    names=('future_1h','future_3h','future_6h','block_0_1h','block_1_3h','block_3_6h')
    for ax,(y,h,m,_,title) in zip(axs.flat,CASES):
        vals=[100*(float(dm[y,h,m,w]['abs_corrected_RMSE'])/float(dm[y,h,m,w]['abs_raw_RMSE'])-1) for w in names]
        ax.bar(range(6),vals,color=['#ab5945' if v>0 else '#198383' for v in vals])
        ax.axhline(0,color='#555',lw=.7)
        ax.axvline(2.5,color='#999',ls='--',lw=.8)
        ax.set(title=title,xticks=range(6),xticklabels=['+1','+3','+6','0–1','1–3','3–6'],
               ylabel='绝对 RMSE 变化 / %',xlabel='累计与不重叠时窗 / h')
    save(fig,'05_time_aggregation.png','累计改善与局部退化并存','左侧三条为累计，右侧三条为非重叠；正值表示误差变大。')

    fig,axs=plt.subplots(2,2,figsize=(11,7))
    for ax,(y,h,m,w,title) in zip(axs.flat,CASES):
        r=dm[y,h,m,w]
        vv=[100*float(idx[y,h,m,w,'latitude',region][key])/float(r['raw_abs' if key=='delta_abs' else 'raw_rel'])
            for key in ('delta_abs','delta_rel') for region in ('low','mid','high')]
        for j,label in enumerate(['绝对 MSE','相对 MSE']):
            ax.bar(np.arange(3)+(j-.5)*.35,vv[3*j:3*j+3],width=.32,label=label)
        ax.axhline(0,color='#555',lw=.7)
        ax.legend(fontsize=8)
        ax.set(title=title+(' · +3 h' if w=='future_3h' else ' · +6 h'),xticks=range(3),
               xticklabels=['低纬','中纬','高纬'],ylabel='增量 / 全窗口 Raw MSE (%)')
    save(fig,'06_case_latitude.png','四个案例的纬度贡献及误差冲突','各区增量按同一窗口Raw误差归一化，低中高纬之和为全窗口MSE变化比例。')
    table('figure_captions.csv',caps)


if __name__=='__main__':
    main()
