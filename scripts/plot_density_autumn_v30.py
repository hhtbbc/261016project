"""V30 aggregate tables and Chinese figures from one-time results."""
from collections import Counter
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import ListedColormap
import numpy as np

from density_autumn_v30 import ROOT, OUT, SPRING, YEARS, BANDS, day, load, rows, sha, table
from runtime.tiegcm_rank_exit import write_once

FONT = ROOT/'data/presentation_assets/noto_sans_sc/NotoSansSC-400.ttf'
LABELS = {'Raw':'原始','GlobalAdaptive06':'全局06Z','GlobalAdaptive18':'全局18Z',
          'LatitudeAdaptive18':'纬区18Z','Stale06':'沿用06Z'}
COLORS = dict(zip(LABELS,['#25344a','#147c82','#3b73b8','#cf6540','#7453a1']))
FLAGS = ('RMSE_BENEFIT','RELATIVE_RMS_BENEFIT','TAIL_NONWORSENED','LOW_LATITUDE_BIAS_NONWORSENED')
IDENTITY = 'TIE-GCM / Swarm A DNSAPOD 0301 · UTC · HINDCAST / PROVISIONAL Map-A'


def main(figures_only=False):
    ver=load(OUT/'independent_verification.json')
    assert OUT.resolve()==OUT
    output=OUT/'figures'
    output.mkdir()
    original='通过' if ver['PASS'] else '未闭合'
    font_manager.fontManager.addfont(FONT)
    plt.rcParams.update({'font.family':font_manager.FontProperties(fname=FONT).get_name(),
                         'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False})
    captions=[]
    def save(fig,name,title,caption):
        fig.suptitle(title,fontsize=14)
        fig.text(.5,.014,IDENTITY+f' · 数值独立复核{original}',ha='center',fontsize=8)
        fig.tight_layout(rect=(0,.045,1,.95))
        path=output/name
        assert not path.exists()
        fig.savefig(path,dpi=190,bbox_inches='tight',facecolor='white')
        plt.close(fig)
        captions.append(dict(file='figures/'+name,title_zh=title,caption_zh=caption))
    metrics={year:rows(OUT/f'{year}_metrics.csv') for year in YEARS}
    joints={year:rows(OUT/f'{year}_joint.csv') for year in YEARS}
    maps={year:{(int(r['cutoff']),r['window'],r['method'],r['region']):r for r in metrics[year]} for year in YEARS}
    cache={y:np.load(OUT/f'{y}_matched_local.npz') for y in YEARS}
    times=np.arange(2880)/120
    fig,axes=plt.subplots(2,1,figsize=(12,6),sharex=True)
    for y,ax in zip(YEARS,axes):
        a=cache[y]
        ax.plot(times,a['density']*1e12,color='#a35425',lw=.8,label='Swarm A 反演')
        ax.plot(times,a['raw']*1e12,color=COLORS['Raw'],lw=.9,label='TIE-GCM 原始')
        ax.set(title=day(y),ylabel='密度 / $10^{-12}$ kg m$^{-3}$',ylim=(0,None),xlim=(0,24))
        ax.legend(loc='upper right',fontsize=8)
    axes[-1].set(xlabel='UTC 小时',xticks=range(0,25,3))
    save(fig,'01_raw_time_series.png','2021 与 2022 年 9 月 23 日沿轨密度','30 秒全日真实 Swarm A 反演和原始 TIE-GCM，逐年 2880 点。')
    fig,axes=plt.subplots(2,2,figsize=(13,7))
    for i,y in enumerate(YEARS):
        a=cache[y]
        for ax,h in zip(axes[i],(6,18)):
            idx=(times>=h)&(times<h+6)
            ax.plot(times[idx],a['density'][idx]*1e12,color='black',lw=.8,alpha=.65,label='Swarm A')
            for name in ('Raw',f'GlobalAdaptive{h:02d}',*(('LatitudeAdaptive18','Stale06') if h==18 else ())):
                key='raw' if name=='Raw' else name
                ax.plot(times[idx],a[key][idx]*1e12,lw=1,color=COLORS[name],label=LABELS[name])
            ax.set(title=f'{day(y)} · {h:02d}Z 后 6 小时',xlabel='UTC 小时',
                   ylabel='密度 / $10^{-12}$ kg m$^{-3}$',ylim=(0,None),xlim=(h,h+6))
            ax.legend(ncol=2,fontsize=7)
    save(fig,'02_correction_time_series.png','冻结校正的未来时段沿轨对比','仅显示两个截点后各 6 小时；沿用06Z为同日参数。')
    def leads(fields):
        fig,axes=plt.subplots(2,2,figsize=(12,7))
        for i,y in enumerate(YEARS):
            for ax,h in zip(axes[i],(6,18)):
                for name in ('Raw',f'GlobalAdaptive{h:02d}',*(('LatitudeAdaptive18','Stale06') if h==18 else ())):
                    for key,scale,label,style in fields:
                        ax.plot([1,3,6],[float(maps[y][h,f'future_{lead}h',name,'all'][key])*scale for lead in (1,3,6)],
                                style,markersize=4,color=COLORS[name],label=LABELS[name]+label)
                ax.set(title=f'{day(y)} · {h:02d}Z',xlabel='累计时长 / h',xticks=[1,3,6],ylim=(0,None))
                ax.legend(fontsize=7,ncol=2)
        return fig,axes
    fig,axes=leads([('RMSE',1e12,'','o-')])
    for ax in axes.flat:ax.set_ylabel('RMSE / $10^{-12}$ kg m$^{-3}$')
    save(fig,'03_rmse.png','未来 1、3、6 小时绝对 RMSE','每个累计时长使用全部共同有效观测 ID。')
    fig,axes=leads([('relative_RMS',100,' RMS','o-'),('relative_P95',100,' P95','s--')])
    for ax in axes.flat:ax.set_ylabel('相对误差 / %')
    save(fig,'04_relative_errors.png','未来 1、3、6 小时 Relative RMS 与 P95','分母为同一时刻 Swarm A 反演密度，保留高相对误差和尾部。')
    fig,axes=plt.subplots(2,2,figsize=(12,7))
    for i,y in enumerate(YEARS):
        for ax,h in zip(axes[i],(6,18)):
            names=('Raw',f'GlobalAdaptive{h:02d}',*(('LatitudeAdaptive18','Stale06') if h==18 else ()))
            for j,name in enumerate(names):
                ax.bar(np.arange(3)+(j-(len(names)-1)/2)*.18,
                       [100*float(maps[y][h,'future_6h',name,r]['relative_RMS']) for r in BANDS],
                       width=.17,color=COLORS[name],label=LABELS[name])
            ax.set(title=f'{day(y)} · {h:02d}Z 后累计6小时',ylabel='Relative RMS / %',
                   xticks=[0,1,2],xticklabels=['低纬','中纬','高纬'])
            ax.legend(fontsize=8,ncol=2)
    save(fig,'05_latitude_errors.png','低、中、高纬累计 6 小时的误差','用原始 GRS80 纬度划分 30° 和 60°；未按误差重筛样本。')
    fig,ax=plt.subplots(figsize=(9,4))
    coeff=[]
    for season in ('spring','autumn'):
        for y in YEARS:
            par=(load(OUT/f'{y}_parameters.json')['parameters'] if season=='autumn'
                 else load(SPRING[y]/'correction_parameters.json')['parameters'])
            par=par.get('B14',par)
            for label,c in [('Global06',par['GlobalAdaptive06']),('Global18',par['GlobalAdaptive18']),
                            *[(r,par['LatitudeAdaptive18'][r]) for r in BANDS]]:
                coeff.append(dict(year=y,season=season,method=label,N=c['N'],b=c['b'],multiplier=c['multiplier']))
    for j,y in enumerate(YEARS):
        group=[r for r in coeff if r['year']==y and r['season']=='autumn']
        ax.bar(np.arange(5)+(j-.5)*.32,[r['multiplier'] for r in group],width=.30,
               color=('#147c82','#cf6540')[j],label=str(y))
    ax.axhline(1,color='#52606d',ls='--',lw=.8)
    ax.set(ylabel='历史冻结密度乘数',xticks=range(5),xticklabels=['全局06Z','全局18Z','低纬18Z','中纬18Z','高纬18Z'],ylim=(0,1.08))
    ax.legend()
    save(fig,'06_multipliers.png','两年秋季历史校正乘数','乘数为 NumPy exp(b)，b 为过去3小时 log 残差中位数。')
    fig,axes=plt.subplots(1,2,figsize=(13,8))
    for y,ax in zip(YEARS,axes):
        group=[r for r in joints[y] if r['window'].startswith('future_')]
        z=np.array([[1 if r[k]=='True' else 0 if r[k]=='False' else -1 for k in FLAGS]+
                    [1 if r['JOINT_NO_REGRET']=='PASS' else 0 if r['JOINT_NO_REGRET']=='FAIL' else -1] for r in group])
        ax.imshow(z,aspect='auto',cmap=ListedColormap(['#dddfe3','#f9caac','#b0e3d3']),vmin=-1,vmax=1)
        ax.set(title=day(y),xticks=range(5),xticklabels=['绝对RMSE','相对RMS','相对P95','低纬偏差','联合'],
               yticks=range(12),yticklabels=[f"{LABELS[r['method']]} +{r['window'][7:]}" for r in group])
        for (i,j),value in np.ndenumerate(z):
            ax.text(j,i,{1:'通过',0:'失败',-1:'N/A'}[value],ha='center',va='center',fontsize=8)
    save(fig,'07_joint_matrix.png','四项联合无退化判据','每年12个累计窗口判定，非重叠块另见联合表，累计窗相互嵌套。')
    cross=[]
    counts={}
    for season in ('spring','autumn'):
        for y in YEARS:
            if season=='spring':
                mr=rows(SPRING[y]/'metrics.csv')+rows(SPRING[y]/'region_metrics.csv')
                jr=rows(SPRING[y]/'joint_assessment.csv')
            else:
                mr,jr=metrics[y],joints[y]
            jr=[r for r in jr if r.get('case','B14')=='B14' and r['window'].startswith('future_')]
            counts[f'{y}_{season}']=dict(Counter(r['JOINT_NO_REGRET'] for r in jr))
            jj={(r['cutoff'],r['window'],r['method']):r for r in jr}
            for r in mr:
                if r.get('case','B14')!='B14' or not r['window'].startswith('future_'):
                    continue
                j=jj.get((r['cutoff'],r['window'],r['method']),{})
                cross.append(dict(year=y,season=season,**{k:r[k] for k in
                    ('cutoff','window','region','method','n','MAE','RMSE','bias','relative_RMS','relative_P95','relative_bias')},
                    **{k:j.get(k,'') if r['region']=='all' else '' for k in
                    ('RMSE_gain_pct','relative_RMS_gain_pct','JOINT_NO_REGRET')}))
    fig,axes=plt.subplots(1,3,figsize=(13,4))
    labels=['2021春','2021秋','2022春','2022秋']
    for i,(y,seas) in enumerate([(2021,'spring'),(2021,'autumn'),(2022,'spring'),(2022,'autumn')]):
        raw=[r for r in cross if r['year']==y and r['season']==seas and
             r['method']=='Raw' and r['window']=='future_6h' and r['region']=='all']
        for jj,h in enumerate(('6','18')):
            row=next(r for r in raw if r['cutoff']==h)
            color=('#2b6e84','#cf6540')[jj]
            axes[0].bar(i+(jj-.5)*.33,float(row['RMSE'])*1e12,width=.31,color=color,label=(h.zfill(2)+'Z') if i==0 else None)
            axes[1].bar(i+(jj-.5)*.33,float(row['relative_RMS'])*100,width=.31,color=color)
        axes[2].bar(i,counts[f'{y}_{seas}'].get('PASS',0),color='#147c82')
    for ax,label in zip(axes,['Raw RMSE / $10^{-12}$ kg m$^{-3}$','Raw Relative RMS / %','联合通过组数 / 12']):
        ax.set(xticks=range(4),xticklabels=labels,ylabel=label,ylim=(0,None))
    axes[0].legend()
    save(fig,'08_spring_autumn.png','春季冻结结果与秋季独立日期对照','误差比较为两截点后累计6小时；通过数来自每日期12个累计判据。日期、背景和预热时长共同变化。')
    if figures_only:
        for item in cache.values():
            item.close()
        return
    table(OUT/'cross_season_metrics.csv',cross)
    table(OUT/'cross_season_coefficients.csv',coeff)
    table(OUT/'figure_captions.csv',captions)
    for item in cache.values():
        item.close()
    write_once(OUT/'result.json',dict(
        status='SCIENTIFIC_EVALUATION_COMPLETE_VERIFIED' if ver['PASS'] else 'INCONCLUSIVE',
        score_attempts={str(y):load(OUT/f'{y}_score_receipt.json')['attempts'] for y in YEARS},
        per_date_joint=counts,new_model_runs=0,GPU_calls=0,threshold_changes=False,
        independent_SHA256=sha(OUT/'independent_verification.json'),
        parameter_freeze_SHA256=sha(OUT/'dual_freeze_receipt.json'),
        methods_retuned=False,figure_count=len(captions)))


if __name__=='__main__':
    main(sys.argv[1:] == ['--figures-only'])
